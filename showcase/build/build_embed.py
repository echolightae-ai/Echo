"""Build the Squarespace embed blocks (English + Arabic) and per-event page blocks.

Usage: python3 -I build_embed.py <showcase_dir> <media_base_url>
Reads  site/data/events.json (+ site/assets/css/site.css), writes <showcase_dir>/embed/.
Each output is ONE block of HTML (CSS + markup + JS inline); media is loaded from <media_base_url>.
"""
import sys, os, re, json, csv, html, urllib.parse
sys.path.insert(0, os.path.dirname(__file__))
import events_src as E
from events_ar import AR, UI_AR
root = sys.argv[1]; MEDIA = sys.argv[2].rstrip("/") + "/"
HUB = {"en": "https://www.echolight.ae/showcase", "ar": "https://www.echolight.ae/ar-/showcase"}
events = json.load(open(f"{root}/site/data/events.json"))
SRC = os.path.join(os.path.dirname(__file__), "embed_src")
esc = lambda s: html.escape(str(s), quote=True)
def trim(s, n):
    if len(s) <= n: return s
    return s[:n - 1].rsplit(" ", 1)[0].rstrip(" ,;:-") + "…"

# ---- shared copy ----------------------------------------------------------------------------
SVN = {"en": {"lighting": "Stage Lighting", "led": "LED Screens", "sound": "Sound", "mapping": "3D Mapping", "laser": "Laser & Light Shows"},
       "ar": {"lighting": "إضاءة المسارح", "led": "شاشات LED", "sound": "الصوتيات", "mapping": "الإسقاط ثلاثي الأبعاد", "laser": "عروض الليزر والضوء"}}
PH = {"en": {"lighting": "stage and architectural lighting", "led": "LED screen staging", "sound": "line-array sound", "mapping": "3D projection mapping", "laser": "laser and sky-beam light show"},
      "ar": {"lighting": "إضاءة مسرح ومعمارية", "led": "شاشات LED", "sound": "نظام صوت Line Array", "mapping": "إسقاط ثلاثي الأبعاد", "laser": "أشعة وليزر وعرض ضوئي"}}
TN = {"en": {k: v[0] for k, v in E.TYPES.items()}, "ar": {k: v[1] for k, v in E.TYPES.items()}}
SVC = {"en": {
  "lighting": ("Stage Lighting", "Moving heads, washes and pattern projection, programmed cue by cue so the room changes with the moment. From conference stages to ballroom wedding floors.", ["Moving heads", "Gobo patterns", "Architectural light", "Cue programming"]),
  "led": ("LED Screens", "High-resolution LED walls for conferences, launches and ceremonies. Delivered, operated and struck by a dedicated LED team, with content mapped to the real pixel grid.", ["Fine-pitch walls", "Content mapping", "Stage integration", "On-site operator"]),
  "sound": ("Sound", "Line-array coverage and digital consoles tuned to the room, so every seat hears clearly. Sound is part of every EchoLight event, from keynotes to first dances.", ["Line arrays", "Digital consoles", "Wireless mics", "Conference audio"]),
  "mapping": ("3D Mapping", "Projection onto buildings, objects, frames and stage sets. We survey the surface, fit the content to every window and ledge, then blend the edges.", ["Facade mapping", "Object mapping", "Warp & edge blend", "Content design"]),
  "laser": ("Laser & Light Shows", "High-power lasers, sky beams and cold-spark effects for grand entrances, reveals and outdoor nights that can be seen across a whole site.", ["Sky beams", "Laser scanning", "Cold sparks", "Show control"])},
 "ar": {
  "lighting": ("إضاءة المسارح", "رؤوس متحركة وإضاءة غامرة وإسقاط أنماط، مبرمجة مشهداً بمشهد لتتغيّر القاعة مع اللحظة. من منصات المؤتمرات إلى أرضيات الأعراس.", ["رؤوس متحركة", "أنماط غوبو", "إضاءة معمارية", "برمجة المشاهد"]),
  "led": ("شاشات LED", "جدران LED عالية الدقة للمؤتمرات والإطلاقات والحفلات. يوفّرها ويشغّلها ويفكّكها فريق LED متخصص، مع محتوى مضبوط على شبكة البكسل الفعلية.", ["جدران دقيقة البكسل", "ضبط المحتوى", "دمج مع المنصة", "مشغّل في الموقع"]),
  "sound": ("الصوتيات", "تغطية Line Array ومنصات رقمية مضبوطة على القاعة ليسمع كل مقعد بوضوح. الصوت جزء من كل فعالية لإيكو لايت، من الكلمات الرئيسية إلى الرقصة الأولى.", ["Line Array", "منصات رقمية", "مايكروفونات لاسلكية", "صوت المؤتمرات"]),
  "mapping": ("الإسقاط ثلاثي الأبعاد", "إسقاط على المباني والأجسام والإطارات وديكورات المسرح. نمسح السطح ونضبط المحتوى على كل نافذة وحافة ثم نمزج الأطراف.", ["إسقاط الواجهات", "إسقاط الأجسام", "Warp وEdge Blend", "تصميم المحتوى"]),
  "laser": ("عروض الليزر والضوء", "ليزر عالي القدرة وأشعة سماء وشرارات باردة للدخولات الكبرى واللحظات الكاشفة والليالي المفتوحة التي تُرى من الموقع كله.", ["أشعة السماء", "مسح الليزر", "شرارات باردة", "التحكم بالعرض"])}}
