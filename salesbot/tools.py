"""Tools the sales agent can call, their implementations, and the pipeline/quote rules they share with the dashboard."""

import json
import logging
import time
from datetime import date, datetime, timedelta

from salesbot import config
from salesbot.channels import Channels
from salesbot.db import STAGES, Database
from salesbot.outbound import DRAFTED, Outbound

log = logging.getLogger(__name__)

AGENT_STAGES = ["qualifying", "negotiating", "booked", "lost"]  # awaiting_price and quoted are set automatically
TEAM_STAGES = {  # buttons on the dashboard
    "confirmed": "Deposit received",
    "completed": "Event done / balance received",
    "lost": "Mark as lost",
}
NO_FOLLOWUP_STAGES = ("awaiting_price", "booked", "confirmed", "completed", "lost")
OPEN_QUOTE_STAGES = ("quoted", "negotiating")
BEFORE_QUOTED = ("new", "qualifying", "awaiting_price")


def tool_definitions() -> list[dict]:
    return [
        {
            "name": "save_lead_details",
            "description": "Save details about the customer and their event as soon as you learn them. "
            "Only include fields you learned; omitted fields keep their saved value.",
            "strict": True,
            "input_schema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "name": {"type": "string"},
                    "email": {"type": "string"},
                    "phone": {"type": "string", "description": "International format, e.g. +9715..."},
                    "language": {"type": "string", "enum": ["ar", "en", "other"]},
                    "event_type": {"type": "string", "description": "e.g. wedding, gala dinner, conference, car launch"},
                    "event_date": {"type": "string", "description": "YYYY-MM-DD if known, otherwise as stated"},
                    "venue": {"type": "string"},
                    "emirate": {"type": "string"},
                    "guest_count": {"type": "integer"},
                    "indoor_outdoor": {"type": "string", "enum": ["indoor", "outdoor", "both"]},
                    "services": {"type": "array", "items": {"type": "string"}},
                    "budget_aed": {"type": "integer"},
                    "notes": {"type": "string", "description": "Anything else relevant, appended to earlier notes"},
                },
                "required": [],
            },
        },
        {
            "name": "request_price",
            "description": "Ask the EchoLight team to price this project, to answer a price negotiation, or to "
            "re-confirm an expired quote. The team replies with the price and you will be told it in a system note.",
            "strict": True,
            "input_schema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "requirements": {
                        "type": "string",
                        "description": "Everything the team needs to price it: event, date, venue, guests, indoor/"
                        "outdoor, services and quantities wanted, special requests, budget if mentioned",
                    },
                    "customer_request": {
                        "type": "string",
                        "description": "Only for negotiation or an expired quote: what the customer is asking for "
                        "(e.g. a lower price, or to re-confirm the expired quote)",
                    },
                },
                "required": ["requirements"],
            },
        },
        {
            "name": "book_consultation",
            "description": "Book a call, site visit or meeting once the customer agrees on a time.",
            "strict": True,
            "input_schema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "kind": {"type": "string", "enum": ["call", "site_visit", "meeting"]},
                    "preferred_time": {"type": "string", "description": "Date and time as agreed, local UAE time"},
                    "notes": {"type": "string"},
                },
                "required": ["kind", "preferred_time", "notes"],
            },
        },
        {
            "name": "set_stage",
            "description": "Move the lead through the pipeline. Use 'booked' when the customer confirms they want "
            "to go ahead with a valid quote, 'lost' when they decline or chose someone else.",
            "strict": True,
            "input_schema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "stage": {"type": "string", "enum": AGENT_STAGES},
                    "reason": {"type": "string"},
                },
                "required": ["stage", "reason"],
            },
        },
        {
            "name": "escalate_to_team",
            "description": "Alert the EchoLight team about something you cannot settle alone. "
            "The conversation continues; tell the customer the team will confirm.",
            "strict": True,
            "input_schema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "reason": {"type": "string"},
                    "urgency": {"type": "string", "enum": ["normal", "urgent"]},
                },
                "required": ["reason", "urgency"],
            },
        },
        {
            "name": "set_contact_preferences",
            "description": "Record the customer's consent to updates and offers, or their request to stop messages.",
            "strict": True,
            "input_schema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "marketing_opt_in": {"type": "boolean"},
                    "do_not_contact": {"type": "boolean"},
                },
                "required": [],
            },
        },
        {
            "name": "send_email_summary",
            "description": "Email the customer a written summary or proposal (services, the team's price if given, next "
            "steps). Only when they have given an email address and asked for details by email.",
            "strict": True,
            "input_schema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "subject": {"type": "string"},
                    "body": {"type": "string", "description": "Plain text email body, signed 'EchoLight team'"},
                },
                "required": ["subject", "body"],
            },
        },
    ]


# Dates and quote validity (all in UAE time)


def today_local(now: float | None = None) -> date:
    return datetime.fromtimestamp(now if now is not None else time.time(), config.settings.timezone).date()


