"""A table read again from the cells its page draws, where the text built it across them.

GIO's home PDS page 26 draws its limits table as tiled filled cells - a blue header of two bands, the first holding one
cell that spans the three cover levels, then grey cells meeting at every row's edge - and TrueDoc built it from text
lines: the header's second band shared a row with the first line of every Jewellery limit, and "Paintings, pictures,
works of art, antiques, sculptures, ornaments and art objects" became two items with different limits. The Seniors
home PDS nests a grid of limits inside a "We cover" cell, and the ruled finder read the nest as one cell of run-on text;
a German dishwasher manual's fault table on the benchmark came out with its causes cut apart and run together.

A page that draws a table as filled cells has drawn its own grid, and `drawn_grids` reads it: groups of filled
rectangles that share edges; grid lines at their edges and at the rules among them; a fill covering several intervals
as one cell spanning them; open positions joined across any stretch of grid line nothing draws; grid lines no cell
starts or ends at taken out; rows no line of the table's text would fit in, holding only empty cells of their own,
taken out; and groups whose cells are mostly empty set aside as decoration. The header is the run of top rows drawn in
colours the body never uses, with at least two rows under it.

Most tables drawn that way are read right already - every table the ruled finder built on the eighteen benchmark and
insurance pages checked agrees with its drawing - so `redraw_tables` lets the drawing replace a table only on a stated
disagreement: words of one text cell lying on both sides of a drawn cell edge, in at least two places. A text table that
keeps several rows inside one shaded band, where the page lists sub-items ("# Fibres", "Passband", "Velocity accuracy"
under a spectrograph), shows no such crossing and stays as it is.
"""
from __future__ import annotations

from dataclasses import dataclass

from truedoc.extract import pdfium_objects
from truedoc.model import BBox, Block, BlockKind, Table, TableCell
from truedoc.tables.aligned import _join_lines

SAME = 1.0          # edges within this of one another are one grid line
EDGE = 1.0          # two fills touch when their facing sides lie within this
MIN_W, MIN_H = 8.0, 6.0
MIN_RULE = 10.0
THIN = 4.0          # the least height a row of text needs, when the table's words say nothing
CLEAR = 1.0         # a word this close to a drawn edge is on it, not on one side
MIN_CROSSINGS = 2
INSIDE = 0.9        # the share of a text table's words the drawing must hold before it may replace the table


@dataclass
class Cell:
    r0: int
    c0: int
    r1: int             # inclusive
    c1: int             # inclusive
    fill: tuple | None  # the fill's colour, rounded; None for an open cell
    text: str = ""


def _merged(values: list[float]) -> list[float]:
    groups: list[list[float]] = []
    for v in sorted(values):
        if groups and v - groups[-1][-1] <= SAME:
            groups[-1].append(v)
        else:
            groups.append([v])
    return [sum(g) / len(g) for g in groups]


def _index(lines: list[float], v: float) -> int:
    return min(range(len(lines)), key=lambda i: abs(lines[i] - v))


def _area(box: tuple) -> float:
    return max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])


def fills_from(objs, page_w: float, page_h: float) -> list[tuple]:
    """(rect, colour) for the filled rectangles a reader sees: not white, not transparent, not specks, not a panel
    behind the page."""
    out = []
    for o in objs:
        if o.kind != "path" or o.fill is None:
            continue
        f = o.fill
        if isinstance(f, (tuple, list)) and len(f) >= 3 and min(f[:3]) > 0.985:
            continue
        if o.fill_alpha is not None and o.fill_alpha < 0.05:
            continue
        colour = tuple(round(float(v), 2) for v in f) if isinstance(f, (tuple, list)) else (round(float(f), 2),)
        for r in o.rects or []:
            w, h = r[2] - r[0], r[3] - r[1]
            if w >= MIN_W and h >= MIN_H and not (w > 0.9 * page_w and h > 0.4 * page_h):
                out.append((tuple(r), colour))
    return out


def groups_of(fills: list[tuple]) -> list[list[tuple]]:
    """Fills gathered into groups whose members share edges, side by side or stacked."""
    n = len(fills)
    parent = list(range(n))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(n):
        a = fills[i][0]
        for j in range(i + 1, n):
            b = fills[j][0]
            v_overlap = min(a[3], b[3]) - max(a[1], b[1])
            h_overlap = min(a[2], b[2]) - max(a[0], b[0])
            side = ((abs(a[2] - b[0]) <= EDGE or abs(b[2] - a[0]) <= EDGE)
                    and v_overlap >= 0.5 * min(a[3] - a[1], b[3] - b[1]))
            stacked = ((abs(a[3] - b[1]) <= EDGE or abs(b[3] - a[1]) <= EDGE)
                       and h_overlap >= 0.5 * min(a[2] - a[0], b[2] - b[0]))
            if side or stacked:
                parent[find(i)] = find(j)
    found: dict[int, list[tuple]] = {}
    for i in range(n):
        found.setdefault(find(i), []).append(fills[i])
    return list(found.values())


