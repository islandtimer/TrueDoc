"""Whether a page-number line in a page's margin is the page's own number.

`classify_blocks` takes any block reading just "page N", "N", "N of M" or a roman numeral in the top or bottom strip
for the page's own number, and the renderer leaves page numbers out. A pointer set there reads the same. Budget
Direct's home PDS ends the Landlord Options card on PDF page 8 with "page 52", 41pt above the foot: it was published
nowhere, while "page 53", 28pt higher, stood; Allianz's renter PDS lost "PAGE 25" and "PAGE 32" from its snapshot page
the same way. What makes a number the page's own is that it counts pages, so the pages beside it print theirs at the
same distance from their place in the file: Budget Direct prints 4, 5, 7 and 8 at the top of PDF pages 6, 7, 9 and
10, and 6 on page 8.

So the nearest page before and the nearest page after that print a number in their strips, up to two pages each way,
are asked - through PDFium by the file's path, as the readers read it. When both print one at the same distance, a
number at that distance counts pages and a number at any other does not. None when nothing can say: a file of one
page, no number in the strips beside it, a roman numeral, or pages beside it that disagree - and the zone rule stands.

A number that counts no pages can still be furniture of another kind. RACQ's household PDS sets a section tab, "1",
in the top corner of PDF pages 11 and 13; it runs, and a running head is known the way `layout/fuse.py` knows a running
foot (`_repeated_beside`): a page beside it prints the same at the same place. `release_pointers` gives a margin line
back to the text only when it neither counts pages nor runs, whichever rule took it.
"""
from __future__ import annotations

import functools
import os
import re

from truedoc.classify.blocks import _PAGE_NUMBER
from truedoc.model import Block, BlockKind, Page

_FIRST_INT = re.compile(r"\d{1,4}")
_REACH = 2


def _strip_lines(textpage, top: float, height: float, zone: float) -> list[tuple[float, float, float, float, str]]:
    """The text in a page's top and bottom strips as lines, (y0, y1, x0, x1, text) measured down from the top of its
    box.

    PDFium hands back runs of one font, so "page" and "52" in two weights are two runs; runs whose middles share a
    line and that follow on within a gap of about one and a half times their height are one line."""
    pieces = []
    for i in range(textpage.count_rects()):
        left, bottom, right, upper = textpage.get_rect(i)
        y0, y1 = top - upper, top - bottom
        if y1 <= zone * 1.3 + 12 or y0 >= (height - zone) * 0.97 - 12:
            words = " ".join(textpage.get_text_bounded(left, bottom, right, upper).split())
            if words:
                pieces.append([y0, y1, left, right, words])
    pieces.sort(key=lambda p: ((p[0] + p[1]) / 2, p[2]))
    lines: list[list] = []
    for p in pieces:
        h = max(1.0, p[1] - p[0])
        for line in lines:
            lh = max(1.0, line[1] - line[0])
            if (abs((line[0] + line[1]) / 2 - (p[0] + p[1]) / 2) <= 0.5 * min(h, lh)
                    and -2.0 <= p[2] - line[3] <= 1.5 * max(h, lh)):
                line[0], line[1], line[3] = min(line[0], p[0]), max(line[1], p[1]), max(line[3], p[3])
                line[4] = line[4] + " " + p[4]
                break
        else:
            lines.append(p)
    return [(l[0], l[1], l[2], l[3], l[4]) for l in lines]


@functools.lru_cache(maxsize=256)
def _strip(path: str, stamp: tuple, index: int) -> tuple | None:
    """A page's height and the lines of its top and bottom strips; None when the page has no text layer, lies turned,
    or cannot be read. `stamp` (the file's size and time) keeps an answer from outliving a changed file."""
    try:
        import pypdfium2 as pdfium

        doc = pdfium.PdfDocument(path)
    except Exception:
        return None
    try:
        page = doc[index]
        try:
            if int(page.get_rotation()) % 180:
                return None
            _, bottom, _, top = page.get_cropbox()
            height = top - bottom
            textpage = page.get_textpage()
            try:
                if textpage.count_chars() == 0:
                    return None
                return height, tuple(_strip_lines(textpage, top, height, 0.09 * height))
            finally:
                textpage.close()
        finally:
            page.close()
    except Exception:
        return None
    finally:
        doc.close()


