# EchoLight sales bot

A Claude-powered sales assistant for EchoLight's own channels: WhatsApp, Instagram, email, missed calls and the
website chat. It answers enquiries, collects the event details, asks you for the price and passes it on, books calls
and site visits, follows up, and sends you a daily pipeline digest.

## Status: read this first

- **It is not deployed and does nothing yet.** It needs an Anthropic API key, hosting, and the WhatsApp/Meta,
  Twilio and email setup below. Until then it is frozen code.
- **The CRM is the one system of record.** Leads, prices and stages live in the CRM (`crm/index.html`). This bot keeps
  its own small database and an `/admin` page because it was built first. If you deploy it, connect it to the CRM
  first so the team works in one place; that connection is not built yet.
- **Trial mode is on by default** (`TRIAL_MODE=true`). The bot sends nothing to customers. See below.
- **A live test is required before launch.** The automated tests use a stand-in for Claude. The bot stores each
  lead's context as "system" turns inside the conversation history; this has never been run against the real
  Claude API. Before any customer sees it, run one full conversation (enquiry, price, follow-up) on a test number
  and check that the API accepts it.

## Trial mode (the default)

While `TRIAL_MODE=true`:

- The bot reads every incoming message, keeps the CRM-style record up to date, and writes the reply it would send.
  **Nothing it writes is sent**, on any channel: replies, prices, follow-ups, templates, review requests, Instagram
  comment replies and email summaries all become drafts.
- Drafts appear on `/admin` next to the conversation, and all together on `/admin/drafts`. Rate each one **Good**,
  **Needs changes** or **Wrong**, with a note. The drafts page shows how often the drafts were right (overall, last 7
  days, and by type of message). Use those numbers to decide when to switch trial mode off.
- Owner alerts (price needed, reminders, voice notes, daily digest) still reach you.
- **You are alerted about every new customer message** (WhatsApp, Instagram DMs and comments, email, website
  chat), because in trial mode nobody else answers. The alert shows who wrote, what they said, the draft reply
  and the link to the lead on `/admin`, so you can answer within minutes. To avoid floods, a lead that keeps
  writing alerts you at most once every 30 minutes (`TRIAL_ALERT_MINUTES`).
- You can still answer customers yourself with **Reply as team** on the lead's page (that is you sending, not the
  bot). **Use this draft** copies a draft into that box so you can edit it and send it.
- The website chat shows the visitor "the team will get back to you" and asks for a WhatsApp number or email.

Only you switch to live mode, by setting `TRIAL_MODE=false` and restarting.

## What it does, channel by channel

| Channel | How leads arrive | What the bot does |
|---|---|---|
| WhatsApp | Customer messages +971 56 722 0533 (WhatsApp Cloud API) | Replies in their language and dialect and reads photos of venues. Voice notes and files: you are alerted at once and can play or download them on `/admin`; the bot acknowledges them and carries on in text |
| Instagram | DMs, plus comments on posts and reels | Replies to DMs. A comment gets one private DM only when the whole comment is a keyword (`عرض`, `سعر`, `price`, `quote`, `info`) or it asks the price (`سعر`, `كم السعر`, `بكم...`, `price`, `quote`, `how much`). "عرض رهيب" ("amazing show") is a compliment and gets nothing |
| Email | Mail to sales@ forwarded by your provider's inbound webhook | Replies by email and can send a written summary |
| Phone | Calls to a Twilio number (or your number forwarded to it) | Rings the team first if configured. If nobody answers, it plays a short message and sends the caller the `missed_call` WhatsApp template |
| Website | Chat bubble on echolight.ae (one script tag) | Live chat in English or Arabic |

**The sales process:** greet → understand the event (type, date, venue, guests, indoor/outdoor, services, name) →
recommend services with matching past work → ask you for the price and tell the customer the team is preparing
their quote → pass your price on word for word, with its validity date → book a call or site visit → mark "booked"
and alert you.

## Pipeline stages (the same as the CRM)

