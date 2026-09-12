"""Fuse layout-model regions with text-layer blocks.

The text layer knows *what the characters are*; the layout model knows *what
kind of thing each area of the page is*. This module lets the model decide
kinds (header, footer, caption, table, figure, formula, heading, list item)
while the text layer keeps supplying the characters. Every override records
its provenance so it can be audited.
"""

from __future__ import annotations

import re

from truedoc.classify.blocks import _CONTACT
from truedoc.layout.base import Region, RegionKind
from truedoc.model import BBox, Block, BlockKind, Line, Page
from truedoc.tables.aligned import table_from_lines

_MIN_SCORE = {
    RegionKind.TABLE: 0.5,
    RegionKind.FIGURE: 0.5,
    RegionKind.FORMULA: 0.5,
    RegionKind.PAGE_HEADER: 0.45,
    RegionKind.PAGE_FOOTER: 0.45,
    RegionKind.FOOTNOTE: 0.45,
    RegionKind.CAPTION: 0.45,
    RegionKind.SECTION_HEADER: 0.45,
    RegionKind.TITLE: 0.45,
    RegionKind.LIST_ITEM: 0.5,
    RegionKind.TEXT: 0.45,
    RegionKind.CODE: 0.5,
}

_KIND_MAP = {
    RegionKind.PAGE_HEADER: BlockKind.HEADER,
    RegionKind.PAGE_FOOTER: BlockKind.FOOTER,
    RegionKind.FOOTNOTE: BlockKind.FOOTNOTE,
    RegionKind.CAPTION: BlockKind.CAPTION,
    RegionKind.SECTION_HEADER: BlockKind.HEADING,
    RegionKind.TITLE: BlockKind.TITLE,
    RegionKind.LIST_ITEM: BlockKind.LIST_ITEM,
    RegionKind.FORMULA: BlockKind.FORMULA,
    RegionKind.TEXT: BlockKind.TEXT,
    RegionKind.CODE: BlockKind.CODE,
}


_SPECIFICITY = {RegionKind.TEXT: 0, RegionKind.LIST_ITEM: 1}


def _rank(r: Region) -> tuple[int, float]:
    """Prefer a specific kind (header, caption, formula ...) over generic text when it is reasonably confident."""
    specific = _SPECIFICITY.get(r.kind, 2)
    return (specific if r.score >= 0.45 else -1, r.score)


def clean_regions(regions: list[Region], page_height: float = 0.0) -> list[Region]:
    """Drop weak regions and near-duplicates (keep the more specific, then the higher score)."""
    keep: list[Region] = []

    def rank(r: Region) -> tuple[int, float]:
        specific, score = _rank(r)
        # In the page margins a header/footer reading beats any other kind.
        if page_height and r.kind in (RegionKind.PAGE_HEADER, RegionKind.PAGE_FOOTER) and r.score >= 0.45:
            if r.bbox.y1 <= 0.1 * page_height or r.bbox.y0 >= 0.9 * page_height:
                specific = 3
        return (specific, score)

    for r in sorted(regions, key=rank, reverse=True):
        if r.score < _MIN_SCORE.get(r.kind, 0.5):
            continue
        dup = False
        for i, k in enumerate(keep):
            if {r.kind, k.kind} == {RegionKind.TABLE, RegionKind.FIGURE}:
                continue  # a table inside a figure is a table too (matrices, panels of numbers)
            inter = r.bbox.intersection(k.bbox)
            if inter is None:
                continue
            smaller = min(r.bbox.area, k.bbox.area) or 1.0
            if inter.area / smaller > 0.85:
                # One inside another of the same kind is the same thing seen smaller, and the bigger one
                # holds more of it: a table region over a table's right-hand column alone scored higher
                # than the one over the whole table, won here, and left the rows as prose (the fees page
                # tables/937a90b2 page 7, five checks, run 83).
                if r.kind == k.kind and r.bbox.area > k.bbox.area:
                    keep[i] = r
                dup = True
                break
        if not dup:
            keep.append(r)
    return keep


