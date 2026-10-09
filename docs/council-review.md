# EchoLight sales system: council review

Four independent reviewers each read everything built so far (the WhatsApp bot, the CRM and the Claude playbook). The Believer makes the case for it, the Skeptic attacks it, the Investor looks at the money, and the Judge checks their claims against the code and rules. The Judge's verdict comes first; the full reports follow.

---

## The Judge: final verdict on EchoLight's sales system

**Verdict: Use the CRM and the playbook now, with Claude drafting and a person pressing send. Shelve the Python salesbot until you accept an API key, and fix it before it goes live.**

**Score: 6/10.** The price, VAT, payment and no-generator rules are well thought through, and the CRM fits how EchoLight sells. But nothing is live, there are three systems that disagree with each other, and several bugs would embarrass you in front of a customer.

### What I checked in the files

| Skeptic's claim | Ruling | Reason |
|---|---|---|
| Review request not cancelled when a lead is marked "lost" | CONFIRMED | `tools.py _set_stage` schedules the review on "booked" and never cancels it on "lost". `run_template_touch` only checks do-not-contact. |
| Instagram comment fakes the 24h window | PARTLY TRUE | `app.py reply_to_comment` does set `last_inbound_at`, so the 20h follow-up tries a DM that Instagram will refuse, retries 3 times and then alerts you. The jump to WhatsApp only happens if a phone number was saved, which is rare. |
| "عرض" keyword is ambiguous | CONFIRMED | `config.py` matches it as a substring, so "عرض رهيب" ("amazing show") triggers a sales DM. |
| Template language and "there" fallback | CONFIRMED | There is one `WA_TEMPLATE_LANGUAGE` (default "en"), and an unknown name becomes "there" (`agent.py send_template`). |
| `parse_amount` picks up a year | CONFIRMED | "#12 Dec 2026 gala, AED 28,000" is recorded as 2026. This only affects revenue figures, not the customer's message. |
| Revised prices are not delivered | CONFIRMED | SKILL.md step 11.3 only delivers prices on `awaiting_price` leads. For other stages the CRM price form ticks "already sent" by default and sets no "send" flag. |
| README contradicts business.md | CONFIRMED | There is no "To confirm" section. The price examples say "incl. VAT" in the README, `tools.py` and `app.py`, which goes against your excl.-VAT rule. |
| System-role messages in the history | PARTLY TRUE | The code does this on purpose, and the test fake enforces a specific API rule. It has never been run against the real API, so it needs one live test. |
| "Team is copied on the conversation" | CONFIRMED (bot), PARTLY (playbook) | In the bot nobody watches live, so the claim is false. In the laptop mode a person does see WhatsApp Web. |
| Owner price email can be spoofed | CONFIRMED | `handle_owner_email` trusts the From address. There is no SPF/DKIM check. |
| Marketing templates sent without opt-in | CONFIRMED | Follow-up and review templates check only do-not-contact, and the README lists both as Marketing. |
| No human takeover | CONFIRMED | `/admin` has only a price form: no reply box and no pause switch. Meta's "coexistence" mode may now allow the app and the API on one number, so check before giving up the app. |
| Voice notes answered with "please type" | CONFIRMED | `whatsapp_content`. |
| Arabic dialect mismatch | CONFIRMED | The templates use Levantine words ("كيف فينا", "كتير"), but the prompt says Gulf-neutral. |
| Price reminders stop after 24h | PARTLY TRUE | They do stop, but the 09:00 digest still lists every lead waiting for a price. |
| Bot has no confirmed/completed stages | CONFIRMED | `tools.py STAGES`. There are 4 places to enter a price. |

**Believer, checked:** 35 tests pass (I ran them). Price reminders go out at 3h and 24h. Follow-ups stop when a reply comes in. Missed calls ring the team first. "Customer messages can't change its rules" overreaches: that is a prompt instruction, not a guarantee.

