# Put the showcase on echolight.ae/showcase

You need Squarespace **Business** plan or higher (Code Blocks).

## English page: www.echolight.ae/showcase
1. **Pages → + → Blank page.** Title it `Showcase`. Page settings → **URL slug: `showcase`**.
2. **Page settings → SEO.** Copy the first row of `SEO-PACK-EN.csv` (Showcase hub): *seo_title* into SEO Title, *seo_description* into SEO Description.
3. Edit the page → **Add Block → Code.** Open `embed/showcase-en.html` in any text editor (Notepad is fine), select all, copy, paste into the block. **Untick "Display Source"**, apply, save.
4. Edit the section → Format → set top and bottom padding to **0** so the dark block touches the edges. The block fills the whole width by itself.
5. Preview in a normal browser tab (the Squarespace editor does not run Code Blocks).

## Arabic page: www.echolight.ae/ar-/showcase
Same steps on the Arabic site, with `embed/showcase-ar.html` and the first row of `SEO-PACK-AR.csv`.

## If Squarespace says the code is too long
Use `embed/showcase-en.loader.html` (or `-ar`) instead. It is a few lines and loads the same page.

## Links for clients
- One event: `https://www.echolight.ae/showcase#e=al-nayef-group-awards-night` (the event's name is in `SEO-PACK-EN.csv`, last part of its URL).
- A hand-picked set: open `https://www.echolight.ae/showcase#curator`, open events, tick the clips you discussed, type the client's name, press **Copy link**. They see only those clips.
- The curator is not linked from anywhere on the page. Keep its address to yourself.

## Extra SEO (optional, recommended for your best events)
Squarespace can only give a page one title and one description. For your strongest events, add a page per event:
1. New blank page, URL slug `showcase/<event-name>` (the *squarespace_url* column in `SEO-PACK-EN.csv`).
2. SEO Title and Description from the same row.
3. Code Block with `embed/events-en/<event-name>.html`.
Do the Arabic ones under `/ar-/showcase/`. `SEO-ALT-TEXT.csv` lists the alt text of every photo and video in English and Arabic.

## If something looks off
- Videos or animations stop after you click around the menu: turn off AJAX loading in your Squarespace site settings.
- Media comes from the free jsDelivr CDN (your public GitHub repo, pinned to one commit). New clips mean a new build: send them to Claude.
