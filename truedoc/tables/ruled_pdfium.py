"""Find ruled tables from our own geometry, using pdfplumber's algorithm (D007, M18).

PyMuPDF's `find_tables` is itself a port of pdfplumber's, and says so in its own source header, so
the algorithm this project depends on has always been MIT-licensed. Only the copy of it was AGPL.

**Using pdfplumber as a library does not work**, and that is worth stating because it is the
obvious thing to try: `pdfplumber.open(...).pages[0].find_tables(...)` reads the page through
pdfminer, and "lines_strict" means "the lines my own reader found". On one benchmark page PyMuPDF
finds two tables that way and pdfplumber finds none. It also drags in a third PDF engine.

What works is taking the algorithm without the reader. `snap_edges`, `merge_edges`,
`edges_to_intersections`, `intersections_to_cells` and `cells_to_tables` are plain functions over
plain dictionaries, and `Table` needs nothing from a page but a list of cells. Fed the rules
TrueDoc already has, they reproduce PyMuPDF: on `b5c5b866...` two tables of 35 and 30 cells
against PyMuPDF's 5x7 and 6x5.

**Everything here is in the page's rendered space** - the space PyMuPDF's own finder reports in
(measured on a page turned 90 degrees: its first cell holds the word "Table" only once the word
is turned by the rotation matrix). Rows are what a reader sees as rows, so a turned page reads 8
rows by 7 as PyMuPDF does and not the transpose, which building in the unrotated space gave.

**Cell text comes from TrueDoc's own words**, not from pdfplumber's character clustering. That
clustering breaks words at one fixed gap, and no single gap fits both a 9pt table whose word
spaces are 2.5pt ("TypeofTask" at 3pt) and a 7pt table whose letter spacing runs past a
seventh of an em ("fr actu res" at 0.15 em); TrueDoc's word builder judges each line by its own
letter gaps and reads both. It also settles the turned page: the words already follow their
line's direction, where a character clustering that assumes level text stacked each cell into
`K
a
p
p
a`.
"""
from __future__ import annotations

import os

from truedoc.extract import pdfium_objects

# How thin a shape has to be before it counts as a rule rather than a box. The same limit
# `textlayer._extract_drawings` uses to call something an "hline" or a "vline".
_MAX_RULE = 3.0
_MIN_RULE = 2.0
_MAX_EDGES = 20000      # a generated page can carry tens of thousands of shapes


def _edge_rule() -> str:
    return os.environ.get("TRUEDOC_TABLE_EDGES", "all").strip().lower()


def available() -> bool:
    try:
        import pdfplumber.table  # noqa: F401
    except Exception:
        return False
    return pdfium_objects.available()


def _turned(rect, M):
    """A rectangle turned into the rendered space by the page's rotation matrix."""
    if M is None:
        return rect
    import pymupdf
    r = pymupdf.Rect(*rect) * pymupdf.Matrix(M)
    r.normalize()
    return (float(r.x0), float(r.y0), float(r.x1), float(r.y1))


def _edges_from_objects(objs: list, M=None) -> list[dict]:
    """Every thin, long shape on the page, as a pdfplumber edge, in the rendered space.

    A rule may be drawn as a stroked line, as a very flat filled rectangle, or as a one-pixel
    image stretched along a row, so each is tagged with where it came from and `_edge_rule`
    decides which of them count.

    Only thin shapes become edges. Breaking every *box* into its four sides as well - which is
    what pdfplumber does with a rectangle - was written and measured, because a page that reads
    4x2 against PyMuPDF's 5x2 is missing exactly one outer rule. It did not fix that page, and it
    invented a spurious table on two pages that had been matching PyMuPDF cell for cell, so it
    came out again. (What that page was missing turned out to be the outline of its rules as a
    whole - see `_frame_edges`.)
    """
    out: list[dict] = []
    for o in objs:
        if o.kind not in ("path", "image"):
            continue
        if len(out) >= _MAX_EDGES:
            break
        stroked = o.kind == "path" and o.stroke is not None
        source = "line" if stroked else ("image" if o.kind == "image" else "rect_edge")
        for rect in (o.rects or [o.bbox]):
            x0, y0, x1, y1 = _turned(rect, M)
            w, h = x1 - x0, y1 - y0
            if h <= _MAX_RULE and w >= _MIN_RULE:
                out.append(_h_edge(source, x0, x1, (y0 + y1) / 2.0))
            elif w <= _MAX_RULE and h >= _MIN_RULE:
                out.append(_v_edge(source, (x0 + x1) / 2.0, y0, y1))
    return out


