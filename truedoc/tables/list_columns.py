"""Lists set side by side are written as lists, not as rows cut from their lines (D028, D042).

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
section's label, and a row for each section whose cells hold the lists - where every column of every section opens
with an entry, one column somewhere is a list (`cell_lists.is_list`), and the rebuilt table holds exactly the words the
old one held.

The same cut, more widely (D042, 23 September): a covered list beside a not-covered list under a label
set beside them ("Buildings", 23 printed lines down), a when / how much / what's-not-covered table whose columns each
open with a sentence before their bullets, features divided by a rule with prose and lists in every column. A column
may then open with words before its entries (`CellList.lead`), end with words after them (`note`), or hold no entry at
all (its words, joined). So wide a reading is taken only where the page shows the rows are its printed lines and not
records: an entry of one column carried on beside the line where another column opens an entry of its own. A table
whose rows are records starts its cells level, and is left as it is. And the rows the page does draw are kept: a rule
drawn across the table under its top rows ends the headings, one drawn across it lower down divides two sections, and
a short label in the first column, beside lists with no mark of its own, heads the section it stands level with.

Read on 45 pages of the owner's library before it was kept: an entry may open inside a cell the finder built of
several lines, a cell of marks run together ("• •") is marks, a heading the finder split over a marks column is one
heading, a label's "(continued...)" is the label's, and a line opening in lower case ("such as:") heads nothing.
"""
from __future__ import annotations

import collections

from truedoc.model import BBox, Block, BlockKind, CellList, Table, TableCell
from truedoc.tables.cell_lists import BULLETS, MARK_TEXT, MARKS, PARAGRAPH, SLACK, build_listing, is_list, lines_in

TEXT_BUILT = ("textlayer-aligned", "layout-table")
RULE_SPAN = 0.9       # a drawn rule divides the table where its pieces cover this share of its width
RULE_LEVEL = 1.5      # pieces of one rule lie within this of each other's height (pt)
LABEL_WORDS = 8       # a label set beside lists: this many words at most ...
LABEL_LINES = 3       # ... on this many printed lines at most


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


def _rules_across(page, box: BBox) -> list[float]:
    """The heights inside the box at which drawn rules cross its whole width, the pieces of one rule taken together (a
    table's rule is often drawn a column at a time)."""
    pieces = sorted(((d.bbox.y0 + d.bbox.y1) / 2.0, max(d.bbox.x0, box.x0), min(d.bbox.x1, box.x1))
                    for d in getattr(page, "drawings", ()) if d.kind == "hline")
    out: list[float] = []
    i = 0
    while i < len(pieces):
        j = i
        while j + 1 < len(pieces) and pieces[j + 1][0] - pieces[i][0] <= RULE_LEVEL:
            j += 1
        y = pieces[i][0]
        covered, reach = 0.0, box.x0
        for _y, x0, x1 in sorted(pieces[i:j + 1], key=lambda p: p[1]):
            if x1 > reach:
                covered += x1 - max(x0, reach)
                reach = x1
        if box.y0 < y < box.y1 and covered >= RULE_SPAN * box.width:
            out.append(y)
        i = j + 1
    return out


def _marks_only(text: str) -> bool:
    """A cell holding nothing but marks - one, or several the finder ran together ("• •")."""
    return all(w in MARKS for w in text.split())


def _crossing(rows: list[int], groups: list[list[int]], text) -> bool:
    """Does an entry of one column carry on beside a row where another column opens an entry? Then the rows are the
    page's printed lines, not records: a record starts its cells level. An entry may open inside a cell, after words
    that lead up to it, and a row that opens with words and no mark carries on the entry open above it."""
    starts: dict[int, list[int]] = {}
    spans: list[tuple[int, int, int]] = []
    for gi, g in enumerate(groups):
        start = last = None
        for r in rows:
            words = " ".join(t for t in (text(r, col) for col in g) if t).split()
            if not words:
                continue
            if words[0] not in MARKS and start is not None:
                last = r
            if any(w in MARKS for w in words):
                if start is not None and last > start:
                    spans.append((gi, start, last))
                starts.setdefault(gi, []).append(r)
                start = last = r
        if start is not None and last > start:
            spans.append((gi, start, last))
    return any(start < r <= last for gi, start, last in spans for gj, rs in starts.items() if gj != gi for r in rs)


