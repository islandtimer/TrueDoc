"""Pages lying on their side are turned upright before they are read.

Two cases: a text layer whose lines run up or down the page (a scan with a
hidden OCR layer, or a wide table printed sideways), and an image-only scan
that the OCR engine reads sideways. Both end with the page's in-memory
rotation changed and the text read in order, top to bottom.
"""

import pymupdf

from truedoc.pipeline import ConvertOptions, _sideways_text_turn, process_page

LINES = [
    "The committee met on the third of May.",
    "Minutes of the previous meeting were read.",
    "The treasurer reported a balance of 412 dollars.",
    "Membership rose by twelve during the quarter.",
    "The next meeting is on the seventh of June.",
]

_OPTS = ConvertOptions(layout=False, tables=False, math=False, marks=False)


def _texts(page):
    return [l.text for l in sorted(page.lines, key=lambda l: l.bbox.y0)]


def _sideways_text_page(text_runs_up: bool):
    """A landscape page whose lines are written running up or down the page.

    Running up means the document's top is on the left (its first line is the
    leftmost); running down means the top is on the right.
    """
    doc = pymupdf.open()
    page = doc.new_page(width=600, height=400)
    for i, t in enumerate(LINES):
        if text_runs_up:
            page.insert_text((60 + 24 * i, 360), t, fontsize=12, rotate=90)
        else:
            page.insert_text((540 - 24 * i, 40), t, fontsize=12, rotate=270)
    return page


def test_text_layer_running_up_is_turned_clockwise():
    pdf_page = _sideways_text_page(text_runs_up=True)
    page = process_page(pdf_page, 1, ConvertOptions(layout=False, tables=False, math=False, marks=False, ocr=False))
    assert page.meta.get("turned") == 90 and pdf_page.rotation == 90
    assert page.lines and not any(l.rotated for l in page.lines)
    assert _texts(page) == LINES


def test_text_layer_running_down_is_turned_anticlockwise():
    pdf_page = _sideways_text_page(text_runs_up=False)
    page = process_page(pdf_page, 1, ConvertOptions(layout=False, tables=False, math=False, marks=False, ocr=False))
    assert page.meta.get("turned") == 270 and pdf_page.rotation == 270
    assert _texts(page) == LINES


def test_a_rotated_stamp_does_not_turn_the_page():
    doc = pymupdf.open()
    page = doc.new_page(width=400, height=600)
    for i, t in enumerate(LINES):
        page.insert_text((40, 60 + 24 * i), t, fontsize=12)
    page.insert_text((380, 500), "Downloaded from the archive", fontsize=8, rotate=90)
    out = process_page(page, 1, ConvertOptions(layout=False, tables=False, math=False, marks=False, ocr=False))
    assert "turned" not in out.meta and page.rotation == 0
    assert _sideways_text_turn(out) == 0


def _scan_of(src_page, rotate: int):
    """An image-only page holding a picture of `src_page` turned by `rotate` degrees."""
    pix = src_page.get_pixmap(matrix=pymupdf.Matrix(2, 2))
    doc = pymupdf.open()
    page = doc.new_page(width=600, height=400)
    page.insert_image(page.rect, pixmap=pix, rotate=rotate)
    return page


def test_sideways_scan_is_turned_and_read_in_order():
    src = pymupdf.open()
    portrait = src.new_page(width=400, height=600)
    for i, t in enumerate(LINES):
        portrait.insert_text((40, 60 + 24 * i), t, fontsize=12)
    for rotate in (90, 270):
        pdf_page = _scan_of(portrait, rotate)
        assert pdf_page.get_text().strip() == ""
        page = process_page(pdf_page, 1, _OPTS)
        assert page.meta.get("turned") in (90, 270), page.meta
        assert page.lines and not any(l.rotated for l in page.lines)
        texts = _texts(page)
        assert "committee" in texts[0].lower(), texts
        assert "june" in texts[-1].lower(), texts