UI = {"en": {"eyebrow": "EchoLight · Abu Dhabi · UAE-wide", "h1a": "Show us your event.", "h1b": "We'll show you the proof.", "lead": "Type what you're planning. We'll light up the work we've done for events like yours, and tell you what we'd build.", "go": "Show me", "qlabel": "Describe your event",
        "ev": "The proof", "evh": "Real events. Real rigs. Real nights.", "svce": "What we specialise in", "svch": "Five specialisms. A dedicated team for each.", "svcsub": "EchoLight is built around five disciplines, and each one has its own specialist team. Try them below: every lab ends with a message to us describing what you built.", "idx": "All events at a glance", "ctah": "Let's light your date.", "ctas": "Send us the date, the venue and a rough idea. We reply on WhatsApp with a plan and a quote.", "wa": "Chat on WhatsApp", "area": "Anywhere in the UAE",
        "stats": [("400+", "events produced"), ("100+", "venues"), ("34+", "clients"), ("5.0 ★", "Google rating")], "back": "← All EchoLight work", "plan": "Plan something like this", "film": "Full film", "full": "▶ Watch the full film", "copy": "Copy link to this page", "more": "More like this", "see": "See {n} {w} with {s} →", "empty": "Nothing under that exact combination yet. Try removing a filter or message us on WhatsApp.", "events": "events", "event": "event", "videos": "videos", "video": "video",
        "cur_h": "Build a client page", "cur_s": "Open an event, tick the clips you discussed, name the client, copy the link. They see only those clips. This page is not linked anywhere on the site.", "cur_c": "Client or company (optional)", "cur_n": "A short note, e.g. the reference videos we spoke about", "cur_o": "Your link appears here", "cur_p": "Preview", "cur_x": "Clear", "reel": "Quick picks"},
      "ar": {"eyebrow": "إيكو لايت · أبوظبي · كل الإمارات", "h1a": "أخبرنا عن فعاليتك.", "h1b": "ونُريك الإثبات.", "lead": "اكتب ما تخطّط له، وسنُضيء لك أعمالنا في فعاليات تشبه فعاليتك، ونخبرك بما كنّا سنبنيه.", "go": "أرني", "qlabel": "صف فعاليتك",
        "ev": "الإثبات", "evh": "فعاليات حقيقية. أجهزة حقيقية. ليالٍ حقيقية.", "svce": "ما نتخصص فيه", "svch": "خمسة تخصصات، ولكل تخصص فريقه المتخصص.", "svcsub": "تقوم إيكو لايت على خمسة تخصصات، ولكل تخصص فريقه المتخصص. جرّبها بالأسفل: كل مختبر ينتهي برسالة إلينا تصف ما صممته.", "idx": "كل الفعاليات في لمحة", "ctah": "لنُضئ موعدك.", "ctas": "أرسل لنا التاريخ والموقع وفكرة تقريبية. نردّ عبر واتساب بخطة وعرض سعر.", "wa": "تحدّث معنا عبر واتساب", "area": "في أي مكان في الإمارات",
        "stats": [("+400", "فعالية أنتجناها"), ("+100", "موقع"), ("+34", "عميل"), ("★ 5.0", "تقييم جوجل")], "back": "→ كل أعمال إيكو لايت", "plan": "خطّط لشيء مثل هذا", "film": "الفيلم الكامل", "full": "▶ شاهد الفيلم كاملاً", "copy": "انسخ رابط هذه الصفحة", "more": "المزيد مثل هذا", "see": "شاهد {n} {w} {s} ←", "empty": "لا شيء بهذا الجمع بعد. جرّب إزالة أحد المرشّحات أو راسلنا عبر واتساب.", "events": "فعالية", "event": "فعالية", "videos": "فيديو", "video": "فيديو",
        "cur_h": "أنشئ صفحة لعميل", "cur_s": "افتح فعالية، حدّد المقاطع التي ناقشتموها، اكتب اسم العميل وانسخ الرابط. سيرى هذه المقاطع فقط. هذه الصفحة غير مرتبطة بأي مكان في الموقع.", "cur_c": "العميل أو الشركة (اختياري)", "cur_n": "ملاحظة قصيرة، مثلاً الفيديوهات المرجعية التي تحدثنا عنها", "cur_o": "يظهر رابطك هنا", "cur_p": "معاينة", "cur_x": "مسح", "reel": "اختيارات سريعة"}}
