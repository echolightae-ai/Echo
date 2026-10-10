"""Generate the static showcase: hub, one SEO page per event, curator, client page, sitemaps and SEO pack.

Usage: python3 -I build_site.py <site_dir> [site_url]
Reads  <site_dir>/data/events.json (from assemble.py + cut_shots.py), writes pages next to it.
"""
import sys, os, json, html, csv, re
sys.path.insert(0, os.path.dirname(__file__))
import events_src as E
site = sys.argv[1]; URL = (sys.argv[2] if len(sys.argv) > 2 else "https://showcase.echolight.ae").rstrip("/")
events = json.load(open(f"{site}/data/events.json"))
WA = "971567220533"
SVN = {"lighting": "Stage Lighting", "led": "LED Screens", "sound": "Sound", "mapping": "3D Mapping", "laser": "Laser & Light Shows"}
SVP = {"lighting": "stage and architectural lighting", "led": "LED screen staging", "sound": "line-array sound", "mapping": "3D projection mapping", "laser": "laser and sky-beam light show"}
TN = {k: v[0] for k, v in E.TYPES.items()}
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
esc = lambda s: html.escape(str(s), quote=True)
def mlabel(m): return f"{MON[int(m[5:7]) - 1]} {m[:4]}" if m else ""
def trim(s, n):
    if len(s) <= n: return s
    c = s[:n - 1].rsplit(" ", 1)[0].rstrip(" ,;:-"); return c + "…"
def where(e): return ", ".join(x for x in [e.get("venue"), e.get("city")] if x and x != "Undisclosed venue" and x != e.get("city") or x == e.get("city"))
def place(e):
    v = e.get("venue") or ""; c = e.get("city") or ""
    if v in ("", "Undisclosed venue"): return c
    if c and (c.startswith(v) or v in c or c in v): return v if c in v else c
    return f"{v}, {c}" if c else v

# ---- enrich: alt text, titles, urls, covers ------------------------------------------------
for i, e in enumerate(events):
    e["place"] = place(e); e["label"] = mlabel(e.get("month", ""))
    e["ty"] = [TN[t] for t in e["types"]]
    e["url"] = f"e/{e['slug']}.html"
    n_p = n_v = 0
    for c in e["clips"]:
        s = c["svc"][0] if c["svc"] else e["svc"][0]; ph = SVP.get(s, "event lighting")
        loc = f" at {e['place']}" if e["place"] else ""
        if c["t"] == "p": n_p += 1; c["alt"] = f"{e['title']}: {ph}{loc} by EchoLight (photo {n_p})"
        else: n_v += 1; c["alt"] = f"{e['title']}: {ph}{loc} by EchoLight (video {n_v})"
        c["title"] = e["title"]
    cover = next((c for c in e["clips"] if c["t"] != "p" and c.get("star")), None) or next((c for c in e["clips"] if c["t"] != "p"), None) or e["clips"][0]
    e["cover"] = cover; e["vcover"] = next((c for c in e["clips"] if c["t"] != "p"), None)
    months = sorted(x for x in [e.get("month", "")] if x)
    e["rank"] = (100 if e.get("hero") else 0) + (int(e["month"][:4]) * 12 + int(e["month"][5:7]) - 24000 if e.get("month") else 0)
    e["metaTitle"] = trim(f"{e['title']} | EchoLight", 60) if len(f"{e['title']} | EchoLight {e.get('city','')}") > 60 else f"{e['title']} | EchoLight {e.get('city','')}".strip()
    e["metaDesc"] = trim(e["desc"], 155)
events.sort(key=lambda e: -e["rank"])

def media(c, root=""):
    stem = c["k"] if c["t"] == "s" else c.get("f")
    if c["t"] == "p": return f"{root}assets/img/{stem}.jpg", f"{root}assets/img/{stem}.jpg"
    return f"{root}assets/v/{stem}.mp4", f"{root}assets/v/{stem}.jpg"
