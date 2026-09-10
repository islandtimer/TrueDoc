"""Ruled-table extraction using PyMuPDF's table finder (lines strategy).

This is the conservative first cut: only tables with visible rulings are
detected. Cell text is taken from the text layer, so characters are exact.
"""

from __future__ import annotations

import re

import pymupdf

from truedoc.extract import pdfium_objects, pdftext_rawdict
from truedoc.model import BBox, Block, BlockKind, Table, TableCell
from truedoc.tables.aligned import _continues
from truedoc.tables.cells import clean_cell_text, is_bracketed_statistic
from truedoc.tables import ruled_pdfium


def fold_stacked_statistics(rows: list[list], n_cols: int) -> list[tuple[list, list[int]]]:
    """A statistic set under its value ("0.150**" over "(4.07)": a t-value, a
    standard error) is one cell with the value, which is how a reader quotes it.

    The table finder gives the statistics a row of their own. A row with nothing
    in the label column whose filled cells are all bracketed numbers, each under
    a number in the row above, folds into that row. Returns (cell texts, source
    row indices) per row; the first row (the heading) never takes a fold.
    """
    def texts(row):
        return [((row[ci] if ci < len(row) else None) or "").replace("\n", " ").strip() for ci in range(n_cols)]

    out: list[tuple[list, list[int]]] = []
    for ri, row in enumerate(rows):
        cells = texts(row)
        filled = [ci for ci in range(1, n_cols) if cells[ci]]
        if out and ri > 1 and filled and not cells[0] and all(is_bracketed_statistic(cells[ci]) for ci in filled):
            prev, srcs = out[-1]
            above = texts(prev)
            # (A row that has taken a fold takes no second one: a second row of
            # brackets is not a value's statistic.)
            if len(srcs) == 1 and all(above[ci] and any(ch.isdigit() for ch in above[ci]) and not is_bracketed_statistic(above[ci]) for ci in filled):
                merged = [(above[ci] + " " + cells[ci]).strip() if cells[ci] else (prev[ci] if ci < len(prev) else None) for ci in range(n_cols)]
                out[-1] = (merged, srcs + [ri])
                continue
        out.append((list(row), [ri]))
    return out


_PLACEHOLDER = re.compile(r"^(?:[-–—.]{1,3}|n/?a|none|nil)$", re.I)


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
    # Lines pair up across cells or not at all: one stacked cell beside one-line
    # cells is a wrapped cell ("Chief, Cardiac Catheterization Laboratory" over
    # "MedStar Union Memorial Hospital" beside a name), not two rows; unless
    # every line of the stack carries a number, when it is a stack of entries
    # (a tariff's tiers, "1-80 Kwh - $50" over "81-600 Kwh - $100") and each
    # line is a row.
    if not multi:
        return None
    # A label cell one line taller than the stacks beside it wraps its first label
    # ("Shapiro / W / P value" beside "0.46 / < 2.2e-16": "Shapiro W" and "P value");
    # the wrapped line carries no digit and is short. Run 58 lost four checks to it.
    # ... and at least two stacks agree on the row count: one stack beside a taller label
    # is ambiguous and stays whole.
    heights = {len(lines[ci]) for ci in multi}
    if len(heights) == 2 and len(multi) >= 3:
        k = min(heights)
        tall = [ci for ci in multi if len(lines[ci]) == k + 1]
        first = tall[0] if len(tall) == 1 else None
        # ... and the stacks are single values, one number a line: a cell holding a row of
        # numbers ("14664576 45182539.6 0.325", sub-columns the rules did not divide) is a
        # sub-table, left whole for the rebuild from its lines (run 59 lost five checks to it).
        single_values = all(sum(1 for tok in ln.split() if any(ch.isdigit() for ch in tok)) <= 1 for ci in multi if ci != multi[0] for ln in lines[ci])
        if first is not None and first == multi[0] and single_values and not any(ch.isdigit() for ch in lines[first][0]) and len(lines[first][0].split()) <= 3:
            lines[first] = [lines[first][0] + " " + lines[first][1]] + lines[first][2:]
            heights = {len(lines[ci]) for ci in multi}
    if len(heights) != 1:
        return None
    if len(multi) == 1 and not all(any(ch.isdigit() for ch in ln) for ln in lines[multi[0]]):
        return None
    # A one-line cell left of the stacks is the row's label ("Cd" beside
    # "Shapiro W / P value") and stays on the first row; one to the right is
    # the single value of a wrapped label, so the row is left whole.
    # A dash or an empty marker to the right ("-" in a column with nothing to report)
    # is not a value of a wrapped label: it fills the first row and the rest stay empty.
    if any(len(ls) == 1 and ci > multi[0] and not _PLACEHOLDER.match(ls[0]) for ci, ls in enumerate(lines)):
        return None
    k = len(lines[multi[0]])
    if k > 8:
        return None
    # Beside stacks of numbers the label lines pair up with them whatever their case
    # ("Pearson r" over "p value"); a lowercase start is a wrapped line only elsewhere.
    numeric_stacks = len(multi) >= 2 and all(all(any(ch.isdigit() for ch in ln) for ln in lines[ci]) for ci in multi[1:])
    for ci, ls in enumerate(lines):
        if any(len(ln.split()) > 6 for ln in ls):
            return None
        if numeric_stacks and ci == multi[0]:
            continue
        if any(_continues(a, b) for a, b in zip(ls, ls[1:])):
            return None
    return [[(ls[i] if i < len(ls) else "") for ls in lines] for i in range(k)]