**Investor, checked:** The README figures ($0.10-0.40 per enquiry, "2-3 hrs" setup) are quoted correctly. One claim is partly wrong: the CRM does record arrival time (`createdAt`). It does not record first-reply time.

**I also found:** the README says the system "does not cold-message strangers", but SKILL.md section 9 does cold email outreach. You need to decide which one is your policy.

### Weighing the three cases

- **Believer** is right that speed to reply and disciplined follow-up are where small AV firms lose deals, and that reminding the owner about prices is a smart design. They overreach by counting gains from a bot that cannot run under "no API", and by praising the "comment عرض" call to action.
- **Skeptic** is right on almost every code defect. Losing the ability to take over a chat, and marketing templates sent without consent, are real risks to your only WhatsApp number. They overreach on WhatsApp crossover from Instagram, and on suggesting price bands: an approved price band is still a price, which breaks your rule 3 unless you choose it.
- **Investor** is right about the main point: the realistic failure is an empty CRM, not the cost. The advice to run path (a) now, measure, and decide on (b) at day 90 is sound. The revenue scenarios are assumptions, not forecasts.

### Must fix before any customer sees it (in order)

1. **One system of record: the CRM.** Enter prices only through the CRM price form. Turn off the other three price routes.
2. **Human sends, Claude drafts,** for at least the first 30 days. Set `inboundReplies` so Claude writes drafts as next steps, and a team member sends them from the phone. This avoids WhatsApp Web automation risk and wrong-chat mistakes.
3. **Honest disclosure line.** Change rule 9 to: "I'm EchoLight's assistant; Kareem's team reviews every quote." Remove "the team is on the conversation" unless that is true.
4. **Revised prices:** add a "send this price" tick to the CRM price form for every stage, and make SKILL.md step 3 look for it.
5. **Reviews only after "Event done"** (SKILL.md already does this). Never send a review request on a verbal yes.
6. **Import only labelled business chats.** Archive or label personal and family chats before Claude touches WhatsApp Web.
7. **Price promise:** you commit to pricing within a set time (for example same day, 4h for weddings), and Claude tells the customer that time.
8. **Add the missing assets:** Google review link, portfolio links per segment, and one Arabic dialect choice for templates.
9. **Decide on outbound:** keep it off for now. Kareem sends 5 personal emails a week that Claude drafts.

### Drop or merge

- **Keep:** the CRM (system of record) and SKILL.md (the playbook).
- **Freeze:** `salesbot/`. Don't deploy it. If you later accept an API key, rewire it to read and write the CRM database instead of its own SQLite and `/admin`. Before launch, fix: cancel the review on "lost", the Instagram window, the keyword list, the opt-in check for marketing templates, sender verification on owner emails, `parse_amount`, the "incl. VAT" examples, template language per lead, a pause/reply-as-team button, one live API test, and voice notes.
- **Drop:** the email and WhatsApp `#12` price routes. They are spoofable and they duplicate the CRM form.

### 30-day plan for Kareem

- **Week 1:** Label your business chats. Ask Claude to import the last 6-12 months into the CRM (no messages sent). Add your Google review link and portfolio links. Make the fixes above to SKILL.md and the CRM price form.
- **Week 2:** Every morning and evening, open Claude Desktop and say "run sales". Claude drafts replies and follow-ups, and you or a team member send them. Enter every price in the CRM, within your promised time.
- **Week 3:** Keep going. Log a lost reason on every lost deal. Check the Call sheet daily. If the drafts look right 9 times out of 10, let Claude send follow-ups itself (not first replies).
- **Week 4:** Open Reports. Look at enquiries by source, time to price, win rate, and how many enquiries came in at night. If more than a quarter come in between 22:00 and 09:00, or you keep missing them, that is the case for the API key and for reviving the bot, fixed first. If the CRM has fewer than 30 real leads, the problem is habit, not software.


---

## The Believer: why this system can win EchoLight more deals

