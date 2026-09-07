"""A scanned page of measurements is kept from the page floor up; leader dots leave cells."""

import truedoc.ocr.rapid as rapid
from truedoc.model import BBox, Page
from truedoc.tables.cells import clean_cell_text


def _lines(texts, size=10.0):
    out = []
    for i, text in enumerate(texts):
        y = 100 + 14 * i
        box = BBox(72, y, 72 + 5.0 * len(text), y + size)
        out.append(rapid.Line(words=rapid._split_words(text, box, 0.8), bbox=box))
    return out


def _page():
    page = Page(number=1, width=612, height=792)
    page.quality.kind = "none"
    return page


def _run(monkeypatch, texts, conf):
    monkeypatch.setattr(rapid, "ocr_page_turn", lambda pdf_page, want_turn=True: (_lines(texts), conf, 0))
    page = _page()
    ok = rapid.apply_ocr(page, None)
    return ok, page


NUMBERS = ["4.41 3.4 1.9 0.061 0.007 5.3", "0.92 11 0.054 0.048 0.017", "4.71 4.6 2.2 0.71 0.009 7.4"] * 8
LABELS = ["Los Angeles City", "Orange County", "Chlorinated hydrocarbon concentrations"]


def test_numeric_page_above_the_floor_is_kept(monkeypatch):
    # 0.785 was the wastewater table's read: under the 0.8 rescue bar, over the 0.75 floor.
    ok, page = _run(monkeypatch, NUMBERS + LABELS, 0.785)
    assert ok and page.quality.kind == "ocr-truedoc"
    assert page.meta["ocr_numeric_share"] >= 0.5 and "ocr_rejected" not in page.meta


def test_numeric_page_under_the_floor_stays_empty(monkeypatch):
    ok, page = _run(monkeypatch, NUMBERS + LABELS, 0.69)
    assert not ok and page.meta.get("ocr_rejected") and not page.lines


def test_a_few_numbers_are_not_a_table_page(monkeypatch):
    ok, page = _run(monkeypatch, NUMBERS[:4], 0.785)
    assert not ok and not page.lines


def test_a_page_of_unknown_words_is_still_rejected(monkeypatch):
    ok, page = _run(monkeypatch, ["=&5FT& ,nnO*##L. &.bH"] * 24, 0.785)
    assert not ok and not page.lines


def test_leader_dots_and_rules_leave_cells():
    assert clean_cell_text("Hettinger .........") == "Hettinger"
    assert clean_cell_text("(1) Bowbells..........") == "(1) Bowbells"
    assert clean_cell_text("Rugby . . . . . 12") == "Rugby . . . . . 12"   # leaders inside a cell are left alone
    assert clean_cell_text("---------------- Percent") == "Percent"
    assert clean_cell_text("---------- 2.98E-002 - - - - - - - - - -") == "2.98E-002"
    # An ellipsis, a form blank, a hyphenated word end and a bare rule stay.
    assert clean_cell_text("Ch = ...") == "Ch = ..."
    assert clean_cell_text("Name: ______") == "Name: ______"
    assert clean_cell_text("Diver-") == "Diver-"
    assert clean_cell_text("-----") == "-----"
    assert clean_cell_text("") == ""
