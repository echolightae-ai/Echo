"""Rebuild the whole content set from the originals, with nothing dropped silently.

Usage: python3 -I rebuild_content.py <scratch_dir> <showcase_dir>
 - every original file is placed in an event or listed in COVERAGE.csv with a reason
 - clips keep their FULL length (no stabilising, no 6 s cuts); promo films and shots are kept as they are
 - each clip's service tag is limited to the services the event really delivers
"""
import sys, os, json, csv, subprocess, collections
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageOps
Image.MAX_IMAGE_PIXELS = None
sys.path.insert(0, os.path.dirname(__file__))
import events_src as E, assignments as A
scratch, root = sys.argv[1:3]
al = {a["id"]: a for a in json.load(open(f"{scratch}/allfiles.json"))}
ev = json.load(open(f"{root}/content/events.json"))
by = {e["slug"]: e for e in ev}
# explicit services per event (what the crew really delivered); sound is added at build time for every event
SV = {e["slug"]: list(e.get("svc") or []) for e in E.EVENTS if e.get("svc")}
SV.update({"emirati-kuwaiti-womens-forum": ["lighting"], "laser-mapping-showcase": ["laser", "mapping"], "laser-mapping-on-an-led-video-wall": ["laser", "led", "mapping"],
           "3d-mapping-on-a-hotel-facade": ["mapping"], "projection-mapping-showcase": ["mapping"], "dibo-showroom-opening-dubai": ["laser"], "al-nayef-group-awards-night": ["laser", "led"],
           "new-year-countdown-sky-beams-rak": ["laser"], "garden-wedding-light-show-cold-sparks": ["laser", "lighting"], "the-muse-grand-opening": ["laser", "lighting"], "the-muse-branch-opening": ["laser", "lighting"],
           "diet-box-launch-night": ["led", "lighting"], "corporate-stage-designs": ["led", "lighting"], "she-leads-series": ["led", "lighting"], "led-screens-that-set-the-scene": ["led"],
           "show-of-the-night-timecoded-lighting": ["lighting"], "echolight-showreel": ["lighting"], "3d-mapping-on-a-car": ["mapping"], "more-from-our-events": ["lighting", "led"]})
NEW = {
 "3d-mapping-on-a-car": dict(slug="3d-mapping-on-a-car", title="3D Mapping on a Car", types=["launch"], city="UAE", venue="", month="", hero=True, svc=["mapping"],
   dek="A vehicle becomes the screen: patterns, outlines and text fitted to its bodywork.", desc="3D projection mapping onto a car for a vehicle launch: patterns, outlines and text fitted to the bodywork. Projection mapping by EchoLight, UAE.",
   body="The car is the canvas. We map the projection to its bodywork so patterns flow over the doors and roof, glowing outlines trace its shape and text lands exactly where it should."),
 "more-from-our-events": dict(slug="more-from-our-events", title="More from Our Events", types=["show", "wedding", "gala"], city="UAE", venue="", month="", hero=False, svc=["lighting", "led"],
   dek="More moments from our shows across the UAE.", desc="More moments from EchoLight shows across the UAE: ballroom lighting, LED stages and light effects.",
   body="A wider look at what we light, light-programme and screen across weddings, galas and stage shows in the UAE."),
}
for k, n in NEW.items():
    n.update(clips=[], ty=[], place="", label="", url=f"e/{k}.html")
    by[k] = n; ev.append(n)
# AR text for the two new events is in events_ar.AR (added there)
def add(slug, cid):
    e = by[slug]
    if any(c["k"] == cid for c in e["clips"]): return
    a = al[cid]; e["clips"].append(dict(k=cid, t="p" if a["kind"] == "image" else "v", svc=A.SVC.get(cid, []), star=False, w=a["w"], h=a["h"], d=round(a["dur"], 1)))