### The short version
A small AV company in the UAE rarely loses deals because its lighting is worse. It loses them in the gaps around the show: the WhatsApp that sat unanswered for six hours, the quote that never went out because Kareem was rigging a ballroom, the "let me check with management" that nobody chased, the missed call that went to a competitor. What was built here goes after those gaps one at a time, and it does it without breaking the owner's most important rule: **only Kareem sets prices**. That design keeps the owner in control of margin and puts the machine in charge of speed and memory.

### What each piece fixes

**1. Slow first replies → an answer in minutes, in the customer's own dialect.**
In this market, the first supplier to reply properly usually gets the event brief. The bot (`salesbot/agent.py`, `prompts.py`) answers WhatsApp, Instagram DMs, email and the website chat. It mirrors Gulf, Levantine, Egyptian or standard Arabic, and it asks at most two questions per message. That suits a Syrian-Arabic brand talking to Emirati families and expat corporate buyers. The playbook (`SKILL.md` §6.1) has the same "first reply within minutes" rule for the laptop-run version.

**2. Half-qualified enquiries → a ready-to-price brief.**
Today, "how much for lights?" takes four messages before anyone can quote. The agent collects the checklist (event, date, venue/emirate, guests, indoor/outdoor, services, name) and saves each item to the lead with `save_lead_details` as it hears it. Then `request_price` emails Kareem a "[Lead #12] Price needed" summary. He replies with a price in one line by email, by WhatsApp (`#12 AED …`) or on the dashboard. The discovery questions in `SKILL.md` §6.2 ("What's the moment you most want guests to remember?") lead naturally to laser shows and LED walls, so they raise order value as well as qualifying the lead.

**3. Prices sitting unsent → the owner gets reminded, not the customer.**
This is the cleverest mechanism. While a lead waits on a price, follow-ups to the customer stop (`tools.py` `_request_price`). Kareem is reminded instead, at 3 and 24 hours (`scheduler.py remind_price`), and every waiting lead shows in the 09:00 digest. The CRM Call sheet opens with "Waiting for your price", showing how long the oldest lead has waited, and Reports tracks "Time to price". The real bottleneck in an owner-priced business is the owner, and the system keeps him in front of it.

**4. Forgotten follow-ups → three timed touches, then a polite close.**
Quotes that get no reply are the biggest silent loss. The bot sends follow-ups at 20 hours, 3 days and 7 days. They never go out in quiet hours (22:00-09:00), they stop as soon as the customer replies, books, declines or opts out, and outside WhatsApp's 24-hour window they switch to Meta-approved templates (`agent.py run_followup`, `send_template`). Each follow-up is told to "add something useful", such as a past project or a next step, so it doesn't read as nagging.

**5. Missed calls → a WhatsApp conversation.**
During a get-in, nobody answers the phone. The Twilio flow (`app.py`) rings the team first. If nobody picks up, it plays a bilingual message and sends the caller a WhatsApp template straight away. A call that would have been lost becomes a live lead.

**6. Reels with no sales path → comment-to-DM.**
Kareem's Instagram reels already bring in attention. With keyword comments ("عرض", "سعر", "price") the bot sends a private DM (`handle_instagram_comment`), so a call to action like "comment عرض" goes straight into a sales conversation.

**7. No visibility → one pipeline everyone shares.**
The CRM (`crm/index.html`) gives the team a Call sheet (prices needed, follow-ups due, shows in 3 weeks), a kanban running from New enquiry to deposit paid, a Shows calendar with 50/50 payment status, and Reports (win rate, average deal, lost reasons, source and segment). For the first time, EchoLight would know which segment wins and why deals are lost.

**8. No outbound → careful, compliant prospecting.**
`SKILL.md` §9 targets the right buyers: hotels before NYE and National Day, wedding planners in August and September, car dealers around launches, agencies all year. Outreach is email-only to business addresses, needs approval, is capped at 20 a day and stops after two follow-ups. That protects the business number from a WhatsApp ban and respects UAE PDPL consent rules. It is OFF by default, which is right.

