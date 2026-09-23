"""Group line segments into blocks (paragraph candidates).

A block is a run of vertically adjacent lines that overlap horizontally and
share a font size. The rules are deliberately conservative: it is easier for
later stages to merge two blocks than to split one.

Prose set inside a drawn box stays with its box (D042): a note boxed beside a paragraph ("If relevant,
please see our Financial Hardship ... policies") was threaded line by line into the paragraph, its lines between the
paragraph's. A line inside such a box joins only a block inside the same box, and a line outside joins none inside.
A box holds prose when two of its lines of four words or more run across half its width; a figure's frame round its
axis labels holds short ones, a table's shaded label cell holds a word or three, and a box round all the page's text
divides nothing. It is a box set round its text: a shape a line runs across - a room of a floor plan behind a note, a
panel behind a title's first lines - is none. And it is a box a reader sees: a white shape with no outline, as design
tools leave behind a page's text frames, is none.
"""

from __future__ import annotations

import re

from truedoc.model import BBox, Block, BlockKind, Line, Page

_LIST_MARKER = re.compile(
    r"^(?:[•◦▪●‣⁃■□–—\-\*·]|"
    r"\(?\d{1,3}[.)]|\(?[a-z][.)]|\([A-Z]\)|[A-Z]\)|\(?[ivxIVX]{1,6}[.)])\s*$"
)


_NUMBERED_HEADING = re.compile(r"^\s*\d{1,2}(?:\.\d{1,2}){0,4}\.?\s+[A-Z]")


