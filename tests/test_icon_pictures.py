"""A picture a mark's size that stands in a table, or heads a line of text, is an icon and not a figure.

A tick, a cross or a dollar in a circle opening every item, the ticks down a table's columns: the layout model calls
each one a picture, and each was written as an empty placeholder on a line of its own - stacked above a table whose
cells already held the ticks, or between an item's lead and the list under it. D013 is the rule they now meet: a mark
the reader can read is its character where it stands, a mark in a cell it cannot read is the cell's "[icon]", and an
unreadable shape beside running text is decoration. A picture of that size standing on its own stays a figure, as does
a bigger one, one that is a single mark (drawn between two statements, it stands for "then") and one a model
transcribed.
"""
from truedoc.model import BBox, Block, BlockKind, Line, Page, Word
from truedoc.pipeline import _icons_are_not_pictures


def _page():
    return Page(number=1, width=595.0, height=842.0, body_font_size=10.0)


def _text(x0, y0, x1, y1, text="an item of the list, running on to the end of its line"):
    box = BBox(x0, y0, x1, y1)
    return Block(kind=BlockKind.TEXT, bbox=box, lines=[Line(words=[Word(text=w, bbox=box) for w in text.split()], bbox=box)])


def _picture(x0, y0, x1, y1):
    return Block(kind=BlockKind.FIGURE, bbox=BBox(x0, y0, x1, y1), provenance="layout-figure")


def test_an_icon_at_the_head_of_a_line_is_not_a_picture():
    page, icon, item = _page(), _picture(40, 100, 54, 114), _text(66, 101, 400, 113)
    blocks = [icon, item]
    _icons_are_not_pictures(page, blocks)
    assert blocks == [item]
    [call] = page.meta["decisions"]
    assert call["kind"] == "icon" and "head of a line" in call["because"] and call["text"] == ""


def test_an_icon_in_a_table_is_not_a_picture_and_says_what_the_reader_made_of_it():
    page = _page()
    table = Block(kind=BlockKind.TABLE, bbox=BBox(40, 200, 555, 400))
    ticks = [_picture(400, 220 + 30 * i, 414, 234 + 30 * i) for i in range(5)]
    page.meta["marks"] = [{"kind": "tick", "colour": "green", "score": 0.9, "bbox": [401, 221, 413, 233], "placed": True}]
    blocks = [table] + ticks
    _icons_are_not_pictures(page, blocks)
    assert blocks == [table]
    assert len(page.meta["decisions"]) == 5
    assert "(read as a tick)" in page.meta["decisions"][0]["because"] and page.meta["decisions"][0]["checked"] is True
    assert page.meta["decisions"][1]["checked"] is False


def test_a_small_picture_standing_on_its_own_stays_a_figure():
    page, alone, text = _page(), _picture(280, 100, 300, 120), _text(40, 300, 555, 312)
    blocks = [alone, text]
    _icons_are_not_pictures(page, blocks)
    assert blocks == [alone, text] and not page.meta.get("decisions")


def test_a_bigger_picture_beside_a_line_stays_a_figure():
    page, picture, text = _page(), _picture(40, 100, 140, 180), _text(150, 120, 555, 132)
    blocks = [picture, text]
    _icons_are_not_pictures(page, blocks)
    assert blocks == [picture, text]


def test_a_picture_that_is_one_mark_or_was_transcribed_stays():
    page = _page()
    arrow = _picture(40, 100, 54, 114)
    arrow.meta["mark_only"] = "↓"
    read = _picture(40, 140, 54, 154)
    read.text_override = "a word a model read in it"
    blocks = [arrow, read, _text(66, 101, 400, 113), _text(66, 141, 400, 153)]
    _icons_are_not_pictures(page, blocks)
    assert arrow in blocks and read in blocks
