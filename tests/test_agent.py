import time
from datetime import datetime, timedelta

import anthropic
import httpx
import pytest

from conftest import FakeClient, assert_valid_message_order, configure, message, text, tool
from salesbot.agent import SalesAgent, TeamActionError
from salesbot.tools import format_date, today_local, valid_until_from


def make_agent(db, channels, *responses):
    client = FakeClient(*responses)
    return SalesAgent(db, channels, client), client


def quoted_lead(db, wa_id, valid_days_from_today, **fields):
    """A lead who received a quote; valid_days_from_today < 0 means it has expired."""
    lead = db.get_or_create_lead("whatsapp", wa_id, name="Hamad")
    valid = today_local() + timedelta(days=valid_days_from_today)
    return db.update_lead(lead["id"], stage="quoted", quote_details="AED 20,000 excl. VAT", quote_aed=20000,
                          quote_sent_at=time.time() - 86400, quote_valid_until=valid.isoformat(),
                          last_inbound_at=time.time() - 3600, **fields)


async def test_inbound_collects_details_and_asks_team_for_price(db, channels):
    agent, client = make_agent(
        db, channels,
        message(
            tool("save_lead_details", {"name": "Sara", "event_type": "wedding", "event_date": "2026-12-12",
                                       "guest_count": 300, "services": ["stage lighting", "LED wall"]}),
            tool("request_price", {"requirements": "Wedding 12 Dec, 300 guests, Jumeirah Saadiyat, lighting + LED"}),
        ),
        message(text("Thank you Sara! Our team is preparing your quote and will share it shortly.")),
    )
    lead = db.get_or_create_lead("whatsapp", "971500000001")

    reply = await agent.handle_inbound(lead["id"], [text("Hi, wedding 12 Dec, 300 guests, need lights and LED")])

    assert reply.startswith("Thank you Sara!")
    assert channels.of("whatsapp_text") == [("whatsapp_text", "971500000001", reply)]
    saved = db.get_lead(lead["id"])
    assert (saved["name"], saved["stage"], saved["guest_count"]) == ("Sara", "awaiting_price", 300)
    [(_, subject, body)] = channels.of("owner")
    assert subject.startswith(f"[Lead #{lead['id']}] Price needed: Sara")
    assert "Jumeirah Saadiyat" in body and f"/admin/leads/{lead['id']}" in body, "the alert links the price form"
    assert f"#{lead['id']} AED" not in body and "Replies to this email are not read" in body
    assert "excl. VAT" in body and "incl. VAT" not in body
    # The customer is waiting on us: no customer follow-ups, but the owner gets reminders.
    assert db.pending_jobs(lead["id"], "followup") == []
    assert len(db.pending_jobs(lead["id"], "price_reminder")) == 2
    # The second call carries the tool results back, and the conversation is well formed.
    second = client.messages.calls[1]
    assert_valid_message_order(second["messages"])
    results = second["messages"][-1]["content"]
    assert [r["type"] for r in results] == ["tool_result", "tool_result"]
    assert not any(r["is_error"] for r in results)
    # Request shape: default model, adaptive thinking, refusal fallback opt-in, caching, no price tool.
    assert second["model"] == "claude-opus-5-5"
    assert second["fallbacks"] == "default" and second["betas"] == ["server-side-fallback-2026-07-01"]
    assert second["thinking"] == {"type": "adaptive"}
    assert second["cache_control"] == {"type": "ephemeral"}
    assert "estimate_quote" not in {t["name"] for t in second["tools"]}


async def test_price_request_warns_about_same_date(db, channels):
    agent, _ = make_agent(
        db, channels,
        message(tool("save_lead_details", {"event_date": "2026-12-12"}),
                tool("request_price", {"requirements": "Gala 12 Dec"})),
        message(text("The team is preparing your quote.")),
    )
    other = db.get_or_create_lead("whatsapp", "971500000090", name="Mona", event_date="2026-12-12", stage="booked")
    db.get_or_create_lead("whatsapp", "971500000091", name="Lost one", event_date="2026-12-12", stage="lost")
    lead = db.get_or_create_lead("whatsapp", "971500000092", name="Ali")
    await agent.handle_inbound(lead["id"], [text("Gala on 12 Dec")])
    [(_, _, body)] = channels.of("owner")
    assert f"Same date as: #{other['id']} Mona (booked)" in body and "Lost one" not in body