def absu(p): return f"{URL}/{p}"
def iso_dur(d): d = int(round(d or 5)); return f"PT{d // 60}M{d % 60}S" if d >= 60 else f"PT{d}S"
def up(e): return (e.get("month") or "2026-01") + "-01"

HEAD = """<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{root}assets/css/site.css"><meta name="theme-color" content="#05060a">"""
def waurl(msg): return f"https://wa.me/{WA}?text=" + __import__("urllib.parse").parse.quote(msg)

# ---- event pages ----------------------------------------------------------------------------
def event_page(e, i):
    root = "../"; slug = e["slug"]; img, _ = media(e["cover"], "")
    tiles = []
    for n, c in enumerate(e["clips"]):
        src, post = media(c, root); ratio = max(0.58, min(1.7, c["w"] / c["h"]))
        vb = f'<span class="vbadge">▶ {int(round(c.get("d") or 5))}s</span>' if c["t"] != "p" else ""
        tiles.append(f'<a class="tile{" is-v" if c["t"] != "p" else ""}" href="{src}" data-src="{src}" style="aspect-ratio:{ratio:.3f}" aria-label="{esc(c["alt"])}"><img src="{post}" alt="{esc(c["alt"])}" width="{c["w"]}" height="{c["h"]}" {"loading=\"lazy\" " if n > 5 else ""}decoding="async">{vb}<span class="cap">{esc(e["title"])}</span></a>')
    rel = sorted((x for x in events if x is not e), key=lambda x: -(len(set(x["types"]) & set(e["types"])) * 3 + len(set(x["svc"]) & set(e["svc"])) + (2 if x.get("hero") else 0) - (5 if x.get("old") else 0)))[:3]
    relh = "".join(card(x, "../") for x in rel)
    chips = "".join(f'<li><a href="{root}index.html#s={s}">{SVN[s]}</a></li>' for s in e["svc"]) + "".join(f'<li><a href="{root}index.html#t={t}">{TN[t]}</a></li>' for t in e["types"])
    meta = "".join(f"<li>{esc(x)}</li>" for x in [e["place"], e["label"]] if x)
    full = f'<a class="btn btn-ghost small" href="{root}assets/v/{e["fullClip"]}.mp4" data-full>▶ Watch the full show ({e["fullDur"] // 60}:{e["fullDur"] % 60:02d})</a>' if e.get("fullClip") else ""
    vids = [c for c in e["clips"] if c["t"] != "p"]; pics = [c for c in e["clips"] if c["t"] == "p"]
    ld = [{"@type": "BreadcrumbList", "itemListElement": [{"@type": "ListItem", "position": 1, "name": "EchoLight Showcase", "item": absu("index.html")}, {"@type": "ListItem", "position": 2, "name": e["title"], "item": absu(e["url"])}]},
          {"@type": "CollectionPage", "@id": absu(e["url"]), "name": e["title"], "description": e["desc"], "url": absu(e["url"]), "inLanguage": "en", "isPartOf": {"@type": "WebSite", "name": "EchoLight Showcase", "url": absu("index.html")},
           "about": [SVN[s] for s in e["svc"]], "primaryImageOfPage": {"@type": "ImageObject", "contentUrl": absu(media(e["cover"], "")[1]), "caption": e["cover"]["alt"]},
           "provider": {"@type": "Organization", "name": "EchoLight", "url": "https://www.echolight.ae", "telephone": "+971567220533"}}]
    for c in pics[:12]: ld.append({"@type": "ImageObject", "contentUrl": absu(media(c, "")[0]), "name": c["alt"], "caption": c["alt"], "creator": {"@type": "Organization", "name": "EchoLight"}, "license": "https://www.echolight.ae"})
    for n, c in enumerate(vids):
        ld.append({"@type": "VideoObject", "name": f"{e['title']} (video {n + 1})", "description": f"{e['desc']} Clip {n + 1}: {SVP.get((c['svc'] or e['svc'])[0], 'event lighting')}.", "thumbnailUrl": absu(media(c, "")[1]), "contentUrl": absu(media(c, "")[0]), "uploadDate": up(e), "duration": iso_dur(c.get("d")), "publisher": {"@type": "Organization", "name": "EchoLight"}})
    if e.get("fullClip"): ld.append({"@type": "VideoObject", "name": f"{e['title']}: full show", "description": e["desc"], "thumbnailUrl": absu(media(e["cover"], "")[1]), "contentUrl": absu(f"assets/v/{e['fullClip']}.mp4"), "uploadDate": up(e), "duration": iso_dur(e["fullDur"]), "publisher": {"@type": "Organization", "name": "EchoLight"}})
    payload = {"title": e["title"], "fullClip": e.get("fullClip"), "clips": [{k: c[k] for k in ("k", "t", "f", "w", "h", "d", "alt", "title") if k in c} for c in e["clips"]]}
    return f"""<!doctype html><html lang="en"><head>{HEAD.format(root=root)}
<title>{esc(e['metaTitle'])}</title><meta name="description" content="{esc(e['metaDesc'])}"><link rel="canonical" href="{absu(e['url'])}"><meta name="robots" content="index,follow,max-image-preview:large,max-video-preview:-1">
<meta property="og:type" content="website"><meta property="og:site_name" content="EchoLight"><meta property="og:title" content="{esc(e['metaTitle'])}"><meta property="og:description" content="{esc(e['metaDesc'])}"><meta property="og:url" content="{absu(e['url'])}"><meta property="og:image" content="{absu(media(e['cover'], '')[1])}"><meta property="og:image:alt" content="{esc(e['cover']['alt'])}">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{esc(e['metaTitle'])}"><meta name="twitter:description" content="{esc(e['metaDesc'])}"><meta name="twitter:image" content="{absu(media(e['cover'], '')[1])}">
<script type="application/ld+json">{json.dumps({"@context": "https://schema.org", "@graph": ld}, ensure_ascii=False)}</script></head>
<body><div class="wrap">
<nav class="crumbs" aria-label="Breadcrumb"><a href="{root}index.html#work">All EchoLight work</a> / <span>{esc(e['title'])}</span></nav>
<header class="ehead"><p class="eyebrow">{esc(" · ".join(e['ty']))}</p><h1>{esc(e['title'])}</h1><p class="dek">{esc(e['dek'])}</p><ul class="meta">{meta}</ul><ul class="chiprow">{chips}</ul></header>
<section class="story"><p>{esc(e['body'])}</p><div class="acts"><a class="btn btn-wa" target="_blank" rel="noopener" href="{waurl('Hello EchoLight, I saw ' + e['title'] + ' on your showcase and I would like something like it for my event. Date / venue / guests: ')}">Plan something like this</a>{full}<button class="btn btn-ghost small" type="button" data-copy>Copy link to this page</button></div></section>
<section class="gal" aria-label="Photos and videos from {esc(e['title'])}">{"".join(tiles)}</section>
<section class="rel"><h2>More like this</h2><div class="cards">{relh}</div></section>
</div>
<script>window.ROOT="{root}";window.EVENT={json.dumps(payload, ensure_ascii=False)};</script>
<script src="{root}assets/js/common.js"></script><script src="{root}assets/js/event.js"></script></body></html>"""

