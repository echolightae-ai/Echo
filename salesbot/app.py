"""HTTP entry points: Meta (WhatsApp + Instagram) webhooks, email, phone, website chat, admin dashboard."""

import asyncio
import base64
import html
import logging
import re
import secrets
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from email.utils import parseaddr
from pathlib import Path

import anthropic
from fastapi import Depends, FastAPI, Form, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field

from salesbot import config
from salesbot.agent import DeliveryError, SalesAgent
from salesbot.channels import Channels
from salesbot.db import Database
from salesbot.scheduler import Scheduler
from salesbot.security import verify_meta_signature, verify_twilio_signature

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger(__name__)
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
RETRY_INBOUND_SECONDS = 120


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
            db.schedule_job("deliver", time.time() + RETRY_INBOUND_SECONDS, lead_id, {"text": exc.text})
        except Exception:
            log.exception("reply failed for lead %s; retrying shortly", lead_id)
            db.schedule_job("retry_inbound", time.time() + RETRY_INBOUND_SECONDS, lead_id, {"content": content})

    @app.get("/health")
    async def health() -> dict:
        return {"ok": True}

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
            await handle_owner_whatsapp(message)
            return
        lead = db.get_or_create_lead("whatsapp", wa_id, phone=f"+{wa_id}", name=profile_name, source="whatsapp")
        content = await whatsapp_content(message)
        await reply_to(lead["id"], content)

    async def whatsapp_content(message: dict) -> list[dict]:
        kind = message.get("type")
        if kind == "text":
            return [{"type": "text", "text": message["text"]["body"]}]
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
            return blocks + [{"type": "text", "text": caption}]
        if kind in ("audio", "voice"):
            return [{"type": "text", "text": "[The customer sent a voice note. You cannot listen to it. Ask them "
                                             "kindly to type the key details, in their language.]"}]
        if kind == "location":
            loc = message["location"]
            return [{"type": "text", "text": f"[Shared location: {loc.get('name', '')} {loc.get('address', '')} "
                                             f"({loc.get('latitude')}, {loc.get('longitude')})]"}]
        if kind == "button":
            return [{"type": "text", "text": message["button"].get("text", "")}]
        if kind == "interactive":
            reply = message["interactive"].get("button_reply") or message["interactive"].get("list_reply") or {}
            return [{"type": "text", "text": reply.get("title", "")}]
        if kind == "document":
            name = message["document"].get("filename", "a file")
            return [{"type": "text", "text": f"[The customer sent a document: {name}. You cannot open it; the team "
                                             "will review it.]"}]
        return [{"type": "text", "text": f"[The customer sent a {kind} message.]"}]

    # Prices from the owner

    async def submit_price(lead_id: int, details: str) -> str:
        """Hand the owner's price to the agent. Returns a short confirmation for the owner."""
        try:
            lead = db.get_lead(lead_id)
        except KeyError:
            return f"There is no lead #{lead_id}."
        details = details.strip()
        if not details:
            return "The price message was empty."
        status = await agent.present_price(lead_id, details, parse_amount(details))
        who = lead.get("name") or f"lead #{lead_id}"
        if status == "sent":
            return f"Price sent to {who}."
        return (f"{who} last wrote more than 24 hours ago, so WhatsApp only allows a template. They were told their "
                "quote is ready, and the price will be given as soon as they reply.")

    async def handle_owner_whatsapp(message: dict) -> None:
        body = (message.get("text") or {}).get("body", "")
        match = re.match(r"\s*#\s*(\d+)\s+(.+)", body, re.DOTALL)
        if match:
            try:
                reply = await submit_price(int(match.group(1)), match.group(2))
            except Exception:
                log.exception("owner price failed")
                reply = "Something went wrong sending that price. Please try again or use the dashboard."
        else:
            reply = ("To send a price, start with the lead number, for example:\n"
                     "#12 AED 28,000 incl. VAT - lighting, LED wall, setup and 2 technicians")
        await channels.whatsapp_text(s.owner_whatsapp, reply)

    async def handle_owner_email(subject: str, body: str) -> None:
        match = re.search(r"\[Lead #(\d+)\]", subject)
        price = strip_quoted_reply(body)
        if not match or not price:
            return
        try:
            reply = await submit_price(int(match.group(1)), price)
        except Exception:
            log.exception("owner price failed")
            reply = "Something went wrong sending that price. Please try again or use the dashboard."
        await channels.notify_owner(f"[Lead #{match.group(1)}] {reply}", f"Your message:\n{price}")

    def handle_instagram_dm(event: dict) -> None:
        message = event.get("message") or {}
        sender = event.get("sender", {}).get("id")
        if not message or message.get("is_echo") or not sender or sender == s.instagram_account_id:
            return
        if not db.mark_seen(f"ig:{message.get('mid')}"):
            return
        text = message.get("text") or "[The customer sent an attachment or sticker.]"
        lead = db.get_or_create_lead("instagram", sender, source="instagram_dm")
        spawn(reply_to(lead["id"], [{"type": "text", "text": text}]))

    def handle_instagram_comment(value: dict) -> None:
        text = (value.get("text") or "").lower()
        author = value.get("from", {})
        if author.get("id") == s.instagram_account_id or not any(k.lower() in text for k in s.instagram_comment_keywords):
            return
        if not db.mark_seen(f"igc:{value.get('id')}"):
            return
        lead = db.get_or_create_lead("instagram", author.get("id", value["id"]), name=author.get("username"),
                                     source="instagram_comment")
        spawn(reply_to_comment(lead["id"], value["id"], value.get("text") or ""))

    async def reply_to_comment(lead_id: int, comment_id: str, text: str) -> None:
        try:
            reply = await agent.handle_comment(lead_id, text)
            if reply:
                await channels.instagram_private_reply(comment_id, reply)
                # A private reply opens the conversation; the customer's answer arrives as a normal DM.
                db.update_lead(lead_id, last_inbound_at=time.time())
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
        if not db.mark_seen(f"email:{data.get('MessageID') or hash((address, subject, body))}"):
            return {"ok": True, "duplicate": True}
        if s.owner_email and address == s.owner_email.lower():
            spawn(handle_owner_email(subject, body))
            return {"ok": True, "owner": True}
        lead = db.get_or_create_lead("email", address, email=address, name=name or None, source="email")
        spawn(reply_to(lead["id"], [{"type": "text", "text": f"Subject: {subject}\n\n{body.strip()[:8000]}"}]))
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
            '<Say voice="Polly.Hala-Neural" language="ar-AE">أهلاً بك في إيكو لايت. أرسلنا لك رسالة على واتساب لنكمل معك فوراً.</Say>'
            '<Say voice="Polly.Joanna-Neural" language="en-US">Thanks for calling EchoLight. We have just sent you a WhatsApp message so we '
            'can help you right away.</Say><Hangup/></Response>'
        )
        return Response(twiml, media_type="application/xml")

    async def handle_missed_call(caller: str) -> None:
        digits = "".join(ch for ch in caller if ch.isdigit())
        if not digits:
            return
        lead = db.get_or_create_lead("whatsapp", digits, phone=f"+{digits}", source="missed_call")
        try:
            await agent.send_template(lead, "missed_call")
        except Exception:
            log.exception("missed-call WhatsApp failed")
        await channels.notify_owner("Missed call", f"Caller: {caller}\nThe bot sent a WhatsApp follow-up.")

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
        try:
            reply = await agent.handle_inbound(lead["id"], [{"type": "text", "text": body.text}], deliver=False)
        except Exception:
            log.exception("web chat reply failed")
            reply = ("Sorry, something went wrong on our side. Please message us on WhatsApp at +971 56 722 0533 "
                     "and we'll reply right away.")
        return {"reply": reply or ""}

    @app.get("/widget.js")
    async def widget() -> FileResponse:
        return FileResponse(STATIC_DIR / "widget.js", media_type="application/javascript")

    # Admin dashboard (HTTP basic auth; any username, password = ADMIN_TOKEN)

    def admin(credentials: HTTPBasicCredentials = Depends(security)) -> None:
        if not s.admin_token or not secrets.compare_digest(credentials.password, s.admin_token):
            raise HTTPException(401, headers={"WWW-Authenticate": "Basic"})

    @app.get("/admin", response_class=HTMLResponse, dependencies=[Depends(admin)])
    async def admin_index() -> str:
        rows = "".join(
            f"<tr><td><a href='/admin/leads/{l['id']}'>{l['id']}</a></td><td>{html.escape(l['name'] or '')}</td>"
            f"<td>{l['channel']}</td><td>{html.escape(l['event_type'] or '')}</td>"
            f"<td>{html.escape(l['event_date'] or '')}</td><td>{l['stage']}</td>"
            f"<td>{_aed(l)}</td><td>{_ago(l['updated_at'])}</td></tr>"
            for l in db.list_leads()
        )
        return _page("Leads", "<table><tr><th>#</th><th>Name</th><th>Channel</th><th>Event</th><th>Date</th>"
                              f"<th>Stage</th><th>Quote</th><th>Updated</th></tr>{rows}</table>")

    @app.get("/admin/leads/{lead_id}", response_class=HTMLResponse, dependencies=[Depends(admin)])
    async def admin_lead(lead_id: int) -> str:
        try:
            lead = db.get_lead(lead_id)
        except KeyError:
            raise HTTPException(404)
        details = "".join(
            f"<tr><th>{k}</th><td>{html.escape(str(v))}</td></tr>"
            for k, v in lead.items() if v not in (None, "") and k != "agent_notes"
        )
        messages = []
        for turn in db.transcript(lead_id):
            if turn["role"] != "user":
                continue
            for block in turn["content"]:
                if block.get("type") == "text":
                    messages.append((block, "customer"))
        conversation = "".join(
            f"<p class='{who}'><b>{who}:</b> {html.escape(block['text'])}</p>" for block, who in messages
        )
        sent = "".join(
            f"<p class='bot'><b>sent ({m['channel']}, {_ago(m['created_at'])}):</b> {html.escape(m['text'])}</p>"
            for m in db.outbound_messages(lead_id)
        )
        bookings = "".join(f"<li>{b['kind']}: {html.escape(b['preferred_time'])}</li>" for b in db.bookings(lead_id))
        price_form = (
            f"<h2>Send the price</h2><form method='post' action='/admin/leads/{lead_id}/price'>"
            "<textarea name='details' rows='4' style='width:100%' required placeholder='AED 28,000 incl. VAT - "
            "lighting, 6x3m LED wall, setup and 2 technicians'></textarea><button>Send to customer</button></form>"
        )
        return _page(f"Lead {lead_id}", f"<p><a href='/admin'>All leads</a></p><table>{details}</table>{price_form}"
                                        f"<h2>Bookings</h2><ul>{bookings or '<li>none</li>'}</ul>"
                                        f"<h2>Customer messages</h2>{conversation}<h2>Messages sent</h2>{sent}")

    @app.post("/admin/leads/{lead_id}/price", dependencies=[Depends(admin)])
    async def admin_price(lead_id: int, request: Request, details: str = Form(...)) -> Response:
        origin = request.headers.get("origin")
        if origin and origin.rstrip("/") != s.public_base_url.rstrip("/"):
            raise HTTPException(403, "cross-site form post")
        message = await submit_price(lead_id, details)
        return _page_response(f"Lead {lead_id}", f"<p>{html.escape(message)}</p>"
                                                 f"<p><a href='/admin/leads/{lead_id}'>Back to the lead</a></p>")

    app.state.submit_price = submit_price
    return app