def grid_of(fills: list[tuple], edges: list[dict]):
    """(xs, ys, cells) for one group of fills, or None when it spans fewer than two columns or two rows."""
    gx0, gy0 = min(f[0][0] for f in fills), min(f[0][1] for f in fills)
    gx1, gy1 = max(f[0][2] for f in fills), max(f[0][3] for f in fills)
    xs = [x for f in fills for x in (f[0][0], f[0][2])]
    ys = [y for f in fills for y in (f[0][1], f[0][3])]
    hrules, vrules = [], []
    for e in edges:
        if (e["orientation"] == "h" and e["x1"] - e["x0"] >= MIN_RULE and gy0 - SAME <= e["top"] <= gy1 + SAME
                and e["x0"] >= gx0 - 3 and e["x1"] <= gx1 + 3):
            ys.append(e["top"])
            hrules.append((e["top"], e["x0"], e["x1"]))
        elif (e["orientation"] == "v" and e["bottom"] - e["top"] >= MIN_RULE and gx0 - SAME <= e["x0"] <= gx1 + SAME
              and e["top"] >= gy0 - 3 and e["bottom"] <= gy1 + 3):
            xs.append(e["x0"])
            vrules.append((e["x0"], e["top"], e["bottom"]))
    xs, ys = _merged(xs), _merged(ys)
    n_cols, n_rows = len(xs) - 1, len(ys) - 1
    if n_cols < 2 or n_rows < 2:
        return None
    owner: list[list[Cell | None]] = [[None] * n_cols for _ in range(n_rows)]
    cells: list[Cell] = []
    for (x0, y0, x1, y1), colour in fills:
        c0, c1 = _index(xs, x0), _index(xs, x1)
        r0, r1 = _index(ys, y0), _index(ys, y1)
        if c1 <= c0 or r1 <= r0:
            continue
        if any(owner[r][c] is not None for r in range(r0, r1) for c in range(c0, c1)):
            continue    # a fill drawn over another: the first keeps its place
        cell = Cell(r0, c0, r1 - 1, c1 - 1, colour)
        cells.append(cell)
        for r in range(r0, r1):
            for c in range(c0, c1):
                owner[r][c] = cell

    def v_drawn(r: int, c: int) -> bool:
        x, top, bottom = xs[c + 1], ys[r], ys[r + 1]
        covered = sum(max(0.0, min(bottom, e1) - max(top, e0)) for ex, e0, e1 in vrules if abs(ex - x) <= SAME)
        return covered >= 0.6 * (bottom - top)

    def h_drawn(r: int, c: int) -> bool:
        y, left, right = ys[r + 1], xs[c], xs[c + 1]
        covered = sum(max(0.0, min(right, e1) - max(left, e0)) for ey, e0, e1 in hrules if abs(ey - y) <= SAME)
        return covered >= 0.6 * (right - left)

    active: dict[tuple[int, int], Cell] = {}
    for r in range(n_rows):
        runs = []
        c = 0
        while c < n_cols:
            if owner[r][c] is not None:
                c += 1
                continue
            c1 = c
            while c1 + 1 < n_cols and owner[r][c1 + 1] is None and not v_drawn(r, c1):
                c1 += 1
            runs.append((c, c1))
            c = c1 + 1
        new_active: dict[tuple[int, int], Cell] = {}
        for c0, c1 in runs:
            cell = active.get((c0, c1))
            if cell is not None and not any(h_drawn(r - 1, cc) for cc in range(c0, c1 + 1)):
                cell.r1 = r
            else:
                cell = Cell(r, c0, r, c1, None)
                cells.append(cell)
            new_active[(c0, c1)] = cell
        active = new_active
    return xs, ys, cells


def collapse(xs: list[float], ys: list[float], cells: list[Cell]) -> None:
    """Take out the grid lines no cell starts or ends at."""
    changed = True
    while changed:
        changed = False
        for i in range(1, len(xs) - 1):
            if not any(c.c0 == i or c.c1 + 1 == i for c in cells):
                del xs[i]
                for c in cells:
                    if c.c0 >= i:
                        c.c0 -= 1
                    if c.c1 >= i:
                        c.c1 -= 1
                changed = True
                break
        if changed:
            continue
        for i in range(1, len(ys) - 1):
            if not any(c.r0 == i or c.r1 + 1 == i for c in cells):
                del ys[i]
                for c in cells:
                    if c.r0 >= i:
                        c.r0 -= 1
                    if c.r1 >= i:
                        c.r1 -= 1
                changed = True
                break