def _distances(path: str, stamp: tuple, index: int) -> frozenset | None:
    """How far each page number a page prints in its strips stands from the page's place in the file: the number
    minus the place, counted from 1."""
    strip = _strip(path, stamp, index)
    if strip is None:
        return None
    height, lines = strip
    zone = 0.09 * height
    found = set()
    for y0, y1, _, _, text in lines:
        if (y1 <= zone * 1.3 or y0 >= (height - zone) * 0.97) and _PAGE_NUMBER.match(text):
            m = _FIRST_INT.search(text)
            if m:
                found.add(int(m.group()) - (index + 1))
    return frozenset(found)


def _file(pdf_page) -> tuple | None:
    """(path, stamp, index, page count) for a page handle, or None when it names no file."""
    parent = getattr(pdf_page, "parent", None)
    path = getattr(parent, "name", None)
    index = getattr(pdf_page, "number", None)
    if not path or index is None:
        return None
    try:
        count = len(parent)
        info = os.stat(path)
    except (TypeError, OSError):
        return None
    return path, (info.st_size, info.st_mtime_ns), index, count


def counts_pages(text: str, pdf_page) -> bool | None:
    """Whether the page number `text`, read in this page's margin, counts pages by the numbers printed beside it."""
    m = _FIRST_INT.search(text)
    where = _file(pdf_page)
    if m is None or where is None:
        return None
    path, stamp, index, count = where
    before = next((d for i in range(index - 1, index - 1 - _REACH, -1)
                   if 0 <= i < count and (d := _distances(path, stamp, i))), None)
    after = next((d for i in range(index + 1, index + 1 + _REACH)
                  if 0 <= i < count and (d := _distances(path, stamp, i))), None)
    if not before or not after:
        return None
    shared = before & after
    if not shared:
        return None
    return int(m.group()) - (index + 1) in shared


def _same(text: str) -> str:
    return " ".join(text.split()).lower()


def runs_beside(text: str, bbox, page_height: float, pdf_page) -> bool | None:
    """Whether a page within two each way prints the same line at the same place - measured down from the top for a
    line in the page's top half, up from the foot for one in its bottom half - as a running head, a section's tab or a
    running foot does. None when no page beside it has a text layer to ask."""
    where = _file(pdf_page)
    if where is None:
        return None
    path, stamp, index, count = where
    want = _same(text)
    top_half = bbox.y0 < page_height / 2
    near = max(4.0, 0.8 * (bbox.y1 - bbox.y0))
    asked = False
    for i in (index - 2, index - 1, index + 1, index + 2):
        if not 0 <= i < count:
            continue
        strip = _strip(path, stamp, i)
        if strip is None:
            continue
        asked = True
        height, lines = strip
        for y0, y1, x0, _, line in lines:
            if _same(line) != want or abs(x0 - bbox.x0) > near:
                continue
            gap = abs(y0 - bbox.y0) if top_half else abs((height - y1) - (page_height - bbox.y1))
            if gap <= near:
                return True
    return False if asked else None


def release_pointers(pdf_page, page: Page, blocks: list[Block]) -> None:
    """Give a margin line taken for the page's number back to the text when the pages beside it show that it counts no
    pages and does not run - whichever rule took it: the zone rule, the layout model's page header or footer, or the
    margin clean-up. Manuscript line numbers count lines, not pages, and stay where their own rule put them."""
    for b in blocks:
        if (b.kind in (BlockKind.PAGE_NUMBER, BlockKind.HEADER, BlockKind.FOOTER) and b.lines
                and b.provenance != "margin-line-number" and _PAGE_NUMBER.match(b.text)
                and counts_pages(b.text, pdf_page) is False
                and runs_beside(b.text, b.bbox, page.height, pdf_page) is False):
            b.kind = BlockKind.TEXT
            b.provenance = "page-pointer"