| Stage | Meaning | Set by |
|---|---|---|
| `new` | First message | The bot |
| `qualifying` | Collecting details | The bot |
| `awaiting_price` | Waiting for your price | The bot, when it asks you |
| `quoted` | The customer has the price | The bot, when the price reaches them |
| `negotiating` | Discussing the price | The bot |
| `booked` | Said yes, deposit due | The bot |
| `confirmed` | Deposit received | You: "Deposit received" button |
| `completed` | Event done, balance received | You: "Event done / balance received" button |
| `lost` | Declined or cancelled | The bot, or you: "Mark as lost" |

## How pricing works

Every project is priced by you. The bot never sets, estimates, rounds or discounts a price.

1. When it has the details, it alerts you: **"[Lead #12] Price needed: Sara"**, with the requirements and a link to
   the lead. If another live lead has the same event date, the alert says so, so you can check crew and equipment.
2. **You enter the price only on the dashboard** (`/admin/leads/12`): the amount in AED excluding VAT (for reports)
   and the exact wording for the customer, for example
   `AED 28,000 excl. VAT (+5% VAT) - lighting, 6x3m LED wall, setup and 2 technicians`.
   Replies to alert emails and WhatsApp messages from your phone are **not** read as prices: those routes were
   removed because anyone could fake them.
3. The bot gives the customer your price exactly as you wrote it (adding "+5% VAT" only if your wording doesn't
   mention VAT), the payment terms (50% deposit, balance on the event date) and the date the quote is valid until.
   In trial mode it drafts this message instead.

**Things to know:**
- If the customer last wrote more than 24 hours ago, WhatsApp only allows a pre-approved template. The bot sends
  "your quote is ready, reply to see it" and gives the price the moment they reply.
- While a customer waits for your price, they get no follow-ups. You get reminders after 3 and 24 hours, then once
  a day until you price it (`PRICE_REMINDER_HOURS`, `PRICE_REMINDER_REPEAT_HOURS`), and the daily digest lists
  everyone waiting.
- The bot never promises when the price will arrive; it says the team will share it as soon as possible.
- When a customer negotiates, the bot asks you again and tells them it is checking. It never agrees to a discount.

## Quotes are valid for 7 days

Every price message states "valid until <date>" (7 days from the day it is sent; `QUOTE_VALIDITY_DAYS`). After a
quote goes out, the follow-ups are:

- **Day 1:** a normal check-in.
- **Day 3 (expiry day):** "your quote is valid until today; shall we lock the date?"
- **Day 7:** the last check-in, offering to refresh the quote.

After the validity date the bot never presents the old price as valid and cannot mark the lead "booked" on it. It asks
you to re-confirm the price and the date's availability, and tells the customer the team is checking.

## Taking over a chat

On a lead's page in `/admin`:

- **Pause bot** stops the bot for that lead. New messages are logged and you are alerted, but the bot neither replies
  nor drafts.
- **Reply as team** sends what you type from the business number (or email). WhatsApp and Instagram only allow this
  within 24 hours of the customer's last message; outside that window the page tells you and nothing is sent. Tick
  "This message gives the customer the price" when it does, so the 7-day validity starts.
- **Resume bot** hands the chat back. The bot is told what the customer and you wrote while it was paused.

Moving +971 56 722 0533 to the WhatsApp Cloud API has traditionally meant it can no longer be used in the WhatsApp
Business phone app. Meta has a "coexistence" option that may let you keep using the app on the same number: check
whether it's available for your number before you move it.

## Follow-ups, reviews and consent

- **Follow-ups** go to people who contacted us, at 20 hours, 3 days and 7 days after the last message. Never between
  22:00 and 09:00 UAE time, and they stop when the customer replies, books, declines or asks to stop. Outside the
  24-hour window the bot uses the `followup` template, a Utility message about their own enquiry.
- **Review requests** are sent only after you press "Event done / balance received", and only to customers who agreed
  to receive messages. Marking a lead lost cancels any pending review request and follow-ups.
