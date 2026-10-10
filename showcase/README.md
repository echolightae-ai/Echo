# EchoLight showcase

A static website (no server, no database). Open `site/index.html` to run it on your own computer.

| File | What it is |
|---|---|
| `site/index.html` | Hub: finder, event cards, five live motion-graphic services, contact |
| `site/e/<event>.html` | One page per event with its own SEO title, description, schema and image/video metadata |
| `site/curator.html` | Private page for you: tick clips, name the client, copy their link (not linked, hidden from Google) |
| `site/c.html` | What the client sees: only the clips you picked (hidden from Google) |
| `site/sitemap.xml`, `robots.txt` | For Google (includes image and video entries) |
| `SEO-PACK.csv` | Every page's meta title, meta description, H1, location, services |
| `SEO-ALT-TEXT.csv` | Alt text or video title for every photo and video |
| `squarespace-embed.html` | Paste into a Squarespace Code Block to show the showcase on echolight.ae |
| `squarespace-links.html` | Paste under it so Google sees links from echolight.ae to every event |
| `build/` | Scripts that regenerate everything from `curation.csv` and your labels |

## Put it online (about 10 minutes)

1. Create a free Cloudflare account, then Workers & Pages → Create → Pages → **Direct Upload**.
2. Name the project, drag the whole `site` folder in, deploy. You get a `*.pages.dev` address straight away.
3. Add the custom domain `showcase.echolight.ae` to that project and create the DNS record Cloudflare shows you (a CNAME) where echolight.ae's DNS lives.
4. In Squarespace, add a Code Block on the page where it should appear, paste `squarespace-embed.html`, and below it another Code Block with `squarespace-links.html`. Code Blocks need a Squarespace Business plan or higher.
5. In Google Search Console add `showcase.echolight.ae` and submit `https://showcase.echolight.ae/sitemap.xml`.

If you use a different address than `showcase.echolight.ae`, tell Claude: every canonical link, sitemap entry and share image is built from it.

## Client links

- To send one event: copy its address, for example `https://showcase.echolight.ae/e/dibo-showroom-opening-dubai.html`.
- To send a hand-picked set: open `/curator.html`, tick clips from any events, type the client name, press Copy link.
