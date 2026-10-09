"""Trial mode (the default): the bot drafts everything and nothing it writes reaches a customer on any channel."""

import time
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from conftest import FakeClient, message, text, tool
from salesbot.agent import SalesAgent
from salesbot.app import create_app
from salesbot.prompts import TRIAL_NOTE
from salesbot.security import twilio_signature
from salesbot.tools import format_date, today_local, valid_until_from
from test_app import ADMIN, comment_payload, meta_post, wait_for, whatsapp_payload


@pytest.fixture
def app_env(trial, db, channels):
    claude = FakeClient()
    app = create_app(db=db, channels=channels, client=claude, start_scheduler=False)
    with TestClient(app) as client:
        yield client, claude, app


def test_trial_mode_is_the_default(monkeypatch):
    from salesbot import config

    monkeypatch.delenv("TRIAL_MODE")
    assert config.Settings().trial_mode is True
    monkeypatch.setenv("TRIAL_MODE", "false")
    assert config.Settings().trial_mode is False


def test_whatsapp_reply_is_drafted_with_the_conversation(app_env, db, channels):
    client, claude, _ = app_env
    claude.queue(
        message(tool("save_lead_details", {"name": "Sara", "event_type": "wedding"}),
                tool("request_price", {"requirements": "Wedding, 300 guests, lighting"})),
        message(text("Thank you Sara! The team is preparing your quote.")),
    )
    meta_post(client, whatsapp_payload("wamid.t1", "971501112233", "Wedding for 300 guests, need lighting", "Sara"))
    wait_for(lambda: db.list_leads() and db.drafts(db.list_leads()[0]["id"]))
    lead = db.list_leads()[0]

    assert channels.to_customers() == [], "nothing reaches the customer"
    alerts = [subject for _, subject, _ in channels.of("owner")]
    assert len(alerts) == 2, "owner alerts still go out: the price request and the new-message alert"
    assert any("New message from Sara on whatsapp" in a for a in alerts)
    assert db.outbound_messages(lead["id"]) == []
    [draft] = db.drafts(lead["id"])
    assert (draft["kind"], draft["channel"], draft["status"]) == ("reply", "whatsapp", "pending")
    assert draft["text"] == "Thank you Sara! The team is preparing your quote."
    assert draft["in_reply_to"] == "Wedding for 300 guests, need lighting"
    assert TRIAL_NOTE in claude.messages.calls[0]["messages"][-1]["content"], "Claude knows nothing is sent"
    assert len(db.pending_jobs(lead["id"], "price_reminder")) == 2

    page = client.get(f"/admin/leads/{lead['id']}", auth=ADMIN).text
    assert "Trial mode: the bot drafts only" in page
    assert "Wedding for 300 guests, need lighting" in page and "Thank you Sara!" in page
    assert "Draft: reply" in page and "Use this draft" in page
    assert ">1</td>" in client.get("/admin", auth=ADMIN).text, "pending drafts are counted per lead"


def test_draft_review_and_readiness(app_env, db):
    client, _, _ = app_env
    lead = db.get_or_create_lead("whatsapp", "971501112244", name="Omar")
    good = db.add_draft(lead["id"], "whatsapp", "reply", "Hello Omar!")
    bad = db.add_draft(lead["id"], "whatsapp", "follow_up", "Buy now!!!")
    url = f"/admin/drafts/{good}/review"
    assert client.post(url, data={"status": "good"}).status_code == 401
    assert client.post(url, data={"status": "good"}, auth=ADMIN, headers={"Origin": "https://evil.example"}).status_code == 403
    assert client.post(url, data={"status": "great"}, auth=ADMIN).status_code == 400
    response = client.post(url, data={"status": "good", "back": f"/admin/leads/{lead['id']}"}, auth=ADMIN,
                           follow_redirects=False)
    assert response.status_code == 303 and response.headers["location"] == f"/admin/leads/{lead['id']}#draft-{good}"
    client.post(f"/admin/drafts/{bad}/review", data={"status": "wrong", "feedback": "Too pushy",
                                                     "back": "https://evil.example"}, auth=ADMIN)
    assert db.get_draft(good)["status"] == "good" and db.get_draft(good)["reviewed_at"]
    assert (db.get_draft(bad)["status"], db.get_draft(bad)["feedback"]) == ("wrong", "Too pushy")
    page = client.get("/admin/drafts", auth=ADMIN).text
    assert "0 waiting for review" in page and "Overall: 50% good of 2 reviewed" in page
    assert "reply: 100% good of 1 reviewed" in page and "follow up: 0% good of 1 reviewed" in page
    assert "Too pushy" in page