CHIPS = [("corporate", "#3da9ff"), ("wedding", "#ffb86b"), ("gala", "#ffd27a"), ("launch", "#c04dff"), ("government", "#2ee59d"), ("show", "#ff3df0")]
MON_EN = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# ---- enrich ---------------------------------------------------------------------------------
def place_en(e):
    v = e.get("venue") or ""; c = e.get("city") or ""
    if v in ("", "Undisclosed venue"): return c
    if c and (v in c or c in v): return v if c in v else c
    return f"{v}, {c}" if c else v
for e in events:
    if "sound" not in e["svc"]: e["svc"].append("sound")     # owner: every event has sound
    e["svc"] = sorted(set(e["svc"]))
    e["rank"] = (100 if e.get("hero") else 0) + (int(e["month"][:4]) * 12 + int(e["month"][5:7]) - 24000 if e.get("month") else 0)
    e["vcover"] = next((c for c in e["clips"] if c["t"] != "p"), None)
    e["cover"] = next((c for c in e["clips"] if c["t"] != "p" and c.get("star")), None) or e["vcover"] or e["clips"][0]
FULLJ = json.load(open(os.path.join(root, "full.json"))) if os.path.exists(os.path.join(root, "full.json")) else {}
for e in events:
    e.pop("fullClip", None); e.pop("fullDur", None)
    if e["slug"] in FULLJ: e["fullClip"] = "full-" + FULLJ[e["slug"]]["k"]; e["fullDur"] = FULLJ[e["slug"]]["dur"]
events.sort(key=lambda e: -e["rank"])

def loc(e, lang):
    if lang == "en": return dict(title=e["title"], dek=e["dek"], desc=e["desc"], body=e["body"], place=place_en(e), label=(f"{MON_EN[int(e['month'][5:7]) - 1]} {e['month'][:4]}" if e.get("month") else ""))
    t, d, ds, b = AR[e["slug"]]; v = UI_AR["venue"].get(e.get("venue") or "", e.get("venue") or ""); c = UI_AR["city"].get(e.get("city") or "", e.get("city") or "")
    pl = c if (e.get("venue") or "") in ("", "Undisclosed venue") else (v if (c and (e["city"] in e["venue"] or e["venue"] in e["city"])) else (f"{v}، {c}" if c else v))
    return dict(title=t, dek=d, desc=ds, body=b, place=pl, label=(f"{UI_AR['mon'][int(e['month'][5:7]) - 1]} {e['month'][:4]}" if e.get("month") else ""))
def url(c, kind):
    stem = c["k"] if c["t"] == "s" else c.get("f")
    if c["t"] == "p": return MEDIA + f"i/{stem}.jpg"
    return MEDIA + f"v/{stem}." + ("mp4" if kind == "src" else "jpg")
def poster(c): return url(c, "poster")
def alt(e, c, n, lang, L):
    s = (c["svc"] or e["svc"])[0]
    if s == "sound": s = next((x for x in c["svc"] if x != "sound"), s)
    ph = PH[lang].get(s, "")
    if lang == "en": return f"{L['title']}: {ph}" + (f" at {L['place']}" if L["place"] else "") + f" by EchoLight ({'photo' if c['t'] == 'p' else 'video'} {n})"
    return f"{L['title']}: {ph}" + (f" ({L['place']})" if L["place"] else "") + f" من إيكو لايت ({'صورة' if c['t'] == 'p' else 'فيديو'} {n})"
def iso(d): d = int(round(d or 5)); return f"PT{d // 60}M{d % 60}S" if d >= 60 else f"PT{d}S"