async def test_present_price_inside_window(db, channels):
    agent, client = make_agent(
        db, channels,
        message(tool("request_price", {"requirements": "gala dinner"})),
        message(text("The team is preparing your quote.")),
        message(text("Your quote: AED 28,000 excl. VAT (+5% VAT) for lighting, LED wall and setup. Shall we go ahead?")),
    )
    lead = db.get_or_create_lead("whatsapp", "971500000020", name="Hamad")
    await agent.handle_inbound(lead["id"], [text("Gala dinner, 200 guests, need lighting and LED")])

    status = await agent.present_price(lead["id"], "AED 28,000 excl. VAT - lighting, LED wall, setup", 28000)

    assert status == "sent"
    assert channels.of("whatsapp_text")[-1][2].startswith("Your quote: AED 28,000")
    request = client.messages.calls[-1]
    assert_valid_message_order(request["messages"])
    context = request["messages"][-1]["content"]
    assert "AED 28,000 excl. VAT - lighting, LED wall, setup" in context
    valid_until = valid_until_from()
    assert f"valid until {format_date(valid_until)}" in context, "the price message states the validity date"
    saved = db.get_lead(lead["id"])
    assert (saved["stage"], saved["quote_aed"], saved["price_to_send"]) == ("quoted", 28000, 0)
    assert saved["quote_valid_until"] == valid_until.isoformat() and saved["quote_sent_at"]
    assert db.pending_jobs(lead["id"], "price_reminder") == []
    # Follow-ups resume: day 1, the expiry day at 10:00 ("valid until today"), and day 7.
    jobs = sorted(db.pending_jobs(lead["id"], "followup"), key=lambda j: j["payload"]["step"])
    assert [j["payload"]["step"] for j in jobs] == [1, 2, 3]
    expiry_check = datetime.fromtimestamp(jobs[1]["run_at"], agent_tz())
    assert (expiry_check.date(), expiry_check.hour) == (valid_until, 10)


def agent_tz():
    from salesbot import config

    return config.settings.timezone


async def test_present_price_outside_window_waits_for_customer(db, channels):
    agent, client = make_agent(
        db, channels,
        message(tool("request_price", {"requirements": "car launch"})),
        message(text("The team is preparing your quote.")),
    )
    lead = db.get_or_create_lead("whatsapp", "971500000021", name="Noor Saleh")
    await agent.handle_inbound(lead["id"], [text("Car launch next month")])
    db.update_lead(lead["id"], last_inbound_at=time.time() - 30 * 3600)

    status = await agent.present_price(lead["id"], "AED 45,000 + VAT, laser show and LED", 45000)

    assert status == "queued"
    assert len(client.messages.calls) == 2, "no free-text message allowed outside 24h"
    assert channels.of("whatsapp_template") == [
        ("whatsapp_template", "971500000021", "quote_ready_v1", ["Noor"], "ar")]
    saved = db.get_lead(lead["id"])
    assert saved["price_to_send"] == 1 and saved["quote_sent_at"] is None, "not sent yet, so no validity yet"
    # When the customer replies, the agent is given the price, and only then does the quote count as sent.
    client.queue(message(text("Here's your quote: AED 45,000 + VAT for the laser show and LED.")))
    await agent.handle_inbound(lead["id"], [text("Yes please share")])
    context = client.messages.calls[-1]["messages"][-1]["content"]
    assert "AED 45,000 + VAT, laser show and LED" in context and "valid until" in context
    saved = db.get_lead(lead["id"])
    assert (saved["stage"], saved["price_to_send"]) == ("quoted", 0)
    assert saved["quote_valid_until"] == valid_until_from().isoformat()


async def test_no_followups_while_awaiting_price(db, channels):
    agent, _ = make_agent(db, channels, message(text("one")))
    lead = db.get_or_create_lead("whatsapp", "971500000022")
    db.update_lead(lead["id"], stage="awaiting_price")
    await agent.handle_inbound(lead["id"], [text("any update?")])
    assert db.pending_jobs(lead["id"], "followup") == []
    await agent.run_followup(lead["id"], 1)
    assert len(channels.of("whatsapp_text")) == 1


