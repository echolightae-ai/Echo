"""Business rules that don't need a conversation: keywords, price parsing, wording, settings, storage."""

import re
import sqlite3
from pathlib import Path

import pytest

from salesbot.app import comment_triggers, parse_amount
from salesbot.config import Settings
from salesbot.templates import EMAIL_TOUCHES, WHATSAPP_TEMPLATES, render_email, render_whatsapp

ROOT = Path(__file__).resolve().parent.parent
KEYWORDS = Settings().instagram_comment_keywords


@pytest.mark.parametrize("comment", [
    "عرض", "عرض!", " عرض 🔥🔥 ", "#عرض", "عَرض", "سعر", "Price", "PRICE?", "info", "quote",
    "كم السعر؟", "السعر لو سمحت", "ممكن الأسعار", "بكم الليزر؟", "بكم", "how much for a wedding?",
    "What are your prices", "Can I get a quote for my wedding",
])
def test_comment_that_asks_triggers_a_private_reply(comment):
    assert comment_triggers(comment, KEYWORDS)


@pytest.mark.parametrize("comment", [
    "عرض رهيب", "عرض رهيب 🔥", "أحلى عرض", "عرض please", "ما شاء الله", "فخورين بكم", "أهلاً بكم",
    "nice", "amazing show", "priceless 😍", "info about the song?", "", "🔥🔥",
])
def test_compliments_and_chatter_do_not_trigger(comment):
    assert not comment_triggers(comment, KEYWORDS)


@pytest.mark.parametrize("wording, amount", [
    ("AED 28,000 excl. VAT", 28000),
    ("#12 Dec 2026 gala, AED 28,000", 28000),
    ("Dec 2026 AED 28,000 excl. VAT", 28000),
    ("28,000 AED for 12/12/2026", 28000),
    ("السعر 28000 درهم غير شامل الضريبة", 28000),
    ("AED28,500.50 + VAT", 28500),
    ("45000 + VAT for 2 days", 45000),
    ("Gala on 12 Dec 2026, 15,000 all in", 15000),
    ("2026 event, lighting only, 9500", 9500),
    ("price on request", None),
    ("event in 2026", None),
    ("AED 2026", 2026),
])
def test_parse_amount_prefers_currency_and_ignores_years(wording, amount):
    assert parse_amount(wording) == amount


def test_readme_template_table_matches_the_code():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for kind, template in WHATSAPP_TEMPLATES.items():
        assert template["ar"] in readme, f"Arabic wording of {kind} differs from templates.py"
        assert template["en"] in readme, f"English wording of {kind} differs from templates.py"
        assert f"| `{template['name']}` " in readme and template["category"] in readme
    assert WHATSAPP_TEMPLATES["review_request"]["category"] == "Marketing"
    assert WHATSAPP_TEMPLATES["reactivation"]["category"] == "Marketing"
    assert WHATSAPP_TEMPLATES["followup"]["category"] == "Utility"
    assert "about your event enquiry" in WHATSAPP_TEMPLATES["followup"]["en"]


def test_readme_has_no_stale_or_contradictory_claims():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "To confirm" not in readme
    assert "incl. VAT" not in readme and "excl. VAT (+5% VAT)" in readme
    assert "#12 AED" not in readme and "Reply to that email" not in readme
    assert "TRIAL_MODE" in readme and "not deployed" in readme and "system of record" in readme
    assert "coexistence" in readme and "live test" in readme.lower()
    assert "never contacts strangers" in readme and "off by default" in readme
    assert "around the clock" not in readme


def test_env_example_is_safe_to_load():
    lines = (ROOT / ".env.example").read_text(encoding="utf-8").splitlines()
    settings = [line for line in lines if line.strip() and not line.lstrip().startswith("#")]
    assert all("=" in line and " #" not in line for line in settings), "no comments after values"
    values = dict(line.split("=", 1) for line in settings)
    assert values["TRIAL_MODE"] == "true"
    assert values["WA_TEMPLATE_DEFAULT_LANGUAGE"] == "ar" and "WA_TEMPLATE_LANGUAGE" not in values
    assert {"PRICE_REMINDER_REPEAT_HOURS", "QUOTE_VALIDITY_DAYS"} <= set(values)


