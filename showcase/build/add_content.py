"""Add new photos/videos (and optionally a new event) to the showcase. Works from any chat or terminal.

  python3 -I add_content.py --src /path/to/new/files --event dibo-showroom-opening-dubai [--svc laser,lighting] [--star]
  python3 -I add_content.py --src /path --manifest manifest.csv        # columns: file,event,svc,star   (svc like "lighting,laser")
  python3 -I add_content.py --src /path --event my-new-event --new-event --title "..." --dek "..." --desc "..." --body "..." \\
        --types wedding,gala --city "Abu Dhabi" --venue "..." --month 2026-10 --event-svc lighting,laser \\
        --ar-title "..." --ar-dek "..." --ar-desc "..." --ar-body "..."
  add --film to a long promo: it is encoded as the event's full-length film (shown with a play button on the event page).

It encodes web copies into showcase/media/, records the clips in showcase/content/events.json, skips exact duplicates
(by file hash), and prints what to do next. Then run release.py to publish.
"""
import argparse, csv, hashlib, json, os, subprocess, sys
from PIL import Image, ImageOps
Image.MAX_IMAGE_PIXELS = None
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
EV = f"{ROOT}/content/events.json"; HASH = f"{ROOT}/content/hashes.json"
ap = argparse.ArgumentParser()
ap.add_argument("--src", required=True); ap.add_argument("--event"); ap.add_argument("--manifest"); ap.add_argument("--svc", default=""); ap.add_argument("--star", action="store_true"); ap.add_argument("--film", action="store_true")
ap.add_argument("--new-event", action="store_true"); ap.add_argument("--title"); ap.add_argument("--dek"); ap.add_argument("--desc"); ap.add_argument("--body"); ap.add_argument("--types", default="show")
ap.add_argument("--city", default="UAE"); ap.add_argument("--venue", default=""); ap.add_argument("--month", default=""); ap.add_argument("--event-svc", default="lighting"); ap.add_argument("--hero", action="store_true")
for k in ("title", "dek", "desc", "body"): ap.add_argument(f"--ar-{k}")
a = ap.parse_args()
ev = json.load(open(EV)); by = {e["slug"]: e for e in ev}; hashes = json.load(open(HASH)) if os.path.exists(HASH) else {}
def md5(p): h = hashlib.md5()
def md5f(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()
def nxt(prefix): return max([int(c["k"][1:]) for e in ev for c in e["clips"] if c["k"][0] == prefix and c["k"][1:].isdigit()] + [0]) + 1
if a.new_event:
    assert a.event and a.title and a.dek and a.desc and a.body and a.ar_title and a.ar_dek and a.ar_desc and a.ar_body, "a new event needs --event --title --dek --desc --body and the four --ar-* texts (Arabic page)"
    es = a.event_svc.split(","); e = dict(slug=a.event, title=a.title, dek=a.dek, desc=a.desc, body=a.body, types=a.types.split(","), city=a.city, venue=a.venue, month=a.month, svc=es, hero=a.hero, clips=[],
                                         ar=dict(title=a.ar_title, dek=a.ar_dek, desc=a.ar_desc, body=a.ar_body))
    ev.append(e); by[a.event] = e
rows = []
if a.manifest: rows = list(csv.DictReader(open(a.manifest)))
else:
    assert a.event, "give --event (or --manifest)"
    rows = [dict(file=f, event=a.event, svc=a.svc, star="1" if a.star else "") for f in sorted(os.listdir(a.src)) if not f.startswith(".")]
EXT_I = (".jpg", ".jpeg", ".png", ".heic"); EXT_V = (".mp4", ".mov", ".m4v")
out_i = f"{ROOT}/media/i"; out_v = f"{ROOT}/media/v"; os.makedirs(out_i, exist_ok=True); os.makedirs(out_v, exist_ok=True); added = skipped = 0
for r in rows:
    p = os.path.join(a.src, r["file"]); lo = r["file"].lower()
    if not os.path.isfile(p) or not lo.endswith(EXT_I + EXT_V): print("skip (not media):", r["file"]); continue
    h = md5f(p)
    if h in hashes: print("skip duplicate of", hashes[h], ":", r["file"]); skipped += 1; continue
    e = by[r["event"]]; svc = [s for s in (r.get("svc") or a.svc).split(",") if s] or e["svc"][:1]
    if lo.endswith(EXT_I):
        cid = f"I{nxt('I')}"; im = ImageOps.exif_transpose(Image.open(p)).convert("RGB"); im.thumbnail((1200, 1200)); im.save(f"{out_i}/{cid}.jpg", quality=72, optimize=True, progressive=True)
        e["clips"].append(dict(k=cid, t="p", f=cid, w=im.width, h=im.height, svc=svc, star=bool(r.get("star")))); hashes[h] = cid
    else:
        cid = f"V{nxt('V')}"; pr = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height:stream_side_data=rotation:format=duration", "-of", "json", p], capture_output=True, text=True).stdout)
        s = pr["streams"][0]; w, hh = s["width"], s["height"]; rot = abs(int((s.get("side_data_list") or [{}])[0].get("rotation", 0)))
        if rot in (90, 270): w, hh = hh, w
        dur = min(float(pr["format"]["duration"]), 170.0 if a.film else 150.0); tw = min(w, (960 if w >= hh else 576)); tw -= tw % 2
        name = f"full-{cid}" if a.film else cid; dst = f"{out_v}/{name}.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", p, "-t", f"{dur:.2f}", "-an", "-vf", f"scale={tw}:-2:flags=lanczos,eq=contrast=1.04:saturation=1.08,fps=30,format=yuv420p", "-c:v", "libx264", "-crf", "27", "-maxrate", "1800k" if a.film else "3000k", "-bufsize", "4000k", "-preset", "medium", "-profile:v", "high", "-movflags", "+faststart", dst], check=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{min(1.0, dur / 3):.2f}", "-i", dst, "-frames:v", "1", "-q:v", "4", f"{out_v}/{name}.jpg"], check=True)
        assert os.path.getsize(dst) < 19.5e6, f"{name}.mp4 is over the CDN's 20 MB limit; shorten it"
        if a.film: e["fullClip"] = name; e["fullDur"] = round(dur)
        else:
            ph = Image.open(f"{out_v}/{name}.jpg"); e["clips"].append(dict(k=cid, t="v", f=cid, w=ph.width, h=ph.height, d=round(dur, 1), svc=svc, star=bool(r.get("star"))))
        hashes[h] = cid
    added += 1; print("added", cid, "->", r["event"], svc)
os.makedirs(os.path.dirname(HASH), exist_ok=True); json.dump(hashes, open(HASH, "w")); json.dump(ev, open(EV, "w"), separators=(",", ":"))
print(f"\nadded {added}, skipped {skipped} duplicates. Next: python3 -I {HERE}/release.py")