async def test_system_prompt_is_stable_and_has_facts(db, channels):
    agent, client = make_agent(db, channels, message(text("a")), message(text("b")))
    lead = db.get_or_create_lead("whatsapp", "971500000002")
    await agent.handle_inbound(lead["id"], [text("hello")])
    await agent.handle_inbound(lead["id"], [text("again")])
    first, second = client.messages.calls
    assert first["system"] == second["system"], "a changing system prompt would break the cache"
    assert "Abu Dhabi" in first["system"] and "request_price" in first["system"]
    assert "Minimum notice" not in first["system"], "HTML comments in business.md are stripped"
    assert_valid_message_order(second["messages"])


def test_prompt_never_volunteers_ai_and_is_honest_when_asked(db, channels):
    agent, _ = make_agent(db, channels)
    system = agent.system_prompt
    assert "virtual assistant" not in system and "copied on the conversation" not in system
    assert "Never introduce yourself as an assistant, a bot, an AI" in system
    assert "never claim to be human and never deny being automated" in system
    assert "Would you like Kareem to call you?" in system and "تحب كريم يتصل فيك؟" in system
    assert "escalate_to_team" in system and "not sincere questions" in system
    assert "never promise a time" in system
    assert "valid for 7 days" in system and "valid until" in system


async def test_new_message_resets_followups(db, channels):
    agent, _ = make_agent(db, channels, message(text("one")), message(text("two")))
    lead = db.get_or_create_lead("whatsapp", "971500000003")
    await agent.handle_inbound(lead["id"], [text("hi")])
    await agent.handle_inbound(lead["id"], [text("still there?")])
    assert len(db.pending_jobs(lead["id"], "followup")) == 3


async def test_followup_inside_window_is_written_by_claude(db, channels):
    agent, client = make_agent(db, channels, message(text("first reply")), message(text("Quick check-in!")))
    lead = db.get_or_create_lead("whatsapp", "971500000004")
    await agent.handle_inbound(lead["id"], [text("hello")])

    await agent.run_followup(lead["id"], step=1)

    assert channels.of("whatsapp_text")[-1][2] == "Quick check-in!"
    request = client.messages.calls[-1]
    assert_valid_message_order(request["messages"])
    assert "Follow-up 1 of 3" in request["messages"][-1]["content"]


async def test_followup_outside_window_uses_approved_template(db, channels):
    agent, client = make_agent(db, channels, message(text("first reply")))
    lead = db.get_or_create_lead("whatsapp", "971500000005", name="Omar Khalid")
    await agent.handle_inbound(lead["id"], [text("hello")])
    db.update_lead(lead["id"], last_inbound_at=time.time() - 30 * 3600)

    await agent.run_followup(lead["id"], step=2)

    assert channels.of("whatsapp_template") == [("whatsapp_template", "971500000005", "followup_v1", ["Omar"], "ar")]
    assert len(client.messages.calls) == 1, "no Claude call when only a template can be sent"
    # The agent hears about the template on its next turn.
    client.queue(message(text("Welcome back")))
    await agent.handle_inbound(lead["id"], [text("yes still interested")])
    assert "followup_v1" in client.messages.calls[-1]["messages"][-1]["content"]
    assert db.get_lead(lead["id"])["agent_notes"] == ""


async def test_template_language_follows_the_lead(db, channels, monkeypatch):
    agent, _ = make_agent(db, channels)
    arabic = db.get_or_create_lead("whatsapp", "971500000060", language="ar")
    english = db.get_or_create_lead("whatsapp", "971500000061", name="Omar Khalid", language="en")
    unknown = db.get_or_create_lead("whatsapp", "971500000062")

    for lead in (arabic, english, unknown):
        await agent.send_template(lead, "followup")
    # Default language is Arabic: an unknown name reads "مرحباً بك"، never "مرحباً there".
    assert [s[3:] for s in channels.of("whatsapp_template")] == [(["بك"], "ar"), (["Omar"], "ar"), (["بك"], "ar")]

    configure(monkeypatch, WA_TEMPLATE_DEFAULT_LANGUAGE="en")
    channels.sent.clear()
    for lead in (arabic, english, unknown):
        await agent.send_template(lead, "followup")
    assert [s[3:] for s in channels.of("whatsapp_template")] == [(["بك"], "ar"), (["Omar"], "en"), (["there"], "en")]
    notes = db.get_lead(arabic["id"])["agent_notes"]
    assert "followup_v1" in notes


