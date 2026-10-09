"""Outbound calls to WhatsApp, Instagram, email and owner notifications."""

import asyncio
import logging
import smtplib
from email.message import EmailMessage

import httpx

from salesbot import config

log = logging.getLogger(__name__)


class ChannelError(Exception):
    pass


class Channels:
    """Thin wrappers over each platform's send API. Swapped for a fake in tests."""

    def __init__(self, http: httpx.AsyncClient | None = None):
        self.http = http or httpx.AsyncClient(timeout=20)

    def _graph(self, path: str) -> str:
        return f"https://graph.facebook.com/{config.settings.meta_graph_version}/{path}"

    async def _post_graph(self, path: str, token: str, body: dict) -> dict:
        response = await self.http.post(self._graph(path), json=body, headers={"Authorization": f"Bearer {token}"})
        if response.status_code >= 400:
            raise ChannelError(f"Graph API {path} failed: {response.status_code} {response.text[:300]}")
        return response.json()

    # WhatsApp Cloud API

    async def whatsapp_text(self, to: str, text: str) -> None:
        s = config.settings
        await self._post_graph(
            f"{s.whatsapp_phone_number_id}/messages",
            s.whatsapp_token,
            {"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": text[:4096]}},
        )

    async def whatsapp_template(self, to: str, template: str, params: list[str]) -> None:
        s = config.settings
        await self._post_graph(
            f"{s.whatsapp_phone_number_id}/messages",
            s.whatsapp_token,
            {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "template",
                "template": {
                    "name": template,
                    "language": {"code": s.wa_template_language},
                    "components": [
                        {"type": "body", "parameters": [{"type": "text", "text": p} for p in params]}
                    ],
                },
            },
        )

    async def whatsapp_media(self, media_id: str) -> tuple[bytes, str]:
        """Download an image a customer sent. Returns (bytes, mime type)."""
        s = config.settings
        headers = {"Authorization": f"Bearer {s.whatsapp_token}"}
        meta = await self.http.get(self._graph(media_id), headers=headers)
        meta.raise_for_status()
        info = meta.json()
        media = await self.http.get(info["url"], headers=headers)
        media.raise_for_status()
        return media.content, info.get("mime_type", "image/jpeg")

    # Instagram messaging

    async def instagram_text(self, user_id: str, text: str) -> None:
        s = config.settings
        await self._post_graph(
            f"{s.instagram_account_id}/messages",
            s.instagram_token,
            {"recipient": {"id": user_id}, "message": {"text": text[:1000]}},
        )

    async def instagram_private_reply(self, comment_id: str, text: str) -> None:
        """DM someone who commented on a post or reel (Instagram 'private replies')."""
        s = config.settings
        await self._post_graph(
            f"{s.instagram_account_id}/messages",
            s.instagram_token,
            {"recipient": {"comment_id": comment_id}, "message": {"text": text[:1000]}},
        )

    # Email (SMTP)

    async def send_email(self, to: str, subject: str, body: str) -> None:
        s = config.settings
        if not s.smtp_host:
            raise ChannelError("SMTP is not configured")
        message = EmailMessage()
        message["From"] = s.email_from or s.smtp_user
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)

        def _send() -> None:
            with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=30) as smtp:
                smtp.starttls()
                if s.smtp_user:
                    smtp.login(s.smtp_user, s.smtp_password)
                smtp.send_message(message)

        await asyncio.to_thread(_send)

    # Owner alerts: email first, WhatsApp as a best-effort extra

    async def notify_owner(self, subject: str, text: str) -> None:
        s = config.settings
        if s.owner_email and s.smtp_host:
            try:
                await self.send_email(s.owner_email, f"[EchoLight sales bot] {subject}", text)
            except Exception:
                log.exception("owner email failed")
        if s.owner_whatsapp and s.whatsapp_token:
            try:
                # Free-form text only reaches the owner if they messaged the business number in the last 24h.
                await self.whatsapp_text(s.owner_whatsapp, f"{subject}\n\n{text}")
            except Exception:
                try:
                    if not s.wa_template_owner_alert:
                        raise
                    await self.whatsapp_template(s.owner_whatsapp, s.wa_template_owner_alert, [subject[:200]])
                except Exception:
                    log.warning("owner WhatsApp alert not delivered (owner outside 24h window, no template?)")
        if not (s.owner_email or s.owner_whatsapp):
            log.warning("owner alert (no owner contact configured): %s - %s", subject, text)
