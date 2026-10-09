"""Tools the sales agent can call, and their implementations."""

import json
import logging
from datetime import datetime, time as dtime, timedelta

from salesbot import config
from salesbot.channels import Channels
from salesbot.db import Database
from salesbot.knowledge import PriceList

log = logging.getLogger(__name__)

STAGES = ["qualifying", "quoted", "negotiating", "booked", "lost"]


def tool_definitions(service_ids: list[str]) -> list[dict]:
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
            "name": "estimate_quote",
            "description": "Compute the indicative price range from EchoLight's price list. "
            "Always use this before mentioning any price.",
            "strict": True,
            "input_schema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "service_id": {"type": "string", "enum": service_ids},
                                "quantity": {"type": "number", "description": "Units as defined in the price list"},
                                "days": {"type": "number", "description": "Event days, usually 1"},
                            },
                            "required": ["service_id", "quantity", "days"],
                        },
                    }
                },
                "required": ["items"],
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
            "description": "Email the customer a written summary or proposal (services, indicative price, next "
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
            "indoor_outdoor", "services", "budget_aed", "stage", "quote_min_aed", "quote_max_aed", "notes")
    lines = [f"{k}: {lead[k]}" for k in keys if lead.get(k) not in (None, "")]
    lines.append(f"dashboard: {config.settings.public_base_url}/admin/leads/{lead['id']}")
    return "\n".join(lines)


def parse_event_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").replace(tzinfo=config.settings.timezone)
    except ValueError:
        return None


class ToolExecutor:
    def __init__(self, db: Database, channels: Channels, prices: PriceList):
        self.db = db
        self.channels = channels
        self.prices = prices

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

    async def _estimate_quote(self, lead_id: int, args: dict) -> dict:
        estimate = self.prices.estimate(args["items"])
        if estimate["lines"]:
            lead = self.db.update_lead(
                lead_id,
                quote_min_aed=estimate["total_min_incl_vat_aed"],
                quote_max_aed=estimate["total_max_incl_vat_aed"],
                stage="quoted",
            )
            await self.channels.notify_owner(
                f"Quote sent: AED {estimate['total_min_incl_vat_aed']:,}-{estimate['total_max_incl_vat_aed']:,}",
                lead_summary(lead),
            )
        return estimate

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
        await self.channels.notify_owner(f"{prefix}Needs the team: {args['reason'][:80]}", f"{args['reason']}\n\n{lead_summary(lead)}")
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
