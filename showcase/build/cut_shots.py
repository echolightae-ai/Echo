"""Cut promo shots and full-length shows from the originals with the same premium grade.

Usage: python3 -I cut_shots.py <scratch_dir> <site_dir>
"""
import sys, os, json, subprocess
from concurrent.futures import ThreadPoolExecutor
scratch, site = sys.argv[1:3]
out = f"{site}/assets/v"; os.makedirs(out, exist_ok=True)
idx = json.load(open(f"{scratch}/index.json")); new = sorted(os.listdir(f"{scratch}/media_new"))
def src(k): return f"{scratch}/media/{idx[k]}" if k in idx else f"{scratch}/media_new/{new[int(k[1:])]}"
shots = {s["id"]: s for v in json.load(open(f"{scratch}/label/shots.json")).values() for s in v["shots"]}
events = json.load(open(f"{site}/data/events.json"))
GRADE = "eq=contrast=1.06:saturation=1.12:gamma=0.98,unsharp=5:5:0.4,vignette=PI/7"
def enc(p, a, ln, name, size, crf=23, full=False):
    dst = f"{out}/{name}.mp4"
    if os.path.exists(dst): return name
    fo = max(0.0, ln - 0.4)
    vf = f"scale={size}:flags=lanczos,{GRADE},fps=30,fade=t=in:st=0:d=0.3,fade=t=out:st={fo:.2f}:d=0.4,format=yuv420p"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{a:.2f}", "-t", f"{ln:.2f}", "-i", p, "-an", "-vf", vf, "-c:v", "libx264", "-crf", str(crf), "-preset", "slow", "-profile:v", "high", "-movflags", "+faststart", dst])
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{min(1.5, ln / 2):.2f}", "-i", dst, "-frames:v", "1", "-q:v", "3", f"{out}/{name}.jpg"])
    return name
jobs = []
for e in events:
    for c in e["clips"]:
        if c["t"] != "s": continue
        s = shots[c["k"]]; ln = min(5.0, s["b"] - s["a"]); a = s["a"] + max(0.0, (s["b"] - s["a"] - ln) / 2)
        par = c["par"]; portrait = par not in ("V6", "V39", "N1")
        probe = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height:stream_side_data=rotation", "-of", "json", src(par)], capture_output=True, text=True).stdout)["streams"][0]
        w, h = probe["width"], probe["height"]
        rot = abs(int((probe.get("side_data_list") or [{}])[0].get("rotation", 0)))
        if rot in (90, 270): w, h = h, w
        size = "720:-2" if h >= w else "1280:-2"
        if min(w, h) < 540: size = f"{w}:-2"
        c["w"], c["h"] = (720, int(720 * h / w)) if h >= w else (1280, int(1280 * h / w))
        if min(w, h) < 540: c["w"], c["h"] = w, h
        c["d"] = round(ln, 1)
        jobs.append((src(par), a, ln, c["k"], size, 23))
    if e.get("full"):
        k = e["full"]; p = src(k); dur = float(json.loads(subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", p], capture_output=True, text=True).stdout)["format"]["duration"])
        ln = min(dur - 0.2, 170.0)
        jobs.append((p, 0.0, ln, "full-" + k, "1280:-2" if k == "V6" else "720:-2", 25))
        e["fullClip"] = "full-" + k; e["fullDur"] = round(ln)
with ThreadPoolExecutor(2) as ex:
    for n in ex.map(lambda j: enc(*j), jobs): print(n, flush=True)
json.dump(events, open(f"{site}/data/events.json", "w"), separators=(",", ":"))
print("DONE", len(jobs))
