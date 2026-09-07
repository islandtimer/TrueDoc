"""A model's saved page readings replayed from disk (`--vision-endpoint file:<folder>`).

The folder is laid out as a benchmark candidate (`<category>/<stem>_pg1_repeat1.md`); a reading
may start with olmOCR's small YAML front matter, which is not page text; a page with no saved
reading yields nothing, so the pipeline leaves it as it was.
"""
import os

from truedoc.vision import make_provider
from truedoc.vision.file_readings import FileReadings


def _folder(tmp_path):
    cat = tmp_path / "old_scans"
    cat.mkdir()
    (cat / "abc_pg1_repeat1.md").write_text("---\nprimary_language: en\nis_table: false\n---\nDear Sir,\n\nYour letter arrived.\n", encoding="utf-8")
    (cat / "flat.md").write_text("A flat reading\n", encoding="utf-8")
    return str(tmp_path)


def test_reading_found_by_stem_and_front_matter_stripped(tmp_path):
    p = FileReadings(_folder(tmp_path))
    assert p.read_page(os.path.join("anywhere", "abc.pdf"), 1) == "Dear Sir,\n\nYour letter arrived."
    assert p.read_page("flat.pdf", 1) == "A flat reading"
    assert p.read_page("missing.pdf", 1) is None
    assert p.read_region("abc.pdf", 1, (0, 0, 10, 10), "icon") is None


def test_make_provider_routes_file_specs(tmp_path):
    p = make_provider("file:" + _folder(tmp_path), model="olmocr")
    assert isinstance(p, FileReadings) and p.name == "olmocr"


def test_crop_readings_answer_region_questions_through_the_manifest(tmp_path):
    # Session 3's layout: a second folder of crop readings named by the crop tool
    # (`<stem>__r<i>`), with its manifest mapping each crop to a page and a bbox.
    import json

    pages = _folder(tmp_path)
    crops = tmp_path / "crops"
    (crops / "tables").mkdir(parents=True)
    (crops / "tables" / "abc__r0_pg1_repeat1.md").write_text("| a | b |\n|---|---|\n| 1 | 2 |\n", encoding="utf-8")
    (crops / "manifest.json").write_text(json.dumps([{"crop": "tables/abc__r0.pdf", "page": "tables/abc", "bbox": [40.0, 100.0, 360.0, 260.0]}]), encoding="utf-8")
    p = make_provider("file:" + pages + "+" + str(crops))
    assert p.read_page("x/abc.pdf", 1).startswith("Dear Sir")
    assert p.read_region("x/abc.pdf", 1, (42.0, 98.0, 358.0, 262.0), "picture-text") == "| a | b |\n|---|---|\n| 1 | 2 |"
    assert p.read_region("x/abc.pdf", 1, (0.0, 0.0, 50.0, 50.0), "picture-text") is None      # no crop there
    assert p.read_region("x/abc.pdf", 1, (42.0, 98.0, 358.0, 262.0), "figure") is None       # descriptions never come from disk
