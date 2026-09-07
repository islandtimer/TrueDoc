"""A ruled box of names in columns is rebuilt as a grid, numbers or not.

The rule-based finder returns a committee attendance list as a 3 by 3 box with every name in
one cell. The sparse-table rebuild used to demand that a rebuilt table be at least three-tenths
numbers (a bar against boxed prose); a grid of short cells in several columns over many rows is
a table on its own evidence (tables/b10f6b51, 4 checks in run 49).
"""
from truedoc.model import BBox, Block, BlockKind, Char, Line, Table, TableCell, Word
from truedoc.pipeline import _rebuild_sparse_ruled_tables

SIZE = 10.0


def _seg(text, x0, x1, y0):
    cw = (x1 - x0) / max(1, len(text))
    chars = [Char(text=c, bbox=BBox(x0 + i * cw, y0, x0 + (i + 1) * cw, y0 + SIZE), font="F", size=SIZE, origin_y=y0 + 0.8 * SIZE) for i, c in enumerate(text)]
    words = [Word(text=text, bbox=BBox(x0, y0, x1, y0 + SIZE), chars=chars)]
    return Line(words=words, bbox=BBox(x0, y0, x1, y0 + SIZE))


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


def _lines():
    lines = [_seg("Program Committee", 147, 242, 87), _seg("Student Rep Attendance", 377, 493, 87)]
    for i, (a, ta, b, tb, c) in enumerate(NAMES):
        y = 100 + 12.4 * i
        lines.append(_seg(a, 45, 45 + 5.2 * len(a), y))
        if ta:
            lines.append(_seg("√", 187, 192, y))
        lines.append(_seg(b, 205, 205 + 5.2 * len(b), y))
        if tb:
            lines.append(_seg("√", 347, 352, y))
        lines.append(_seg(c, 365, 365 + 5.2 * len(c), y))
    return lines


def _ruled_box():
    bbox = BBox(25, 85, 520, 235)
    cells = [
        TableCell(text="Program Committee Student Rep Attendance", row=0, col=0, is_header=True),
        TableCell(text="", row=0, col=1, is_header=True),
        TableCell(text=" ".join(a + " " + b for a, _, b, _, _ in NAMES), row=1, col=0),
        TableCell(text=" ".join(c for *_, c in NAMES), row=1, col=1),
        TableCell(text="", row=2, col=0),
        TableCell(text="", row=2, col=1),
    ]
    table = Table(n_rows=3, n_cols=2, cells=cells, bbox=bbox, provenance="pymupdf-lines")
    return Block(kind=BlockKind.TABLE, bbox=bbox, table=table, provenance="pymupdf-lines", confidence=0.8)


def test_box_of_names_is_rebuilt_from_its_lines():
    out = _rebuild_sparse_ruled_tables([_ruled_box()], _lines(), SIZE)
    assert len(out) == 1
    t = out[0].table
    assert out[0].provenance == "ruled-rebuilt"
    assert t.n_rows >= 10 and t.n_cols >= 5
    col_of = {c.text: c.col for c in t.cells if c.text}
    assert col_of["Bartholomew, Deb"] == col_of["Bourekas, Eric"] == col_of["Arnold, Mark"]
    assert col_of["Rose, Stephen"] == col_of["Khandelwal, Sorabh"]


def test_boxed_prose_is_not_rebuilt():
    # A framed paragraph: one segment a line, nothing to rebuild into columns.
    bbox = BBox(25, 85, 520, 235)
    lines = [_seg("The committee met to review the annual report and its findings on %d matters" % i, 45, 480, 100 + 12 * i) for i in range(8)]
    cells = [TableCell(text=" ".join(l.text for l in lines), row=0, col=0), TableCell(text="", row=0, col=1)]
    table = Table(n_rows=1, n_cols=2, cells=cells, bbox=bbox, provenance="pymupdf-lines")
    block = Block(kind=BlockKind.TABLE, bbox=bbox, table=table, provenance="pymupdf-lines", confidence=0.8)
    out = _rebuild_sparse_ruled_tables([block], lines, SIZE)
    assert out[0].provenance == "pymupdf-lines"
