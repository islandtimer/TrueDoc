"""Group line segments into blocks (paragraph candidates).

A block is a run of vertically adjacent lines that overlap horizontally and
share a font size. The rules are deliberately conservative: it is easier for
later stages to merge two blocks than to split one.
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


def build_blocks(page: Page, lines: list[Line] | None = None) -> list[Block]:
    lines = sorted(page.lines if lines is None else lines, key=lambda l: (round(l.bbox.y0, 1), l.bbox.x0))
    blocks: list[Block] = []
    open_blocks: list[Block] = []
    top_zone = 0.09 * page.height
    bottom_zone = page.height - 0.09 * page.height
    ocr_layer = page.quality.kind == "ocr"

    for line in lines:
        if not line.words:
            continue
        size = max(line.size, 0.7 * line.bbox.height) or page.body_font_size or 10.0
        best: Block | None = None
        best_score = 0.0
        heading_line = _heading_like(line)
        for blk in open_blocks:
            if heading_line:
                break
            if blk.meta.get("closed"):
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