def _frame_edges(edges: list[dict], words: list[dict], snap: float = 3.0) -> list[dict]:
    """The outline of each cluster of touching rules, as four more edges.

    A table ruled only between its rows - horizontal rules the full width, a vertical rule or
    two inside, none down the left - has no crossing at its left corners, and pdfplumber's cell
    finder, which needs a crossing at every corner, closes only the columns that have one: on
    one benchmark page it read the right column alone, 4 cells for PyMuPDF's 10. PyMuPDF's port
    first joins rules that stand within a snap tolerance of each other into one box and, where
    the box holds text, takes its four sides as rules too. Measured on that page, the missing
    rule is exactly that box's left side. This does the same over the same edges.
    """
    rects = [(e["x0"], e["top"], e["x1"], e["bottom"]) for e in edges]
    if not rects:
        return []

    def neighbours(a, b) -> bool:
        ax0, ay0, ax1, ay1 = a
        bx0, by0, bx1, by1 = b
        near_x = (bx0 - snap <= ax0 <= bx1 + snap or bx0 - snap <= ax1 <= bx1 + snap
                  or ax0 - snap <= bx0 <= ax1 + snap or ax0 - snap <= bx1 <= ax1 + snap)
        near_y = (by0 - snap <= ay0 <= by1 + snap or by0 - snap <= ay1 <= by1 + snap
                  or ay0 - snap <= by0 <= ay1 + snap or ay0 - snap <= by1 <= ay1 + snap)
        return near_x and near_y

    boxes: list[tuple[float, float, float, float]] = []
    pending = sorted(set(rects), key=lambda r: (r[3], r[0]))
    while pending:
        box = pending.pop(0)
        grew = True
        while grew:
            grew = False
            for i in range(len(pending) - 1, -1, -1):
                if neighbours(box, pending[i]):
                    r = pending.pop(i)
                    box = (min(box[0], r[0]), min(box[1], r[1]), max(box[2], r[2]), max(box[3], r[3]))
                    grew = True
        boxes.append(box)
    out: list[dict] = []
    for x0, y0, x1, y1 in boxes:
        if x1 - x0 < _MIN_RULE or y1 - y0 < _MIN_RULE:
            continue
        if not any(x0 <= (w["x0"] + w["x1"]) / 2.0 <= x1 and y0 <= (w["top"] + w["bottom"]) / 2.0 <= y1 for w in words):
            continue
        out.append(_h_edge("rect_edge", x0, x1, y0))
        out.append(_h_edge("rect_edge", x0, x1, y1))
        out.append(_v_edge("rect_edge", x0, y0, y1))
        out.append(_v_edge("rect_edge", x1, y0, y1))
    return out


def _h_edge(source: str, x0: float, x1: float, y: float) -> dict:
    return {"object_type": source, "orientation": "h", "x0": x0, "x1": x1,
            "top": y, "bottom": y, "width": x1 - x0, "height": 0.0, "doctop": y}


def _v_edge(source: str, x: float, y0: float, y1: float) -> dict:
    return {"object_type": source, "orientation": "v", "x0": x, "x1": x,
            "top": y0, "bottom": y1, "width": 0.0, "height": y1 - y0, "doctop": y0}


def _words_for_cells(page) -> list[dict]:
    """TrueDoc's own words, in the rendered space they are held in, with the line each is on.

    Overprinted text - a document that fakes bold by drawing the same run twice - is already
    one word here; it read "SSmmiitthh eett aall." when cells were filled from characters.
    """
    out: list[dict] = []
    for li, line in enumerate(page.lines):
        for wi, w in enumerate(line.words):
            if not w.text.strip():
                continue
            b = w.bbox
            out.append({"line": li, "order": wi, "text": w.text, "x0": b.x0, "x1": b.x1, "top": b.y0, "bottom": b.y1})
    return out