def card(e, root=""):
    cov = e["cover"]; v = e["vcover"]; poster = media(cov, root)[1]
    vattr = f' data-v="{media(v, root)[0]}"' if v else ""
    nv = sum(1 for c in e["clips"] if c["t"] != "p"); badge = f'<span class="badge">▶ {nv} video{"s" if nv != 1 else ""}</span>' if nv else ""
    sub = " · ".join(x for x in [e["place"], e["label"]] if x)
    return (f'<article class="ecard" data-slug="{e["slug"]}"{vattr}><a href="{root}{e["url"]}" aria-label="{esc(e["title"])}"><div class="cov"><img src="{poster}" alt="{esc(cov["alt"])}" width="{cov["w"]}" height="{cov["h"]}" loading="lazy" decoding="async">{badge}'
            f'<div class="eb"><span class="ty">{esc(e["ty"][0])}</span><h3>{esc(e["title"])}</h3><p>{esc(trim(e["dek"], 90))}</p><span class="mt">{esc(sub)}</span></div></div></a></article>')

# ---- hub ------------------------------------------------------------------------------------
def hub():
    counts = {s: sum(1 for e in events if s in e["svc"]) for s in SVN}
    SVC = {
     "lighting": ("Stage Lighting", "Moving heads, washes and pattern projection, programmed cue by cue so the room changes with the moment. From conference stages to ballroom wedding floors.", ["Moving heads", "Gobo patterns", "Architectural light", "Cue programming"]),
     "led": ("LED Screens", "High-resolution LED walls for conferences, launches and ceremonies. Delivered, operated and struck by our crew, with content mapped to the real pixel grid.", ["Fine-pitch walls", "Content mapping", "Stage integration", "On-site operator"]),
     "sound": ("Sound", "Line-array coverage and digital consoles tuned to the room, so every seat hears clearly: speech, music and wireless systems for conferences and celebrations.", ["Line arrays", "Digital consoles", "Wireless mics", "Conference audio"]),
     "mapping": ("3D Mapping", "Projection onto buildings, objects, frames and stage sets. We survey the surface, fit the content to every window and ledge, then blend the edges.", ["Facade mapping", "Object mapping", "Warp & edge blend", "Content design"]),
     "laser": ("Laser & Light Shows", "High-power lasers, sky beams and cold-spark effects for grand entrances, reveals and outdoor nights that can be seen across a whole site.", ["Sky beams", "Laser scanning", "Cold sparks", "Show control"])}
    sv = "".join(f'<article class="svc" id="svc-{k}"><div><p class="eyebrow">0{i + 1} / 05</p><h3>{v[0]}</h3><p>{v[1]}</p><ul>{"".join(f"<li>{x}</li>" for x in v[3 if False else 2])}</ul><a class="go" href="#work" data-svc="{k}">See {counts[k]} event{"s" if counts[k] != 1 else ""} with {v[0]} →</a></div><div class="fx"><canvas data-fx="{k}" role="img" aria-label="Live animation of {v[0].lower()}"></canvas></div></article>' for i, (k, v) in enumerate(SVC.items()))
    chips = "".join(f'<button class="chip" type="button" data-pick="{k}"><i style="background:{c}"></i>{TN[k]}</button>' for k, c in [("corporate", "#3da9ff"), ("wedding", "#ffb86b"), ("gala", "#ffd27a"), ("launch", "#c04dff"), ("government", "#2ee59d"), ("show", "#ff3df0")])
    hubdata = [{"slug": e["slug"], "types": e["types"], "svc": e["svc"], "hero": bool(e.get("hero")), "old": bool(e.get("old")), "clips": len(e["clips"]), "rank": e["rank"]} for e in events]
    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "WebSite", "name": "EchoLight Showcase", "url": absu("index.html"), "inLanguage": "en", "publisher": {"@type": "Organization", "name": "EchoLight"}},
        {"@type": "ProfessionalService", "name": "EchoLight", "alternateName": "إيكو لايت", "url": "https://www.echolight.ae", "telephone": "+971567220533", "areaServed": "AE", "address": {"@type": "PostalAddress", "addressLocality": "Abu Dhabi", "addressCountry": "AE"}, "description": "Event production specialised in AV: stage lighting, LED screens, sound, 3D projection mapping, laser and light shows across the UAE.", "aggregateRating": {"@type": "AggregateRating", "ratingValue": "5.0", "bestRating": "5"}, "hasOfferCatalog": {"@type": "OfferCatalog", "name": "Event AV services", "itemListElement": [{"@type": "Offer", "itemOffered": {"@type": "Service", "name": v[0], "description": v[1]}} for v in SVC.values()]}},
        {"@type": "ItemList", "name": "EchoLight events", "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": absu(e["url"]), "name": e["title"]} for i, e in enumerate(events)]}]}
    t = "Event Lighting, LED, Sound & Laser Shows UAE | EchoLight"; d = "Describe your event and see real EchoLight work: stage lighting, LED screens, sound, 3D mapping and laser shows across Abu Dhabi, Dubai and the UAE."
    return f"""<!doctype html><html lang="en"><head>{HEAD.format(root="")}
<title>{t}</title><meta name="description" content="{d}"><link rel="canonical" href="{absu('index.html')}"><meta name="robots" content="index,follow,max-image-preview:large,max-video-preview:-1">
<meta property="og:type" content="website"><meta property="og:site_name" content="EchoLight"><meta property="og:title" content="{t}"><meta property="og:description" content="{d}"><meta property="og:url" content="{absu('index.html')}"><meta property="og:image" content="{absu(media(events[0]['cover'], '')[1])}">
<meta name="twitter:card" content="summary_large_image"><script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script></head>
<body>
<section class="hero" aria-labelledby="h1"><canvas id="hero-canvas" aria-hidden="true"></canvas><div class="hero-fade" aria-hidden="true"></div><div class="hero-inner">
<p class="eyebrow">EchoLight · Abu Dhabi · UAE-wide</p><h1 id="h1">Show us your event. <em>We'll show you the proof.</em></h1>
<p class="lead">Type what you're planning. We'll light up the work we've done for events like yours, and tell you what we'd build.</p>
<form class="finder" id="finder" role="search" autocomplete="off"><label for="q" class="sr">Describe your event</label><div class="finder-box"><input id="q" name="q" type="text" inputmode="search" enterkeyhint="search" maxlength="120" placeholder=""><button class="btn btn-go" type="submit">Show me</button></div></form>
<div class="chips" role="group" aria-label="Quick picks">{chips}</div>
<div class="stats"><div><b>400+</b><span>events produced</span></div><div><b>50+</b><span>premium venues</span></div><div><b>14+</b><span>major clients</span></div><div><b>5.0 ★</b><span>Google rating</span></div></div></div></section>
<main>
<section class="work" id="work" aria-labelledby="w-title"><div class="wrap"><p class="eyebrow">The proof</p><h2 id="w-title">Real events. Real rigs. Real nights.</h2><p class="sub" id="g-sub"></p>
<div class="reco" id="reco" hidden aria-live="polite"></div>
<div class="filters"><div class="f-row" id="f-types" role="group" aria-label="Event type"></div><div class="f-row" id="f-svc" role="group" aria-label="Service"></div></div>
<p class="count" id="count" aria-live="polite"></p>
<div class="cards" id="cards">{"".join(card(e) for e in events)}</div>
<p class="empty" id="empty" hidden>Nothing under that exact combination yet. Try removing a filter or message us on WhatsApp.</p></div></section>
<section class="services" id="services" aria-labelledby="s-title"><div class="wrap"><p class="eyebrow">What we bring</p><h2 id="s-title">Five disciplines. One crew.</h2>{sv}</div></section>
<section class="contact" id="contact" aria-labelledby="c-title"><div class="wrap"><h2 id="c-title">Let's light your date.</h2><p class="sub">Send us the date, the venue and a rough idea. We reply on WhatsApp with a plan and a quote.</p>
<div class="c-actions"><a class="btn btn-wa big" target="_blank" rel="noopener" href="{waurl('Hello EchoLight, I would like to plan an event. Date / venue / guests: ')}">Chat on WhatsApp</a><a class="btn btn-ghost big" href="tel:+971567220533">+971 56 722 0533</a></div>
<p class="fine"><a href="https://www.echolight.ae" rel="noopener">echolight.ae</a> · <a href="https://instagram.com/echolightae" rel="noopener">@echolightae</a> · Anywhere in the UAE</p></div></section>
</main>
<script>window.ROOT="";window.HUB={json.dumps(hubdata)};</script>
<script src="assets/js/common.js"></script><script src="assets/js/beams.js"></script><script src="assets/js/fx.js"></script><script src="assets/js/hub.js"></script></body></html>"""

