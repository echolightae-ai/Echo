"""Make CDN-sized copies of the site media: portrait 576 wide, landscape 960 wide, CRF 27.
Usage: python3 -I shrink_media.py <site_dir> <out_dir>"""
import sys, os, json, subprocess, glob, shutil
from concurrent.futures import ThreadPoolExecutor
site, out = sys.argv[1:3]
os.makedirs(f"{out}/v", exist_ok=True); os.makedirs(f"{out}/i", exist_ok=True)
def probe(p):
    j = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "json", p], capture_output=True, text=True).stdout)["streams"][0]
    return j["width"], j["height"]
def vid(p):
    name = os.path.basename(p); dst = f"{out}/v/{name}"
    if os.path.exists(dst): return name
    w, h = probe(p); full = name.startswith("full-")
    tw = 960 if w >= h else 576
    if full and name == "full-V6.mp4": tw = 1280
    tw = min(tw, w)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", p, "-an", "-vf", f"scale={tw}:-2:flags=lanczos", "-c:v", "libx264", "-crf", "28" if not full else "27", "-preset", "slow", "-profile:v", "high", "-movflags", "+faststart", "-pix_fmt", "yuv420p", dst])
    jp = p[:-4] + ".jpg"
    if os.path.exists(jp):
        from PIL import Image
        im = Image.open(jp).convert("RGB"); im.thumbnail((tw, tw * 2)); im.save(f"{out}/v/{name[:-4]}.jpg", quality=70, optimize=True, progressive=True)
    return name
with ThreadPoolExecutor(4) as ex:
    for n in ex.map(vid, sorted(glob.glob(f"{site}/assets/v/*.mp4"))): print(n, flush=True)
from PIL import Image
for p in glob.glob(f"{site}/assets/img/*.jpg"):
    im = Image.open(p).convert("RGB"); im.thumbnail((1200, 1200)); im.save(f"{out}/i/{os.path.basename(p)}", quality=70, optimize=True, progressive=True)
print("DONE")
