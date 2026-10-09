"""The sales agent: runs Claude over a lead's conversation and delivers replies on the right channel."""

import asyncio
import json
import logging
import time
from collections import defaultdict
from datetime import datetime

import anthropic

from salesbot import config
from salesbot.channels import Channels
from salesbot.db import Database
from salesbot.knowledge import load_business_facts
from salesbot.prompts import (
    COMMENT_INSTRUCTION,
    FINAL_FOLLOWUP_NOTE,
    FOLLOWUP_INSTRUCTION,
    NO_REPLY,
    PRICE_READY_INSTRUCTION,
    build_system_prompt,
)
from salesbot.tools import ToolExecutor, tool_definitions

log = logging.getLogger(__name__)

WHATSAPP_WINDOW_SECONDS = 24 * 3600
MAX_TOOL_ROUNDS = 8
FALLBACK_BETA = "server-side-fallback-2026-07-01"

LEAD_CONTEXT_KEYS = ("name", "phone", "email", "language", "event_type", "event_date", "venue", "emirate",
                     "guest_count", "indoor_outdoor", "services", "budget_aed", "stage", "quote_details",
                     "marketing_opt_in", "source")


class AgentError(Exception):
    pass


class DeliveryError(Exception):
    """Claude wrote the reply but the channel refused it. Resend the text; don't re-run Claude."""

    def __init__(self, text: str):
        super().__init__("reply written but not delivered")
        self.text = text


def _strip_declined_partial(blocks: list[dict]) -> list[dict]:
    """After a mid-output model fallback, drop non-text blocks that came before the last fallback marker."""
    last = max((i for i, b in enumerate(blocks) if b.get("type") == "fallback"), default=None)
    if last is None:
        return blocks
    return [b for b in blocks[:last] if b.get("type") == "text"] + blocks[last:]


