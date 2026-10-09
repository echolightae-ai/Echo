import hashlib
import hmac
import json
import time
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from conftest import FakeClient, message, text, tool
from salesbot.app import create_app
from salesbot.security import twilio_signature


def wait_for(predicate, timeout=3.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return
        time.sleep(0.02)
    raise AssertionError("condition not met in time")


def meta_post(client, payload, secret="app-secret"):
    body = json.dumps(payload).encode()
    signature = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return client.post("/webhooks/meta", content=body,
                       headers={"X-Hub-Signature-256": signature, "Content-Type": "application/json"})


def whatsapp_payload(msg_id, wa_id, body, name="Fatima"):
    return {"object": "whatsapp_business_account", "entry": [{"changes": [{"value": {
        "contacts": [{"wa_id": wa_id, "profile": {"name": name}}],
        "messages": [{"from": wa_id, "id": msg_id, "type": "text", "text": {"body": body}}],
    }}]}]}


@pytest.fixture
def app_env(db, channels):
    claude = FakeClient()
    app = create_app(db=db, channels=channels, client=claude, start_scheduler=False)
    with TestClient(app) as client:
        yield client, claude, app


def test_meta_verification_handshake(app_env):
    client, _, _ = app_env
    ok = client.get("/webhooks/meta", params={"hub.mode": "subscribe", "hub.verify_token": "verify-me",
                                              "hub.challenge": "42"})
    assert ok.text == "42"
    assert client.get("/webhooks/meta", params={"hub.mode": "subscribe", "hub.verify_token": "no"}).status_code == 403


def test_whatsapp_message_gets_reply_once(app_env, db, channels):
    client, claude, _ = app_env
    claude.queue(message(text("أهلاً فاطمة! شو نوع الفعالية؟")))
    payload = whatsapp_payload("wamid.1", "971501112222", "مرحبا بدي اضاءة لعرس")
    assert meta_post(client, payload).status_code == 200
    assert meta_post(client, payload).status_code == 200  # Meta retry: must not reply twice
    wait_for(lambda: channels.of("whatsapp_text"))
    time.sleep(0.1)
    assert channels.of("whatsapp_text") == [("whatsapp_text", "971501112222", "أهلاً فاطمة! شو نوع الفعالية؟")]
    lead = db.list_leads()[0]
    assert (lead["name"], lead["phone"], lead["source"]) == ("Fatima", "+971501112222", "whatsapp")


def test_unsigned_meta_webhook_rejected(app_env):
    client, _, _ = app_env
    response = meta_post(client, whatsapp_payload("wamid.2", "971500000000", "hi"), secret="wrong")
    assert response.status_code == 401


def test_failed_reply_is_queued_for_retry(app_env, db, channels):
    client, claude, _ = app_env
    claude.queue(RuntimeError("API down"))
    meta_post(client, whatsapp_payload("wamid.3", "971503334444", "hello"))
    wait_for(lambda: db.pending_jobs(kind="retry_inbound"))
    [job] = db.pending_jobs(kind="retry_inbound")
    assert job["payload"]["content"] == [{"type": "text", "text": "hello"}]
    assert db.transcript(job["lead_id"]) == []


def test_whatsapp_image_is_passed_to_claude(app_env, channels):
    client, claude, _ = app_env
    claude.queue(message(text("Beautiful venue!")))
    payload = whatsapp_payload("wamid.4", "971505556666", "")
    payload["entry"][0]["changes"][0]["value"]["messages"][0] = {
        "from": "971505556666", "id": "wamid.4", "type": "image", "image": {"id": "media-1", "caption": "our hall"}}
    meta_post(client, payload)
    wait_for(lambda: channels.of("whatsapp_text"))
    content = claude.messages.calls[0]["messages"][0]["content"]
    assert content[0]["type"] == "image" and content[0]["source"]["media_type"] == "image/png"
    assert content[1] == {"type": "text", "text": "our hall"}


def test_instagram_comment_keyword_gets_private_reply(app_env, db, channels):
    client, claude, _ = app_env
    claude.queue(message(text("Thanks for your comment! What's the event?")))
    payload = {"object": "instagram", "entry": [{"changes": [{"field": "comments", "value": {
        "id": "comment-9", "text": "عرض please", "from": {"id": "ig-user-1", "username": "noor"}}}]}]}
    meta_post(client, payload)
    wait_for(lambda: channels.of("instagram_private_reply"))
    assert channels.of("instagram_private_reply") == [
        ("instagram_private_reply", "comment-9", "Thanks for your comment! What's the event?")]
    assert db.list_leads()[0]["source"] == "instagram_comment"

    # A comment without a keyword is ignored.
    meta_post(client, {"object": "instagram", "entry": [{"changes": [{"field": "comments", "value": {
        "id": "comment-10", "text": "nice", "from": {"id": "ig-user-2"}}}]}]})
    time.sleep(0.1)
    assert len(claude.messages.calls) == 1


def test_instagram_dm_reply_and_echo_ignored(app_env, channels):
    client, claude, _ = app_env
    claude.queue(message(text("Hello from EchoLight")))
    meta_post(client, {"object": "instagram", "entry": [{"messaging": [
        {"sender": {"id": "ig-user-3"}, "message": {"mid": "m1", "text": "price for laser?"}},
        {"sender": {"id": "ig-business"}, "message": {"mid": "m2", "text": "echo", "is_echo": True}},
    ]}]})
    wait_for(lambda: channels.of("instagram_text"))
    assert channels.of("instagram_text") == [("instagram_text", "ig-user-3", "Hello from EchoLight")]


def test_email_inbound(app_env, db, channels):
    client, claude, _ = app_env
    claude.queue(message(text("Dear Ahmed, thank you for your enquiry.")))
    assert client.post("/webhooks/email?token=wrong", json={}).status_code == 401
    response = client.post("/webhooks/email?token=mail-token", json={
        "From": "Ahmed <ahmed@corp.ae>", "Subject": "LED wall for conference", "TextBody": "We need a 6x3m LED wall",
        "MessageID": "abc"})
    assert response.status_code == 200
    wait_for(lambda: channels.of("email"))
    assert channels.of("email")[0][1:3] == ("ahmed@corp.ae", "EchoLight - your event")
    assert db.list_leads()[0]["name"] == "Ahmed"
    # Our own outgoing mail bouncing back is ignored.
    assert client.post("/webhooks/email?token=mail-token", json={"from": "sales@echolight.ae", "text": "x"}).json()["ignored"]


def test_missed_call_sends_whatsapp_template(app_env, db, channels):
    client, _, _ = app_env
    params = {"From": "+971507778888", "CallSid": "CA1"}
    url = "https://bot.example.com/webhooks/voice"
    assert client.post("/webhooks/voice", data=params).status_code == 401
    response = client.post("/webhooks/voice", data=params,
                           headers={"X-Twilio-Signature": twilio_signature("twilio-token", url, params)})
    assert response.status_code == 200 and "<Say" in response.text
    wait_for(lambda: channels.of("whatsapp_template"))
    assert channels.of("whatsapp_template")[0][1:3] == ("971507778888", "missed_call_v1")
    assert db.list_leads()[0]["source"] == "missed_call"


def test_web_chat(app_env, db):
    client, claude, _ = app_env
    claude.queue(message(tool("save_lead_details", {"email": "visitor@mail.com"})),
                 message(text("Thanks! What date is the event?")))
    response = client.post("/chat", json={"session_id": "session-123456", "text": "Hi, I need lighting"},
                           headers={"Origin": "https://www.echolight.ae"})
    assert response.json() == {"reply": "Thanks! What date is the event?"}
    assert response.headers["access-control-allow-origin"] == "https://www.echolight.ae"
    assert db.list_leads()[0]["email"] == "visitor@mail.com"
    assert client.get("/widget.js").status_code == 200


def test_admin_requires_password(app_env, db):
    client, _, _ = app_env
    lead = db.get_or_create_lead("whatsapp", "971509990000", name="<script>")
    assert client.get("/admin").status_code == 401
    page = client.get("/admin", auth=("owner", "admin-secret"))
    assert page.status_code == 200 and "&lt;script&gt;" in page.text
    assert client.get(f"/admin/leads/{lead['id']}", auth=("owner", "admin-secret")).status_code == 200


async def test_scheduler_respects_quiet_hours_and_runs_due_jobs(db, channels, settings):
    from salesbot.agent import SalesAgent
    from salesbot.scheduler import Scheduler

    agent = SalesAgent(db, channels, FakeClient())
    scheduler = Scheduler(db, agent)
    lead = db.get_or_create_lead("whatsapp", "971501231234", name="Layla")
    db.update_lead(lead["id"], last_inbound_at=time.time() - 3 * 86400)
    job_id = db.schedule_job("followup", 0, lead["id"], {"step": 2})

    night = datetime(2026, 10, 10, 23, 30, tzinfo=settings.timezone).timestamp()
    await scheduler.tick(now=night)
    [job] = db.pending_jobs(lead["id"])
    assert datetime.fromtimestamp(job["run_at"], settings.timezone).hour == 9
    assert channels.sent == []

    morning = datetime(2026, 10, 11, 9, 5, tzinfo=settings.timezone).timestamp()
    await scheduler.tick(now=morning)
    assert channels.of("whatsapp_template") == [("whatsapp_template", "971501231234", "followup_v1", ["Layla"])]
    assert db.pending_jobs(lead["id"]) == [] and job_id


async def test_daily_digest(db, channels, settings):
    from salesbot.agent import SalesAgent
    from salesbot.scheduler import Scheduler

    scheduler = Scheduler(db, SalesAgent(db, channels, FakeClient()))
    lead = db.get_or_create_lead("whatsapp", "971501239999", name="Hamad", event_type="gala dinner")
    db.update_lead(lead["id"], stage="quoted", quote_min_aed=10000, quote_max_aed=15000)
    scheduler.ensure_digest_scheduled()
    [job] = db.pending_jobs(kind="daily_digest")
    await scheduler.tick(now=job["run_at"] + 1)
    [(_, subject, body)] = channels.of("owner")
    assert subject == "Daily sales digest" and "Hamad" in body and "AED 10,000-15,000" in body
    assert len(db.pending_jobs(kind="daily_digest")) == 1, "the digest reschedules itself"


def test_send_failure_resends_text_without_rerunning_claude(app_env, db, channels):
    client, claude, app = app_env
    claude.queue(message(text("Hello!")))

    async def broken(to, body):
        raise RuntimeError("WhatsApp API down")

    channels.whatsapp_text = broken
    meta_post(client, whatsapp_payload("wamid.9", "971504440000", "hi"))
    wait_for(lambda: db.pending_jobs(kind="deliver"))
    [job] = db.pending_jobs(kind="deliver")
    assert job["payload"] == {"text": "Hello!"}
    assert len(claude.messages.calls) == 1
