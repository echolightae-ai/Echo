import hashlib
import hmac
import json
import time
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from conftest import FakeClient, message, text, tool
from salesbot.app import create_app
from salesbot.prompts import VOICE_NOTE_TEXT
from salesbot.security import twilio_signature
from salesbot.tools import today_local

ADMIN = ("owner", "admin-secret")


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


def comment_payload(comment_id, text_, user_id="ig-user-1", username="noor"):
    return {"object": "instagram", "entry": [{"changes": [{"field": "comments", "value": {
        "id": comment_id, "text": text_, "from": {"id": user_id, "username": username}}}]}]}


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
    claude.queue(message(text("أهلاً فاطمة! ما نوع الفعالية؟")))
    payload = whatsapp_payload("wamid.1", "971501112222", "مرحبا أبي إضاءة لعرس")
    assert meta_post(client, payload).status_code == 200
    assert meta_post(client, payload).status_code == 200  # Meta retry: must not reply twice
    wait_for(lambda: channels.of("whatsapp_text"))
    time.sleep(0.1)
    assert channels.of("whatsapp_text") == [("whatsapp_text", "971501112222", "أهلاً فاطمة! ما نوع الفعالية؟")]
    lead = db.list_leads()[0]
    assert (lead["name"], lead["phone"], lead["source"]) == ("Fatima", "+971501112222", "whatsapp")
    assert [m["text"] for m in db.inbound_messages(lead["id"])] == ["مرحبا أبي إضاءة لعرس"]


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


def test_whatsapp_image_is_passed_to_claude(app_env, db, channels):
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
    [logged] = db.inbound_messages(db.list_leads()[0]["id"])
    assert (logged["kind"], logged["media_id"]) == ("image", "media-1")


def test_voice_note_alerts_owner_and_can_be_played(app_env, db, channels):
    client, claude, _ = app_env
    claude.queue(message(text("Thanks for the voice note! The team will listen to it. What's the event date?")))
    payload = whatsapp_payload("wamid.v1", "971505550000", "", name="Maryam")
    payload["entry"][0]["changes"][0]["value"]["messages"][0] = {
        "from": "971505550000", "id": "wamid.v1", "type": "audio",
        "audio": {"id": "audio-77", "mime_type": "audio/ogg; codecs=opus", "voice": True}}
    meta_post(client, payload)
    wait_for(lambda: channels.of("whatsapp_text"))
    lead = db.list_leads()[0]
    [(_, subject, body)] = channels.of("owner")
    assert "voice note" in subject and f"/admin/leads/{lead['id']}" in body
    assert claude.messages.calls[0]["messages"][0]["content"] == [{"type": "text", "text": VOICE_NOTE_TEXT}]
    assert "please type" not in VOICE_NOTE_TEXT.lower()

    [note] = db.inbound_messages(lead["id"])
    media_url = f"/admin/inbox/{note['id']}/media"
    page = client.get(f"/admin/leads/{lead['id']}", auth=ADMIN)
    assert f"<audio controls preload='none' src='{media_url}'" in page.text
    assert client.get(media_url).status_code == 401, "only the team can listen"
    audio = client.get(media_url, auth=ADMIN)
    assert audio.status_code == 200 and audio.content == b"OggS fake voice"
    assert audio.headers["content-type"].startswith("audio/ogg")


def test_instagram_comment_gets_one_private_reply_and_nothing_more(app_env, db, channels):
    client, claude, _ = app_env
    claude.queue(message(text("Thanks for your comment! What's the event?")))
    meta_post(client, comment_payload("comment-9", "عرض 🔥"))
    wait_for(lambda: channels.of("instagram_private_reply"))
    assert channels.of("instagram_private_reply") == [
        ("instagram_private_reply", "comment-9", "Thanks for your comment! What's the event?")]
    lead = db.list_leads()[0]
    assert lead["source"] == "instagram_comment"
    assert lead["last_inbound_at"] is None, "a comment reply doesn't open the DM window"
    assert db.pending_jobs(lead["id"], "followup") == [], "no follow-ups until they DM us"

    # Compliments and comments without a keyword are ignored.
    meta_post(client, comment_payload("comment-10", "عرض رهيب", user_id="ig-user-2"))
    meta_post(client, comment_payload("comment-11", "nice", user_id="ig-user-3"))
    time.sleep(0.1)
    assert len(claude.messages.calls) == 1


