# EchoLight sales agent

A Claude-powered salesperson that works on EchoLight's own channels around the clock. It answers every enquiry,
qualifies the event, recommends services, gets the price from you and passes it on, books calls and site visits,
follows up, asks for
reviews and referrals after the event, and sends the owner a daily pipeline digest.

## What it does, channel by channel

| Channel | How leads arrive | What the agent does |
|---|---|---|
| WhatsApp | Customer messages +971 56 722 0533 (WhatsApp Cloud API) | Replies in their language and dialect, reads photos of venues, and handles voice notes by asking for text |
| Instagram | DMs, plus comments on posts and reels containing a keyword (`عرض`, `سعر`, `price`...) | Replies to DMs. Answers keyword comments with a private DM, so a reel CTA like "comment عرض" turns into a conversation |
| Email | Mail to sales@ forwarded by your provider's inbound webhook | Replies by email and can send a written proposal summary |
| Phone | Calls to a Twilio number (or your number forwarded to it) | Rings the team first if configured. If nobody answers, it plays a short bilingual message and starts a WhatsApp conversation with the caller |
| Website | Chat bubble on echolight.ae (one script tag) | Live chat in English or Arabic. It asks for an email or WhatsApp number so it can follow up |

**The sales process the agent follows:** greet → understand the event (type, date, venue, guests, indoor/outdoor,
services, name) → recommend services with matching past work → ask you for the price and tell the customer the team is
preparing their quote → pass your price on word for word → book a call or site visit → mark "booked" and alert you →
review and referral request the day after the event.

## How pricing works

Every project is priced by you. The agent never sets, estimates, rounds or discounts a price.

1. When it has the details (event, date, venue, guests, services), it emails you
   **"[Lead #12] Price needed: Sara"** with the full requirements, and tells the customer the team is preparing their
   quote.
2. You send the price in any of three ways:
   - **Reply to that email** with the price and what it includes, e.g.
     `AED 28,000 incl. VAT - lighting, 6x3m LED wall, setup and 2 technicians`
   - **WhatsApp the bot number from your personal phone:** `#12 AED 28,000 incl. VAT - lighting, ...`
   - **The dashboard:** open the lead and use "Send the price".
3. The agent sends your price to the customer exactly as you wrote it, asks whether they want to go ahead, and resumes
   follow-ups. You get a confirmation back.

**Things to know:**
- If the customer last wrote more than 24 hours ago, WhatsApp only allows a pre-approved template. The agent sends
  "your quote is ready, reply to see it" and gives the price the moment they reply.
- While a customer waits for your price, the agent sends them no follow-ups. Instead it reminds you after 3 and 24
  hours, and the daily digest lists everyone waiting.
- When a customer negotiates, the agent asks you again and tells them it is checking. It never agrees to a discount
  itself.

**Automatic follow-ups:** if a lead goes quiet, it sends three follow-ups (20 hours, 3 days and 7 days after the last
message). It never sends between 22:00 and 09:00 UAE time, and it stops immediately when the customer replies, books,
declines, or asks to stop. Leads who agreed to receive offers get a check-in 60 days later.

**What you receive:** an email for every quote, booking, "ready to book" and escalation, a daily digest at 09:00, and a
dashboard at `/admin` with every lead, its stage, quote, bookings and full message history.

## What the agent will not do on its own

Every rule below is a guardrail against losing money or getting your WhatsApp number banned:

- **It never sets a price** (see above).
- **It only states facts from `knowledge/business.md`.** Policies such as deposit, cancellation, lead time and VAT
  handling are listed under "To confirm". Fill those in and the agent answers them itself.
- **It never confirms date availability.** It notes the date and says the team confirms it with the quote.
- **It does not cold-message strangers.** WhatsApp only allows business-initiated messages to people who contacted
  you or opted in, using approved templates. Mass cold outreach gets numbers banned, and UAE data-protection law
  requires consent for marketing. New leads come in through your reels, ads, site and calls, and the agent converts
  them.
- **It escalates to you when needed:** when a customer asks for a person, complains, or wants something outside your
  services. The conversation continues while you're alerted.

## Set up (one time, about 2-3 hours)

1. **Fill in the knowledge file.** Complete the "To confirm" list in `knowledge/business.md`. This file controls
   every fact the agent states.
2. **Get a Claude API key** at console.anthropic.com and set `ANTHROPIC_API_KEY`.
3. **Host the service** anywhere that runs Docker with a public HTTPS URL and a persistent disk (Railway, Render,
   Fly.io, or a small VPS):
   ```bash
   docker build -t echolight-sales .
   docker run -d --env-file .env -v echolight-data:/data -p 8000:8000 echolight-sales
   ```
   Set `PUBLIC_BASE_URL` to the HTTPS URL and `ADMIN_TOKEN` to a long random password.
