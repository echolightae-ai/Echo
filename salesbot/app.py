"""HTTP entry points: Meta (WhatsApp + Instagram) webhooks, email, phone, website chat, admin dashboard."""

import asyncio
import base64
import html
import logging
import re
import secrets
import time
import unicodedata
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import date, datetime
from email.utils import parseaddr
from pathlib import Path

import anthropic
from fastapi import Depends, FastAPI, Form, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field

from salesbot import config
from salesbot.agent import DeliveryError, SalesAgent, TeamActionError
from salesbot.channels import Channels
from salesbot.db import DRAFT_STATUSES, Database
from salesbot.outbound import is_trial
from salesbot.prompts import VOICE_NOTE_TEXT
from salesbot.scheduler import Scheduler
from salesbot.security import verify_meta_signature, verify_twilio_signature
from salesbot.tools import TEAM_STAGES, format_date, lead_summary, lead_tag, lead_url, quote_valid_until, today_local

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger(__name__)
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
RETRY_INBOUND_SECONDS = 120
TRIAL_BANNER = "Trial mode: the bot drafts only, nothing is sent to customers. Review its drafts and rate them."


class ChatIn(BaseModel):
    session_id: str = Field(min_length=8, max_length=64)
    text: str = Field(min_length=1, max_length=2000)
    email: str | None = Field(default=None, max_length=200)


class RateLimiter:
    """In-memory sliding window, per key."""

    def __init__(self, limit: int, window_seconds: float):
        self.limit, self.window = limit, window_seconds
        self.hits: dict[str, deque] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now, hits = time.time(), self.hits[key]
        while hits and now - hits[0] > self.window:
            hits.popleft()
        if len(hits) >= self.limit:
            return False
        hits.append(now)
        return True