async def test_instagram_commenter_is_never_moved_to_whatsapp(db, channels):
    from salesbot.agent import SalesAgent

    agent = SalesAgent(db, channels, FakeClient(message(text("Thanks for your comment! What's the occasion?"))))
    lead = db.get_or_create_lead("instagram", "ig-user-5", source="instagram_comment", phone="+971501234567",
                                 marketing_opt_in=1)
    await agent.handle_comment(lead["id"], "comment-1", "price?")
    assert len(channels.of("instagram_private_reply")) == 1
    assert db.get_lead(lead["id"])["last_inbound_at"] is None
    assert db.pending_jobs(lead["id"], "followup") == []
    await agent.run_followup(lead["id"], 1)
    for kind in ("followup", "quote_ready", "missed_call", "reactivation"):
        assert await agent.send_template(db.get_lead(lead["id"]), kind) == "skipped"
    assert channels.to_customers() == channels.of("instagram_private_reply")


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
    wait_for(lambda: channels.of("owner"))
    assert channels.of("whatsapp_template") == [
        ("whatsapp_template", "971507778888", "missed_call_v1", ["بك"], "ar")]
    assert "The bot sent them a WhatsApp message." in channels.of("owner")[0][2]
    assert db.list_leads()[0]["source"] == "missed_call"


def test_web_chat(app_env, db):
    client, claude, _ = app_env
    claude.queue(message(tool("save_lead_details", {"email": "visitor@mail.com"})),
                 message(text("Thanks! What date is the event?")))
    response = client.post("/chat", json={"session_id": "session-123456", "text": "Hi, I need lighting"},
                           headers={"Origin": "https://www.echolight.ae"})
    assert response.json() == {"reply": "Thanks! What date is the event?"}
    assert response.headers["access-control-allow-origin"] == "https://www.echolight.ae"
    lead = db.list_leads()[0]
    assert lead["email"] == "visitor@mail.com"
    assert db.outbound_messages(lead["id"])[0]["channel"] == "webchat"
    assert client.get("/widget.js").status_code == 200


def test_admin_requires_password(app_env, db):
    client, _, _ = app_env
    lead = db.get_or_create_lead("whatsapp", "971509990000", name="<script>")
    assert client.get("/admin").status_code == 401
    page = client.get("/admin", auth=ADMIN)
    assert page.status_code == 200 and "&lt;script&gt;" in page.text
    assert "Trial mode" not in page.text, "live mode shows no trial banner"
    assert client.get(f"/admin/leads/{lead['id']}", auth=ADMIN).status_code == 200
    assert client.get("/admin/drafts").status_code == 401
    assert client.get("/admin/drafts", auth=ADMIN).status_code == 200
    assert client.get("/health").json() == {"ok": True, "trial_mode": False}


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
    assert channels.of("whatsapp_template") == [("whatsapp_template", "971501231234", "followup_v1", ["Layla"], "ar")]
    assert db.pending_jobs(lead["id"]) == [] and job_id


async def test_daily_digest(db, channels, settings):
    from salesbot.agent import SalesAgent
    from salesbot.scheduler import Scheduler

    scheduler = Scheduler(db, SalesAgent(db, channels, FakeClient()))
    lead = db.get_or_create_lead("whatsapp", "971501239999", name="Hamad", event_type="gala dinner")
    db.update_lead(lead["id"], stage="quoted", quote_aed=12000, quote_details="AED 12,000 excl. VAT",
                   quote_sent_at=time.time(), quote_valid_until=today_local().isoformat())
    db.get_or_create_lead("whatsapp", "971501238888", name="Mira", stage="awaiting_price")
    scheduler.ensure_digest_scheduled()
    [job] = db.pending_jobs(kind="daily_digest")
    await scheduler.tick(now=job["run_at"] + 1)
    [(_, subject, body)] = channels.of("owner")
    assert subject == "Daily sales digest" and "Hamad" in body and "AED 12,000" in body
    assert body.index("Waiting for your price") < body.index("Mira") < body.index("Hot leads")
    assert body.index("Quotes expiring today") < body.index("Hamad")
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
    assert job["payload"] == {"text": "Hello!", "kind": "reply", "quote_valid_until": None}
    assert len(claude.messages.calls) == 1


