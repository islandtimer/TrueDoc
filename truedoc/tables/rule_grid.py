"""A table a layout model sees but the text cannot build, read from the page's own rules.

QBE's home PDS page 16 sets a table of which cover each change concerns: a column of situations beside two columns under
"If you have buildings cover" and "If you have contents cover" that hold nothing but a drawn tick or cross. The layout
model boxes it as a table (0.95), but a table is built from the text lines inside the box, and the two mark columns hold
no text, so none came out: the rows read as headings and paragraphs, and the eight marks - read correctly by
`truedoc/marks.py` - had no cell to go to. The page draws no vertical rules either. What it does draw is a rule under the
header and one under every row, each rule stroked in pieces that meet at the two column edges, at the same x on every row.

`table_from_rules` reads that drawing inside a confident table region: the rows are the bands between consecutive rules,
with the text above the first rule as the header, the columns are the x positions where the pieces of at least three rules
meet, and each word goes to the cell its centre falls in - so a wrapped entry stays whole, and a header line the text layer
runs across two columns is divided where the columns divide. It is asked only where the model is confident of a table and
the text builds none, because pieces meeting at a shared x are also how pages draw their decoration: a census found such
joins on 3,213 of the insurance library's 23,870 pages, most of them nowhere near a table.

RAC's premium, excess and discount guide sets the same kind of table on its first page - pricing factors beside columns
of ticks under "Buildings" and "Contents" - and draws it another way. Each rule is dotted and stroked in three pieces
that stop 1.5pt short of one another at the column edges, and the header sits in a filled band with no rule under it.
Pieces that met only by touching found no column edge there, and the first rule lies under the first row, so that row
would have joined the header. Pieces that stop short of one another by less than a word space meet, and a filled band
drawn across the table divides its rows as a rule does wherever it has text on both sides.
"""
from __future__ import annotations

from truedoc.extract import pdfium_objects
from truedoc.model import BBox, Page, Table, TableCell
from truedoc.tables.aligned import _join_lines

_GAP = 0.25         # the next piece starts no more than this many text sizes after the last one ends: a word space
_OVERLAP = 3.0      # ... or overlaps it by no more than this
_MIN_PIECE = 10.0   # a dash of a dashed rule is not a piece of a rule
_SAME_Y = 0.75      # pieces within this of one another in y make one rule
_SAME_X = 1.5       # joins within this of one another in x make one column edge
_MIN_RULES = 3      # a column edge is where the pieces of at least this many rules meet
_SLACK = 3.0        # how far outside the region a rule may start or end


def _rules(pdf_page, region: BBox) -> tuple[list[list[dict]], list[dict]]:
    """The horizontal rules inside the region, each a list of its pieces, and the vertical rules there.

    Read as the ruled finder reads them (`ruled_pdfium._edges_from_objects`), before anything joins a rule's pieces."""
    from truedoc.tables import ruled_pdfium as rp

    objs = pdfium_objects.page_objects(pdf_page.parent.name, pdf_page.number + 1)
    if not objs:
        return [], []
    M = pdf_page.rotation_matrix if pdf_page.rotation else None
    edges = rp._clip_to_page(rp._edges_from_objects(objs, M),
                             (0.0, 0.0, float(pdf_page.rect.width), float(pdf_page.rect.height)))

    def within(e: dict) -> bool:
        return (region.x0 - _SLACK <= e["x0"] and e["x1"] <= region.x1 + _SLACK
                and region.y0 - _SLACK <= e["top"] <= region.y1 + _SLACK)

    pieces = sorted((e for e in edges if e["orientation"] == "h" and e["x1"] - e["x0"] >= _MIN_PIECE and within(e)),
                    key=lambda e: (e["top"], e["x0"]))
    verticals = [e for e in edges if e["orientation"] == "v" and within(e)]
    rules: list[list[dict]] = []
    for e in pieces:
        if rules and abs(rules[-1][0]["top"] - e["top"]) <= _SAME_Y:
            rules[-1].append(e)
        else:
            rules.append([e])
    return rules, verticals


def _column_edges(rules: list[list[dict]], verticals: list[dict], gap: float) -> list[float]:
    """Where the pieces of at least `_MIN_RULES` rules meet at one x, with no vertical rule drawn there.

    A piece meets the next where it overlaps it a little or stops short of it by no more than `gap`."""
    joins: list[tuple[float, float]] = []
    for rule in rules:
        ordered = sorted(rule, key=lambda e: e["x0"])
        for a, b in zip(ordered, ordered[1:]):
            if -_OVERLAP <= b["x0"] - a["x1"] <= gap:
                joins.append(((a["x1"] + b["x0"]) / 2.0, round(a["top"], 1)))
    joins.sort()
    edges: list[float] = []
    group: list[tuple[float, float]] = []
    for x, y in joins + [(float("inf"), 0.0)]:
        if group and x - group[-1][0] > _SAME_X:
            ys = sorted({g[1] for g in group})
            at = sum(g[0] for g in group) / len(group)
            # A vertical rule standing at the join is a ruled grid, and the ruled finder's business.
            drawn = any(abs(v["x0"] - at) <= 2.0 and v["top"] <= ys[-1] and v["bottom"] >= ys[0] for v in verticals)
            if len(ys) >= _MIN_RULES and not drawn:
                edges.append(at)
            group = []
        group.append((x, y))
    return edges


