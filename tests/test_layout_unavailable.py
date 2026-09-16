"""A stage that was asked for and could not run is said out loud.

The layout model is optional and a conversion never fails for want of it, but until now it fell back in silence: an
interpreter whose installed libraries it cannot load converted every page without it and the output said nothing.
Twice in two days a measurement was taken from such a run and had to be withdrawn - the second time on ING's home
SPDS page 4, which reads as two stranded paragraphs without the model and as two lists with it. The reason now
reaches the front matter, where anyone reading the conversion can see what did not run.
"""
import pymupdf
import pytest

import truedoc.layout.docling_layout as docling_layout
from truedoc.pipeline import ConvertOptions, convert, load_document

ASKED = ConvertOptions(layout=True, ocr=False, math=False, marks=False, tables=False)
NOT_ASKED = ConvertOptions(layout=False, ocr=False, math=False, marks=False, tables=False)


def _pdf(tmp_path):
    doc = pymupdf.open()
    page = doc.new_page(width=400, height=560)
    page.insert_text((40, 80), "Home Building Insurance", fontsize=12)
    page.insert_text((40, 110), "What you are covered for, and what you are not.", fontsize=10)
    path = tmp_path / "pds.pdf"
    doc.save(str(path))
    doc.close()
    return str(path)


def _refuse(*args, **kwargs):
    raise RuntimeError("tokenizers>=0.21,<0.22 is required, but found tokenizers==0.22.2")


def test_a_model_that_cannot_run_is_named_in_the_warnings(tmp_path, monkeypatch):
    monkeypatch.setattr(docling_layout, "get_detector", _refuse)
    doc = load_document(_pdf(tmp_path), ASKED)
    assert [w for w in doc.warnings if "layout model" in w], doc.warnings
    assert "tokenizers" in " ".join(doc.warnings)


def test_the_warning_reaches_the_front_matter(tmp_path, monkeypatch):
    monkeypatch.setattr(docling_layout, "get_detector", _refuse)
    text = convert(_pdf(tmp_path), ASKED)
    head = text.split("---", 2)[1]
    assert "layout model was asked for and could not run" in head


def test_a_conversion_that_never_asked_for_the_model_says_nothing(tmp_path):
    doc = load_document(_pdf(tmp_path), NOT_ASKED)
    assert not [w for w in doc.warnings if "layout model" in w], doc.warnings


def test_the_page_carries_the_reason_so_a_probe_can_see_it(tmp_path, monkeypatch):
    monkeypatch.setattr(docling_layout, "get_detector", _refuse)
    doc = load_document(_pdf(tmp_path), ASKED)
    assert all("tokenizers" in p.meta.get("layout_unavailable", "") for p in doc.pages)


@pytest.mark.parametrize("layout", [True, False])
def test_the_warning_stays_out_of_the_body(tmp_path, monkeypatch, layout):
    """The warning is front matter: nothing it says reaches a line of the body, so no score can see it."""
    monkeypatch.setattr(docling_layout, "get_detector", _refuse)
    path = _pdf(tmp_path)
    whole = convert(path, ConvertOptions(layout=layout, ocr=False, math=False, marks=False, tables=False))
    body = convert(path, ConvertOptions(layout=layout, ocr=False, math=False, marks=False, tables=False,
                                        frontmatter=False))
    assert whole.split("---", 2)[2].strip() == body.strip()
    assert "layout model" not in body
