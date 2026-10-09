import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("showcase_build", ROOT / "showcase" / "build.py")
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)

CATALOG = json.loads((ROOT / "showcase" / "catalog.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "text, event, services, city",
    [
        ("2025-03 Rixos corporate gala - LED wall and laser opening", "corporate", {"led-screens", "laser-light"}, ""),
        ("Wedding in Dubai with bridal walk", "wedding", set(), "Dubai"),
        ("عرس في أبوظبي مع شاشة ليد", "wedding", {"led-screens"}, "Abu Dhabi"),
        ("حفل اليوم الوطني", "government", set(), ""),
        ("Car launch, projection mapping on the car", "launch", {"3d-mapping"}, ""),
    ],
)
def test_detect_reads_english_and_arabic(text, event, services, city):
    found = build.detect(CATALOG, text)
    assert found["eventTypes"][0] == event
    assert services <= set(found["services"])
    assert found["city"] == city


def test_detect_needs_whole_words():
    # "led" inside "called" and "pa" inside "party" must not count as services.
    assert build.detect(CATALOG, "a party called Winter")["services"] == []


def test_folder_name_gives_year_and_title():
    assert build.parse_folder_name("2025-12 National Day - Abu Dhabi") == (2025, "National Day - Abu Dhabi")
    assert build.parse_folder_name("Saadiyat wedding") == (None, "Saadiyat wedding")


def test_catalog_ids_are_consistent():
    events = {e["id"] for e in CATALOG["eventTypes"]}
    services = {s["id"] for s in CATALOG["services"]}
    ids = [p["id"] for p in CATALOG["projects"]]
    assert len(ids) == len(set(ids))
    for p in CATALOG["projects"]:
        assert set(p["eventTypes"]) <= events, p["id"]
        assert set(p["services"]) <= services, p["id"]
    for e in CATALOG["eventTypes"]:
        assert set(e["essential"] + e["elevate"] + e["signature"]) <= services, e["id"]


def test_inbox_folder_becomes_a_project(tmp_path, monkeypatch):
    Image = pytest.importorskip("PIL.Image")
    catalog = tmp_path / "catalog.json"
    catalog.write_text(json.dumps({**CATALOG, "projects": []}), encoding="utf-8")
    inbox = tmp_path / "inbox"
    folder = inbox / "2026-02 Corniche Wedding - Abu Dhabi"
    folder.mkdir(parents=True)
    Image.new("RGB", (3000, 2000), "navy").save(folder / "IMG_0001.jpg")
    (folder / "notes.txt").write_text("Outdoor wedding, laser and cold sparks for the zaffa", encoding="utf-8")
    for name, value in {"CATALOG": catalog, "INBOX": inbox, "MEDIA": tmp_path / "media",
                        "OUT": tmp_path / "index.html", "HERE": tmp_path}.items():
        monkeypatch.setattr(build, name, value)

    build.build()

    saved = json.loads(catalog.read_text(encoding="utf-8"))
    (project,) = saved["projects"]
    assert project["title"] == "Corniche Wedding - Abu Dhabi"
    assert project["year"] == 2026 and project["city"] == "Abu Dhabi"
    assert project["eventTypes"][0] == "wedding" and "laser-light" in project["services"]
    photo = tmp_path / project["media"][0]["src"]
    assert max(Image.open(photo).size) == build.PHOTO_PX
    page = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert "Corniche Wedding" in page and "__CATALOG__" not in page

    build.build()  # running again does not import the same folder twice
    assert len(json.loads(catalog.read_text(encoding="utf-8"))["projects"]) == 1


def test_page_data_cannot_close_its_script_tag(monkeypatch):
    catalog = {**CATALOG, "projects": [{**CATALOG["projects"][0], "summary": "</script><b>x</b>"}]}
    html = build.render(catalog)
    blob = html.split('<script id="catalog" type="application/json">')[1].split("</script>")[0]
    assert json.loads(blob)["projects"][0]["summary"] == "</script><b>x</b>"


def _photo(path, when, gps=None, color="navy"):
    Image = pytest.importorskip("PIL.Image")
    img = Image.new("RGB", (800, 600), color)
    exif = Image.Exif()
    exif.get_ifd(0x8769)[36867] = when
    if gps:
        def dms(v):
            return (int(v), int(v * 60 % 60), round(v * 3600 % 60, 2))
        exif.get_ifd(0x8825).update({1: "N", 2: dms(gps[0]), 3: "E", 4: dms(gps[1])})
    img.save(path, exif=exif)


@pytest.fixture
def organize(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "showcase"))
    spec = importlib.util.spec_from_file_location("showcase_organize", ROOT / "showcase" / "organize.py")
    mod = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, "showcase_organize", mod)
    spec.loader.exec_module(mod)
    monkeypatch.setattr(mod, "INBOX", tmp_path / "inbox")
    return mod


