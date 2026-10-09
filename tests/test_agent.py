import time

import anthropic
import httpx
import pytest

from conftest import FakeClient, assert_valid_message_order, message, text, tool
from salesbot.agent import SalesAgent


def make_agent(db, channels, *responses):
    client = FakeClient(*responses)
    return SalesAgent(db, channels, client), client


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
    assert "Jumeirah Saadiyat" in body and f"#{lead['id']} AED" in body, "the alert explains how to reply"
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


async def test_present_price_inside_window(db, channels):
    agent, client = make_agent(
        db, channels,
        message(tool("request_price", {"requirements": "gala dinner"})),
        message(text("The team is preparing your quote.")),
        message(text("Your quote: AED 28,000 incl. VAT for lighting, LED wall and setup. Shall we go ahead?")),
    )
    lead = db.get_or_create_lead("whatsapp", "971500000020", name="Hamad")
    await agent.handle_inbound(lead["id"], [text("Gala dinner, 200 guests, need lighting and LED")])

    status = await agent.present_price(lead["id"], "AED 28,000 incl. VAT - lighting, LED wall, setup", 28000)

    assert status == "sent"
    assert channels.of("whatsapp_text")[-1][2].startswith("Your quote: AED 28,000")
    request = client.messages.calls[-1]
    assert_valid_message_order(request["messages"])
    assert "AED 28,000 incl. VAT - lighting, LED wall, setup" in request["messages"][-1]["content"]
    saved = db.get_lead(lead["id"])
    assert (saved["stage"], saved["quote_aed"]) == ("quoted", 28000)
    assert db.pending_jobs(lead["id"], "price_reminder") == []
    assert len(db.pending_jobs(lead["id"], "followup")) == 3, "follow-ups resume once the price is out"


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
    assert channels.of("whatsapp_template") == [("whatsapp_template", "971500000021", "quote_ready_v1", ["Noor"])]
    # When the customer replies, the agent is given the price.
    client.queue(message(text("Here's your quote: AED 45,000 + VAT for the laser show and LED.")))
    await agent.handle_inbound(lead["id"], [text("Yes please share")])
    context = client.messages.calls[-1]["messages"][-1]["content"]
    assert "AED 45,000 + VAT, laser show and LED" in context


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
    assert "follow-up 1 of 3" in request["messages"][-1]["content"]


async def test_followup_outside_window_uses_approved_template(db, channels):
    agent, client = make_agent(db, channels, message(text("first reply")))
    lead = db.get_or_create_lead("whatsapp", "971500000005", name="Omar Khalid")
    await agent.handle_inbound(lead["id"], [text("hello")])
    db.update_lead(lead["id"], last_inbound_at=time.time() - 30 * 3600)

    await agent.run_followup(lead["id"], step=2)

    assert channels.of("whatsapp_template") == [("whatsapp_template", "971500000005", "followup_v1", ["Omar"])]
    assert len(client.messages.calls) == 1, "no Claude call when only a template can be sent"
    # The agent hears about the template on its next turn.
    client.queue(message(text("Welcome back")))
    await agent.handle_inbound(lead["id"], [text("yes still interested")])
    assert "followup_v1" in client.messages.calls[-1]["messages"][-1]["content"]
    assert db.get_lead(lead["id"])["agent_notes"] == ""


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
    assert len(channels.of("whatsapp_text")) == 1


async def test_booked_schedules_review_request_and_stops_followups(db, channels):
    agent, _ = make_agent(
        db, channels,
        message(tool("save_lead_details", {"event_date": "2026-11-20"}),
                tool("set_stage", {"stage": "booked", "reason": "customer confirmed"})),
        message(text("Wonderful! The team will send the final proposal today.")),
    )
    lead = db.get_or_create_lead("whatsapp", "971500000008")
    await agent.handle_inbound(lead["id"], [text("Let's go ahead")])
    assert db.pending_jobs(lead["id"], "followup") == []
    [review] = db.pending_jobs(lead["id"], "review_request")
    assert review["run_at"] > time.time()

    await agent.run_template_touch(lead["id"], "review_request")
    assert channels.of("whatsapp_template")[-1][2] == "review_v1"


async def test_api_error_rolls_back_transcript(db, channels):
    error = anthropic.APIConnectionError(request=httpx.Request("POST", "https://api.anthropic.com"))
    agent, client = make_agent(db, channels, message(text("ok")), error)
    lead = db.get_or_create_lead("whatsapp", "971500000009")
    await agent.handle_inbound(lead["id"], [text("first")])
    before = db.transcript(lead["id"])
    with pytest.raises(anthropic.APIConnectionError):
        await agent.handle_inbound(lead["id"], [text("second")])
    assert db.transcript(lead["id"]) == before
    client.queue(message(text("recovered")))
    assert await agent.handle_inbound(lead["id"], [text("second")]) == "recovered"
    assert_valid_message_order(client.messages.calls[-1]["messages"])


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