def valid_until_from(now: float | None = None) -> date:
    return today_local(now) + timedelta(days=config.settings.quote_validity_days)


def format_date(day: date) -> str:
    return day.strftime("%A %d %B %Y")


def parse_event_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").replace(tzinfo=config.settings.timezone)
    except ValueError:
        return None


def quote_valid_until(lead: dict) -> date | None:
    """The validity date of a quote the customer received and hasn't decided on yet."""
    if not lead.get("quote_sent_at") or not lead.get("quote_valid_until") or lead["stage"] not in OPEN_QUOTE_STAGES:
        return None
    try:
        return date.fromisoformat(lead["quote_valid_until"])
    except ValueError:
        return None


def quote_expired(lead: dict, now: float | None = None) -> bool:
    valid = quote_valid_until(lead)
    return bool(valid and valid < today_local(now))


def quote_status_note(lead: dict, now: float | None = None) -> str:
    """What the agent must know about the customer's quote right now."""
    valid = quote_valid_until(lead)
    if not valid:
        return ""
    today = today_local(now)
    if valid > today:
        return f"Their quote is valid until {format_date(valid)}."
    if valid == today:
        return (f"Their quote is valid until today ({format_date(valid)}). Remind them kindly and ask whether they "
                "would like to lock the date.")
    return (f"Their quote expired on {format_date(valid)}. Do not present the old price as valid. Offer to have the "
            "team refresh the quote (re-confirm the price and the date's availability); if they want that, call "
            "request_price.")


def needs_price(lead: dict) -> bool:
    """The bot asked for a price and none has been entered since."""
    return (lead["stage"] == "awaiting_price" and not lead.get("do_not_contact")
            and (not lead.get("priced_at") or (lead.get("price_requested_at") or 0) > lead["priced_at"]))


def lead_summary(lead: dict) -> str:
    keys = ("name", "channel", "phone", "email", "event_type", "event_date", "venue", "emirate", "guest_count",
            "indoor_outdoor", "services", "budget_aed", "stage", "quote_details", "quote_valid_until", "notes")
    lines = [f"{k}: {lead[k]}" for k in keys if lead.get(k) not in (None, "")]
    lines.append(f"dashboard: {lead_url(lead['id'])}")
    return "\n".join(lines)


def lead_url(lead_id: int) -> str:
    return f"{config.settings.public_base_url}/admin/leads/{lead_id}"


def lead_tag(lead_id: int) -> str:
    """Put in alert subjects so the owner can find the lead quickly."""
    return f"[Lead #{lead_id}]"


def price_help(lead_id: int) -> str:
    return (
        "Enter the price on the dashboard: the amount in AED excluding VAT, and the exact wording for the customer, "
        "for example\n  AED 28,000 excl. VAT (+5% VAT) - lighting, 6x3m LED wall, setup and 2 technicians\n"
        f"{lead_url(lead_id)}\n"
        "Prices are only taken from the dashboard. Replies to this email are not read."
    )


def apply_stage(db: Database, lead_id: int, stage: str) -> dict:
    """Move a lead and cancel or schedule what depends on the stage. Returns the updated lead."""
    if stage not in STAGES:
        raise ValueError(f"unknown stage {stage}")
    lead = db.update_lead(lead_id, stage=stage)
    if stage in NO_FOLLOWUP_STAGES:
        db.cancel_jobs(lead_id, ("followup",))
    if stage == "lost":
        db.cancel_jobs(lead_id, ("review_request", "price_reminder", "reactivation"))
        if lead.get("marketing_opt_in") and not lead.get("do_not_contact"):
            run_at = time.time() + config.settings.reactivation_delay_days * 86400
            db.schedule_job("reactivation", run_at, lead_id)
    if stage == "completed":
        db.cancel_jobs(lead_id, ("review_request", "price_reminder"))
        # Review requests are marketing: only for customers who agreed to receive messages.
        if lead.get("marketing_opt_in") and not lead.get("do_not_contact"):
            db.schedule_job("review_request", time.time() + config.settings.review_request_delay_hours * 3600, lead_id)
    return lead