def _camera_roll(root):
    root.mkdir()
    # A wedding night in Abu Dhabi, a family lunch in Dubai a week later, plus noise.
    for i in range(8):
        _photo(root / f"IMG_{100 + i}.JPG", f"2026:02:14 21:{10 + i * 5}:00", (24.46, 54.38))
    for i in range(7):
        _photo(root / f"IMG_{200 + i}.JPG", f"2026:02:21 13:{10 + i}:00", (25.20, 55.27), "green")
    _photo(root / "Screenshot_20260214-211500.png", "2026:02:14 21:15:00")
    (root / "IMG_100.MOV").write_bytes(b"live photo clip")


def test_camera_roll_is_grouped_into_events(tmp_path, organize):
    _camera_roll(tmp_path / "DCIM")
    shots, skipped = organize.scan(tmp_path / "DCIM")
    assert skipped == 2  # the screenshot and the Live Photo clip
    groups = organize.group(shots)
    assert [len(g.shots) for g in groups] == [8, 7]
    assert [g.city for g in groups] == ["Abu Dhabi", "Dubai"]


def test_claude_keeps_events_and_drops_the_rest(tmp_path, organize, monkeypatch):
    _camera_roll(tmp_path / "DCIM")

    def fake_claude(client, catalog, g, sheet):
        if g.city == "Dubai":
            return {"is_event": False, "reason": "A family lunch."}
        return {"is_event": True, "reason": "Lit wedding stage.", "title": "Garden Wedding Spotlights",
                "summary": "Spotlights over the aisle.", "venue": "", "eventTypes": ["wedding"],
                "services": ["stage-lighting"], "tags": ["outdoor"], "best": [3, 1, 99]}

    monkeypatch.setattr(organize, "ask_claude", fake_claude)
    monkeypatch.setattr("anthropic.Anthropic", lambda: object())
    organize.organize(tmp_path / "DCIM")

    inbox = tmp_path / "inbox"
    (folder,) = [p for p in inbox.iterdir() if p.is_dir()]
    assert folder.name == "2026-02-14 Garden Wedding Spotlights - Abu Dhabi"
    assert sorted(p.name for p in folder.iterdir()) == ["01.jpg", "02.jpg", "_contact-sheet.jpg", "info.json"]
    report = (inbox / "REVIEW.md").read_text(encoding="utf-8")
    assert "1 events picked" in report and "A family lunch." in report


def test_without_claude_groups_wait_for_review(tmp_path, organize):
    _camera_roll(tmp_path / "DCIM")
    organize.organize(tmp_path / "DCIM", use_ai=False)
    waiting = sorted(p.name for p in (tmp_path / "inbox" / "_to-review").iterdir())
    assert len(waiting) == 2 and waiting[0].startswith("2026-02-14")


def test_sorted_event_lands_on_the_page(tmp_path, organize, monkeypatch):
    _camera_roll(tmp_path / "DCIM")
    monkeypatch.setattr(organize, "ask_claude", lambda client, catalog, g, sheet: {
        "is_event": g.city == "Abu Dhabi", "reason": "", "title": "Garden Wedding Spotlights", "summary": "Spotlights over the aisle.",
        "venue": "Emirates Palace", "eventTypes": ["wedding"], "services": ["stage-lighting", "laser-light"],
        "tags": ["outdoor"], "best": [1, 2]})
    monkeypatch.setattr("anthropic.Anthropic", lambda: object())
    organize.organize(tmp_path / "DCIM")

    b = organize.build
    catalog = tmp_path / "catalog.json"
    catalog.write_text(json.dumps({**CATALOG, "projects": []}), encoding="utf-8")
    for name, value in {"CATALOG": catalog, "INBOX": tmp_path / "inbox", "MEDIA": tmp_path / "media",
                        "OUT": tmp_path / "index.html", "HERE": tmp_path}.items():
        monkeypatch.setattr(b, name, value)
    b.build()

    projects = json.loads(catalog.read_text(encoding="utf-8"))["projects"]
    assert len(projects) == 1  # the Dubai lunch went nowhere, the contact sheet isn't a photo
    p = projects[0]
    assert (p["title"], p["venue"], p["city"], p["year"]) == ("Garden Wedding Spotlights", "Emirates Palace", "Abu Dhabi", 2026)
    assert p["services"] == ["stage-lighting", "laser-light"] and len(p["media"]) == 2