def create_app(
    db: Database | None = None,
    channels: Channels | None = None,
    client: anthropic.AsyncAnthropic | None = None,
    start_scheduler: bool = True,
) -> FastAPI:
    s = config.settings
    db = db or Database(s.database_path)
    channels = channels or Channels()
    agent = SalesAgent(db, channels, client)
    scheduler = Scheduler(db, agent)
    background: set[asyncio.Task] = set()
    chat_limiter = RateLimiter(30, 3600)
    ip_limiter = RateLimiter(120, 3600)
    security = HTTPBasic()

    def spawn(coro) -> None:
        task = asyncio.create_task(coro)
        background.add(task)
        task.add_done_callback(background.discard)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if is_trial():
            log.info("TRIAL MODE: the bot writes drafts only and sends nothing to customers")
        if start_scheduler:
            spawn(scheduler.run_forever())
        yield
        for task in list(background):
            task.cancel()

    app = FastAPI(title="EchoLight sales agent", lifespan=lifespan)
    app.state.db, app.state.agent, app.state.scheduler, app.state.background = db, agent, scheduler, background
    app.add_middleware(
        CORSMiddleware, allow_origins=s.webchat_allowed_origins, allow_methods=["POST"], allow_headers=["Content-Type"]
    )

    async def reply_to(lead_id: int, content: list[dict]) -> None:
        """Run the agent for an inbound message; on failure, queue a retry instead of losing the message."""
        try:
            await agent.handle_inbound(lead_id, content)
        except DeliveryError as exc:
            log.exception("reply for lead %s not delivered; resending shortly", lead_id)
            db.schedule_job("deliver", time.time() + RETRY_INBOUND_SECONDS, lead_id, exc.payload)
        except Exception:
            log.exception("reply failed for lead %s; retrying shortly", lead_id)
            db.schedule_job("retry_inbound", time.time() + RETRY_INBOUND_SECONDS, lead_id, {"content": content})

    @app.get("/health")
    async def health() -> dict:
        return {"ok": True, "trial_mode": is_trial()}

    # Meta webhooks (WhatsApp Cloud API and Instagram messaging share one Meta app)

    @app.get("/webhooks/meta")
    async def meta_verify(request: Request) -> Response:
        q = request.query_params
        if q.get("hub.mode") == "subscribe" and s.meta_verify_token and q.get("hub.verify_token") == s.meta_verify_token:
            return PlainTextResponse(q.get("hub.challenge", ""))
        raise HTTPException(403)

    @app.post("/webhooks/meta")
    async def meta_webhook(request: Request) -> dict:
        body = await request.body()
        if not verify_meta_signature(s.meta_app_secret, body, request.headers.get("X-Hub-Signature-256")):
            raise HTTPException(401, "bad signature")
        payload = await request.json()
        if payload.get("object") == "whatsapp_business_account":
            for entry in payload.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    names = {c.get("wa_id"): c.get("profile", {}).get("name") for c in value.get("contacts", [])}
                    for message in value.get("messages", []):
                        if db.mark_seen(f"wa:{message.get('id')}"):
                            spawn(handle_whatsapp(message, names.get(message.get("from"))))
        elif payload.get("object") == "instagram":
            for entry in payload.get("entry", []):
                for event in entry.get("messaging", []):
                    handle_instagram_dm(event)
                for change in entry.get("changes", []):
                    if change.get("field") == "comments":
                        handle_instagram_comment(change.get("value", {}))
        return {"ok": True}

    async def handle_whatsapp(message: dict, profile_name: str | None) -> None:
        wa_id = message["from"]
        if s.owner_whatsapp and wa_id == s.owner_whatsapp:
            # The owner is never a lead, and prices are no longer taken from WhatsApp messages.
            try:
                await channels.whatsapp_text(s.owner_whatsapp, (
                    "Prices are entered only on the dashboard, so this message was not sent to anyone: "
                    f"{s.public_base_url}/admin"))
            except Exception:
                log.exception("could not answer the owner on WhatsApp")
            return
        lead = db.get_or_create_lead("whatsapp", wa_id, phone=f"+{wa_id}", name=profile_name, source="whatsapp")
        content, logged = await whatsapp_content(message)
        db.log_inbound(lead["id"], "whatsapp", **logged)
        if logged["kind"] in ("audio", "document"):
            what = "a voice note" if logged["kind"] == "audio" else "a file"
            await channels.notify_owner(
                f"{lead_tag(lead['id'])} {lead.get('name') or 'A customer'} sent {what}: please check it",
                f"The bot can't open it. Listen to or download it from the dashboard: {lead_url(lead['id'])}\n\n"
                f"{lead_summary(lead)}",
            )
        await reply_to(lead["id"], content)

    async def whatsapp_content(message: dict) -> tuple[list[dict], dict]:
        """What Claude sees, and what the dashboard logs, for one WhatsApp message."""
        kind = message.get("type")
        if kind == "text":
            body = message["text"]["body"]
            return [{"type": "text", "text": body}], {"text": body}
        if kind == "image":
            image = message["image"]
            try:
                data, mime = await channels.whatsapp_media(image["id"])
                blocks = [{"type": "image", "source": {"type": "base64", "media_type": mime,
                                                       "data": base64.b64encode(data).decode()}}]
            except Exception:
                log.exception("could not download WhatsApp image")
                blocks = [{"type": "text", "text": "[The customer sent an image that could not be loaded.]"}]
            caption = image.get("caption") or "[The customer sent this image without a caption.]"
            logged = {"text": f"[Photo] {image.get('caption') or ''}".strip(), "kind": "image",
                      "media_id": image.get("id"), "mime": image.get("mime_type")}
            return blocks + [{"type": "text", "text": caption}], logged
        if kind in ("audio", "voice"):
            audio = message.get(kind) or {}
            logged = {"text": "[Voice note]", "kind": "audio", "media_id": audio.get("id"),
                      "mime": audio.get("mime_type")}
            return [{"type": "text", "text": VOICE_NOTE_TEXT}], logged
        if kind == "location":
            loc = message["location"]
            text = (f"[Shared location: {loc.get('name', '')} {loc.get('address', '')} "
                    f"({loc.get('latitude')}, {loc.get('longitude')})]")
            return [{"type": "text", "text": text}], {"text": text}
        if kind == "button":
            text = message["button"].get("text", "")
            return [{"type": "text", "text": text}], {"text": text}
        if kind == "interactive":
            reply = message["interactive"].get("button_reply") or message["interactive"].get("list_reply") or {}
            return [{"type": "text", "text": reply.get("title", "")}], {"text": reply.get("title", "")}
        if kind == "document":
            document = message["document"]
            name = document.get("filename", "a file")
            logged = {"text": f"[File] {name}", "kind": "document", "media_id": document.get("id"),
                      "mime": document.get("mime_type")}
            return [{"type": "text", "text": f"[The customer sent a document: {name}. You cannot open it; the team "
                                             "has been alerted and will review it.]"}], logged
        text = f"[The customer sent a {kind} message.]"
        return [{"type": "text", "text": text}], {"text": text, "kind": "other"}

    # Prices: entered only on the dashboard (the CRM is the system of record; this form is the bot's only route)

    async def submit_price(lead_id: int, details: str, amount_aed: int | None = None) -> str:
        """Hand the owner's price to the agent. Returns a short confirmation for the owner."""
        try:
            lead = db.get_lead(lead_id)
        except KeyError:
            return f"There is no lead #{lead_id}."
        details = details.strip()
        if not details:
            return "The price message was empty."
        if amount_aed is None:
            amount_aed = parse_amount(details)
        who = lead.get("name") or f"lead #{lead_id}"
        try:
            status = await agent.present_price(lead_id, details, amount_aed)
        except Exception as exc:
            log.exception("presenting the price failed for lead %s", lead_id)
            return (f"The price is saved, but writing the message failed ({type(exc).__name__}). It will be given "
                    f"when {who} next writes.")
        lead = db.get_lead(lead_id)
        valid = lead.get("quote_valid_until")
        messages = {
            "sent": f"Price sent to {who}." + (f" Valid until {format_date(date.fromisoformat(valid))}." if valid else ""),
            "drafted": (f"Trial mode: nothing was sent. The bot drafted the price message for {who}; review it below. "
                        "To send it, press 'Use this draft' and send it yourself."),
            "queued": (f"{who} last wrote more than 24 hours ago, so WhatsApp only allows a template. They were told "
                       "their quote is ready, and the price will be given as soon as they reply."),
            "waiting": f"{who} can't be messaged right now. The price is saved and will be given when they write again.",
            "paused": ("The bot is paused for this lead, so it did not message the customer. The price is saved: send "
                       "it yourself with 'Reply as team' and tick 'This message gives the customer the price'."),
            "do_not_contact": f"{who} asked not to be contacted, so nothing was sent. The price is saved.",
        }
        message = messages.get(status, f"Price saved ({status}).")
        if status == "queued" and is_trial():
            message = ("Trial mode: nothing was sent. " + message.replace("They were told", "Live, they would be told")
                       .replace("the price will be given", "the price would be given"))
        return message

    # Instagram

    def handle_instagram_dm(event: dict) -> None:
        message = event.get("message") or {}
        sender = event.get("sender", {}).get("id")
        if not message or message.get("is_echo") or not sender or sender == s.instagram_account_id:
            return
        if not db.mark_seen(f"ig:{message.get('mid')}"):
            return
        text = message.get("text") or "[The customer sent an attachment or sticker.]"
        lead = db.get_or_create_lead("instagram", sender, source="instagram_dm")
        db.log_inbound(lead["id"], "instagram", text)
        spawn(reply_to(lead["id"], [{"type": "text", "text": text}]))

    def handle_instagram_comment(value: dict) -> None:
        text = value.get("text") or ""
        author = value.get("from", {})
        if author.get("id") == s.instagram_account_id or not comment_triggers(text, s.instagram_comment_keywords):
            return
        if not db.mark_seen(f"igc:{value.get('id')}"):
            return
        lead = db.get_or_create_lead("instagram", author.get("id", value["id"]), name=author.get("username"),
                                     source="instagram_comment")
        db.log_inbound(lead["id"], "instagram", text, kind="comment")
        spawn(reply_to_comment(lead["id"], value["id"], text))

    async def reply_to_comment(lead_id: int, comment_id: str, text: str) -> None:
        try:
            await agent.handle_comment(lead_id, comment_id, text)
        except Exception:
            log.exception("comment reply failed for lead %s", lead_id)

    # Email (any provider's inbound webhook: Postmark JSON, SendGrid form, or {from, subject, text} JSON)

    @app.post("/webhooks/email")
    async def email_webhook(request: Request) -> dict:
        if not s.email_inbound_token or not secrets.compare_digest(request.query_params.get("token", ""), s.email_inbound_token):
            raise HTTPException(401)
        if request.headers.get("content-type", "").startswith("application/json"):
            data = await request.json()
        else:
            data = dict(await request.form())
        sender = data.get("From") or data.get("from") or ""
        name, address = parseaddr(sender)
        name = data.get("FromName") or name
        subject = data.get("Subject") or data.get("subject") or ""
        body = data.get("StrippedTextReply") or data.get("TextBody") or data.get("text") or ""
        address = address.lower()
        if not address or address == (s.email_from or s.smtp_user).lower():
            return {"ok": True, "ignored": True}
        if s.owner_email and address == s.owner_email.lower():
            # Replies to alert emails are not read (prices come only from the dashboard), and the owner is no lead.
            return {"ok": True, "ignored": True}
        if not db.mark_seen(f"email:{data.get('MessageID') or hash((address, subject, body))}"):
            return {"ok": True, "duplicate": True}
        lead = db.get_or_create_lead("email", address, email=address, name=name or None, source="email")
        text = f"Subject: {subject}\n\n{body.strip()[:8000]}"
        db.log_inbound(lead["id"], "email", text)
        spawn(reply_to(lead["id"], [{"type": "text", "text": text}]))
        return {"ok": True}

    # Phone (Twilio): ring the team first if configured, otherwise or if unanswered, follow up on WhatsApp

    async def twilio_params(request: Request) -> dict[str, str]:
        params = {k: str(v) for k, v in (await request.form()).items()}
        url = s.public_base_url.rstrip("/") + request.url.path
        if request.url.query:
            url += "?" + request.url.query
        if not verify_twilio_signature(s.twilio_auth_token, url, params, request.headers.get("X-Twilio-Signature")):
            raise HTTPException(401, "bad signature")
        return params

    def missed_call_twiml() -> Response:
        twiml = (
            '<?xml version="1.0" encoding="UTF-8"?><Response>'
            '<Say voice="Polly.Hala-Neural" language="ar-AE">أهلاً بك في إيكو لايت. الفريق سيتواصل معك في أقرب وقت.</Say>'
            '<Say voice="Polly.Joanna-Neural" language="en-US">Thanks for calling EchoLight. The team will get back to '
            'you as soon as possible.</Say><Hangup/></Response>'
        )
        return Response(twiml, media_type="application/xml")

    async def handle_missed_call(caller: str) -> None:
        digits = "".join(ch for ch in caller if ch.isdigit())
        if not digits:
            return
        lead = db.get_or_create_lead("whatsapp", digits, phone=f"+{digits}", source="missed_call")
        db.log_inbound(lead["id"], "phone", "[Missed call]", kind="call")
        try:
            status = await agent.send_template(lead, "missed_call")
        except Exception:
            log.exception("missed-call WhatsApp failed")
            status = "failed"
        outcome = {
            "sent": "The bot sent them a WhatsApp message.",
            "drafted": "Trial mode: a WhatsApp message was drafted, not sent. Please call them back.",
        }.get(status, "No WhatsApp message was sent. Please call them back.")
        await channels.notify_owner(f"{lead_tag(lead['id'])} Missed call", f"Caller: {caller}\n{outcome}\n"
                                                                           f"{lead_url(lead['id'])}")

    @app.post("/webhooks/voice")
    async def voice_incoming(request: Request) -> Response:
        params = await twilio_params(request)
        if s.call_forward_number:
            twiml = (
                '<?xml version="1.0" encoding="UTF-8"?><Response>'
                f'<Dial timeout="20" action="/webhooks/voice/after-dial">{html.escape(s.call_forward_number)}</Dial>'
                "</Response>"
            )
            return Response(twiml, media_type="application/xml")
        spawn(handle_missed_call(params.get("From", "")))
        return missed_call_twiml()

    @app.post("/webhooks/voice/after-dial")
    async def voice_after_dial(request: Request) -> Response:
        params = await twilio_params(request)
        if params.get("DialCallStatus") == "completed":
            return Response('<?xml version="1.0" encoding="UTF-8"?><Response><Hangup/></Response>',
                            media_type="application/xml")
        spawn(handle_missed_call(params.get("From", "")))
        return missed_call_twiml()

    # Website chat

    @app.post("/chat")
    async def chat(body: ChatIn, request: Request) -> dict:
        ip = request.client.host if request.client else "unknown"
        if not ip_limiter.allow(ip) or not chat_limiter.allow(body.session_id):
            raise HTTPException(429, "Too many messages, please message us on WhatsApp: +971 56 722 0533")
        lead = db.get_or_create_lead("webchat", body.session_id, source="website")
        if body.email:
            db.update_lead(lead["id"], email=body.email)
        db.log_inbound(lead["id"], "webchat", body.text)
        try:
            reply = await agent.handle_inbound(lead["id"], [{"type": "text", "text": body.text}], deliver=False)
        except Exception:
            log.exception("web chat reply failed")
            reply = ("Sorry, something went wrong on our side. Please message us on WhatsApp at +971 56 722 0533 "
                     "and we'll reply right away.")
        if is_trial() or db.get_lead(lead["id"])["bot_paused"]:
            # Nothing the bot wrote is shown; the widget tells the visitor the team will get back to them.
            return {"reply": "", "held": True}
        return {"reply": reply or ""}

    @app.get("/widget.js")
    async def widget() -> FileResponse:
        return FileResponse(STATIC_DIR / "widget.js", media_type="application/javascript")

    # Admin dashboard (HTTP basic auth; any username, password = ADMIN_TOKEN)

    def admin(credentials: HTTPBasicCredentials = Depends(security)) -> None:
        if not s.admin_token or not secrets.compare_digest(credentials.password, s.admin_token):
            raise HTTPException(401, headers={"WWW-Authenticate": "Basic"})

    def same_site(request: Request) -> None:
        origin = request.headers.get("origin")
        if origin and origin.rstrip("/") != s.public_base_url.rstrip("/"):
            raise HTTPException(403, "cross-site form post")

    def lead_or_404(lead_id: int) -> dict:
        try:
            return db.get_lead(lead_id)
        except KeyError:
            raise HTTPException(404)

    def result_page(lead_id: int, message: str) -> HTMLResponse:
        return _page_response(f"Lead {lead_id}", f"<p>{html.escape(message)}</p>"
                                                  f"<p><a href='/admin/leads/{lead_id}'>Back to the lead</a></p>")

    @app.get("/admin", response_class=HTMLResponse, dependencies=[Depends(admin)])
    async def admin_index() -> str:
        pending = db.pending_draft_counts()
        rows = "".join(
            f"<tr><td><a href='/admin/leads/{l['id']}'>{l['id']}</a></td><td>{_e(l['name'])}</td>"
            f"<td>{_e(l['channel'])}</td><td>{_e(l['event_type'])}</td><td>{_e(l['event_date'])}</td>"
            f"<td>{_e(l['stage'])}{' <span class=pill>paused</span>' if l['bot_paused'] else ''}</td>"
            f"<td>{_aed(l)}</td><td>{_validity(l)}</td><td>{pending.get(l['id'], '')}</td>"
            f"<td>{_ago(l['updated_at'])}</td></tr>"
            for l in db.list_leads()
        )
        return _page("Leads", f"<p><a href='/admin/drafts'>Drafts to review ({sum(pending.values())})</a></p>"
                              "<div class=scroll><table><tr><th>#</th><th>Name</th><th>Channel</th><th>Event</th>"
                              "<th>Date</th><th>Stage</th><th>Quote</th><th>Valid until</th><th>Drafts</th>"
                              f"<th>Updated</th></tr>{rows}</table></div>")

    @app.get("/admin/drafts", response_class=HTMLResponse, dependencies=[Depends(admin)])
    async def admin_drafts() -> str:
        drafts = db.drafts(limit=300)
        names = {l["id"]: l for l in db.list_leads(limit=5000)}
        items = "".join(
            f"<div class='msg draft'><p><a href='/admin/leads/{d['lead_id']}'>#{d['lead_id']} "
            f"{_e((names.get(d['lead_id']) or {}).get('name')) or 'lead'}</a> · "
            f"{_e((names.get(d['lead_id']) or {}).get('stage'))}</p>{_draft_html(d)}</div>"
            for d in drafts
        )
        return _page("Drafts", f"<p><a href='/admin'>All leads</a></p>{_readiness(db.drafts(limit=100000))}"
                               f"{items or '<p>No drafts yet.</p>'}")

    @app.get("/admin/leads/{lead_id}", response_class=HTMLResponse, dependencies=[Depends(admin)])
    async def admin_lead(lead_id: int, draft: int | None = None) -> str:
        lead = lead_or_404(lead_id)
        hidden = ("agent_notes", "channel_user_id")
        details = "".join(
            f"<tr><th>{_e(k)}</th><td>{_e(_show(k, v))}</td></tr>"
            for k, v in lead.items() if v not in (None, "") and k not in hidden
        )
        paused = bool(lead["bot_paused"])
        pause_form = (
            f"<form method='post' action='/admin/leads/{lead_id}/{'resume' if paused else 'pause'}'>"
            f"<button>{'Resume bot' if paused else 'Pause bot (take over this chat)'}</button></form>"
        )
        stage_forms = "".join(
            f"<form method='post' action='/admin/leads/{lead_id}/stage'><input type=hidden name=stage value='{k}'>"
            f"<button>{_e(label)}</button></form>"
            for k, label in TEAM_STAGES.items() if lead["stage"] != k
        )
        pills = f"<span class=pill>{_e(lead['stage'])}</span>"
        if paused:
            pills += " <span class='pill warn'>bot paused: the team is handling this chat</span>"
        if _validity(lead):
            pills += f" <span class=pill>{_validity(lead)}</span>"
        trial = is_trial()
        price_form = (
            f"<h2>Give the price</h2><form method='post' action='/admin/leads/{lead_id}/price'>"
            "<label>Amount in AED, excluding VAT (for reports)<br><input name='amount' inputmode='numeric' "
            "placeholder='28000'></label><br><label>Exact wording for the customer<br>"
            "<textarea name='details' rows='4' required placeholder='AED 28,000 excl. VAT (+5% VAT) - lighting, "
            "6x3m LED wall, setup and 2 technicians'></textarea></label><br>"
            f"<button>{'Save price (trial: the bot drafts the message)' if trial else 'Send to customer'}</button>"
            "</form>"
        )
        prefill, prefill_price = "", False
        if draft:
            chosen = db.get_draft(draft)
            if chosen and chosen["lead_id"] == lead_id:
                prefill = chosen["text"]
                prefill_price = chosen["kind"] == "price"
        problem = agent.team_reply_problem(lead)
        reply_form = (
            f"<h2 id='reply'>Reply as team</h2><p class=muted>{_e(problem) or 'You can message this customer now.'} "
            "This sends for real, even in trial mode, because you are sending it.</p>"
            f"<form method='post' action='/admin/leads/{lead_id}/reply'>"
            f"<textarea name='text' rows='4' required>{_e(prefill)}</textarea><br>"
            f"<label><input type='checkbox' name='gives_price' value='1'{' checked' if prefill_price else ''}> "
            "This message gives the customer the price (starts the "
            f"{s.quote_validity_days}-day validity)</label><br>"
            f"<input type='hidden' name='draft_id' value='{draft or ''}'><button>Send now as the team</button></form>"
        )
        timeline = _timeline(db, lead_id)
        bookings = "".join(f"<li>{_e(b['kind'])}: {_e(b['preferred_time'])}</li>" for b in db.bookings(lead_id))
        return _page(
            f"Lead {lead_id}",
            f"<p><a href='/admin'>All leads</a> · <a href='/admin/drafts'>Drafts</a></p><p>{pills}</p>"
            f"<div class=actions>{pause_form}{stage_forms}</div><div class=scroll><table>{details}</table></div>"
            f"{price_form}{reply_form}<h2>Conversation</h2>{timeline or '<p>No messages yet.</p>'}"
            f"<h2>Bookings</h2><ul>{bookings or '<li>none</li>'}</ul>",
        )

    @app.post("/admin/leads/{lead_id}/price", dependencies=[Depends(admin)])
    async def admin_price(lead_id: int, request: Request, details: str = Form(...), amount: str = Form("")) -> Response:
        same_site(request)
        lead_or_404(lead_id)
        amount_aed = None
        if amount.strip():
            cleaned = re.sub(r"[,\s]|aed", "", amount.strip(), flags=re.I)
            if not cleaned.isdigit():
                return result_page(lead_id, "The amount must be a number in AED, for example 28000. Nothing was saved.")
            amount_aed = int(cleaned)
        return result_page(lead_id, await submit_price(lead_id, details, amount_aed))

    @app.post("/admin/leads/{lead_id}/reply", dependencies=[Depends(admin)])
    async def admin_reply(lead_id: int, request: Request, text: str = Form(...), gives_price: str = Form(""),
                          draft_id: str = Form("")) -> Response:
        same_site(request)
        lead_or_404(lead_id)
        try:
            message = await agent.team_reply(lead_id, text, gives_price=bool(gives_price),
                                             draft_id=int(draft_id) if draft_id.isdigit() else None)
        except TeamActionError as exc:
            message = f"Not sent. {exc}"
        return result_page(lead_id, message)

    @app.post("/admin/leads/{lead_id}/pause", dependencies=[Depends(admin)])
    async def admin_pause(lead_id: int, request: Request) -> Response:
        same_site(request)
        lead_or_404(lead_id)
        agent.pause(lead_id)
        return result_page(lead_id, "Bot paused for this lead. Customer messages are logged and you are alerted, "
                                    "but the bot won't reply or draft. Use 'Reply as team' to answer.")

    @app.post("/admin/leads/{lead_id}/resume", dependencies=[Depends(admin)])
    async def admin_resume(lead_id: int, request: Request) -> Response:
        same_site(request)
        lead_or_404(lead_id)
        agent.resume(lead_id)
        return result_page(lead_id, "Bot resumed. It will read what happened while it was paused before its next reply.")

    @app.post("/admin/leads/{lead_id}/stage", dependencies=[Depends(admin)])
    async def admin_stage(lead_id: int, request: Request, stage: str = Form(...)) -> Response:
        same_site(request)
        lead_or_404(lead_id)
        try:
            message = agent.team_set_stage(lead_id, stage)
        except TeamActionError as exc:
            message = str(exc)
        return result_page(lead_id, message)

    @app.post("/admin/drafts/{draft_id}/review", dependencies=[Depends(admin)])
    async def admin_review(draft_id: int, request: Request, status: str = Form(...), feedback: str = Form(""),
                           back: str = Form("/admin/drafts")) -> Response:
        same_site(request)
        if status not in DRAFT_STATUSES or not db.get_draft(draft_id):
            raise HTTPException(400, "unknown draft or rating")
        db.review_draft(draft_id, status, feedback.strip())
        target = back if back.startswith("/admin") and "//" not in back else "/admin/drafts"
        return RedirectResponse(f"{target}#draft-{draft_id}", status_code=303)

    @app.get("/admin/inbox/{item_id}/media", dependencies=[Depends(admin)])
    async def admin_media(item_id: int) -> Response:
        item = db.inbound_item(item_id)
        if not item or not item["media_id"]:
            raise HTTPException(404)
        try:
            data, mime = await channels.whatsapp_media(item["media_id"])
        except Exception:
            log.exception("media %s could not be fetched", item_id)
            raise HTTPException(502, "WhatsApp no longer has this file (media expires after some weeks).")
        extension = (mime or "").split("/")[-1].split(";")[0] or "bin"
        return Response(data, media_type=mime or "application/octet-stream",
                        headers={"Content-Disposition": f'inline; filename="{item["kind"]}-{item_id}.{extension}"'})

    app.state.submit_price = submit_price
    return app