def _label_blocks(page, box: BBox, marks) -> list[tuple[float, str]] | None:
    """The labels a first column sets beside lists, each as (its top, its words): blocks of lines apart by a paragraph's
    gap, each short. None where the column holds anything longer - it is a column of its own, not labels."""
    lines = lines_in(page, box, marks)
    if not lines:
        return []
    blocks: list[list[list]] = []
    bottom = None
    for ws in lines:
        top, foot = min(w[3] for w in ws), max(w[4] for w in ws)
        if bottom is None or top - bottom >= PARAGRAPH * (foot - top):
            blocks.append([])
        blocks[-1].append(ws)
        bottom = foot
    # A block opening in lower case or with a bracket carries the label above it on ("Contents" over "(continued...)").
    joined: list[list[list]] = []
    for block in blocks:
        first = block[0][0][0][:1]
        if joined and (first.islower() or first in "(["):
            joined[-1].extend(block)
        else:
            joined.append(block)
    out = []
    for block in joined:
        words = [w[0] for ws in block for w in ws]
        if len(block) > LABEL_LINES or len(words) > LABEL_WORDS or any(w in MARKS for w in words):
            return None
        out.append((min(w[3] for w in block[0]), " ".join(words)))
    return out


def side_by_side(page, t: Table, marks: list[dict]) -> Table | None:
    """The table rebuilt as the lists it sets side by side, or None where it does not."""
    if t.n_cols < 2 or t.n_rows < 3 or any(c.rowspan > 1 and c.col != 0 for c in t.cells):
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

    def text(r: int, col: int) -> str:
        cell = grid.get((r, col))
        return cell.text.strip() if cell is not None else ""

    extents: dict[int, tuple[float, float]] = {}
    for c in t.cells:
        if c.rowspan == 1 and c.bbox is not None and c.text.strip():
            y0, y1 = extents.get(c.row, (c.bbox.y0, c.bbox.y1))
            extents[c.row] = (min(y0, c.bbox.y0), max(y1, c.bbox.y1))
    rules = _rules_across(page, t.bbox)

    def ruled_before(r: int) -> bool:
        """A rule drawn across the table between row r and the filled row above it."""
        above = next((extents[q] for q in range(r - 1, -1, -1) if q in extents), None)
        return r in extents and above is not None and any(above[1] <= y <= extents[r][0] for y in rules)

    # The headings are the rows at the top the table marks as headings - but not one that opens with a tick or a cross,
    # which is an entry the finder took for a heading (POL1418DIR's page 28 opens its table with one) unless a rule
    # drawn across the table sets it apart as a heading ("✓ Covered" over the lists it heads).
    heads: list[int] = []
    for r in range(t.n_rows):
        row_cells = [c for c in t.cells if c.row == r]
        if not any(c.is_header for c in row_cells) or any(ch in MARKS for c in row_cells for ch in c.text):
            break
        heads.append(r)
    ruled = next((r for r in range(1, t.n_rows) if ruled_before(r)), None)
    wider = ruled is not None and ruled > len(heads) and all(any(c.is_header for c in t.cells if c.row == r)
                                                              for r in range(ruled))
    if wider:
        heads = list(range(ruled))
    body = list(range(len(heads), t.n_rows))
    if not body:
        return None

    marks_only = {col for col in bands if any(text(r, col) for r in body) and all(_marks_only(text(r, col)) for r in body)}
    groups: list[list[int]] = []
    for col in range(t.n_cols):
        if groups and groups[-1][-1] in marks_only:
            groups[-1].append(col)
        else:
            groups.append([col])
    if groups[-1][-1] in marks_only:
        return None
    # A label starts at the column's edge, where its entries' marks do; a line alone in its row further in, at their
    # hanging indent, carries an entry on.
    edge = [ws[0] for ws in lines_in(page, BBox(bands[0][0], t.bbox.y0, bands[0][1], t.bbox.y1), marks)
            if ws[0][0] in MARKS]

    def at_the_edge(r: int) -> bool:
        cell = grid[(r, 0)]
        ws = lines_in(page, cell.bbox, marks) if cell.bbox is not None and edge else []
        return not ws or ws[0][0][1] <= min(w[1] for w in edge) + max(1.0, SLACK * (ws[0][0][4] - ws[0][0][3]))

    # And a line opening in lower case carries a sentence on ("such as:", before the list it leads into).
    labels = {r for r in body if [col for col in range(t.n_cols) if text(r, col)] == [0]
              and not any(ch in MARKS for ch in text(r, 0)) and not text(r, 0)[:1].islower() and at_the_edge(r)}
    sections: list[tuple[int | None, list[int]]] = []
    label: int | None = None
    rows: list[int] = []
    for r in body:
        if r in labels:
            if rows:
                sections.append((label, rows))
            elif label is not None:
                return None
            label, rows = r, []
            continue
        if rows and ruled_before(r):
            sections.append((label, rows))
            label, rows = None, []
        rows.append(r)
    if not rows:
        return None
    sections.append((label, rows))

    n_cols = len(groups)
    out: list[TableCell] = []
    for r in heads:
        # A heading is every cell of the row over the column's words and its marks ("We" over the bullets, "do not
        # cover" over the words), and one heading spanning several columns spans them still.
        row_cells = sorted((c for c in t.cells if c.row == r), key=lambda c: c.col)
        ci = 0
        while ci < n_cols:
            cols, span = set(groups[ci]), 1
            while True:
                here = [c for c in row_cells if any(c.col <= k < c.col + c.colspan for k in cols)]
                reach = max((c.col + c.colspan - 1 for c in here), default=-1)
                if ci + span < n_cols and groups[ci + span][0] <= reach:
                    cols |= set(groups[ci + span])
                    span += 1
                    continue
                break
            out.append(TableCell(text=" ".join(c.text.strip() for c in here if c.text.strip()), row=r, col=ci,
                                 colspan=span, bbox=BBox.union_all(c.bbox for c in here if c.bbox is not None),
                                 is_header=True))
            ci += span
    row = len(heads)
    kept: list[str] = []
    # Read as D028 first read it - every column of every section opening with an entry - the table needs no more
    # evidence; read more widely, it needs the rows shown to be printed lines (`_crossing`).
    listed, strict = False, not wider
    for label, rows in sections:
        if label is not None:
            lab = grid[(label, 0)]
            out.append(TableCell(text=lab.text, row=row, col=0, colspan=n_cols, bbox=lab.bbox, is_header=True))
            kept.append(lab.text)
            row += 1
        held = [grid[(r, col)] for r in rows for col in range(t.n_cols)
                if (r, col) in grid and grid[(r, col)].bbox is not None]
        y0, y1 = min(c.bbox.y0 for c in held), max(c.bbox.y1 for c in held)
        # A first column of short labels beside lists, with no mark of its own, heads the parts of the section it
        # stands level with: each label and the lists beside it are one row.
        parts: list[tuple[float, float, str | None]] = [(y0, y1, None)]
        if len(groups[0]) == 1 and n_cols > 1:
            found = _label_blocks(page, BBox(bands[0][0], y0, bands[0][1], y1), marks)
            if found:
                strict = False
                tops = [top for top, _ in found]
                tops[0] = y0
                parts = [(top, tops[i + 1] if i + 1 < len(tops) else y1, words)
                         for i, (top, (_t, words)) in enumerate(zip(tops, found))]
        for p0, p1, side in parts:
            first = 0
            if side is not None:
                out.append(TableCell(text=side, row=row, col=0, bbox=BBox(bands[0][0], p0, bands[0][1], p1)))
                kept.append(side)
                first = 1
            for ci in range(first, n_cols):
                g = groups[ci]
                box = BBox(bands[g[0]][0], p0, bands[g[-1]][1], p1)
                lines = lines_in(page, box, marks)
                if not lines:
                    out.append(TableCell(text="", row=row, col=ci, bbox=box))
                    continue
                listing = build_listing(lines, least=1)
                if listing is None:
                    strict = False
                    words = " ".join(w[0] for ws in lines for w in ws)
                    out.append(TableCell(text=words, row=row, col=ci, bbox=box))
                    kept.append(words)
                    continue
                strict = strict and not listing.lead
                listed = listed or is_list(listing)
                # A list is written as a list; one entry is not a list, and keeps its mark where it stands.
                words = _listing_words(listing) if is_list(listing) else " ".join(w[0] for ws in lines for w in ws)
                kept.append(words)
                out.append(TableCell(text=words, row=row, col=ci, bbox=box, listing=listing if is_list(listing) else None))
            row += 1
    if not listed or _words(text(r, col) for r in body for col in range(t.n_cols)) != _words(kept):
        return None
    if not strict and not _crossing(body, groups, text):
        return None
    return Table(n_rows=row, n_cols=n_cols, cells=out, bbox=t.bbox, has_merged=True, provenance=t.provenance)
