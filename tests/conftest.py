import itertools
import os
import shutil
from pathlib import Path

import pytest
from anthropic.types.beta import BetaMessage

ROOT = Path(__file__).resolve().parent.parent

TEST_ENV = {
    "ADMIN_TOKEN": "admin-secret",
    "META_APP_SECRET": "app-secret",
    "META_VERIFY_TOKEN": "verify-me",
    "WHATSAPP_TOKEN": "wa-token",
    "WHATSAPP_PHONE_NUMBER_ID": "123",
    "WA_TEMPLATE_FOLLOWUP": "followup_v1",
    "WA_TEMPLATE_MISSED_CALL": "missed_call_v1",
    "WA_TEMPLATE_REVIEW": "review_v1",
    "WA_TEMPLATE_REACTIVATION": "reactivation_v1",
    "INSTAGRAM_ACCOUNT_ID": "ig-business",
    "INSTAGRAM_TOKEN": "ig-token",
    "EMAIL_INBOUND_TOKEN": "mail-token",
    "EMAIL_FROM": "sales@echolight.ae",
    "TWILIO_AUTH_TOKEN": "twilio-token",
    "PUBLIC_BASE_URL": "https://bot.example.com",
    "OWNER_EMAIL": "owner@example.com",
}

PRICING = """
vat_rate: 0.05
quote_validity_days: 14
max_discount_percent: 0
services:
  stage_lighting: {label: Stage lighting, unit: package per event day, min: 5000, max: 9000}
  led_screen: {label: LED screen, unit: square metre per event day, min: 300, max: 450}
  laser_show: {label: Laser show, unit: show, min: null, max: null}
"""


@pytest.fixture(autouse=True)
def settings(tmp_path, monkeypatch):
    knowledge = tmp_path / "knowledge"
    knowledge.mkdir()
    shutil.copy(ROOT / "knowledge" / "business.md", knowledge / "business.md")
    (knowledge / "pricing.yaml").write_text(PRICING)
    for key, value in {**TEST_ENV, "KNOWLEDGE_DIR": str(knowledge)}.items():
        monkeypatch.setenv(key, value)
    from salesbot import config

    monkeypatch.setattr(config, "settings", config.Settings())
    return config.settings


_ids = itertools.count(1)


def message(*blocks: dict, stop_reason: str | None = None) -> BetaMessage:
    """Build a real SDK response object from content blocks."""
    if stop_reason is None:
        stop_reason = "tool_use" if any(b["type"] == "tool_use" for b in blocks) else "end_turn"
    return BetaMessage.model_validate({
        "id": f"msg_{next(_ids)}", "type": "message", "role": "assistant", "model": "claude-opus-5-5",
        "content": list(blocks), "stop_reason": stop_reason, "stop_sequence": None,
        "usage": {"input_tokens": 10, "output_tokens": 10},
    })


def text(value: str) -> dict:
    return {"type": "text", "text": value}


def tool(name: str, args: dict) -> dict:
    return {"type": "tool_use", "id": f"toolu_{next(_ids)}", "name": name, "input": args}


class FakeMessages:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls: list[dict] = []

    async def create(self, **kwargs):
        # Snapshot messages: the list is rebuilt from the database each call.
        self.calls.append({**kwargs, "messages": [dict(m) for m in kwargs["messages"]]})
        if not self.responses:
            raise AssertionError("unexpected extra Claude call")
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class FakeClient:
    def __init__(self, *responses):
        self.messages = FakeMessages(responses)
        self.beta = self

    def queue(self, *responses):
        self.messages.responses.extend(responses)


class FakeChannels:
    def __init__(self):
        self.sent: list[tuple] = []

    async def whatsapp_text(self, to, body):
        self.sent.append(("whatsapp_text", to, body))

    async def whatsapp_template(self, to, template, params):
        self.sent.append(("whatsapp_template", to, template, params))

    async def whatsapp_media(self, media_id):
        return b"\x89PNG fake", "image/png"

    async def instagram_text(self, user_id, body):
        self.sent.append(("instagram_text", user_id, body))

    async def instagram_private_reply(self, comment_id, body):
        self.sent.append(("instagram_private_reply", comment_id, body))

    async def send_email(self, to, subject, body):
        self.sent.append(("email", to, subject, body))

    async def notify_owner(self, subject, body):
        self.sent.append(("owner", subject, body))

    def of(self, kind):
        return [s for s in self.sent if s[0] == kind]


@pytest.fixture
def db():
    from salesbot.db import Database

    return Database(":memory:")


@pytest.fixture
def channels():
    return FakeChannels()


def assert_valid_message_order(messages: list[dict]) -> None:
    """The API rule for mid-conversation system messages, plus strict user/assistant alternation."""
    assert messages[0]["role"] == "user"
    for i, m in enumerate(messages):
        if m["role"] == "system":
            assert messages[i - 1]["role"] == "user"
            assert i == len(messages) - 1 or messages[i + 1]["role"] == "assistant"
    roles = [m["role"] for m in messages if m["role"] != "system"]
    assert all(a != b for a, b in zip(roles, roles[1:])), roles