# Prices

_CURRENCY = r"(?:(?<![A-Za-z])(?:AED|Dhs?\.?)(?![A-Za-z])|درهم|د\.إ)"
_NUMBER = r"\d{1,3}(?:[,٬]\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?"


def _to_int(figure: str) -> int:
    return int(float(figure.replace(",", "").replace("٬", "")))


def parse_amount(text: str) -> int | None:
    """Fallback for reports when the amount field is empty: the price figure in the owner's wording.

    Prefers the number next to AED/درهم ("AED 28,000", "28,000 درهم"). Without a currency it takes the first figure
    of 100 or more, skipping years (1900-2100), so "Dec 2026 gala, 28,000" gives 28000, not 2026.
    """
    for pattern in (rf"{_CURRENCY}\s*({_NUMBER})", rf"({_NUMBER})\s*{_CURRENCY}"):
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return _to_int(match.group(1))
    for match in re.finditer(r"\d{1,3}(?:[,٬]\d{3})+|\d{3,}", text):
        figure = match.group()
        value = _to_int(figure)
        if figure.isdigit() and 1900 <= value <= 2100:
            continue
        if value >= 100:
            return value
    return None


# Instagram comment keywords

_PRICE_PHRASES = [
    re.compile(r"سعر"),                                  # سعر، السعر، كم السعر
    re.compile(r"[اأإ]سعار"),                            # أسعار، الأسعار
    re.compile(r"^بكم(?!\w)"),                           # "بكم ...؟" asks the price; "فخورين بكم" (proud of you) doesn't
    re.compile(r"\bprices?\b|\bpricing\b|\bquotes?\b|\bquotation\b|\bhow much\b"),
]