def _region_for(bbox: BBox, regions: list[Region], kinds=None, min_frac: float = 0.6) -> Region | None:
    best, best_frac = None, 0.0
    for r in regions:
        if kinds and r.kind not in kinds:
            continue
        frac = bbox.overlap_fraction(r.bbox)
        if frac > best_frac:
            best, best_frac = r, frac
    return best if best_frac >= min_frac else None


_CAPTION_START = re.compile(r"^\s*(table|tab\.|fig\.?|figure|exhibit|chart|scheme|appendix)\s*[A-Z]?\d", re.I)
_FUNCTION_WORDS = {"of", "and", "the", "in", "for", "with", "between", "by", "to", "on", "from", "at", "a", "an", "as", "or"}


def caption_like(line: Line, width: float) -> bool:
    """A table's caption, or a sentence, and never its header row: it starts
    like "Table 2." or reads as prose (eight words or more, two of them function
    words) while running across most of the table's width rather than sitting
    in one column. Twenty-six tables in run 39's output opened with such a
    line as their header row, which pushed the real headings into the data."""
    text = line.text.strip()
    if _CAPTION_START.match(text):
        return True
    words = text.split()
    if len(words) < 8 or line.bbox.width < 0.6 * max(width, 1.0):
        return False
    return sum(1 for w in words if w.lower().strip(".,;:()") in _FUNCTION_WORDS) >= 2


def _strip_captions(inside: list, width: float) -> list:
    """Drop caption-like lines from the top and bottom of a table region's lines."""
    lines = sorted(inside, key=lambda l: l.bbox.cy)
    while lines and caption_like(lines[0], width):
        lines.pop(0)
    while lines and caption_like(lines[-1], width):
        lines.pop()
    return lines