def curator():
    allj = [{"title": e["title"], "city": e["city"], "venue": e["venue"], "clips": [{k: c[k] for k in ("k", "t", "f", "w", "h", "d", "alt") if k in c} for c in e["clips"]]} for e in events]
    return f"""<!doctype html><html lang="en"><head>{HEAD.format(root="")}<title>Curator | EchoLight</title><meta name="robots" content="noindex,nofollow"></head><body><div class="wrap"><div class="cur">
<div class="col"><h1>Build a client page</h1><p class="sub">Open an event, tick the clips you discussed, name the client, copy the link. They see only those clips. This page is not linked anywhere and is hidden from search engines.</p><div id="list" class="col"></div></div>
<aside class="panel"><strong id="cnt">0 clips selected</strong><div class="sel" id="sel"></div><label class="sr" for="client">Client name</label><input id="client" placeholder="Client or company (optional)"><label class="sr" for="note">Note</label><textarea id="note" rows="3" placeholder="A short note, e.g. the reference videos we spoke about"></textarea>
<input id="out" readonly placeholder="Your link appears here"><div class="acts" style="display:flex;gap:8px;flex-wrap:wrap"><button class="btn btn-go small" id="copy" type="button">Copy link</button><a class="btn btn-ghost small" id="open" target="_blank" rel="noopener">Preview</a><button class="btn btn-ghost small" id="clear" type="button">Clear</button></div></aside></div></div>
<script>window.ROOT="";window.ALL={json.dumps(allj, ensure_ascii=False)};</script><script src="assets/js/common.js"></script><script src="assets/js/curator.js"></script></body></html>"""

