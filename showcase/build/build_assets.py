"""Build web-ready copies of the curated media for the showcase site.

Usage: python3 -I build_assets.py <scratch_dir> <site_dir>
  scratch_dir holds media/ (original zip), media_new/, index.json.
Originals are never modified. Output names are neutral (p001.jpg / v001.mp4)
so no client or location names leak through filenames.
"""
import sys, os, json, csv, subprocess
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageOps
Image.MAX_IMAGE_PIXELS = None
scratch, site = sys.argv[1], sys.argv[2]
idx = json.load(open(f"{scratch}/index.json"))
src = {k: f"{scratch}/media/{v}" for k, v in idx.items()}
new = sorted(os.listdir(f"{scratch}/media_new"))
newmap = {f"N{i}": f"{scratch}/media_new/{f}" for i, f in enumerate(new)}
src.update(newmap)

SV = {"stage_lighting": "lighting", "gobo_atmosphere": "lighting", "laser_skybeams": "laser",
      "pyro_effects": "laser", "led_screens": "led", "mapping_projection": "mapping", "sound": "sound"}
rows = list(csv.DictReader(open(f"{site}/../curation.csv")))
EVM = {"wedding_social": "wedding", "cultural_national": "cultural", "launch_activation": "launch", "corporate": "corporate"}
meta = {}
for r in rows:
    if r["note"] and not r["note"].startswith("keep"): continue
    s = sorted({SV[x] for x in r["services"].split("|") if x}); e = [EVM[x] for x in r["event_types"].split("|") if x]
    if s or e: meta[r["id"]] = dict(s=s, e=e)
# new material (summit photos show hung line arrays + LED wall; laser/LED stage clip)
meta.update({
 "N1": dict(s=["led", "laser"], e=["corporate"]), "N2": dict(s=["led", "lighting"], e=["corporate"]),
 "N3": dict(s=["led", "lighting"], e=["corporate"]), "N4": dict(s=["sound", "led"], e=["corporate"]),
 "N5": dict(s=["led"], e=["corporate"]), "N6": dict(s=["sound", "led"], e=["corporate"]),
 "N7": dict(s=["led", "sound"], e=["corporate"])})
FEATURED = set("""V23 V80 V67 V70 V71 V73 V54 V37 V38 V58 V9 V77 V63 V76 V84 V26 V42 V93 N1 N7
I13 I17 I10 I2 I94 I95 I97 I99 I41 I43 I32 I11 I87 I90 I57 I81 I86 I104 I77 I79 I62 I68 I114 I101 I116 N2 N6 N4""".split())

def order(k): return (k[0], int(k[1:]))
ids = sorted((k for k in meta if k in src), key=order)

def photo(k, n):
    out = f"p{n:03d}"; im = ImageOps.exif_transpose(Image.open(src[k])).convert("RGB")
    c = "#%02x%02x%02x" % im.resize((1, 1), Image.BILINEAR).getpixel((0, 0))
    im.thumbnail((1280, 1280)); im.save(f"{site}/assets/img/{out}.jpg", quality=72, optimize=True, progressive=True)
    return dict(id=k, t="p", f=out, w=im.width, h=im.height, c=c)

def video(k, n):
    out = f"v{n:03d}"; p = src[k]
    j = json.loads(subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", p], capture_output=True, text=True).stdout)
    vs = [s for s in j["streams"] if s["codec_type"] == "video"][0]
    w, h = vs["width"], vs["height"]
    for sd in vs.get("side_data_list", []) or []:
        if abs(int(sd.get("rotation", 0))) in (90, 270): w, h = h, w
    d = float(j["format"]["duration"]); ln = d if d <= 6 else 5; st = 0 if d <= 8 else d * 0.35
    sc = "scale=540:-2" if h >= w else "scale=960:-2"
    if min(w, h) < 540: sc = f"scale={w}:-2"
    dst = f"{site}/assets/vid/{out}.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{st:.2f}", "-t", f"{ln:.2f}", "-i", p, "-an", "-vf", sc + ",fps=30",
                    "-c:v", "libx264", "-crf", "29", "-preset", "medium", "-pix_fmt", "yuv420p", "-movflags", "+faststart", dst])
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "0.8", "-i", dst, "-frames:v", "1", "-q:v", "5", f"{site}/assets/vid/{out}.jpg"])
    pim = Image.open(f"{site}/assets/vid/{out}.jpg").convert("RGB")
    c = "#%02x%02x%02x" % pim.resize((1, 1), Image.BILINEAR).getpixel((0, 0))
    return dict(id=k, t="v", f=out, w=pim.width, h=pim.height, c=c, d=round(ln, 1))

jobs = []; pn = vn = 0
for k in ids:
    if src[k].lower().endswith((".jpg", ".png")): pn += 1; jobs.append((photo, k, pn))
    else: vn += 1; jobs.append((video, k, vn))
with ThreadPoolExecutor(4) as ex: res = list(ex.map(lambda a: a[0](a[1], a[2]), jobs))
for r in res:
    m = meta[r["id"]]; r["s"] = m["s"]; r["e"] = m["e"]; r["ft"] = 1 if r["id"] in FEATURED else 0
json.dump(res, open(f"{site}/data/items.json", "w"), separators=(",", ":"))
open(f"{site}/data/items.js", "w").write("window.ITEMS=" + json.dumps(res, separators=(",", ":")) + ";")
print(len(res), "items;", pn, "photos;", vn, "videos")