def parse_amount(text: str) -> int | None:
    """First figure that looks like a price (100 or more), e.g. 'AED 28,000' -> 28000."""
    for match in re.finditer(r"\d{1,3}(?:,\d{3})+|\d{3,}", text):
        return int(match.group().replace(",", ""))
    return None


def strip_quoted_reply(body: str) -> str:
    """Keep only what the owner typed above the quoted alert in an email reply."""
    kept = []
    for line in body.splitlines():
        if line.startswith(">") or re.match(r"^\s*On .+wrote:\s*$", line) or line.strip() == "--":
            break
        kept.append(line)
    return "\n".join(kept).strip()


def _aed(lead: dict) -> str:
    return f"AED {lead['quote_aed']:,}" if lead["quote_aed"] else ("priced" if lead["quote_details"] else "")


def _page_response(title: str, body: str) -> HTMLResponse:
    return HTMLResponse(_page(title, body))


def _ago(ts: float | None) -> str:
    if not ts:
        return ""
    minutes = int((time.time() - ts) / 60)
    return f"{minutes}m ago" if minutes < 120 else f"{minutes // 60}h ago" if minutes < 2880 else f"{minutes // 1440}d ago"


def _page(title: str, body: str) -> str:
    return (
        f"<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width'>"
        f"<title>{title} - EchoLight sales</title><style>body{{font-family:system-ui;margin:16px;}}"
        "table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid #ddd;padding:6px;text-align:start}"
        ".customer{background:#f3f3f3;padding:6px}.bot{background:#eef6ff;padding:6px}</style></head>"
        f"<body><h1>{title}</h1>{body}</body></html>"
    )
