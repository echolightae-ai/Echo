"""Build the EchoLight event finder page from catalog.json and the inbox folder.

    python showcase/build.py            # import new inbox folders, write showcase/index.html
    python showcase/build.py --ai       # also let Claude look at the photos and write titles and tags
    python showcase/build.py --embed    # also write dist/echolight-showcase.html with every image inside it

Inbox: make one folder per event in showcase/inbox/, for example
"2025-12 National Day - Abu Dhabi", and drop the photos and videos from your phone into it.
An optional notes.txt in the folder can say anything about the event ("corporate gala at Rixos,
LED wall, laser opening"). See showcase/README.md.
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import re
import shutil
import subprocess
import sys
import unicodedata
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
CATALOG = HERE / "catalog.json"
TEMPLATE = HERE / "template.html"
INBOX = HERE / "inbox"
MEDIA = HERE / "media"
OUT = HERE / "index.html"
DIST = HERE / "dist"

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}
VIDEO_EXT = {".mp4", ".mov", ".m4v"}
MAX_PHOTOS = 12      # per project; the best-looking first ones are kept
MAX_VIDEOS = 3
PHOTO_PX = 1600


# Same rules as norm() in template.html.
def norm(text: str) -> str:
    text = (text or "").lower()
    text = re.sub(r"[ً-ْـ]", "", text)
    text = re.sub(r"[أإآ]", "ا", text)
    text = text.replace("ة", "ه").replace("ى", "ي")
    return re.sub(r"\s+", " ", text).strip()


def hit(text: str, term: str) -> bool:
    term = norm(term)
    if not term:
        return False
    if re.fullmatch(r"[a-z0-9 '&.\-]+", term):
        return re.search(r"(^|[^a-z0-9])" + re.escape(term) + r"(s|es)?(?![a-z0-9])", text) is not None
    return term in text


def detect(catalog: dict, text: str) -> dict:
    """Event types, services and city named in free text (folder name plus notes)."""
    t = norm(text)
    scored = []
    for e in catalog["eventTypes"]:
        score = sum(1 + len(norm(term).split()) for term in e["terms"] + [e["name"]] if hit(t, term))
        if score:
            scored.append((score, e["id"]))
    scored.sort(key=lambda x: -x[0])
    services = [s["id"] for s in catalog["services"] if any(hit(t, term) for term in s["terms"] + [s["name"]])]
    city = next((name for name, terms in catalog["places"].items() if any(hit(t, term) for term in terms + [name])), "")
    return {"eventTypes": [i for _, i in scored[:2]], "services": services, "city": city}


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "project"


def parse_folder_name(name: str) -> tuple[int | None, str]:
    """'2025-12 National Day - Abu Dhabi' -> (2025, 'National Day - Abu Dhabi')."""
    m = re.match(r"\s*((?:19|20)\d{2})(?:[-_. ]\d{1,2})?(?:[-_. ]\d{1,2})?[\s_\-]+(.*)", name)
    if m:
        return int(m.group(1)), m.group(2).strip() or name
    return None, name.strip()


# ---------------------------------------------------------------- media

def register_heic() -> bool:
    """Let Pillow open iPhone HEIC photos, if pillow-heif is installed."""
    try:
        import pillow_heif

        pillow_heif.register_heif_opener()
        return True
    except ImportError:
        return False


def _open_image(path: Path):
    from PIL import Image, ImageOps

    if path.suffix.lower() in {".heic", ".heif"} and not register_heic():
        print(f"  ! skipped {path.name}: install pillow-heif to read iPhone HEIC photos (pip install pillow-heif)")
        return None
    img = Image.open(path)
    return ImageOps.exif_transpose(img).convert("RGB")


def save_photo(src: Path, dest: Path) -> bool:
    try:
        img = _open_image(src)
    except Exception as exc:  # a corrupt or unsupported file should not stop the whole import
        print(f"  ! skipped {src.name}: {exc}")
        return False
    if img is None:
        return False
    img.thumbnail((PHOTO_PX, PHOTO_PX))
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, "JPEG", quality=82, optimize=True, progressive=True)
    return True


def save_video(src: Path, dest: Path, poster: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if shutil.which("ffmpeg"):
        # 720p, web-friendly H.264, starts playing before it finishes downloading.
        enc = subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-vf", "scale='min(1280,iw)':-2",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "27", "-c:a", "aac", "-b:a", "128k",
             "-movflags", "+faststart", str(dest)],
            capture_output=True, text=True,
        )
        if enc.returncode != 0:
            print(f"  ! skipped {src.name}: ffmpeg failed: {enc.stderr.strip()[:200]}")
            return False
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "1", "-i", str(dest), "-frames:v", "1",
                        "-q:v", "4", str(poster)], capture_output=True)
        return True
    if src.suffix.lower() != ".mp4":
        print(f"  ! skipped {src.name}: install ffmpeg to convert .mov videos for the web")
        return False
    print(f"  ! {src.name} copied as-is (install ffmpeg to shrink videos and make a cover image)")
    shutil.copy2(src, dest)
    return True


def import_folder(folder: Path, catalog: dict, use_ai: bool) -> dict | None:
    year, title = parse_folder_name(folder.name)
    notes_file = folder / "notes.txt"
    notes = notes_file.read_text(encoding="utf-8").strip() if notes_file.exists() else ""
    files = sorted(p for p in folder.rglob("*") if p.is_file() and not p.name.startswith((".", "_")))
    photos = [p for p in files if p.suffix.lower() in IMAGE_EXT]
    videos = [p for p in files if p.suffix.lower() in VIDEO_EXT]
    if not photos and not videos:
        print(f"  - {folder.name}: no photos or videos yet, skipped")
        return None

    slug = slugify(title)
    taken = {p["id"] for p in catalog["projects"]}
    base, n = slug, 2
    while slug in taken:
        slug, n = f"{base}-{n}", n + 1

    dest = MEDIA / slug
    media = []
    for i, src in enumerate(videos[:MAX_VIDEOS], 1):
        out, poster = dest / f"video-{i}.mp4", dest / f"video-{i}.jpg"
        if save_video(src, out, poster):
            item = {"type": "video", "src": f"media/{slug}/{out.name}"}
            if poster.exists():
                item["poster"] = f"media/{slug}/{poster.name}"
            media.append(item)
    for i, src in enumerate(photos[:MAX_PHOTOS], 1):
        out = dest / f"photo-{i:02d}.jpg"
        if save_photo(src, out):
            media.append({"type": "image", "src": f"media/{slug}/{out.name}"})
    # Cards show the first item; a photo makes a better cover than a video poster.
    media.sort(key=lambda m: m["type"] != "image")
    if not media:
        return None

    found = detect(catalog, f"{folder.name}\n{notes}")
    city = found["city"] or "UAE"
    project = {
        "id": slug, "title": title, "client": "", "venue": "", "city": city, "year": year,
        "summary": notes.splitlines()[0][:220] if notes else "",
        "eventTypes": found["eventTypes"], "services": found["services"], "tags": [],
        "featured": False, "link": "", "media": media, "source": folder.name,
    }
    info_file = folder / "info.json"
    if info_file.exists():  # written by organize.py, which already looked at the photos
        info = json.loads(info_file.read_text(encoding="utf-8"))
        project.update({k: v for k, v in info.items() if v})
    elif use_ai:
        ai = describe_with_claude(catalog, project, dest, notes)
        if ai:
            project.update(ai)
    if not project["eventTypes"]:
        print(f"  ! {title}: couldn't tell the event type. Add it to notes.txt (e.g. 'wedding') or edit catalog.json")
    if not project["services"]:
        project["services"] = ["stage-lighting"]
        print(f"  ! {title}: no services named; set to Stage Lighting. Say 'LED', 'laser', 'sound'... in notes.txt")
    if not project["summary"]:
        names = [s["name"] for s in catalog["services"] if s["id"] in project["services"]]
        project["summary"] = f"{' and '.join(names)} by EchoLight" + (f" in {city}." if city != "UAE" else ".")
    print(f"  + {title}: {len(media)} files, {project['eventTypes'] or '?'} / {project['services']}")
    return project


# ---------------------------------------------------------------- optional: Claude writes the case study

def describe_with_claude(catalog: dict, project: dict, dest: Path, notes: str) -> dict | None:
    try:
        import anthropic
        from pydantic import BaseModel
    except ImportError:
        print("  ! --ai needs the anthropic package: pip install -r requirements.txt")
        return None

    event_ids = [e["id"] for e in catalog["eventTypes"]]
    service_ids = [s["id"] for s in catalog["services"]]

    class WriteUp(BaseModel):
        title: str
        summary: str
        venue: str
        eventTypes: list[str]
        services: list[str]
        tags: list[str]

    images = sorted(dest.glob("photo-*.jpg"))[:4] + sorted(dest.glob("video-*.jpg"))[:2]
    content = []
    for img in images:
        content.append({"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                                   "data": base64.standard_b64encode(img.read_bytes()).decode()}})
    content.append({"type": "text", "text": (
        "These are photos from an event produced by EchoLight, an AV production company in the UAE "
        "(stage lighting, LED screens, sound, 3D projection mapping, laser and light shows).\n"
        f"Folder name: {project['source']}\nOwner's notes: {notes or '(none)'}\n\n"
        "Write the portfolio entry:\n"
        "- title: short and specific, max 8 words, in the style 'The Twin Beacons' or 'Rixos Clinic Corporate Event'. "
        "Use names only if they are in the folder name or notes; never invent a client, venue or brand.\n"
        "- summary: one or two sentences on what EchoLight delivered and the effect, based only on what you see "
        "and the notes. No prices, no guest numbers unless in the notes.\n"
        "- venue: the venue if named in the folder or notes, else an empty string.\n"
        f"- eventTypes: 1-2 of {event_ids}, most fitting first.\n"
        f"- services: those clearly visible or named, from {service_ids}.\n"
        "- tags: 3-6 short lowercase words a client might search for (e.g. 'outdoor', 'ballroom', 'bridal walk')."
    )})
    try:
        client = anthropic.Anthropic()
        response = client.messages.parse(
            model="claude-opus-5-5",
            max_tokens=2000,
            output_config={"effort": "low"},
            messages=[{"role": "user", "content": content}],
            output_format=WriteUp,
        )
    except anthropic.APIError as exc:
        print(f"  ! Claude could not describe {project['title']}: {exc}")
        return None
    out = response.parsed_output
    if out is None:
        print(f"  ! Claude returned no description for {project['title']} ({response.stop_reason})")
        return None
    result = out.model_dump()
    result["eventTypes"] = [e for e in result["eventTypes"] if e in event_ids][:2] or project["eventTypes"]
    result["services"] = [s for s in result["services"] if s in service_ids] or project["services"]
    return result


# ---------------------------------------------------------------- page

def render(catalog: dict, embed: bool = False) -> str:
    data = json.loads(json.dumps(catalog))
    data["projects"] = [p for p in data["projects"] if p.get("media")]
    if embed:
        for p in data["projects"]:
            # Videos are too heavy to embed: keep their cover image, the project link carries the video.
            p["media"] = [{"type": "image", "src": m["poster"], "video": True} if m["type"] == "video" else m
                          for m in p["media"] if m["type"] != "video" or m.get("poster")]
            for m in p["media"]:
                m["src"] = to_data_uri(m["src"]) or m["src"]
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return TEMPLATE.read_text(encoding="utf-8").replace("__CATALOG__", blob)


def to_data_uri(src: str, px: int = 900) -> str | None:
    from PIL import Image

    try:
        if src.startswith("http"):
            url = re.sub(r"\?format=\d+w$", "", src) + ("?format=1000w" if "squarespace-cdn.com" in src and "/thumbnail" not in src else "")
            with urllib.request.urlopen(url, timeout=30) as resp:
                raw = resp.read()
        else:
            raw = (HERE / src).read_bytes()
        img = Image.open(io.BytesIO(raw)).convert("RGB")
    except Exception as exc:
        print(f"  ! could not embed {src[:80]}: {exc}")
        return None
    img.thumbnail((px, px))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=78, optimize=True, progressive=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def build(use_ai: bool = False, embed: bool = False) -> dict:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    imported = {p.get("source") for p in catalog["projects"]}
    added = 0
    if INBOX.exists():
        for folder in sorted(p for p in INBOX.iterdir() if p.is_dir() and not p.name.startswith((".", "_"))):
            if folder.name in imported:
                continue
            project = import_folder(folder, catalog, use_ai)
            if project:
                catalog["projects"].append(project)
                added += 1
    if added:
        CATALOG.write_text(json.dumps(catalog, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    OUT.write_text(render(catalog), encoding="utf-8")
    live = sum(1 for p in catalog["projects"] if p.get("media"))
    waiting = [p["title"] for p in catalog["projects"] if not p.get("media")]
    print(f"Wrote {OUT.relative_to(HERE.parent)}: {live} projects on the page, {added} new.")
    if waiting:
        print("Waiting for photos: " + "; ".join(waiting))
    if embed:
        DIST.mkdir(exist_ok=True)
        (DIST / "echolight-showcase.html").write_text(render(catalog, embed=True), encoding="utf-8")
        print(f"Wrote {(DIST / 'echolight-showcase.html').relative_to(HERE.parent)} (single file, images inside).")
    return catalog


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ai", action="store_true", help="let Claude write titles, summaries and tags from the photos")
    ap.add_argument("--embed", action="store_true", help="also write a single self-contained HTML file")
    args = ap.parse_args(argv)
    build(use_ai=args.ai, embed=args.embed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
