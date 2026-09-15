"""A table the text built across boxes its page strokes keeps what one box holds as one run of text in one cell.

Budget Direct's home PDS sets its optional covers as cards: each cover's name in a green box, on one line or two
("Unspecified" over "Personal Effects", "Motor" over "Burnout"), and a link to its page under the box. The aligned finder
read each row of cards as a table and gave each line of a name a row of its own, so "Unspecified Personal Effects" was
nowhere in the markdown: a reader met "Unspecified | Specified" over "Personal Effects | Personal Effects". The break
is not forced by the width - "Unspecified Personal" is 100pt and the box 148pt - so the lines themselves say nothing
about belonging together. The box does.

`join_boxed_rows` folds the rows of a text-built table that one drawn box holds together: a rectangle whose four sides
the page draws, holding whole cells of one column across consecutive rows and no other text, where every other column
holds text in at most one of those rows or has a box of its own over the same rows. It acts on a single run of text
only - no line opening a list item (a tick, cross, bullet, dash or number), no sentence closed before the last line, one
size of type, the lines a line apart and no rule drawn across them in between - so a ticked list in one box, or a
paragraph with a "Go to page" line under it, is left as the table has it. And the box must divide the table's rows: a
frame round the whole table, or a box round each whole column, holds every row and says nothing about which belong
together.
"""
from __future__ import annotations

from typing import NamedTuple

from truedoc.classify.blocks import _LIST_START
from truedoc.extract import pdfium_objects
from truedoc.model import BBox, Block, BlockKind, Table, TableCell
from truedoc.tables.aligned import _BULLET_START, _join_lines

TEXT_BUILT = ("textlayer-aligned", "layout-table")   # tables built from text lines rather than from a drawing
CORNER = 6.0        # two sides of a box meet when their ends lie within this of each other (a rounded corner's gap)
MIN_SIDE = 8.0      # a box shorter or narrower than this holds no line of text
REACH = 36.0        # words further than this from a table belong to none of its cells
SLACK = 1.0         # a word whose centre lies within this of a box or cell is inside it
SAME_SIZE = 0.5     # the lines of one run of text differ in size by no more than this
LEADING = 0.8       # ... and lie no further apart than this share of their size
ACROSS = 0.5        # a rule divides two lines when it runs under at least this share of the narrower one


class _Held(NamedTuple):
    """The words of one text line that a box holds."""
    y0: float
    y1: float
    size: float
    text: str
    x0: float
    x1: float

    @property
    def cy(self) -> float:
        return (self.y0 + self.y1) / 2.0


