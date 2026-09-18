"""A picture the layout model found and the PDF's own image object are one picture, so one block.

Found 18 September 2026 through a model's caption appearing twice on three pages of run 97: the
fusion refuses a layout figure where a figure stands, and the later step that adds the PDF's image
objects did not look, so a picture both saw was written twice - two `![](figure)` lines, or a
transcription of it twice in the body (209 of the 333 pages with a figure in that run).
"""

import io

import pymupdf
from PIL import Image

from truedoc import pipeline
from truedoc.layout.base import Region, RegionKind
from truedoc.model import BBox, BlockKind
from truedoc.pipeline import ConvertOptions, convert, load_document

PICTURE = (72, 200, 372, 400)          # where the picture is drawn, in page points


def _page_with_a_picture(path, second=None):
    png = io.BytesIO()
    Image.new("RGB", (300, 200), (30, 90, 160)).save(png, format="PNG")
    pdf = pymupdf.open()
    page = pdf.new_page(width=612, height=792)
    page.insert_text((72, 120), "A paragraph above the picture, long enough to be a text layer of its own.")
    page.insert_image(pymupdf.Rect(*PICTURE), stream=png.getvalue())
    if second:
        page.insert_image(pymupdf.Rect(*second), stream=png.getvalue())
    page.insert_text((72, 460), "A paragraph below the picture, so that the picture sits between two blocks.")
    pdf.save(str(path))
    pdf.close()
    return str(path)


def _layout_sees(monkeypatch, *boxes):
    regions = [Region(kind=RegionKind.FIGURE, bbox=BBox(*b), score=0.9) for b in boxes]
    monkeypatch.setattr(pipeline, "_detect_layout", lambda pdf_page, opts, page=None: list(regions))


def _figures(path):
    doc = load_document(path, ConvertOptions(frontmatter=False, math=False, ocr=False))
    return [b for b in doc.pages[0].blocks if b.kind == BlockKind.FIGURE]


def test_a_picture_both_stages_found_is_written_once(tmp_path, monkeypatch):
    pdf = _page_with_a_picture(tmp_path / "one.pdf")
    _layout_sees(monkeypatch, (70, 198, 374, 403))                  # the model's box: the same picture, a little loose
    figures = _figures(pdf)
    assert len(figures) == 1
    box = figures[0].bbox                                           # and the block carries the PDF's exact box
    assert [round(v) for v in (box.x0, box.y0, box.x1, box.y1)] == list(PICTURE)
    assert convert(pdf, ConvertOptions(frontmatter=False, math=False, ocr=False)).count("](figure)") == 1


def test_without_the_layout_model_the_picture_is_still_there(tmp_path, monkeypatch):
    pdf = _page_with_a_picture(tmp_path / "one.pdf")
    _layout_sees(monkeypatch)
    assert len(_figures(pdf)) == 1


def test_a_figure_holding_two_pictures_is_left_as_it_was(tmp_path, monkeypatch):
    pdf = _page_with_a_picture(tmp_path / "two.pdf", second=(72, 520, 372, 720))
    _layout_sees(monkeypatch, (70, 198, 374, 722))                  # one region round both: neither picture alone is it
    assert len(_figures(pdf)) == 3                                  # a composite figure is a separate question
