"""Prose set inside a drawn box stays with its box (D042).

A note boxed beside a paragraph was threaded into it: the paragraph's block, wide from the full-measure lines above,
took each of the note's lines as it came, so the note's words stood between the paragraph's. A line inside a box of
prose now joins only a block inside the same box, and a line outside joins none inside - nor does a short lowercase
piece of the note, on a line of the paragraph, pass for the rest of that line. A figure's frame round its labels is no
box of prose, and nor is a box round all the page's text.
"""
import pymupdf
import pytest

from truedoc.extract.handle import open_pdf
from truedoc.extract.textlayer import extract_page
from truedoc.model import BBox, Drawing, Line, Page, Word
from truedoc.segment.blocks import _box_of, _boxed_prose, build_blocks

FULL = [(40, 100, "This section explains our claims process and how we pay claims under"),
        (40, 112, "this policy, and where to find the guide that explains more of it.")]
LEFT = [(40, 124, "Occasionally, circumstances beyond the control"), (40, 136, "of our customers can prevent strict compliance"),
        (40, 148, "with policy terms. If this happens to you then"), (40, 160, "you should speak to us about your situation.")]
NOTE = [(276, 130, "If relevant, please see"), (276, 142, "our hardship and family"), (276, 154, "violence policies that")]
BOX = (270, 119, 392, 172)


def _page(tmp_path, text, box=BOX):
    doc = pymupdf.open()
    page = doc.new_page(width=420, height=300)
    for x, y, words in text:
        page.insert_text((x, y), words, fontsize=10)
    page.draw_rect(pymupdf.Rect(*box), width=0.75)
    path = tmp_path / f"note{len(list(tmp_path.glob('note*.pdf')))}.pdf"
    doc.save(str(path))
    doc.close()
    handle = open_pdf(str(path))
    try:
        return extract_page(handle[0], 1)
    finally:
        handle.close()


def test_a_note_in_a_box_stays_one_block_and_joins_nothing_beside_it(tmp_path):
    page = _page(tmp_path, FULL + LEFT + NOTE)
    note = {t for _x, _y, t in NOTE}
    blocks = [{l.text for l in b.lines} for b in build_blocks(page)]
    holding = [b for b in blocks if b & note]
    assert holding == [note]


def test_a_short_piece_of_the_note_is_not_the_rest_of_a_line_beside_it(tmp_path):
    # on the paragraph's last baseline, lowercase, three words, set in from the note's other lines; the paragraph's line
    # stops short of the note without a stop
    left = LEFT[:3] + [(40, 160, "you should speak to us about your situation and the")]
    note = NOTE[:2] + [(282, 160, "on our website")]
    page = _page(tmp_path, FULL + left + note)
    lines = {l.text for b in build_blocks(page) for l in b.lines}
    assert "on our website" in lines                        # a line of its own, not glued onto "... and the"
    holding = [b for b in build_blocks(page) if any(l.text == "on our website" for l in b.lines)]
    assert {l.text for l in holding[0].lines} == {t for _x, _y, t in note}


def _line(x0, y0, x1, y1, text="words"):
    box = BBox(x0, y0, x1, y1)
    return Line(words=[Word(text=w, bbox=box) for w in text.split()], bbox=box)


def test_a_frame_round_short_labels_or_round_everything_is_no_box_of_prose():
    frame = Drawing(kind="rect", bbox=BBox(100, 100, 300, 250))
    labels = [_line(105, 110, 115, 118, "10"), _line(105, 170, 115, 178, "5"), _line(105, 230, 115, 238, "0")]
    body = [_line(40, 300, 380, 310, "a line of the body below the figure")]
    page = Page(number=1, width=420, height=400, drawings=[frame])
    assert _boxed_prose(page, labels + body) == []
    prose = [_line(105, 110, 250, 118, "a line of prose in it"), _line(105, 122, 260, 130, "and another line of it")]
    assert _boxed_prose(page, prose + body) == [frame.bbox]
    assert _boxed_prose(page, prose) == []                 # it holds every line on the page
    labels = [_line(105, 110, 250, 118, "Customer objectives,"), _line(105, 122, 260, 130, "financial situation and")]
    assert _boxed_prose(page, labels + body) == []         # a table's label cell: a word or three a line
    narrow = [_line(105, 110, 150, 118, "10 20 30 40"), _line(105, 122, 150, 130, "50 60 70 80")]
    assert _boxed_prose(page, narrow + body) == []         # short lines in a wide frame: a chart's scale


