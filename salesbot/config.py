"""Settings, read once from environment variables (see .env.example)."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _env_list(name: str, default: str = "") -> list[str]:
    return [item.strip() for item in _env(name, default).split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    # Claude
    model: str = field(default_factory=lambda: _env("CLAUDE_MODEL", "claude-opus-5-5"))
    effort: str = field(default_factory=lambda: _env("CLAUDE_EFFORT", "medium"))

    # Storage and paths
    database_path: str = field(default_factory=lambda: _env("DATABASE_PATH", str(ROOT / "data" / "salesbot.db")))
    knowledge_dir: Path = field(default_factory=lambda: Path(_env("KNOWLEDGE_DIR", str(ROOT / "knowledge"))))
    public_base_url: str = field(default_factory=lambda: _env("PUBLIC_BASE_URL", "http://localhost:8000"))
    timezone: ZoneInfo = field(default_factory=lambda: ZoneInfo(_env("TIMEZONE", "Asia/Dubai")))

    # Admin dashboard
    admin_token: str = field(default_factory=lambda: _env("ADMIN_TOKEN"))

    # WhatsApp Cloud API (Meta)
    meta_graph_version: str = field(default_factory=lambda: _env("META_GRAPH_VERSION", "v21.0"))
    meta_app_secret: str = field(default_factory=lambda: _env("META_APP_SECRET"))
    meta_verify_token: str = field(default_factory=lambda: _env("META_VERIFY_TOKEN"))
    whatsapp_token: str = field(default_factory=lambda: _env("WHATSAPP_TOKEN"))
    whatsapp_phone_number_id: str = field(default_factory=lambda: _env("WHATSAPP_PHONE_NUMBER_ID"))
    # Approved WhatsApp templates used outside the 24-hour customer-service window.
    # Each template takes one body parameter: the customer's first name.
    wa_template_followup: str = field(default_factory=lambda: _env("WA_TEMPLATE_FOLLOWUP"))
    wa_template_missed_call: str = field(default_factory=lambda: _env("WA_TEMPLATE_MISSED_CALL"))
    wa_template_review: str = field(default_factory=lambda: _env("WA_TEMPLATE_REVIEW"))
    wa_template_reactivation: str = field(default_factory=lambda: _env("WA_TEMPLATE_REACTIVATION"))
    wa_template_language: str = field(default_factory=lambda: _env("WA_TEMPLATE_LANGUAGE", "en"))

    # Instagram messaging (same Meta app)
    instagram_account_id: str = field(default_factory=lambda: _env("INSTAGRAM_ACCOUNT_ID"))
    instagram_token: str = field(default_factory=lambda: _env("INSTAGRAM_TOKEN"))
    instagram_comment_keywords: list[str] = field(
        default_factory=lambda: _env_list("INSTAGRAM_COMMENT_KEYWORDS", "عرض,سعر,price,quote,info")
    )

    # Email
    smtp_host: str = field(default_factory=lambda: _env("SMTP_HOST"))
    smtp_port: int = field(default_factory=lambda: int(_env("SMTP_PORT", "587")))
    smtp_user: str = field(default_factory=lambda: _env("SMTP_USER"))
    smtp_password: str = field(default_factory=lambda: _env("SMTP_PASSWORD"))
    email_from: str = field(default_factory=lambda: _env("EMAIL_FROM"))
    email_inbound_token: str = field(default_factory=lambda: _env("EMAIL_INBOUND_TOKEN"))

    # Phone (Twilio voice number)
    twilio_auth_token: str = field(default_factory=lambda: _env("TWILIO_AUTH_TOKEN"))
    call_forward_number: str = field(default_factory=lambda: _env("CALL_FORWARD_NUMBER"))

    # Owner notifications (hot leads, escalations, daily digest)
    owner_email: str = field(default_factory=lambda: _env("OWNER_EMAIL"))
    owner_whatsapp: str = field(default_factory=lambda: _env("OWNER_WHATSAPP"))

    # Website chat
    webchat_allowed_origins: list[str] = field(
        default_factory=lambda: _env_list("WEBCHAT_ALLOWED_ORIGINS", "https://www.echolight.ae,https://echolight.ae")
    )

    # Automation timing
    followup_delays_hours: list[float] = field(
        default_factory=lambda: [float(h) for h in _env_list("FOLLOWUP_DELAYS_HOURS", "20,72,168")]
    )
    review_request_delay_hours: float = field(default_factory=lambda: float(_env("REVIEW_DELAY_HOURS", "24")))
    reactivation_delay_days: float = field(default_factory=lambda: float(_env("REACTIVATION_DELAY_DAYS", "60")))
    quiet_hours: tuple[int, int] = field(default_factory=lambda: (22, 9))  # no automated sends 22:00-09:00 local
    digest_hour: int = field(default_factory=lambda: int(_env("DIGEST_HOUR", "9")))


settings = Settings()
