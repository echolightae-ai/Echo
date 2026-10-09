"""Tools the sales agent can call, and their implementations."""

import json
import logging
import time
from datetime import datetime, time as dtime, timedelta

from salesbot import config
from salesbot.channels import Channels
from salesbot.db import Database

log = logging.getLogger(__name__)

STAGES = ["qualifying", "negotiating", "booked", "lost"]  # awaiting_price and quoted are set automatically


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
            "description": "Ask the EchoLight team to price this project (or to answer a price negotiation). "
            "The team replies with the price and you will be told it in a system note.",
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
                        "description": "Only for negotiation: what the customer is asking for (e.g. a lower price)",
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
            "to go ahead, 'lost' when they decline or chose someone else.",
            "strict": True,
            "input_schema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "stage": {"type": "string", "enum": STAGES},
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


def lead_summary(lead: dict) -> str:
    keys = ("name", "channel", "phone", "email", "event_type", "event_date", "venue", "emirate", "guest_count",
            "indoor_outdoor", "services", "budget_aed", "stage", "quote_details", "notes")
    lines = [f"{k}: {lead[k]}" for k in keys if lead.get(k) not in (None, "")]
    lines.append(f"dashboard: {config.settings.public_base_url}/admin/leads/{lead['id']}")
    return "\n".join(lines)


def lead_tag(lead_id: int) -> str:
    """Put in alert subjects; replying to the email with this tag in the subject routes the reply to the lead."""
    return f"[Lead #{lead_id}]"


def price_reply_help(lead_id: int) -> str:
    return (
        "To send the price, reply to this email with the price and what it includes, for example:\n"
        "  AED 28,000 incl. VAT - lighting, 6x3m LED wall, setup and 2 technicians\n"
        f"Or WhatsApp the bot number from your own phone: #{lead_id} AED 28,000 incl. VAT ...\n"
        f"Or use the dashboard: {config.settings.public_base_url}/admin/leads/{lead_id}"
    )


def parse_event_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").replace(tzinfo=config.settings.timezone)
    except ValueError:
        return None


class ToolExecutor:
    def __init__(self, db: Database, channels: Channels):
        self.db = db
        self.channels = channels

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
        # The customer is waiting on us, so no follow-ups; remind the owner instead.
        self.db.cancel_jobs(lead_id, ("followup", "price_reminder"))
        for hours in config.settings.price_reminder_hours:
            self.db.schedule_job("price_reminder", time.time() + hours * 3600, lead_id)
        ask = args.get("customer_request")
        title = "Price negotiation" if ask else "Price needed"
        body = f"{args['requirements']}\n"
        if ask:
            body += f"\nCustomer is asking: {ask}\n"
        await self.channels.notify_owner(
            f"{lead_tag(lead_id)} {title}: {lead.get('name') or 'new lead'}",
            f"{body}\n{price_reply_help(lead_id)}\n\n{lead_summary(lead)}",
        )
        return {"status": "The team has been asked for the price. Tell the customer they are preparing it."}

    async def _book_consultation(self, lead_id: int, args: dict) -> dict:
        booking_id = self.db.add_booking(lead_id, args["kind"], args["preferred_time"], args.get("notes", ""))
        lead = self.db.get_lead(lead_id)
        await self.channels.notify_owner(
            f"New {args['kind'].replace('_', ' ')} booked for {args['preferred_time']}",
            f"{args.get('notes', '')}\n\n{lead_summary(lead)}",
        )
        return {"booking_id": booking_id, "status": "requested; the team has been notified"}

    async def _set_stage(self, lead_id: int, args: dict) -> dict:
        stage = args["stage"]
        lead = self.db.update_lead(lead_id, stage=stage)
        if stage in ("booked", "lost"):
            self.db.cancel_jobs(lead_id, ("followup",))
        if stage == "booked":
            await self.channels.notify_owner(f"Customer ready to book: {lead.get('name') or 'lead'}", lead_summary(lead))
            event_day = parse_event_date(lead.get("event_date"))
            if event_day:
                review_at = datetime.combine(event_day.date(), dtime(11), tzinfo=config.settings.timezone)
                review_at += timedelta(hours=config.settings.review_request_delay_hours)
                self.db.cancel_jobs(lead_id, ("review_request",))
                self.db.schedule_job("review_request", review_at.timestamp(), lead_id)
        if stage == "lost" and lead.get("marketing_opt_in"):
            self.db.cancel_jobs(lead_id, ("reactivation",))
            run_at = datetime.now(config.settings.timezone) + timedelta(days=config.settings.reactivation_delay_days)
            self.db.schedule_job("reactivation", run_at.timestamp(), lead_id)
        return {"stage": stage}

    async def _escalate_to_team(self, lead_id: int, args: dict) -> dict:
        lead = self.db.get_lead(lead_id)
        prefix = "URGENT: " if args["urgency"] == "urgent" else ""
        await self.channels.notify_owner(f"{lead_tag(lead_id)} {prefix}Needs the team: {args['reason'][:80]}", f"{args['reason']}\n\n{lead_summary(lead)}")
        return {"status": "team alerted"}

    async def _set_contact_preferences(self, lead_id: int, args: dict) -> dict:
        updates = {}
        if "marketing_opt_in" in args:
            updates["marketing_opt_in"] = int(args["marketing_opt_in"])
        if "do_not_contact" in args:
            updates["do_not_contact"] = int(args["do_not_contact"])
        self.db.update_lead(lead_id, **updates)
        if updates.get("do_not_contact"):
            self.db.cancel_jobs(lead_id, ("followup", "review_request", "reactivation"))
        if updates.get("marketing_opt_in") == 0:
            self.db.cancel_jobs(lead_id, ("reactivation",))
        return {"saved": updates}

    async def _send_email_summary(self, lead_id: int, args: dict) -> dict:
        lead = self.db.get_lead(lead_id)
        if not lead.get("email"):
            return {"sent": False, "reason": "no email address saved; ask for it first"}
        await self.channels.send_email(lead["email"], args["subject"], args["body"])
        self.db.record_outbound(lead_id, "email", f"{args['subject']}\n\n{args['body']}")
        return {"sent": True, "to": lead["email"]}
