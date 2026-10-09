"""Background loop that runs follow-ups, review requests, reactivations, price reminders, retries and the digest."""

import asyncio
import logging
import time
from datetime import datetime, timedelta

from salesbot import config
from salesbot.agent import SalesAgent
from salesbot.db import Database
from salesbot.outbound import is_trial
from salesbot.tools import lead_summary, lead_tag, lead_url, needs_price, price_help, quote_valid_until, today_local

log = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 15 * 60


def next_allowed_time(now: datetime) -> datetime | None:
    """If `now` is inside quiet hours, the next moment sending is allowed; otherwise None."""
    start, end = config.settings.quiet_hours
    if now.hour >= start or now.hour < end:
        target = now.replace(hour=end, minute=0, second=0, microsecond=0)
        return target if now.hour < end else target + timedelta(days=1)
    return None


def next_digest_time(now: datetime) -> datetime:
    target = now.replace(hour=config.settings.digest_hour, minute=0, second=0, microsecond=0)
    return target if target > now else target + timedelta(days=1)


class Scheduler:
    def __init__(self, db: Database, agent: SalesAgent):
        self.db = db
        self.agent = agent

    def ensure_digest_scheduled(self) -> None:
        if not self.db.pending_jobs(kind="daily_digest"):
            now = datetime.now(config.settings.timezone)
            self.db.schedule_job("daily_digest", next_digest_time(now).timestamp())

    async def run_forever(self, interval: float = 60) -> None:
        self.ensure_digest_scheduled()
        while True:
            try:
                await self.tick()
            except Exception:
                log.exception("scheduler tick failed")
            await asyncio.sleep(interval)

    async def tick(self, now: float | None = None) -> None:
        now = now if now is not None else time.time()
        local_now = datetime.fromtimestamp(now, config.settings.timezone)
        for job in self.db.due_jobs(now):
            respects_quiet_hours = job["kind"] in ("followup", "review_request", "reactivation", "price_reminder")
            later = next_allowed_time(local_now) if respects_quiet_hours else None
            if later:
                self.db.reschedule_job(job["id"], later.timestamp())
                continue
            try:
                await self._run(job, local_now)
                self.db.finish_job(job["id"])
            except Exception as exc:
                attempts = job["payload"].get("attempts", 0) + 1
                log.exception("job %s (%s) failed, attempt %s", job["id"], job["kind"], attempts)
                self.db.finish_job(job["id"], "failed")
                if attempts < MAX_ATTEMPTS:
                    self.db.schedule_job(job["kind"], now + RETRY_DELAY_SECONDS, job["lead_id"],
                                         {**job["payload"], "attempts": attempts})
                elif job["lead_id"]:
                    await self.agent.channels.notify_owner(
                        f"{lead_tag(job['lead_id'])} Bot could not complete '{job['kind']}' - please reply yourself",
                        f"Error: {exc}\n{lead_url(job['lead_id'])}",
                    )

    async def _run(self, job: dict, local_now: datetime) -> None:
        kind, lead_id, payload = job["kind"], job["lead_id"], job["payload"]
        if kind == "followup":
            await self.agent.run_followup(lead_id, payload["step"])
        elif kind in ("review_request", "reactivation"):
            await self.agent.run_template_touch(lead_id, kind)
        elif kind == "retry_inbound":
            await self.agent.handle_inbound(lead_id, payload["content"])
        elif kind == "price_reminder":
            still_waiting = await self.remind_price(lead_id)
            repeat = config.settings.price_reminder_repeat_hours
            others = [j for j in self.db.pending_jobs(lead_id, "price_reminder") if j["id"] != job["id"]]
            if still_waiting and repeat > 0 and not others:
                # After the first reminders, keep reminding every day (by default) until the lead is priced.
                self.db.schedule_job("price_reminder", local_now.timestamp() + repeat * 3600, lead_id)
        elif kind == "deliver":
            await self.agent.resend(lead_id, payload)
        elif kind == "daily_digest":
            await self.send_digest(local_now)
            self.db.schedule_job("daily_digest", next_digest_time(local_now + timedelta(minutes=1)).timestamp())
        else:
            raise ValueError(f"unknown job kind {kind}")

    async def remind_price(self, lead_id: int) -> bool:
        """Remind the owner that a customer is waiting for a price. Returns False once nobody is waiting."""
        lead = self.db.get_lead(lead_id)
        if not needs_price(lead):
            return False
        waiting = round((time.time() - (lead["price_requested_at"] or time.time())) / 3600)
        await self.agent.channels.notify_owner(
            f"{lead_tag(lead_id)} Reminder: {lead.get('name') or 'a customer'} has waited {waiting}h for a price",
            f"{price_help(lead_id)}\n\n{lead_summary(lead)}",
        )
        return True

    async def send_digest(self, local_now: datetime) -> None:
        since = local_now.timestamp() - 86400
        today = today_local(local_now.timestamp())
        leads = self.db.list_leads(limit=1000)
        new = [l for l in leads if l["created_at"] >= since]
        active = [l for l in leads if l["updated_at"] >= since]
        by_stage: dict[str, int] = {}
        for lead in leads:
            by_stage[lead["stage"]] = by_stage.get(lead["stage"], 0) + 1
        waiting = [l for l in leads if needs_price(l)]
        undelivered = [l for l in leads if l["price_to_send"]]
        expiring = [l for l in leads if quote_valid_until(l) == today]
        expired = [l for l in leads if (quote_valid_until(l) or today) < today]
        hot = [l for l in active if l["stage"] in ("quoted", "negotiating", "booked")]

        def line(l: dict, extra: str = "") -> str:
            return (f"- #{l['id']} {l.get('name') or 'Unknown'} | {l.get('event_type') or '?'} on "
                    f"{l.get('event_date') or '?'}{extra} | {lead_url(l['id'])}")

        lines = []
        if is_trial():
            pending = sum(self.db.pending_draft_counts().values())
            lines += [f"Trial mode: nothing is sent to customers. {pending} drafts are waiting for your review: "
                      f"{config.settings.public_base_url}/admin/drafts", ""]
        lines += [
            f"Last 24 hours: {len(new)} new leads, {len(active)} active conversations.",
            "Pipeline: " + ", ".join(f"{stage} {count}" for stage, count in sorted(by_stage.items())),
            "",
        ]
        sections = [
            ("Waiting for your price:", waiting, lambda l: ""),
            ("Price entered, waiting for the customer to write back (WhatsApp 24-hour rule):", undelivered,
             lambda l: ""),
            ("Quotes expiring today:", expiring, lambda l: ""),
            ("Quotes expired without a decision (the team re-confirms before booking):", expired,
             lambda l: f" | expired {l['quote_valid_until']}"),
        ]
        for title, items, extra in sections:
            if items:
                lines.append(title)
                lines += [line(l, extra(l)) for l in items]
                lines.append("")
        lines.append("Hot leads:" if hot else "No hot leads today.")
        for lead in hot:
            quote = f"AED {lead['quote_aed']:,}" if lead["quote_aed"] else ("priced" if lead["quote_details"] else "no quote yet")
            lines.append(line(lead, f" | {lead['stage']} | {quote}"))
        await self.agent.channels.notify_owner("Daily sales digest", "\n".join(lines))
