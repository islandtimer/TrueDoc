"""Unruled ("whitespace") table extraction from text-layer geometry.

Most tables in real documents have no ruling lines: the cells are just text
aligned in columns. This module finds vertical runs of lines whose segments
line up in columns, works out the column boundaries from the whitespace
channels that run through the whole region, and assigns each text segment to
a cell. Characters come straight from the text layer, so cell content is
exact; only the structure is inferred.
"""

from __future__ import annotations

import collections
import re
from dataclasses import dataclass, field

from truedoc.model import BBox, Block, BlockKind, Line, Page, Table, TableCell

_NUMERIC = re.compile(
    r"^[\(\[]?[-+−–<>≤≥↑↓~≈]?\s*[\d.,]+\s*(?:[±+\-−]\s*[\d.,]+)?\s*%?[\)\]]?[*†‡a-z]{0,2}$|^[-–—]$|^n/?a$|^n\.?s\.?$|^\d+[\d.,]*\s*[×x]\s*10[-−]?\d*$"
    # a value with its error or count in parentheses: "−.25 (.23)", "7.90 (3.07)", "12 (4.5%)"
    r"|^[-+−]?[\d.,]+\s*%?\s*\([-+−]?[\d.,]+\s*%?\)[*†‡a-z]{0,2}$",
    re.IGNORECASE,
)


@dataclass
class _Row:
    segments: list[Line]
    y0: float
    y1: float

    @property
    def cy(self) -> float:
        return (self.y0 + self.y1) / 2.0


@dataclass
class _Candidate:
    rows: list[_Row]
    bbox: BBox
    columns: list[tuple[float, float]] = field(default_factory=list)


def find_aligned_tables(page: Page, lines: list[Line], body_size: float) -> tuple[list[Block], list[Line]]:
    """Return (table blocks, lines not consumed by any table)."""
    size = body_size or 10.0
    all_lines = list(lines)
    # Running headers and footers never belong to a table.
    top_zone = 0.09 * page.height
    bottom_zone = page.height - 0.09 * page.height
    lines = [l for l in lines if not l.rotated and not (l.bbox.y1 <= top_zone or l.bbox.y0 >= bottom_zone)]
    rows = _cluster_rows(lines, size)
    candidates = _find_runs(rows, size)
    tables: list[Block] = []
    consumed: set[int] = set()
    for cand in candidates:
        for sub in _split_side_by_side(cand, size):
            table = _build_table(sub, size)
            if table is None:
                continue
            tables.append(Block(kind=BlockKind.TABLE, bbox=table.bbox, table=table, provenance="textlayer-aligned", confidence=0.7))
            for r in sub.rows:
                for seg in r.segments:
                    consumed.add(id(seg))
    remaining = [l for l in all_lines if id(l) not in consumed]
    return tables, remaining


def table_from_lines(lines: list[Line], size: float, trusted: bool = False, extent: BBox | None = None) -> Table | None:
    """Build a table from the lines inside a known table region (e.g. from a layout model).

    `trusted` means the region came from a confident detector: the prose
    rejections (meant for paragraphs mistaken for word grids) are skipped, so a
    table of long wrapped cells survives. `extent` is the region's own box: the
    column channels are looked for across it, so a narrow last column is not
    lost when the lines happen to stop short of the box's edge.
    """
    lines = [l for l in lines if not l.rotated]
    if len(lines) < 3:
        return None
    rows = _cluster_rows(lines, size or 10.0)
    if len(rows) < 2:
        return None
    bbox = BBox.union_all(seg.bbox for r in rows for seg in r.segments)
    if extent is not None:
        bbox = BBox(min(bbox.x0, extent.x0), bbox.y0, max(bbox.x1, extent.x1), bbox.y1)
    cand = _Candidate(rows=rows, bbox=bbox)
    return _build_table(cand, size or 10.0, strict=False, trusted=trusted)


def _cluster_rows(lines: list[Line], size: float) -> list[_Row]:
    rows: list[_Row] = []
    for line in sorted(lines, key=lambda l: (l.bbox.cy, l.bbox.x0)):
        tol = 0.45 * max(size, line.size or size)
        if rows and abs(line.bbox.cy - rows[-1].cy) <= tol:
            r = rows[-1]
            r.segments.append(line)
            r.y0 = min(r.y0, line.bbox.y0)
            r.y1 = max(r.y1, line.bbox.y1)
        else:
            rows.append(_Row(segments=[line], y0=line.bbox.y0, y1=line.bbox.y1))
    for r in rows:
        r.segments.sort(key=lambda l: l.bbox.x0)
    return rows


