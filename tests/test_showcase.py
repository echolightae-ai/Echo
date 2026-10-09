import importlib.util
import json
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
