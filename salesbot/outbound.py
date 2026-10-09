"""The one gate every message to a customer passes through.

In trial mode (TRIAL_MODE=true, the default) nothing the bot writes is sent: each message becomes a draft the owner
reviews in /admin. Messages the team types themselves ("Reply as team") are always sent, because a person is sending
them. Owner alerts do not pass through here; they always go to the owner.
"""

import logging
from collections.abc import Awaitable, Callable

from salesbot import config
from salesbot.channels import ChannelError, Channels
from salesbot.db import Database
from salesbot.templates import MARKETING_KINDS, WHATSAPP_TEMPLATES, first_name, render_email, render_whatsapp

log = logging.getLogger(__name__)

SENT, DRAFTED, SKIPPED = "sent", "drafted", "skipped"


def is_trial() -> bool:
    return config.settings.trial_mode


def email_subject(lead: dict) -> str:
    return f"EchoLight - your {lead['event_type']}" if lead.get("event_type") else "EchoLight - your event"


def template_language(lead: dict) -> str:
    """Arabic leads get the Arabic template; everyone else gets WA_TEMPLATE_DEFAULT_LANGUAGE."""
    if (lead.get("language") or "").lower() == "ar":
        return "ar"
    return config.settings.wa_template_default_language or "ar"


class Outbound:
    def __init__(self, db: Database, channels: Channels):
        self.db = db
        self.channels = channels

    async def _gate(self, lead: dict, channel: str, kind: str, text: str, send: Callable[[], Awaitable] | None,
                    *, by: str = "bot", in_reply_to: str = "", quote_valid_until: str | None = None) -> str:
        if by == "bot" and is_trial():
            self.db.add_draft(lead["id"], channel, kind, text, in_reply_to, quote_valid_until)
            return DRAFTED
        if send is not None:
            await send()
        self.db.record_outbound(lead["id"], channel, text, sender=by, kind=kind)
        return SENT

    async def text(self, lead: dict, text: str, kind: str = "reply", *, by: str = "bot", in_reply_to: str = "",
                   quote_valid_until: str | None = None) -> str:
        """A free-form message on the lead's own channel (the caller checks the 24-hour rule)."""
        channel, to = lead["channel"], lead["channel_user_id"]
        if channel == "whatsapp":
            send = lambda: self.channels.whatsapp_text(to, text)  # noqa: E731
        elif channel == "instagram":
            send = lambda: self.channels.instagram_text(to, text)  # noqa: E731
        elif channel == "email":
            send = lambda: self.channels.send_email(to, email_subject(lead), text)  # noqa: E731
        elif channel == "webchat" and lead.get("email"):
            # Live chat replies travel in the HTTP response; later messages go to the visitor's email.
            channel = "email"
            send = lambda: self.channels.send_email(lead["email"], email_subject(lead), text)  # noqa: E731
        else:
            raise ChannelError(f"no way to message this {channel} lead")
        return await self._gate(lead, channel, kind, text, send, by=by, in_reply_to=in_reply_to,
                                quote_valid_until=quote_valid_until)

    async def chat_reply(self, lead: dict, text: str, kind: str = "reply", *, in_reply_to: str = "",
                         quote_valid_until: str | None = None) -> str:
        """A website chat reply. Live, the caller returns it in the HTTP response; in trial it is only a draft."""
        return await self._gate(lead, "webchat", kind, text, None, in_reply_to=in_reply_to,
                                quote_valid_until=quote_valid_until)

    async def comment_reply(self, lead: dict, comment_id: str, text: str, comment_text: str) -> str:
        """Instagram's one private DM to someone who commented on a post or reel."""
        send = lambda: self.channels.instagram_private_reply(comment_id, text)  # noqa: E731
        return await self._gate(lead, "instagram", "comment_reply", text, send, in_reply_to=comment_text)

    async def email(self, lead: dict, to: str, subject: str, body: str, kind: str) -> str:
        send = lambda: self.channels.send_email(to, subject, body)  # noqa: E731
        return await self._gate(lead, "email", kind, f"Subject: {subject}\n\n{body}", send)

    async def template(self, lead: dict, kind: str) -> str:
        """A pre-approved WhatsApp template (outside the 24-hour window), or the email version.

        Never moves someone onto a channel they didn't use with us: WhatsApp templates go only to people who
        messaged or called our WhatsApp number. Instagram allows nothing after its window, so Instagram leads get
        only email, and only if they gave us an address.
        """
        if lead.get("bot_paused") or lead.get("do_not_contact"):
            return SKIPPED
        if kind in MARKETING_KINDS and not lead.get("marketing_opt_in"):
            log.info("no %s for lead %s: no marketing opt-in", kind, lead["id"])
            return SKIPPED
        template = getattr(config.settings, WHATSAPP_TEMPLATES[kind]["setting"])
        if lead["channel"] == "whatsapp" and template:
            language = template_language(lead)
            name = first_name(lead, language)
            to = "".join(ch for ch in lead["channel_user_id"] if ch.isdigit())
            preview = f"[WhatsApp template '{template}' ({language})]\n{render_whatsapp(kind, language, name)}"
            status = await self._gate(
                lead, "whatsapp", kind, preview,
                lambda: self.channels.whatsapp_template(to, template, [name], language),
            )
            if status == SENT:
                self.db.append_note(lead["id"], f"[WhatsApp template '{template}' sent: {kind.replace('_', ' ')}]")
            return status
        if lead.get("email") or lead["channel"] == "email":
            to = lead.get("email") or lead["channel_user_id"]
            subject, body = render_email(kind, lead)
            status = await self.email(lead, to, subject, body, kind)
            if status == SENT:
                self.db.append_note(lead["id"], f"[Automated email sent: {kind.replace('_', ' ')}]")
            return status
        log.info("no channel for %s to lead %s", kind, lead["id"])
        return SKIPPED
