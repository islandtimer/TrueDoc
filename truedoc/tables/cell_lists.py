"""A list set inside a table cell is written as a list (D028).

Kogan's home PDS page 29 draws its "What's covered?" column as boxes, and one box holds a whole ticked list: five
covers, one of them with a bulleted sub-list of appliances. A drawn box is read as one cell, and the cell ran the covers
together on one line. The owner ruled that the box is one cell and that a list inside it is written as a list: each
entry a list element with its tick or cross, a sub-list nested under the entry it belongs to, and a note that is not an
entry kept after the list. One row per entry was the other reading, and it was declined for what it would tell a
machine: two lists set side by side share rows only by their order, and a tool that reads each row as a record would
pair a cover with an exclusion the page never pairs.

The list is read from the page as it is set, in geometry alone:
- a line opening with a tick, a cross or a bullet - a word of its own, or a drawn mark just left of the line - opens an
  entry, and the entry's words start where the word after the mark starts: the hanging indent;
- a line starting at that indent carries the entry on, whatever its first word ("- $5,000 limit applies.");
- a mark set further in than the entry's own opens an item of a sub-list, carried on the same way;
- a line back at the entry's indent after its sub-list carries the entry on after it ("if it is caused directly by and
  occurs within 72 hours of an earthquake or tsunami", under BOM's four kinds of soil movement);
- a line starting left of the marks, back at the box's edge, is a note, and the list has ended (BOM's "An additional
  excess of $250 ... applies to each earthquake and/or tsunami"); so is a line left of the entry's indent after a
  paragraph's break (POL1418DIR's "You must report the incident to police", set where its tick starts), while a line
  wrapped back under its bullet with no break above carries the entry on.

A cell becomes a list with two entries or more, or one entry with a sub-list of two or more, and only when the words it
is read from say what its text says,
so nothing the cell says changes - only its shape. A bullet's own glyph is left to the list element; a tick or a cross
stays with its words, because it says whether the entry is covered.
"""
from __future__ import annotations

import re

from truedoc.model import BBox, Block, BlockKind, CellItem, CellList

TICKS = frozenset("✓✔✗✘☑☒")
BULLETS = frozenset("•◦▪‣·")
MARKS = TICKS | BULLETS | frozenset("●■□○")
SLACK = 0.3          # of a line's height: two lines start at one place when their starts are this close
EDGE = 1.0           # a line starting this far left of the entries' marks, or further, is out at the box's edge
PARAGRAPH = 0.4      # of a line's height: a gap this wide above a line, or wider, is a paragraph's break
MARK_TEXT = {"tick": "✓", "cross": "✗", "dot": "●", "circle": "○", "square": "■", "box": "□"}
_SPACE = re.compile(r"\s+")

Word = tuple[str, float, float, float, float]    # text, x0, x1, top, bottom


def lines_in(page, bbox: BBox, marks: list[dict] | None = None) -> list[list[Word]]:
    """The words whose centres fall in the box, one visual line to a list, left to right.

    Lines are grouped as the ruled finder groups a cell's text (`ruled_pdfium._cell_text`): text-layer lines whose bands
    overlap by more than half the shorter one are one line. A drawn mark inside the box (`page.meta["marks"]`) leads the
    line it sits beside, as `_attach_marks` placed it in the cell's text."""
    by_line: dict[int, list[Word]] = {}
    for li, line in enumerate(page.lines):
        if line.rotated:
            continue
        for w in line.words:
            if w.text.strip() and bbox.contains_point(w.bbox.cx, w.bbox.cy):
                by_line.setdefault(li, []).append((w.text, w.bbox.x0, w.bbox.x1, w.bbox.y0, w.bbox.y1))
    bands = sorted(((min(w[3] for w in ws), max(w[4] for w in ws), ws) for ws in by_line.values()), key=lambda b: b[0])
    rows: list[list[Word]] = []
    band: tuple[float, float] | None = None
    for y0, y1, ws in bands:
        if band is not None and min(band[1], y1) - max(band[0], y0) > 0.5 * min(band[1] - band[0], y1 - y0):
            rows[-1].extend(ws)
            band = (min(band[0], y0), max(band[1], y1))
        else:
            rows.append(list(ws))
            band = (y0, y1)
    rows = [sorted(ws, key=lambda w: w[1]) for ws in rows]
    for m in marks or ():
        text = MARK_TEXT.get(m.get("kind", ""))
        x0, y0, x1, y1 = m["bbox"]
        if text is None or not bbox.contains_point((x0 + x1) / 2.0, (y0 + y1) / 2.0):
            continue
        cy = (y0 + y1) / 2.0
        beside = [ws for ws in rows if min(w[3] for w in ws) <= cy <= max(w[4] for w in ws) and ws[0][1] >= x1 - 1.0]
        if beside:
            line = min(beside, key=lambda ws: ws[0][1] - x1)
            if line[0][0] not in MARKS:
                line.insert(0, (text, x0, x1, y0, y1))
    return rows


