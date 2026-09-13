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
from truedoc.tables.cells import clean_cell_text, is_bracketed_statistic

_NUMERIC = re.compile(
    # A currency sign before the number ("$448", "€1,298") is still a number: a press release's
    # revenue row read as a heading without it (run 58).
    r"^[\(\[]?[-+−–<>≤≥↑↓~≈]?\s*[$€£¥]?\s?[\d.,]+\s*(?:[±+\-−]\s*[\d.,]+)?\s*%?[\)\]]?[*†‡a-z]{0,3}$|^[-–—]$|^n/?a$|^n\.?s\.?$|^\d+[\d.,]*\s*[×x]\s*10[-−]?\d*$"
    # a value with its error or count in parentheses: "−.25 (.23)", "7.90 (3.07)", "12 (4.5%)";
    # significance stars sit on the value ("0.0475** (0.0205)"), up to three of them
    r"|^[-+−]?\s*[\d.,]+\s*%?[*†‡a-z]{0,3}\s*\([-+−]?\s*[\d.,]+\s*%?\)[*†‡a-z]{0,3}$",
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
    # Running headers and footers never belong to a table: the top and bottom
    # strips are left out. Rows of several cells alone in a strip are not a
    # table either (a document-control stamp, "issued: | 2019-04-17" over three
    # more such rows, is furniture; reading it as a table cost five checks in
    # run 50). The one exception is the heading row of a table that starts in
    # the strip (a continued table's "Category | Region | Phenotype" over its
    # first body rows), which sits within a line of a body row of several cells.
    top_zone = 0.09 * page.height
    bottom_zone = page.height - 0.09 * page.height
    lines = [l for l in lines if not l.rotated]
    body = [l for l in lines if not (l.bbox.y1 <= top_zone or l.bbox.y0 >= bottom_zone)]
    all_rows = _cluster_rows(lines, size)
    body_multi = [r for r in _cluster_rows(body, size) if _is_multicell(r, size)]
    # A one-line group label ("Adjusted EPS*:") between a strip row and the body: the rows
    # above and below it are one table (a press release's revenue and earnings rows, run 58,
    # five checks), so the gap it makes is bridged.
    labels = [r for r in all_rows if len(r.segments) == 1 and len(r.segments[0].text.split()) <= 4]

    def bridged(r, b):
        """The one-line label between two rows a longer gap apart, or None."""
        gap_below = b.y0 - r.y1
        gap_above = r.y0 - b.y1
        if 1.8 * size < gap_below <= 3.4 * size:
            return next((lab for lab in labels if r.y1 - 0.2 * size <= lab.y0 and lab.y1 <= b.y0 + 0.2 * size), None)
        if 1.8 * size < gap_above <= 3.4 * size:
            return next((lab for lab in labels if b.y1 - 0.2 * size <= lab.y0 and lab.y1 <= r.y0 + 0.2 * size), None)
        return None

    joined: set[int] = set()
    for strip, nearest_first in (([l for l in lines if l.bbox.y1 <= top_zone], lambda r: -r.y0), ([l for l in lines if l.bbox.y0 >= bottom_zone], lambda r: r.y0)):
        multi = [r for r in _cluster_rows(strip, size) if _is_multicell(r, size)] if strip else []
        # Nearest the body first: a row the table takes in carries the row above
        # it (a heading over a first data row that also sits in the strip).
        pool = list(body_multi)
        for r in sorted(multi, key=nearest_first):
            # ... and its cells start where the table's columns start (a report's
            # banner of wide centred titles right above a table is not its heading),
            # and the body below it is a table of at least two such rows (the third
            # row of a document-control stamp that crosses the strip's edge is not).
            near = [b for b in pool if -0.6 * size <= b.y0 - r.y1 <= 1.8 * size or -0.6 * size <= r.y0 - b.y1 <= 1.8 * size or bridged(r, b) is not None]
            if near and any(_columns_align(r, b, size) for b in near):
                first = min(near, key=lambda b: b.y0)
                run_below = sum(1 for b in pool if -0.6 * size <= b.y0 - first.y0 <= 3.6 * size)
                # A row chaining onto a strip row already taken in rests on that row's proof; so
                # does one with another strip row aligned on it (a block whose last row alone
                # crosses into the body: a figure's key values, run 59).
                stacked = any(m is not r and abs(m.y0 - r.y0) <= 3.6 * size and _columns_align(m, r, size) for m in multi)
                if run_below >= 2 or id(first) in joined or (run_below >= 1 and stacked):
                    body.extend(r.segments)
                    for b in near:
                        lab = bridged(r, b)
                        if lab is not None and id(lab) not in joined:
                            body.extend(lab.segments)   # the label is a row of the table too
                            joined.add(id(lab))
                    pool.append(r)
                    joined.add(id(r))
    # Strip rows taken in were appended out of order; the clusterer wants the page's order.
    body.sort(key=lambda l: (l.bbox.y0, l.bbox.x0))
    rows = _cluster_rows(body, size)
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


def _centred_title(row: _Row, run: list[_Row], size: float) -> bool:
    """A short one-line title centred over a run, just above it, that is not a caption."""
    if len(row.segments) != 1:
        return False
    seg = row.segments[0]
    text = seg.text.strip()
    if _CAPTION_LIKE.match(text) or len(text.split()) > 6 or text.endswith((":", ".", ";", "?", "!")):
        return False
    x0 = min(s.bbox.x0 for r in run for s in r.segments)
    x1 = max(s.bbox.x1 for r in run for s in r.segments)
    width = x1 - x0
    if width <= 0 or seg.bbox.width >= 0.9 * width:
        return False
    centre = (seg.bbox.x0 + seg.bbox.x1) / 2.0
    if not (x0 + 0.25 * width <= centre <= x1 - 0.25 * width):
        return False
    return -0.6 * size <= run[0].y0 - row.y1 <= 1.5 * size


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
        title: _Row | None = None
        while run and not _is_multicell(run[0], size):
            if _heading_fragment(run[0], run, size):
                break
            title = run.pop(0)
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
        elif (len(run) == 2 and multi == 2 and all(len(r.segments) >= 2 for r in run) and any(len(r.segments) >= 3 for r in run)
              and title is not None and _centred_title(title, run, size)):
            # A two-row table under its own centred title ("Scale Reliability Statistics" over
            # "Cronbach's α | McDonald's ω" over one row of values): the title is its heading.
            run.insert(0, title)
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
        elif _wrapped_cell_line(row, run, size):
            # The rest of a wrapped cell ("Bhattacharya et al., 2012;" under
            # "Huber et al., 2002; Hou et al., 2006;" in a references column):
            # inside the table, not a break in it, however many lines it takes.
            run.append(row)
        else:
            singles_in_a_row += 1
            if singles_in_a_row > 1:
                close()
                pending = row   # the lone row that ended this run may head the next table
            else:
                run.append(row)
    close()
    return candidates


def _columns_align(r: _Row, b: _Row, size: float) -> bool:
    """Do the cells of row `r` start on the columns of row `b` (within an em): at
    least two of them, and at least half? (A heading "# | Attribute | Description"
    over rows whose first column is empty aligns two of three; a banner of wide
    centred titles aligns none.)"""
    starts = [s.bbox.x0 for s in b.segments]
    ends = [s.bbox.x1 for s in b.segments]
    if len(r.segments) < 2:
        return False
    # A right-aligned column of values lines up on its right edge ("TN 3600 µg l-1" over
    # "pH 6.9"), so either edge counts.
    aligned = sum(1 for s in r.segments if any(abs(s.bbox.x0 - x0) <= 1.0 * size for x0 in starts) or any(abs(s.bbox.x1 - x1) <= 1.0 * size for x1 in ends))
    return aligned >= 2 and aligned * 2 >= len(r.segments)


def _wrapped_cell_line(row: _Row, run: list[_Row], size: float) -> bool:
    """A lone line that starts on a column of the last row of several cells and
    stays inside that column: the continuation of a wrapped cell. A caption or a
    note across the table starts at the table's edge, off any column but the
    first, and runs past the next column's start."""
    if len(row.segments) != 1:
        return False
    ref = next((r for r in reversed(run) if len(r.segments) >= 2), None)
    if ref is None:
        return False
    seg = row.segments[0]
    starts = sorted(s.bbox.x0 for s in ref.segments)
    for i, x0 in enumerate(starts):
        if abs(seg.bbox.x0 - x0) <= 0.5 * size:
            if i == 0:
                return False   # the first column's edge is also where a caption starts
            nxt = starts[i + 1] if i + 1 < len(starts) else None
            return nxt is None or seg.bbox.x1 <= nxt - 0.3 * size
    return False


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
    # Text lying wholly inside a run of low cover is a sparse column, not whitespace: a
    # label column filled on five rows in twenty-nine ("Emotion Type": Sequential,
    # Prevalent, Inverse) read as empty space from the table's edge to the next column,
    # and an edge-to-column run is never a channel (run 58, two checks). Segments of two
    # rows or more inside a run split it.
    channels: list[tuple[float, float]] = []
    i = 0
    while i < width:
        if cover[i] <= limit:
            j = i
            while j + 1 < width and cover[j + 1] <= limit:
                j += 1
            lo, hi = x0 + i - 1.0, x0 + j + 2.0
            inside = [(ri, seg) for ri, r in enumerate(rows) for seg in r.segments if seg.bbox.x0 >= lo and seg.bbox.x1 <= hi]
            # (Two rows or more: a heading set a shade left of its narrow column sits in the
            # gap on purpose and alone, and stays a heading in order.)
            if inside and len({ri for ri, _ in inside}) >= 2:
                a = int(min(seg.bbox.x0 for _, seg in inside) - x0)
                b = int(max(seg.bbox.x1 for _, seg in inside) - x0)
                for p, q in ((i, a - 1), (b + 1, j)):
                    if p > 0 and q < width - 1 and (q - p + 1) >= 0.6 * size:
                        channels.append((x0 + p, x0 + q + 1))
            elif i > 0 and j < width - 1 and (j - i + 1) >= 0.6 * size:
                channels.append((x0 + i, x0 + j + 1))
            i = j + 1
        else:
            i += 1
    return channels


def _runs_on(segments: list[Line]) -> bool:
    """Do these lines read as one paragraph, or as a column of separate cells?

    A paragraph's lines run on: they break wherever the measure ends, so line after line begins in
    the middle of a sentence, in lower case. A column of cells starts: each cell is its own
    statement and opens with a capital.

    This decides whether a wide column of words beside a block of short cells is prose that happens
    to sit there - a figure's key values set beside the body text of a paper (run 58) - or the third
    column of a three-column table. Getting it wrong the second way is expensive and silent: on 51 of
    190 Key Facts Sheets the exclusions column was cut off the table and left as loose paragraphs, so
    every "no cover for..." was still on the page with nothing to say which insured event it
    qualified. Nothing is deleted; the meaning is.

    Judged on the opening letter alone, which is typography and knows nothing of any subject.
    """
    starts = [s.text.strip() for s in segments if s.text.strip()]
    if len(starts) < 3:
        return True
    capital = sum(1 for t in starts if t[:1].isupper())
    return capital <= 0.3 * len(starts)


def _split_side_by_side(cand: _Candidate, size: float) -> list[_Candidate]:
    """Split a region into separate tables where a much wider whitespace channel divides it,
    or where a channel divides a prose column from a block of short cells."""
    channels = _channels(cand.rows, cand.bbox.x0, cand.bbox.x1, size)
    prose_split = False
    if len(channels) < 3:
        # A figure's key values ("surface water | bottom water" over "TP 120 µg l-1 | TP 1500
        # µg l-1") set beside a column of prose: the channel between them parts eleven-word
        # segments from cells of a few words, and the block is a table on its own even
        # though the prose side has no columns (run 58, five checks).
        wide = []
        for c in channels:
            mid = (c[0] + c[1]) / 2.0
            # The segments adjacent to the channel, row by row: a channel between two columns of
            # short cells is not a prose split because prose sits further left.
            left: list[int] = []
            right: list[int] = []
            for r in cand.rows:
                ls = [s for s in r.segments if s.bbox.cx < mid]
                rs = [s for s in r.segments if s.bbox.cx >= mid]
                if ls:
                    left.append(len(max(ls, key=lambda s: s.bbox.x1).words))
                if rs:
                    right.append(len(min(rs, key=lambda s: s.bbox.x0).words))
            if len(left) >= 3 and len(right) >= 3:
                lm = sorted(left)[len(left) // 2]
                rm = sorted(right)[len(right) // 2]
                if (lm >= 7 and rm <= 4) or (rm >= 7 and lm <= 4):
                    wordy = [s for r in cand.rows for s in r.segments
                             if (s.bbox.cx >= mid) == (rm >= 7)]
                    if _runs_on(wordy):
                        wide.append(c)
        if not wide:
            return [cand]
        prose_split = True
    else:
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
    if prose_split:
        return parts if parts else [cand]
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
    same x in most rows is a column boundary. A gap of at least 0.4 em counts
    as a vote; an x range left empty by six in ten multi-word rows, with no
    word straddling its right end, splits every segment that crosses it.
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
    all_segments = [seg for r in rows for seg in r.segments]
    events = sorted([(x0, 1) for x0, _ in spans] + [(x1, -1) for _, x1 in spans], key=lambda e: (e[0], e[1]))
    cuts: list[float] = []
    depth = 0
    start: float | None = None

    def straddled(c: float) -> bool:
        return any(w.bbox.x0 < c - 1 and w.bbox.x1 > c + 1 for w in all_words)

    for x, d in events:
        depth += d
        if depth >= need and start is None:
            start = x
        elif depth < need and start is not None:
            if x - start >= 1.0:
                # A segment running across the whole range belongs to both
                # sides (a group heading, a title over the table): no cut, even
                # through one of its word spaces. A heading row set closer than
                # two ems ("N Minimum Maximum Gemiddelde Sd") is one segment
                # too, but its own word gap over the range voted for the cut.
                spanning = [s for s in all_segments if s.bbox.x0 <= start + 1 and s.bbox.x1 >= x - 1]

                def open_over(s: Line) -> bool:
                    ws = sorted(s.words, key=lambda w: w.bbox.x0)
                    return any(b.bbox.x0 - a.bbox.x1 >= 0.4 * size and a.bbox.x1 < x and b.bbox.x0 > start
                               for a, b in zip(ws, ws[1:]))

                if all(open_over(s) for s in spanning):
                    # The right end first, just before the words that close the
                    # range: rows without a vote (a wrapped description line)
                    # fill the range from the left, and the midpoint of a wide
                    # range landed in one of their word spaces ("(approx." |
                    # "90-95%"), moving half a cell over. A heading centred over
                    # the right column can reach back over that end ("C14" over
                    # "23.8"); then the middle, then the left end.
                    for c in (x - 1.0, (start + x) / 2.0, start + 1.0):
                        if not straddled(c):
                            cuts.append(c)
                            break
            start = None
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


def _headings_in_order(row: _Row, cols: list[int]) -> bool:
    """A row of short headings set a shade left of the narrow columns beneath
    them ("BM BF WM ... Total" over "4 4 7 ... 25"): by position two headings
    share a column and another column has none, yet the row holds one heading
    per column of the stretch it covers. Such a row is read in order."""
    n = len(cols)
    if n < 3 or len(set(cols)) == n or cols != sorted(cols):
        return False
    if cols[-1] - cols[0] + 1 != n:
        return False
    return not any(_NUMERIC.match(seg.text.strip()) for seg in row.segments)


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
        cols = [_column_of(seg.bbox, columns) for seg in r.segments]
        if _headings_in_order(r, cols):
            cols = list(range(cols[0], cols[0] + len(cols)))
        # (Moving a band into the first column it covers was tried here, on the grounds that a
        # reader takes the first cell as the row's own label and a later cell as belonging under
        # that column's heading. Measured on the 202 Key Facts Sheets it cost 26 events their
        # Yes/No answer and four sheets their heading: a single wrapped line that spills a little
        # into the narrow "Yes/No" column reads as a band under any test loose enough to catch the
        # real ones, and lands on top of the answer. Keeping the band out of the cell above it wins
        # all 60 bands on its own, so the placement is not worth a second attempt without a much
        # sharper test of what a band is.)
        for seg, ci in zip(r.segments, cols):
            cells[ci] = (cells[ci] + " " + seg.text).strip() if cells[ci] else seg.text
        grid_rows.append(cells)

    grid_rows, grid_geom = _merge_wrapped_rows(grid_rows, cand.rows, size, columns)
    grid_rows, grid_geom = _fold_wrapped_heading(grid_rows, grid_geom)
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
    elif n_header == 1 and len(kept_columns) == n_cols and grid_geom:
        spans = _single_header_spans(grid_rows, grid_geom[0], col_bounds)

    # Validation: tables are made of short cells, prose is not.
    non_empty = [c for row in grid_rows for c in row if c]
    if not non_empty:
        return None
    short = sum(1 for c in non_empty if len(c.split()) <= 4)
    numeric = sum(1 for c in non_empty if _NUMERIC.match(c.strip()))
    # A dichotomous key ("A. Glands of the involucre ovate ..." beside "Euphorbia
    # helioscopia", "aa. Glands kidney-shaped ..." beside "B") is a two-column
    # table of long leads and short names that every prose test would throw out.
    key = _key_table(grid_rows, n_cols)
    if not trusted and not key:
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
        # The cuts carved the text layer's segments into pieces when the columns
        # filled on most rows outnumber the segments a row came with. Columns
        # filled on few rows (the tick columns of a checklist of names) are not
        # pieces of anything: they are why such a list has more columns than
        # segments, and they must not make it prose.
        dense_cols = sum(1 for c in range(n_cols) if sum(1 for row in grid_rows if row[c]) >= 0.5 * len(grid_rows))
        sliced = dense_cols > 1.5 * median_segments
        # Cells that carry a digit ("TP 120 µg l-1", a value with its unit) are not prose either,
        # whatever the number pattern says of them (a figure's value block, run 59).
        digitish = sum(1 for c in non_empty if any(ch.isdigit() for ch in c))
        if numeric < 0.1 * len(non_empty) and digitish < 0.3 * len(non_empty) and words_per_row >= 6 and (words_per_cell >= 3 or sliced):
            return None
    if strict and not key:
        if short < 0.6 * len(non_empty) and numeric < 0.3 * len(non_empty):
            return None
        if n_cols == 2 and numeric < 0.25 * len(non_empty) and short < 0.85 * len(non_empty):
            return None
    filled_rows = sum(1 for row in grid_rows if sum(1 for c in row if c) >= 2)
    if filled_rows < 2:
        return None

    rowspans = _label_rowspans(grid_rows, row_geom, n_header) if len(row_geom) == len(grid_rows) else {}
    cells: list[TableCell] = []
    covered = {(r, c + k) for (r, c), span in spans.items() for k in range(1, span)}
    covered |= {(r + k, 0) for r, n in rowspans.items() for k in range(1, n)}
    for ri, row in enumerate(grid_rows):
        for ci, text in enumerate(row):
            if (ri, ci) in covered:
                continue
            span = spans.get((ri, ci), 1)
            down = rowspans.get(ri, 1) if ci == 0 else 1
            x0, x1 = col_bounds[ci][0], col_bounds[min(n_cols - 1, ci + span - 1)][1]
            if ri < len(row_geom):
                y0, y1 = row_geom[ri].y0 - 0.3 * size, row_geom[min(len(row_geom) - 1, ri + down - 1)].y1 + 0.3 * size
            else:
                y0, y1 = cand.bbox.y0, cand.bbox.y1
            cells.append(TableCell(text=clean_cell_text(text), row=ri, col=ci, rowspan=down, colspan=span, is_header=(ri < max(1, n_header)), bbox=BBox(x0, y0, x1, y1)))
    # Stacked headings (a group heading over its sub-headings) need HTML: markdown
    # tables have one heading row and no spanning cells.
    merged = n_header >= 2 or any(span > 1 for span in spans.values()) or bool(rowspans)
    return Table(n_rows=len(grid_rows), n_cols=n_cols, cells=cells, bbox=cand.bbox, has_merged=merged, provenance="textlayer-aligned")


# A qualifier line under a heading: "(percent)", "[kg]", "%", "$", "mm", "ppm".
_UNIT = re.compile(r"^(\(.*\)|\[.*\]|%|\$|[a-z%$/]{1,3})$")


# A line opening with an enumerator starts an entry, however lowercase it is. A flora's key sets
# its leads "A. Glands of the involucre ovate..." over "aa. Glands kidney-shaped...": the second is
# a new lead, not the tail of the first, and reading it as one folded two rows of the key into one.
_ENUMERATED = re.compile(r"^\s*\(?(?:[A-Za-z]{1,3}|\d{1,3})[.)]\s+\S")


def _fold_wrapped_heading(grid: list[list[str]], geom: list[_Row]) -> tuple[list[list[str]], list[_Row]]:
    """A heading set over two or three lines is one heading row, so join it before anything counts.

    Every rule downstream - how many rows are heading, whether the heading is stacked, which cell a
    column is headed by - assumes a heading occupies whole rows. A heading whose widest column runs
    to three lines breaks that assumption at the first step: `_header_row_count` ends the heading at
    the first cell of more than six words, which is the heading's own third column, so the rest of
    the heading becomes body.

    Joining here rather than teaching each downstream rule about it keeps one mechanism in one place,
    and leaves a grid every later rule already handles: the Bendigo sheet, whose heading fits on one
    line, has always worked and is untouched by this.
    """
    if len(grid) < 3:
        return grid, geom
    grid = [list(row) for row in grid]
    geom = list(geom)
    for _ in range(5):      # a heading of up to six lines
        if len(grid) < 3:
            break
        if not (_heading_wraps_on(grid, 0) or _heading_hangs_open(grid, 0)):
            break
        grid[0] = [_join_lines(upper, lower) for upper, lower in zip(grid[0], grid[1])]
        if len(geom) > 1:
            geom[0] = _Row(segments=geom[0].segments + geom[1].segments,
                           y0=min(geom[0].y0, geom[1].y0), y1=max(geom[0].y1, geom[1].y1))
            del geom[1]
        del grid[1]
    return grid, geom


def _heading_hangs_open(grid: list[list[str]], i: int) -> bool:
    """The heading breaks off on a word that cannot end it, and the row below is not a body row.

    Where the columns of a heading wrap by different amounts their lines interleave, so a column's
    continuation can sit two rows below its own start with an empty cell between:

        |             |          | Some examples of specific conditions ... that apply to |
        |             | Yes/No   |                                                        |
        | Event/Cover |          | events/covers (see PDS and other policy documentation for details of |
        |             | Optional |                                                        |
        |             |          | others)*                                               |

    `_heading_wraps_on` looks one row down and finds nothing, so the fold stops at the first line.
    The signal that this is still the heading is the break itself: "apply to", "details of" - a
    preposition or conjunction cannot end a column heading, so the sentence has to go on somewhere.
    That is a far tighter test than "no full stop", which most headings would pass.

    The row below must also still look like heading: part of it empty. A body row of the prescribed
    table fills every column, so the fold stops there.
    """
    if i + 1 >= len(grid):
        return False
    row, below = grid[i], grid[i + 1]
    if not any(row) or all(below):
        return False
    hangs = any(text and text.rstrip().rstrip("-,;:").split()[-1:] and
                text.rstrip().rstrip("-,;:").split()[-1].lower() in _CONNECTORS for text in row)
    return hangs and any(below)


def _heading_wraps_on(grid: list[list[str]], i: int) -> bool:
    """Is this row's long cell an unfinished sentence that the row below carries on in the same column?

    Written in typography, not in subject matter: a cell of more than six words that closes on no
    full stop, with a lowercase line beneath it in its own column, is one sentence set over two
    lines. A body row's long cell is a finished statement, so this never fires on one.
    """
    if i + 1 >= len(grid):
        return False
    row, below = grid[i], grid[i + 1]
    for k, text in enumerate(row):
        if not text or len(text.split()) <= 6 or text.rstrip()[-1:] in ".?!":
            continue
        under = below[k] if k < len(below) else ""
        if under and under.lstrip()[:1].islower() and not _ENUMERATED.match(under):
            return True
    return False


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
    # The first long cell is weak evidence. It says this row has more words than
    # the rows above it, not that those rows are a heading: when a row above has
    # the same shape - the same cells filled, the same cells opening with a
    # number, and a label in the first column - it is another body row, and
    # counting it as heading merges two rows into one. The fees table
    # (tables/937a90b2 page 7) lost two courses and their fees that way: its
    # third row names a course in seven words, its first two in five.
    if by_long_cell and first_data:
        def shape(row: list[str]) -> list[tuple[bool, bool]]:
            return [(bool(c), bool(c) and c.strip()[:1].isdigit()) for c in row]

        here = shape(grid[first_data])
        while (first_data >= 1 and grid[first_data][0] and grid[first_data - 1][0]
               and any(digit for _, digit in here[1:]) and shape(grid[first_data - 1]) == here):
            first_data -= 1
            here = shape(grid[first_data])
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

    # A title row (one cell) above a row of several headings spans every column those
    # headings cover: "Scale Reliability Statistics" over "Cronbach's α | McDonald's ω" heads
    # both, though its ink, centred over the whole table, reaches only the first (run 58's
    # reliability table, three checks).
    for r in range(n_header - 1):
        filled = [c for c in range(n_cols) if header[r][c]]
        below_filled = [c for c in range(n_cols) if header[r + 1][c]]
        if len(filled) == 1 and len(below_filled) >= 2 and (r, filled[0]) not in spans:
            start, end = min(below_filled), max(below_filled)
            # "Number of Agreement" over "Item | I-CVI" with "(ranked 3 or 4)" two rows down
            # in its own column is a two-line heading with single-line headings centred
            # beside it, not a title (3c0b540d, run 60): a title's column has nothing more.
            continued = any(header[r2][filled[0]] for r2 in range(r + 2, n_header))
            if start <= filled[0] <= end and end > start and not continued:
                if start != filled[0]:
                    header[r][start], header[r][filled[0]] = header[r][filled[0]], ""
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
                    header[above][c] = _join_lines(header[above][c], text)
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


def _single_header_spans(grid: list[list[str]], geom: _Row, col_bounds: list[tuple[float, float]]) -> dict[tuple[int, int], int]:
    """A one-row heading centred over a group of columns heads every column it covers.

    "Program Committee" set over two name columns and their tick columns, with no heading
    of their own beneath it, is the heading of each of them (a roster, run 58, three
    checks). A heading whose ink reaches into a neighbouring column that has no heading but
    has body text spans it, and one that already covers two columns runs on over such
    columns until the next heading, both ways. Returns {(0, start): colspan}."""
    header = grid[0]
    n_cols = len(col_bounds)
    body_has = [any(grid[r][c] for r in range(1, len(grid))) for c in range(n_cols)]

    def reach(segs, k):
        lo, hi = col_bounds[k]
        best = max((min(s.bbox.x1, hi) - max(s.bbox.x0, lo)) for s in segs)
        return best / max(1.0, hi - lo)

    extents: list[tuple[int, int, int]] = []
    for c in range(n_cols):
        if not header[c]:
            continue
        mine = [s for s in geom.segments if s.text.strip() and s.text.strip() in header[c]]
        if not mine:
            continue
        start = end = c
        while start - 1 >= 0 and not header[start - 1] and body_has[start - 1] and reach(mine, start - 1) > 0.15:
            start -= 1
        while end + 1 < n_cols and not header[end + 1] and body_has[end + 1] and reach(mine, end + 1) > 0.15:
            end += 1
        extents.append((c, start, end))
    heads = sorted(c for c, _, _ in extents)
    spans: dict[tuple[int, int], int] = {}
    # In a table of numbers, text under the span on the first body row is a second heading
    # row the header count capped ("Mean (log DNA copies/g) ± SD" over "Microbiota | Pre-Test |
    # ..."): the top heading spans nothing. A table without numbers (a roster of names) has
    # no such row, and its heading spans its group.
    def numeric_row(row):
        filled = [x for x in row if x]
        return bool(filled) and sum(1 for x in filled if _NUMERIC.match(x.strip())) >= max(1, 0.4 * len(filled))
    numeric_table = any(numeric_row(r) for r in grid[1:])
    for c, start, end in extents:
        if end > start and numeric_table and len(grid) > 1:
            # ... on any row under the span before the first numeric row ("Day 0 and 35 |
            # Day 35 and 42" two rows under "Δ Average %", the row between empty there).
            under: list[str] = []
            for r in range(1, min(4, len(grid))):
                if numeric_row(grid[r]):
                    break
                under += [grid[r][k] for k in range(start, end + 1) if grid[r][k]]
            if under and not any(_NUMERIC.match(x.strip()) for x in under):
                continue
        if end > start:
            prev_head = max((h for h in heads if h < c), default=-1)
            next_head = min((h for h in heads if h > c), default=n_cols)
            while start - 1 > prev_head and not header[start - 1] and body_has[start - 1]:
                start -= 1
            while end + 1 < next_head and not header[end + 1] and body_has[end + 1]:
                end += 1
        if end > start:
            if start != c:
                header[start], header[c] = header[c], ""
            spans[(0, start)] = end - start + 1
    return spans


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
    merged = []
    for c in range(len(grid[0])):
        text = ""
        for row in header_rows:
            if row[c]:
                text = _join_lines(text, row[c])
        merged.append(text)
    return [merged] + grid[first_data:]


def _column_of(b: BBox, columns: list[tuple[float, float]]) -> int:
    best, best_ov = 0, -1.0
    for i, (lo, hi) in enumerate(columns):
        ov = min(b.x1, hi) - max(b.x0, lo)
        if ov > best_ov:
            best, best_ov = i, ov
    return best


_ENUMERATOR = re.compile(r"^(?:[A-Za-z]{1,2}\.|\d{1,3}\.|[ivxlcIVXLC]{1,5}\.|\(?[A-Za-z0-9]{1,3}\))\s")


def _key_table(grid: list[list[str]], n_cols: int) -> bool:
    """Two columns, three rows or more: every left cell opens with an enumerator
    ("A.", "aa.", "1.", "(b)") and the right cells are short labels on four rows
    in five. A column of prose beside margin line numbers is the mirror image
    (numbers left, prose right) and does not pass."""
    if n_cols != 2 or len(grid) < 3:
        return False
    rows = [r for r in grid if r[0] and r[1]]
    if len(rows) < 3 or len(rows) < 0.8 * len(grid):
        return False
    if not all(_ENUMERATOR.match(r[0].strip()) for r in rows):
        return False
    return sum(1 for r in rows if len(r[1].split()) <= 3) >= 0.8 * len(rows)


def _has_digit(text: str) -> bool:
    return any(ch.isdigit() for ch in text)


_CONNECTORS = {"and", "or", "of", "the", "a", "an", "to", "for", "in", "on", "with", "by", "&", "at", "from", "as", "per", "not"}


def _join_lines(upper: str, lower: str) -> str:
    """Join two lines of one cell. A word broken at a hyphen closes up
    ("Diver-" / "sity" gives "Diversity"), a hyphenated compound keeps its
    hyphen with no space after it ("Automotive-" / "Industrial", "NON-" /
    "RECURRING", "self-" / "employed"); anything else takes a space."""
    upper, lower = upper.rstrip(), lower.lstrip()
    if not upper or not lower:
        return upper or lower
    if upper.endswith("-") and len(upper) >= 2 and upper[-2].isalnum() and lower[:1].isalnum():
        if lower[:1].islower():
            from truedoc.ocr.rapid import _common_words

            words = _common_words()
            head, tail = upper[:-1].split()[-1].lower(), lower.split()[0].lower()
            if head in words and tail.rstrip(".,;:") in words:
                return upper + lower
            return upper[:-1] + lower
        return upper + lower
    return upper + " " + lower


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


_ENTRY_END = re.compile(r"\(\s*[^()]*\d[^()]*\)\s*[*†‡]?\s*$")

# A tick, cross or bullet at the head of a cell starts a new entry, and never continues the one
# above. An insurance "What's covered? / What's not covered?" page is two lists of different
# lengths set side by side, so the two columns' lines interleave and a continuation can land
# under an empty cell; without this the merger read "✗ Pontoons" and "✗ Buildings under
# construction where..." as one exclusion and joined them into a single cell, which publishes a
# list of exclusions the page does not have. The glyphs are the ones `truedoc/marks.py` speaks,
# plus the bullet a text layer writes directly.
# Ticks and crosses only. A round or square bullet leads a *sub-list* under an entry, not a new
# entry: "✓ Loss or damage caused by impact from: • any motor vehicle, • any aircraft, • any animal"
# is one covered item, and starting a row at each bullet shreds it - measured, two checks on the
# insurance set. A bare hyphen is out for the same reason and one more: it also leads a wrapped
# continuation in a reference list, which the benchmark has far more of.
_BULLET_START = re.compile(r"^\s*[✓✔✗✘☑☒]\s+\S")


def _label_rowspans(grid: list[list[str]], geom: list[_Row], n_header: int) -> dict[int, int]:
    """A row label written once for a group of entry rows ("Education" beside
    three education levels, a year beside its quarters) spans the group.

    A label centred on its group has entries above it as well as below; a
    label set at the top of its group has them below only. The label's text
    moves to the group's first row (the grid is changed in place) and the
    result maps that row to the number of rows spanned.
    """
    data = [r for r in range(n_header, len(grid)) if any(grid[r][1:])]
    labels = [r for r in data if grid[r][0]]
    entries = [r for r in data if not grid[r][0]]
    # Entry rows must be the rule, not a missing value here and there.
    if not labels or len(entries) < 2 * len(labels) or len(geom) != len(grid):
        return {}

    def cy(r: int) -> float:
        return (geom[r].y0 + geom[r].y1) / 2.0

    pitches = sorted(cy(b) - cy(a) for a, b in zip(data, data[1:]))
    pitch = pitches[len(pitches) // 2] if pitches else 0.0
    centred = entries[0] < labels[0]
    owner: dict[int, int] = {}
    for e in entries:
        if centred:
            best = min(labels, key=lambda l: abs(cy(l) - cy(e)))
            if abs(cy(best) - cy(e)) > 2.5 * max(pitch, 1.0):
                continue
        else:
            above = [l for l in labels if l < e]
            if not above:
                continue
            best = above[-1]
        owner[e] = best
    spans: dict[int, int] = {}
    for l in labels:
        members = sorted([l] + [e for e, o in owner.items() if o == l])
        lo, hi = members[0], members[-1]
        # A group is one unbroken stretch of rows.
        if hi == lo or hi - lo + 1 != len(members) or any(r not in data for r in range(lo, hi + 1)):
            continue
        if lo != l:
            grid[lo][0], grid[l][0] = grid[l][0], ""
        spans[lo] = hi - lo + 1
    return spans


def _spanned_columns(row: _Row, columns: list[tuple[float, float]] | None) -> set[int]:
    """The columns one piece of this row's text is laid across, if it crosses more than its own.

    Measured on the page rather than guessed: an ordinary wrapped continuation begins some 16pt
    *inside* its own column, while a band begins 96pt to the left of the column it was filed under
    and crosses the ones between.
    """
    if not columns or len(columns) < 2:
        return set()
    for seg in row.segments:
        touched = {k for k, (lo, hi) in enumerate(columns)
                   if min(seg.bbox.x1, hi) - max(seg.bbox.x0, lo) > 0.3 * (hi - lo)}
        if len(touched) >= 2:
            return touched
    return set()


def _is_band(index: int, grid: list[list[str]], rows: list[_Row],
             columns: list[tuple[float, float]] | None) -> bool:
    """Is this row a band laid across the table, rather than a title above it?

    A band - "Cover for valuables, collections and items away from the insured address" opening a
    section of a Key Facts Sheet - is a row of the table in its own right, but it is not a *cell*,
    and markdown has no way to say "this row spans every column". Left to the wrapped-cell merger it
    reads as the continuation of whatever sat above, so the heading of a new section ends up inside
    the previous exclusion and a reader ties it to escape of liquid.

    A table's own centred title crosses the columns in exactly the same way, and must not be treated
    the same: splitting "TABLE 1 / Partial Correlations Between Stroop Scores and / Verbal Responses"
    dragged a piece of the title into the headings and cost two checks.

    What separates them is **where** they sit, not how wide they are. A title stands above the grid,
    with no proper row of the table before it; a band stands inside the body, with proper rows both
    above and below. Width was tried first - a band crosses three columns, a title two - and the
    owner pointed out it cannot be right: a two-column table can hold a band and would never satisfy
    it, so live documents would keep the fault whatever this corpus happens to contain.

    "A proper row" is counted only within the columns the text spans, so a neighbouring column of a
    two-column page - the references running down beside a table - cannot vouch for a title.
    """
    spanned = _spanned_columns(rows[index], columns)
    if len(spanned) < 2:
        return False

    def solid(cells: list[str]) -> bool:
        return sum(1 for k in spanned if k < len(cells) and cells[k]) >= 2

    return (any(solid(grid[k]) for k in range(index))
            and any(solid(grid[k]) for k in range(index + 1, len(grid))))


def _merge_wrapped_rows(grid: list[list[str]], rows: list[_Row], size: float,
                        columns: list[tuple[float, float]] | None = None) -> tuple[list[list[str]], list[_Row]]:
    """Fold continuation lines of a wrapped cell into the row above.

    Returns the grid and the row geometry that goes with it (merged rows span
    the lines they were folded from)."""
    if not grid:
        return grid, list(rows)
    grid = [list(cells) for cells in grid]
    rows = list(rows)
    out: list[list[str]] = [grid[0]]
    out_rows: list[_Row] = [rows[0]]
    took_statistics: set[int] = set()   # rows of `out` that have folded a statistics row in
    k = 1
    while k < len(grid):
        here = k
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
        # A statistic set under its value ("0.150**" over "(4.07)": a t-value, a
        # standard error) is one cell with the value, which is how a reader
        # quotes it: a row with nothing in the label column whose filled cells
        # are all bracketed numbers, each under a number in the row above.
        if (filled and not cells[0] and gap <= 0.6 * size and len(out) >= 2 and len(out) - 1 not in took_statistics
                and all(is_bracketed_statistic(cells[i]) for i in filled)
                and all(prev[i] and any(ch.isdigit() for ch in prev[i]) and not is_bracketed_statistic(prev[i]) for i in filled)):
            for i in filled:
                prev[i] = prev[i] + " " + cells[i]
            out_rows[-1] = _Row(segments=prev_row.segments + row.segments, y0=prev_row.y0, y1=row.y1)
            took_statistics.add(len(out) - 1)
            continue
        # (A continuation whose own column is empty in the row above - "or commercial building"
        # under the empty half of a side-by-side pair of lists - was tried here, folding into the
        # last row with anything in that column. Measured on the benchmark's 188 table pages it
        # cost 48 checks across 21 of them: reaching past a row destabilises the grid far more
        # often than it rescues a continuation. Not retried without a much narrower gate.)
        into = len(out) - 1
        tight = bool(filled) and gap <= 0.6 * size and all(prev[i] for i in filled) and not any(_NUMERIC.match(cells[i].strip()) for i in filled)
        # A tick, cross or bullet at the head of the line starts a new entry, whatever sits above it.
        if any(_BULLET_START.match(cells[i]) for i in filled):
            tight = False
        # A band laid across the table is a row of its own, never the tail of the cell above it.
        if _is_band(here, grid, rows, columns):
            tight = False
        is_continuation = tight and (
            # A long line under a heading reads as a wrapped continuation, unless
            # it is an entry in its own right, closing with a count or share
            # ("High school or less (107; 16.3%)" under "Groups").
            (cells[0] == "" and all(cells[i][:1].islower() or (len(cells[i].split()) > 2 and not _ENTRY_END.search(cells[i])) for i in filled))
            # Every column wraps ("US Citizens and" / "Permanent Residents" over
            # "Please visit the" / "program website"): each filled cell must read
            # as the continuation of the cell above it. A value carrying a number
            # under a value carrying a number is a row of its own however
            # lowercase it starts ("kłodę | do 15 pkt." under "głowę i szyję |
            # do 5 pkt.", a scoring sheet folded into one row): a wrapped cell
            # does not split its number from the line above.
            or (all(_continues(prev[i], cells[i]) for i in filled)
                # (The number test yields to a comma, a hyphen or a connector at the
                # end of the cell above: "ENGR 350A," over "ENGR 370A", "(approx. 90-"
                # over "95% design level)" are wrapped cells, numbers or not.)
                and not any(_has_digit(prev[i]) and _has_digit(cells[i]) and len(cells[i].split()) <= 4
                            and prev[i].rstrip()[-1:] not in ",;:-–&/" for i in filled))
        )
        if is_continuation:
            for i in filled:
                prev[i] = _join_lines(prev[i], cells[i])
            out_rows[into] = _Row(segments=prev_row.segments + row.segments,
                                  y0=prev_row.y0, y1=max(prev_row.y1, row.y1))
        else:
            out.append(cells)
            out_rows.append(row)
    return out, out_rows
