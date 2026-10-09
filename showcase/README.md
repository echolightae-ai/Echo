# EchoLight Event Finder

A page where a client types their event ("corporate gala for 300 in Abu Dhabi", "عرس في دبي") and immediately sees:

1. **The setup we recommend** for that kind of event, split into *Essential*, *Elevate it* and *Signature moment*,
   plus the one moment guests will film.
2. **Our real projects that match**, best match first, with photos and videos.
3. **A WhatsApp button** that opens a chat with +971 56 722 0533, already filled in with their event and the
   recommended services. The sales bot (or you) picks it up from there.

It understands English and Arabic, ten event types (corporate, gala and awards, wedding, car and product launch,
grand opening, National Day and government, party and New Year, hotel events, concerts and fashion shows,
exhibitions), the five services, the emirates, guest numbers and indoor or outdoor. Clients can also filter by
service. If we have no project for something yet (3D mapping today), the page says so honestly and offers videos on
WhatsApp.

| File | What it is |
|---|---|
| `index.html` | The finished page. This is what goes online. Rebuilt by `build.py`; don't edit it by hand. |
| `catalog.json` | Every project, every event type and its recommended setup, and the words that trigger each one. |
| `template.html` | The page design. |
| `build.py` | Imports new events from `inbox/` and rebuilds `index.html`. |
| `inbox/` | Where you drop photos and videos from your phone. Not saved in git. |
| `media/` | The web-sized copies `build.py` makes. These go online with `index.html`. |

## Adding projects (the lazy way)

1. **Get the files off your phone.** AirDrop, Google Photos, a cable, or WhatsApp them to yourself and save them.
   Any mix of photos (including iPhone HEIC) and videos (.mp4, .mov) is fine. Don't pick: dump the whole event.
2. **Make one folder per event** inside `showcase/inbox/`, named with the date and a title:
   `2025-12 National Day - Abu Dhabi`, `2026-02 Rixos gala dinner`, `Saadiyat wedding`.
   Words in the name count: "wedding", "launch", "laser", "LED" and the city all tag the project automatically.
3. **Optional:** put a `notes.txt` in the folder with a line about it, in English or Arabic:
   `Corporate gala at Rixos, 6x3 LED wall, laser opening, 400 guests`.
4. **Run:**

   ```
   pip install pillow pillow-heif     # once
   python showcase/build.py
   ```

   It shrinks the photos to web size (1600px), converts videos to small 720p MP4s with a cover image (if
   [ffmpeg](https://ffmpeg.org/download.html) is installed), tags the event, adds it to `catalog.json` and rebuilds
   the page. It never imports the same folder twice, so you can keep adding folders and re-running it.

**Even lazier:** run `python showcase/build.py --ai` and Claude looks at each new event's photos and writes the
title, a one-line summary and the tags for you. It needs an Anthropic API key (`ANTHROPIC_API_KEY`). It only uses
names that are in your folder name or notes, so it won't invent clients.

**Laziest:** open Claude Code in this repo, drop the folders into `showcase/inbox/`, and say *"import my new
events into the showcase"*.

After any import, glance at the new entries at the bottom of `catalog.json`. Fix a title, set `"featured": true` on
your best work (it shows first when nobody has searched), or add `"link"` to the project's page on echolight.ae.

### Waiting for photos

These are in `catalog.json` (from the sales bot's knowledge file) but hidden until they have media. Give each one a
folder in `inbox/` and run the build, or add their photo links to `"media"` in `catalog.json`:

- Sky Laser Spectacular (Unique Homes & Al Nayef Group)
- Captiva Launch Production (Bin Hamoodah Auto)
- Winter Corner New Year's Countdown
- Jumeirah Saadiyat Wedding Production
- RAK Grand Wedding

If you add these through `inbox/`, delete the old placeholder entry from `catalog.json` so the project isn't listed
twice.

## Putting it on echolight.ae

The page is plain HTML: `index.html` plus the `media/` folder. Squarespace can't host a folder like that, so:

1. Go to [app.netlify.com/drop](https://app.netlify.com/drop) and drag the whole `showcase` folder onto it. You get a
   link like `echolight-finder.netlify.app`. (A free account keeps it online; you can also point
   `find.echolight.ae` at it.)
2. In Squarespace, add a navigation link called **Find your event** that points to that link, and/or add a button on
   the home page and the Our Work page: *"Planning an event? See work like yours"*.
3. To show it inside a Squarespace page instead, add a **Code** block with:

   ```html
   <iframe src="https://YOUR-LINK.netlify.app" style="width:100%;height:2200px;border:0" loading="lazy"></iframe>
   ```

When you add projects, run the build and drag the folder onto Netlify again.

**Deep links** for ads, Instagram bio and the sales bot: `…/?q=wedding` or `…/?q=car launch` opens the page already
showing that event type. `…/#corporate` works too (any event type id from `catalog.json`).

**One file to send anyone:** `python showcase/build.py --embed` writes `showcase/dist/echolight-showcase.html`, a
single file with every photo inside it (videos become their cover image). Good for email or WhatsApp.

## Changing what it recommends

Each event type in `catalog.json` has:

- `terms`: words that mean this event type (add slang or Arabic spellings you hear from clients),
- `pitch`: one sentence on what matters for that event,
- `essential`, `elevate`, `signature`: which services go in each column,
- `moment`: the signature idea.

Services have the same `terms` list. Edit, then run `python showcase/build.py`. The tests in
`tests/test_showcase.py` check that every id in the catalog is valid.
