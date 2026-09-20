"""A table cell that holds a table of its own is read as that table (D038).

CGU's Key Facts Sheet sets, in the third cell of "High value items and collections":

    Policy                    Item Limit     Overall Limit
    Accidental Damage Home    $2,500/item    20% of Contents SI or $7,500 (whichever is higher)
    Listed Events Home        $2,500/item    20% of Contents SI or $5,000 (whichever is higher)
    Fundamentals Home         $1,000/item    $2,000

and a field-trial report rules one cell around each treatment's product lines (name, rate, unit, timing). Written
flat, the cell keeps every word and loses which limit belongs to which policy. The owner's decision: a cell holds
what its box holds (D028), and a table inside a cell is written as a table, inside the cell (D038).

What marks such a cell is geometry, sized before this was written (`bench/probes/nested_table_census.py`): it holds
three lines or more, EVERY one of them broken at a gap no word space makes, and the pieces after the gap start at
the same place on most of them. Running text does not do that, and a list inside a cell - which breaks every line
after its mark - is D028's and is left to it. On 380 Key Facts Sheet pages, 25 insurance pages and 1,122 benchmark
pages that picks CGU's four cells and the field-trial table's eleven, and no other cell.

The inner table is built from the cell's own lines by the builder every text-built table goes through
(`aligned.table_from_lines`), so columns set flush right or centred are found as they are anywhere else. It is kept
only if it says exactly what the cell said: the same words in the same order (`TableCell.text` stays whole).

Its first row is a heading only on evidence. CGU sets "Policy | Item Limit | Overall Limit" in the face, size and
colour of the rows beneath, so type cannot say; what can is that a heading names and the rows beneath count: no cell
of the first row holds a digit, and in some column every row beneath does. "Accidental Damage Home | Australia &
New Zealand", over "Listed Events Home | Australia up to 90 consecutive days" and "Fundamentals Home | Not
Covered", is a row like the others and is written as one.
"""
from __future__ import annotations

import re

from truedoc.model import Block, BlockKind, Line, Table
from truedoc.tables.aligned import table_from_lines

_WIDE = 1.0           # of the line's height: a gap this wide is not a word space
_SAME_START = 2.5     # points
_LEAST_ROWS = 3
_LIST_MARK = re.compile(r"^(?:[^\w\s$(\[]|\(?[A-Za-z0-9]{1,2}[.)])$")      # a tick, a bullet, "a)", "1." alone at the head of a line


def _visual_rows(lines: list[Line]) -> list[list[Line]]:
    rows: list[list[Line]] = []
    for line in sorted(lines, key=lambda l: (l.bbox.cy, l.bbox.x0)):
        if rows and abs(line.bbox.cy - rows[-1][0].bbox.cy) <= 0.5 * max(line.bbox.height, 1.0):
            rows[-1].append(line)
        else:
            rows.append([line])
    return rows


def _pieces(row: list[Line]) -> list[tuple[float, str]]:
    """(x0, text) of each piece of a visual row: its first word, and every word a wide gap after the one before."""
    words = sorted((w for l in row for w in l.words if w.text.strip()), key=lambda w: w.bbox.x0)
    if not words:
        return []
    height = max(max(l.bbox.height for l in row), 1.0)
    pieces = [[words[0]]]
    for a, b in zip(words, words[1:]):
        if b.bbox.x0 - a.bbox.x1 >= _WIDE * height:
            pieces.append([b])
        else:
            pieces[-1].append(b)
    return [(p[0].bbox.x0, " ".join(w.text for w in p)) for p in pieces]


def _set_as_a_table(rows: list[list[Line]]) -> bool:
    """Every line broken at a wide gap, and the pieces after it starting at one place on most lines."""
    if len(rows) < _LEAST_ROWS:
        return False
    pieces = [_pieces(r) for r in rows]
    if any(len(p) < 2 for p in pieces) or any(_LIST_MARK.match(p[0][1]) for p in pieces):
        return False
    later = [[x for x, _text in p[1:]] for p in pieces]
    best = max(sum(1 for xs in later if any(abs(x - y) <= _SAME_START for y in xs)) for xs0 in later for x in xs0)
    return best >= max(2, len(rows) - 1)


def _plain(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _heading_by_what_it_says(grid: list[list[str]]) -> bool:
    first, beneath = grid[0], grid[1:]
    if not beneath or any(any(ch.isdigit() for ch in c) for c in first):
        return False
    return any(first[k] and all(any(ch.isdigit() for ch in r[k]) for r in beneath) for k in range(len(first)))


def read_inner_table(lines: list[Line], cell_text: str, size: float, box) -> Table | None:
    rows = _visual_rows(lines)
    if not _set_as_a_table(rows):
        return None
    inner = table_from_lines(lines, size, trusted=True, extent=box)
    if inner is None or inner.n_cols < 2 or inner.n_rows < 2 or inner.has_merged:
        return None
    grid = [[(c.text if c is not None else "") for c in r] for r in inner.grid()]
    if _plain(" ".join(c for r in grid for c in r if c)) != _plain(cell_text):
        return None                                       # it must say what the cell said, word for word, in order
    heading = _heading_by_what_it_says(grid)
    for c in inner.cells:
        c.is_header = heading and c.row == 0
    inner.provenance = "cell-table"
    return inner


def table_cells(page, blocks: list[Block]) -> None:
    """Each body cell whose box holds a table set as a table gets that table (`TableCell.inner`)."""
    size = page.body_font_size or 10.0
    lines = [l for l in page.lines if l.text.strip() and not l.rotated]
    for b in blocks:
        if b.kind != BlockKind.TABLE or b.table is None:
            continue
        for cell in b.table.cells:
            if cell.bbox is None or cell.is_header or cell.listing is not None or cell.inner is not None or not cell.text.strip():
                continue
            mine = [l for l in lines if cell.bbox.contains_point(l.bbox.cx, l.bbox.cy)]
            if len(mine) < _LEAST_ROWS:
                continue
            cell.inner = read_inner_table(mine, cell.text, size, cell.bbox)
