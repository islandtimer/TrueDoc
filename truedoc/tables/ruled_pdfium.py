"""Find ruled tables from our own geometry, using pdfplumber's algorithm (D007, M18).

PyMuPDF's `find_tables` is itself a port of pdfplumber's, and says so in its own source header, so
the algorithm this project depends on has always been MIT-licensed. Only the copy of it was AGPL.

**Using pdfplumber as a library does not work**, and that is worth stating because it is the
obvious thing to try: `pdfplumber.open(...).pages[0].find_tables(...)` reads the page through
pdfminer, and "lines_strict" means "the lines my own reader found". On one benchmark page PyMuPDF
finds two tables that way and pdfplumber finds none. It also drags in a third PDF engine.

What works is taking the algorithm without the reader. `snap_edges`, `merge_edges`,
`edges_to_intersections`, `intersections_to_cells` and `cells_to_tables` are plain functions over
plain dictionaries, and `Table` needs nothing from a page except a list of characters. Fed the
lines and characters TrueDoc already has, they reproduce PyMuPDF: on `b5c5b866...` two tables of
35 and 30 cells against PyMuPDF's 5x7 and 6x5.

**Everything here is in the page's unrotated space**, which is what `find_ruled_tables` expects -
it applies the page rotation itself, at the end. TrueDoc's characters are held rotated, so they are
turned back on the way in, inverting exactly the turn `textlayer._rect` applied.

Building in the *rendered* space instead was tried, because PyMuPDF's own finder reports its table
box there - `(66.6, 84.9, 545.4, 304.0)`, landscape, inside a 792x612 rendered rect. It is worse:
a page turned 90 degrees has its glyphs turned too, so in rendered space the text runs down the
page one letter at a time, and pdfplumber's extractor - which assumes level text - stacks each cell
into `K
a
p
p
a`. Unrotated space at least reads each cell correctly. What it does not fix is
the row and column assignment on such a page, where PyMuPDF reads 8 rows by 7 and this reads the
transpose; that is the largest single piece of the remaining gap.
"""
from __future__ import annotations

import os
from types import SimpleNamespace

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


def _edges_from_objects(objs: list) -> list[dict]:
    """Every thin, long shape on the page, as a pdfplumber edge.

    A rule may be drawn as a stroked line, as a very flat filled rectangle, or as a one-pixel
    image stretched along a row, so each is tagged with where it came from and `_edge_rule`
    decides which of them count.

    Only thin shapes become edges. Breaking every *box* into its four sides as well - which is
    what pdfplumber does with a rectangle - was written and measured, because a page that reads
    4x2 against PyMuPDF's 5x2 is missing exactly one outer rule. It did not fix that page, and it
    invented a spurious table on two pages that had been matching PyMuPDF cell for cell, so it
    came out again.
    """
    out: list[dict] = []
    for o in objs:
        if o.kind not in ("path", "image"):
            continue
        if len(out) >= _MAX_EDGES:
            break
        stroked = o.kind == "path" and o.stroke is not None
        source = "line" if stroked else ("image" if o.kind == "image" else "rect_edge")
        for x0, y0, x1, y1 in (o.rects or [o.bbox]):
            w, h = x1 - x0, y1 - y0
            if h <= _MAX_RULE and w >= _MIN_RULE:
                out.append(_h_edge(source, x0, x1, (y0 + y1) / 2.0))
            elif w <= _MAX_RULE and h >= _MIN_RULE:
                out.append(_v_edge(source, (x0 + x1) / 2.0, y0, y1))
    return out


def _h_edge(source: str, x0: float, x1: float, y: float) -> dict:
    return {"object_type": source, "orientation": "h", "x0": x0, "x1": x1,
            "top": y, "bottom": y, "width": x1 - x0, "height": 0.0, "doctop": y}


def _v_edge(source: str, x: float, y0: float, y1: float) -> dict:
    return {"object_type": source, "orientation": "v", "x0": x, "x1": x,
            "top": y0, "bottom": y1, "width": 0.0, "height": y1 - y0, "doctop": y0}


def _chars_for_pdfplumber(page, M) -> list[dict]:
    """TrueDoc's own characters as pdfplumber character dicts, in unrotated page space.

    Overprinted text is dropped on the way. A document that fakes bold by drawing the same run
    twice in the same place - 755 characters of one benchmark page - would otherwise read
    "SSmmiitthh eett aall." in every cell, because nothing downstream of here collapses them.
    TrueDoc's own word building already does this, which is why the page converts correctly
    everywhere else; PyMuPDF's cell extractor does it too.
    """
    import pymupdf

    inverse = ~pymupdf.Matrix(M) if M is not None else None
    out: list[dict] = []
    seen: set[tuple] = set()
    for c in page.chars:
        b = c.bbox
        if inverse is not None:
            r = pymupdf.Rect(b.x0, b.y0, b.x1, b.y1) * inverse
            r.normalize()
            x0, top, x1, bottom = float(r.x0), float(r.y0), float(r.x1), float(r.y1)
        else:
            x0, top, x1, bottom = b.x0, b.y0, b.x1, b.y1
        stamp = (c.text, round(x0, 1), round(top, 1))
        if stamp in seen:
            continue
        seen.add(stamp)
        out.append({"text": c.text, "x0": x0, "x1": x1, "top": top, "bottom": bottom,
                    "doctop": top, "upright": True, "size": c.size, "fontname": c.font,
                    "width": x1 - x0, "height": bottom - top, "object_type": "char"})
    return out


def find_tables(pdf_page, page) -> list | None:
    """Tables with visible rulings, or None when this path cannot answer.

    Each result quacks like PyMuPDF's: it has `.extract()`, `.rows` and `.bbox`, which is all
    `find_ruled_tables` and the cell logic downstream of it ever ask for.
    """
    try:
        from pdfplumber.table import (Table, TableSettings, cells_to_tables,
                                      edges_to_intersections, intersections_to_cells, merge_edges)
        from pdfplumber.utils import filter_edges
    except Exception:
        return None
    if page is None or not getattr(page, "chars", None):
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
        edges = _edges_from_objects(objs)
        if not edges:
            return []
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
        M = pdf_page.rotation_matrix if pdf_page.rotation else None
        stub = SimpleNamespace(chars=_chars_for_pdfplumber(page, M))
        return [Table(stub, group) for group in cells_to_tables(cells)]
    except Exception:
        return None
