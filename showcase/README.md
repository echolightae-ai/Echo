# EchoLight showcase

One block of HTML for Squarespace (English + Arabic), plus the sources that build it. Start with `INSTALL.md`.

| Path | What it is |
|---|---|
| `embed/showcase-en.html`, `showcase-ar.html` | The page. Paste into a Squarespace Code Block |
| `embed/*.loader.html` | Tiny fallback if Squarespace refuses the large block |
| `embed/events-en/`, `events-ar/` | One block per event, for optional per-event pages |
| `SEO-PACK-EN.csv`, `SEO-PACK-AR.csv` | SEO title and description for every page |
| `SEO-ALT-TEXT.csv` | Alt text for every photo and video, English and Arabic |
| `media/` | Web-sized photos and videos, served by jsDelivr |
| `build/` | Scripts that rebuild everything (events text in `events_src.py` and `events_ar.py`) |
| `curation.csv`, `inventory.csv` | Early tagging and metadata of the source files |
