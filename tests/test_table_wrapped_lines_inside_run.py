"""Two continuation lines of a wrapped cell do not break a table in two.

A references column wraps to three lines ("Huber et al., 2002; Hou et al., 2006;" / "Bhattacharya
et al., 2012;" / "Michalon et al., 2012"), so two lone lines follow the first body row; the run
finder took two lone rows in a row for the end of the table and started a second table under
them, leaving the first with its heading row and one body row (tables/0b100ba0 page 4, run 49).
A lone line that starts on a column of the row above and stays inside that column is the rest
of a cell; a caption or a note across the table starts at the table's edge and stays a break.
"""
from truedoc.model import BBox, Char, Line, Page, Word
from truedoc.tables.aligned import find_aligned_tables

SIZE = 9.0


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


ROWS = [
    (103, [("Category", 77, 109), ("Region", 170, 194), ("Phenotype", 235, 300), ("Age", 389, 402), ("References", 435, 472)]),
    (117, [("mGluR LTD", 75, 111), ("hippocampus", 160, 204), ("enhanced", 235, 267), ("P25-30", 385, 406), ("Huber et al., 2002; Hou et al., 2006;", 435, 539)]),
    (126, [("Bhattacharya et al., 2012;", 435, 508)]),
    (135, [("Michalon et al., 2012", 435, 497)]),
    (149, [("mGluR LTD", 75, 111), ("hippocampus", 160, 204), ("does not require", 235, 289), ("4-12 wk", 383, 408), ("Nosyreva and Huber, 2006", 435, 538)]),
    (172, [("mGluR LTD", 75, 111), ("hippocampus", 160, 204), ("enhanced and not PS-dependent", 235, 340), ("P35-42", 385, 406), ("Iliff et al., 2012", 435, 481)]),
    (186, [("LTP", 87, 98), ("hippocampus", 160, 204), ("NONE", 235, 254), ("20-26 wk", 366, 425), ("Godfraind et al., 1996", 435, 531)]),
]


def test_wrapped_reference_lines_keep_the_table_whole():
    lines = [_seg(t, x0, x1, y) for y, row in ROWS for t, x0, x1 in row]
    tables, _ = find_aligned_tables(_page(lines), lines, SIZE)
    assert len(tables) == 1
    t = tables[0].table
    texts = {(c.row, c.col): c.text for c in t.cells}
    assert texts[(0, 0)] == "Category"
    assert "Bhattacharya" in texts[(1, 4)] and "Michalon" in texts[(1, 4)]
    assert texts[(4, 0)] == "LTP"


def test_a_caption_under_the_table_still_ends_it():
    # The same table without the wrapped lines, its rows at one pitch, then a
    # caption and a note across the table's left edge.
    body = [ROWS[0][1], ROWS[1][1], ROWS[4][1], ROWS[5][1], ROWS[6][1]]
    lines = [_seg(t, x0, x1, 103 + 14 * i) for i, row in enumerate(body) for t, x0, x1 in row]
    lines.append(_seg("Table 2 Behavioural phenotypes of the same mice", 57, 300, 175))
    lines.append(_seg("Note: ages are in weeks unless stated", 57, 240, 186))
    tables, remaining = find_aligned_tables(_page(lines), lines, SIZE)
    assert len(tables) == 1
    assert all("Table 2" not in c.text and "Note:" not in c.text for c in tables[0].table.cells)