def test_owner_whatsapp_is_not_a_price_route(app_env, db, channels):
    client, claude, _ = app_env
    lead = db.get_or_create_lead("whatsapp", "971501110000", name="Sara", stage="awaiting_price",
                                 last_inbound_at=time.time())
    meta_post(client, whatsapp_payload("wamid.o1", "971509998888", f"#{lead['id']} AED 28,000 excl. VAT - all in",
                                       name="Kareem"))
    wait_for(lambda: channels.of("whatsapp_text"))
    [(_, to, body)] = channels.of("whatsapp_text")
    assert to == "971509998888" and "/admin" in body, "the owner is pointed to the dashboard"
    assert claude.messages.calls == []
    saved = db.get_lead(lead["id"])
    assert saved["quote_details"] is None and saved["stage"] == "awaiting_price"
    assert len(db.list_leads()) == 1, "the owner is never treated as a lead"


def test_owner_email_reply_is_not_a_price_route(app_env, db, channels):
    client, claude, _ = app_env
    lead = db.get_or_create_lead("email", "buyer@corp.ae", email="buyer@corp.ae", name="Ahmed",
                                 stage="awaiting_price")
    response = client.post("/webhooks/email?token=mail-token", json={
        "From": "Owner <owner@example.com>",
        "Subject": f"Re: [EchoLight sales] [Lead #{lead['id']}] Price needed: Ahmed",
        "TextBody": "AED 15,500 excl. VAT, conference audio and LED\n\nOn Mon, bot wrote:\n> Price needed",
        "MessageID": "owner-1"})
    assert response.json()["ignored"]
    time.sleep(0.1)
    assert claude.messages.calls == [] and channels.sent == []
    assert db.get_lead(lead["id"])["quote_details"] is None
    assert len(db.list_leads()) == 1


def test_owner_sends_price_from_dashboard(app_env, db, channels):
    client, claude, _ = app_env
    lead = db.get_or_create_lead("whatsapp", "971501117777", name="Laila", stage="awaiting_price",
                                 last_inbound_at=time.time())
    page = client.get(f"/admin/leads/{lead['id']}", auth=ADMIN)
    assert "Give the price" in page.text and "name='amount'" in page.text and "excluding VAT" in page.text
    url = f"/admin/leads/{lead['id']}/price"
    form = {"details": "AED 9,500 excl. VAT - uplighting for 12 Dec 2026", "amount": "9,000"}
    assert client.post(url, data=form).status_code == 401
    assert client.post(url, data=form, auth=ADMIN, headers={"Origin": "https://evil.example"}).status_code == 403
    bad = client.post(url, data={**form, "amount": "nine thousand"}, auth=ADMIN)
    assert "must be a number" in bad.text and db.get_lead(lead["id"])["quote_details"] is None

    claude.queue(message(text("Laila, your quote is AED 9,500 excl. VAT, valid until Monday.")))
    response = client.post(url, data=form, auth=ADMIN)
    assert "Price sent to Laila" in response.text and "Valid until" in response.text
    assert channels.of("whatsapp_text")[-1][2] == "Laila, your quote is AED 9,500 excl. VAT, valid until Monday."
    saved = db.get_lead(lead["id"])
    assert (saved["quote_aed"], saved["quote_details"]) == (9000, form["details"]), "the amount field wins"

    # Without an amount, the figure next to AED is used, never the year.
    claude.queue(message(text("Updated quote: AED 28,000 excl. VAT.")))
    client.post(url, data={"details": "Dec 2026 gala, AED 28,000 excl. VAT"}, auth=ADMIN)
    assert db.get_lead(lead["id"])["quote_aed"] == 28000