def _normalize(text: str) -> str:
    """Lower-case, drop Arabic diacritics and tatweel, and trim punctuation, emoji and spaces from both ends."""
    text = "".join(c for c in unicodedata.normalize("NFKC", text) if unicodedata.category(c) != "Mn" and c != "ـ")
    keep = [unicodedata.category(c)[0] in "LN" for c in text]
    if True not in keep:
        return ""
    start, end = keep.index(True), len(keep) - keep[::-1].index(True)
    return " ".join(text[start:end].casefold().split())


def comment_triggers(text: str, keywords: list[str]) -> bool:
    """Should this reel/post comment get a private sales DM?

    Only when the whole comment is a call-to-action keyword ("عرض", "عرض!", "price 🔥"), or it clearly asks about
    price. "عرض رهيب" ("amazing show") is a compliment, not a request, so it gets nothing.
    """
    comment = _normalize(text)
    if not comment:
        return False
    if comment in {_normalize(k) for k in keywords}:
        return True
    return any(p.search(comment) for p in _PRICE_PHRASES)


# Dashboard HTML


def _e(value) -> str:
    return "" if value in (None, "") else html.escape(str(value))


def _show(key: str, value) -> str:
    if key.endswith("_at") and isinstance(value, (int, float)):
        return _when(value)
    return str(value)