4. **WhatsApp (Meta Business Suite → WhatsApp Cloud API):**
   - Move +971 56 722 0533 to the Cloud API (or add a new number). Note that a number on the Cloud API can no longer
     be used in the WhatsApp Business phone app.
   - Create a System User token (`WHATSAPP_TOKEN`) and copy the phone number ID.
   - Webhook URL: `https://YOUR-HOST/webhooks/meta`. Verify token: `META_VERIFY_TOKEN`. Subscribe to `messages`.
   - Copy the App Secret to `META_APP_SECRET`.
   - Submit the templates below for approval and put their names in `.env`.
   - Set `OWNER_WHATSAPP` to your **personal** number, not the business number (that one now belongs to the bot).
     Messages from it that start with `#<lead number>` are read as prices.
5. **Instagram:** connect the @echolightae professional account to the same Meta app, grant
   `instagram_manage_messages` and `instagram_manage_comments`, and subscribe the webhook to `messages` and
   `comments`.
6. **Email:** point an inbound-email webhook (Postmark, SendGrid Inbound Parse, Mailgun routes) at
   `https://YOUR-HOST/webhooks/email?token=EMAIL_INBOUND_TOKEN`, and fill in the SMTP settings for sending.
7. **Phone:** buy a UAE number on Twilio (or forward calls to it). Set its voice webhook to
   `https://YOUR-HOST/webhooks/voice`. Set `CALL_FORWARD_NUMBER` if the team should be rung first.
8. **Website:** add one line before `</body>` on echolight.ae and /ar-/:
   ```html
   <script src="https://YOUR-HOST/widget.js" defer></script>
   ```

### WhatsApp templates to submit

Each template has one variable, `{{1}}`: the customer's first name, or for `owner_alert` the alert title. The
`owner_alert` template only matters if you want WhatsApp alerts even when you haven't messaged the bot in the last
24 hours; email alerts always work. Submit them in Arabic, and in English
too if you set up a second language.

| Name | Category | Arabic | English |
|---|---|---|---|
| `followup` | Marketing | مرحباً {{1}}، حابين نطمن إذا عندك أي سؤال عن فعاليتك. فريق إيكو لايت جاهز يساعدك بالإضاءة والشاشات والصوت. | Hi {{1}}, just checking whether you have any questions about your event. The EchoLight team is here to help with lighting, LED and sound. |
| `missed_call` | Utility | مرحباً {{1}}، فاتتنا مكالمتك. كيف فينا نساعدك بفعاليتك؟ | Hi {{1}}, sorry we missed your call. How can we help with your event? |
| `review` | Marketing | شكراً {{1}} لاختيارك إيكو لايت! إذا عجبتك الفعالية، تقييمك على جوجل بيفرق معنا كتير: [your Google review link] | Thank you for choosing EchoLight, {{1}}! If you enjoyed the event, a Google review means a lot to us: [your Google review link] |
| `quote_ready` | Utility | مرحباً {{1}}، عرض السعر لفعاليتك صار جاهز. رد على هالرسالة وبنرسلك التفاصيل. | Hi {{1}}, your event quote is ready. Reply to this message and we'll send you the details. |
| `owner_alert` (sent to you) | Utility | تنبيه من بوت المبيعات: {{1}} | EchoLight sales bot: {{1}} |
| `reactivation` | Marketing | مرحباً {{1}}، عندك فعالية جاية؟ إيكو لايت جاهزة بأحدث الإضاءة والشاشات والليزر. رد علينا وبنساعدك. | Hi {{1}}, planning another event? EchoLight is ready with the latest lighting, LED and lasers. Reply and we'll help. |

Replace `[your Google review link]` with the link from your Google Business Profile ("Ask for reviews").

## Running costs (estimate)

- **Claude:** with the default model, a typical 10-message enquiry costs roughly USD 0.10-0.40. To trade some quality
  for cost, set `CLAUDE_EFFORT=low`.
- **WhatsApp:** replies within 24 hours of the customer's message are free. Templates are charged per message by Meta.
- **Twilio:** a UAE number plus per-minute call charges.
- **Hosting:** about USD 5-20 a month.

## Develop

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest
.venv/bin/uvicorn salesbot.app:create_app --factory --reload
```

| Path | Contents |
|---|---|
| `salesbot/agent.py` | The Claude conversation loop, delivery rules (24-hour window, templates), follow-up scheduling |
| `salesbot/prompts.py` | The agent's instructions |
| `salesbot/tools.py` | Lead saving, price requests, booking, stages, escalation, consent, email proposals |
| `salesbot/app.py` | Webhooks, website chat, dashboard, your price replies (email, WhatsApp, dashboard) |
| `salesbot/scheduler.py` | Follow-ups, price reminders, review requests, reactivation, retries, daily digest |

The agent uses `claude-opus-5-5` with adaptive thinking. It opts into server-side refusal fallbacks
(`fallbacks: "default"`), so a declined request is retried on another model automatically. If a reply still fails,
the message is retried and you are alerted.