def has_text(cell: Cell) -> bool:
    """A cell holds text when a letter or digit is in it: a zero-width or no-break space is not text."""
    return any(ch.isalnum() for ch in cell.text)


def place_words(xs: list[float], ys: list[float], cells: list[Cell], lines, join) -> None:
    pieces: dict[int, dict[int, list[str]]] = {}
    for li, line in enumerate(lines):
        for w in line.words:
            cx, cy = w.bbox.cx, w.bbox.cy
            if not w.text.strip() or not (xs[0] <= cx <= xs[-1] and ys[0] <= cy <= ys[-1]):
                continue
            for k, c in enumerate(cells):
                if xs[c.c0] <= cx <= xs[c.c1 + 1] and ys[c.r0] <= cy <= ys[c.r1 + 1]:
                    pieces.setdefault(k, {}).setdefault(li, []).append(w.text)
                    break
    for k, by_line in pieces.items():
        text = ""
        for li in sorted(by_line):
            text = join(text, " ".join(by_line[li]))
        cells[k].text = text


def drop_gaps(xs: list[float], ys: list[float], cells: list[Cell], line_height: float) -> None:
    """A row no line of the table's text could fit in, holding only empty cells of its own, is a drawn gap."""
    r = 0
    while r < len(ys) - 1:
        touching = [c for c in cells if c.r0 <= r <= c.r1]
        if (ys[r + 1] - ys[r] < max(THIN, line_height) and touching
                and all(c.r0 == r == c.r1 and not has_text(c) for c in touching)):
            cells[:] = [c for c in cells if all(c is not t for t in touching)]
            if r + 1 < len(ys) - 1:
                del ys[r + 1]       # the gap joins the row below it
            else:
                del ys[r]           # the last row: the gap joins the row above
            for c in cells:
                if c.r0 > r:
                    c.r0 -= 1
                if c.r1 > r:
                    c.r1 -= 1
            continue
        r += 1


def header_rows(cells: list[Cell], n_rows: int) -> int:
    """The run of top rows drawn wholly in fills whose colours no row below uses, with at least two rows under it."""
    best = 0
    for h in range(1, n_rows):
        top = [c for c in cells if c.r0 < h]
        if any(c.fill is None or c.r1 >= h for c in top):
            break
        below = {c.fill for c in cells if c.r0 >= h and c.fill is not None}
        if {c.fill for c in top} & below:
            continue
        if n_rows - h < 2:
            break       # a band over one row is not a header: BOM's coloured boxes over their grey panel
        best = h
    return best


