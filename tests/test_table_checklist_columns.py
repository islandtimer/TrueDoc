"""A checklist of names with sparse tick columns is a table, not prose sliced at word gaps.

A committee attendance list sets three columns of names with a tick beside those present
("Arnold, Mark | √ | Khandelwal, Sorabh | | Bashaw, Hillary"). The ticks are sparse, so the
grid has more columns than a typical row has segments, which is the signature of justified
prose cut at wide word gaps; but every name starts on one of the same three left edges down
the whole list, which prose never does (tables/b10f6b51, 4 checks in run 48).
"""
from truedoc.model import BBox, Char, Line, Page, Word
from truedoc.tables.aligned import find_aligned_tables

SIZE = 10.0


def _seg(text, x0, x1, y0):
    cw = (x1 - x0) / max(1, len(text))
    chars = [Char(text=c, bbox=BBox(x0 + i * cw, y0, x0 + (i + 1) * cw, y0 + SIZE), font="F", size=SIZE, origin_y=y0 + 0.8 * SIZE) for i, c in enumerate(text)]
    words = [Word(text=text, bbox=BBox(x0, y0, x1, y0 + SIZE), chars=chars)]
    return Line(words=words, bbox=BBox(x0, y0, x1, y0 + SIZE))


def _page(lines):
    page = Page(number=1, width=792, height=612)
    page.lines = lines
    page.body_font_size = SIZE
    return page


NAMES = [
    ("Arnold, Mark", True, "Khandelwal, Sorabh", False, "Bashaw, Hillary"),
    ("Barin, Kamrin", True, "Kman, Nicholas", False, "Fu, Julia"),
    ("Bartholomew, Deb", True, "Ledford, Cindy", True, "Gerstman, Jacob"),
    ("Bourekas, Eric", False, "Letson, Alan", False, "Ho, Vincent"),
    ("Bowyer, Brian", False, "Liston, Beth", False, "House, Melissa"),
    ("Clinchot, Dan", False, "Lynn, Joanne", False, "Rose, Maggie"),
    ("Cohen, Dan", True, "McIlroy, Mary", False, "Sauers, Lynn"),
    ("Cronau, Holly", False, "Muscarella, Pete", False, "Schroeder, Catherine"),
    ("Ecklar, Pat", True, "Nagaraja, Haikady", False, "Scharschmidt, Thomas"),
    ("Hasbrouck, Carol", True, "Rose, Stephen", True, "Way, David"),
]


def test_sparse_tick_columns_keep_the_checklist_a_table():
    lines = [_seg("Program Committee", 147, 242, 87), _seg("Student Rep Attendance", 377, 493, 87)]
    # The minutes' own column runs down the right of the list on a few rows.
    side = {2: "Presiding Chair: Mary McIlroy, MD", 4: "Recording Secretary: Sean Bragg", 6: "Call To Order: 4:07 pm"}
    lead = {4, 6, 7}   # a tick in the margin before the first name on a few rows
    for i, (a, ta, b, tb, c) in enumerate(NAMES):
        y = 100 + 12.4 * i
        if i in lead:
            lines.append(_seg("√", 27, 32, y))
        lines.append(_seg(a, 45, 45 + 5.2 * len(a), y))
        if ta:
            lines.append(_seg("√", 187, 192, y))
        lines.append(_seg(b, 205, 205 + 5.2 * len(b), y))
        if tb:
            lines.append(_seg("√", 347, 352, y))
        lines.append(_seg(c, 365, 365 + 5.2 * len(c), y))
        if i in side:
            lines.append(_seg(side[i], 525, 525 + 4.9 * len(side[i]), y))
    tables, _ = find_aligned_tables(_page(lines), lines, SIZE)
    assert len(tables) == 1
    t = tables[0].table
    texts = {(c.row, c.col): c.text for c in t.cells}
    by_row = {}
    for (r, c), text in texts.items():
        by_row.setdefault(r, []).append(text)
    # Every name is a cell of its own, and Bartholomew sits above Bourekas.
    col_of = {text: c for (r, c), text in texts.items() if text}
    assert col_of["Bartholomew, Deb"] == col_of["Bourekas, Eric"] == col_of["Arnold, Mark"]
    assert col_of["Rose, Stephen"] == col_of["Khandelwal, Sorabh"]
    assert t.n_rows >= 11 and t.n_cols >= 5


def test_justified_prose_at_word_gaps_is_still_prose():
    # Three lines of prose whose wide word gaps split them into irregular pieces.
    rows = [
        [("The committee met", 40, 130), ("to review the", 150, 215), ("annual report and", 240, 330), ("its findings", 350, 410)],
        [("on the programme.", 40, 128), ("Several members", 145, 222), ("asked for more", 250, 322), ("time to read", 340, 400)],
        [("the appendices", 40, 112), ("before voting on", 130, 212), ("the recommendations", 235, 335), ("of the chair.", 355, 420)],
        [("Discussion then", 40, 118), ("turned to the", 140, 205), ("budget for the", 225, 300), ("coming year.", 320, 385)],
    ]
    lines = []
    for i, row in enumerate(rows):
        for text, x0, x1 in row:
            lines.append(_seg(text, x0, x1, 100 + 12 * i))
    tables, _ = find_aligned_tables(_page(lines), lines, SIZE)
    assert tables == []
