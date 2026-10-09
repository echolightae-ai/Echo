"""Background loop that runs follow-ups, review requests, reactivations, retries and the daily digest."""

import asyncio
import logging
import time
from datetime import datetime, timedelta

from salesbot import config
from salesbot.agent import SalesAgent
from salesbot.db import Database
from salesbot.tools import lead_summary, lead_tag, price_reply_help

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
                        f"Bot could not complete '{job['kind']}' - please reply manually",
                        f"Error: {exc}\n{config.settings.public_base_url}/admin/leads/{job['lead_id']}",
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
            await self.remind_price(lead_id)
        elif kind == "deliver":
            await self.agent.deliver(lead_id, payload["text"])
        elif kind == "daily_digest":
            await self.send_digest(local_now)
            self.db.schedule_job("daily_digest", next_digest_time(local_now + timedelta(minutes=1)).timestamp())
        else:
            raise ValueError(f"unknown job kind {kind}")

    async def remind_price(self, lead_id: int) -> None:
        lead = self.db.get_lead(lead_id)
        if lead["stage"] != "awaiting_price":
            return
        waiting = round((time.time() - (lead["price_requested_at"] or time.time())) / 3600)
        await self.agent.channels.notify_owner(
            f"{lead_tag(lead_id)} Reminder: {lead.get('name') or 'a customer'} has waited {waiting}h for a price",
            f"{price_reply_help(lead_id)}\n\n{lead_summary(lead)}",
        )

    async def send_digest(self, local_now: datetime) -> None:
        since = local_now.timestamp() - 86400
        leads = self.db.list_leads(limit=1000)
        new = [l for l in leads if l["created_at"] >= since]
        active = [l for l in leads if l["updated_at"] >= since]
        by_stage: dict[str, int] = {}
        for lead in leads:
            by_stage[lead["stage"]] = by_stage.get(lead["stage"], 0) + 1
        waiting = [l for l in leads if l["stage"] == "awaiting_price"]
        hot = [l for l in active if l["stage"] in ("quoted", "negotiating", "booked")]
        lines = [
            f"Last 24 hours: {len(new)} new leads, {len(active)} active conversations.",
            "Pipeline: " + ", ".join(f"{stage} {count}" for stage, count in sorted(by_stage.items())),
            "",
        ]
        if waiting:
            lines.append("Waiting for your price:")
            lines += [f"- #{l['id']} {l.get('name') or 'Unknown'} | {l.get('event_type') or '?'} on "
                      f"{l.get('event_date') or '?'} | {config.settings.public_base_url}/admin/leads/{l['id']}"
                      for l in waiting]
            lines.append("")
        lines.append("Hot leads:" if hot else "No hot leads today.")
        for lead in hot:
            quote = f"AED {lead['quote_aed']:,}" if lead["quote_aed"] else ("priced" if lead["quote_details"] else "no quote yet")
            lines.append(f"- {lead.get('name') or 'Unknown'} | {lead.get('event_type') or '?'} on "
                         f"{lead.get('event_date') or '?'} | {lead['stage']} | {quote} | "
                         f"{config.settings.public_base_url}/admin/leads/{lead['id']}")
        await self.agent.channels.notify_owner("Daily sales digest", "\n".join(lines))