# ---- css (scoped) ---------------------------------------------------------------------------
def scope(css, p="#elsc"):
    out = []; i = 0; n = len(css)
    while i < n:
        j = css.find("{", i)
        if j < 0: break
        sel = css[i:j].strip(); d = 1; k = j + 1
        while d and k < n:
            d += (css[k] == "{") - (css[k] == "}"); k += 1
        body = css[j + 1:k - 1]; i = k
        if sel.startswith("@media") or sel.startswith("@supports"): out.append(f"{sel}{{{scope(body, p)}}}"); continue
        if sel.startswith("@"): out.append(f"{sel}{{{body}}}"); continue
        parts = []
        for s in [x.strip() for x in sel.split(",")]:
            if s in ("html",): continue
            if s in (":root", "body"): parts.append(p); continue
            if s.startswith("body"): s = s[4:]; parts.append(p + s); continue
            if s == "*": parts.append(f"{p} *"); continue
            parts.append(f"{p} {s}")
        if parts: out.append(f"{','.join(parts)}{{{body}}}")
    return "\n".join(out)
css = open(f"{root}/site/assets/css/site.css").read()
css = css.replace("#hero-canvas", "#el-hero-canvas").replace("#q{", "#el-q{").replace("#q::", "#el-q::")
css = re.sub(r"@import[^;]+;", "", css)
CSS = scope(css) + """
#elsc{position:relative;left:50%;width:100vw;margin-left:-50vw;max-width:100vw;overflow-x:clip;background:var(--bg);color:var(--ink);font:16px/1.55 var(--font);text-align:start;-webkit-font-smoothing:antialiased}
#elsc *{box-sizing:border-box}
#elsc h1,#elsc h2,#elsc h3,#elsc p,#elsc ul,#elsc figure{margin:0;padding:0;font-family:inherit}
#elsc ul{list-style:none}
#elsc a{text-decoration:none}
#elsc .btn{text-decoration:none}
#elsc[dir=rtl]{font-family:"Tajawal","Space Grotesk",system-ui,sans-serif}
#elsc[dir=rtl] .eyebrow,#elsc[dir=rtl] .stats span,#elsc[dir=rtl] .ct{letter-spacing:0}
#elsc[dir=rtl] .finder-box{padding:8px 20px 8px 8px}
#elsc[dir=rtl] .cov::after{background:linear-gradient(180deg,rgba(5,6,10,0) 35%,rgba(5,6,10,.92))}
#elsc .lb{z-index:2147483000}
#elsc .el-index{padding:30px 0 10px}#elsc .el-index h2{font-size:1.3rem;margin-bottom:14px}
#elsc .el-index ul{columns:2 320px;column-gap:28px}#elsc .el-index li{break-inside:avoid;margin-bottom:12px;font-size:.92rem;color:var(--mute)}#elsc .el-index h3{font-size:1rem;color:var(--ink);display:inline}
#elsc .elev{padding-bottom:20px}#elsc .crumbs a{color:var(--accent)}
#elsc .rel ul{display:grid;gap:8px}#elsc .rel a{color:var(--ink);border-bottom:1px solid var(--line)}
#elsc .sel-i{border:0;padding:0}
#elsc .cg{padding-top:2px}
#elsc a,#elsc button,#elsc input,#elsc textarea,#elsc select{font-family:inherit;letter-spacing:inherit;text-transform:none}
#elsc header,#elsc nav,#elsc section,#elsc article,#elsc aside,#elsc figure,#elsc figcaption{display:block;position:static;float:none;width:auto;height:auto;min-height:0;max-width:none;margin:0;padding:0;background:none;border:0;box-shadow:none;transform:none;color:inherit;font:inherit}
#elsc button{background:none;border:0;padding:0;margin:0;box-shadow:none;border-radius:0;line-height:inherit;color:inherit}
#elsc [hidden]{display:none!important}
#elsc .ehead h2{font-size:clamp(2rem,5vw,3.4rem);margin:8px 0 12px;max-width:20ch;line-height:1.08;letter-spacing:-.02em;font-weight:700}
#elsc .client h2{font-size:clamp(1.9rem,4.5vw,3.2rem);margin:6px 0 10px;line-height:1.1}
#elsc .cur h2{font-size:1.8rem;margin-bottom:8px}
#elsc .fxwrap{display:grid;gap:10px;min-width:0}
#elsc .svc:nth-child(even) .fxwrap{order:-1}
#elsc .labctl{display:flex;flex-wrap:wrap;gap:12px 18px;align-items:end;padding:12px 14px;border:1px solid var(--line);border-radius:14px;background:rgba(8,10,16,.7)}
#elsc .ctl{display:grid;gap:6px;font-size:.7rem;color:var(--mute);text-transform:uppercase;letter-spacing:.1em}
#elsc[dir=rtl] .ctl{letter-spacing:0;font-size:.82rem}
#elsc .sw{display:flex;gap:6px}#elsc .swatch{width:24px;height:24px;border-radius:50%;border:2px solid transparent}#elsc .swatch.on{border-color:#fff}
#elsc .swatch.auto{background:conic-gradient(#2bc4e0,#ff7aa8,#ffd27a,#2ee59d,#2bc4e0)}
#elsc .seg{display:flex;border:1px solid var(--line);border-radius:999px;overflow:hidden}
#elsc .seg-b{padding:6px 11px;font-size:.8rem;color:var(--mute);text-transform:none;letter-spacing:0}#elsc .seg-b.on{background:var(--ink);color:#031018}
#elsc .ctl input[type=text]{background:#141821;color:var(--ink);border:1px solid var(--line);border-radius:8px;padding:6px 9px;width:150px;font:inherit}
#elsc .ctl input[type=range]{accent-color:var(--accent);width:130px}
#elsc .ctl em{font-style:normal;color:var(--ink);text-transform:none;letter-spacing:0}
"""