def _join(*parts: str) -> str:
    return " ".join(p for p in parts if p)


def build_listing(lines: list[list[Word]], least: int = 2) -> CellList | None:
    """The lines read as a list, or None where they hold fewer than `least` entries."""
    lead: list[str] = []
    items: list[CellItem] = []
    note: list[str] = []
    top: tuple[float, float] | None = None       # the open entry's mark and indent
    sub: tuple[float, float] | None = None       # the open sub-item's mark and indent
    bottom: float | None = None                  # the foot of the line above
    for ws in lines:
        x = ws[0][1]
        line_top, line_bottom = min(w[3] for w in ws), max(w[4] for w in ws)
        height = line_bottom - line_top
        gap = line_top - bottom if bottom is not None else 0.0
        bottom = line_bottom
        slack = max(1.0, SLACK * height)
        words = [w[0] for w in ws]
        if note:
            note.append(" ".join(words))
            continue
        if ws[0][0] in MARKS and len(ws) >= 2:
            text = " ".join(words[1:] if ws[0][0] in BULLETS else words)
            if top is not None and x > top[0] + slack and items:
                items[-1].children.append(text)
                sub = (x, ws[1][1])
            else:
                items.append(CellItem(text=text))
                top, sub = (x, ws[1][1]), None
            continue
        line = " ".join(words)
        if top is None:
            lead.append(line)
        elif sub is not None and abs(x - sub[1]) <= slack:
            items[-1].children[-1] = _join(items[-1].children[-1], line)
        elif x >= top[0] - EDGE and (x >= top[1] - slack or gap < PARAGRAPH * height):
            # At the entry's indent, or wrapped back under its mark with no break above: the entry carries on - after its
            # sub-list, if it has one, and closing that sub-list. A line clearly left of the marks is back at the box's
            # edge (BOM's note starts 2.8pt left of its ticks, closer than a line's slack), and a line left of the indent
            # after a paragraph's break is a note too.
            if items[-1].children:
                items[-1].tail = _join(items[-1].tail, line)
            else:
                items[-1].text = _join(items[-1].text, line)
            sub = None
        else:
            note.append(line)
    if len(items) < least:
        return None
    return CellList(items=items, lead=" ".join(lead), note=" ".join(note))


def is_list(listing: CellList) -> bool:
    """Is the listing a list to be shown as one: two entries or more, or an entry with a sub-list of two or more
    ("Loss or damage caused by impact from:" over five kinds of impact, on POL1418DIR's page 28)?"""
    return len(listing.items) >= 2 or any(len(item.children) >= 2 for item in listing.items)


def _plain(text: str) -> str:
    """Text as a cell compares it: bullets gone, space collapsed."""
    return _SPACE.sub(" ", "".join(" " if ch in BULLETS else ch for ch in text)).strip()


def flat_text(listing: CellList) -> str:
    parts = [listing.lead]
    for item in listing.items:
        parts += [item.text, *item.children, item.tail]
    parts.append(listing.note)
    return _plain(" ".join(p for p in parts if p))


def list_cells(page, blocks: list[Block]) -> None:
    """Each table cell whose box holds a list set as a list gets that list (`TableCell.listing`)."""
    marks = [m for m in page.meta.get("marks", []) if m.get("kind") in MARK_TEXT]
    for b in blocks:
        if b.kind != BlockKind.TABLE or b.table is None:
            continue
        for cell in b.table.cells:
            if cell.bbox is None or cell.listing is not None or not any(ch in MARKS for ch in cell.text):
                continue
            listing = build_listing(lines_in(page, cell.bbox, marks), least=1)
            if listing is not None and is_list(listing) and flat_text(listing) == _plain(cell.text):
                cell.listing = listing