**9. Revenue after the show → reviews, referrals, reactivation.**
`set_stage("booked")` schedules a review request for after the event date. Leads who opted in get a check-in after 60 days. That keeps the 5.0 Google rating growing and brings back repeat hotel and agency work.

### Guardrails that protect revenue
The bot never quotes, rounds or discounts. It passes the price on word for word, adds "+5% VAT" if the price doesn't mention it, and sends payments only to the company account on the invoice. It never confirms a date without the team, and it doesn't mention insurance. Customer messages can't change its rules. If a reply fails, it retries and then alerts the owner (`scheduler.py`). All of this is backed by 35 tests.

### What to expect (estimates; my assumptions)
Assume about 40 enquiries a month and a 20% close rate today, with roughly a third of losses caused by slow replies or no follow-up (typical for small owner-run teams; EchoLight's real figures are unknown). Under those assumptions:
- Replying 24/7 and following up every quote could lift the close rate by about 3-6 points, which is **1-2 extra events a month**.
- Missed-call recovery and comment-to-DM add enquiries EchoLight currently never sees.
- "Time to price" becomes measured and drops, because the owner is reminded.
- Within about 90 days, the Reports tab would show which segments and sources pay off. Kareem's other Claude can use that to decide where Google Ads money goes.

These gains need the bot to be live. In laptop-only mode they shrink to whatever "run sales" sessions cover.

### The best way to get the most out of it
- **Price fast.** Make answering "Price needed" alerts a habit within a few hours, from your phone. Speed to quote is the biggest lever you control.
- **Import the last 12 months of chats first** (`SKILL.md` §10). Open quotes and past clients make up the quickest revenue in the CRM.
- **Fill in `knowledge/business.md` and add the sales assets**: the Google review link, portfolio links per segment, and named clients. The bot can only sell with facts it has been given.
- **Run sales at least twice a day while the laptop route is all you have, and plan to go live.** Turn on the API version, at least for WhatsApp and missed calls, when you're ready. That is what makes it 24/7.
- **Read Reports weekly.** Act on lost reasons and on which sources win, and switch on outreach (with approval) before National Day, NYE and wedding season.


---

## The Skeptic: what goes wrong with EchoLight's sales system

Bottom line: the guardrails on price, generators and insurance are good. The weak spot is everything around them. Once the bot is live, nobody can step into a WhatsApp chat themselves. Some messages break WhatsApp's rules. The bot and the CRM disagree about the pipeline. And EchoLight sells on Kareem's personal touch, which the bot can't copy.

### Critical

1. **Nobody can take over a chat.** Once +971 56 722 0533 moves to the Cloud API, the team can't type on it in the WhatsApp Business app. The /admin dashboard only has a "Send the price" form (salesbot/app.py). When a bride's mother asks for a person, the bot alerts the owner and carries on talking. Kareem can't answer her on the same number.
   **Fix:** add a "reply as team" box and a pause-bot-on-this-lead switch to /admin, or first check whether Meta's coexistence mode lets the number stay in the Business app as well. The README says this isn't possible, so check before trusting it.

2. **Anyone can fake a price email.** handle_owner_email (app.py) trusts the email's From address. A forged email from the owner's address with "[Lead #12]" in the subject goes to the customer "verbatim". A competitor or scammer could send a wrong price, or a wrong set of payment instructions.
   **Fix:** reject owner emails that fail the provider's SPF/DKIM check, or take prices only from WhatsApp and the dashboard.

3. **Marketing templates go to people who never opted in.** Follow-up templates and the Google review template are sent to every quiet or booked lead, whatever their opt-in status. agent.py run_followup / run_template_touch only check do_not_contact. The README files both templates under Marketing. Meta needs consent for marketing templates, and blocks and reports lower the number's quality rating. That is a ban risk on the company's only WhatsApp number.
   **Fix:** send marketing templates only when marketing_opt_in is set, and make the 20h follow-up a Utility "still need help with your event?" message.

4. **Claude driving the owner's WhatsApp Web** (SKILL.md section 2, section 10 import). Automating WhatsApp Web breaks WhatsApp's terms. One wrong click sends a message to the wrong chat. The 12-month import reads personal and family chats in order to "skip" them. On top of that, every customer's data gets copied into a claude.ai artifact the whole team can open, with no export (a UAE PDPL purpose and minimisation problem).
   **Fix:** while this is in place, Claude drafts and a human sends. Import only labelled business chats, and only after the owner has removed the personal ones.

### High

5. **The owner is now a formal bottleneck.** Every quote waits on Kareem, who is on site at shows in the evenings. The customer hears only "the team is preparing your quote" and never gets an update. Reminders stop after 24h (config.py price_reminder_hours 3, 24). Assumption: if prices take 1-3 days, wedding families will already have quotes from 2-3 competitors.
   **Fix:** reply within 2 hours with price bands for common setups that the owner has approved, plus a "price promised by" time and a second person who can price.

6. **Review requests reach cancelled clients.** When the bot marks "booked" on a verbal yes (tools.py _set_stage), it schedules the Google review request. Setting "lost" later doesn't cancel it. So a cancelled client gets "thanks for choosing EchoLight, please review us".
   **Fix:** cancel review_request when a lead moves to lost, and schedule it only from "event done".

7. **Instagram follow-ups break the rules and will fail.** After a comment reply, reply_to_comment fakes `last_inbound_at`, so follow-ups go out as free DMs to people who never wrote. Instagram allows only one private reply, so these will fail, retry three times, then alert the owner. If the person has a phone number saved, the WhatsApp marketing template goes to someone who only commented on a reel.
   **Fix:** don't set last_inbound_at on comment replies, and never move an Instagram commenter onto WhatsApp.

8. **The comment keyword "عرض" means "show" as well as "offer".** A fan writing "عرض رهيب" ("amazing show") under a laser reel gets a sales DM (config.py instagram_comment_keywords). That's creepy on Kareem's own reels.
   **Fix:** use "سعر", "price", or a single unusual CTA word.

9. **Three systems give three answers.** The bot has no confirmed or completed stages. The CRM does. SKILL.md sends the review request after "completed", the bot sends it after "booked". Prices can be entered in four places: email, WhatsApp, /admin, the CRM form. The team will use none of them consistently.
   **Fix:** pick one system of record now. If there's no API key, that's the CRM; shelve salesbot.

10. **No equipment or crew calendar, so double bookings are possible.** The bot collects dates and requests prices for clashing events. The CRM Shows view lists events but not LED walls or technicians.
    **Fix:** add a required "date and kit checked by" field before a price can be entered.

11. **The bot claims "the team is copied on the conversation"** (prompts.py, SKILL.md rule 9). It isn't: the owner only gets alerts. The bot also hides that it's automated unless asked. Clients who were sold on "Mr. Kareem" will feel misled when they find out.
    **Fix:** disclose up front in a friendly way ("EchoLight's assistant, Kareem's team reviews every quote"), and remove the false claim.

### Medium

12. **Voice notes get "please type".** Gulf families use voice notes constantly (agent.py whatsapp_content). **Fix:** transcribe them, or alert a human straight away.
13. **The Arabic doesn't match.** The templates are Levantine ("كيف فينا", "كتير"), the prompt asks for "Gulf-neutral", and the brand voice is Syrian. Templates use one language (WA_TEMPLATE_LANGUAGE defaults to "en"), and an unknown name becomes "مرحباً there". **Fix:** submit both language versions, choose by lead language, and use a proper Arabic fallback with no name.
14. **"Verbatim" price versus "reply in their language".** If the owner writes the price in English for an Arabic-speaking customer, the bot will either translate it, which changes the wording, or paste the English. Email replies can also carry signatures or internal notes straight to the customer. **Fix:** owner writes in the customer's language; show the owner a preview before sending.
15. **Price revisions are missed.** SKILL.md routine step 3 only delivers prices for `awaiting_price`, so a revised price on a `negotiating` or `quoted` lead is never sent. **Fix:** add a "price ready to send" flag.
16. **Revenue figures can be wrong.** parse_amount takes the first number of 3+ digits. "#12 Dec 2026 gala, AED 28,000" is recorded as 2026. **Fix:** take the number after "AED".
17. **The README contradicts itself.** It says deposit and VAT policies sit under "To confirm" in business.md, but business.md has no such section. Its price examples say "incl. VAT", while the company rule is to quote excluding VAT. **Fix:** update the README and switch the examples to "excl. VAT".
18. **Automation depends on the laptop.** "Run sales" only happens while the laptop is on and Claude Desktop is open. Overnight and show-night enquiries sit unanswered, while the README promises "around the clock". **Fix:** say plainly that replies are human-hours only, or accept the API key.
19. **Possibly untested against the real Claude API.** Lead context is stored as role "system" turns inside the message history (agent.py _context_message, db.transcript), and the tests use a fake client. The real API may reject this. **Fix:** run one live end-to-end test before any launch.
20. **Cold email outreach in SKILL.md section 9 carries reputational risk.** Hotels and agencies talk to each other, and 20 emails a day from a small brand get noticed. **Fix:** keep it off. Have Kareem send 5 personal emails a week that Claude drafts.


---

## The Investor: does this make money?

**Short answer:** Yes, and it doesn't take much. One extra booked event pays for either path for a year or more. Money is not the constraint. The real risks are that the CRM stays empty, and that customers wait too long for the owner's price. **Pay for path (a) now. Earn your way to path (b) with 90 days of data.**

### Assumptions (I don't have EchoLight's real numbers; replace them with yours)

All figures in AED, excluding VAT.

| Segment | Typical deal (range) | Base used |
|---|---|---|
| Weddings | 15k–60k | 25k |
| Hotels (ballroom, NYE, brunches; repeat business) | 10k–60k | 20k |
| Corporate galas, launches, government | 30k–150k | 50k |
| Automotive launches (Bin Hamoodah, DIBO-type) | 50k–250k | 80k |
| **Blended average** | | **~35k** |

- **Margin:** about 45% contribution after crew, transport and subrentals, so roughly 15k profit on an average deal.
- **Inbound volume:** 25–60 real enquiries a month. Base case is 40. That fits "400+ events": roughly 6–8 shows a month over several years.
- **Current conversion (enquiry to deposit):** 12–20%. Base case is 15%, which is 6 deals and about AED 210k a month.
- **What the system adds:**
  - Replying within minutes instead of hours (nights and weekends especially): +1–2 points.
  - Three disciplined follow-ups on quiet and quoted leads (SKILL.md §6.5, `scheduler.py`): +1–3 points.
  - Outbound email to hotels, corporates and auto brands (SKILL.md §9, cap of 20 a day): realistically 0–1 deal a month, and nothing in the first 60 days because corporate sales cycles are long.

### What each path costs

| | (a) CRM + Claude Desktop on the laptop | (b) Full salesbot (`salesbot/`) |
|---|---|---|
| Software | Claude Max plan, about USD 100–200/mo (AED 370–735). Pro is too small for daily runs that drive WhatsApp Web. | Anthropic API USD 30–150/mo (README estimates $0.10–0.40 per enquiry; website chat time-wasters push it up). Hosting USD 5–20. Meta template fees, likely under USD 25/mo at this volume. Twilio UAE number and minutes USD 20–60 (UAE numbers need regulatory paperwork and may be hard to get). Inbound email service USD 0–15. **Total about AED 300–950/mo** |
| Setup | 4–8 hrs: import past chats (SKILL.md §10), fill in settings | README says 2–3 hrs. **Realistically 15–30 hrs**, covering Meta business verification, template approvals, Twilio paperwork and testing. AED 4k–10k if you hire a freelancer. |
| Owner time | 20–40 min a day: start "run sales", approve prospects, set prices | 1–2 hrs a month of maintenance, plus pricing |
| Hidden cost | Nothing happens while the laptop is off or nobody starts a run, so nights get no replies | The business number leaves the WhatsApp Business app. The team can no longer chat from their phones, and a bot mistake can cost you a large deal. |
| **Year-1 cash** | **AED 4.5k–9k** | **AED 8k–22k** |

**Break-even:**
- **(a):** one extra wedding every 1–2 years covers the subscription. If you also value the owner's time at AED 200/hr (about 12 hrs/mo, or AED 29k/yr), you need about **2 extra small deals a year**.
- **(b):** **1–2 extra deals a year**, or just one automotive launch.
- **Payback:** both pay back on the first extra booking, usually within a month of that deal's deposit.

### Scenarios: extra profit per year (base 35k deal, 45% margin)

| | Leads/mo | Conversion uplift | Extra deals/mo | Extra revenue/yr | Extra profit/yr |
|---|---|---|---|---|---|
| **Worst** | 25 | 0 (CRM left empty, runs skipped) | 0 | 0 | **–AED 9k (a) / –AED 22k (b)** |
| **Base** | 40 | +2.5 pts | 1 | ~420k | **~190k** |
| **Best** | 60 | +5 pts, plus outbound 1/mo | 4 | ~1.9M | **~850k**, but capped by crew and equipment on peak weekends (Oct–Apr) |

The worst case is the realistic failure. Every build here is unused and has no real data in it. The software only earns once it is used every day.

### The 3 levers that move the money most

1. **Time to price.** Every lead goes through the owner for a price (rule 3). If quotes take 2–3 days, faster replies and follow-ups are wasted, because the customer has already booked a competitor. The CRM measures this directly ("Time to price" in Reports, "Waiting for your price" on the Call sheet). Target: under 24 hrs, and under 4 hrs for weddings.
2. **Follow-up on quotes already sent.** "Quoted" leads that go quiet are the cheapest money available: the work is done and the customer is already interested. Recovering 1 in 10 of them is the whole base case.
3. **Segment mix.** One automotive or corporate launch is worth three weddings, and hotels repeat. Point outbound (Settings, then Target segments) at hotels and auto dealers rather than chasing more wedding enquiries.

### Which path to pay for

- **Now: path (a).** It is close to free, it respects "no API", and it creates the data needed for any future decision.
- **Not now: path (b).** The extra it delivers over (a) is mainly instant replies at night and missed-call recovery. That might be worth +0.5 deal a month, but nobody can prove it yet, and it costs you the WhatsApp phone app and 20+ hours of setup.
- **When to switch:** build (b) if the 90-day data shows **more than 25% of enquiries arrive between 22:00 and 09:00 or on days nobody runs Claude**, *and* win rate is clearly lower for slow-reply leads. At that point (b) pays back within 1–2 deals.

### What to measure in the first 90 days (CRM → Reports)

1. **Week 1, baseline.** Import the last 3–6 months of WhatsApp and email chats (SKILL.md §10). Without this there is no "before" to compare against.
2. **Weekly:** leads by **source** and **segment**, **win rate** (won ÷ (won + lost)), **average deal**, **time to price**, and the funnel drop between "Quote sent" and "Booked".
3. **Lost reasons.** Record one for every lost lead. If "No response" leads, follow-up is the fix. If "Price" leads, the problem is not this software.
4. **Outbound:** prospects contacted, replies, meetings, and deals marked "Outbound (Claude)". Expect zero deals before day 60; judge it at day 90.
5. **Gap to fix.** The CRM does **not** record first-reply time or time of arrival. Add a note per lead (or a field) for "first reply took X min", or you can't test the case for (b).

**Day-90 test:** if win rate is up 2+ points or one deal can be traced to a follow-up or outbound, the system has paid for itself several times over and is worth keeping. If the CRM has fewer than 30 real leads in it, the problem is adoption, not the software, and no more should be spent on technology.


---