class SalesAgent:
    def __init__(self, db: Database, channels: Channels, client: anthropic.AsyncAnthropic | None = None):
        self.db = db
        self.channels = channels
        self.client = client or anthropic.AsyncAnthropic()
        s = config.settings
        self.system_prompt = build_system_prompt(load_business_facts(s.knowledge_dir))
        self.tools = tool_definitions()
        self.executor = ToolExecutor(db, channels)
        self._locks: dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)

    # Public entry points

    async def handle_inbound(self, lead_id: int, content: list[dict], deliver: bool = True) -> str | None:
        """A customer wrote to us. Reply, reset the follow-up sequence, and return the reply text."""
        async with self._locks[lead_id]:
            self.db.update_lead(lead_id, last_inbound_at=time.time())
            self.db.cancel_jobs(lead_id, ("followup", "reactivation"))
            lead = self.db.get_lead(lead_id)
            reply = await self._run(lead_id, [{"role": "user", "content": content}, self._context_message(lead)])
            self._schedule_followups(lead_id)
            if reply and deliver:
                try:
                    await self.deliver(lead_id, reply)
                except Exception as exc:
                    raise DeliveryError(reply) from exc
            elif reply:
                self.db.record_outbound(lead_id, self.db.get_lead(lead_id)["channel"], reply)
            return reply

    async def handle_comment(self, lead_id: int, comment_text: str) -> str | None:
        """Someone commented a keyword on a post or reel. Draft the private DM reply (sent by the caller)."""
        async with self._locks[lead_id]:
            lead = self.db.get_lead(lead_id)
            content = [{"type": "text", "text": f"[Instagram comment] {comment_text}"}]
            context = self._context_message(lead, extra=COMMENT_INSTRUCTION)
            reply = await self._run(lead_id, [{"role": "user", "content": content}, context])
            if reply:
                self.db.record_outbound(lead_id, "instagram", reply)
                self._schedule_followups(lead_id)
            return reply

    async def present_price(self, lead_id: int, details: str, amount_aed: int | None = None) -> str:
        """The owner priced the project. Pass it to the customer now, or as soon as WhatsApp allows.

        Returns "sent" or "queued" (the customer must reply first; they were sent a template nudge).
        """
        async with self._locks[lead_id]:
            lead = self.db.update_lead(lead_id, quote_details=details, quote_aed=amount_aed, stage="quoted")
            self.db.cancel_jobs(lead_id, ("price_reminder",))
            instruction = PRICE_READY_INSTRUCTION.format(details=details)
            if self._can_send_free_text(lead):
                note = {"role": "user", "content": [{"type": "text", "text": "[The team has sent the price.]"}]}
                reply = await self._run(lead_id, [note, self._context_message(lead, extra=instruction)])
                if reply:
                    await self.deliver(lead_id, reply)
                self._schedule_followups(lead_id)
                return "sent"
            # Outside WhatsApp's 24h window: nudge with a template; the price is presented when they reply.
            self.db.update_lead(lead_id, agent_notes="\n".join(filter(None, [lead.get("agent_notes"), instruction])))
            await self.send_template(self.db.get_lead(lead_id), "quote_ready")
            self._schedule_followups(lead_id)
            return "queued"

    async def run_followup(self, lead_id: int, step: int) -> None:
        async with self._locks[lead_id]:
            lead = self.db.get_lead(lead_id)
            if lead["do_not_contact"] or lead["stage"] in ("booked", "lost", "awaiting_price"):
                return
            total = len(config.settings.followup_delays_hours)
            if self._can_send_free_text(lead):
                hours = round((time.time() - (lead["last_outbound_at"] or time.time())) / 3600)
                instruction = FOLLOWUP_INSTRUCTION.format(
                    step=step, total=total, hours=hours, no_reply=NO_REPLY,
                    final_note=FINAL_FOLLOWUP_NOTE if step == total else "",
                )
                note = {"role": "user", "content": [{"type": "text", "text": "[No reply from the customer yet.]"}]}
                reply = await self._run(lead_id, [note, self._context_message(lead, extra=instruction)])
                if reply:
                    await self.deliver(lead_id, reply)
            else:
                await self.send_template(lead, "followup")
            if step == total and lead["marketing_opt_in"]:
                run_at = time.time() + config.settings.reactivation_delay_days * 86400
                self.db.schedule_job("reactivation", run_at, lead_id)

    async def run_template_touch(self, lead_id: int, kind: str) -> None:
        """Post-event review request or reactivation of an opted-in past lead."""
        async with self._locks[lead_id]:
            lead = self.db.get_lead(lead_id)
            if lead["do_not_contact"] or (kind == "reactivation" and not lead["marketing_opt_in"]):
                return
            await self.send_template(lead, kind)

    # Delivery

    def _can_send_free_text(self, lead: dict) -> bool:
        if lead["channel"] in ("whatsapp", "instagram"):
            return bool(lead["last_inbound_at"]) and time.time() - lead["last_inbound_at"] < WHATSAPP_WINDOW_SECONDS
        return lead["channel"] == "email" or (lead["channel"] == "webchat" and bool(lead.get("email")))

    async def deliver(self, lead_id: int, text: str) -> None:
        lead = self.db.get_lead(lead_id)
        channel = lead["channel"]
        if channel == "whatsapp":
            await self.channels.whatsapp_text(lead["channel_user_id"], text)
        elif channel == "instagram":
            await self.channels.instagram_text(lead["channel_user_id"], text)
        elif channel == "email":
            await self.channels.send_email(lead["channel_user_id"], self._email_subject(lead), text)
        elif channel == "webchat" and lead.get("email"):
            # Live chat replies return in the HTTP response; this path is follow-ups, sent to the visitor's email.
            await self.channels.send_email(lead["email"], self._email_subject(lead), text)
            channel = "email"
        self.db.record_outbound(lead_id, channel, text)

    async def send_template(self, lead: dict, kind: str) -> None:
        """Outside the 24h window WhatsApp only allows pre-approved templates."""
        s = config.settings
        template = {
            "followup": s.wa_template_followup,
            "review_request": s.wa_template_review,
            "reactivation": s.wa_template_reactivation,
            "missed_call": s.wa_template_missed_call,
            "quote_ready": s.wa_template_quote_ready,
        }[kind]
        first_name = (lead.get("name") or "").split(" ")[0] or "there"
        phone = lead["channel_user_id"] if lead["channel"] == "whatsapp" else lead.get("phone")
        if phone and template:
            await self.channels.whatsapp_template("".join(ch for ch in phone if ch.isdigit()), template, [first_name])
            sent = f"[WhatsApp template '{template}' sent: {kind.replace('_', ' ')}]"
            self.db.record_outbound(lead["id"], "whatsapp", sent)
        elif lead.get("email") or lead["channel"] == "email":
            await self._email_touch(lead, kind)
            return
        else:
            log.info("no channel for %s to lead %s", kind, lead["id"])
            return
        notes = "\n".join(filter(None, [lead.get("agent_notes"), sent]))
        self.db.update_lead(lead["id"], agent_notes=notes)

    async def _email_touch(self, lead: dict, kind: str) -> None:
        to = lead.get("email") or lead["channel_user_id"]
        name = (lead.get("name") or "").split(" ")[0] or "there"
        bodies = {
            "followup": f"Hi {name},\n\nJust checking in on your event plans. Happy to answer any questions or send "
            "a detailed proposal whenever you're ready. Simply reply to this email.\n\nEchoLight team\n+971 56 722 0533",
            "review_request": f"Hi {name},\n\nThank you for choosing EchoLight. We hope the event was everything you "
            "wanted. If you have a minute, a Google review helps us a lot, and if you know anyone planning an event, "
            "we'd love an introduction.\n\nEchoLight team",
            "reactivation": f"Hi {name},\n\nPlanning another event? We'd be glad to help with lighting, LED screens, "
            "lasers or sound. Reply to this email and we'll take it from there. (Reply STOP to unsubscribe.)\n\n"
            "EchoLight team",
            "missed_call": f"Hi {name},\n\nSorry we missed your call. How can we help with your event?\n\nEchoLight team",
            "quote_ready": f"Hi {name},\n\nYour EchoLight quote is ready. Reply to this email and we'll share it "
            "with all the details.\n\nEchoLight team",
        }
        subject = "EchoLight" if kind != "review_request" else "Thank you from EchoLight"
        await self.channels.send_email(to, subject, bodies[kind])
        self.db.record_outbound(lead["id"], "email", bodies[kind])
        notes = "\n".join(filter(None, [lead.get("agent_notes"), f"[Automated email sent: {kind.replace('_', ' ')}]"]))
        self.db.update_lead(lead["id"], agent_notes=notes)

    @staticmethod
    def _email_subject(lead: dict) -> str:
        return f"EchoLight - your {lead['event_type']}" if lead.get("event_type") else "EchoLight - your event"

    # Follow-up scheduling

    def _schedule_followups(self, lead_id: int) -> None:
        lead = self.db.get_lead(lead_id)
        if lead["do_not_contact"] or lead["stage"] in ("booked", "lost", "awaiting_price"):
            return
        self.db.cancel_jobs(lead_id, ("followup",))
        now = time.time()
        for step, hours in enumerate(config.settings.followup_delays_hours, start=1):
            self.db.schedule_job("followup", now + hours * 3600, lead_id, {"step": step})

    # Claude loop

    def _context_message(self, lead: dict, extra: str = "") -> dict:
        now = datetime.now(config.settings.timezone).strftime("%A %d %B %Y, %H:%M")
        known = {k: lead[k] for k in LEAD_CONTEXT_KEYS if lead.get(k) not in (None, "")}
        parts = [f"Channel: {lead['channel']}. Local time (UAE): {now}.",
                 f"Saved lead record: {json.dumps(known, ensure_ascii=False)}"]
        if lead.get("agent_notes"):
            parts.append(f"Since your last turn: {lead['agent_notes']}")
            self.db.update_lead(lead["id"], agent_notes="")
        if extra:
            parts.append(extra)
        return {"role": "system", "content": "\n".join(parts)}

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