# The numbers a page prints (E3): read from every line at its edge that TrueDoc leaves out of the body - a running line
# too ("Page 30 | Household Insurance Policy" carries its page's number) - one number to a position, kept only when it
# runs on from the pages beside it.
_PRINTED = re.compile(r"(?<![\w./:\-–,$])(\d{1,4})(?![\w./:\-–%$,])")


def _printed_in(text: str, box) -> list[dict]:
    """Each number standing alone in an edge line, and where along the line it stands: its share of the line's
    characters laid over the line's box."""
    x0, y0, x1, y1 = box
    out = []
    for m in _PRINTED.finditer(text):
        a, b = m.start() / max(1, len(text)), m.end() / max(1, len(text))
        out.append({"value": int(m.group(1)), "number": m.group(1), "x": x0 + (a + b) / 2 * (x1 - x0),
                    "box": [round(v, 1) for v in (x0, y0, x1, y1)]})
    return out


def assign_printed_numbers(pages: list[Page], path: str) -> None:
    """The numbers each page prints, and where each applies: `page.meta["printed_numbers"]`.

    Three rules. **Every edge line is read**, running lines included: the lines at a page's edge TrueDoc leaves out of
    the body are in its decisions (D040), and a number standing alone in one (not part of a date, a code or an amount) is
    a candidate. **A number is kept only when it runs on from the pages beside it**: a page up to two places away prints a
    number as many more as the pages between (the pages counted one each), or twice as many on the same half of the page
    (a spread, two pages printed on one). A section tab at the head of page after page ("2", "2", "2") runs on from
    nothing and is dropped, and so is a form code or a year. **A number belongs to a position**: where a page keeps two,
    one on each half, the second one more than the first, it is a spread, and each applies to its half; otherwise a
    number applies to the page. The pages beside are read from the file's own text in their strips when they were not
    converted in this run (`_strip`), so a single page converted alone is still checked against its neighbours.
    """
    try:
        import pypdfium2 as pdfium

        pdf = pdfium.PdfDocument(path)
        count = len(pdf)
        pdf.close()
        info = os.stat(path)
        stamp = (info.st_size, info.st_mtime_ns)
    except Exception:
        return
    own: dict[int, list[dict]] = {}
    for p in pages:
        found: list[dict] = []
        for d in p.meta.get("decisions") or []:
            if d.get("kind") == "edge-line" and d.get("text") and d.get("bbox") and not d["because"].startswith("a turned"):
                found.extend(_printed_in(d["text"], d["bbox"]))
        own[p.number - 1] = found
    beside: dict[int, list[dict]] = {}

    def numbers_of(i: int) -> list[dict]:
        if i in own:
            return own[i]
        if i not in beside:
            strip = _strip(path, stamp, i) if 0 <= i < count else None
            beside[i] = [] if strip is None else [n for y0, y1, x0, x1, text in strip[1] for n in _printed_in(text, (x0, y0, x1, y1))]
        return beside[i]

    for p in pages:
        i = p.number - 1
        half = p.width / 2
        kept: list[dict] = []
        for c in own.get(i, []):
            left = c["x"] < half
            runs = any(d["value"] - c["value"] == j - i
                       or (d["value"] - c["value"] == 2 * (j - i) and (d["x"] < half) == left)
                       for j in range(i - _REACH, i + _REACH + 1) if j != i and 0 <= j < count
                       for d in numbers_of(j))
            if runs and all(k["value"] != c["value"] for k in kept):
                kept.append(dict(c, left=left))
        lefts = [k for k in kept if k["left"]]
        rights = [k for k in kept if not k["left"]]
        spread = len(kept) == 2 and len(lefts) == 1 and len(rights) == 1 and rights[0]["value"] == lefts[0]["value"] + 1
        p.meta["printed_numbers"] = [{"number": k["number"],
                                      "applies": ("left half" if k["left"] else "right half") if spread else "page",
                                      "box": k["box"]} for k in kept]