def _band_edges(pdf_page, region: BBox, left: float, right: float, size: float) -> list[float]:
    """The top and bottom of every filled shape drawn inside the region across the table - from within a text size of
    its left end to within a text size of its right - in order."""
    from truedoc.tables import ruled_pdfium as rp

    M = pdf_page.rotation_matrix if pdf_page.rotation else None
    ys: list[float] = []
    for o in pdfium_objects.page_objects(pdf_page.parent.name, pdf_page.number + 1) or []:
        if o.kind != "path" or o.fill is None or o.fill_alpha <= 0.0:
            continue
        x0, y0, x1, y1 = rp._turned(o.bbox, M)
        if x0 < region.x0 - _SLACK or x1 > region.x1 + _SLACK or x0 > left + size or x1 < right - size:
            continue
        ys.extend(y for y in (y0, y1) if region.y0 - _SLACK <= y <= region.y1 + _SLACK)
    return sorted(ys)


def table_from_rules(page: Page, pdf_page, region: BBox, size: float) -> tuple[Table, list] | None:
    """The table the region's own rules describe, with the lines it takes, or None where they describe none."""
    try:
        rules, verticals = _rules(pdf_page, region)
    except Exception:
        return None
    if len(rules) < 2:
        return None
    size = size or 10.0
    left = min(p["x0"] for rule in rules for p in rule)
    right = max(p["x1"] for rule in rules for p in rule)
    xs = [x for x in _column_edges(rules, verticals, _GAP * size) if left + size < x < right - size]
    if not xs:
        return None
    ys = [sum(p["top"] for p in rule) / len(rule) for rule in rules]
    lines = sorted((l for l in page.lines if not l.rotated and region.contains_point(l.bbox.cx, l.bbox.cy)),
                   key=lambda l: (round(l.bbox.cy, 1), l.bbox.x0))
    words = [(li, w) for li, l in enumerate(lines) for w in l.words if w.text.strip() and left <= w.bbox.cx <= right]
    # A filled band drawn across the table divides its rows as a rule does, where there is text between its edge and
    # the rule or edge either side of it: RAC's header band ends above the first row, and the first rule lies under that
    # row. Above the last rule only, so the rules still close the table.
    centres = [w.bbox.cy for _, w in words]
    try:
        band_edges = _band_edges(pdf_page, region, left, right, size)
    except Exception:
        band_edges = []
    for y in band_edges:
        if y >= ys[-1] or any(abs(y - c) <= _SAME_Y for c in ys):
            continue
        before = max((c for c in ys if c < y), default=float("-inf"))
        after = min(c for c in ys if c > y)
        if any(before < c < y for c in centres) and any(y < c < after for c in centres):
            ys = sorted(ys + [y])
    above = [w for _, w in words if w.bbox.cy < ys[0]]
    bands = ([(min(w.bbox.y0 for w in above), ys[0])] if above else []) + list(zip(ys, ys[1:]))
    cols = [left] + xs + [right]
    grid: list[list[str]] = []
    for top, bottom in bands:
        row: list[str] = []
        for c0, c1 in zip(cols, cols[1:]):
            pieces: dict[int, list[str]] = {}
            placed: list[tuple[str, BBox]] = []
            for li, w in words:
                if c0 <= w.bbox.cx <= c1 and top <= w.bbox.cy <= bottom:
                    # A word reported twice at one place is one word to a reader. On QBE's page 11 the reader gives
                    # "contents cover" both inside the header line "buildings cover contents cover" and as a line of
                    # its own, where the file draws it once.
                    if any(t == w.text and abs(b.x0 - w.bbox.x0) < 0.5 and abs(b.y0 - w.bbox.y0) < 0.5 for t, b in placed):
                        continue
                    placed.append((w.text, w.bbox))
                    pieces.setdefault(li, []).append(w.text)
            text = ""
            for li in sorted(pieces):
                text = _join_lines(text, " ".join(pieces[li]))
            row.append(text)
        grid.append(row)
    n_cols = len(cols) - 1
    header = 1 if above else 0
    # Every column holds something (a mark column's heading counts), and at least two rows below the header hold text.
    if not all(any(grid[r][c] for r in range(len(grid))) for c in range(n_cols)):
        return None
    if sum(1 for r in range(header, len(grid)) if any(grid[r])) < 2:
        return None
    cells = [TableCell(text=grid[r][c], row=r, col=c, bbox=BBox(cols[c], bands[r][0], cols[c + 1], bands[r][1]),
                       is_header=r < header)
             for r in range(len(grid)) for c in range(n_cols)]
    bbox = BBox(left, bands[0][0], right, ys[-1])
    taken = [l for l in lines if bbox.contains_point(l.bbox.cx, l.bbox.cy)]
    return Table(n_rows=len(grid), n_cols=n_cols, cells=cells, bbox=bbox, provenance="layout-table-rules"), taken