def test_price_is_drafted_then_sent_by_the_team(app_env, db, channels):
    client, claude, _ = app_env
    lead = db.get_or_create_lead("whatsapp", "971501117700", name="Laila", stage="awaiting_price",
                                 last_inbound_at=time.time(), price_requested_at=time.time() - 3600)
    claude.queue(message(text("Laila, your quote is AED 9,000 excl. VAT (+5% VAT), valid until Monday.")))
    response = client.post(f"/admin/leads/{lead['id']}/price", data={"details": "AED 9,000 excl. VAT", "amount": "9000"},
                           auth=ADMIN)
    assert "Trial mode: nothing was sent" in response.text
    assert channels.to_customers() == []
    [draft] = db.drafts(lead["id"])
    assert draft["kind"] == "price" and draft["quote_valid_until"] == valid_until_from().isoformat()
    saved = db.get_lead(lead["id"])
    assert (saved["price_to_send"], saved["quote_sent_at"], saved["stage"]) == (0, None, "awaiting_price")
    assert db.pending_jobs(lead["id"], "price_reminder") == [], "priced, so no more reminders"

    # "Use this draft" fills the team reply box; the team sends it themselves.
    page = client.get(f"/admin/leads/{lead['id']}?draft={draft['id']}", auth=ADMIN).text
    assert "Laila, your quote is AED 9,000" in page.split("id='reply'")[1]
    assert "name='gives_price' value='1' checked" in page
    sent = client.post(f"/admin/leads/{lead['id']}/reply", auth=ADMIN, data={
        "text": draft["text"], "gives_price": "1", "draft_id": str(draft["id"])})
    assert f"Quote valid until {format_date(valid_until_from())}" in sent.text
    assert channels.of("whatsapp_text") == [("whatsapp_text", "971501117700", draft["text"])]
    saved = db.get_lead(lead["id"])
    assert (saved["stage"], saved["quote_valid_until"]) == ("quoted", draft["quote_valid_until"])
    assert db.get_draft(draft["id"])["sent_at"]


def test_comment_reply_webchat_and_missed_call_send_nothing(app_env, db, channels):
    client, claude, _ = app_env
    claude.queue(message(text("Thanks for your comment! What's the event?")))
    meta_post(client, comment_payload("comment-t1", "price?"))
    wait_for(lambda: db.list_leads() and db.drafts(db.list_leads()[0]["id"]))
    [draft] = db.drafts(db.list_leads()[0]["id"])
    assert (draft["kind"], draft["in_reply_to"]) == ("comment_reply", "price?")

    claude.queue(message(text("Hi! What date is the event?")))
    chat = client.post("/chat", json={"session_id": "session-trial-1", "text": "Hi, I need lighting"})
    assert chat.json() == {"reply": "", "held": True}, "the widget shows its own 'the team will reply' note"

    params = {"From": "+971507770000", "CallSid": "CA9"}
    client.post("/webhooks/voice", data=params, headers={
        "X-Twilio-Signature": twilio_signature("twilio-token", "https://bot.example.com/webhooks/voice", params)})
    wait_for(lambda: any("call them back" in body for _, _, body in channels.of("owner")))
    assert any("Trial mode: a WhatsApp message was drafted, not sent. Please call them back." in body
               for _, _, body in channels.of("owner"))
    new_message_alerts = [body for _, subject, body in channels.of("owner") if "New message from" in subject]
    assert len(new_message_alerts) == 2, "the comment and the website chat each alert the owner"
    assert "Hi! What date is the event?" in new_message_alerts[1]

    assert channels.to_customers() == []
    kinds = sorted(d["kind"] for d in db.drafts())
    assert kinds == ["comment_reply", "missed_call", "reply"]
    missed = next(d for d in db.drafts() if d["kind"] == "missed_call")
    assert "missed_call_v1" in missed["text"] and "مرحباً بك، فاتتنا مكالمتك" in missed["text"]


async def test_followups_templates_reviews_and_emails_are_drafted(trial, db, channels):
    client = FakeClient(
        message(text("Just checking in!")),
        message(tool("send_email_summary", {"subject": "Your proposal", "body": "Lighting and LED.\n\nEchoLight team"})),
        message(text("I've prepared the summary for you.")),
    )
    agent = SalesAgent(db, channels, client)
    inside = db.get_or_create_lead("whatsapp", "971501119901", last_inbound_at=time.time() - 3600)
    outside = db.get_or_create_lead("whatsapp", "971501119902", name="Khalid", language="ar",
                                    last_inbound_at=time.time() - 30 * 3600)
    done = db.get_or_create_lead("whatsapp", "971501119903", stage="completed", marketing_opt_in=1)
    mail = db.get_or_create_lead("email", "a@corp.ae", email="a@corp.ae", last_inbound_at=time.time())

    await agent.run_followup(inside["id"], 1)
    await agent.run_followup(outside["id"], 2)
    await agent.run_template_touch(done["id"], "review_request")
    await agent.handle_inbound(mail["id"], [text("Please email me a summary")])
    status = await agent.present_price(outside["id"], "AED 5,000 excl. VAT")

    assert channels.to_customers() == []
    assert [d["kind"] for d in db.drafts(inside["id"])] == ["follow_up"]
    [template] = db.drafts(outside["id"])[-1:]
    assert template["kind"] == "followup"
    assert "followup_v1" in template["text"] and "مرحباً Khalid، بخصوص استفسارك" in template["text"]
    assert status == "queued" and any(d["kind"] == "quote_ready" for d in db.drafts(outside["id"]))
    assert db.get_lead(outside["id"])["price_to_send"] == 1, "the price is drafted when the customer next writes"
    assert [d["kind"] for d in db.drafts(done["id"])] == ["review_request"]
    mail_kinds = sorted(d["kind"] for d in db.drafts(mail["id"]))
    assert mail_kinds == ["email_summary", "reply"]
    tool_result = client.messages.calls[2]["messages"][-1]["content"][0]["content"]
    assert '"drafted": true' in tool_result and "not sent" in tool_result
    assert "[WhatsApp template" not in (db.get_lead(outside["id"])["agent_notes"] or ""), "nothing was sent"


