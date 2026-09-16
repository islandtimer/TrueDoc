"""A drawn mark that nothing takes is kept in the front matter rather than lost.

`_attach_marks` places a mark in three ways: a table cell holds it, it leads a line, or it is the whole content of a
picture. AAMI's home building PDS chains its settlement statements with a chevron in a grey disc, and on printed page
75 those chevrons fall inside the region the layout model calls a table, so none of the three applies and all five
are dropped. Publishing such a mark by its geometry was measured over 59 documents of the library and refused - the
ten arrows it would publish are a benefit table's marks, a list of tradespeople and a section numeral - so the mark
is not published. It is recorded instead, with its page and the box it was drawn in, as D029 keeps a line at a
page's edge that nothing places. The body does not move.
"""

import pymupdf

from truedoc.pipeline import ConvertOptions, convert, load_document

OFF = ConvertOptions(layout=False, ocr=False, math=False, tables=False)
BODYLESS = ConvertOptions(layout=False, ocr=False, math=False, tables=False, frontmatter=False)


def _tick(page, x, y, s=8, color=(0.2, 0.7, 0.2)):
    # A check mark: short stroke down-right, long stroke up-right (as tests/test_marks.py draws one).
    page.draw_polyline([(x, y + 0.5 * s), (x + 0.35 * s, y + 0.9 * s), (x + s, y)], color=color, width=1.6)


def _pdf(tmp_path, draw, name="marks.pdf"):
    doc = pymupdf.open()
    page = doc.new_page(width=400, height=300)
    page.insert_text((40, 60), "We cover loss or damage to your home caused by an insured event.", fontsize=10)
    page.insert_text((40, 240), "The most we will pay is the sum insured on your certificate.", fontsize=10)
    draw(page)
    path = tmp_path / name
    doc.save(str(path))
    doc.close()
    return str(path)


def _kept(path):
    return load_document(path, OFF).metadata.get("marks_not_placed") or []


def test_a_mark_nothing_takes_is_kept_with_its_page(tmp_path):
    # Alone between two paragraphs, on no line's baseline and in no cell or picture: nothing places it.
    path = _pdf(tmp_path, lambda p: _tick(p, 190, 150))
    kept = _kept(path)
    assert [(m["kind"], m["page"]) for m in kept] == [("tick", 1)], kept


def test_a_mark_that_leads_a_line_is_not_kept_there(tmp_path):
    # It reaches the text instead, which is where it belongs.
    path = _pdf(tmp_path, lambda p: _tick(p, 26, 54))
    body = convert(path, BODYLESS)
    assert "✓" in body, body[:200]
    assert not _kept(path), _kept(path)


def test_the_mark_nothing_takes_stays_out_of_the_body(tmp_path):
    # Keeping it in the front matter is not publishing it: a rule that published such marks was measured and refused.
    path = _pdf(tmp_path, lambda p: _tick(p, 190, 150))
    assert "✓" not in convert(path, BODYLESS), convert(path, BODYLESS)[:200]


def test_a_page_with_no_marks_records_none(tmp_path):
    path = _pdf(tmp_path, lambda p: None)
    assert _kept(path) == []