def _aed(lead: dict) -> str:
    return f"AED {lead['quote_aed']:,}" if lead["quote_aed"] else ("priced" if lead["quote_details"] else "")


def _validity(lead: dict) -> str:
    valid = quote_valid_until(lead)
    if not valid:
        return ""
    days = (valid - today_local()).days
    if days >= 0:
        return f"valid until {valid:%d %b}" + (" (today)" if days == 0 else "")
    return f"expired {-days}d ago"


def _when(ts: float) -> str:
    local = datetime.fromtimestamp(ts, config.settings.timezone)
    return f"{local:%a %d %b %H:%M} ({_ago(ts)})"


def _ago(ts: float | None) -> str:
    if not ts:
        return ""
    minutes = int((time.time() - ts) / 60)
    return f"{minutes}m ago" if minutes < 120 else f"{minutes // 60}h ago" if minutes < 2880 else f"{minutes // 1440}d ago"


def _draft_html(d: dict) -> str:
    status = d["status"].replace("_", " ")
    sent = f" · sent by the team {_ago(d['sent_at'])}" if d["sent_at"] else ""
    answers = (f"<p class=muted>Answering: {_e(d['in_reply_to'][:500])}</p>" if d["in_reply_to"] else "")
    buttons = "".join(
        f"<button name='status' value='{v}'{' class=on' if d['status'] == v else ''}>{label}</button>"
        for v, label in (("good", "Good"), ("needs_changes", "Needs changes"), ("wrong", "Wrong"))
    )
    return (
        f"<p id='draft-{d['id']}'><b>Draft: {_e(d['kind'].replace('_', ' '))}</b> ({_e(d['channel'])}) · "
        f"{_when(d['created_at'])} · <b>{_e(status)}</b>{sent}</p>{answers}<pre>{_e(d['text'])}</pre>"
        f"<form method='post' action='/admin/drafts/{d['id']}/review'>"
        f"<input type='hidden' name='back' value='/admin/leads/{d['lead_id']}'>"
        f"<textarea name='feedback' rows='2' placeholder='What should change? (optional)'>{_e(d['feedback'])}</textarea>"
        f"<br>{buttons} <a href='/admin/leads/{d['lead_id']}?draft={d['id']}#reply'>Use this draft</a></form>"
    )


