"""Ruled-table extraction using PyMuPDF's table finder (lines strategy).

This is the conservative first cut: only tables with visible rulings are
detected. Cell text is taken from the text layer, so characters are exact.
"""

from __future__ import annotations

import pymupdf

from truedoc.model import BBox, Block, BlockKind, Table, TableCell


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
        for ri, row in enumerate(rows):
            for ci in range(n_cols):
                val = row[ci] if ci < len(row) else None
                text = (val or "").replace("\n", " ").strip()
                if text:
                    non_empty += 1
                cbox = None
                if ri < len(cell_rects) and ci < len(cell_rects[ri]) and cell_rects[ri][ci] is not None:
                    cr = pymupdf.Rect(cell_rects[ri][ci])
                    if pdf_page.rotation:
                        cr = cr * pdf_page.rotation_matrix
                    cr.normalize()
                    cbox = BBox(float(cr.x0), float(cr.y0), float(cr.x1), float(cr.y1))
                cells.append(TableCell(text=text, row=ri, col=ci, is_header=(ri == 0), bbox=cbox))
        if non_empty < min(4, n_rows * n_cols):
            continue
        rect = pymupdf.Rect(t.bbox)
        if pdf_page.rotation:
            rect = rect * pdf_page.rotation_matrix
        bbox = BBox(float(rect.x0), float(rect.y0), float(rect.x1), float(rect.y1))
        table = Table(n_rows=n_rows, n_cols=n_cols, cells=cells, bbox=bbox, provenance="pymupdf-lines")
        blocks.append(Block(kind=BlockKind.TABLE, bbox=bbox, table=table, provenance="pymupdf-lines", confidence=0.8))
    return blocks
