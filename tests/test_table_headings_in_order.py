"""Headings set a shade left of their narrow columns are read in order.

The geometry is a scanned applicant table: eight short headings ("BM BF WM
WF OM OF ?? Total") over eight columns of counts, each heading about a third
of a column to the left of its numbers. By position "BM" and "BF" both land
on the first count column and the seventh column gets no heading at all.
"""

from truedoc.model import BBox, Char, Line, Page, Word
from truedoc.tables.aligned import find_aligned_tables

SIZE = 12.0


def _seg(text, x0, x1, y0):
    cw = (x1 - x0) / max(1, len(text))
    chars = [Char(text=c, bbox=BBox(x0 + i * cw, y0, x0 + (i + 1) * cw, y0 + SIZE), font="F", size=SIZE, origin_y=y0 + 0.8 * SIZE) for i, c in enumerate(text)]
    words = [Word(text=text, bbox=BBox(x0, y0, x1, y0 + SIZE), chars=chars)]
    return Line(words=words, bbox=BBox(x0, y0, x1, y0 + SIZE))


def _page(lines):
    page = Page(number=1, width=612, height=792)
    page.lines = lines
    page.body_font_size = SIZE
    return page


def test_offset_headings_are_read_in_order():
    lines = []
    for text, x0, x1 in [("BM", 149, 164), ("BF", 194, 207), ("WM", 239, 257), ("WF", 288, 304),
                         ("OM", 336, 353), ("OF", 384, 398), ("??", 432, 444), ("Total", 480, 503)]:
        lines.append(_seg(text, x0, x1, 463))
    rows = [
        (476, [("Year One", 77, 119), ("4", 178, 184), ("4", 223, 229), ("7", 272, 278), ("6", 320, 326), ("1", 368, 374), ("0", 416, 422), ("3", 464, 470), ("25", 507, 518)]),
        (490, [("Year Two", 77, 119), ("10", 173, 184), ("4", 223, 229), ("9", 272, 278), ("2", 320, 326), ("4", 368, 374), ("4", 416, 422), ("11", 459, 470), ("44", 507, 518)]),
        (504, [("Year Three", 77, 127), ("15", 173, 184), ("7", 223, 229), ("16", 267, 278), ("8", 320, 326), ("2", 368, 374), ("1", 416, 422), ("7", 464, 470), ("56", 507, 518)]),
        (518, [("Year Four", 77, 122), ("12", 173, 184), ("6", 223, 229), ("11", 267, 278), ("9", 320, 326), ("3", 368, 374), ("2", 416, 422), ("5", 464, 470), ("48", 507, 518)]),
        (532, [("Year Five", 77, 121), ("9", 178, 184), ("8", 223, 229), ("10", 267, 278), ("7", 320, 326), ("1", 368, 374), ("0", 416, 422), ("4", 464, 470), ("39", 507, 518)]),
    ]
    # Six rows: the channel finder then lets one row (the headings) sit in a channel.
    for y, cells in rows:
        for text, x0, x1 in cells:
            lines.append(_seg(text, x0, x1, y))
    tables, _ = find_aligned_tables(_page(lines), lines, SIZE)
    assert len(tables) == 1
    t = tables[0].table
    assert t.n_cols == 9
    assert [c.text for c in t.cells if c.row == 0] == ["", "BM", "BF", "WM", "WF", "OM", "OF", "??", "Total"]
    assert [c.text for c in t.cells if c.row == 1] == ["Year One", "4", "4", "7", "6", "1", "0", "3", "25"]


def test_lines_of_a_table_nested_in_a_column_are_not_a_row_of_short_headings():
    # CGU's Key Facts Sheet, read against its page on 19 September 2026: the third column of "High
    # value items and collections" holds a table of its own, and its second line - [0, 2, 2] by
    # position - was read in order, which wrote "Accidental Damage Home" into the Yes/No column.
    from truedoc.tables.aligned import _Row, _headings_in_order

    def row(*texts):
        return _Row(segments=[_seg(t, 50 + 150 * i, 50 + 150 * i + 5 * len(t), 100) for i, t in enumerate(texts)], y0=100, y1=112)

    nested = row("and collections", "Accidental Damage Home", "$2,500/item 20% of Contents SI or $7,500 (whichever is higher)")
    assert not _headings_in_order(nested, [0, 2, 2])
    assert _headings_in_order(row("First Term's", "Students", "Graduation"), [0, 0, 2])    # short headings still are
