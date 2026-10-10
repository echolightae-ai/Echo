"""Scan every web clip/photo for given words (e.g. a partner logo that must not appear). Usage: scan_text.py <showcase_dir> zee [word ...]"""
import sys, os, re, glob, json, subprocess, tempfile
from rapidocr_onnxruntime import RapidOCR
root = sys.argv[1]; words = [w.lower() for w in sys.argv[2:]] or ["zee"]
pat = re.compile("|".join(w.replace("e", "[e3]") for w in words), re.I)
ocr = RapidOCR(); hits = []
def scan(img, label, t=None):
    r, _ = ocr(img)
    for box, text, conf in (r or []):
        if pat.search(re.sub(r"\s+", "", text)) and float(conf) > 0.4: hits.append(dict(file=label, t=t, text=text, conf=round(float(conf), 2)))
for p in sorted(glob.glob(f"{root}/media/i/*.jpg")): scan(p, os.path.relpath(p, root))
for p in sorted(glob.glob(f"{root}/media/v/*.mp4")):
    d = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p], capture_output=True, text=True).stdout or 0)
    step = 1.5 if d <= 20 else 3.0; ts = [x * step for x in range(int(d / step) + 1)][:70]
    with tempfile.TemporaryDirectory() as td:
        for i, t in enumerate(ts):
            f = f"{td}/f{i}.jpg"; subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", p, "-frames:v", "1", "-q:v", "3", f], capture_output=True)
            if os.path.exists(f): scan(f, os.path.relpath(p, root), round(t, 1))
json.dump(hits, open(f"{root}/../scan_hits.json" if False else "/tmp/scan_hits.json", "w"), indent=1); print("DONE", len(hits))
