"""Premium re-cut of showcase clips: best-window pick, stabilise, grade, fades.

Usage: python3 -I recut_videos.py <scratch_dir> <items.json> <out_dir>
Picks the steadiest, best-exposed ~6 s window (skipping the first/last second of
handheld footage), stabilises it with vidstab, grades it and adds soft fades.
"""
import sys, os, json, subprocess, statistics, tempfile
from concurrent.futures import ThreadPoolExecutor
scratch, items_path, out = sys.argv[1:4]
os.makedirs(out, exist_ok=True)
idx = json.load(open(f"{scratch}/index.json")); new = sorted(os.listdir(f"{scratch}/media_new"))
def src(k): return f"{scratch}/media/{idx[k]}" if k in idx else f"{scratch}/media_new/{new[int(k[1:])]}"
vids = [it for it in json.load(open(items_path)) if it["t"] == "v"]
LEN = 6.0

def stats(p):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-vf", "fps=10,scale=160:-2,signalstats,metadata=print:file=-", "-an", "-f", "null", "-"], capture_output=True, text=True)
    t, rows = None, []
    for ln in r.stdout.splitlines():
        if ln.startswith("frame:"): t = float(ln.split("pts_time:")[1])
        elif "YAVG=" in ln: y = float(ln.split("=")[1]); rows.append([t, y, 0.0])
        elif "YDIF=" in ln and rows: rows[-1][2] = float(ln.split("=")[1])
    return rows

def best_start(rows, dur):
    if dur <= LEN + 1.2: return max(0.0, min(0.4, dur - LEN)) if dur > LEN else 0.0, min(dur, LEN)
    lo, hi = 1.0, dur - 1.0 - LEN
    if hi <= lo: return max(0.0, (dur - LEN) / 2), LEN
    best, bs = -1e9, lo
    s = lo
    while s <= hi:
        w = [r for r in rows if s <= r[0] < s + LEN]
        if len(w) > 5:
            y = statistics.mean(r[1] for r in w); d = [r[2] for r in w]
            score = min(y, 110) / 110 - statistics.pstdev(d) / 12 - max(0, statistics.mean(d) - 9) / 15
            if score > best: best, bs = score, s
        s += 0.5
    return bs, LEN

def recut(it):
    p = src(it["id"]); dst = f"{out}/{it['f']}.mp4"
    if os.path.exists(dst): return it["id"], "cached"
    dur = float(json.loads(subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", p], capture_output=True, text=True).stdout)["format"]["duration"])
    st, ln = best_start(stats(p), dur)
    portrait = it["h"] >= it["w"]
    size = "720:-2" if portrait else "1280:-2"
    if min(it["w"], it["h"]) < 540: size = f"{it['w']}:-2"
    with tempfile.TemporaryDirectory() as td:
        trf = f"{td}/t.trf"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{st:.2f}", "-t", f"{ln:.2f}", "-i", p, "-vf", f"vidstabdetect=shakiness=6:accuracy=12:result={trf}", "-f", "null", "-"])
        fo = max(0.0, ln - 0.35)
        vf = (f"vidstabtransform=input={trf}:smoothing=18:zoom=4:optzoom=0,scale={size}:flags=lanczos,"
              f"eq=contrast=1.07:saturation=1.14:gamma=0.97,unsharp=5:5:0.45,"
              f"vignette=PI/6,fps=30,fade=t=in:st=0:d=0.3,fade=t=out:st={fo:.2f}:d=0.35,format=yuv420p")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{st:.2f}", "-t", f"{ln:.2f}", "-i", p, "-an", "-vf", vf,
                        "-c:v", "libx264", "-crf", "22", "-preset", "slow", "-profile:v", "high", "-movflags", "+faststart", dst])
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{min(1.5, ln / 2):.2f}", "-i", dst, "-frames:v", "1", "-q:v", "3", f"{out}/{it['f']}.jpg"])
    return it["id"], f"start={st:.1f}s len={ln:.1f}s"

with ThreadPoolExecutor(4) as ex:
    for k, msg in ex.map(recut, vids): print(k, msg, flush=True)
print("DONE")