def _heading_like(line: Line) -> bool:
    """A short numbered line such as '1.2. Analysis and results' that stands alone."""
    text = line.text.strip()
    if len(text) > 90 or len(line.words) < 2:
        return False
    if not _NUMBERED_HEADING.match(text):
        return False
    if text.endswith((".", ",", ";", ":")) and not re.search(r"[A-Z][a-z]+\.$", text):
        return False
    # Numbered list items ("1. Introduce the ...") are long sentences; headings are title-ish.
    words = text.split()[1:]
    caps = sum(1 for w in words if w[:1].isupper())
    return caps >= max(1, len(words) // 2) or len(words) <= 4


_STYLE_SUFFIX = re.compile(r"[-,_ ]?(bold|italic|oblique|regular|roman|medium|light|black|heavy|semibold|demibold|bd|it|mt|psmt)+$", re.IGNORECASE)


def font_family(line: Line) -> str:
    """Font name with subset prefix and style suffixes removed, e.g. 'ABCDEF+Times-BoldItalic' -> 'times'."""
    name = line.words[0].font if line.words else ""
    if "+" in name:
        name = name.split("+", 1)[1]
    name = name.split(",")[0]
    name = _STYLE_SUFFIX.sub("", name)
    return name.lower()


def _starts_with_list_marker(line: Line) -> bool:
    if not line.words:
        return False
    first = line.words[0].text
    if _LIST_MARKER.match(first):
        return True
    # Marker glued to the word, e.g. "1.Introduction" or "•Item"
    return bool(re.match(r"^[•◦▪●‣⁃·]", first))


def _is_fragment(line: Line) -> bool:
    """A short lowercase fragment cut off the end of a line by a wide gap."""
    t = line.text.strip()
    return 0 < len(line.words) <= 3 and bool(t) and t[0].isalpha() and t[0].islower()


def _starts_a_column(line: Line, starts: list[tuple[float, float]], size: float) -> bool:
    """Other lines nearby start where this one does: it heads a column of text, not a line."""
    return any(abs(x0 - line.bbox.x0) <= 2.0 and 0.5 * size < abs(y0 - line.bbox.y0) <= 8.0 * size for x0, y0 in starts)


def _fragment_host(line: Line, open_blocks: list[Block], size: float, gutters: list[tuple[float, float]]) -> Block | None:
    """The open block whose last line the fragment continues: on its baseline, in its face and
    size, ending without punctuation, and within a stretched word space of its end, or within
    six ems when the fragment stays inside the block's own width ("A sweet domestic comedy" |
    "from the" in a newspaper's justified column, 20_pg39 in run 60). Never across a column
    gutter, and never beyond the block's width: the next column's "cohort." on the same
    baseline is not the rest of the line (0e5f0c3447, a page-check loss)."""
    for blk in open_blocks:
        if blk.meta.get("closed") or not blk.lines:
            continue
        last = blk.lines[-1]
        if abs(last.baseline - line.baseline) > 0.3 * size:
            continue
        gap = line.bbox.x0 - last.bbox.x1
        inside = len(blk.lines) >= 2 and line.bbox.x1 <= blk.bbox.x1 + 1.0 * size
        if not (0.0 <= gap <= 1.5 * size or (inside and gap <= 6.0 * size)):
            continue
        if any(g0 < line.bbox.x0 and g1 > last.bbox.x1 for g0, g1 in gutters):
            continue
        lt = last.text.rstrip()
        if not lt or not (lt[-1].isalnum() or lt[-1] in ",;"):
            continue
        if abs((last.size or size) - size) > 0.15 * size or font_family(last) != font_family(line):
            continue
        return blk
    return None


_NOTE_LINES = 2       # a drawn box holds prose when this many of its lines ...
_NOTE_ACROSS = 0.5    # ... run across this share of its width or more ...
_NOTE_WORDS = 4       # ... each of this many words at least: a label cell's two or three words are no prose
_NOTE_SLACK = 1.0     # a line within this of a box's sides is inside it (pt)


def _within(inner: BBox, outer: BBox) -> bool:
    """A line lies in a box when it runs within the box's sides and its middle is inside: large type's glyph boxes stand
    above and below the letters, past the box they are set in (a title in a dark panel, its first line's box above the
    panel's top)."""
    s = _NOTE_SLACK
    return inner.x0 >= outer.x0 - s and inner.x1 <= outer.x1 + s and outer.y0 <= inner.cy <= outer.y1


def _crosses(line: Line, box: BBox) -> bool:
    """Does the line run across one of the box's sides - its middle level with the box, starting on one side of an edge
    and ending on the other? A shape drawn behind text (a room of a floor plan, a panel behind a title) does; a box set
    round its own text does not."""
    if not box.y0 <= line.bbox.cy <= box.y1:
        return False
    s = _NOTE_SLACK
    return any(line.bbox.x0 < edge - s and line.bbox.x1 > edge + s for edge in (box.x0, box.x1))


def _boxed_prose(page: Page, lines: list[Line]) -> list[BBox]:
    """The drawn boxes that hold prose, smallest first."""
    written = [l for l in lines if l.words]
    out = []
    for d in page.drawings:
        if d.kind != "rect" or d.unseen:
            continue
        inside = [l for l in written if _within(l.bbox, d.bbox)]
        if len(inside) == len(written) or any(_crosses(l, d.bbox) for l in written):
            continue
        prose = [l for l in inside if l.bbox.width >= _NOTE_ACROSS * d.bbox.width and len(l.words) >= _NOTE_WORDS]
        if len(prose) >= _NOTE_LINES:
            out.append(d.bbox)
    return sorted(out, key=lambda b: b.area)


def _box_of(line: Line, boxes: list[BBox]) -> int | None:
    """The smallest box of prose the line lies in, as its place in `boxes`."""
    return next((i for i, b in enumerate(boxes) if _within(line.bbox, b)), None)


def build_blocks(page: Page, lines: list[Line] | None = None) -> list[Block]:
    lines = sorted(page.lines if lines is None else lines, key=lambda l: (round(l.bbox.y0, 1), l.bbox.x0))
    starts = [(l.bbox.x0, l.bbox.y0) for l in lines if l.words]
    boxes = _boxed_prose(page, lines)
    blocks: list[Block] = []
    open_blocks: list[Block] = []
    top_zone = 0.09 * page.height
    bottom_zone = page.height - 0.09 * page.height
    ocr_layer = page.quality.kind == "ocr"

    for line in lines:
        if not line.words:
            continue
        size = max(line.size, 0.7 * line.bbox.height) or page.body_font_size or 10.0
        box = _box_of(line, boxes) if boxes else None
        if _is_fragment(line) and not _starts_a_column(line, starts, size):
            host = _fragment_host(line, [b for b in open_blocks if b.meta.get("box") == box], size,
                                  page.meta.get("column_gutters") or [])
            if host is not None:
                last = host.lines[-1]
                last.words.extend(line.words)
                last.bbox = last.bbox.union(line.bbox)
                host.bbox = host.bbox.union(line.bbox)
                continue
        best: Block | None = None
        best_score = 0.0
        heading_line = _heading_like(line)
        for blk in open_blocks:
            if heading_line:
                break
            if blk.meta.get("closed") or blk.meta.get("box") != box:
                continue
            last = blk.lines[-1]
            # On a hidden OCR layer the boxes are far taller than the declared size,
            # and comparing an inflated line size with the block's plain one refused
            # every other line, so there the block is measured like the line. Not on
            # digital text: a paragraph line carrying tall inline maths would then
            # refuse its own next line, and the orphaned sentence gets swallowed by
            # the display formula beside it (2503.07924, run 39).
            bsize = max(blk.size or size, 0.7 * last.bbox.height) if ocr_layer else (blk.size or size)
            gap = line.bbox.y0 - last.bbox.y1
            # "Above" is judged by boxes on digital text (a text line under a tall
            # display formula overlaps the formula's box and must not join it) and
            # by baselines on a hidden OCR layer, whose boxes can be half again as
            # tall as the line pitch, so the next line's box starts well above the
            # last one's bottom (a patent scan: the short last line of a paragraph
            # was skipped and the paragraph after it took its place, 6 Sept).
            if ocr_layer:
                if line.baseline <= last.baseline + 0.4 * size:
                    continue  # not below the block's last line: not a continuation
            elif gap < -0.6 * size:
                continue  # line is above the block's last line: not a continuation
            if gap > 0.9 * max(size, bsize):
                continue
            # Horizontal relationship: must overlap the block's x-range.
            xo = line.bbox.x_overlap(blk.bbox)
            if xo <= 0.2 * min(line.bbox.width, blk.bbox.width):
                continue
            # Font size compatibility. On a hidden OCR layer neither the nominal
            # size nor the box height is reliable alone (a dictionary page swings
            # between 7 and 11 pt boxes on a 5 pt size from line to line), so a
            # line is refused only when both disagree with the block's last line,
            # as a journal's small copyright line under a footnote does.
            ratio = size / bsize if bsize else 1.0
            if ocr_layer:
                sr = (line.size or size) / max(last.size or size, 0.1)
                hr = line.bbox.height / max(last.bbox.height, 0.1)
                if (sr < 0.75 or sr > 1.33) and (hr < 0.75 or hr > 1.33):
                    continue
            elif ratio < 0.8 or ratio > 1.25:
                continue
            # A single line in a different typeface and size is a different thing
            # (a running header above a caption, a display heading above text).
            if len(blk.lines) == 1 and abs(ratio - 1.0) > 0.05 and font_family(last) != font_family(line):
                continue
            # Do not merge across the running-header / running-footer boundary
            # unless the sizes match exactly (a header is usually a different size).
            if abs(ratio - 1.0) > 0.05 and (
                (blk.bbox.y1 <= top_zone and line.bbox.y0 > top_zone)
                or (blk.bbox.y1 <= bottom_zone < line.bbox.y0)
            ):
                continue
            # Do not merge a list item onto the previous item.
            if _starts_with_list_marker(line) and line.bbox.x0 <= blk.bbox.x0 + 0.5 * size:
                continue
            # Do not merge a bold single line (likely heading) with normal text or vice versa.
            if len(blk.lines) == 1 and last.bold != line.bold and len(last.text) < 80:
                continue
            score = xo - gap
            if best is None or score > best_score:
                best, best_score = blk, score
        if best is None:
            blk = Block(kind=BlockKind.TEXT, bbox=line.bbox, lines=[line])
            if box is not None:
                blk.meta["box"] = box
            if heading_line:
                blk.meta["closed"] = True
                blk.meta["heading_like"] = True
            blocks.append(blk)
            open_blocks.append(blk)
        else:
            best.lines.append(line)
            best.bbox = best.bbox.union(line.bbox)
        # Close blocks that are now far above the current line.
        open_blocks = [b for b in open_blocks if line.bbox.y0 - b.bbox.y1 < 3.0 * size]

    return blocks