class ToolExecutor:
    def __init__(self, db: Database, channels: Channels, outbound: Outbound):
        self.db = db
        self.channels = channels
        self.outbound = outbound

    async def run(self, lead_id: int, name: str, args: dict) -> tuple[str, bool]:
        """Execute one tool call. Returns (result text, is_error)."""
        handler = getattr(self, f"_{name}", None)
        if handler is None:
            return f"Unknown tool {name}", True
        try:
            return json.dumps(await handler(lead_id, args), ensure_ascii=False), False
        except Exception as exc:  # the agent sees the error and can recover
            log.exception("tool %s failed", name)
            return f"{type(exc).__name__}: {exc}", True

    async def _save_lead_details(self, lead_id: int, args: dict) -> dict:
        lead = self.db.get_lead(lead_id)
        fields = dict(args)
        if "services" in fields:
            fields["services"] = ", ".join(fields["services"])
        if fields.get("notes") and lead.get("notes"):
            fields["notes"] = f"{lead['notes']}\n{fields['notes']}"
        if lead["stage"] == "new":
            fields["stage"] = "qualifying"
        self.db.update_lead(lead_id, **fields)
        return {"saved": sorted(args)}

    async def _request_price(self, lead_id: int, args: dict) -> dict:
        lead = self.db.update_lead(lead_id, stage="awaiting_price", price_requested_at=time.time())
        # The customer is waiting on us, so no follow-ups; remind the owner instead (3h, 24h, then daily).
        self.db.cancel_jobs(lead_id, ("followup", "price_reminder"))
        for hours in config.settings.price_reminder_hours:
            self.db.schedule_job("price_reminder", time.time() + hours * 3600, lead_id)
        ask = args.get("customer_request")
        title = "Price negotiation" if ask else "Price needed"
        body = f"{args['requirements']}\n"
        if ask:
            body += f"\nCustomer is asking: {ask}\n"
        if lead.get("event_date"):
            clashes = self.db.leads_on_date(lead["event_date"], lead_id)
            if clashes:
                names = ", ".join(f"#{c['id']} {c.get('name') or 'unnamed'} ({c['stage']})" for c in clashes)
                body += f"\nSame date as: {names}. Check crew and equipment before pricing.\n"
        await self.channels.notify_owner(
            f"{lead_tag(lead_id)} {title}: {lead.get('name') or 'new lead'}",
            f"{body}\n{price_help(lead_id)}\n\n{lead_summary(lead)}",
        )
        return {"status": "The team has been asked for the price. Tell the customer they are preparing it."}

    async def _book_consultation(self, lead_id: int, args: dict) -> dict:
        booking_id = self.db.add_booking(lead_id, args["kind"], args["preferred_time"], args.get("notes", ""))
        lead = self.db.get_lead(lead_id)
        await self.channels.notify_owner(
            f"{lead_tag(lead_id)} New {args['kind'].replace('_', ' ')} booked for {args['preferred_time']}",
            f"{args.get('notes', '')}\n\n{lead_summary(lead)}",
        )
        return {"booking_id": booking_id, "status": "requested; the team has been notified"}

    async def _set_stage(self, lead_id: int, args: dict) -> dict:
        stage = args["stage"]
        if stage not in AGENT_STAGES:
            raise ValueError(f"stage must be one of {AGENT_STAGES}")
        lead = self.db.get_lead(lead_id)
        if stage == "booked" and quote_expired(lead):
            raise ValueError(
                f"The quote expired on {lead['quote_valid_until']}. Do not book on the old price: call request_price "
                "so the team re-confirms the price and the date, and tell the customer you are checking."
            )
        lead = apply_stage(self.db, lead_id, stage)
        if stage == "booked":
            await self.channels.notify_owner(
                f"{lead_tag(lead_id)} Customer ready to book: {lead.get('name') or 'lead'}",
                f"Send the final proposal and the deposit details.\n\n{lead_summary(lead)}",
            )
        return {"stage": stage}

    async def _escalate_to_team(self, lead_id: int, args: dict) -> dict:
        lead = self.db.get_lead(lead_id)
        prefix = "URGENT: " if args["urgency"] == "urgent" else ""
        await self.channels.notify_owner(f"{lead_tag(lead_id)} {prefix}Needs the team: {args['reason'][:80]}",
                                         f"{args['reason']}\n\n{lead_summary(lead)}")
        return {"status": "team alerted"}

    async def _set_contact_preferences(self, lead_id: int, args: dict) -> dict:
        updates = {}
        if "marketing_opt_in" in args:
            updates["marketing_opt_in"] = int(args["marketing_opt_in"])
        if "do_not_contact" in args:
            updates["do_not_contact"] = int(args["do_not_contact"])
        self.db.update_lead(lead_id, **updates)
        if updates.get("do_not_contact"):
            self.db.cancel_jobs(lead_id, ("followup", "review_request", "reactivation", "price_reminder"))
        if updates.get("marketing_opt_in") == 0:
            self.db.cancel_jobs(lead_id, ("review_request", "reactivation"))
        return {"saved": updates}

    async def _send_email_summary(self, lead_id: int, args: dict) -> dict:
        lead = self.db.get_lead(lead_id)
        if not lead.get("email"):
            return {"sent": False, "reason": "no email address saved; ask for it first"}
        status = await self.outbound.email(lead, lead["email"], args["subject"], args["body"], "email_summary")
        if status == DRAFTED:
            return {"sent": False, "drafted": True, "to": lead["email"],
                    "note": "Trial mode: saved as a draft for the team, not sent."}
        return {"sent": True, "to": lead["email"]}