def _readiness(drafts: list[dict]) -> str:
    """How often the drafts were right: the numbers to decide when to switch trial mode off."""
    week_ago = time.time() - 7 * 86400

    def score(items: list[dict]) -> str:
        reviewed = [d for d in items if d["status"] != "pending"]
        if not reviewed:
            return "no reviews yet"
        good = sum(d["status"] == "good" for d in reviewed)
        return f"{round(100 * good / len(reviewed))}% good of {len(reviewed)} reviewed"

    kinds = sorted({d["kind"] for d in drafts})
    by_kind = "".join(f"<li>{_e(k.replace('_', ' '))}: {score([d for d in drafts if d['kind'] == k])}</li>"
                      for k in kinds)
    pending = sum(d["status"] == "pending" for d in drafts)
    return (f"<h2>Readiness</h2><p>{pending} waiting for review. Overall: {score(drafts)}. Last 7 days: "
            f"{score([d for d in drafts if (d['reviewed_at'] or 0) >= week_ago])}.</p><ul>{by_kind}</ul>")


def _timeline(db: Database, lead_id: int) -> str:
    items = []
    for m in db.inbound_messages(lead_id):
        media = ""
        if m["media_id"]:
            url = f"/admin/inbox/{m['id']}/media"
            if m["kind"] == "audio":
                media = f"<br><audio controls preload='none' src='{url}'></audio> <a href='{url}' download>Download</a>"
            elif m["kind"] == "image":
                media = f"<br><a href='{url}'>Open photo</a>"
            else:
                media = f"<br><a href='{url}' download>Download file</a>"
        items.append((m["created_at"], f"<div class='msg customer'><b>Customer</b> ({_e(m['channel'])}) · "
                                       f"{_when(m['created_at'])}<pre>{_e(m['text'])}</pre>{media}</div>"))
    for m in db.outbound_messages(lead_id):
        who = "the team" if m["sender"] == "team" else "the bot"
        items.append((m["created_at"], f"<div class='msg sent'><b>Sent by {who}</b> ({_e(m['channel'])}) · "
                                       f"{_when(m['created_at'])}<pre>{_e(m['text'])}</pre></div>"))
    for d in db.drafts(lead_id):
        items.append((d["created_at"], f"<div class='msg draft'>{_draft_html(d)}</div>"))
    return "".join(block for _, block in sorted(items, key=lambda item: item[0]))


