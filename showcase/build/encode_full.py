"""Encode the full-length films (graded, faded, capped to stay under the CDN's 20 MB file limit).
Usage: python3 -I encode_full.py <scratch_dir> <out_media_dir>   (writes <out>/v/full-<id>.mp4/.jpg and <out>/full.json)"""
import sys, os, json, subprocess
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(__file__)); import events_src as E
scratch, out = sys.argv[1:3]; os.makedirs(f"{out}/v", exist_ok=True)
idx = json.load(open(f"{scratch}/index.json")); new = sorted(os.listdir(f"{scratch}/media_new"))
def src(k): return f"{scratch}/media/{idx[k]}" if k in idx else f"{scratch}/media_new/{new[int(k[1:])]}"
shots = {s["id"]: s for v in json.load(open(f"{scratch}/label/shots.json")).values() for s in v["shots"]}
GRADE = "eq=contrast=1.06:saturation=1.12:gamma=0.98,unsharp=5:5:0.4,vignette=PI/7"
def probe(p):
    j = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height:stream_side_data=rotation:format=duration", "-of", "json", p], capture_output=True, text=True).stdout)
    s = j["streams"][0]; w, h = s["width"], s["height"]; r = abs(int((s.get("side_data_list") or [{}])[0].get("rotation", 0)))
    if r in (90, 270): w, h = h, w
    return w, h, float(j["format"]["duration"])
def job(item):
    slug, (k, segs) = item; dst = f"{out}/v/full-{k}.mp4"; p = src(k); w, h, dur = probe(p)
    if segs: wins = [(shots[s]["a"], shots[s]["b"]) for s in segs]
    else: wins = [(0.0, min(dur - 0.1, 170.0))]
    total = sum(b - a for a, b in wins); tw = 960 if w >= h else 576
    if k == "V6": tw = 1280
    tw = min(tw, w)
    kbps = int(max(300, min(2500, 17.0 * 8 * 1024 / total)))
    if not os.path.exists(dst):
        fc = ";".join(f"[0:v]trim=start={a:.2f}:end={b:.2f},setpts=PTS-STARTPTS[v{i}]" for i, (a, b) in enumerate(wins))
        fc += ";" + "".join(f"[v{i}]" for i in range(len(wins))) + f"concat=n={len(wins)}:v=1:a=0[c];[c]scale={tw}:-2:flags=lanczos,{GRADE},fps=30,fade=t=in:st=0:d=0.4,fade=t=out:st={max(0, total - 0.5):.2f}:d=0.5,format=yuv420p[o]"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", p, "-filter_complex", fc, "-map", "[o]", "-an", "-c:v", "libx264", "-crf", "26", "-maxrate", f"{kbps}k", "-bufsize", f"{kbps * 2}k", "-preset", "slow", "-profile:v", "high", "-movflags", "+faststart", dst])
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{min(2.0, total / 2):.2f}", "-i", dst, "-frames:v", "1", "-q:v", "4", f"{out}/v/full-{k}.jpg"])
    return slug, k, round(total), os.path.getsize(dst) // 1024
res = {}
with ThreadPoolExecutor(3) as ex:
    for slug, k, d, kb in ex.map(job, E.FULL.items()): res[slug] = {"k": k, "dur": d}; print(slug, k, d, "s", kb, "KB", flush=True)
json.dump(res, open(f"{out}/full.json", "w")); print("DONE")