def _header_lines_above(page: Page, box: BBox, table, inside: list, consumed: set) -> list:
    """Lines within two line heights above a table box whose words all sit on the
    table's columns (at least two columns hit): the header row the box missed."""
    size = page.body_font_size or 10.0
    spans: dict[int, list[float]] = {}
    for c in table.cells:
        if c.bbox is None:
            continue
        s = spans.setdefault(c.col, [c.bbox.x0, c.bbox.x1])
        s[0], s[1] = min(s[0], c.bbox.x0), max(s[1], c.bbox.x1)
    if len(spans) < 2:
        return []
    inside_ids = {id(l) for l in inside}
    sizes = sorted(l.size for l in inside if l.size > 0)
    table_size = sizes[len(sizes) // 2] if sizes else size

    def column_of(w) -> int | None:
        return next((k for k, (x0, x1) in spans.items() if x0 - size <= w.bbox.cx <= x1 + size), None)

    out = []
    columns_hit: set[int] = set()
    for l in page.lines:
        if id(l) in inside_ids or id(l) in consumed or l.rotated or not l.words:
            continue
        if not (0 <= box.y0 - l.bbox.y1 <= 2.0 * size) or l.bbox.x0 < box.x0 - size or l.bbox.x1 > box.x1 + size:
            continue
        if l.size > 1.15 * table_size:
            continue  # a section heading above the table, not its header row
        if caption_like(l, box.width):
            continue  # "Table 2. ..." or a sentence spanning the columns
        cols = [column_of(w) for w in l.words]
        if any(c is None for c in cols):
            continue  # a word off the columns: a caption or a sentence, not a header row
        out.append(l)
        columns_hit.update(c for c in cols if c is not None)
    if len(columns_hit) >= 2:
        return out
    # One short line over a single column, right above the box, is the upper
    # line of a stacked heading ("Number of Agreement" over "(ranked 3 or 4)")
    # when the table's own first cell in that column reads as the lower half:
    # a parenthesis, a lowercase word or nothing. Over a complete heading it is
    # a title ("Verbal Responses") and stays out.
    if len(out) == 1 and len(columns_hit) == 1:
        l = out[0]
        text = l.text.strip()
        col = next(iter(columns_hit))
        first = next((c.text.strip() for c in table.cells if c.row == 0 and c.col == col), "")
        lower_half = first == "" or first[:1] == "(" or first[:1].islower()
        if lower_half and box.y0 - l.bbox.y1 <= 1.2 * size and len(text.split()) <= 6 and text[:1] not in "-•*" and not text.endswith((".", ":", ";")):
            return out
    return []


def _label_lines_below(page: Page, box: BBox, table, inside: list, consumed: set) -> list:
    """A lone lowercase line at the table's left edge just under the box: the
    second line of the last row's label ("Slaapkwaliteit tijdens" /
    "consignatiediensten"), which the box's bottom edge cut off."""
    size = page.body_font_size or 10.0
    inside_ids = {id(l) for l in inside}
    left = min((l.bbox.x0 for l in inside), default=box.x0)
    out = []
    for l in page.lines:
        if id(l) in inside_ids or id(l) in consumed or l.rotated or not l.words:
            continue
        text = l.text.strip()
        if not (-0.6 * size <= l.bbox.y0 - box.y1 <= 1.0 * size):
            continue
        if abs(l.bbox.x0 - left) > size or l.bbox.width > 0.5 * box.width or not text[:1].islower():
            continue
        out.append(l)
    return out[:1]


_NUMBERISH = re.compile(r"[-+±]?[\d.,]+%?|[\d.,]+[-–][\d.,]+|\d+(st|nd|rd|th)")


def _table_from_picture(page: Page, pdf_page, box: BBox):
    """OCR a table region that holds no text, gated like page OCR: the engine must
    be confident and most tokens must look like words or numbers."""
    try:
        from truedoc.ocr.rapid import ocr_region

        lines, conf, wordlike = ocr_region(pdf_page, box)
    except Exception:
        return None
    if len(lines) < 3 or conf < 0.75:
        return None
    # Tables are full of numbers, percentages and metric names that no word list
    # knows ("sensitivity/recall", "93.75%"): a confident read with a numeric
    # share is accepted even when few tokens look like words.
    tokens = [w.text for l in lines for w in l.words]
    numeric = sum(1 for t in tokens if _NUMBERISH.fullmatch(t))
    if wordlike < 0.5 and not (conf >= 0.85 and tokens and numeric >= 0.3 * len(tokens)):
        return None
    size = sorted(l.size for l in lines)[len(lines) // 2] if lines else page.body_font_size
    table = table_from_lines(lines, size or page.body_font_size, trusted=True)
    if table is not None:
        table.provenance = "ocr-region"
    return table


def apply_layout(page: Page, blocks: list[Block], regions: list[Region], pdf_page=None, ocr: bool = True) -> list[Block]:
    regions = clean_regions(regions, page.height)
    if not regions:
        return blocks

    # 1. Tables from the model's boxes (the text-layer heuristics may have missed them).
    table_regions = [r for r in regions if r.kind == RegionKind.TABLE]
    out: list[Block] = []
    consumed_lines: set[int] = set()
    new_tables: list[Block] = []
    # An aligned-table block that spans several model boxes (side-by-side sub-tables)
    # is rebuilt one table per box, so row headings stay with their own table.
    rebuilt: set[int] = set()
    for b in blocks:
        if b.kind != BlockKind.TABLE or b.provenance != "textlayer-aligned":
            continue
        covering = [tr for tr in table_regions if tr.bbox.overlap_fraction(b.bbox) > 0.6 and b.bbox.overlap_fraction(tr.bbox) < 0.7]
        if len(covering) >= 2:
            rebuilt.add(id(b))
    # A confident text region is a veto: an aligned "table" that the model
    # sees as ordinary text (line-numbered prose, two-column body text) is dropped
    # and its lines go back to the text flow.
    vetoed: set[int] = set()
    text_regions = [r for r in regions if r.kind in (RegionKind.TEXT, RegionKind.LIST_ITEM) and r.score >= 0.85]
    for b in blocks:
        if b.kind != BlockKind.TABLE or b.provenance != "textlayer-aligned":
            continue
        if any(tr.bbox.overlap_fraction(b.bbox) > 0.5 for tr in table_regions):
            continue
        inside_text = max((b.bbox.overlap_fraction(t.bbox) for t in text_regions), default=0.0)
        covered = sum(t.bbox.area for t in text_regions if t.bbox.overlap_fraction(b.bbox) > 0.8)
        if inside_text > 0.8 or covered > 0.6 * b.bbox.area:
            vetoed.add(id(b))
    if vetoed:
        from truedoc.segment.blocks import build_blocks

        freed = [l for b in blocks if id(b) in vetoed for l in _table_lines(page, b)]
        blocks = [b for b in blocks if id(b) not in vetoed]
        if freed:
            blocks.extend(build_blocks(page, freed))
    blocks = [b for b in blocks if id(b) not in rebuilt]

    dropped: set[int] = set()   # aligned fragments replaced by a box's whole table

    def _is_fragment(b: Block, tr: Region) -> bool:
        return b.bbox.overlap_fraction(tr.bbox) > 0.8 and b.bbox.area < 0.5 * tr.bbox.area

    for tr in table_regions:
        existing = [b for b in blocks if b.kind == BlockKind.TABLE and b.bbox.overlap_fraction(tr.bbox) > 0.5 and not (tr.score >= 0.7 and _is_fragment(b, tr))]
        if existing:
            continue
        inside = [l for l in page.lines if tr.bbox.contains_point(l.bbox.cx, l.bbox.cy)]
        # (A caption swallowed by the model's box is left as a row for now: taking it
        # out changed nothing on the benchmark and once merged two columns whose
        # channel the wide caption line had been holding open, 6 Sept.)
        trusted = tr.score >= 0.7
        if len(inside) < 3 and ocr and pdf_page is not None and page.quality.kind == "digital":
            # (any table box the model offers: the OCR gate supplies its own evidence)
            # A table drawn as a picture on a digital page: read the picture.
            table = _table_from_picture(page, pdf_page, tr.bbox)
            if table is not None:
                new_tables.append(Block(kind=BlockKind.TABLE, bbox=table.bbox, table=table, provenance="layout-table-ocr", confidence=min(tr.score, 0.7)))
            continue
        table = table_from_lines(inside, page.body_font_size, trusted=trusted)
        if table is None:
            continue
        # A small aligned table inside this box (a fragment of it that the
        # whitespace finder accepted on its own) gives way only to a bigger table
        # built from the whole box; when the box yields nothing better the
        # fragment stays (a course list vanished when it was dropped in advance).
        fragments = [b for b in blocks if b.kind == BlockKind.TABLE and b.table is not None and tr.score >= 0.7 and _is_fragment(b, tr)]
        # Several small tables inside one box are either sub-tables the box spans
        # (applicants and participants, each with its caption) or pieces of one
        # table broken at its wrapped rows (a table of eye diseases in three
        # pieces). The box's own table tells them apart: pieces leave rows out,
        # so the whole box holds clearly more rows than the pieces together.
        if fragments:
            total = sum(f.table.n_rows for f in fragments)
            if len(fragments) == 1 and table.n_rows <= total:
                continue
            if len(fragments) >= 2 and table.n_rows < total + 2:
                continue
        for f in fragments:
            dropped.add(id(f))
        # The model's box often starts under the header row. A line just above the
        # box whose words sit on the table's columns is the header; rebuild with it.
        header = _header_lines_above(page, tr.bbox, table, inside, consumed_lines)
        if header:
            with_header = table_from_lines(header + inside, page.body_font_size, trusted=trusted)
            if with_header is not None and with_header.n_cols == table.n_cols and with_header.n_rows > table.n_rows:
                table, inside = with_header, header + inside
        # The box's bottom edge may cut a wrapped row label; its second line
        # rejoins the table (and folds into the label above it).
        tail = _label_lines_below(page, tr.bbox, table, inside, consumed_lines)
        if tail:
            with_tail = table_from_lines(inside + tail, page.body_font_size, trusted=trusted)
            if with_tail is not None and with_tail.n_cols == table.n_cols and with_tail.n_rows >= table.n_rows:
                table, inside = with_tail, inside + tail
        for l in inside:
            consumed_lines.add(id(l))
        new_tables.append(Block(kind=BlockKind.TABLE, bbox=table.bbox, table=table, provenance="layout-table", confidence=tr.score))

    for b in blocks:
        if id(b) in dropped:
            continue
        if b.kind == BlockKind.TABLE or not b.lines:
            out.append(b)
            continue
        remaining = [l for l in b.lines if id(l) not in consumed_lines]
        if not remaining:
            continue
        if len(remaining) != len(b.lines):
            b.lines = remaining
            b.bbox = BBox.union_all(l.bbox for l in remaining)  # type: ignore[assignment]
        out.append(b)
    out.extend(new_tables)

    # 2. Split text blocks that straddle regions of different kinds.
    split: list[Block] = []
    for b in out:
        if b.kind == BlockKind.TABLE or len(b.lines) < 2:
            split.append(b)
            continue
        groups: list[tuple[Region | None, list[Line]]] = []
        for l in b.lines:
            r = _line_region(l, regions)
            if groups and _same_group(groups[-1][0], r):
                groups[-1][1].append(l)
            else:
                groups.append((r, [l]))
        if len(groups) == 1:
            split.append(b)
            continue
        for r, ls in groups:
            nb = Block(kind=b.kind, bbox=BBox.union_all(l.bbox for l in ls), lines=ls, provenance="layout-split")  # type: ignore[arg-type]
            nb.meta = dict(b.meta)
            split.append(nb)
    out = split

    # 3. Figures from the model.
    for r in regions:
        if r.kind != RegionKind.FIGURE:
            continue
        if any(b.kind == BlockKind.FIGURE and b.bbox.overlap_fraction(r.bbox) > 0.5 for b in out):
            continue
        if any(b.kind == BlockKind.TABLE and b.bbox.overlap_fraction(r.bbox) > 0.5 for b in out):
            continue
        out.append(Block(kind=BlockKind.FIGURE, bbox=r.bbox, provenance="layout-figure", confidence=r.score))

    # 4. Kind overrides for text blocks.
    figure_boxes = [r.bbox for r in regions if r.kind == RegionKind.FIGURE and r.score >= 0.5]
    for b in out:
        if b.kind in (BlockKind.TABLE, BlockKind.FIGURE):
            continue
        # Short text inside a logo/banner picture at the top of the page is decoration
        # (form titles, letterheads), which readers treat like a running header.
        if (
            b.lines
            and len(b.lines) <= 4
            and len(b.text) <= 200
            and b.bbox.y1 <= 0.12 * page.height
            and any(b.bbox.overlap_fraction(fb) >= 0.8 for fb in figure_boxes)
        ):
            b.kind = BlockKind.HEADER
            b.provenance = "layout:banner"
            continue
        if b.lines and all(l.rotated for l in b.lines):
            b.kind = BlockKind.HEADER
            b.provenance = "rotated-text"
            continue
        r = _region_for(b.bbox, regions, min_frac=0.55)
        if r is None:
            continue
        # A "section header" in the page's margin that the model also rated nearly
        # as high as a page header or footer is a running head ("INVESTIGACIONES /
        # RESEARCH", "esa SP-301"): in the margin, the tie goes to the margin.
        if r.kind == RegionKind.SECTION_HEADER:
            rival = RegionKind.PAGE_HEADER if b.bbox.cy < 0.5 * page.height else RegionKind.PAGE_FOOTER
            in_margin = b.bbox.y1 <= 0.15 * page.height or b.bbox.y0 >= 0.85 * page.height
            # The rival box is a near-duplicate that the cleaning step removed, so
            # look at the detector's raw output.
            raw = page.meta.get("layout_regions") or regions
            if in_margin and any(q.kind == rival and q.score >= r.score - 0.1 and (q.bbox.overlap_fraction(b.bbox) >= 0.5 or b.bbox.overlap_fraction(q.bbox) >= 0.5) for q in raw):
                b.kind = BlockKind.HEADER if rival == RegionKind.PAGE_HEADER else BlockKind.FOOTER
                b.provenance = "layout:margin-tie"
                continue
        new_kind = _KIND_MAP.get(r.kind)
        if new_kind is None:
            continue
        if new_kind == BlockKind.TEXT:
            # Only demote heuristic headings that look like body text.
            if b.kind in (BlockKind.HEADING, BlockKind.LIST_ITEM) and (len(b.lines) > 2 or len(b.text) > 120):
                b.kind = BlockKind.TEXT
                b.provenance = f"layout:{r.kind.value}"
            elif b.kind in (BlockKind.HEADER, BlockKind.FOOTER, BlockKind.PAGE_NUMBER) and r.score >= 0.7 and len(b.text.split()) >= 3 and b.provenance != "margin-line-number":
                # A body line at the top or bottom of a column that the zone rule mistook
                # for a running header. Strong evidence keeps the heuristic: an address,
                # journal line or stamp, or text in the outermost strip of the page.
                n_words = len(b.text.split())
                in_strip = b.bbox.y1 <= 0.09 * page.height or b.bbox.y0 >= 0.91 * page.height
                # A running head or foot is short and set apart by white space; a
                # paragraph that happens to reach the strip (the last lines of a
                # letter, a catalogue entry) is body text and the model's verdict stands.
                if (_CONTACT.search(b.text) and n_words <= 40) or (in_strip and n_words <= 12 and _set_apart(b, blocks, page)):
                    continue
                b.kind = BlockKind.TEXT
                b.provenance = f"layout:{r.kind.value}"
            continue
        if new_kind == BlockKind.TITLE:
            b.kind = BlockKind.HEADING
            b.level = 1
        elif new_kind == BlockKind.HEADING:
            if b.kind != BlockKind.HEADING:
                b.kind = BlockKind.HEADING
                b.level = b.level or 2
        else:
            b.kind = new_kind
        b.provenance = f"layout:{r.kind.value}"
        b.confidence = r.score
    return out


def _set_apart(b: Block, blocks: list[Block], page: Page) -> bool:
    """White space of at least a line separates the block from the body text
    beside it (above, for a foot; below, for a head)."""
    size = b.size or page.body_font_size or 10.0
    others = [o for o in blocks if o is not b and o.lines and o.kind not in (BlockKind.FIGURE, BlockKind.TABLE) and o.bbox.x_overlap(b.bbox) > 0]
    if b.bbox.y0 >= 0.5 * page.height:
        above = [o.bbox.y1 for o in others if o.bbox.y1 <= b.bbox.y0 + 1.0]
        return not above or b.bbox.y0 - max(above) >= 1.0 * size
    below = [o.bbox.y0 for o in others if o.bbox.y0 >= b.bbox.y1 - 1.0]
    return not below or min(below) - b.bbox.y1 >= 1.0 * size


def _table_lines(page: Page, table_block: Block) -> list[Line]:
    """The page lines that an aligned table consumed (by geometry)."""
    return [l for l in page.lines if table_block.bbox.contains_point(l.bbox.cx, l.bbox.cy) and not l.rotated]


def _line_region(line: Line, regions: list[Region]) -> Region | None:
    best, best_frac = None, 0.0
    for r in regions:
        if r.kind == RegionKind.FIGURE:
            continue
        frac = line.bbox.overlap_fraction(r.bbox)
        if frac > best_frac:
            best, best_frac = r, frac
    return best if best_frac >= 0.5 else None


def _same_group(a: Region | None, b: Region | None) -> bool:
    if a is None or b is None:
        return a is b
    if a is b:
        return True
    # Two regions of the same kind next to each other are still separate blocks
    # only when the model says so with confidence; merge low-confidence splits.
    return a.kind == b.kind and a.kind not in (RegionKind.SECTION_HEADER, RegionKind.TITLE, RegionKind.CAPTION, RegionKind.LIST_ITEM)