# ---- html pieces ------------------------------------------------------------------------------
def tile(e, c, n, lang, L, first):
    src = url(c, "src"); ratio = max(0.58, min(1.7, c["w"] / c["h"])); a = alt(e, c, n, lang, L); vb = f'<span class="vbadge">▶ {int(round(c.get("d") or 5))}s</span>' if c["t"] != "p" else ""
    return (f'<a class="tile{" is-v" if c["t"] != "p" else ""}" href="{src}" data-k="{c["k"]}" data-t="{c["t"]}" data-src="{src}" data-poster="{poster(c)}" style="aspect-ratio:{ratio:.3f}" aria-label="{esc(a)}">'
            f'<img src="{poster(c)}" alt="{esc(a)}" width="{c["w"]}" height="{c["h"]}" {"loading=\"lazy\" " if not first else ""}decoding="async">{vb}<span class="cap">{esc(L["title"])}</span></a>')
def article(e, lang, L, ui, mode, h):
    tiles = []; np_ = nv = 0
    for i, c in enumerate(e["clips"]):
        if c["t"] == "p": np_ += 1; n = np_
        else: nv += 1; n = nv
        tiles.append(tile(e, c, n, lang, L, i < 4))
    hub = HUB[lang] if mode == "event" else ""
    chips = "".join(f'<li><a href="{hub}#s={s}">{SVN[lang][s]}</a></li>' for s in e["svc"]) + "".join(f'<li><a href="{hub}#t={t}">{TN[lang][t]}</a></li>' for t in e["types"])
    meta = "".join(f"<li>{esc(x)}</li>" for x in [L["place"], L["label"]] if x)
    wamsg = (f'Hello EchoLight, I saw "{L["title"]}" on your showcase and I would like something like it for my event. Date / venue / guests: ' if lang == "en" else f'مرحباً إيكو لايت، شاهدت "{L["title"]}" في معرض أعمالكم وأريد شيئاً مثله لفعاليتي. التاريخ / الموقع / الضيوف: ')
    full = ""
    if e.get("fullClip"): full = f'<a class="btn btn-ghost small" data-full data-poster="{MEDIA}v/{e["fullClip"]}.jpg" href="{MEDIA}v/{e["fullClip"]}.mp4">{ui["full"]} ({e["fullDur"] // 60}:{e["fullDur"] % 60:02d})</a>'
    related = sorted((x for x in events if x is not e), key=lambda x: -(len(set(x["types"]) & set(e["types"])) * 3 + len(set(x["svc"]) & set(e["svc"]) - {"sound"}) + (2 if x.get("hero") else 0) - (5 if x.get("old") else 0)))[:3]
    rel = "".join(f'<li><a href="{hub}#e={x["slug"]}">{esc(loc(x, lang)["title"])}</a></li>' for x in related)
    back = f'<a data-back href="{HUB[lang] if mode == "event" else "#"}">{ui["back"]}</a>'
    return (f'<article class="elev wrap" id="el-ev-{e["slug"]}" data-title="{esc(L["title"])}"{"" if mode == "event" else " hidden"}><nav class="crumbs" aria-label="Breadcrumb">{back}</nav>'
            f'<header class="ehead"><p class="eyebrow">{esc(" · ".join(TN[lang][t] for t in e["types"]))}</p><{h}>{esc(L["title"])}</{h}><p class="dek">{esc(L["dek"])}</p><ul class="meta">{meta}</ul><ul class="chiprow">{chips}</ul></header>'
            f'<section class="story"><p>{esc(L["body"])}</p><div class="acts"><a class="btn btn-wa" target="_blank" rel="noopener" data-wa="{esc(wamsg)}" href="#">{ui["plan"]}</a>{full}<button class="btn btn-ghost small" type="button" data-copy>{ui["copy"]}</button></div></section>'
            f'<section class="gal" aria-label="{esc(L["title"])}">{"".join(tiles)}</section><section class="rel"><h3>{ui["more"]}</h3><ul>{rel}</ul></section></article>')