async def test_no_reply_marker_sends_nothing(db, channels):
    agent, _ = make_agent(db, channels, message(text("<no_reply>")))
    lead = db.get_or_create_lead("whatsapp", "971500000006")
    assert await agent.handle_inbound(lead["id"], [text("thanks")]) is None
    assert channels.of("whatsapp_text") == []


async def test_opt_out_stops_everything(db, channels):
    agent, _ = make_agent(
        db, channels,
        message(tool("set_contact_preferences", {"do_not_contact": True})),
        message(text("Understood, we won't message you again.")),
    )
    lead = db.get_or_create_lead("whatsapp", "971500000007")
    await agent.handle_inbound(lead["id"], [text("stop messaging me")])
    assert db.get_lead(lead["id"])["do_not_contact"] == 1
    assert db.pending_jobs(lead["id"]) == []
    await agent.run_followup(lead["id"], 1)
    await agent.run_template_touch(lead["id"], "reactivation")
    assert len(channels.to_customers()) == 1


async def test_booked_stops_followups_but_review_waits_for_completed(db, channels):
    agent, _ = make_agent(
        db, channels,
        message(tool("save_lead_details", {"event_date": "2026-11-20"}),
                tool("set_stage", {"stage": "booked", "reason": "customer confirmed"})),
        message(text("Wonderful! The team will send the final proposal today.")),
    )
    lead = db.get_or_create_lead("whatsapp", "971500000008", marketing_opt_in=1)
    await agent.handle_inbound(lead["id"], [text("Let's go ahead")])
    assert db.pending_jobs(lead["id"], "followup") == []
    assert db.pending_jobs(lead["id"], "review_request") == [], "a verbal yes is not a finished event"
    assert any("ready to book" in o[1] for o in channels.of("owner"))
    # A review request scheduled by mistake is still checked at send time.
    await agent.run_template_touch(lead["id"], "review_request")
    assert channels.of("whatsapp_template") == []

    agent.team_set_stage(lead["id"], "confirmed")
    assert db.get_lead(lead["id"])["stage"] == "confirmed"
    message_to_team = agent.team_set_stage(lead["id"], "completed")
    assert "review request will go out" in message_to_team
    [review] = db.pending_jobs(lead["id"], "review_request")
    assert review["run_at"] > time.time()
    await agent.run_template_touch(lead["id"], "review_request")
    assert channels.of("whatsapp_template")[-1][2] == "review_v1"


async def test_no_review_or_reactivation_without_opt_in(db, channels):
    agent, _ = make_agent(db, channels)
    lead = db.get_or_create_lead("whatsapp", "971500000030", name="Rana")
    message_to_team = agent.team_set_stage(lead["id"], "completed")
    assert "Ask for a review yourself" in message_to_team
    assert db.pending_jobs(lead["id"], "review_request") == []
    await agent.run_template_touch(lead["id"], "review_request")
    await agent.run_template_touch(lead["id"], "reactivation")
    assert channels.to_customers() == [], "marketing templates need marketing_opt_in"
    # The follow-up is a Utility "about your enquiry" message, allowed for people who contacted us.
    db.update_lead(lead["id"], stage="qualifying", last_inbound_at=time.time() - 30 * 3600)
    await agent.run_followup(lead["id"], 1)
    assert channels.of("whatsapp_template") == [("whatsapp_template", "971500000030", "followup_v1", ["Rana"], "ar")]


async def test_lost_cancels_review_and_followups(db, channels):
    agent, _ = make_agent(
        db, channels,
        message(tool("set_stage", {"stage": "lost", "reason": "cancelled the event"})),
        message(text("Sorry to hear that. We're here whenever you need us.")),
    )
    lead = db.get_or_create_lead("whatsapp", "971500000031", marketing_opt_in=1, stage="booked")
    db.schedule_job("review_request", time.time() + 86400, lead["id"])
    db.schedule_job("price_reminder", time.time() + 86400, lead["id"])
    await agent.handle_inbound(lead["id"], [text("We cancelled the event, sorry")])
    assert db.get_lead(lead["id"])["stage"] == "lost"
    assert db.pending_jobs(lead["id"], "review_request") == []
    assert db.pending_jobs(lead["id"], "price_reminder") == []
    assert db.pending_jobs(lead["id"], "followup") == []
    assert len(db.pending_jobs(lead["id"], "reactivation")) == 1, "opted in, so a check-in in 60 days"
    # Even a review job that slipped through is re-checked at send time.
    await agent.run_template_touch(lead["id"], "review_request")
    assert channels.of("whatsapp_template") == []