def drawn_grids(objs, edges, lines, page_w: float, page_h: float, join) -> list[tuple]:
    """Every group of fills that reads as a table: (xs, ys, cells), the cells' text placed."""
    out = []
    for group in groups_of(fills_from(objs, page_w, page_h)):
        read = grid_of(group, edges)
        if read is None:
            continue
        xs, ys, cells = read
        collapse(xs, ys, cells)
        place_words(xs, ys, cells, lines, join)
        heights = sorted(w.bbox.y1 - w.bbox.y0 for line in lines for w in line.words
                         if w.text.strip() and xs[0] <= w.bbox.cx <= xs[-1] and ys[0] <= w.bbox.cy <= ys[-1])
        drop_gaps(xs, ys, cells, heights[len(heights) // 2] if heights else THIN)
        collapse(xs, ys, cells)
        if len(xs) < 3 or len(ys) < 3:
            continue
        if sum(1 for c in cells if has_text(c)) < 0.5 * len(cells):
            continue
        out.append((xs, ys, cells))
    return out


def crossings(table_cells, xs: list[float], ys: list[float], cells: list[Cell], words) -> int:
    """How many times words of one text cell lie on both sides of a drawn cell's edge."""
    found = set()
    for k, tc in enumerate(table_cells):
        if tc.bbox is None or not tc.text.strip():
            continue
        tokens = set(tc.text.split())
        mine = [w for w in words if w.text in tokens
                and tc.bbox.x0 - 1 <= w.bbox.cx <= tc.bbox.x1 + 1 and tc.bbox.y0 - 1 <= w.bbox.cy <= tc.bbox.y1 + 1]
        if len(mine) < 2:
            continue
        for dc in cells:
            x0, x1, y0, y1 = xs[dc.c0], xs[dc.c1 + 1], ys[dc.r0], ys[dc.r1 + 1]
            column = [w for w in mine if x0 <= w.bbox.cx <= x1]
            for y in (y0, y1):
                if any(w.bbox.cy < y - CLEAR for w in column) and any(w.bbox.cy > y + CLEAR for w in column):
                    found.add((k, "row", round(y, 1)))
            band = [w for w in mine if y0 <= w.bbox.cy <= y1]
            for x in (x0, x1):
                if any(w.bbox.cx < x - CLEAR for w in band) and any(w.bbox.cx > x + CLEAR for w in band):
                    found.add((k, "column", round(x, 1)))
    return len(found)


def table_from_grid(xs: list[float], ys: list[float], cells: list[Cell]) -> Table:
    """The drawing as a table: each cell with its span and box, the header rows marked."""
    header = header_rows(cells, len(ys) - 1)
    out = [TableCell(text=c.text, row=c.r0, col=c.c0, rowspan=c.r1 - c.r0 + 1, colspan=c.c1 - c.c0 + 1,
                     bbox=BBox(xs[c.c0], ys[c.r0], xs[c.c1 + 1], ys[c.r1 + 1]), is_header=c.r1 < header)
           for c in sorted(cells, key=lambda c: (c.r0, c.c0))]
    # Spans, and a header of two rows, are written as HTML, as the ruled and aligned finders' tables are: a pipe table
    # repeats a spanning cell's text in every column it covers ("Limits for any one incident" three times over).
    merged = header >= 2 or any(c.r1 > c.r0 or c.c1 > c.c0 for c in cells)
    return Table(n_rows=len(ys) - 1, n_cols=len(xs) - 1, cells=out, bbox=BBox(xs[0], ys[0], xs[-1], ys[-1]),
                 has_merged=merged, provenance="drawn-cells")


def redraw_tables(page, pdf_page, blocks: list[Block]) -> list[Block]:
    """The page's blocks, each table the text built across its drawn cells read again from the drawing.

    A table is replaced only where words of one of its cells lie on both sides of a drawn cell's edge in at least two
    places and the drawing holds nine in ten of the table's words; the drawing's lines leave the text blocks that held
    them, and another table lying inside the drawing gives way to it."""
    tables = [b for b in blocks if b.kind == BlockKind.TABLE and b.table is not None and b.table.cells]
    if not tables or pdf_page is None or getattr(pdf_page, "rotation", 0):
        return blocks
    try:
        from truedoc.tables import ruled_pdfium as rp

        objs = pdfium_objects.page_objects(pdf_page.parent.name, pdf_page.number + 1) or []
        width, height = float(pdf_page.rect.width), float(pdf_page.rect.height)
        if len(fills_from(objs, width, height)) < 4:
            return blocks
        edges = rp._clip_to_page(rp._edges_from_objects(objs, None), (0.0, 0.0, width, height))
    except Exception:
        return blocks
    lines = sorted((l for l in page.lines if not l.rotated), key=lambda l: (round(l.bbox.cy, 1), l.bbox.x0))
    grids = drawn_grids(objs, edges, lines, width, height, _join_lines)
    if not grids:
        return blocks
    words = [w for line in lines for w in line.words if w.text.strip()]
    replaced: dict[int, Block] = {}
    boxes: list[BBox] = []
    for b in tables:
        tb = (b.bbox.x0, b.bbox.y0, b.bbox.x1, b.bbox.y1)
        mine = [w for w in words if tb[0] <= w.bbox.cx <= tb[2] and tb[1] <= w.bbox.cy <= tb[3]]
        if not mine:
            continue
        best = None
        for xs, ys, cells in grids:
            box = (xs[0], ys[0], xs[-1], ys[-1])
            inter = (max(tb[0], box[0]), max(tb[1], box[1]), min(tb[2], box[2]), min(tb[3], box[3]))
            if _area(inter) < 0.5 * min(_area(tb), _area(box)):
                continue
            held = [w for w in mine if box[0] <= w.bbox.cx <= box[2] and box[1] <= w.bbox.cy <= box[3]]
            if len(held) < INSIDE * len(mine):
                continue
            n = crossings(b.table.cells, xs, ys, cells, words)
            if n >= MIN_CROSSINGS and (best is None or n > best[0]):
                best = (n, xs, ys, cells)
        if best is None:
            continue
        _, xs, ys, cells = best
        table = table_from_grid(xs, ys, cells)
        replaced[id(b)] = Block(kind=BlockKind.TABLE, bbox=table.bbox, table=table, provenance="drawn-cells",
                                confidence=b.confidence)
        boxes.append(table.bbox)
    if not replaced:
        return blocks

    def inside(line) -> bool:
        return not line.rotated and any(box.contains_point(line.bbox.cx, line.bbox.cy) for box in boxes)

    out: list[Block] = []
    for b in blocks:
        if id(b) in replaced:
            out.append(replaced[id(b)])
            continue
        if b.kind == BlockKind.TABLE:
            if not any(b.bbox.overlap_fraction(box) > 0.8 for box in boxes):
                out.append(b)
            continue
        if not b.lines:
            out.append(b)
            continue
        remaining = [l for l in b.lines if not inside(l)]
        if not remaining:
            continue
        if len(remaining) != len(b.lines):
            b.lines = remaining
            b.bbox = BBox.union_all(l.bbox for l in remaining)
        out.append(b)
    return out