def _page_response(title: str, body: str) -> HTMLResponse:
    return HTMLResponse(_page(title, body))


def _page(title: str, body: str) -> str:
    banner = f"<p class=banner>{TRIAL_BANNER}</p>" if is_trial() else ""
    return (
        f"<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width'>"
        f"<title>{html.escape(title)} - EchoLight sales</title><style>"
        "body{font-family:system-ui;margin:16px;max-width:960px}"
        "table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid #ddd;padding:6px;text-align:start;"
        "vertical-align:top}.scroll{overflow-x:auto}pre{white-space:pre-wrap;word-wrap:break-word;font:inherit;margin:6px 0}"
        ".msg{padding:8px;margin:8px 0;border-radius:8px}.customer{background:#f3f3f3}.sent{background:#eef6ff}"
        ".draft{background:#fff8e6;border:1px dashed #d9a400}.muted{color:#666}.banner{background:#fff1c2;padding:8px;"
        "border-radius:6px}.pill{background:#eee;border-radius:10px;padding:2px 8px}.warn{background:#ffd9d9}"
        ".actions form{display:inline-block;margin:0 6px 6px 0}textarea,input[name=amount]{width:100%;"
        "box-sizing:border-box}button.on{font-weight:bold;outline:2px solid #333}</style></head>"
        f"<body>{banner}<h1>{html.escape(title)}</h1>{body}</body></html>"
    )