def _is_multicell(row: _Row, size: float) -> bool:
    if len(row.segments) < 2:
        return False
    # At least one real gap between segments.
    for a, b in zip(row.segments, row.segments[1:]):
        if b.bbox.x0 - a.bbox.x1 >= 0.8 * size:
            return True
    return False


_CAPTION_LIKE = re.compile(r"^\s*(table|tab\.|fig\.?|figure|exhibit|chart|scheme|appendix|source|note)s?\b", re.I)


def _run_width(run: list[_Row]) -> float:
    multi = [r for r in run if len(r.segments) >= 2]
    if not multi:
        return 0.0
    return max(s.bbox.x1 for r in multi for s in r.segments) - min(s.bbox.x0 for r in multi for s in r.segments)


def _heading_fragment(row: _Row, run: list[_Row], size: float) -> bool:
    """A lone narrow line just above a table's first multi-cell row: the upper
    line of a stacked column heading ("Number of Agreement" over "(ranked 3 or
    4)"), not a caption running across the table."""
    if len(row.segments) != 1 or len(run) < 2:
        return False
    seg = row.segments[0]
    text = seg.text.strip()
    width = _run_width(run)
    # A title over the table ("t Distribution" centred over three headings, "In
    # relationship to others I feel:") sits over words of the first row; a
    # heading fragment sits over an empty stretch of it.
    below = [w for s in run[1].segments for w in s.words if w.bbox.x0 < seg.bbox.x1 and w.bbox.x1 > seg.bbox.x0]
    return (width > 0 and seg.bbox.width < 0.5 * width and not _CAPTION_LIKE.match(text)
            and not below and not text.endswith((":", ".", ";", "?", "!")) and len(text.split()) <= 6
            and -0.6 * size <= run[1].y0 - row.y1 <= 1.5 * size)


def _wrapped_label(row: _Row, run: list[_Row], size: float) -> bool:
    """A lone lowercase line at the table's left edge just under its last row:
    the second line of the last row's label ("Slaapkwaliteit tijdens" /
    "consignatiediensten"), not a note under the table."""
    if len(row.segments) != 1 or len(run) < 2:
        return False
    seg = row.segments[0]
    width = _run_width(run)
    multi = [r for r in run if len(r.segments) >= 2]
    left = min(s.bbox.x0 for r in multi for s in r.segments) if multi else seg.bbox.x0
    text = seg.text.strip()
    return (width > 0 and seg.bbox.width < 0.5 * width and abs(seg.bbox.x0 - left) <= size
            and text[:1].islower() and -0.6 * size <= row.y0 - run[-2].y1 <= 1.2 * size)


def _find_runs(rows: list[_Row], size: float) -> list[_Candidate]:
    """Group vertically adjacent rows into candidate table regions."""
    candidates: list[_Candidate] = []
    run: list[_Row] = []
    singles_in_a_row = 0
    pending: _Row | None = None   # the lone row just before a run: a heading fragment, perhaps

    def close():
        nonlocal run, singles_in_a_row
        # Trim single-segment rows at both ends, except a heading fragment above
        # the first multi-cell row and a wrapped label under the last.
        while run and not _is_multicell(run[0], size):
            if _heading_fragment(run[0], run, size):
                break
            run.pop(0)
        while run and not _is_multicell(run[-1], size):
            if _wrapped_label(run[-1], run, size):
                break
            run.pop()
        multi = sum(1 for r in run if _is_multicell(r, size))
        if len(run) >= 3 and multi >= max(3, int(0.6 * len(run))):
            bbox = BBox.union_all(seg.bbox for r in run for seg in r.segments)
            candidates.append(_Candidate(rows=list(run), bbox=bbox))
        elif len(run) == 2 and multi == 2 and all(len(r.segments) >= 3 for r in run):
            bbox = BBox.union_all(seg.bbox for r in run for seg in r.segments)
            candidates.append(_Candidate(rows=list(run), bbox=bbox))
        run = []
        singles_in_a_row = 0

    for row in rows:
        if run and row.y0 - run[-1].y1 > 1.8 * size:
            close()
        if not run:
            if _is_multicell(row, size):
                if pending is not None and -0.6 * size <= row.y0 - pending.y1 <= 1.5 * size:
                    run.append(pending)
                run.append(row)
                pending = None
            else:
                pending = row   # a lone row outside any run, remembered in case a table starts under it
            continue
        if _is_multicell(row, size):
            run.append(row)
            singles_in_a_row = 0
        else:
            singles_in_a_row += 1
            if singles_in_a_row > 1:
                close()
                pending = row   # the lone row that ended this run may head the next table
            else:
                run.append(row)
    close()
    return candidates