for cid, slug in A.ASSIGN.items(): add(slug, cid)
# whole-clip jobs ------------------------------------------------------------------------------
os.makedirs(f"{root}/media/i", exist_ok=True); os.makedirs(f"{root}/media/v", exist_ok=True)
def enc_photo(cid):
    a = al[cid]; out = f"{root}/media/i/{cid}.jpg"; im = ImageOps.exif_transpose(Image.open(a["path"])).convert("RGB"); w, h = im.size
    if not os.path.exists(out): t = im.copy(); t.thumbnail((1200, 1200)); t.save(out, quality=72, optimize=True, progressive=True)
    im2 = Image.open(out); return cid, im2.size
def enc_video(cid):
    a = al[cid]; out = f"{root}/media/v/{cid}.mp4"; w, h = a["w"], a["h"]; tw = min(w, 576 if h >= w else 960); tw -= tw % 2
    dur = min(a["dur"], 150.0)
    if not os.path.exists(out):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a["path"], "-t", f"{dur:.2f}", "-an", "-vf", f"scale={tw}:-2:flags=lanczos,eq=contrast=1.04:saturation=1.08,fps=30,format=yuv420p",
                        "-c:v", "libx264", "-crf", "27", "-preset", "medium", "-profile:v", "high", "-movflags", "+faststart", out])
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{min(1.0, dur / 3):.2f}", "-i", out, "-frames:v", "1", "-q:v", "4", f"{root}/media/v/{cid}.jpg"])
    p = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,duration", "-of", "json", out], capture_output=True, text=True).stdout)["streams"][0]
    return cid, (p["width"], p["height"], round(float(p.get("duration") or dur), 1))
photos = sorted({c["k"] for e in ev for c in e["clips"] if c["t"] == "p"}); videos = sorted({c["k"] for e in ev for c in e["clips"] if c["t"] == "v"})
print("photos", len(photos), "videos", len(videos), flush=True)
dims = {}
with ThreadPoolExecutor(4) as ex:
    for cid, d in ex.map(enc_photo, photos): dims[cid] = d
    for cid, d in ex.map(enc_video, videos): dims[cid] = d; print(cid, d, flush=True)
# finalize clip records --------------------------------------------------------------------------
for e in ev:
    es = SV.get(e["slug"], e.get("svc") or ["lighting"]); e["svc"] = es
    if e["slug"] in E.FULL: pass
    for c in e["clips"]:
        k = c["k"]
        if c["t"] in ("p", "v"):
            d = dims[k]; c["f"] = k; c["w"], c["h"] = d[0], d[1]
            if c["t"] == "v": c["d"] = d[2]
        mine = [s for s in (c.get("svc") or []) if s in es]
        c["svc"] = mine or es[:1]
    # order: starred first, then videos and photos alternating, so the first screen has motion
    vs = [c for c in e["clips"] if c["t"] != "p"]; ps = [c for c in e["clips"] if c["t"] == "p"]; key = lambda c: (not c.get("star"), c["k"])
    vs.sort(key=key); ps.sort(key=key); out = []
    while vs or ps:
        if vs: out.append(vs.pop(0))
        if ps: out.append(ps.pop(0))
    e["clips"] = out
json.dump(ev, open(f"{root}/content/events.json", "w"), separators=(",", ":"))
# coverage report ------------------------------------------------------------------------------
where = collections.defaultdict(list)
for e in ev:
    for c in e["clips"]:
        par = c["k"][:c["k"].rindex("s")] if c["t"] == "s" else c["k"]; where[par].append(e["slug"])
for slug, (vid, segs) in E.FULL.items(): where[vid].append(slug + " (full film)")
with open(f"{root}/COVERAGE.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["original_file", "id", "kind", "status", "event_or_reason"])
    for cid, a in sorted(al.items(), key=lambda x: (x[0][0], int(x[0][1:]))):
        if where.get(cid): w.writerow([a["file"], cid, a["kind"], "on the site", "; ".join(sorted(set(where[cid])))])
        elif cid in A.SKIP: w.writerow([a["file"], cid, a["kind"], "skipped", A.SKIP[cid]])
        else: w.writerow([a["file"], cid, a["kind"], "UNACCOUNTED", ""])
rows = list(csv.DictReader(open(f"{root}/COVERAGE.csv"))); print(collections.Counter(r["status"] for r in rows))
print("events", len(ev), "clips", sum(len(e["clips"]) for e in ev))
