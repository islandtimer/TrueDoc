"""Ruled-table extraction using PyMuPDF's table finder (lines strategy).

This is the conservative first cut: only tables with visible rulings are
detected. Cell text is taken from the text layer, so characters are exact.
"""

from __future__ import annotations

import pymupdf

from truedoc.model import BBox, Block, BlockKind, Table, TableCell
from truedoc.tables.aligned import _continues
from truedoc.tables.cells import clean_cell_text


def split_multiline_row(row: list, n_cols: int) -> list[list[str]] | None:
    """Lines that pair up across a ruled row's cells are rows of their own.

    A statistics table rules a box around "Shapiro W / P value" beside "0.46 /
    < 2.2e-16", a specification sheet around four instrument properties beside
    their four values; a reader takes each line as a row. Every filled cell must
    hold the same number of short lines, and no line may read as the wrapped
    continuation of the one above it (a lowercase start, a bracketed statistic
    under its value, a line ending in a comma or a connector).
    """
    texts = [((row[ci] if ci < len(row) else None) or "") for ci in range(n_cols)]
    lines = [[ln.strip() for ln in t.split("\n") if ln.strip()] for t in texts]
    multi = [ci for ci, ls in enumerate(lines) if len(ls) >= 2]
    if not multi or len({len(lines[ci]) for ci in multi}) != 1:
        return None
    # A one-line cell left of the stacks is the row's label ("Cd" beside
    # "Shapiro W / P value") and stays on the first row; one to the right is
    # the single value of a wrapped label, so the row is left whole.
    if any(len(ls) == 1 and ci > multi[0] for ci, ls in enumerate(lines)):
        return None
    k = len(lines[multi[0]])
    if k > 8:
        return None
    for ls in lines:
        if any(len(ln.split()) > 6 for ln in ls):
            return None
        if any(_continues(a, b) for a, b in zip(ls, ls[1:])):
            return None
    return [[(ls[i] if i < len(ls) else "") for ls in lines] for i in range(k)]


def find_ruled_tables(pdf_page: "pymupdf.Page") -> list[Block]:
    blocks: list[Block] = []
    try:
        found = pdf_page.find_tables(strategy="lines_strict")
    except Exception:
        return blocks
    for t in found.tables:
        try:
            rows = t.extract()
        except Exception:
            continue
        if not rows:
            continue
        n_rows = len(rows)
        n_cols = max(len(r) for r in rows)
        # A boxed single row is returned too: the pipeline keeps it only when the
        # column headings printed above the box turn it into a two-row table.
        if n_rows < 1 or n_cols < 2:
            continue
        cells: list[TableCell] = []
        non_empty = 0
        # Cell boxes, so marks drawn inside a cell (a tick, a cross) can be placed.
        cell_rects: list[list] = []
        try:
            for trow in t.rows:
                cell_rects.append(list(trow.cells))
        except Exception:
            cell_rects = []
        # A body row whose cells hold lines that pair up becomes several rows.
        expanded: list[tuple[list, int, int, int]] = []   # (cell texts, source row, slice, slices)
        for ri, row in enumerate(rows):
            parts = split_multiline_row(row, n_cols) if ri > 0 else None
            if parts:
                for k, prow in enumerate(parts):
                    expanded.append((prow, ri, k, len(parts)))
            else:
                expanded.append((row, ri, 0, 1))
        n_rows = len(expanded)
        for ri, (row, src, k, slices) in enumerate(expanded):
            for ci in range(n_cols):
                val = row[ci] if ci < len(row) else None
                text = (val or "").replace("\n", " ").strip()
                if text:
                    non_empty += 1
                cbox = None
                if src < len(cell_rects) and ci < len(cell_rects[src]) and cell_rects[src][ci] is not None:
                    cr = pymupdf.Rect(cell_rects[src][ci])
                    if pdf_page.rotation:
                        cr = cr * pdf_page.rotation_matrix
                    cr.normalize()
                    if slices > 1:
                        h = (cr.y1 - cr.y0) / slices
                        cr = pymupdf.Rect(cr.x0, cr.y0 + k * h, cr.x1, cr.y0 + (k + 1) * h)
                    cbox = BBox(float(cr.x0), float(cr.y0), float(cr.x1), float(cr.y1))
                cells.append(TableCell(text=clean_cell_text(text), row=ri, col=ci, is_header=(ri == 0), bbox=cbox))
        if non_empty < min(4, n_rows * n_cols):
            continue
        rect = pymupdf.Rect(t.bbox)
        if pdf_page.rotation:
            rect = rect * pdf_page.rotation_matrix
        bbox = BBox(float(rect.x0), float(rect.y0), float(rect.x1), float(rect.y1))
        table = Table(n_rows=n_rows, n_cols=n_cols, cells=cells, bbox=bbox, provenance="pymupdf-lines")
        blocks.append(Block(kind=BlockKind.TABLE, bbox=bbox, table=table, provenance="pymupdf-lines", confidence=0.8))
    return blocks