async def test_scheduler_in_trial_sends_nothing_and_digest_counts_drafts(trial, db, channels):
    from salesbot.scheduler import Scheduler

    agent = SalesAgent(db, channels, FakeClient())
    scheduler = Scheduler(db, agent)
    lead = db.get_or_create_lead("whatsapp", "971501119950", name="Layla",
                                 last_inbound_at=time.time() - 3 * 86400)
    db.schedule_job("followup", 0, lead["id"], {"step": 3})
    db.schedule_job("daily_digest", 0)
    noon = time.time() - (time.time() % 86400) + 8 * 3600  # 12:00 UAE today, outside quiet hours
    await scheduler.tick(now=noon)
    assert channels.to_customers() == []
    assert [d["kind"] for d in db.drafts(lead["id"])] == ["followup"]
    [(_, subject, body)] = channels.of("owner")
    assert subject == "Daily sales digest" and "Trial mode: nothing is sent to customers. 1 drafts" in body


async def test_team_reply_is_sent_even_in_trial(trial, db, channels):
    agent = SalesAgent(db, channels, FakeClient())
    lead = db.get_or_create_lead("instagram", "ig-55", name="Aisha", last_inbound_at=time.time())
    assert await agent.team_reply(lead["id"], "Hi Aisha, Kareem here!") == "Sent to Aisha."
    assert channels.of("instagram_text") == [("instagram_text", "ig-55", "Hi Aisha, Kareem here!")]
    assert db.drafts(lead["id"]) == []


def test_expired_quote_shows_in_dashboard(app_env, db):
    client, _, _ = app_env
    lead = db.get_or_create_lead("whatsapp", "971501119960", name="Old quote", stage="quoted",
                                 quote_sent_at=time.time() - 6 * 86400,
                                 quote_valid_until=(today_local() - timedelta(days=3)).isoformat())
    assert "expired 3d ago" in client.get("/admin", auth=ADMIN).text
    assert "expired 3d ago" in client.get(f"/admin/leads/{lead['id']}", auth=ADMIN).text


async def test_trial_alerts_the_owner_about_each_new_message_once_per_window(trial, db, channels):
    claude = FakeClient()
    agent = SalesAgent(db, channels, claude)
    lead = db.get_or_create_lead("whatsapp", "971501113344", name="Mona")
    claude.queue(message(text("Hello Mona! When is the event?")))
    await agent.handle_inbound(lead["id"], [{"type": "text", "text": "Hi, I need a DJ for a wedding"}])

    assert channels.to_customers() == [], "nothing reaches the customer"
    [(_, subject, body)] = channels.of("owner")
    assert subject == f"[Lead #{lead['id']}] New message from Mona on whatsapp: please reply (trial mode)"
    assert "Hi, I need a DJ for a wedding" in body and "Hello Mona! When is the event?" in body
    assert f"/admin/leads/{lead['id']}" in body

    claude.queue(message(text("Great, what date?")))
    await agent.handle_inbound(lead["id"], [{"type": "text", "text": "Also lighting"}])
    assert len(channels.of("owner")) == 1, "one alert per lead per 30 minutes"

    db.update_lead(lead["id"], trial_alert_at=time.time() - 31 * 60)
    claude.queue(message(text("Noted!")))
    await agent.handle_inbound(lead["id"], [{"type": "text", "text": "And a stage"}])
    assert len(channels.of("owner")) == 2
    assert channels.to_customers() == []


async def test_live_mode_sends_no_new_message_alert(db, channels):
    claude = FakeClient()
    agent = SalesAgent(db, channels, claude)
    lead = db.get_or_create_lead("whatsapp", "971501113355", name="Huda")
    claude.queue(message(text("Hello Huda!")))
    await agent.handle_inbound(lead["id"], [{"type": "text", "text": "Hi"}])
    assert channels.of("owner") == []
    assert len(channels.to_customers()) == 1
