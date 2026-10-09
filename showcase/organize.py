"""Sort a whole unsorted camera roll into event folders for the showcase. You don't organize anything.

    python showcase/organize.py "D:/Phone/DCIM"            # sort, then let Claude pick the event shots
    python showcase/organize.py "D:/Phone/DCIM" --no-ai    # sort only; review the contact sheets yourself

1. Reads when (and where, if the phone saved GPS) every photo and video was taken. Nothing is uploaded for this.
2. Groups them into events: shots taken within a few hours of each other at the same place are one event.
3. Makes one contact sheet per group and asks Claude whether it is an EchoLight event or something else
   (family, warehouse, receipts, screenshots). For real events Claude names it (venue and city only, never the
   client), tags the event type and services, and picks the best shots.
4. Copies only the picked shots into showcase/inbox/<date> <title>/ and writes showcase/inbox/REVIEW.md.

Then run `python showcase/build.py` to put them on the page. The originals are never moved or changed.
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import math
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

import build

INBOX = build.INBOX
IMAGE_EXT = build.IMAGE_EXT
VIDEO_EXT = build.VIDEO_EXT
GAP = timedelta(hours=4)          # a pause longer than this starts a new event
MOVE_KM = 3.0                     # ...and so does moving further than this
MIN_ITEMS = 6                     # fewer shots than this is not an event worth showing
SHEET_TILES = 30
KEEP_PHOTOS = 12
KEEP_VIDEOS = 3

# Emirate centres, for naming the city from GPS without any online lookup.
CITIES = {
    "Abu Dhabi": (24.4539, 54.3773), "Dubai": (25.2048, 55.2708), "Al Ain": (24.2075, 55.7447),
    "Sharjah": (25.3463, 55.4209), "Ajman": (25.4052, 55.5136), "Umm Al Quwain": (25.5647, 55.5552),
    "Ras Al Khaimah": (25.8007, 55.9762), "Fujairah": (25.1288, 56.3265),
}


@dataclass
class Shot:
    path: Path
    when: datetime
    gps: tuple[float, float] | None
    video: bool


@dataclass
class Group:
    shots: list[Shot] = field(default_factory=list)

    @property
    def start(self) -> datetime:
        return self.shots[0].when

    @property
    def city(self) -> str:
        pts = [s.gps for s in self.shots if s.gps]
        if not pts:
            return ""
        lat, lon = sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
        name, dist = min(((n, km((lat, lon), c)) for n, c in CITIES.items()), key=lambda x: x[1])
        return name if dist < 40 else ""


def km(a: tuple[float, float], b: tuple[float, float]) -> float:
    la1, lo1, la2, lo2 = map(math.radians, (*a, *b))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


# ---------------------------------------------------------------- reading the camera roll

NAME_DATE = re.compile(r"(20\d{2})[-_]?(\d{2})[-_]?(\d{2})(?:[-_ ]?(\d{2})[-_.]?(\d{2})[-_.]?(\d{2}))?")


def date_from_name(name: str) -> datetime | None:
    m = NAME_DATE.search(name)
    if not m:
        return None
    y, mo, d, hh, mi, ss = (int(x) if x else 0 for x in m.groups())
    try:
        return datetime(y, mo, d, hh, mi, ss)
    except ValueError:
        return None


def _gps(raw: dict) -> tuple[float, float] | None:
    try:
        def deg(v):
            return float(v[0]) + float(v[1]) / 60 + float(v[2]) / 3600
        lat, lon = deg(raw[2]), deg(raw[4])
        if raw.get(1) == "S":
            lat = -lat
        if raw.get(3) == "W":
            lon = -lon
        return (lat, lon) if lat or lon else None
    except (KeyError, TypeError, ValueError, IndexError, ZeroDivisionError):
        return None


def read_photo(path: Path) -> tuple[datetime | None, tuple[float, float] | None]:
    from PIL import Image

    try:
        with Image.open(path) as img:
            exif = img.getexif()
            taken = exif.get_ifd(0x8769).get(36867) or exif.get(306)
            gps = _gps(dict(exif.get_ifd(0x8825)))
    except Exception:
        return None, None
    when = None
    if taken:
        try:
            when = datetime.strptime(str(taken).strip()[:19], "%Y:%m:%d %H:%M:%S")
        except ValueError:
            pass
    return when, gps


def read_video(path: Path) -> tuple[datetime | None, tuple[float, float] | None]:
    if not shutil.which("ffprobe"):
        return None, None
    out = subprocess.run(["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(path)],
                         capture_output=True, text=True)
    try:
        tags = json.loads(out.stdout)["format"].get("tags", {})
    except (json.JSONDecodeError, KeyError):
        return None, None
    tags = {k.lower(): v for k, v in tags.items()}
    when = None
    try:
        if tags.get("com.apple.quicktime.creationdate"):  # iPhone: local time with its offset
            when = datetime.fromisoformat(tags["com.apple.quicktime.creationdate"]).replace(tzinfo=None)
        elif tags.get("creation_time"):  # UTC; the UAE is UTC+4 all year
            utc = datetime.fromisoformat(tags["creation_time"].replace("Z", "+00:00"))
            when = utc.replace(tzinfo=None) + timedelta(hours=4)
    except ValueError:
        pass
    gps = None
    loc = tags.get("com.apple.quicktime.location.iso6709") or tags.get("location")
    m = re.match(r"([+-]\d+\.\d+)([+-]\d+\.\d+)", loc or "")
    if m:
        gps = (float(m.group(1)), float(m.group(2)))
    return when, gps


def scan(root: Path) -> tuple[list[Shot], int]:
    build.register_heic()
    files = [p for p in root.rglob("*") if p.is_file() and not p.name.startswith(".")]
    stems = {p.with_suffix("").name.lower() for p in files if p.suffix.lower() in IMAGE_EXT}
    shots, skipped = [], 0
    for p in files:
        ext = p.suffix.lower()
        if ext not in IMAGE_EXT and ext not in VIDEO_EXT:
            continue
        low = p.name.lower()
        if "screenshot" in low or "screen_recording" in low or "screenrecord" in low:
            skipped += 1
            continue
        video = ext in VIDEO_EXT
        # iPhone Live Photos save a 3-second .MOV next to each photo; the photo is enough.
        if video and p.with_suffix("").name.lower() in stems:
            skipped += 1
            continue
        when, gps = read_video(p) if video else read_photo(p)
        when = when or date_from_name(p.name)
        if not when:
            when = datetime.fromtimestamp(p.stat().st_mtime)
        shots.append(Shot(p, when, gps, video))
    shots.sort(key=lambda s: s.when)
    return shots, skipped


def group(shots: list[Shot]) -> list[Group]:
    groups: list[Group] = []
    last_gps = None
    for s in shots:
        g = groups[-1] if groups else None
        moved = s.gps and last_gps and km(s.gps, last_gps) > MOVE_KM
        if not g or s.when - g.shots[-1].when > GAP or moved:
            groups.append(Group())
        groups[-1].shots.append(s)
        last_gps = s.gps or last_gps
    return groups


# ---------------------------------------------------------------- contact sheets

def thumb(shot: Shot, px: int = 300):
    from PIL import Image

    if shot.video:
        if not shutil.which("ffmpeg"):
            return None
        out = subprocess.run(["ffmpeg", "-v", "quiet", "-ss", "1", "-i", str(shot.path), "-frames:v", "1",
                              "-f", "image2pipe", "-vcodec", "mjpeg", "-"], capture_output=True)
        if not out.stdout:
            return None
        img = Image.open(io.BytesIO(out.stdout)).convert("RGB")
    else:
        img = build._open_image(shot.path)
        if img is None:
            return None
    img.thumbnail((px, px))
    return img


def sample(g: Group) -> list[Shot]:
    """An even spread across the whole event, so the sheet shows setup, show and crowd alike."""
    if len(g.shots) <= SHEET_TILES:
        return list(g.shots)
    step = len(g.shots) / SHEET_TILES
    return [g.shots[int(i * step)] for i in range(SHEET_TILES)]


def contact_sheet(shots: list[Shot]):
    from PIL import Image, ImageDraw

    tiles = [(i, s, thumb(s)) for i, s in enumerate(shots, 1)]
    tiles = [t for t in tiles if t[2] is not None]
    if not tiles:
        return None, []
    cols, cell = 6, 300
    rows = math.ceil(len(tiles) / cols)
    sheet = Image.new("RGB", (cols * cell, rows * cell), (12, 12, 18))
    draw = ImageDraw.Draw(sheet)
    for k, (i, s, img) in enumerate(tiles):
        x, y = (k % cols) * cell, (k // cols) * cell
        sheet.paste(img, (x + (cell - img.width) // 2, y + (cell - img.height) // 2))
        label = f"{i}{' VIDEO' if s.video else ''}"
        draw.rectangle([x + 4, y + 4, x + 14 + 9 * len(label), y + 26], fill=(0, 0, 0))
        draw.text((x + 9, y + 8), label, fill=(255, 255, 255))
    return sheet, [i for i, _, _ in tiles]


# ---------------------------------------------------------------- Claude decides what each group is

def ask_claude(client, catalog: dict, g: Group, sheet) -> dict | None:
    import anthropic
    from pydantic import BaseModel

    event_ids = [e["id"] for e in catalog["eventTypes"]]
    service_ids = [s["id"] for s in catalog["services"]]

    class Verdict(BaseModel):
        is_event: bool
        reason: str
        title: str
        summary: str
        venue: str
        eventTypes: list[str]
        services: list[str]
        tags: list[str]
        best: list[int]

    buf = io.BytesIO()
    sheet.save(buf, "JPEG", quality=80)
    photos = sum(not s.video for s in g.shots)
    prompt = (
        "This contact sheet shows numbered shots (an even sample) from one day on the phone of the owner of "
        "EchoLight, an event production company in the UAE (stage lighting, LED screens, sound, 3D projection "
        "mapping, laser and light shows, stages).\n"
        f"Date: {g.start:%A %d %B %Y, from %H:%M}. City from GPS: {g.city or 'unknown'}. "
        f"{photos} photos and {len(g.shots) - photos} videos in total.\n\n"
        "- is_event: true only if this shows an event EchoLight produced or rigged (lit stages, LED walls, "
        "moving heads, lasers, sound systems, decorated venues, crowds at such an event). False for family or "
        "personal photos, warehouse or equipment stock, documents, receipts, screenshots, travel.\n"
        "- reason: one short sentence on why.\n"
        "- title: a portfolio title, max 7 words, like 'Gala Dinner at Saadiyat Rotana' or 'Outdoor Wedding "
        "Laser Entrance'. Never use a person's, client's or brand's name; a venue or hotel name you can read is fine.\n"
        "- summary: one or two sentences on what EchoLight delivered and the effect. No numbers you can't see.\n"
        "- venue: the venue if it is readable on signage, else an empty string.\n"
        f"- eventTypes: 1-2 of {event_ids}, most fitting first.\n"
        f"- services: the ones clearly visible, from {service_ids}.\n"
        "- tags: 3-6 short lowercase words a client might search for (e.g. 'outdoor', 'ballroom', 'bridal walk').\n"
        f"- best: up to {KEEP_PHOTOS + KEEP_VIDEOS} tile numbers for the portfolio, best first. Pick shots that "
        "show the lighting at its best during the event; skip blurry, dark, duplicate, empty-venue and "
        "people-close-up shots. Include VIDEO tiles that look strong.\n"
        "If is_event is false, leave the other text fields empty and best as []."
    )
    try:
        response = client.messages.parse(
            model="claude-opus-5-5",
            max_tokens=4000,
            output_config={"effort": "low"},
            messages=[{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                             "data": base64.standard_b64encode(buf.getvalue()).decode()}},
                {"type": "text", "text": prompt},
            ]}],
            output_format=Verdict,
        )
    except anthropic.APIError as exc:
        print(f"  ! Claude could not look at the {g.start:%d %b %Y} group: {exc}")
        return None
    if response.parsed_output is None:
        return None
    v = response.parsed_output.model_dump()
    v["eventTypes"] = [e for e in v["eventTypes"] if e in event_ids][:2]
    v["services"] = [s for s in v["services"] if s in service_ids]
    return v


# ---------------------------------------------------------------- writing the inbox

def safe(text: str) -> str:
    return re.sub(r'[<>:"/\\|?*\n\r\t]+', " ", text).strip(" .")[:80] or "Event"


def copy_picks(g: Group, picks: list[Shot], dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    for n, s in enumerate(picks, 1):
        shutil.copy2(s.path, dest / f"{n:02d}{s.path.suffix.lower()}")


def organize(root: Path, use_ai: bool = True, limit: int = 0) -> list[dict]:
    catalog = json.loads(build.CATALOG.read_text(encoding="utf-8"))
    print(f"Reading {root} ...")
    shots, skipped = scan(root)
    groups = [g for g in group(shots) if len(g.shots) >= MIN_ITEMS]
    print(f"{len(shots)} photos and videos ({skipped} screenshots and Live Photo clips ignored), "
          f"{len(groups)} possible events.")
    if limit:
        groups = groups[-limit:]

    client = None
    if use_ai:
        try:
            import anthropic
            client = anthropic.Anthropic()
        except Exception as exc:
            print(f"Claude isn't available ({exc}); sorting by date only. Run with an ANTHROPIC_API_KEY to pick events.")

    done = {p.get("source") for p in catalog["projects"]}
    INBOX.mkdir(parents=True, exist_ok=True)
    report = []
    for g in groups:
        when = f"{g.start:%Y-%m-%d}"
        picks_from, verdict = sample(g), None
        sheet, _ = contact_sheet(picks_from)
        if sheet is None:
            continue
        if client:
            verdict = ask_claude(client, catalog, g, sheet)
        row = {"date": when, "city": g.city, "shots": len(g.shots)}
        if verdict and not verdict["is_event"]:
            row.update(kept=False, reason=verdict["reason"])
            report.append(row)
            print(f"  - {when}: skipped ({verdict['reason']})")
            continue

        title = verdict["title"] if verdict else f"Event {g.start:%d %b}"
        name = safe(f"{when} {title}" + (f" - {g.city}" if g.city and g.city.lower() not in title.lower() else ""))
        if name in done:
            continue
        if verdict:
            # Keep Claude's picks in its order; fall back to an even spread if it named no tiles.
            chosen = [picks_from[i - 1] for i in verdict["best"] if 1 <= i <= len(picks_from)]
            photos = [s for s in chosen if not s.video][:KEEP_PHOTOS]
            videos = [s for s in chosen if s.video][:KEEP_VIDEOS]
            picks = photos + videos or picks_from[:KEEP_PHOTOS]
            dest = INBOX / name
            copy_picks(g, picks, dest)
            (dest / "info.json").write_text(json.dumps({
                "title": title, "summary": verdict["summary"], "venue": verdict["venue"], "city": g.city,
                "eventTypes": verdict["eventTypes"], "services": verdict["services"], "tags": verdict["tags"],
            }, ensure_ascii=False, indent=1), encoding="utf-8")
            sheet.save(dest / "_contact-sheet.jpg", quality=80)
            row.update(kept=True, folder=name, picked=len(picks), reason=verdict["reason"])
            print(f"  + {name}: {len(picks)} best of {len(g.shots)}")
        else:
            # No Claude: park the group with its contact sheet for a human (or Claude Code) to look at.
            dest = INBOX / "_to-review" / name
            copy_picks(g, picks_from[:KEEP_PHOTOS + KEEP_VIDEOS], dest)
            sheet.save(dest / "_contact-sheet.jpg", quality=80)
            row.update(kept=None, folder=f"_to-review/{name}")
            print(f"  ? {name}: needs a look")
        report.append(row)

    write_report(report)
    return report


def write_report(rows: list[dict]) -> None:
    kept = [r for r in rows if r.get("kept")]
    review = [r for r in rows if r.get("kept") is None]
    skipped = [r for r in rows if r.get("kept") is False]
    lines = ["# Camera roll sort", "",
             f"{len(kept)} events picked for the showcase, {len(review)} waiting for a look, {len(skipped)} skipped.", ""]
    if kept:
        lines += ["## Picked (run `python showcase/build.py` to publish)", "",
                  "Delete a folder in `showcase/inbox/` to leave that event out.", ""]
        lines += [f"- **{r['folder']}**: {r['picked']} of {r['shots']} shots. {r['reason']}" for r in kept] + [""]
    if review:
        lines += ["## Waiting for a look", "",
                  "Open `_contact-sheet.jpg` in each folder. Move the ones that are events up into `showcase/inbox/`, "
                  "renamed to say what they are, and delete the rest.", ""]
        lines += [f"- {r['folder']} ({r['shots']} shots)" for r in review] + [""]
    if skipped:
        lines += ["## Skipped (not events)", ""]
        lines += [f"- {r['date']} {r['city']} ({r['shots']} shots): {r['reason']}" for r in skipped] + [""]
    (INBOX / "REVIEW.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {INBOX / 'REVIEW.md'}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder", type=Path, help="the camera folder copied from your phone (for example DCIM)")
    ap.add_argument("--no-ai", action="store_true", help="only group by date and place; don't ask Claude")
    ap.add_argument("--latest", type=int, default=0, metavar="N", help="only the N most recent events (a quick test)")
    args = ap.parse_args(argv)
    if not args.folder.is_dir():
        print(f"{args.folder} is not a folder. Copy the DCIM folder from your phone to your laptop and point at that.")
        return 1
    organize(args.folder, use_ai=not args.no_ai, limit=args.latest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