def clientpage():
    allj = [{"title": e["title"], "city": e["city"], "venue": e["venue"], "clips": [{k: c[k] for k in ("k", "t", "f", "w", "h", "d", "alt") if k in c} for c in e["clips"]]} for e in events]
    return f"""<!doctype html><html lang="en"><head>{HEAD.format(root="")}<title>Selected for you | EchoLight</title><meta name="robots" content="noindex,nofollow"></head><body><div class="wrap client">
<p class="eyebrow">EchoLight · Abu Dhabi</p><h1 id="h">Selected for you</h1><p class="note" id="n">Reference clips from recent EchoLight events.</p><div class="gal" id="g"></div>
<a class="btn btn-wa big" id="wa" target="_blank" rel="noopener">Talk to EchoLight on WhatsApp</a></div>
<script>window.ROOT="";window.ALL={json.dumps(allj, ensure_ascii=False)};</script><script src="assets/js/common.js"></script><script src="assets/js/client.js"></script></body></html>"""

# ---- write ----------------------------------------------------------------------------------
os.makedirs(f"{site}/e", exist_ok=True)
for i, e in enumerate(events): open(f"{site}/e/{e['slug']}.html", "w").write(event_page(e, i))
open(f"{site}/index.html", "w").write(hub()); open(f"{site}/curator.html", "w").write(curator()); open(f"{site}/c.html", "w").write(clientpage())
open(f"{site}/robots.txt", "w").write(f"User-agent: *\nAllow: /\nDisallow: /curator.html\nDisallow: /c.html\n\nSitemap: {URL}/sitemap.xml\n")
sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1" xmlns:video="http://www.google.com/schemas/sitemap-video/1.1">',
      f'<url><loc>{URL}/index.html</loc><changefreq>weekly</changefreq><priority>1.0</priority></url>']
