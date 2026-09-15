"""Two lists set side by side are written as two lists, not as rows cut from their lines (D028).

POL1418DIR's home PDS page 13 sets what its buildings cover includes and excludes as a ticked list beside a crossed
list, with no boxes drawn. The aligned finder built a table from the text lines: a row for each line, the crosses in a
narrow column of their own, and an item cut wherever it wraps - "or commercial building", the end of the hotel and
motel exclusion, in a row of its own, and the condition on residential flats ("that are part of a strata title
development unless buildings cover is included on your policy details document") on the row of "Recreational
structures", where a reader takes it for that item's. The owner named that as the fault that matters for meaning, and
ruled (D028) that a list is written as a list: rows pair a line of one list with a line of the other only by their
order.

The table is read again column by column, as the page sets it. A column holding nothing but marks is the marks of the
column to its right. A row holding only a label in its first column, with no mark, opens a section ("Structures"). In
each section each column's words are read as D028 reads a list in a box (`cell_lists.build_listing`): a mark opens an
entry at its hanging indent, and lines at that indent carry it on. The table is rebuilt - its headings, a band for each
section's label, and a row for each section whose cells hold the lists - only where every column of every section
opens with an entry, one column somewhere is a list (`cell_lists.is_list`), and the rebuilt table holds exactly the words the
old one held.
"""
from __future__ import annotations

import collections

from truedoc.model import BBox, Block, BlockKind, CellList, Table, TableCell
from truedoc.tables.cell_lists import BULLETS, MARK_TEXT, MARKS, build_listing, is_list, lines_in

TEXT_BUILT = ("textlayer-aligned", "layout-table")


def _words(texts) -> collections.Counter:
    return collections.Counter(w for t in texts for w in t.split() if w not in BULLETS)


def _listing_words(listing: CellList) -> str:
    parts = [listing.lead]
    for item in listing.items:
        parts += [item.text, *item.children, item.tail]
    parts.append(listing.note)
    return " ".join(p for p in parts if p)


def rebuild_side_by_side_lists(page, blocks: list[Block]) -> None:
    """Each text-built table that is lists set side by side, rebuilt as those lists."""
    marks = [m for m in page.meta.get("marks", []) if m.get("kind") in MARK_TEXT]
    for b in blocks:
        if b.kind == BlockKind.TABLE and b.table is not None and b.table.provenance in TEXT_BUILT:
            table = side_by_side(page, b.table, marks)
            if table is not None:
                b.table = table


def side_by_side(page, t: Table, marks: list[dict]) -> Table | None:
    """The table rebuilt as the lists it sets side by side, or None where it does not."""
    if t.n_cols < 2 or t.n_rows < 3 or any(c.rowspan > 1 for c in t.cells):
        return None
    if not any(ch in MARKS for c in t.cells for ch in c.text):
        return None
    grid = {(c.row, c.col): c for c in t.cells}
    bands: dict[int, tuple[float, float]] = {}
    for c in t.cells:
        if c.bbox is not None and c.colspan == 1:
            x0, x1 = bands.get(c.col, (c.bbox.x0, c.bbox.x1))
            bands[c.col] = (min(x0, c.bbox.x0), max(x1, c.bbox.x1))
    if sorted(bands) != list(range(t.n_cols)):
        return None
    # The headings are the rows at the top the table marks as headings - but not one that opens with a tick or a cross,
    # which is an entry the finder took for a heading (POL1418DIR's page 28 opens its table with one).
    heads: list[int] = []
    for r in range(t.n_rows):
        row_cells = [c for c in t.cells if c.row == r]
        if not any(c.is_header for c in row_cells) or any(ch in MARKS for c in row_cells for ch in c.text):
            break
        heads.append(r)
    body = list(range(len(heads), t.n_rows))
    if not body:
        return None

    def text(r: int, col: int) -> str:
        cell = grid.get((r, col))
        return cell.text.strip() if cell is not None else ""

    marks_only = {col for col in bands if any(text(r, col) for r in body)
                  and all(text(r, col) in MARKS or not text(r, col) for r in body)}
    groups: list[list[int]] = []
    for col in range(t.n_cols):
        if groups and groups[-1][-1] in marks_only:
            groups[-1].append(col)
        else:
            groups.append([col])
    if groups[-1][-1] in marks_only:
        return None
    labels = {r for r in body if [col for col in range(t.n_cols) if text(r, col)] == [0]
              and not any(ch in MARKS for ch in text(r, 0))}
    sections: list[tuple[int | None, list[int]]] = []
    label: int | None = None
    rows: list[int] = []
    for r in body:
        if r not in labels:
            rows.append(r)
            continue
        if rows:
            sections.append((label, rows))
        elif label is not None:
            return None
        label, rows = r, []
    if not rows:
        return None
    sections.append((label, rows))

    n_cols = len(groups)
    out: list[TableCell] = []
    for r in heads:
        ci = 0
        while ci < n_cols:
            cell = next((c for c in t.cells if c.row == r and c.col <= groups[ci][0] < c.col + c.colspan), None)
            span = 1
            while cell is not None and ci + span < n_cols and cell.col <= groups[ci + span][0] < cell.col + cell.colspan:
                span += 1
            out.append(TableCell(text=cell.text if cell is not None else "", row=r, col=ci, colspan=span,
                                 bbox=cell.bbox if cell is not None else None, is_header=True))
            ci += span
    row = len(heads)
    kept: list[str] = []
    listed = False
    for label, rows in sections:
        if label is not None:
            lab = grid[(label, 0)]
            out.append(TableCell(text=lab.text, row=row, col=0, colspan=n_cols, bbox=lab.bbox, is_header=True))
            kept.append(lab.text)
            row += 1
        held = [grid[(r, col)] for r in rows for col in range(t.n_cols)
                if (r, col) in grid and grid[(r, col)].bbox is not None]
        y0, y1 = min(c.bbox.y0 for c in held), max(c.bbox.y1 for c in held)
        for ci, g in enumerate(groups):
            box = BBox(bands[g[0]][0], y0, bands[g[-1]][1], y1)
            lines = lines_in(page, box, marks)
            if not lines:
                out.append(TableCell(text="", row=row, col=ci, bbox=box))
                continue
            listing = build_listing(lines, least=1)
            if listing is None or listing.lead:
                return None
            words = _listing_words(listing)
            kept.append(words)
            listed = listed or is_list(listing)
            out.append(TableCell(text=words, row=row, col=ci, bbox=box, listing=listing if is_list(listing) else None))
        row += 1
    if not listed or _words(text(r, col) for r in body for col in range(t.n_cols)) != _words(kept):
        return None
    return Table(n_rows=row, n_cols=n_cols, cells=out, bbox=t.bbox, has_merged=True, provenance=t.provenance)