def _cell_text(words: list[dict], cell) -> str:
    """The words whose centres fall in the cell, a visual row to a line, left to right.

    A row is what the reader sees as one: lines whose bands overlap by more than half the
    shorter one. A raised "**" that the file draws before its number arrives on a line of its
    own, above the number's; sorted by top it came first ("** 0.78"), and it belongs after.
    """
    x0, top, x1, bottom = cell
    inside = [w for w in words if x0 <= (w["x0"] + w["x1"]) / 2.0 <= x1 and top <= (w["top"] + w["bottom"]) / 2.0 <= bottom]
    if not inside:
        return ""
    lines: dict[int, list[dict]] = {}
    for w in inside:
        lines.setdefault(w["line"], []).append(w)
    bands = sorted(((min(w["top"] for w in ws), max(w["bottom"] for w in ws), ws) for ws in lines.values()), key=lambda b: b[0])
    rows: list[list[dict]] = []
    row_band: tuple[float, float] | None = None
    for y0, y1, ws in bands:
        if row_band is not None and min(row_band[1], y1) - max(row_band[0], y0) > 0.5 * min(row_band[1] - row_band[0], y1 - y0):
            rows[-1].extend(ws)
            row_band = (min(row_band[0], y0), max(row_band[1], y1))
        else:
            rows.append(list(ws))
            row_band = (y0, y1)
    return "\n".join(" ".join(w["text"] for w in sorted(ws, key=lambda w: (w["x0"], w["order"]))) for ws in rows)


class _Table:
    """What `find_ruled_tables` reads off a table: `.rows[].cells`, `.bbox` and `.extract()`,
    the shape of pdfplumber's `Table` (and PyMuPDF's), with the text filled from our words."""

    def __init__(self, table, words: list[dict]):
        self._table = table
        self._words = words

    @property
    def rows(self):
        return self._table.rows

    @property
    def bbox(self):
        return self._table.bbox

    def extract(self, **kwargs) -> list[list[str | None]]:
        return [[None if cell is None else _cell_text(self._words, cell) for cell in row.cells] for row in self.rows]


def find_tables(pdf_page, page) -> list | None:
    """Tables with visible rulings, in the rendered space, or None when this path cannot answer.

    Each result quacks like PyMuPDF's: it has `.extract()`, `.rows` and `.bbox`, which is all
    `find_ruled_tables` and the cell logic downstream of it ever ask for.
    """
    try:
        from pdfplumber.table import (Table, TableSettings, cells_to_tables,
                                      edges_to_intersections, intersections_to_cells, merge_edges)
        from pdfplumber.utils import filter_edges
    except Exception:
        return None
    if page is None or not getattr(page, "lines", None):
        return None
    try:
        objs = pdfium_objects.page_objects(pdf_page.parent.name, pdf_page.number + 1)
    except Exception:
        return None
    if objs is None:
        return None

    settings = TableSettings.resolve({"vertical_strategy": "lines_strict",
                                      "horizontal_strategy": "lines_strict"})
    try:
        M = pdf_page.rotation_matrix if pdf_page.rotation else None
        words = _words_for_cells(page)
        edges = _edges_from_objects(objs, M)
        if not edges:
            return []
        edges = edges + _frame_edges(edges, words)
        # Which shapes count as a rule. "strokes" matches pdfplumber's own lines_strict and is
        # exact on a table ruled with drawn lines; "all" also takes flat filled rectangles and
        # image strips, which some documents rule with and which strokes-only loses entirely.
        # PyMuPDF's finder sits somewhere between the two, so the choice is made on the score.
        if _edge_rule() == "strokes":
            edges = (filter_edges(edges, "v", edge_type="line", min_length=settings.edge_min_length_prefilter)
                     + filter_edges(edges, "h", edge_type="line", min_length=settings.edge_min_length_prefilter))
        else:
            edges = filter_edges(edges, min_length=settings.edge_min_length_prefilter)
        edges = merge_edges(edges,
                            snap_x_tolerance=settings.snap_x_tolerance,
                            snap_y_tolerance=settings.snap_y_tolerance,
                            join_x_tolerance=settings.join_x_tolerance,
                            join_y_tolerance=settings.join_y_tolerance)
        edges = filter_edges(edges, min_length=settings.edge_min_length)
        if not edges:
            return []
        cells = intersections_to_cells(
            edges_to_intersections(edges, settings.intersection_x_tolerance,
                                   settings.intersection_y_tolerance))
        if not cells:
            return []
        return [_Table(Table(None, group), words) for group in cells_to_tables(cells)]
    except Exception:
        return None