def card(e, lang, L, ui):
    cov = e["cover"]; v = e["vcover"]; nv = sum(1 for c in e["clips"] if c["t"] != "p")
    badge = (f'<span class="badge">▶ {ui["film"]} {e["fullDur"] // 60}:{e["fullDur"] % 60:02d}</span>' if e.get("fullClip") else (f'<span class="badge">▶ {nv} {ui["videos"] if nv != 1 else ui["video"]}</span>' if nv else ""))
    sub = " · ".join(x for x in [L["place"], L["label"]] if x); a = alt(e, cov, 1, lang, L)
    return (f'<article class="ecard" data-slug="{e["slug"]}" data-types="{" ".join(e["types"])}" data-svc="{" ".join(e["svc"])}"{" data-hero" if e.get("hero") else ""}{" data-old" if e.get("old") else ""} data-clips="{len(e["clips"])}" data-rank="{e["rank"]}">'
            f'<a href="#e={e["slug"]}" aria-label="{esc(L["title"])}"><div class="cov"><img src="{poster(cov)}" alt="{esc(a)}" width="{cov["w"]}" height="{cov["h"]}" loading="lazy" decoding="async">{badge}'
            f'<div class="eb"><span class="ty">{esc(TN[lang][e["types"][0]])}</span><h3>{esc(L["title"])}</h3><p>{esc(trim(L["dek"], 90))}</p><span class="mt">{esc(sub)}</span></div></div></a></article>')

def jsonld(lang, mode, ev=None):
    base = HUB[lang]; org = {"@type": "Organization", "name": "EchoLight", "url": "https://www.echolight.ae", "telephone": "+971567220533"}
    g = []
    def vids(e, L):
        out = []
        for n, c in enumerate([c for c in e["clips"] if c["t"] != "p"]):
            out.append({"@type": "VideoObject", "name": f"{L['title']} ({n + 1})", "description": L["desc"], "thumbnailUrl": poster(c), "contentUrl": url(c, "src"), "uploadDate": (e.get("month") or "2026-01") + "-01", "duration": iso(c.get("d")), "publisher": org})
        if e.get("fullClip"): out.append({"@type": "VideoObject", "name": L["title"] + " (full)", "description": L["desc"], "thumbnailUrl": f"{MEDIA}v/{e['fullClip']}.jpg", "contentUrl": f"{MEDIA}v/{e['fullClip']}.mp4", "uploadDate": (e.get("month") or "2026-01") + "-01", "duration": iso(e["fullDur"]), "publisher": org})
        return out
    if mode == "hub":
        g.append({"@type": "ProfessionalService", "name": "EchoLight", "alternateName": "إيكو لايت", "url": "https://www.echolight.ae", "telephone": "+971567220533", "areaServed": "AE", "address": {"@type": "PostalAddress", "addressLocality": "Abu Dhabi", "addressCountry": "AE"}, "description": "Event production specialised in AV: stage lighting, LED screens, sound, 3D projection mapping, laser and light shows across the UAE.", "aggregateRating": {"@type": "AggregateRating", "ratingValue": "5.0", "bestRating": "5"},
                  "hasOfferCatalog": {"@type": "OfferCatalog", "name": "Event AV services", "itemListElement": [{"@type": "Offer", "itemOffered": {"@type": "Service", "name": v[0], "description": v[1]}} for v in SVC[lang].values()]}})
        g.append({"@type": "ItemList", "name": UI[lang]["evh"], "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": f"{base}#e={e['slug']}", "name": loc(e, lang)["title"]} for i, e in enumerate(events)]})
        for e in events: g += vids(e, loc(e, lang))
    else:
        e = ev; L = loc(e, lang)
        g.append({"@type": "CollectionPage", "name": L["title"], "description": L["desc"], "inLanguage": lang, "about": [SVN[lang][s] for s in e["svc"]], "primaryImageOfPage": {"@type": "ImageObject", "contentUrl": poster(e["cover"]), "caption": alt(e, e["cover"], 1, lang, L)}, "provider": org})
        g.append({"@type": "BreadcrumbList", "itemListElement": [{"@type": "ListItem", "position": 1, "name": "EchoLight", "item": base}, {"@type": "ListItem", "position": 2, "name": L["title"]}]})
        for n, c in enumerate([c for c in e["clips"] if c["t"] == "p"][:12]): g.append({"@type": "ImageObject", "contentUrl": url(c, "src"), "name": alt(e, c, n + 1, lang, L), "creator": org})
        g += vids(e, L)
    return '<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@graph": g}, ensure_ascii=False) + "</script>"

