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
| `organize.py` | Sorts a whole camera roll into events and picks the best shots into `inbox/`. |
| `build.py` | Imports new events from `inbox/` and rebuilds `index.html`. |
| `inbox/` | Where you drop photos and videos from your phone. Not saved in git. |
| `media/` | The web-sized copies `build.py` makes. These go online with `index.html`. |

## Adding projects: plug in your phone, run one command

You don't sort anything. `organize.py` goes through your whole camera roll, finds the events, and picks the
best shots.

1. **Copy the camera folder to your laptop.** Plug the phone in with USB.
   - iPhone on Windows: unlock the phone, tap *Trust*, then open the **Photos** app on the PC → *Import* → *All
     items*. Or in File Explorer: *Apple iPhone → Internal Storage → DCIM*, copy the whole `DCIM` folder.
   - iPhone on Mac: **Image Capture** → select all → *Download* to a folder.
   - Android: choose *File transfer* on the phone, then copy `DCIM` (and `Pictures/WhatsApp` if you like) to the laptop.

   Copy everything. Family photos, receipts and screenshots are fine; they get thrown out.
2. **Run it** (once: `pip install pillow pillow-heif anthropic pydantic`, plus [ffmpeg](https://ffmpeg.org/download.html)
   for videos, and set `ANTHROPIC_API_KEY`):

   ```
   python showcase/organize.py "C:/Users/you/Pictures/DCIM"
   python showcase/build.py
   ```

What `organize.py` does:

- Reads when and where every photo and video was taken (from the phone's own data; nothing is uploaded for this),
  and skips screenshots and the short clips iPhone Live Photos make.
- Removes duplicates for free on your laptop: the same file saved twice, and burst shots or re-takes that look
  nearly identical.
- Groups them into events: shots within 4 hours of each other at the same place are one event. The city comes from
  GPS.
- Makes one contact sheet per event and asks Claude: is this an EchoLight event or something else? For real events
  Claude writes a title and summary (venue and city only, never the client's name), tags the event type and
  services, and picks up to 12 photos and 3 videos.
- Copies only those picks into `showcase/inbox/<date> <title> - <city>/` and writes `showcase/inbox/REVIEW.md`,
  which lists what it kept, what it skipped and why. Your originals are never moved or changed.

Then `build.py` shrinks the picks for the web (photos to 1600px, videos to 720p MP4 with a cover image) and puts
them on the page. Both scripts remember what they've done, so next month you copy the new photos and run the same
two commands.

Tips:

- **Cost:** Claude looks at one contact sheet per event group, never at photos one by one. Before spending anything
  it prints how many groups it found and the estimated cost, and asks you to confirm. Roughly $0.03 per group
  with the default model, so ~12,000 photos (typically a few hundred groups) costs about $10-25. Add
  `--model claude-haiku-5-5` to do the same for under $1 (a cheaper model; check the picks a bit more closely),
  and `--budget 20` to make it stop at $20. A rerun continues where it stopped and never pays for the same group twice.
- `--latest 5` sorts only the 5 most recent events, for a quick first try.
- No API key? Use `--no-ai`. The events are grouped and parked in `showcase/inbox/_to-review/` with a contact sheet
  each. Open this repo in Claude Code on your laptop and say *"go through showcase/inbox/_to-review and keep the
  real events"*; Claude Code can look at the contact sheets itself.
- To leave an event out, delete its folder in `showcase/inbox/` before running `build.py`. To take one off the page
  later, delete it from `catalog.json`.
- After a build, set `"featured": true` in `catalog.json` on your best work (it shows first when nobody has searched).

If you'd rather add one event by hand: make a folder in `showcase/inbox/` named like `2025-12 National Day - Abu Dhabi`,
drop the files in, optionally add a `notes.txt` ("corporate gala, LED wall, laser opening"), and run `build.py`
(`build.py --ai` lets Claude write the title and summary).

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