for e in events:
    u = f'<url><loc>{URL}/{e["url"]}</loc><changefreq>monthly</changefreq><priority>0.8</priority>'
    for c in [c for c in e["clips"] if c["t"] == "p"][:20]: u += f'<image:image><image:loc>{URL}/{media(c, "")[0]}</image:loc><image:caption>{esc(c["alt"])}</image:caption><image:title>{esc(e["title"])}</image:title></image:image>'
    for n, c in enumerate([c for c in e["clips"] if c["t"] != "p"]): u += f'<video:video><video:thumbnail_loc>{URL}/{media(c, "")[1]}</video:thumbnail_loc><video:title>{esc(e["title"])} (video {n + 1})</video:title><video:description>{esc(e["metaDesc"])}</video:description><video:content_loc>{URL}/{media(c, "")[0]}</video:content_loc><video:duration>{int(round(c.get("d") or 5))}</video:duration><video:family_friendly>yes</video:family_friendly></video:video>'
    sm.append(u + "</url>")
open(f"{site}/sitemap.xml", "w").write("\n".join(sm + ["</urlset>"]))
with open(f"{site}/../SEO-PACK.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["page", "url", "meta_title", "meta_description", "h1", "types", "services", "place", "images", "videos"])
    w.writerow(["Hub", f"{URL}/index.html", "Event Lighting, LED, Sound & Laser Shows UAE | EchoLight", "Describe your event and see real EchoLight work: stage lighting, LED screens, sound, 3D mapping and laser shows across Abu Dhabi, Dubai and the UAE.", "Show us your event. We'll show you the proof.", "", "all", "UAE", "", ""])
    for e in events: w.writerow(["Event", f"{URL}/{e['url']}", e["metaTitle"], e["metaDesc"], e["title"], "; ".join(e["ty"]), "; ".join(SVN[s] for s in e["svc"]), e["place"], sum(1 for c in e["clips"] if c["t"] == "p"), sum(1 for c in e["clips"] if c["t"] != "p")])
with open(f"{site}/../SEO-ALT-TEXT.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["event", "file", "type", "alt_or_video_title"])
    for e in events:
        for c in e["clips"]:
            p, _ = media(c, ""); w.writerow([e["title"], p, "photo" if c["t"] == "p" else "video", c["alt"]])
print(len(events), "event pages;", sum(len(e["clips"]) for e in events), "clips")
over = [(e["slug"], len(e["metaTitle"]), len(e["metaDesc"])) for e in events if len(e["metaTitle"]) > 60 or len(e["metaDesc"]) > 155]
print("over-length meta:", over)

# ---- Squarespace helpers --------------------------------------------------------------------
open(f"{site}/../squarespace-embed.html", "w").write(f"""<!-- EchoLight showcase: paste into a Squarespace Code Block (Add Block > Code), untick "Display Source". -->
<iframe id="echolight-showcase" src="{URL}/index.html" title="EchoLight event showcase" loading="lazy" style="width:100%;height:1400px;border:0;display:block;background:#05060a" allow="autoplay; fullscreen"></iframe>
<script>
window.addEventListener("message", function (e) {{
  if (e.origin !== "{URL}" || !e.data || !e.data.echolightHeight) return;
  document.getElementById("echolight-showcase").style.height = e.data.echolightHeight + "px";
}});
</script>
""")
li = "\n".join(f'  <li><a href="{URL}/{e["url"]}">{esc(e["title"])}</a>: {esc(e["dek"])}</li>' for e in events)
open(f"{site}/../squarespace-links.html", "w").write(f"""<!-- Paste into a second Squarespace Code Block under the embed. It gives Google plain links from echolight.ae to every event page. -->
<nav aria-label="EchoLight events" style="max-width:1100px;margin:32px auto;padding:0 16px;font:15px/1.6 system-ui,sans-serif">
<h2 style="font-size:1.2rem">EchoLight events</h2>
<ul style="columns:2 320px;padding-left:18px">
{li}
</ul>
</nav>
""")
print("squarespace helpers written")