async def test_expiry_day_followup_reminds_and_expired_quote_offers_refresh(db, channels):
    agent, client = make_agent(db, channels, message(text("Your quote is valid until today!")),
                               message(text("Shall the team refresh your quote?")))
    today = quoted_lead(db, "971500000040", 0)
    await agent.run_followup(today["id"], 2)
    instruction = client.messages.calls[-1]["messages"][-1]["content"]
    assert "validity date today" in instruction and "VAT" in instruction

    expired = quoted_lead(db, "971500000041", -2)
    await agent.run_followup(expired["id"], 3)
    instruction = client.messages.calls[-1]["messages"][-1]["content"]
    assert "expired on" in instruction and "Do not present the old price as valid" in instruction
    assert "refresh the quote" in instruction and "last check-in" in instruction


async def test_cannot_book_on_an_expired_quote(db, channels):
    agent, client = make_agent(
        db, channels,
        message(tool("set_stage", {"stage": "booked", "reason": "wants to go ahead"})),
        message(tool("request_price", {"requirements": "same as before",
                                       "customer_request": "re-confirm the expired quote"})),
        message(text("Great! The team will re-confirm the price and the date for you.")),
    )
    lead = quoted_lead(db, "971500000042", -1)
    await agent.handle_inbound(lead["id"], [text("OK let's book it")])
    first_result = client.messages.calls[1]["messages"][-1]["content"][0]
    assert first_result["is_error"] and "expired" in first_result["content"]
    context = client.messages.calls[0]["messages"][-1]["content"]
    assert "expired on" in context, "the agent is told the quote expired"
    saved = db.get_lead(lead["id"])
    assert saved["stage"] == "awaiting_price"
    assert any("re-confirm the expired quote" in o[2] for o in channels.of("owner"))


async def test_api_error_rolls_back_transcript(db, channels):
    error = anthropic.APIConnectionError(request=httpx.Request("POST", "https://api.anthropic.com"))
    agent, client = make_agent(db, channels, message(text("ok")), error)
    lead = db.get_or_create_lead("whatsapp", "971500000009")
    await agent.handle_inbound(lead["id"], [text("first")])
    before = db.transcript(lead["id"])
    db.append_note(lead["id"], "[a note the agent must still see]")
    with pytest.raises(anthropic.APIConnectionError):
        await agent.handle_inbound(lead["id"], [text("second")])
    assert db.transcript(lead["id"]) == before
    assert db.get_lead(lead["id"])["agent_notes"] == "[a note the agent must still see]", "kept for the retry"
    client.queue(message(text("recovered")))
    assert await agent.handle_inbound(lead["id"], [text("second")]) == "recovered"
    assert_valid_message_order(client.messages.calls[-1]["messages"])
    assert db.get_lead(lead["id"])["agent_notes"] == ""


async def test_refusal_is_not_saved_and_raises(db, channels):
    agent, _ = make_agent(db, channels, message(stop_reason="refusal"))
    lead = db.get_or_create_lead("whatsapp", "971500000010")
    with pytest.raises(Exception, match="declined"):
        await agent.handle_inbound(lead["id"], [text("hello")])
    assert db.transcript(lead["id"]) == []


async def test_tool_error_is_reported_to_claude(db, channels):
    agent, client = make_agent(
        db, channels,
        message(tool("send_email_summary", {"subject": "Proposal", "body": "..."})),
        message(text("Could you share your email?")),
    )
    lead = db.get_or_create_lead("whatsapp", "971500000011")
    await agent.handle_inbound(lead["id"], [text("email me the details")])
    result = client.messages.calls[1]["messages"][-1]["content"][0]
    assert "no email address" in result["content"]
    assert channels.of("email") == []