def _channels(rows: list[_Row], x0: float, x1: float, size: float) -> list[tuple[float, float]]:
    """Whitespace channels running vertically through (nearly) all rows."""
    width = int(x1 - x0) + 2
    if width <= 0:
        return []
    cover = [0] * width
    for r in rows:
        marked = set()
        for seg in r.segments:
            a = max(0, int(seg.bbox.x0 - x0))
            b = min(width - 1, int(seg.bbox.x1 - x0))
            for i in range(a, b + 1):
                marked.add(i)
        for i in marked:
            cover[i] += 1
    n = len(rows)
    limit = max(1, int(0.2 * n)) if n >= 5 else 0
    channels: list[tuple[float, float]] = []
    i = 0
    while i < width:
        if cover[i] <= limit:
            j = i
            while j + 1 < width and cover[j + 1] <= limit:
                j += 1
            if i > 0 and j < width - 1 and (j - i + 1) >= 0.6 * size:
                channels.append((x0 + i, x0 + j + 1))
            i = j + 1
        else:
            i += 1
    return channels


def _split_side_by_side(cand: _Candidate, size: float) -> list[_Candidate]:
    """Split a region into separate tables where a much wider whitespace channel divides it."""
    channels = _channels(cand.rows, cand.bbox.x0, cand.bbox.x1, size)
    if len(channels) < 3:
        return [cand]
    widths = sorted(c[1] - c[0] for c in channels)
    median = widths[len(widths) // 2]
    wide = [c for c in channels if (c[1] - c[0]) > max(2.5 * median, 2.0 * size)]
    if not wide:
        return [cand]
    cuts = sorted((c[0] + c[1]) / 2.0 for c in wide)
    parts: list[_Candidate] = []
    bounds = [cand.bbox.x0] + cuts + [cand.bbox.x1]
    for lo, hi in zip(bounds, bounds[1:]):
        rows: list[_Row] = []
        for r in cand.rows:
            segs = [s for s in r.segments if lo <= s.bbox.cx < hi]
            if segs:
                rows.append(_Row(segments=segs, y0=min(s.bbox.y0 for s in segs), y1=max(s.bbox.y1 for s in segs)))
        if not rows:
            continue
        sub_channels = _channels(rows, lo, hi, size)
        if len(sub_channels) < 1:
            # Fewer than two columns on this side: not a table by itself.
            continue
        bbox = BBox.union_all(s.bbox for r in rows for s in r.segments)
        parts.append(_Candidate(rows=rows, bbox=bbox))
    return parts if len(parts) >= 2 else [cand]


def _structural_rows(rows: list[_Row]) -> list[_Row]:
    """Rows that define the column grid: those with (nearly) the most segments.

    Grouped header rows ("Mean ± SD" spanning three data columns) have fewer,
    wider segments and would erase the channels between the data columns.
    """
    counts = sorted(len(r.segments) for r in rows)
    if not counts:
        return rows
    top = counts[-1]
    # The typical count of the busiest third of rows.
    busy = counts[max(0, len(counts) - max(3, len(counts) // 3)):]
    typical = busy[len(busy) // 2]
    keep = [r for r in rows if len(r.segments) >= max(2, int(0.8 * typical))]
    return keep if len(keep) >= 2 else rows


def _refine_segments(rows: list[_Row], size: float) -> tuple[list[_Row], list[float]]:
    """Split segments at narrow word gaps that line up across most rows.

    "9  SPS/09" is one segment when the gap is under two ems, yet a gap at the
    same x in most rows is a column boundary. A gap of at least 0.8 em counts
    as a vote; a position supported by half the multi-word rows, with no word
    straddling it, splits every segment that crosses it.
    """
    # Each qualifying word gap votes with its whole range, and a cut is an x
    # range that enough rows leave empty: the gap under a heading ("Gemiddelde
    # | Sd") and the gaps between right-aligned numbers below it share only
    # their overlap, whose midpoints can sit twelve points apart.
    spans: list[tuple[float, float]] = []
    rows_with_words = 0
    for r in rows:
        words = sorted((w for seg in r.segments for w in seg.words), key=lambda w: w.bbox.x0)
        if len(words) < 2:
            continue
        rows_with_words += 1
        for a, b in zip(words, words[1:]):
            gap = b.bbox.x0 - a.bbox.x1
            if gap >= 0.4 * size:
                spans.append((a.bbox.x1, b.bbox.x0))
    if rows_with_words < 3 or not spans:
        return rows, []
    need = max(3, 0.6 * rows_with_words)
    all_words = [w for r in rows for seg in r.segments for w in seg.words]
    events = sorted([(x0, 1) for x0, _ in spans] + [(x1, -1) for _, x1 in spans], key=lambda e: (e[0], e[1]))
    cuts: list[float] = []
    depth = 0
    start: float | None = None
    for x, d in events:
        depth += d
        if depth >= need and start is None:
            start = x
        elif depth < need and start is not None:
            if x - start >= 1.0:
                cuts.append((start + x) / 2.0)
            start = None
    cuts = [c for c in cuts if not any(w.bbox.x0 < c - 1 and w.bbox.x1 > c + 1 for w in all_words)]
    if not cuts:
        return rows, []
    out: list[_Row] = []
    for r in rows:
        segs: list[Line] = []
        for seg in r.segments:
            crossing = [c for c in cuts if seg.bbox.x0 < c < seg.bbox.x1]
            if not crossing:
                segs.append(seg)
                continue
            groups: list[list] = [[]]
            bounds = sorted(crossing)
            for w in sorted(seg.words, key=lambda w: w.bbox.x0):
                while len(groups) - 1 < len(bounds) and w.bbox.cx > bounds[len(groups) - 1]:
                    groups.append([])
                groups[-1].append(w)
            for g in groups:
                if g:
                    segs.append(Line(words=g, bbox=BBox.union_all(w.bbox for w in g)))
        segs.sort(key=lambda l: l.bbox.x0)
        out.append(_Row(segments=segs, y0=r.y0, y1=r.y1))
    return out, cuts


def _build_table(cand: _Candidate, size: float, strict: bool = True, trusted: bool = False) -> Table | None:
    # Segments per row as the text layer gave them, before voted cuts re-slice them:
    # prose sliced word by word ends with far more columns than segments.
    seg_counts = sorted(len(r.segments) for r in cand.rows)
    median_segments = seg_counts[len(seg_counts) // 2] if seg_counts else 1
    refined, cuts = _refine_segments(cand.rows, size)
    cand = _Candidate(rows=refined, bbox=cand.bbox)
    channels = _channels(_structural_rows(cand.rows), cand.bbox.x0, cand.bbox.x1, size)
    # Voted cuts are column boundaries even when the gap is narrower than a channel.
    for c in cuts:
        if not any(a - 2 <= c <= b + 2 for a, b in channels):
            channels.append((c - 0.5, c + 0.5))
    channels.sort()
    if not channels:
        return None
    bounds = [cand.bbox.x0 - 1.0] + [(c[0] + c[1]) / 2.0 for c in channels] + [cand.bbox.x1 + 1.0]
    columns = list(zip(bounds, bounds[1:]))
    n_cols = len(columns)
    if n_cols < 2:
        return None

    grid_rows: list[list[str]] = []
    for r in cand.rows:
        cells = [""] * n_cols
        for seg in r.segments:
            ci = _column_of(seg.bbox, columns)
            cells[ci] = (cells[ci] + " " + seg.text).strip() if cells[ci] else seg.text
        grid_rows.append(cells)

    grid_rows, grid_geom = _merge_wrapped_rows(grid_rows, cand.rows, size)
    kept_columns = [c for c in range(n_cols) if any(row[c] for row in grid_rows)]
    grid_rows = _drop_empty_columns(grid_rows)
    n_cols = len(grid_rows[0]) if grid_rows else 0
    if n_cols < 2:
        return None
    col_bounds = [columns[c] for c in kept_columns] if len(kept_columns) == n_cols else [(cand.bbox.x0, cand.bbox.x1)] * n_cols
    n_header = _header_row_count(grid_rows)
    spans: dict[tuple[int, int], int] = {}
    row_geom = list(grid_geom)
    if n_header >= 2 and len(kept_columns) == n_cols:
        n_header0 = n_header
        grid_rows, n_header, spans, kept_rows = _header_structure(grid_rows, grid_geom, n_header, col_bounds, size)
        row_geom = [grid_geom[r] for r in kept_rows if r < len(grid_geom)] + list(grid_geom[n_header0:])
        if len(row_geom) != len(grid_rows):
            row_geom = []
    elif n_header >= 2:
        before = len(grid_rows)
        grid_rows = _merge_header_rows(grid_rows)
        n_header = 1
        if len(grid_rows) != before:
            row_geom = []

    # Validation: tables are made of short cells, prose is not.
    non_empty = [c for row in grid_rows for c in row if c]
    if not non_empty:
        return None
    short = sum(1 for c in non_empty if len(c.split()) <= 4)
    numeric = sum(1 for c in non_empty if _NUMERIC.match(c.strip()))
    if not trusted:
        # Character-weighted view: columns of body text flanked by margin line
        # numbers look "half numeric" cell-wise but are overwhelmingly prose.
        total_chars = sum(len(c) for c in non_empty) or 1
        long_chars = sum(len(c) for c in non_empty if len(c.split()) > 6)
        if long_chars > 0.5 * total_chars:
            return None
        # Justified prose split at wide word gaps: many words per row, nothing
        # numeric, and the pieces themselves are phrases. A table of short labels
        # ("Distribution Code | Distribution Licensees | Separate Annex 5") also
        # carries six words a row, but under three a cell.
        n_words = sum(len(c.split()) for c in non_empty)
        words_per_row = n_words / max(1, len(grid_rows))
        words_per_cell = n_words / max(1, len(non_empty))
        sliced = n_cols > 1.5 * median_segments   # the cuts carved the text layer's segments into pieces
        if numeric < 0.1 * len(non_empty) and words_per_row >= 6 and (words_per_cell >= 3 or sliced):
            return None
    if strict:
        if short < 0.6 * len(non_empty) and numeric < 0.3 * len(non_empty):
            return None
        if n_cols == 2 and numeric < 0.25 * len(non_empty) and short < 0.85 * len(non_empty):
            return None
    filled_rows = sum(1 for row in grid_rows if sum(1 for c in row if c) >= 2)
    if filled_rows < 2:
        return None

    cells: list[TableCell] = []
    covered = {(r, c + k) for (r, c), span in spans.items() for k in range(1, span)}
    for ri, row in enumerate(grid_rows):
        for ci, text in enumerate(row):
            if (ri, ci) in covered:
                continue
            span = spans.get((ri, ci), 1)
            x0, x1 = col_bounds[ci][0], col_bounds[min(n_cols - 1, ci + span - 1)][1]
            if ri < len(row_geom):
                y0, y1 = row_geom[ri].y0 - 0.3 * size, row_geom[ri].y1 + 0.3 * size
            else:
                y0, y1 = cand.bbox.y0, cand.bbox.y1
            cells.append(TableCell(text=text, row=ri, col=ci, colspan=span, is_header=(ri < max(1, n_header)), bbox=BBox(x0, y0, x1, y1)))
    # Stacked headings (a group heading over its sub-headings) need HTML: markdown
    # tables have one heading row and no spanning cells.
    merged = n_header >= 2 or any(span > 1 for span in spans.values())
    return Table(n_rows=len(grid_rows), n_cols=n_cols, cells=cells, bbox=cand.bbox, has_merged=merged, provenance="textlayer-aligned")


# A qualifier line under a heading: "(percent)", "[kg]", "%", "$", "mm", "ppm".
_UNIT = re.compile(r"^(\(.*\)|\[.*\]|%|\$|[a-z%$/]{1,3})$")


def _header_row_count(grid: list[list[str]]) -> int:
    """How many leading rows are column headings.

    The first body row is the first with numbers in it and a label in the
    first column (when the table labels its rows), or a group label such as
    "Topsoil" that stands alone in the first column.
    """
    if len(grid) < 2:
        return 1
    first_col_used = any(row[0] for row in grid[1:])
    first_data = None

    def numeric_cells(row):
        return [c for c in row if c and _NUMERIC.match(c.strip()) and not re.fullmatch(r"\(\d{1,2}\)", c.strip())]

    by_long_cell = False
    for i, row in enumerate(grid[:8]):
        filled = [c for c in row if c]
        if not filled:
            continue
        if any(len(c.split()) > 6 for c in filled):
            first_data = i
            by_long_cell = True
            break
        numeric = numeric_cells(row)
        if len(numeric) >= max(1, 0.4 * len(filled)):
            # A numeric row with an empty label cell may still be a heading line
            # ("2011" under "Aug 21,"), but only when what follows is not data:
            # a run of numeric rows is the body, whatever the label column says.
            nxt = next((r for r in grid[i + 1:] if any(r)), None)
            next_is_data = nxt is None or len(numeric_cells(nxt)) >= max(1, 0.4 * sum(1 for c in nxt if c))
            if row[0] or not first_col_used or i >= 4 or next_is_data:
                first_data = i
                break
    if first_data is None:
        return 1
    # A label alone in the first column right above the data is a group label of
    # the body ("Topsoil" over its rows), not part of the heading.
    while first_data >= 2:
        prev = grid[first_data - 1]
        if prev[0] and sum(1 for c in prev if c) == 1:
            first_data -= 1
        else:
            break
    n = max(1, first_data)
    # A table of short text has no numeric row to end its heading, so the first
    # long cell ended it, rows later than the truth (a table of eye diseases was
    # read as seven heading rows once its caption was no longer its first row).
    # An empty corner cell over a labelled first row is a one-row heading.
    if by_long_cell and n >= 2 and not grid[0][0] and grid[1][0]:
        return 1
    if n > 3:
        if all(not row[0] for row in grid[:n]):
            # Stacked column headings with the corner empty, one word a line on
            # an OCR'd table ("SPECIAL" / "VOLUNTARY" / "FUND"): up to five.
            return min(n, 5)
        labelled = all(row[0] for row in grid[1:n] if any(row))
        n = 1 if (not grid[0][0] and labelled) else 3
    return n


def _header_structure(grid, geom, n_header, col_bounds, size):
    """Recover the shape of a stacked heading: which heading cells span several
    columns (a group heading centred over its sub-headings) and which lines are
    fragments of one heading ("Aug 21," over "2011"). Unit rows such as
    "(percent)" stay their own heading row.

    Returns (grid, n_header, spans) with spans mapping (row, col) to a colspan.
    """
    n_cols = len(col_bounds)
    header = [list(r) for r in grid[:n_header]]
    spans: dict[tuple[int, int], int] = {}

    def reach(segs, k):
        lo, hi = col_bounds[k]
        best = max((min(s.bbox.x1, hi) - max(s.bbox.x0, lo)) for s in segs)
        return best / max(1.0, hi - lo)

    def below(r, k):
        return any(header[r2][k] for r2 in range(r + 1, n_header))

    # Spanning cells, from the geometry of the heading text: a heading whose ink
    # reaches into neighbouring columns that are empty on its own row, and that
    # have sub-headings underneath, covers those columns.
    for r in range(n_header):
        row = header[r]
        segs = geom[r].segments if r < len(geom) else []
        extents: list[tuple[int, int, int]] = []
        for c in range(n_cols):
            if not row[c]:
                continue
            lo, hi = col_bounds[c]
            mine = [s for s in segs if s.text.strip() and s.text.strip() in row[c] and min(s.bbox.x1, hi) - max(s.bbox.x0, lo) > 0]
            if not mine:
                continue
            start = c
            while start - 1 >= 0 and not row[start - 1] and reach(mine, start - 1) > 0.15 and below(r, start - 1):
                start -= 1
            end = c
            while end + 1 < n_cols and not row[end + 1] and reach(mine, end + 1) > 0.15 and below(r, end + 1):
                end += 1
            extents.append((c, start, end))
        for c, start, end in extents:
            if start != c:
                row[start], row[c] = row[c], ""
        # A heading already covering several columns covers its whole group: it
        # runs on over empty columns with sub-headings until the next heading.
        starts = sorted(s for _, s, _ in extents)
        for c, start, end in extents:
            if end > start:
                nxt = min((s for s in starts if s > start), default=n_cols)
                while end + 1 < nxt and not row[end + 1] and below(r, end + 1):
                    end += 1
            if end > start:
                spans[(r, start)] = end - start + 1

    def span_of(r, c):
        return spans.get((r, c), 1)

    # Fragments: a heading cell continues the cell above it in the same column
    # when both cover the same columns and nothing else sits between them. Unit
    # rows ("(percent)") stay their own heading row.
    # A parenthesised line is a unit row for the whole table only when the same
    # text repeats across columns ("(percent)" under every date); on its own it
    # continues the heading above it ("Number of Agreement" / "(ranked 3 or 4)").
    repeats = [collections.Counter(x.strip() for x in row if x) for row in header]
    for c in range(n_cols):
        above = None
        for r in range(n_header):
            text = header[r][c]
            if not text:
                continue
            unit = bool(_UNIT.match(text.strip())) and (not text.strip().startswith("(") or repeats[r][text.strip()] >= 2)
            if above is not None and not unit and span_of(r, c) == span_of(above, c):
                gap = geom[r].y0 - geom[above].y1 if r < len(geom) and above < len(geom) else 0.0
                if gap <= 0.8 * size * (r - above):
                    header[above][c] = (header[above][c] + " " + text).strip()
                    header[r][c] = ""
                    spans.pop((r, c), None)
                    continue
            above = None if unit else r
    # A corner label on its own line ("Item" under a row of dates) belongs with
    # the heading row above it when that row has no label of its own.
    for r in range(1, n_header):
        if header[r][0] and sum(1 for x in header[r] if x) == 1 and not _UNIT.match(header[r][0].strip()):
            k = r
            while k - 1 >= 0 and not header[k - 1][0]:
                k -= 1
            if k != r:
                header[k][0], header[r][0] = header[r][0], ""
    # Drop heading rows emptied by the merges, keeping the spans aligned.
    kept = [r for r in range(n_header) if any(header[r])]
    remap = {r: i for i, r in enumerate(kept)}
    spans = {(remap[r], c): s for (r, c), s in spans.items() if r in remap}
    header = [header[r] for r in kept]
    return header + grid[n_header:], len(header), spans, kept


def _drop_empty_columns(grid: list[list[str]]) -> list[list[str]]:
    """Remove columns that hold no text at all (spurious whitespace channels)."""
    if not grid:
        return grid
    n = len(grid[0])
    keep = [c for c in range(n) if any(row[c] for row in grid)]
    if len(keep) == n:
        return grid
    return [[row[c] for c in keep] for row in grid]


def _merge_header_rows(grid: list[list[str]]) -> list[list[str]]:
    """Join a two- or three-line column header into one header row.

    Academic tables often stack the header ("(5)" over "Female"); readers treat
    the stack as one heading, so the cells are joined column by column.
    """
    if len(grid) < 3:
        return grid
    first_data = None
    for i, row in enumerate(grid):
        filled = [c for c in row if c]
        # Column labels such as "(1)" are headings, not data.
        numeric = [c for c in filled if _NUMERIC.match(c.strip()) and not re.fullmatch(r"\(\d{1,2}\)", c.strip())]
        if filled and len(numeric) >= max(1, 0.4 * len(filled)):
            first_data = i
            break
    if first_data is None or first_data < 2 or first_data > 4:
        return grid
    header_rows = grid[:first_data]
    # Only merge when the stacked rows look like headings (short cells), not data.
    if any(len(c.split()) > 6 for row in header_rows for c in row if c):
        return grid
    merged = [" ".join(row[c] for row in header_rows if row[c]).strip() for c in range(len(grid[0]))]
    return [merged] + grid[first_data:]


def _column_of(b: BBox, columns: list[tuple[float, float]]) -> int:
    best, best_ov = 0, -1.0
    for i, (lo, hi) in enumerate(columns):
        ov = min(b.x1, hi) - max(b.x0, lo)
        if ov > best_ov:
            best, best_ov = i, ov
    return best


_CONNECTORS = {"and", "or", "of", "the", "a", "an", "to", "for", "in", "on", "with", "by", "&", "at", "from", "as", "per", "not"}


def _continues(prev_text: str, text: str) -> bool:
    """Does `text` read as the continuation of the wrapped cell `prev_text`?"""
    p, t = prev_text.strip(), text.strip()
    if not p or not t:
        return False
    if t[:1].islower() or t[:1] in "([":
        return True
    if p[-1] in ",;:-–&/":
        return True
    return p.split()[-1].lower() in _CONNECTORS


def _merge_wrapped_rows(grid: list[list[str]], rows: list[_Row], size: float) -> tuple[list[list[str]], list[_Row]]:
    """Fold continuation lines of a wrapped cell into the row above.

    Returns the grid and the row geometry that goes with it (merged rows span
    the lines they were folded from)."""
    if not grid:
        return grid, list(rows)
    grid = [list(cells) for cells in grid]
    rows = list(rows)
    out: list[list[str]] = [grid[0]]
    out_rows: list[_Row] = [rows[0]]
    k = 1
    while k < len(grid):
        cells, row = grid[k], rows[k]
        k += 1
        prev = out[-1]
        prev_row = out_rows[-1]
        filled = [i for i, c in enumerate(cells) if c]
        gap = row.y0 - prev_row.y1
        # A corner label set centred beside a two-line heading ("Tagetes spp.
        # Treatments" between "Plant / Fresh / Dry" and "height / weight") is a
        # row of its own that overlaps both neighbours; it joins the one it
        # overlaps more, provided that neighbour's first column is empty.
        if filled == [0] and not prev[0] and k < len(grid) and not grid[k][0]:
            height = max(row.y1 - row.y0, 1.0)
            ov_prev = min(row.y1, prev_row.y1) - max(row.y0, prev_row.y0)
            nxt_row = rows[k]
            ov_next = min(row.y1, nxt_row.y1) - max(row.y0, nxt_row.y0)

            def wordy(r):
                # a heading line of words, not a line of numbers ("2011 2011 2010 Average"
                # under "Aug 21, Aug 14," keeps its own row so the heading count sees it)
                cs = [c for c in r if c]
                return cs and sum(1 for c in cs if _NUMERIC.match(c.strip())) <= 0.2 * len(cs)

            if ov_prev >= ov_next and ov_prev >= 0.3 * height and wordy(prev):
                prev[0] = cells[0]
                out_rows[-1] = _Row(segments=prev_row.segments + row.segments, y0=min(prev_row.y0, row.y0), y1=max(prev_row.y1, row.y1))
                continue
            if ov_next > ov_prev and ov_next >= 0.3 * height and wordy(grid[k]):
                grid[k][0] = cells[0]
                rows[k] = _Row(segments=row.segments + nxt_row.segments, y0=min(row.y0, nxt_row.y0), y1=max(row.y1, nxt_row.y1))
                continue
        # A two-line cell is set centred on its row, so its first line rises
        # above the row's other cells and clusters as a row of its own, nearer
        # the row above than below by box gap ("White to cream" over "powder",
        # beside "Appearance"). It belongs to the row it overlaps, below.
        if len(filled) == 1 and k < len(grid):
            nxt, nxt_row = grid[k], rows[k]
            overlap = min(row.y1, nxt_row.y1) - max(row.y0, nxt_row.y0)
            height = max(row.y1 - row.y0, 1.0)
            # Only a line standing clear of the row above (a visible gap) and half
            # sunk into a real row below: a plain wrapped continuation touches the
            # row it continues and folds upwards as before (a table of eye diseases
            # lost its row labels to an earlier, looser version of this rule).
            if (gap >= 0.15 * size and overlap >= 0.5 * height and overlap > gap
                    and sum(1 for c in nxt if c) >= 2 and all(not nxt[i] for i in filled)):
                for i in filled:
                    nxt[i] = cells[i]
                rows[k] = _Row(segments=row.segments + nxt_row.segments, y0=min(row.y0, nxt_row.y0), y1=max(row.y1, nxt_row.y1))
                continue
        tight = bool(filled) and gap <= 0.6 * size and all(prev[i] for i in filled) and not any(_NUMERIC.match(cells[i].strip()) for i in filled)
        is_continuation = tight and (
            (cells[0] == "" and all(cells[i][:1].islower() or len(cells[i].split()) > 2 for i in filled))
            # Every column wraps ("US Citizens and" / "Permanent Residents" over
            # "Please visit the" / "program website"): each filled cell must read
            # as the continuation of the cell above it.
            or all(_continues(prev[i], cells[i]) for i in filled)
        )
        if is_continuation:
            for i in filled:
                prev[i] = (prev[i] + " " + cells[i]).strip()
            out_rows[-1] = _Row(segments=prev_row.segments + row.segments, y0=prev_row.y0, y1=row.y1)
        else:
            out.append(cells)
            out_rows.append(row)
    return out, out_rows
