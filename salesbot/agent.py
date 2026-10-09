"""The sales agent: runs Claude over a lead's conversation and hands replies to the outbound gate."""

import asyncio
import json
import logging
import time
from collections import defaultdict
from datetime import date, datetime, time as dtime

import anthropic

from salesbot import config
from salesbot.channels import ChannelError, Channels
from salesbot.db import Database
from salesbot.knowledge import load_business_facts
from salesbot.outbound import DRAFTED, SENT, SKIPPED, Outbound, is_trial
from salesbot.prompts import (
    COMMENT_INSTRUCTION,
    FINAL_FOLLOWUP_NOTE,
    FOLLOWUP_INSTRUCTION,
    NO_REPLY,
    PAUSE_NOTE,
    PRICE_READY_INSTRUCTION,
    RESUME_NOTE,
    TEAM_REPLY_NOTE,
    TRIAL_NOTE,
    build_system_prompt,
)
from salesbot.tools import (
    BEFORE_QUOTED,
    NO_FOLLOWUP_STAGES,
    TEAM_STAGES,
    ToolExecutor,
    apply_stage,
    format_date,
    lead_summary,
    lead_tag,
    lead_url,
    quote_status_note,
    quote_valid_until,
    tool_definitions,
    valid_until_from,
)

log = logging.getLogger(__name__)

WHATSAPP_WINDOW_SECONDS = 24 * 3600
MAX_TOOL_ROUNDS = 8
FALLBACK_BETA = "server-side-fallback-2026-07-01"
EXPIRY_REMINDER_HOUR = 10  # the expiry-day check-in goes out at 10:00 UAE time

LEAD_CONTEXT_KEYS = ("name", "phone", "email", "language", "event_type", "event_date", "venue", "emirate",
                     "guest_count", "indoor_outdoor", "services", "budget_aed", "stage", "quote_details",
                     "quote_valid_until", "marketing_opt_in", "source")


class AgentError(Exception):
    pass


class TeamActionError(Exception):
    """A dashboard action that can't be done; the message is shown to the team."""


class DeliveryError(Exception):
    """Claude wrote the reply but the channel refused it. Resend the text; don't re-run Claude."""

    def __init__(self, text: str, kind: str = "reply", quote_valid_until: str | None = None):
        super().__init__("reply written but not delivered")
        self.text = text
        self.kind = kind
        self.quote_valid_until = quote_valid_until

    @property
    def payload(self) -> dict:
        return {"text": self.text, "kind": self.kind, "quote_valid_until": self.quote_valid_until}


def _strip_declined_partial(blocks: list[dict]) -> list[dict]:
    """After a mid-output model fallback, drop non-text blocks that came before the last fallback marker."""
    last = max((i for i, b in enumerate(blocks) if b.get("type") == "fallback"), default=None)
    if last is None:
        return blocks
    return [b for b in blocks[:last] if b.get("type") == "text"] + blocks[last:]


def content_text(content: list[dict]) -> str:
    """The customer's message as plain text, for notes and drafts."""
    parts = [b["text"] if b.get("type") == "text" else f"[{b.get('type')}]" for b in content]
    return "\n".join(p for p in parts if p).strip()


