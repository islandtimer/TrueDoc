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
it applies the page rotation itself, at the end, to the cell boxes and the table box. TrueDoc's
own characters are held rotated, so they are turned back on the way in; that inverts exactly the
turn `textlayer._rect` applied, rather than approximating it.
"""
from __future__ import annotations

from types import SimpleNamespace

from truedoc.extract import pdfium_objects

# How thin a shape has to be before it counts as a rule rather than a box. The same limit
# `textlayer._extract_drawings` uses to call something an "hline" or a "vline".
_MAX_RULE = 3.0
_MIN_RULE = 2.0


def available() -> bool:
    try:
        import pdfplumber.table  # noqa: F401
    except Exception:
        return False
    return pdfium_objects.available()


def _edges_from_objects(objs: list) -> list[dict]:
    """Every thin, long shape on the page, as a pdfplumber edge.

    A rule may be drawn as a stroked line, as a very flat filled rectangle, or as a one-pixel
    image stretched along the row - the third is why `textlayer._extract_drawings` consults
    MuPDF's bbox log as well as its drawings, and why images are included here.
    """
    out: list[dict] = []
    for o in objs:
        if o.kind not in ("path", "image"):
            continue
        for x0, y0, x1, y1 in (o.rects or [o.bbox]):
            w, h = x1 - x0, y1 - y0
            if h <= _MAX_RULE and w >= _MIN_RULE:
                y = (y0 + y1) / 2.0
                out.append({"object_type": "line", "orientation": "h",
                            "x0": x0, "x1": x1, "top": y, "bottom": y,
                            "width": w, "height": 0.0, "doctop": y})
            elif w <= _MAX_RULE and h >= _MIN_RULE:
                x = (x0 + x1) / 2.0
                out.append({"object_type": "line", "orientation": "v",
                            "x0": x, "x1": x, "top": y0, "bottom": y1,
                            "width": 0.0, "height": h, "doctop": y0})
    return out


def _chars_for_pdfplumber(page, M) -> list[dict]:
    """TrueDoc's own characters as pdfplumber character dicts, in unrotated page space."""
    import pymupdf

    inverse = ~pymupdf.Matrix(M) if M is not None else None
    out: list[dict] = []
    for c in page.chars:
        b = c.bbox
        if inverse is not None:
            r = pymupdf.Rect(b.x0, b.y0, b.x1, b.y1) * inverse
            r.normalize()
            x0, top, x1, bottom = float(r.x0), float(r.y0), float(r.x1), float(r.y1)
        else:
            x0, top, x1, bottom = b.x0, b.y0, b.x1, b.y1
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