- **Reactivation** ("planning another event?") goes 60 days later, only to customers who agreed to receive messages.
- **Instagram commenters** get one private reply and nothing more until they write to us by DM. They are never
  contacted on WhatsApp.

## Outbound policy

The bot never contacts strangers. It only answers people who contacted EchoLight (message, comment, email, call or
website chat), and WhatsApp templates go only to people who messaged or called the WhatsApp number.

Cold outreach exists only in the CRM playbook (`skills/echolight-sales/SKILL.md`): by email, to business addresses,
with an unsubscribe line, off by default, each message approved first, and only drafts while trial mode is on.

## Who the customer is talking to

The bot writes as the EchoLight team and signs "EchoLight team" / "فريق إيكو لايت". It doesn't introduce itself as
a bot or an assistant, and it never claims that anyone is reading along. If a customer sincerely asks whether they
are talking to a person or a bot, it never claims to be human: it says they are chatting with EchoLight's assistant,
that Kareem and the team personally review every project, offers a call with Kareem, and alerts you.

## What the bot will not do on its own

- **Set a price** (see above).
- **State facts that are not in `knowledge/business.md`.** That file controls every fact the bot states. If something
  is missing, it says the team will confirm and alerts you.
- **Confirm date availability.** It notes the date and says the team confirms it with the quote.
- **Message anyone who hasn't contacted EchoLight** (see the outbound policy).

## Set up (only when you decide to deploy)

1. **Check the knowledge file** `knowledge/business.md`. It controls every fact the bot states.
2. **Get a Claude API key** at console.anthropic.com and set `ANTHROPIC_API_KEY`.
3. **Host the service** anywhere that runs Docker with a public HTTPS URL and a persistent disk (Railway, Render,
   Fly.io, or a small VPS):
   ```bash
   docker build -t echolight-sales .
   docker run -d --env-file .env -v echolight-data:/data -p 8000:8000 echolight-sales
   ```
   Set `PUBLIC_BASE_URL` to the HTTPS URL and `ADMIN_TOKEN` to a long random password. Leave `TRIAL_MODE=true`.
4. **WhatsApp (Meta Business Suite → WhatsApp Cloud API):**
   - Check the coexistence option above, then connect +971 56 722 0533 (or a new number) to the Cloud API.
   - Create a System User token (`WHATSAPP_TOKEN`) and copy the phone number ID.
   - Webhook URL: `https://YOUR-HOST/webhooks/meta`. Verify token: `META_VERIFY_TOKEN`. Subscribe to `messages`.
   - Copy the App Secret to `META_APP_SECRET`.
   - Submit the templates below for approval and put their names in `.env`.
   - Set `OWNER_WHATSAPP` to your **personal** number, not the business number. It is used for alerts only.
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
9. **Run the live test** described at the top, still in trial mode, and review the drafts for a few weeks before
   you set `TRIAL_MODE=false`.

### WhatsApp templates to submit

Every customer template has one variable, `{{1}}`: the customer's first name. When the name is unknown the bot fills
in "بك" in Arabic (so it reads "مرحباً بك،") and "there" in English ("Hi there,"). For `owner_alert`, `{{1}}` is the
alert title; it only matters if you want WhatsApp alerts when you haven't messaged the bot number in the last 24
hours (email alerts always work).

Submit every template in Arabic. Arabic-speaking customers always get the Arabic version; everyone else gets
`WA_TEMPLATE_DEFAULT_LANGUAGE` (Arabic by default). Once the English versions are approved, set it to `en`.
Marketing templates are sent only to customers who agreed to receive messages. Replace `[رابط تقييم جوجل]` and
`[your Google review link]` with the link from your Google Business Profile ("Ask for reviews").