class SalesAgent:
    def __init__(self, db: Database, channels: Channels, client: anthropic.AsyncAnthropic | None = None):
        self.db = db
        self.channels = channels
        self.client = client or anthropic.AsyncAnthropic()
        s = config.settings
        self.system_prompt = build_system_prompt(load_business_facts(s.knowledge_dir), s.quote_validity_days)
        self.tools = tool_definitions()
        self.outbound = Outbound(db, channels)
        self.executor = ToolExecutor(db, channels, self.outbound)
        self._locks: dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)

    # Public entry points

    async def handle_inbound(self, lead_id: int, content: list[dict], deliver: bool = True) -> str | None:
        """A customer wrote to us. Reply (or draft, in trial mode), reset follow-ups, and return the reply text."""
        async with self._locks[lead_id]:
            self.db.update_lead(lead_id, last_inbound_at=time.time())
            self.db.cancel_jobs(lead_id, ("followup", "reactivation"))
            lead = self.db.get_lead(lead_id)
            said = content_text(content)
            if lead["bot_paused"]:
                # The team has taken over: log it for the agent's next turn and tell the team, but don't answer.
                self.db.append_note(lead_id, PAUSE_NOTE.format(text=said))
                await self.channels.notify_owner(
                    f"{lead_tag(lead_id)} {lead.get('name') or 'A customer'} wrote (bot paused, please reply)",
                    f"{said}\n\nReply from the dashboard: {lead_url(lead_id)}",
                )
                return None
            kind, extra, valid_until = "reply", "", None
            if lead["price_to_send"]:
                valid_until = valid_until_from()
                kind, extra = "price", self._price_instruction(lead, valid_until)
            reply = await self._turn(lead, content, extra)  # on failure the caller queues a retry
            try:
                if reply and deliver:
                    try:
                        await self.deliver(lead_id, reply, kind, valid_until and valid_until.isoformat(), said)
                    except Exception as exc:
                        raise DeliveryError(reply, kind, valid_until and valid_until.isoformat()) from exc
                elif reply:
                    # Website chat: live, the reply goes back in the HTTP response; in trial it is only a draft.
                    status = await self.outbound.chat_reply(self.db.get_lead(lead_id), reply, kind, in_reply_to=said,
                                                            quote_valid_until=valid_until and valid_until.isoformat())
                    self._after_send(lead_id, kind, status, valid_until and valid_until.isoformat())
            finally:
                self._schedule_followups(lead_id)
            return reply

    async def handle_comment(self, lead_id: int, comment_id: str, comment_text: str) -> str | None:
        """Someone commented a keyword on a post or reel: one private DM reply, and nothing more until they DM us."""
        async with self._locks[lead_id]:
            lead = self.db.get_lead(lead_id)
            if lead["bot_paused"] or lead["do_not_contact"]:
                return None
            content = [{"type": "text", "text": f"[Instagram comment] {comment_text}"}]
            reply = await self._turn(lead, content, COMMENT_INSTRUCTION)
            if reply:
                await self.outbound.comment_reply(self.db.get_lead(lead_id), comment_id, reply, comment_text)
            # No follow-ups and no 24-hour window: the person has only commented, they haven't written to us.
            return reply

    async def present_price(self, lead_id: int, details: str, amount_aed: int | None = None) -> str:
        """The owner priced the project. Give it to the customer now, or as soon as WhatsApp allows.

        Returns "sent" or "drafted" (trial) when the price message was written now; "queued" when the customer
        must write first (they were sent, or in trial drafted, a 'quote ready' template); "waiting" when there is no
        way to reach them until they write again; "paused" or "do_not_contact" when nothing was written.
        """
        async with self._locks[lead_id]:
            lead = self.db.update_lead(lead_id, quote_details=details, quote_aed=amount_aed, price_to_send=1,
                                       priced_at=time.time())
            self.db.cancel_jobs(lead_id, ("price_reminder",))
            if lead["bot_paused"]:
                return "paused"
            if lead["do_not_contact"]:
                return "do_not_contact"
            if self._can_send_free_text(lead):
                valid_until = valid_until_from()
                note = [{"type": "text", "text": "[The team has priced the project.]"}]
                reply = await self._turn(lead, note, self._price_instruction(lead, valid_until))
                if not reply:
                    return "waiting"
                status = await self.deliver(lead_id, reply, "price", valid_until.isoformat())
                self._schedule_followups(lead_id)
                return status
            # Outside the 24-hour window: nudge with a template; the price is given when they reply.
            status = await self.outbound.template(lead, "quote_ready")
            return "waiting" if status == SKIPPED else "queued"

    async def run_followup(self, lead_id: int, step: int) -> None:
        async with self._locks[lead_id]:
            lead = self.db.get_lead(lead_id)
            if not self._may_follow_up(lead):
                return
            total = len(config.settings.followup_delays_hours)
            if self._can_send_free_text(lead):
                last = lead["last_outbound_at"] or lead["last_inbound_at"] or time.time()
                instruction = FOLLOWUP_INSTRUCTION.format(
                    step=step, total=total, hours=round((time.time() - last) / 3600), no_reply=NO_REPLY,
                    quote_note=quote_status_note(lead), final_note=FINAL_FOLLOWUP_NOTE if step == total else "",
                )
                note = [{"type": "text", "text": "[No reply from the customer yet.]"}]
                reply = await self._turn(lead, note, instruction)
                if reply:
                    await self.deliver(lead_id, reply, "follow_up")
            else:
                await self.outbound.template(lead, "followup")
            if step == total and lead["marketing_opt_in"]:
                run_at = time.time() + config.settings.reactivation_delay_days * 86400
                self.db.schedule_job("reactivation", run_at, lead_id)

    async def run_template_touch(self, lead_id: int, kind: str) -> None:
        """Post-event review request or reactivation of an opted-in past lead. Re-checked at send time."""
        async with self._locks[lead_id]:
            lead = self.db.get_lead(lead_id)
            if kind == "review_request" and lead["stage"] != "completed":
                return
            if kind == "reactivation" and lead["stage"] in ("awaiting_price", "booked", "confirmed"):
                return
            await self.outbound.template(lead, kind)

    async def send_template(self, lead: dict, kind: str) -> str:
        return await self.outbound.template(lead, kind)

    async def resend(self, lead_id: int, payload: dict) -> None:
        """Retry a reply Claude already wrote (the channel failed the first time)."""
        lead = self.db.get_lead(lead_id)
        if lead["bot_paused"] or lead["do_not_contact"]:
            return
        await self.deliver(lead_id, payload["text"], payload.get("kind", "reply"), payload.get("quote_valid_until"))

    # Team actions from the dashboard

    async def team_reply(self, lead_id: int, text: str, gives_price: bool = False, draft_id: int | None = None) -> str:
        """A person on the team types a message. It is sent even in trial mode, because a human is sending it."""
        async with self._locks[lead_id]:
            lead = self.db.get_lead(lead_id)
            text = text.strip()
            if not text:
                raise TeamActionError("The message was empty.")
            problem = self.team_reply_problem(lead)
            if problem:
                raise TeamActionError(problem)
            valid_until = None
            if gives_price:
                draft = self.db.get_draft(draft_id) if draft_id else None
                if draft and draft["lead_id"] == lead_id and draft["kind"] == "price" and draft["quote_valid_until"]:
                    valid_until = draft["quote_valid_until"]
                else:
                    valid_until = valid_until_from().isoformat()
            try:
                await self.outbound.text(lead, text, "price" if gives_price else "reply", by="team")
            except ChannelError as exc:
                raise TeamActionError(f"Not delivered: {exc}") from exc
            self.db.append_note(lead_id, TEAM_REPLY_NOTE.format(text=text))
            if draft_id:
                self.db.mark_draft_sent(draft_id)
            who = lead.get("name") or f"lead #{lead_id}"
            if gives_price:
                self._mark_quote_sent(lead_id, valid_until)
                self._schedule_followups(lead_id)
                return f"Sent to {who}. Quote valid until {format_date(date.fromisoformat(valid_until))}."
            self._schedule_followups(lead_id)
            return f"Sent to {who}."

    def team_reply_problem(self, lead: dict) -> str:
        """Why the team can't message this lead right now, or "" if they can."""
        if lead["channel"] in ("whatsapp", "instagram"):
            app = "WhatsApp" if lead["channel"] == "whatsapp" else "Instagram"
            if not lead["last_inbound_at"]:
                return f"This person has never written to us on {app}, so {app} doesn't allow a free message."
            if time.time() - lead["last_inbound_at"] >= WHATSAPP_WINDOW_SECONDS:
                hours = round((time.time() - lead["last_inbound_at"]) / 3600)
                return (f"{app} only allows free messages within 24 hours of the customer's last message "
                        f"(they last wrote {hours} hours ago). Call them, or wait until they write again.")
            return ""
        if lead["channel"] == "webchat" and not lead.get("email"):
            return "This website visitor left no email address, so they can't be messaged after the chat."
        return ""

    def pause(self, lead_id: int) -> None:
        self.db.update_lead(lead_id, bot_paused=1)
        self.db.cancel_jobs(lead_id, ("followup",))

    def resume(self, lead_id: int) -> None:
        self.db.update_lead(lead_id, bot_paused=0)
        self.db.append_note(lead_id, RESUME_NOTE)
        self._schedule_followups(lead_id)

    def team_set_stage(self, lead_id: int, stage: str) -> str:
        if stage not in TEAM_STAGES:
            raise TeamActionError(f"Unknown stage {stage}.")
        lead = apply_stage(self.db, lead_id, stage)
        message = f"Stage set to {stage}."
        if stage == "completed":
            if lead["marketing_opt_in"] and not lead["do_not_contact"]:
                message += " A review request will go out in about a day."
            else:
                message += (" No automatic review request: the customer hasn't agreed to receive messages. "
                            "Ask for a review yourself.")
        return message

    # Delivery

    def _can_send_free_text(self, lead: dict) -> bool:
        if lead["channel"] in ("whatsapp", "instagram"):
            return bool(lead["last_inbound_at"]) and time.time() - lead["last_inbound_at"] < WHATSAPP_WINDOW_SECONDS
        return lead["channel"] == "email" or (lead["channel"] == "webchat" and bool(lead.get("email")))

    async def deliver(self, lead_id: int, text: str, kind: str = "reply", quote_valid_until: str | None = None,
                      in_reply_to: str = "") -> str:
        """Send (live) or draft (trial) a message Claude wrote, then record what it means for the lead."""
        lead = self.db.get_lead(lead_id)
        status = await self.outbound.text(lead, text, kind, in_reply_to=in_reply_to,
                                          quote_valid_until=quote_valid_until)
        self._after_send(lead_id, kind, status, quote_valid_until)
        return status

    def _after_send(self, lead_id: int, kind: str, status: str, quote_valid_until: str | None) -> None:
        if kind != "price":
            return
        if status == SENT:
            self._mark_quote_sent(lead_id, quote_valid_until or valid_until_from().isoformat())
        elif status == DRAFTED:
            self.db.update_lead(lead_id, price_to_send=0)

    def _mark_quote_sent(self, lead_id: int, valid_until: str) -> None:
        lead = self.db.get_lead(lead_id)
        updates = {"quote_sent_at": time.time(), "quote_valid_until": valid_until, "price_to_send": 0}
        if lead["stage"] in BEFORE_QUOTED:
            updates["stage"] = "quoted"
        self.db.update_lead(lead_id, **updates)
        self.db.cancel_jobs(lead_id, ("price_reminder",))

    def _price_instruction(self, lead: dict, valid_until: date) -> str:
        return PRICE_READY_INSTRUCTION.format(details=lead["quote_details"], valid_until=format_date(valid_until),
                                              days=config.settings.quote_validity_days)

    # Follow-up scheduling

    def _may_follow_up(self, lead: dict) -> bool:
        if lead["do_not_contact"] or lead["bot_paused"] or lead["stage"] in NO_FOLLOWUP_STAGES:
            return False
        # Instagram commenters who never wrote to us get nothing more than the one private reply.
        return not (lead["channel"] == "instagram" and not lead["last_inbound_at"])

    def _schedule_followups(self, lead_id: int) -> None:
        lead = self.db.get_lead(lead_id)
        self.db.cancel_jobs(lead_id, ("followup",))
        if not self._may_follow_up(lead):
            return
        now = time.time()
        times: list[float | None] = [now + hours * 3600 for hours in config.settings.followup_delays_hours]
        valid = quote_valid_until(lead)
        if valid and len(times) >= 2:
            # Day 1 check-in, then the expiry-day check-in ("valid until today"), then the last one offering a refresh.
            expiry = datetime.combine(valid, dtime(EXPIRY_REMINDER_HOUR), tzinfo=config.settings.timezone).timestamp()
            later = times[2] if len(times) > 2 else float("inf")
            if times[0] < expiry < later:
                times[1] = expiry
            elif expiry <= times[0]:
                times[1] = None  # the first check-in already falls on or after the expiry day
        for step, run_at in enumerate(times, start=1):
            if run_at:
                self.db.schedule_job("followup", run_at, lead_id, {"step": step})

    # Claude loop

    def _context_message(self, lead: dict, extra: str = "") -> tuple[dict, str]:
        """The per-turn system note, and the agent notes it consumed (cleared once the turn succeeds)."""
        now = datetime.now(config.settings.timezone).strftime("%A %d %B %Y, %H:%M")
        known = {k: lead[k] for k in LEAD_CONTEXT_KEYS if lead.get(k) not in (None, "")}
        parts = [f"Channel: {lead['channel']}. Local time (UAE): {now}.",
                 f"Saved lead record: {json.dumps(known, ensure_ascii=False)}"]
        notes = lead.get("agent_notes") or ""
        if notes:
            parts.append(f"Since your last turn: {notes}")
        status = quote_status_note(lead)
        if status:
            parts.append(status)
        if is_trial():
            parts.append(TRIAL_NOTE)
        if extra:
            parts.append(extra)
        return {"role": "system", "content": "\n".join(parts)}, notes

    async def _turn(self, lead: dict, content: list[dict], extra: str = "") -> str | None:
        context, notes = self._context_message(lead, extra)
        reply = await self._run(lead["id"], [{"role": "user", "content": content}, context])
        if notes:
            current = self.db.get_lead(lead["id"])["agent_notes"] or ""
            if current.startswith(notes):
                self.db.update_lead(lead["id"], agent_notes=current[len(notes):].lstrip("\n"))
        return reply

    async def _run(self, lead_id: int, new_entries: list[dict]) -> str | None:
        """Append the new entries, loop through tool calls, and return the final customer-facing text."""
        checkpoint = self.db.last_turn_id(lead_id)
        try:
            for entry in new_entries:
                self.db.append_turn(lead_id, entry["role"], entry["content"])
            for _ in range(MAX_TOOL_ROUNDS):
                response = await self._create(self.db.transcript(lead_id))
                blocks = _strip_declined_partial([b.to_dict() for b in response.content])
                if response.stop_reason == "refusal":
                    raise AgentError(f"model declined: {getattr(response, 'stop_details', None)}")
                self.db.append_turn(lead_id, "assistant", blocks)
                tool_uses = [b for b in blocks if b.get("type") == "tool_use"]
                if response.stop_reason != "tool_use" or not tool_uses:
                    text = "\n".join(b["text"] for b in blocks if b.get("type") == "text").strip()
                    return None if not text or NO_REPLY in text else text
                results = []
                for call in tool_uses:
                    output, is_error = await self.executor.run(lead_id, call["name"], call.get("input") or {})
                    results.append({"type": "tool_result", "tool_use_id": call["id"], "content": output,
                                    "is_error": is_error})
                self.db.append_turn(lead_id, "user", results)
            raise AgentError("too many tool rounds")
        except Exception:
            # Remove this run's tail so the transcript stays valid; the caller retries or alerts.
            self.db.rollback_turns(lead_id, checkpoint)
            raise

    async def _create(self, messages: list[dict]):
        s = config.settings
        return await self.client.beta.messages.create(
            model=s.model,
            max_tokens=16000,
            system=self.system_prompt,
            tools=self.tools,
            messages=messages,
            thinking={"type": "adaptive"},
            output_config={"effort": s.effort},
            cache_control={"type": "ephemeral"},
            betas=[FALLBACK_BETA],
            fallbacks="default",
        )