def closed_boxes(edges: list[dict]) -> list[tuple]:
    """(x0, y0, x1, y1) of every rectangle whose four sides are drawn, as rule edges (`ruled_pdfium`)."""
    by_ends: dict[tuple, list[dict]] = {}
    by_x: dict[int, list[dict]] = {}
    for e in edges:
        if e["orientation"] == "h":
            by_ends.setdefault((int(e["x0"] // CORNER), int(e["x1"] // CORNER)), []).append(e)
        else:
            by_x.setdefault(int(e["x0"] // CORNER), []).append(e)

    def side(x: float, y0: float, y1: float) -> bool:
        k = int(x // CORNER)
        return any(abs(v["x0"] - x) <= CORNER and v["top"] <= y0 + CORNER and v["bottom"] >= y1 - CORNER
                   for j in (k - 1, k, k + 1) for v in by_x.get(j, ()))

    found = set()
    for group in by_ends.values():
        for top in group:
            a, b = int(top["x0"] // CORNER), int(top["x1"] // CORNER)
            for bottom in (e for i in (a - 1, a, a + 1) for j in (b - 1, b, b + 1) for e in by_ends.get((i, j), ())):
                y0, y1 = top["top"], bottom["top"]
                if y1 - y0 < MIN_SIDE or abs(top["x0"] - bottom["x0"]) > CORNER or abs(top["x1"] - bottom["x1"]) > CORNER:
                    continue
                x0, x1 = min(top["x0"], bottom["x0"]), max(top["x1"], bottom["x1"])
                if x1 - x0 >= MIN_SIDE and side(x0, y0, y1) and side(x1, y0, y1):
                    found.add((round(x0, 2), round(y0, 2), round(x1, 2), round(y1, 2)))
    return sorted(found)


def _inside(bbox: BBox, box: tuple) -> bool:
    return box[0] - SLACK <= bbox.cx <= box[2] + SLACK and box[1] - SLACK <= bbox.cy <= box[3] + SLACK


def _held_lines(lines: list, box: tuple) -> list[_Held]:
    """The words of each text line inside the box, top to bottom."""
    out = []
    for line in lines:
        words = sorted((w for w in line.words if w.text.strip() and _inside(w.bbox, box)), key=lambda w: w.bbox.x0)
        if not words:
            continue
        sizes = [w.size for w in words if w.size > 0]
        out.append(_Held(y0=min(w.bbox.y0 for w in words), y1=max(w.bbox.y1 for w in words),
                         size=sum(sizes) / len(sizes) if sizes else 0.0, text=" ".join(w.text for w in words),
                         x0=words[0].bbox.x0, x1=max(w.bbox.x1 for w in words)))
    return sorted(out)


def _a_value(text: str) -> bool:
    """A line that is a value rather than words: as many digits as letters, or more ("0.46", "< 2.2e-16", "US $85.00")."""
    digits = sum(ch.isdigit() for ch in text)
    return digits > 0 and digits >= sum(ch.isalpha() for ch in text)


def _one_run(held: list[_Held], edges: list[dict]) -> bool:
    """Do the lines a box holds read as one run of text: nothing opening an item or closing a sentence before the last
    line, no line a value, one size of type, a line apart, and no rule drawn across them in between? The strokes of an
    icon set beside the text (Budget Direct draws an armchair and a lamp in each card) run under none of it. A value on
    a line of its own is a row's: a statistics table boxes "0.46" over "< 2.2e-16" beside "W" over "P value", two values
    the two labels pair with line by line (29c8f321 on the benchmark). And a key's lines are entries, not a run: each has
    a sample drawn just before its words (a plot legend's line and marker, on arxiv 2503.04674)."""
    texts = [h.text.strip() for h in held]
    if len(held) < 2 or any(_LIST_START.match(t) or _BULLET_START.match(t) or _a_value(t) for t in texts):
        return False
    if any(t[-1:] in ".!?" for t in texts[:-1]):
        return False
    if any(h.size <= 0 for h in held) or max(h.size for h in held) - min(h.size for h in held) > SAME_SIZE:
        return False
    if sum(1 for h in held if any(e["orientation"] == "h" and h.y0 <= e["top"] <= h.y1 and 0 <= h.x0 - e["x1"] <= h.size
                                  and e["x1"] - e["x0"] >= 0.5 * h.size for e in edges)) >= 2:
        return False
    for upper, lower in zip(held, held[1:]):
        if lower.y0 - upper.y1 > LEADING * upper.size:
            return False
        narrow = min((upper, lower), key=lambda h: h.x1 - h.x0)
        if any(e["orientation"] == "h" and upper.cy < e["top"] < lower.cy
               and min(e["x1"], narrow.x1) - max(e["x0"], narrow.x0) >= ACROSS * (narrow.x1 - narrow.x0) for e in edges):
            return False
    return True


def _folded(table: Table, folds: list[tuple[int, int]]) -> Table:
    """The table with each run of rows (first, last) made one row, its cells' text joined line by line."""
    row_of: dict[int, int] = {}
    ends = dict(folds)
    row, n_rows = 0, 0
    while row < table.n_rows:
        last = ends.get(row, row)
        for k in range(row, last + 1):
            row_of[k] = n_rows
        n_rows += 1
        row = last + 1
    parts: dict[tuple[int, int], list[TableCell]] = {}
    for c in sorted(table.cells, key=lambda c: (c.row, c.col)):
        parts.setdefault((row_of[c.row], c.col), []).append(c)
    cells = []
    for (r, col), group in sorted(parts.items()):
        text = ""
        for c in group:
            if c.text.strip():
                text = _join_lines(text, c.text)
        boxes = [c.bbox for c in group if c.bbox is not None]
        cells.append(TableCell(text=text, row=r, col=col, bbox=BBox.union_all(boxes) if boxes else None,
                               is_header=group[0].is_header))
    return Table(n_rows=n_rows, n_cols=table.n_cols, cells=cells, bbox=table.bbox, has_merged=table.has_merged,
                 provenance=table.provenance)


def fold_boxed_rows(table: Table, lines: list, edges: list[dict], boxes: list[tuple]) -> Table | None:
    """The table with the rows each drawn box holds together folded into one row, or None where no box does."""
    if table.n_rows < 3 or any(c.rowspan > 1 or c.colspan > 1 for c in table.cells):
        return None
    at = {(c.row, c.col): c for c in table.cells}
    near = table.bbox.expand(REACH)
    words = [w for line in lines for w in line.words if w.text.strip()]

    def place(w) -> tuple[int, int] | None:
        if not near.contains_point(w.bbox.cx, w.bbox.cy):
            return None
        hits = [c for c in table.cells if c.bbox is not None
                and c.bbox.x0 - SLACK <= w.bbox.cx <= c.bbox.x1 + SLACK
                and c.bbox.y0 - SLACK <= w.bbox.cy <= c.bbox.y1 + SLACK]
        if not hits:
            return None
        best = min(hits, key=lambda c: abs(c.bbox.cy - w.bbox.cy))
        return best.row, best.col

    placed = {id(w): place(w) for w in words}
    spans: dict[int, set[tuple]] = {}
    for box in boxes:
        held = [w for w in words if _inside(w.bbox, box)]
        where = {placed[id(w)] for w in held}
        if not held or None in where or len({col for _, col in where}) != 1:
            continue
        rows = sorted({r for r, _ in where})
        if len(rows) < 2 or rows[-1] - rows[0] != len(rows) - 1:
            continue
        if any(placed[id(w)] in where and not _inside(w.bbox, box) for w in words):
            continue
        spans.setdefault(next(iter(where))[1], set()).add((rows[0], rows[-1], box))
    by_rows: dict[tuple[int, int], dict[int, tuple]] = {}
    for col, found in spans.items():
        for first, last, box in found:
            by_rows.setdefault((first, last), {})[col] = box
    folds: list[tuple[int, int]] = []
    for (first, last), boxed in sorted(by_rows.items()):
        if any((f, l) != (first, last) and f <= last and l >= first for found in spans.values() for f, l, _ in found):
            continue
        if any(col not in boxed and sum(1 for r in range(first, last + 1)
                                        if (r, col) in at and at[(r, col)].text.strip()) > 1
               for col in range(table.n_cols)):
            continue
        if not any(c.text.strip() for c in table.cells if c.row < first or c.row > last):
            continue
        if not all(_one_run(_held_lines(lines, box), edges) for box in boxed.values()):
            continue
        folds.append((first, last))
    return _folded(table, folds) if folds else None


def join_boxed_rows(page, pdf_page, blocks: list[Block]) -> list[Block]:
    """The page's blocks, the rows of each text-built table that one drawn box holds together folded into one row."""
    tables = [b for b in blocks if b.kind == BlockKind.TABLE and b.table is not None
              and b.table.provenance in TEXT_BUILT and b.table.n_rows >= 3]
    if not tables or pdf_page is None or getattr(pdf_page, "rotation", 0):
        return blocks
    try:
        from truedoc.tables import ruled_pdfium as rp

        objs = pdfium_objects.page_objects(pdf_page.parent.name, pdf_page.number + 1) or []
        width, height = float(pdf_page.rect.width), float(pdf_page.rect.height)
        edges = rp._clip_to_page(rp._edges_from_objects(objs, None), (0.0, 0.0, width, height))
    except Exception:
        return blocks
    # Boxes are looked for over the whole page: a card's side can lie far from the text inside it.
    boxes = closed_boxes(edges) if edges else []
    if not boxes:
        return blocks
    lines = [l for l in page.lines if not l.rotated]
    for b in tables:
        region = b.table.bbox.union(b.bbox)
        mine = [box for box in boxes if box[0] <= region.x1 and box[2] >= region.x0
                and box[1] <= region.y1 and box[3] >= region.y0]
        if mine:
            folded = fold_boxed_rows(b.table, lines, edges, mine)
            if folded is not None:
                b.table = folded
    return blocks