JS = "\n".join(open(f"{SRC}/{f}").read() for f in ("beams.js", "fx.js", "showcase.js"))
FONTS = '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=Tajawal:wght@400;500;700;800&display=swap" rel="stylesheet">'

def page(lang, mode, ev=None):
    ui = UI[lang]; d = "rtl" if lang == "ar" else "ltr"; wrap = f'<div id="elsc" lang="{lang}" dir="{d}" data-lang="{lang}" data-mode="{mode}" data-hub-url="{HUB[lang]}">'
    arts = "".join(article(e, lang, loc(e, lang), ui, mode, "h1" if mode == "event" else "h2") for e in (events if mode == "hub" else [ev]))
    if mode == "event": return f"{FONTS}<style>{CSS}</style>{wrap}<div class=\"el-evs\">{arts}</div></div>{jsonld(lang, mode, ev)}<script>{JS}</script>"
    chips = "".join(f'<button class="chip" type="button" data-pick="{k}"><i style="background:{c}"></i>{TN[lang][k]}</button>' for k, c in CHIPS)
    cards = "".join(card(e, lang, loc(e, lang), ui) for e in events)
    counts = {s: sum(1 for e in events if s in e["svc"]) for s in SVN[lang]}
    sv = "".join(f'<article class="svc"><div><p class="eyebrow">0{i + 1} / 05</p><h3>{v[0]}</h3><p>{v[1]}</p><ul>{"".join(f"<li>{x}</li>" for x in v[2])}</ul><a class="go" href="#" data-svc="{k}">{ui["see"].format(n=counts[k], w=ui["events"], s=v[0])}</a></div><div class="fxwrap"><div class="fx"><canvas data-fx="{k}" role="img" aria-label="{esc(v[0])}"></canvas></div><div class="labctl"></div></div></article>' for i, (k, v) in enumerate(SVC[lang].items()))
    idx = "".join(f'<li><h3>{esc(loc(e, lang)["title"])}</h3>. {esc(loc(e, lang)["desc"])}</li>' for e in events)
    stats = "".join(f"<div><b>{a}</b><span>{b}</span></div>" for a, b in ui["stats"])
    hub = (f'<div class="el-hub"><section class="hero" aria-labelledby="el-h1"><canvas id="el-hero-canvas" aria-hidden="true"></canvas><div class="hero-fade" aria-hidden="true"></div><div class="hero-inner"><p class="eyebrow">{ui["eyebrow"]}</p><h1 id="el-h1">{ui["h1a"]} <em>{ui["h1b"]}</em></h1><p class="lead">{ui["lead"]}</p>'
           f'<form id="el-finder" role="search" autocomplete="off"><label for="el-q" class="sr">{ui["qlabel"]}</label><div class="finder-box"><input id="el-q" name="q" type="text" inputmode="search" enterkeyhint="search" maxlength="120"><button class="btn btn-go" type="submit">{ui["go"]}</button></div></form><div class="chips" role="group" aria-label="{ui["reel"]}">{chips}</div><div class="stats">{stats}</div></div></section>'
           f'<section class="work" id="el-work"><div class="wrap"><p class="eyebrow">{ui["ev"]}</p><h2>{ui["evh"]}</h2><p class="sub" id="el-gsub"></p><div class="reco" id="el-reco" hidden aria-live="polite"></div><div class="filters"><div class="f-row" id="el-ftypes" role="group"></div><div class="f-row" id="el-fsvc" role="group"></div></div><p class="count" id="el-count" aria-live="polite"></p>'
           f'<div class="cards el-cards">{cards}</div><p class="empty" id="el-empty" hidden>{ui["empty"]}</p></div></section>'
           f'<section class="services"><div class="wrap"><p class="eyebrow">{ui["svce"]}</p><h2>{ui["svch"]}</h2><p class="sub">{ui["svcsub"]}</p>{sv}</div></section>'
           f'<section class="el-index"><div class="wrap"><h2>{ui["idx"]}</h2><ul>{idx}</ul></div></section>'
           f'<section class="contact"><div class="wrap"><h2>{ui["ctah"]}</h2><p class="sub">{ui["ctas"]}</p><div class="c-actions"><a class="btn btn-wa big" target="_blank" rel="noopener" data-wa="{"Hello EchoLight, I would like to plan an event. Date / venue / guests: " if lang == "en" else "مرحباً إيكو لايت، أودّ التخطيط لفعالية. التاريخ / الموقع / الضيوف: "}" href="#">{ui["wa"]}</a><a class="btn btn-ghost big" href="tel:+971567220533">+971 56 722 0533</a></div><p class="fine"><a href="https://www.echolight.ae">echolight.ae</a> · <a href="https://instagram.com/echolightae">@echolightae</a> · {ui["area"]}</p></div></section></div>')
    client = f'<div class="el-client wrap client" hidden><nav class="crumbs"><a data-back href="#">{ui["back"]}</a></nav><p class="eyebrow">{ui["eyebrow"]}</p><h2 class="cl-h"></h2><p class="note cl-n"></p><div class="gal cl-g"></div><a class="btn btn-wa big cl-wa" target="_blank" rel="noopener" href="#">{ui["wa"]}</a></div>'
    cur = (f'<div class="el-cur wrap" hidden><div class="cur"><div class="col"><nav class="crumbs"><a data-back href="#">{ui["back"]}</a></nav><h2>{ui["cur_h"]}</h2><p class="sub">{ui["cur_s"]}</p><div id="cu-list" class="col"></div></div>'
           f'<aside class="panel"><strong id="cu-cnt"></strong><div class="sel" id="cu-sel"></div><input id="cu-client" placeholder="{esc(ui["cur_c"])}" aria-label="{esc(ui["cur_c"])}"><textarea id="cu-note" rows="3" placeholder="{esc(ui["cur_n"])}" aria-label="{esc(ui["cur_n"])}"></textarea><input id="cu-out" readonly placeholder="{esc(ui["cur_o"])}"><div style="display:flex;gap:8px;flex-wrap:wrap"><button class="btn btn-go small" id="cu-copy" type="button">{"Copy link" if lang == "en" else "انسخ الرابط"}</button><a class="btn btn-ghost small" id="cu-open" target="_blank" rel="noopener">{ui["cur_p"]}</a><button class="btn btn-ghost small" id="cu-clear" type="button">{ui["cur_x"]}</button></div></aside></div></div>')
    return f'{FONTS}<style>{CSS}</style>{wrap}{hub}<div class="el-evs" hidden>{arts}</div>{client}{cur}</div>{jsonld(lang, "hub")}<script>{JS}</script>'