def _row_bounds(cell_rects: list[list]) -> list[tuple[float, float] | None]:
    """Each row's vertical extent: its shortest ruled cell (a tall cell spanning rows is not it)."""
    out: list[tuple[float, float] | None] = []
    for rects in cell_rects:
        ys = [(r[1], r[3]) for r in rects if r is not None]
        out.append(min(ys, key=lambda y: y[1] - y[0]) if ys else None)
    return out


def tall_cell_rows(rows: list, cell_rects: list[list], bounds: list, s: int, ci: int) -> list[int]:
    """The rows a ruled cell at (s, ci) spans: itself and the rows beneath whose cell in that
    column the extractor left out (None) because the tall cell covers them."""
    if ci >= len(cell_rects[s]) or cell_rects[s][ci] is None:
        return [s]
    rect = pymupdf.Rect(cell_rects[s][ci])
    spanned = [s]
    r = s + 1
    while r < len(rows) and ci < len(cell_rects[r]) and cell_rects[r][ci] is None and (rows[r][ci] if ci < len(rows[r]) else None) is None and bounds[r] is not None and bounds[r][1] <= rect.y1 + 2.0:
        spanned.append(r)
        r += 1
    return spanned


_SENTENCE = re.compile(r"[^\W\d_]{2,}[.!?] +[A-Z]")