| Name (`.env` setting) | Category | Sent to | Arabic | English |
|---|---|---|---|---|
| `followup` (`WA_TEMPLATE_FOLLOWUP`) | Utility | People who contacted us, after they go quiet | مرحباً {{1}}، بخصوص استفسارك عن فعاليتك مع إيكو لايت: هل تحتاج أي معلومة إضافية منا حتى نكمل؟ ردّ على هذه الرسالة ونكمل معك. | Hi {{1}}, about your event enquiry with EchoLight: is there anything else you need from us to move forward? Reply to this message and we'll pick it up from there. |
| `missed_call` (`WA_TEMPLATE_MISSED_CALL`) | Utility | People who called and weren't answered | مرحباً {{1}}، فاتتنا مكالمتك مع إيكو لايت ونعتذر عن ذلك. كيف نقدر نساعدك في فعاليتك؟ | Hi {{1}}, sorry we missed your call to EchoLight. How can we help with your event? |
| `quote_ready` (`WA_TEMPLATE_QUOTE_READY`) | Utility | Customers whose price is ready but who last wrote over 24h ago | مرحباً {{1}}، عرض السعر لفعاليتك جاهز. ردّ على هذه الرسالة ونرسل لك التفاصيل. | Hi {{1}}, your event quote is ready. Reply to this message and we'll send you the details. |
| `review` (`WA_TEMPLATE_REVIEW`) | Marketing | Customers who agreed to messages, after "Event done" | مرحباً {{1}}، شكراً لاختيارك إيكو لايت! إذا عجبتك الفعالية، تقييمك على جوجل يفرق معنا كثير: [رابط تقييم جوجل] | Hi {{1}}, thank you for choosing EchoLight! If you enjoyed the event, a Google review means a lot to us: [your Google review link] |
| `reactivation` (`WA_TEMPLATE_REACTIVATION`) | Marketing | Customers who agreed to messages, 60 days later | مرحباً {{1}}، عندك فعالية قادمة؟ إيكو لايت جاهزة بالإضاءة والشاشات والليزر. ردّ علينا ونساعدك. لإيقاف هذه الرسائل ردّ بكلمة: إيقاف | Hi {{1}}, planning another event? EchoLight is ready with lighting, LED screens and lasers. Reply and we'll help. To stop these messages, reply STOP. |
| `owner_alert` (`WA_TEMPLATE_OWNER_ALERT`) | Utility | You (the owner) | تنبيه مبيعات إيكو لايت: {{1}} | EchoLight sales alert: {{1}} |

Meta decides the final category; if it moves `followup` to Marketing, the bot keeps sending it only to people who
contacted us, but check Meta's current rules.

## Running costs (estimate)

- **Claude:** with the default model, a typical 10-message enquiry costs roughly USD 0.10-0.40 (an estimate, not a
  measurement). To trade some quality for cost, set `CLAUDE_EFFORT=low`.
- **WhatsApp:** replies within 24 hours of the customer's message are free. Templates are charged per message by Meta.
- **Twilio:** a UAE number plus per-minute call charges.
- **Hosting:** about USD 5-20 a month.

## Develop

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest
ANTHROPIC_API_KEY=... .venv/bin/uvicorn salesbot.app:create_app --factory --reload
```

| Path | Contents |
|---|---|
| `salesbot/agent.py` | The Claude conversation loop, prices and quote validity, follow-up scheduling, team takeover |
| `salesbot/outbound.py` | The one gate every customer message passes through: sends in live mode, drafts in trial mode |
| `salesbot/templates.py` | WhatsApp template wording (the table above) and the email versions |
| `salesbot/prompts.py` | The bot's instructions |
| `salesbot/tools.py` | Lead saving, price requests, booking, stages, escalation, consent, email summaries |
| `salesbot/app.py` | Webhooks, website chat, the `/admin` dashboard (prices, drafts, takeover, stages) |
| `salesbot/scheduler.py` | Follow-ups, price reminders, review requests, reactivation, retries, daily digest |

The bot uses `claude-opus-5-5` with adaptive thinking. It opts into server-side refusal fallbacks
(`fallbacks: "default"`), so a declined request is retried on another model automatically. If a reply still fails,
the message is retried and you are alerted.