LEVANTINE_ONLY = ["كيف فينا", "كتير", "هيك", "بدك", "شو"]


def _arabic_texts() -> list[str]:
    texts = [t["ar"] for t in WHATSAPP_TEMPLATES.values()]
    texts += [t["ar"] for t in EMAIL_TOUCHES.values()] + [t["subject"]["ar"] for t in EMAIL_TOUCHES.values()]
    texts.append((ROOT / "static" / "widget.js").read_text(encoding="utf-8"))
    return texts


@pytest.mark.parametrize("word", LEVANTINE_ONLY)
def test_arabic_templates_are_gulf_neutral(word):
    pattern = re.compile(rf"(?<!\w){word}(?!\w)")
    assert not any(pattern.search(t) for t in _arabic_texts())


def test_name_fallback_reads_naturally():
    assert render_whatsapp("followup", "ar", "بك").startswith("مرحباً بك، بخصوص استفسارك")
    assert render_whatsapp("followup", "en", "there").startswith("Hi there, about your event enquiry")
    subject, body = render_email("review_request", {"language": "ar"})
    assert body.startswith("مرحباً بك،") and subject == "شكراً من إيكو لايت"
    assert render_email("reactivation", {"name": "Sara Ali"})[1].startswith("Hi Sara,")
    assert "STOP" in render_email("reactivation", {})[1]


def test_stages_match_the_crm():
    from salesbot.db import STAGES
    from salesbot.tools import AGENT_STAGES, TEAM_STAGES

    assert STAGES == ("new", "qualifying", "awaiting_price", "quoted", "negotiating", "booked", "confirmed",
                      "completed", "lost")
    assert AGENT_STAGES == ["qualifying", "negotiating", "booked", "lost"]
    assert list(TEAM_STAGES) == ["confirmed", "completed", "lost"]


def test_old_database_is_upgraded_in_place(tmp_path):
    path = tmp_path / "old.db"
    old = sqlite3.connect(path)  # the first version's schema
    old.executescript("""
        CREATE TABLE leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT, channel TEXT NOT NULL, channel_user_id TEXT NOT NULL,
            name TEXT, phone TEXT, email TEXT, language TEXT, event_type TEXT, event_date TEXT, venue TEXT,
            emirate TEXT, guest_count INTEGER, indoor_outdoor TEXT, services TEXT, budget_aed INTEGER, notes TEXT,
            stage TEXT NOT NULL DEFAULT 'new', quote_aed INTEGER, quote_details TEXT, price_requested_at REAL,
            marketing_opt_in INTEGER NOT NULL DEFAULT 0, do_not_contact INTEGER NOT NULL DEFAULT 0, source TEXT,
            agent_notes TEXT, last_inbound_at REAL, last_outbound_at REAL,
            created_at REAL NOT NULL, updated_at REAL NOT NULL, UNIQUE(channel, channel_user_id));
        CREATE TABLE outbox (id INTEGER PRIMARY KEY AUTOINCREMENT, lead_id INTEGER NOT NULL REFERENCES leads(id),
            channel TEXT NOT NULL, text TEXT NOT NULL, created_at REAL NOT NULL);
        INSERT INTO leads (channel, channel_user_id, name, created_at, updated_at) VALUES ('whatsapp', '9715', 'Old', 1, 1);
    """)
    old.commit()
    old.close()
    from salesbot.db import Database

    db = Database(str(path))
    lead = db.get_lead(1)
    assert (lead["name"], lead["bot_paused"], lead["price_to_send"], lead["quote_valid_until"]) == ("Old", 0, 0, None)
    db.record_outbound(1, "whatsapp", "hi", sender="team")
    assert db.outbound_messages(1)[0]["sender"] == "team"
    assert db.add_draft(1, "whatsapp", "reply", "draft text")


def test_removed_price_routes_are_gone():
    import salesbot.app as app_module
    import salesbot.tools as tools_module

    assert not hasattr(app_module, "strip_quoted_reply")
    assert not hasattr(tools_module, "price_reply_help")
    source = (ROOT / "salesbot" / "app.py").read_text(encoding="utf-8")
    assert "handle_owner_email" not in source and "handle_owner_whatsapp" not in source
    assert "incl. VAT" not in source + (ROOT / "salesbot" / "tools.py").read_text(encoding="utf-8")