# ---- write ------------------------------------------------------------------------------------
out = f"{root}/embed"; os.makedirs(out, exist_ok=True)
for lang in ("en", "ar"):
    os.makedirs(f"{out}/events-{lang}", exist_ok=True)
    open(f"{out}/showcase-{lang}.html", "w").write(page(lang, "hub"))
    for e in events: open(f"{out}/events-{lang}/{e['slug']}.html", "w").write(page(lang, "event", e))
    with open(f"{root}/SEO-PACK-{lang.upper()}.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f); w.writerow(["page", "squarespace_url", "seo_title", "seo_description", "event_types", "services", "place"])
        w.writerow(["Showcase hub", "/showcase" if lang == "en" else "/ar-/showcase", UI_AR["title"] if lang == "ar" else "Event Lighting, LED, Sound & Laser Shows UAE | EchoLight", UI_AR["desc"] if lang == "ar" else "Describe your event and see real EchoLight work: stage lighting, LED screens, sound, 3D mapping and laser shows across Abu Dhabi, Dubai and the UAE.", "", "all", "UAE"])
        for e in events:
            L = loc(e, lang); t = (f"{L['title']} | EchoLight" if lang == "en" else f"{L['title']} | إيكو لايت")
            w.writerow(["Event", ("/showcase/" if lang == "en" else "/ar-/showcase/") + e["slug"], trim(t, 60), trim(L["desc"], 155), "; ".join(TN[lang][x] for x in e["types"]), "; ".join(SVN[lang][x] for x in e["svc"]), L["place"]])
with open(f"{root}/SEO-ALT-TEXT.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f); w.writerow(["event", "file", "type", "alt_en", "alt_ar"])
    for e in events:
        LE, LA = loc(e, "en"), loc(e, "ar"); npn = nvn = 0
        for c in e["clips"]:
            if c["t"] == "p": npn += 1; n = npn
            else: nvn += 1; n = nvn
            w.writerow([LE["title"], url(c, "src").replace(MEDIA, ""), "photo" if c["t"] == "p" else "video", alt(e, c, n, "en", LE), alt(e, c, n, "ar", LA)])
sizes = {f: os.path.getsize(f"{out}/{f}") // 1024 for f in ("showcase-en.html", "showcase-ar.html")}
print("hub blocks (KB):", sizes, "| event blocks:", len(events) * 2)
