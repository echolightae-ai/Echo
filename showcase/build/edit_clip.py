"""Edit existing clips in the showcase. Run from the repo; then run release.py to publish.

  edit_clip.py trim   V83 0 8.6                  # keep only 0 s to 8.6 s of clip V83 (re-encoded from the original if --orig is given)
  edit_clip.py trim   V118 41 55.7 --as V118b    # keep a second piece as a new clip next to the original
  edit_clip.py remove V116 [--delete-file]       # take a clip off the site (it stays listed in COVERAGE.csv as removed)
  edit_clip.py move   V114 projection-mapping-showcase [--svc mapping]
  edit_clip.py svc    V117 mapping               # change a clip's service tags (comma separated)
"""
import argparse, csv, json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); EV = f"{ROOT}/content/events.json"; MV = f"{ROOT}/media/v"
ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["trim", "remove", "move", "svc"]); ap.add_argument("id"); ap.add_argument("a", nargs="?"); ap.add_argument("b", nargs="?")
ap.add_argument("--as", dest="newid"); ap.add_argument("--orig"); ap.add_argument("--svc"); ap.add_argument("--delete-file", action="store_true"); n = ap.parse_args()
ev = json.load(open(EV))
def find(i):
    for e in ev:
        for c in e["clips"]:
            if c["k"] == i: return e, c
    sys.exit(f"clip {i} not found")
e, c = find(n.id)
if n.cmd == "trim":
    s, t = float(n.a), float(n.b); src = n.orig or f"{MV}/{n.id}.mp4"; nid = n.newid or n.id; tmp = f"{MV}/_tmp.mp4"; dur = t - s
    pr = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height:stream_side_data=rotation", "-of", "json", src], capture_output=True, text=True).stdout)["streams"][0]
    w, h = pr["width"], pr["height"]; rot = abs(int((pr.get("side_data_list") or [{}])[0].get("rotation", 0)))
    if rot in (90, 270): w, h = h, w
    tw = min(w, 576 if h >= w else 960); tw -= tw % 2
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{s:.2f}", "-t", f"{dur:.2f}", "-i", src, "-an", "-vf", f"scale={tw}:-2:flags=lanczos,eq=contrast=1.04:saturation=1.08,fps=30,format=yuv420p", "-c:v", "libx264", "-crf", "27", "-preset", "medium", "-profile:v", "high", "-movflags", "+faststart", tmp], check=True)
    os.replace(tmp, f"{MV}/{nid}.mp4"); subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{dur * 0.4:.2f}", "-i", f"{MV}/{nid}.mp4", "-frames:v", "1", "-q:v", "4", f"{MV}/{nid}.jpg"], check=True)
    if nid == n.id: c["d"] = round(dur, 1)
    else: e["clips"].append(dict(c, k=nid, f=nid, d=round(dur, 1)))
    print(f"{nid}: {dur:.1f}s kept")
elif n.cmd == "remove":
    e["clips"].remove(c)
    if n.delete_file:
        for ext in ("mp4", "jpg"):
            p = f"{MV}/{c['f']}.{ext}" if c["t"] == "v" else f"{ROOT}/media/i/{c['f']}.jpg"
            if os.path.exists(p): os.remove(p)
    print("removed", n.id, "from", e["slug"])
elif n.cmd == "move":
    e["clips"].remove(c); dst = next(x for x in ev if x["slug"] == n.a); dst["clips"].append(c)
    if n.svc: c["svc"] = n.svc.split(",")
    c["svc"] = [s for s in c["svc"] if s in dst["svc"]] or dst["svc"][:1]; print("moved", n.id, "->", n.a, c["svc"])
elif n.cmd == "svc":
    c["svc"] = n.a.split(","); print(n.id, "->", c["svc"])
json.dump(ev, open(EV, "w"), ensure_ascii=False, separators=(",", ":"))
