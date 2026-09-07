"""A ruled box whose first row is data adopts the heading row printed above it.

A capability list boxes its rows and sets "# | Attribute | Description" unruled above the box.
The heading adoption took headings from above a one-row box only, on the reasoning that a box
of several rows carries its own heading; this one does not (its first row is "driverTypeAddress
| Address of the Driver Type"), and the table lost its heading in run 51 (tables/cefac431).
A caption above a box is still not a heading: it starts with "Table", or is one sentence.
"""
from truedoc.model import BBox, Block, BlockKind, Char, Line, Table, TableCell, Word
from truedoc.pipeline import _adopt_ruled_headers

SIZE = 11.0


def _line(text, x0, x1, y0):
    cw = (x1 - x0) / max(1, len(text))
    chars = [Char(text=c, bbox=BBox(x0 + i * cw, y0, x0 + (i + 1) * cw, y0 + SIZE), font="F", size=SIZE, origin_y=y0 + 0.8 * SIZE) for i, c in enumerate(text)]
    words = []
    x = x0
    for tok in text.split(" "):
        w = cw * len(tok)
        words.append(Word(text=tok, bbox=BBox(x, y0, x + w, y0 + SIZE), chars=[c for c in chars if x <= c.bbox.x0 < x + w + 0.01]))
        x += w + cw
    return Line(words=words, bbox=BBox(x0, y0, x1, y0 + SIZE))


COLS = [(55, 78), (78, 200), (200, 360)]


def _box(rows, y0=52, pitch=24):
    cells = []
    for r, row in enumerate(rows):
        for c, text in enumerate(row):
            cells.append(TableCell(text=text, row=r, col=c, is_header=(r == 0), bbox=BBox(COLS[c][0], y0 + r * pitch, COLS[c][1], y0 + (r + 1) * pitch)))
    bbox = BBox(55, y0, 360, y0 + len(rows) * pitch)
    table = Table(n_rows=len(rows), n_cols=3, cells=cells, bbox=bbox, provenance="pymupdf-lines")
    return Block(kind=BlockKind.TABLE, bbox=bbox, table=table, provenance="pymupdf-lines", confidence=0.8)


def test_headerless_box_adopts_the_heading_row_above():
    box = _box([["", "driverTypeAddress", "Address of the Driver Type"], ["", "serial", "Serial number of the driver"], ["", "projectID", "Name of the Project / Tender"]])
    heading = [_line("#", 64, 70, 33), _line("Attribute", 83, 128, 33), _line("Description", 209, 269, 33)]
    tables, remaining = _adopt_ruled_headers([box], list(heading), SIZE)
    t = tables[0].table
    assert t.n_rows == 4
    top = {c.col: c.text for c in t.cells if c.row == 0}
    assert top == {0: "#", 1: "Attribute", 2: "Description"}
    assert all(c.is_header for c in t.cells if c.row == 0)
    assert not any(c.is_header for c in t.cells if c.row == 1)
    assert remaining == []


def test_a_box_with_its_own_heading_row_takes_no_caption():
    box = _box([["No.", "Attribute", "Description"], ["1", "serial", "Serial number of the driver"], ["2", "projectID", "Name of the Project / Tender"]])
    caption = [_line("Table 3. Attributes of the driver asset", 55, 300, 33)]
    tables, remaining = _adopt_ruled_headers([box], list(caption), SIZE)
    assert tables[0].table.n_rows == 3
    assert len(remaining) == 1