def test_a_shape_a_line_runs_across_is_no_box():
    room = Drawing(kind="rect", bbox=BBox(25, 275, 97, 332), fill=True)          # a shaded room of a floor plan
    note = [_line(27, 273, 90, 285, "A passageway or the stair"), _line(27, 285, 102, 297, "hallway has the same meaning"),
            _line(27, 297, 97, 309, "meaning as a room is")]
    body = [_line(40, 500, 380, 510, "a line of the body below the plan")]
    assert _boxed_prose(Page(number=1, width=420, height=600, drawings=[room]), note + body) == []


def test_a_line_belongs_to_the_smallest_box_it_lies_in():
    outer, inner = BBox(50, 50, 400, 400), BBox(100, 100, 300, 200)
    boxes = sorted([outer, inner], key=lambda b: b.area)
    assert boxes[_box_of(_line(110, 110, 290, 120), boxes)] == inner
    assert boxes[_box_of(_line(60, 300, 390, 310), boxes)] == outer
    assert _box_of(_line(0, 0, 20, 10), boxes) is None
    page = Page(number=1, width=420, height=500, drawings=[Drawing(kind="rect", bbox=outer), Drawing(kind="rect", bbox=inner)])
    prose = [_line(110, 110, 290, 120, "a line of the inner note"), _line(110, 125, 290, 135, "and its second line"),
             _line(60, 300, 390, 310, "a line of the outer note"), _line(60, 315, 390, 325, "and its second line"),
             _line(10, 450, 400, 460, "the body, outside both")]
    assert _boxed_prose(page, prose) == [inner, outer]     # smallest first, so a line is the inner box's


def test_a_box_no_reader_sees_divides_nothing(tmp_path):
    frame = Drawing(kind="rect", bbox=BBox(100, 100, 300, 250), fill=True, unseen=True)
    prose = [_line(105, 110, 250, 118, "a line of prose in it"), _line(105, 122, 260, 130, "and another line of it")]
    body = [_line(40, 300, 380, 310, "a line of the body below")]
    assert _boxed_prose(Page(number=1, width=420, height=400, drawings=[frame]), prose + body) == []


@pytest.mark.parametrize("reader", ["pdfium", "mupdf"])
def test_a_white_shape_with_no_outline_is_drawn_unseen(tmp_path, monkeypatch, reader):
    monkeypatch.setenv("TRUEDOC_OBJECTS", reader)
    doc = pymupdf.open()
    page = doc.new_page(width=420, height=300)
    page.draw_rect(pymupdf.Rect(20, 20, 200, 120), color=None, fill=(1, 1, 1))        # a text frame left behind
    page.draw_rect(pymupdf.Rect(220, 20, 400, 120), color=(0, 0, 0), width=0.75)      # a box
    page.draw_rect(pymupdf.Rect(20, 150, 200, 250), color=None, fill=(0.3, 0.5, 0.8))  # a coloured panel
    page.draw_rect(pymupdf.Rect(220, 150, 400, 250), color=None, fill=(0.3, 0.5, 0.8), fill_opacity=0)   # and a clear one
    path = tmp_path / f"frames_{reader}.pdf"
    doc.save(str(path))
    doc.close()
    handle = open_pdf(str(path))
    try:
        drawn = extract_page(handle[0], 1).drawings
    finally:
        handle.close()
    unseen = {(round(d.bbox.x0 / 10), round(d.bbox.y0 / 10)): d.unseen for d in drawn if d.kind == "rect"}   # a stroke widens its box
    assert unseen == {(2, 2): True, (22, 2): False, (2, 15): False, (22, 15): True}


def test_a_line_of_large_type_is_in_the_box_its_middle_is_in():
    panel = BBox(30, 66, 250, 148)
    title = [_line(34, 61, 240, 90, "A NOTE SET IN LARGE"), _line(34, 90, 240, 118, "TYPE ON A DARK PANEL"),
             _line(34, 118, 245, 146, "OF ITS OWN, FOUR WORDS")]
    body = [_line(30, 300, 380, 310, "the body of the page below the title")]
    page = Page(number=1, width=420, height=400, drawings=[Drawing(kind="rect", bbox=panel, fill=True)])
    assert _boxed_prose(page, title + body) == [panel]
    assert {_box_of(l, [panel]) for l in title} == {0}           # the first line's box stands 5pt above the panel
