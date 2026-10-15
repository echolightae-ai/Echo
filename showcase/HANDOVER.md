# EchoLight Showcase – Handover

Everything for www.echolight.ae/showcase (English) and www.echolight.ae/ar-/showcase (Arabic).
Content: **47 events, 302 photos and clips**, five services: Stage Lighting, LED Screens, Sound, 3D Mapping, Laser & Light Shows.

## 1. Put it live (Squarespace)
1. Open `embed/showcase-en.html` in a text editor, select all, copy.
2. On the `/showcase` page: **Edit → the Code Block → delete everything inside → paste.** Untick "Display Source". Save.
3. Do the same on `/ar-/showcase` with `embed/showcase-ar.html`.
4. Section padding top and bottom = 0. Preview in a normal browser tab (the editor does not run code).
5. If Squarespace says the code is too long, paste `embed/showcase-en.loader.html` (or `-ar`) instead.
6. If videos stop after clicking around the site menu, turn off AJAX loading in Squarespace site settings.

**Every time the showcase is rebuilt, replace the whole Code Block again.**

## 2. Page SEO (Page Settings → SEO)
**English, /showcase**
- SEO title: `Event Lighting, LED, Sound & Laser Shows UAE | EchoLight`
- SEO description: `Describe your event and see real EchoLight work: stage lighting, LED screens, sound, 3D mapping and laser shows across Abu Dhabi, Dubai and the UAE.`

**Arabic, /ar-/showcase**
- SEO title: `إضاءة فعاليات وشاشات LED وصوت وليزر في الإمارات | إيكو لايت`
- SEO description: `صف فعاليتك وشاهد أعمال إيكو لايت الحقيقية: إضاءة مسرح وشاشات LED وصوت وإسقاط ثلاثي الأبعاد وعروض ليزر في أبوظبي ودبي والإمارات.`

Every event, photo and clip already carries its own title, description and alt text inside the code. The "All events at a glance" list is hidden from visitors but readable by Google.
Optional: `SEO-PACK-EN.csv` / `SEO-PACK-AR.csv` have the title and description for each event, and `embed/events-en|ar/<event>.html` is a block per event, if you ever want a separate Squarespace page for an event.

## 3. What visitors get
- A finder: type the event (corporate, wedding, gala, launch...) and it recommends services and shows matching work.
- Filters by event type and by service; every service has its own interactive lab.
- Live-playing clips, full-length films on events that have them, a lightbox, WhatsApp button.
- Event pages: `www.echolight.ae/showcase#e=<event-name>` (event names are in `SEO-PACK-EN.csv`).

## 4. Private client links (curator mode)
1. Open `www.echolight.ae/showcase#curator`. A **＋** appears on every clip and on each full film.
2. Browse normally and tap ＋ on what you want (for example one 3D mapping clip and one wedding lighting clip).
3. The bar at the bottom: type the client's name and a short note, press **Copy client link**, send it on WhatsApp/email. **Preview** shows what they will see.
4. The client sees only those clips, with their name. **Clear** empties the selection, **Exit** turns curator mode off. Your picks stay saved in your browser until you clear them.
Curator mode is not linked anywhere on the page. Keep its address to yourself.

## 5. Content rules
- Service tags are honest: 3D Mapping only for real projection, Laser only for lasers or sky beams. Sound is included on every event (it is not shown as footage).
- The partner logo "Zee" must never appear. Clips showing it were removed or cut.
- Don't name clients the owner asked to keep anonymous (the Antalya event and the Dubai real estate signing gala are shown without names).
- Long videos are usually promos. They are kept full length as "films", not cut down to 5 seconds.

## 6. Adding or changing content (any Claude chat can do this)
Tell the chat: "Read showcase/CLAUDE.md and CONTENT.md in the echolightae-ai/Echo repo, branch claude/trusting-babbage-t9xuem", then send the files and say which event and service they are.
- Add files: `build/add_content.py` (existing or new event, English + Arabic text, `--film` for long promos).
- Trim, remove, move or retag a clip: `build/edit_clip.py`.
- Check for a logo or word in every clip: `build/scan_text.py` (also check by eye).
- Publish: `python3 -I showcase/build/release.py` → then replace the Code Blocks (step 1).
- `COVERAGE.csv` lists every original file and where it ended up (or why it was skipped).

## 7. Promo reel
`promo/EchoLight-Promo-Reel.mp4`: 27 s, 9:16, cut on the beat of an original track (no copyright issues), no end card.
To change it: edit the shot list at the top of `promo/make_reel.py` and run it.

## 8. Latest additions
- **Real Estate Signing Ceremony Gala, Dubai**: LED Screens (gala, corporate, launch).
- **3D Table Mapping for a Gala Dinner**: 3D Mapping on plates and table (gala, corporate, private).
- **Liwa Dates Festival Press Conference**: LED Screens for the Abu Dhabi Heritage Authority (government, corporate), 2 clips + 1 photo.

## 9. Technical notes
- Media is served free from jsDelivr out of the public GitHub repo, pinned to one commit, so old links never break.
- The GitHub repo is **public**. Anything committed there (including old versions) can be seen. Keep private documents out of it.
- Files: `embed/` (what you paste), `content/events.json` (all text and clips), `media/` (web copies), `build/` (tools), `promo/` (reel).
