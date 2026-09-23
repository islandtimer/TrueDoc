"""Every conversion says what made it: the package and the commit, the options in force, the readers and where they
ran, and the seconds it took - in the status (`--status`, `convert_with_status`) and in the front matter. Without it a
conversion made before a change cannot be told from one made after. An address is written without its credentials."""
import re

import pymupdf
import yaml

from truedoc import __version__
from truedoc.build import _without_credentials, record
from truedoc.pipeline import ConvertOptions, convert_with_status

OFF = ConvertOptions(layout=False, ocr=False, math=False, marks=False)


def _pdf(tmp_path):
    doc = pymupdf.open()
    page = doc.new_page(width=400, height=500)
    page.insert_text((40, 60), "A page with one line of text on it.", fontsize=11)
    path = tmp_path / "one.pdf"
    doc.save(str(path))
    doc.close()
    return str(path)


def test_the_status_says_what_made_the_conversion(tmp_path):
    result = convert_with_status(_pdf(tmp_path), OFF)
    build = result.as_dict()["build"]
    assert build["code"]["package"] == __version__
    commit = build["code"]["commit"]
    assert commit is None or re.fullmatch(r"[0-9a-f]{40}", commit)
    assert build["options"]["layout"] is False and build["options"]["ocr"] is False
    assert "layout" not in build["readers"] and "ocr" not in build["readers"]
    assert build["readers"]["pdf"]["pdfium"]
    assert build["seconds"] >= 0


def test_the_front_matter_carries_the_same_record(tmp_path):
    result = convert_with_status(_pdf(tmp_path), ConvertOptions(layout=False, ocr=False, math=False, marks=False, frontmatter=True))
    front = yaml.safe_load(result.markdown.split("---")[1])
    assert front["truedoc"]["build"]["code"] == result.build["code"]
    assert front["truedoc"]["build"]["options"]["pages"] is None


def test_an_address_is_written_without_its_credentials():
    opts = ConvertOptions(vision_endpoint="http://reader:secret@gpu.example:8000", vision_deep="anthropic")
    build = record(opts, 1.0)
    assert "secret" not in str(build)
    assert build["readers"]["vision"]["where"] == "http://gpu.example:8000"
    assert build["readers"]["deep"]["where"] == "the Anthropic API"
    assert _without_credentials("file:C:/readings") == "file:C:/readings"
    assert record(ConvertOptions(vision_endpoint="file:some/folder"), 0.0)["readers"]["vision"]["where"] == "readings replayed from disk"