async def test_price_reminders_continue_daily_until_priced(db, channels, settings):
    from salesbot.agent import SalesAgent
    from salesbot.scheduler import Scheduler

    scheduler = Scheduler(db, SalesAgent(db, channels, FakeClient()))
    lead = db.get_or_create_lead("whatsapp", "971501236666", name="Omar", stage="awaiting_price",
                                 price_requested_at=time.time() - 3 * 3600)
    assert await scheduler.remind_price(lead["id"])
    [(_, subject, body)] = channels.of("owner")
    assert subject == f"[Lead #{lead['id']}] Reminder: Omar has waited 3h for a price"
    assert "/admin/leads/" in body and "Replies to this email are not read" in body

    # The 3h and 24h reminders, then one a day for as long as nobody has priced it.
    now = datetime(2026, 10, 12, 12, 0, tzinfo=settings.timezone).timestamp()
    db.schedule_job("price_reminder", now - 60, lead["id"])
    db.schedule_job("price_reminder", now + 21 * 3600, lead["id"])
    await scheduler.tick(now=now)
    assert len(db.pending_jobs(lead["id"], "price_reminder")) == 1, "the 24h reminder is still to come"
    later = now + 22 * 3600
    await scheduler.tick(now=later)
    [daily] = db.pending_jobs(lead["id"], "price_reminder")
    assert round((daily["run_at"] - later) / 3600) == 24
    assert len(channels.of("owner")) == 3

    db.update_lead(lead["id"], priced_at=time.time(), price_to_send=1)
    await scheduler.tick(now=daily["run_at"] + 1)
    assert len(channels.of("owner")) == 3 and db.pending_jobs(lead["id"], "price_reminder") == []


def test_admin_pause_reply_and_resume(app_env, db, channels):
    client, claude, _ = app_env
    lead = db.get_or_create_lead("whatsapp", "971502220000", name="Reem", last_inbound_at=time.time())
    base = f"/admin/leads/{lead['id']}"
    assert client.post(f"{base}/pause").status_code == 401
    assert "Bot paused" in client.post(f"{base}/pause", auth=ADMIN).text
    page = client.get(base, auth=ADMIN).text
    assert "Resume bot" in page and "bot paused" in page

    meta_post(client, whatsapp_payload("wamid.p1", "971502220000", "I want to talk to a person", name="Reem"))
    wait_for(lambda: channels.of("owner"))
    assert claude.messages.calls == [] and channels.to_customers() == []
    assert "I want to talk to a person" in client.get(base, auth=ADMIN).text

    response = client.post(f"{base}/reply", data={"text": "Hi Reem, this is Kareem."}, auth=ADMIN)
    assert "Sent to Reem." in response.text
    assert channels.of("whatsapp_text") == [("whatsapp_text", "971502220000", "Hi Reem, this is Kareem.")]
    assert "Sent by the team" in client.get(base, auth=ADMIN).text

    assert "Bot resumed" in client.post(f"{base}/resume", auth=ADMIN).text
    assert db.get_lead(lead["id"])["bot_paused"] == 0

    db.update_lead(lead["id"], last_inbound_at=time.time() - 30 * 3600)
    refused = client.post(f"{base}/reply", data={"text": "Hello again"}, auth=ADMIN)
    assert "Not sent" in refused.text and "24 hours" in refused.text


def test_admin_stage_buttons(app_env, db):
    client, _, _ = app_env
    lead = db.get_or_create_lead("whatsapp", "971502230000", name="Saif", stage="booked", marketing_opt_in=1)
    base = f"/admin/leads/{lead['id']}"
    page = client.get(base, auth=ADMIN).text
    assert "Deposit received" in page and "Event done / balance received" in page
    client.post(f"{base}/stage", data={"stage": "confirmed"}, auth=ADMIN)
    assert db.get_lead(lead["id"])["stage"] == "confirmed"
    done = client.post(f"{base}/stage", data={"stage": "completed"}, auth=ADMIN)
    assert "review request will go out" in done.text
    assert db.get_lead(lead["id"])["stage"] == "completed" and db.pending_jobs(lead["id"], "review_request")
    assert "Unknown stage" in client.post(f"{base}/stage", data={"stage": "booked"}, auth=ADMIN).text
    client.post(f"{base}/stage", data={"stage": "lost"}, auth=ADMIN)
    assert db.pending_jobs(lead["id"], "review_request") == []