async def test_email_lead_gets_free_text_followups(db, channels):
    agent, _ = make_agent(db, channels, message(text("Thanks for your email")), message(text("Following up")))
    lead = db.get_or_create_lead("email", "client@corp.ae", email="client@corp.ae")
    await agent.handle_inbound(lead["id"], [text("Subject: Gala dinner\n\nPrice for lighting?")])
    await agent.run_followup(lead["id"], 3)
    assert [e[3] for e in channels.of("email")] == ["Thanks for your email", "Following up"]


# Human takeover


async def test_paused_lead_is_logged_not_answered(db, channels):
    agent, client = make_agent(db, channels)  # any Claude call would fail the test
    lead = db.get_or_create_lead("whatsapp", "971500000050", name="Dana")
    db.schedule_job("followup", time.time() + 3600, lead["id"], {"step": 1})
    agent.pause(lead["id"])
    assert db.pending_jobs(lead["id"], "followup") == []

    assert await agent.handle_inbound(lead["id"], [text("Can I speak to Kareem please?")]) is None
    assert client.messages.calls == [] and channels.to_customers() == []
    [(_, subject, body)] = channels.of("owner")
    assert "bot paused" in subject and "Can I speak to Kareem please?" in body and "/admin/leads/" in body
    assert db.pending_jobs(lead["id"], "followup") == []
    await agent.run_followup(lead["id"], 1)
    assert channels.to_customers() == []

    # The team answers on the same number.
    assert await agent.team_reply(lead["id"], "Hi Dana, Kareem here. I'll call you in 10 minutes.") == "Sent to Dana."
    assert channels.of("whatsapp_text") == [
        ("whatsapp_text", "971500000050", "Hi Dana, Kareem here. I'll call you in 10 minutes.")]
    assert db.outbound_messages(lead["id"])[-1]["sender"] == "team"

    # Back to the bot: it reads what happened while it was paused.
    agent.resume(lead["id"])
    client.queue(message(text("Thanks Dana! Anything else I can help with?")))
    await agent.handle_inbound(lead["id"], [text("Thanks, spoke to him")])
    context = client.messages.calls[-1]["messages"][-1]["content"]
    assert "Can I speak to Kareem please?" in context
    assert "Kareem here. I'll call you in 10 minutes." in context and "handed the conversation back" in context


async def test_team_reply_respects_24_hour_rule(db, channels):
    agent, _ = make_agent(db, channels)
    lead = db.get_or_create_lead("whatsapp", "971500000051", last_inbound_at=time.time() - 30 * 3600)
    with pytest.raises(TeamActionError, match="24 hours"):
        await agent.team_reply(lead["id"], "Hello?")
    never_wrote = db.get_or_create_lead("whatsapp", "971500000052")
    with pytest.raises(TeamActionError, match="never written"):
        await agent.team_reply(never_wrote["id"], "Hello?")
    visitor = db.get_or_create_lead("webchat", "session-abcdef")
    with pytest.raises(TeamActionError, match="no email"):
        await agent.team_reply(visitor["id"], "Hello?")
    assert channels.to_customers() == []
    # Email has no window.
    mail = db.get_or_create_lead("email", "a@corp.ae", email="a@corp.ae")
    await agent.team_reply(mail["id"], "Dear Ahmed, here are the details.")
    assert channels.of("email")[0][1] == "a@corp.ae"


async def test_team_reply_with_price_starts_quote_validity(db, channels):
    agent, _ = make_agent(db, channels)
    lead = db.get_or_create_lead("whatsapp", "971500000053", name="Huda", stage="awaiting_price",
                                 last_inbound_at=time.time(), price_requested_at=time.time() - 3600)
    db.schedule_job("price_reminder", time.time() + 3600, lead["id"])
    reply = await agent.team_reply(lead["id"], "AED 12,000 excl. VAT, valid for 7 days", gives_price=True)
    assert f"Quote valid until {format_date(valid_until_from())}" in reply
    saved = db.get_lead(lead["id"])
    assert (saved["stage"], saved["quote_valid_until"]) == ("quoted", valid_until_from().isoformat())
    assert db.pending_jobs(lead["id"], "price_reminder") == []
    assert len(db.pending_jobs(lead["id"], "followup")) == 3
