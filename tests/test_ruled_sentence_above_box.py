"""A sentence above a ruled box is not its heading row, even when the box looks headerless.

A box whose first row reads as data - a cell of more than four words - takes its heading from the line
printed above it (`_adopt_ruled_headers`), provided that line's words fall into at least two of the
box's columns and line up with their edges. A Key Facts Sheet's own heading cell, "Some examples of
specific conditions, exclusions or limits...", runs to more than four words, so its box looked
headerless; and the sentence printed above it, "Under this policy you choose the maximum level of
cover...", passed the alignment check and became the table's first row.

What a sentence cannot fake is how it crosses from one column into the next: on a word space, where a
row of headings crosses on the gap between its cells. Here "Under" ends and "this" begins one word
space apart, on either side of the first column's edge - and the sentence still lines up with the
first two column edges, so without the word-space test it is adopted.
"""
from truedoc.model import BBox, Block, BlockKind, Char, Line, Table, TableCell, Word
from truedoc.pipeline import _adopt_ruled_headers

SIZE = 11.0
COLS = [(55, 78), (78, 200), (200, 360)]


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


def _box(rows, y0=52, pitch=24):
    cells = []
    for r, row in enumerate(rows):
        for c, text in enumerate(row):
            cells.append(TableCell(text=text, row=r, col=c, is_header=(r == 0), bbox=BBox(COLS[c][0], y0 + r * pitch, COLS[c][1], y0 + (r + 1) * pitch)))
    bbox = BBox(55, y0, 360, y0 + len(rows) * pitch)
    table = Table(n_rows=len(rows), n_cols=3, cells=cells, bbox=bbox, provenance="pymupdf-lines")
    return Block(kind=BlockKind.TABLE, bbox=bbox, table=table, provenance="pymupdf-lines", confidence=0.8)


def test_a_sentence_above_a_headerless_box_is_not_its_heading():
    box = _box([["", "driverTypeAddress", "Address of the Driver Type"],
                ["", "serial", "Serial number of the driver"],
                ["", "projectID", "Name of the Project / Tender"]])
    sentence = _line("Under this policy you choose the maximum level of cover", 55, 355, 33)
    tables, remaining = _adopt_ruled_headers([box], [sentence], SIZE)
    assert tables[0].table.n_rows == 3, [c.text for c in tables[0].table.cells if c.row == 0]
    assert remaining == [sentence]