def deal_tall_cells(pdf_page: "pymupdf.Page", rows: list, cell_rects: list[list], M=None) -> None:
    """Labels in a cell that spans several ruled rows go to the rows their lines fall in.

    A statistical yearbook rules its value cells row by row and leaves the label column as
    one tall cell: the extractor puts every label on the cell's first row and None on the
    rows it spans (904a1b4e in run 58, four checks). Each text line inside the cell's box
    belongs to the row whose extent holds its middle; rows left without a line stay empty.
    Edits `rows` and `cell_rects` in place.

    A tall cell stays one cell (its rows are spanned, see `find_ruled_tables`) when it is a
    heading over two heading rows ("Minimum Central Pressure (mb)" beside "Landfall Location"
    over "Longitude | Latitude"), when its lines read as prose (a realtors' note beside two
    value rows), or when all its lines fall in one of the rows (a label centred in its cell):
    run 60 lost four checks to dealing those."""
    if not cell_rects or len(cell_rects) != len(rows):
        return
    bounds = _row_bounds(cell_rects)
    for s, row in enumerate(rows):
        if s == 0:
            continue
        for ci, val in enumerate(row):
            if not isinstance(val, str) or "\n" not in val or ci >= len(cell_rects[s]) or cell_rects[s][ci] is None:
                continue
            rect = pymupdf.Rect(cell_rects[s][ci])
            spanned = tall_cell_rows(rows, cell_rects, bounds, s, ci)
            if len(spanned) < 2:
                continue
            blocks = None
            if pdftext_rawdict.enabled():
                # M18, D007: read through PDFium instead of AGPL-licensed MuPDF; the page was
                # already built for the text layer, so this is a filter, not a second reading.
                try:
                    blocks = pdftext_rawdict.clipped_blocks(pdf_page.parent.name, pdf_page.number + 1, tuple(rect), M)
                except Exception:
                    blocks = None
            if blocks is None:
                try:
                    blocks = pdf_page.get_text("dict", clip=rect).get("blocks", [])
                except Exception:
                    continue
            texts: dict[int, list[str]] = {}
            lines: list[tuple[str, float]] = []
            for b in blocks:
                for line in b.get("lines", []):
                    text = "".join(sp.get("text", "") for sp in line.get("spans", [])).strip()
                    if not text:
                        continue
                    lines.append((text, line["bbox"][2] - line["bbox"][0]))
                    cy = (line["bbox"][1] + line["bbox"][3]) / 2.0
                    home = min(spanned, key=lambda rr: 0.0 if bounds[rr][0] <= cy < bounds[rr][1] else min(abs(cy - bounds[rr][0]), abs(cy - bounds[rr][1])))
                    texts.setdefault(home, []).append(text)
            if len(texts) < 2:
                continue
            widths = sorted(w for _, w in lines)
            fill = widths[len(widths) // 2] / max(1.0, rect.width)
            n_words = sum(len(t.split()) for t, _ in lines)
            prose = bool(_SENTENCE.search(" ".join(t for t, _ in lines))) or (len(lines) >= 3 and n_words >= 12 and fill >= 0.7)
            if prose:
                continue
            for rr in spanned:
                while len(rows[rr]) <= ci:
                    rows[rr].append(None)
                rows[rr][ci] = "\n".join(texts.get(rr, [])) or ""
                cell_rects[rr][ci] = pymupdf.Rect(rect.x0, bounds[rr][0], rect.x1, bounds[rr][1])


def row_spans(rows: list, cell_rects: list[list]) -> dict[tuple[int, int], int]:
    """{(row, col): rowspan} for ruled cells still standing across the rows beneath them."""
    if not cell_rects or len(cell_rects) != len(rows):
        return {}
    bounds = _row_bounds(cell_rects)
    spans: dict[tuple[int, int], int] = {}
    for s, row in enumerate(rows):
        for ci in range(len(row)):
            if ci >= len(cell_rects[s]) or cell_rects[s][ci] is None:
                continue
            spanned = tall_cell_rows(rows, cell_rects, bounds, s, ci)
            if len(spanned) >= 2:
                spans[(s, ci)] = len(spanned)
    return spans


_NUMERIC_CELL = re.compile(r"^[\(\[]?[-+−–<>≤≥~≈]?\s*[$€£¥]?\s?[\d.,]+\s*%?[\)\]]?[*†‡a-z]{0,3}$|^[-–—]$|^n/?a$", re.I)


def heading_rows(texts: list[list[str]], spans: dict[tuple[int, int], int]) -> set[int]:
    """The leading rows of a ruled table that are its headings.

    A reader takes every row above the first row of values as a heading: a title in one cell
    across the columns, then the column headings, then a second line of them. (Rendered as
    HTML, a table's headings are its <th> cells and nothing else: run 60 marked only the first
    row and lost four checks to headings the scorer could not see.) A group label across the
    columns under the column headings ("PRE (6/4/18) / POST II") is a body row."""
    n_cols = max((len(r) for r in texts), default=0)
    out: set[int] = set()
    seen_columns = False
    for ri, row in enumerate(texts[:3]):
        filled = [ci for ci in range(n_cols) if ci < len(row) and row[ci].strip()]
        if not filled:
            out.add(ri)
            continue
        full_width = len(filled) == 1 and spans.get((ri, filled[0]), 1) >= n_cols - filled[0]
        # A cell of many words is prose, a body row; a title across the columns may be long.
        if not full_width and any(len(row[ci].split()) > 6 for ci in filled):
            break
        numeric = sum(1 for ci in filled if _NUMERIC_CELL.match(row[ci].strip()))
        if numeric >= max(1, 0.4 * len(filled)):
            break
        if full_width and seen_columns:
            break
        if len(filled) >= 2:
            seen_columns = True
        out.add(ri)
    if len(out) >= len(texts):
        return {0}
    return out or {0}


def column_spans(cell_rects: list[list], n_cols: int) -> dict[tuple[int, int], int]:
    """{(row, col): colspan} for ruled cells whose box runs across the columns to their right.

    '% da população' sits in one cell across the value columns of a yearbook table; the
    extractor gives None for the columns it covers. The column centres come from the rows
    that rule them."""
    centres: list[float | None] = [None] * n_cols
    for rects in cell_rects:
        for ci in range(min(n_cols, len(rects))):
            if centres[ci] is None and rects[ci] is not None:
                centres[ci] = (rects[ci][0] + rects[ci][2]) / 2.0
    spans: dict[tuple[int, int], int] = {}
    for ri, rects in enumerate(cell_rects):
        for ci in range(min(n_cols, len(rects))):
            if rects[ci] is None:
                continue
            x0, x1 = rects[ci][0], rects[ci][2]
            span = 1
            cj = ci + 1
            while cj < n_cols and (cj >= len(rects) or rects[cj] is None) and centres[cj] is not None and x0 < centres[cj] < x1:
                span += 1
                cj += 1
            if span > 1:
                spans[(ri, ci)] = span
    return spans


def find_ruled_tables(pdf_page: "pymupdf.Page", page=None) -> list[Block]:
    blocks: list[Block] = []
    tables = None
    source = "pymupdf-lines"
    if pdfium_objects.enabled() and page is not None:
        # M18, D007: pdfplumber's algorithm - the MIT original PyMuPDF's finder was ported from -
        # over rules and characters we read ourselves, so no AGPL code and no third PDF engine.
        tables = ruled_pdfium.find_tables(pdf_page, page)
        if tables is not None:
            source = "pdfium-lines"
    if tables is None:
        try:
            tables = pdf_page.find_tables(strategy="lines_strict").tables
        except Exception:
            return blocks
    for t in tables:
        try:
            # (The PDFium path fills its cells from TrueDoc's own words - see `ruled_pdfium` -
            # after pdfplumber's character clustering read "TypeofTask" at one tolerance and
            # "fr actu res" at another; no single gap fits both tables.)
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
        rows = [list(r) for r in rows]
        # The PDFium path reports its cells in the rendered space, as PyMuPDF's finder does
        # (measured on a 90-degree page: PyMuPDF's first cell holds the word "Table" only once
        # the word is turned by the rotation matrix). Its tall-cell reader is told, so it can
        # turn each cell back to the unrotated space its character boxes are held in.
        rendered = source == "pdfium-lines"
        deal_tall_cells(pdf_page, rows, cell_rects, M=(pdf_page.rotation_matrix if rendered and pdf_page.rotation else None))
        spans = column_spans(cell_rects, n_cols) if cell_rects else {}
        # A tall cell left standing (a heading over two heading rows, a paragraph beside its
        # rows, a label centred in its cell) spans the rows beneath it.
        rspans = row_spans(rows, cell_rects) if cell_rects else {}
        # A body row whose cells hold lines that pair up becomes several rows;
        # a row of statistics under its values folds into the values' row.
        expanded: list[tuple[list, list[int], int, int]] = []   # (cell texts, source rows, slice, slices)
        for row, srcs in fold_stacked_statistics(rows, n_cols):
            parts = split_multiline_row(row, n_cols) if srcs[0] > 0 and len(srcs) == 1 else None
            if parts:
                for k, prow in enumerate(parts):
                    expanded.append((prow, srcs, k, len(parts)))
            else:
                expanded.append((row, srcs, 0, 1))
        n_rows = len(expanded)
        etexts = [[((row[ci] if ci < len(row) else None) or "").replace("\n", " ").strip() for ci in range(n_cols)] for row, _, _, _ in expanded]
        espans = {(ri, ci): spans[(srcs[0], ci)] for ri, (_, srcs, _, _) in enumerate(expanded) for ci in range(n_cols) if len(srcs) == 1 and (srcs[0], ci) in spans}
        headers = heading_rows(etexts, espans)
        has_merged = False
        covered_rows: set[tuple[int, int]] = set()
        for ri, (row, srcs, k, slices) in enumerate(expanded):
            covered: set[int] = set()
            # A sub-heading across the value columns ('% da população' over its rows) is a
            # heading row: a reader takes it as the heading of the rows beneath (D019's
            # yearbook page, two checks), and the scorer reads a spanning <th> the same way.
            filled = [ci for ci in range(n_cols) if ci < len(row) and (row[ci] or "").strip()]
            sub_heading = (len(filled) == 1 and spans.get((srcs[0], filled[0]), 1) >= 2 and slices == 1
                           and not any(ch.isdigit() for ch in row[filled[0]]) and ri > 0)
            for ci in range(n_cols):
                if ci in covered or (ri, ci) in covered_rows:
                    continue
                span = spans.get((srcs[0], ci), 1) if len(srcs) == 1 else 1
                for extra in range(1, span):
                    covered.add(ci + extra)
                if span > 1:
                    has_merged = True
                # The rows a tall cell spans must follow it one to one, unfolded and unsplit.
                down = rspans.get((srcs[0], ci), 1) if len(srcs) == 1 and slices == 1 else 1
                if down > 1 and not all(ri + j < n_rows and expanded[ri + j][1] == [srcs[0] + j] and expanded[ri + j][3] == 1 for j in range(1, down)):
                    down = 1
                for extra in range(1, down):
                    covered_rows.add((ri + extra, ci))
                val = row[ci] if ci < len(row) else None
                text = (val or "").replace("\n", " ").strip()
                if text:
                    non_empty += 1
                cbox = None
                rects = [cell_rects[s][ci] for s in srcs if s < len(cell_rects) and ci < len(cell_rects[s]) and cell_rects[s][ci] is not None]
                if rects:
                    cr = pymupdf.Rect(rects[0])
                    for extra in rects[1:]:
                        cr |= pymupdf.Rect(extra)
                    if pdf_page.rotation and not rendered:
                        cr = cr * pdf_page.rotation_matrix
                    cr.normalize()
                    if slices > 1:
                        h = (cr.y1 - cr.y0) / slices
                        cr = pymupdf.Rect(cr.x0, cr.y0 + k * h, cr.x1, cr.y0 + (k + 1) * h)
                    cbox = BBox(float(cr.x0), float(cr.y0), float(cr.x1), float(cr.y1))
                cells.append(TableCell(text=clean_cell_text(text), row=ri, col=ci, rowspan=down, colspan=span, is_header=(ri in headers or sub_heading), bbox=cbox))
        if non_empty < min(4, n_rows * n_cols):
            continue
        rect = pymupdf.Rect(t.bbox)
        if pdf_page.rotation and not rendered:
            rect = rect * pdf_page.rotation_matrix
        bbox = BBox(float(rect.x0), float(rect.y0), float(rect.x1), float(rect.y1))
        table = Table(n_rows=n_rows, n_cols=n_cols, cells=cells, bbox=bbox, has_merged=has_merged, provenance=source)
        blocks.append(Block(kind=BlockKind.TABLE, bbox=bbox, table=table, provenance=source, confidence=0.8))
    return blocks
