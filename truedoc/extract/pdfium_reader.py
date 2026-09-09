"""Read a page's characters with PDFium instead of PyMuPDF (D007, M18).

PyMuPDF is AGPL or a paid Artifex licence, and D007 keeps AGPL out of the product path; PDFium is
BSD, is what olmOCR, Marker, Docling and MinerU all read through, and the 8 September census found
it reads the same characters as PyMuPDF on all but about twenty of the 1,403 benchmark pages, 2.44
times faster. What that census did not compare is **geometry** - the boxes - and every stage after
extraction (lines, columns, reading order, tables) is built on those, so this reader exists to be
compared before anything is switched.

Two differences from PyMuPDF worth knowing:

* **Coordinates.** PDFium works in PDF space, origin bottom-left, y increasing upwards. PyMuPDF
  reports top-left with y increasing downwards, which is what the rest of TrueDoc assumes, so
  every y is flipped here rather than at the call sites.
* **No lines or spans.** PyMuPDF's rawdict groups characters into lines and spans; PDFium hands
  back a flat run in reading order. TrueDoc already rebuilds lines from geometry for OCR layers
  (D010), so the machinery exists, but it is a real difference and not a formatting detail.

Nothing here is wired into the converter yet. `bench/tools/reader_compare.py` is what says whether
it should be.
"""
from __future__ import annotations

import ctypes
from dataclasses import dataclass

import pypdfium2 as pdfium
import pypdfium2.raw as raw


@dataclass
class RawChar:
    """One character as the rest of TrueDoc expects it: top-left coordinates, PyMuPDF's shape."""
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    origin_x: float
    origin_y: float
    font: str
    size: float
    weight: int
    color: int          # 0xRRGGBB
    unmapped: bool      # PDFium could not map the glyph to Unicode (a maths font's raw code)


def _font_info(textpage, i: int) -> tuple[str, int]:
    flags = ctypes.c_int(0)
    buf = ctypes.create_string_buffer(256)
    n = raw.FPDFText_GetFontInfo(textpage, i, buf, 256, ctypes.byref(flags))
    if not n:
        return "", 0
    return buf.raw[: max(0, n - 1)].decode("utf-8", "replace"), int(flags.value)


def _fill_colour(textpage, i: int) -> int:
    r = ctypes.c_uint(0); g = ctypes.c_uint(0); b = ctypes.c_uint(0); a = ctypes.c_uint(0)
    if not raw.FPDFText_GetFillColor(textpage, i, ctypes.byref(r), ctypes.byref(g),
                                     ctypes.byref(b), ctypes.byref(a)):
        return 0
    return (int(r.value) << 16) | (int(g.value) << 8) | int(b.value)


def page_chars(pdf_page, page_height: float, *, loose: bool = False) -> list[RawChar]:
    """Every character on the page, in PDFium's reading order, in top-left coordinates.

    `loose` asks PDFium for the box the font's metrics describe rather than the glyph's own
    extent; PyMuPDF's default is closer to the tight box, so the comparison uses tight.
    """
    textpage = raw.FPDFText_LoadPage(pdf_page)
    if not textpage:
        return []
    out: list[RawChar] = []
    try:
        n = raw.FPDFText_CountChars(textpage)
        left = ctypes.c_double(0); right = ctypes.c_double(0)
        bottom = ctypes.c_double(0); top = ctypes.c_double(0)
        ox = ctypes.c_double(0); oy = ctypes.c_double(0)
        for i in range(n):
            code = raw.FPDFText_GetUnicode(textpage, i)
            if raw.FPDFText_IsGenerated(textpage, i):
                continue        # a space PDFium inserted itself, not one the page draws
            getter = raw.FPDFText_GetLooseCharBox if loose else raw.FPDFText_GetCharBox
            if loose:
                # the loose form takes an FS_RECTF, not four doubles
                rect = raw.FS_RECTF()
                if not getter(textpage, i, ctypes.byref(rect)):
                    continue
                l, r_, b_, t_ = rect.left, rect.right, rect.bottom, rect.top
            else:
                if not getter(textpage, i, ctypes.byref(left), ctypes.byref(right),
                              ctypes.byref(bottom), ctypes.byref(top)):
                    continue
                l, r_, b_, t_ = left.value, right.value, bottom.value, top.value
            raw.FPDFText_GetCharOrigin(textpage, i, ctypes.byref(ox), ctypes.byref(oy))
            font, _flags = _font_info(textpage, i)
            try:
                unmapped = bool(raw.FPDFText_HasUnicodeMapError(textpage, i))
            except Exception:
                unmapped = False
            out.append(RawChar(
                text=chr(code) if code else "",
                # PDF space is bottom-left; TrueDoc is top-left, so y flips and top/bottom swap.
                x0=float(min(l, r_)), y0=float(page_height - max(t_, b_)),
                x1=float(max(l, r_)), y1=float(page_height - min(t_, b_)),
                origin_x=float(ox.value), origin_y=float(page_height - oy.value),
                font=font,
                size=float(raw.FPDFText_GetFontSize(textpage, i)),
                weight=int(raw.FPDFText_GetFontWeight(textpage, i)),
                color=_fill_colour(textpage, i),
                unmapped=unmapped,
            ))
    finally:
        raw.FPDFText_ClosePage(textpage)
    return out


def group_lines(chars: list[RawChar]) -> list[list[RawChar]]:
    """Cut the flat character run into lines, the one thing PyMuPDF gives us for nothing.

    PyMuPDF's rawdict arrives already grouped into blocks, lines and spans - its own layout
    analysis, which TrueDoc has been inheriting free. PDFium hands back a flat run in reading
    order, so the lines have to be cut from geometry. Two signals do it, and they are the same
    ones the OCR-layer reassembly uses (D010): the baseline moves, or the pen jumps backwards by
    more than a word, which is what starting a new line looks like from the character's side.

    This is deliberately plain. Everything clever about lines - the gutter splits, the symbol
    folds, the satellite attachment - already happens downstream on whatever lines it is given.
    """
    out: list[list[RawChar]] = []
    current: list[RawChar] = []
    baseline = 0.0
    for c in chars:
        size = c.size or 10.0
        if not current:
            current, baseline = [c], c.origin_y
            continue
        moved = abs(c.origin_y - baseline) > 0.3 * size
        backwards = c.x0 < current[-1].x0 - 2.0 * size
        if moved or backwards:
            out.append(current)
            current, baseline = [c], c.origin_y
            continue
        current.append(c)
        # Follow a drifting baseline (a slightly rotated scan) rather than snapping to the first.
        baseline = 0.7 * baseline + 0.3 * c.origin_y
    if current:
        out.append(current)
    return out


def read(path: str, page_index: int, *, loose: bool = False) -> list[RawChar]:
    """Convenience: open the file, read one page's characters, close it."""
    doc = pdfium.PdfDocument(path)
    try:
        page = doc[page_index]
        height = page.get_height()
        return page_chars(page, height, loose=loose)
    finally:
        doc.close()
