"""Hand `extract_page` the same shape PyMuPDF's rawdict has, built through PDFium (D007, M18).

PyMuPDF is AGPL or a paid Artifex licence and D007 keeps AGPL out of the product path. Everything
`extract_page` needs from PyMuPDF arrives as one `rawdict` structure - blocks, lines, spans, and a
box and origin per character - so the least invasive way to read through PDFium instead is to
rebuild that structure rather than rewrite the stage that consumes it.

**The division of labour.** pdftext (Apache-2.0) does the one thing PDFium does not: deciding which
characters form a span, which spans form a line, and in what order they read. Every *geometric and
font fact* is then read straight from PDFium by the character index pdftext carries (`char_idx`),
rather than taken from pdftext's own output. That split matters, because pdftext rotates its
coordinates into display space and PyMuPDF does not (see below).

**Coordinates.** PyMuPDF reports text in *unrotated* page space, with the origin at the top-left of
the crop box and y increasing downwards; `extract_page` applies the rotation itself. PDFium reports
PDF space - origin bottom-left, y upwards - so each value is flipped about the crop box here:
`x - crop.x0`, `crop.y1 - y`. Measured against PyMuPDF on an unrotated arXiv page and a 90-degree
rotated timetable, character origins agree to a median of 0.000pt on both.

**What is read per character.** The metric box (`FPDFText_GetLooseCharBox`, PyMuPDF's `bbox`), the
drawn outline (`FPDFText_GetCharBox`, what PyMuPDF needs `TEXT_ACCURATE_BBOXES` for, kept as
`ink`), the true baseline origin (`FPDFText_GetCharOrigin`), the fill colour
(`FPDFText_GetFillColor`), and whether PDFium invented the character to fill a gap rather than
finding it drawn (`FPDFText_IsGenerated`, kept as `generated`, which is what PyMuPDF needs
`get_texttrace` for).

**Font flags are translated, not passed through.** PDFium reports the PDF font descriptor's flags,
whose bits mean different things from the span flags PyMuPDF reports: PDFium's 0x2 is Serif where
PyMuPDF's 0x2 is italic. `_mupdf_flags` maps between them, and takes bold from the font's weight.

**Measured differences from PyMuPDF that remain.**

* The metric box is about 1.3pt shorter on a 9pt font - PDFium's top sits 1.05pt lower and its
  bottom 0.29pt higher - because the two engines take ascent and descent from different places.
  Systematic, and consistent within a page.
* Characters whose font has no usable ToUnicode come back as the raw code (a hyphen reading as
  `\\x02`) where PyMuPDF resolves them by glyph name: 2 characters in 1,896 on the arXiv page.
  `FPDFText_HasUnicodeMapError` flags them, and they are kept in `map_error` for a later pass.
* Reading order can differ where two engines group a page differently - about 70 characters of
  1,141 on the rotated timetable, all of them present in both, ordered differently.

Switched on with the environment variable `TRUEDOC_READER=pdftext`, and off by default. That is
deliberately a blunt switch for an experiment rather than a settled option: the question it exists
to answer is what the benchmark score does, and only a scored run can answer it.
"""
from __future__ import annotations

import ctypes
import math
import os

_DESCENDER = 0.21       # last-resort baseline estimate, used only where PDFium will not give an origin
_BOLD_WEIGHT = 600.0    # font weight at or above which a face is treated as bold
_LINE_GAP = 1.5         # a gap this many times the font size ends a line (see _split_at_gaps)

# One page's built structure is wanted by several stages (the main read, the maths ink pass, the
# ruled-table cell reader), so the last few are kept rather than parsed again. Plain dicts only:
# no PDFium handle is held open.
_CACHE: dict[tuple, dict] = {}
_CACHE_MAX = 4


def enabled() -> bool:
    return os.environ.get("TRUEDOC_READER", "").strip().lower() == "pdftext"


def available() -> bool:
    try:
        import pdftext.extraction  # noqa: F401
        import pypdfium2  # noqa: F401
    except Exception:
        return False
    return True


def _mupdf_flags(font: dict, superscript: bool) -> int:
    """PDFium's font-descriptor flags in the bits PyMuPDF's span flags use.

    PyMuPDF: 1 superscript, 2 italic, 4 serif, 8 mono, 16 bold. PDFium reports the PDF font
    descriptor instead: 0x1 fixed pitch, 0x2 serif, 0x40 italic, 0x40000 force bold. Passing one
    through as the other reads a serif face as italic, which is what this exists to stop.
    """
    pf = int(font.get("flags") or 0)
    name = str(font.get("name") or "").lower()
    try:
        weight = float(font.get("weight") or 0.0)
    except (TypeError, ValueError):
        weight = 0.0
    out = 1 if superscript else 0
    if pf & 0x40 or "italic" in name or "oblique" in name:
        out |= 2
    if pf & 0x2:
        out |= 4
    if pf & 0x1:
        out |= 8
    if pf & 0x40000 or weight >= _BOLD_WEIGHT:
        out |= 16
    return out


def _order(path: str, page_number: int) -> dict | None:
    """pdftext's grouping: blocks, lines and spans, each character as its PDFium index."""
    try:
        from pdftext.extraction import dictionary_output
    except Exception:
        return None
    try:
        pages = dictionary_output(path, page_range=[page_number - 1], keep_chars=True)
    except Exception:
        return None
    return pages[0] if pages else None


def _geometry(path: str, page_number: int, wanted: set[int]) -> dict[int, dict]:
    """Every geometric fact PDFium holds for the wanted characters, in PyMuPDF's space."""
    import pypdfium2 as pdfium
    import pypdfium2.raw as raw_api

    out: dict[int, dict] = {}
    doc = pdfium.PdfDocument(path)
    try:
        page = doc[page_number - 1]
        crop = page.get_cropbox()
        x_off, y_top = float(crop[0]), float(crop[3])
        textpage = page.get_textpage()
        try:
            tp = textpage.raw
            ox, oy = ctypes.c_double(), ctypes.c_double()
            il, ir, ib, it = (ctypes.c_double() for _ in range(4))
            fr, fg, fb, fa = (ctypes.c_uint() for _ in range(4))
            loose = raw_api.FS_RECTF()
            for i in wanted:
                box = None
                if raw_api.FPDFText_GetLooseCharBox(tp, i, loose):
                    box = _flip(loose.left, loose.top, loose.right, loose.bottom, x_off, y_top)
                ink = None
                # note the argument order: left, right, bottom, top
                if raw_api.FPDFText_GetCharBox(tp, i, il, ir, ib, it):
                    ink = _flip(il.value, it.value, ir.value, ib.value, x_off, y_top)
                origin = None
                if raw_api.FPDFText_GetCharOrigin(tp, i, ox, oy):
                    origin = (ox.value - x_off, y_top - oy.value)
                color = 0
                if raw_api.FPDFText_GetFillColor(tp, i, fr, fg, fb, fa):
                    color = (fr.value << 16) | (fg.value << 8) | fb.value
                out[i] = {
                    "bbox": box,
                    "ink": ink,
                    "origin": origin,
                    "color": color,
                    "generated": raw_api.FPDFText_IsGenerated(tp, i) == 1,
                    "map_error": raw_api.FPDFText_HasUnicodeMapError(tp, i) == 1,
                }
        finally:
            textpage.close()
    finally:
        doc.close()
    return out


def _flip(x0: float, y0: float, x1: float, y1: float, x_off: float, y_top: float) -> tuple:
    """A PDF-space rectangle in PyMuPDF's top-left, y-down page space."""
    ax0, ax1 = x0 - x_off, x1 - x_off
    ay0, ay1 = y_top - y0, y_top - y1
    return (min(ax0, ax1), min(ay0, ay1), max(ax0, ax1), max(ay0, ay1))


def _stamp(path: str) -> tuple:
    try:
        st = os.stat(path)
        return (st.st_mtime_ns, st.st_size)
    except OSError:
        return (0, 0)


def build(path: str, page_number: int) -> dict | None:
    """A rawdict-shaped reading of one page (1-based), or None if pdftext cannot read it."""
    key = (os.path.abspath(path), page_number, _stamp(path), _gap_limit())
    hit = _CACHE.get(key)
    if hit is not None:
        return hit
    built = _build(path, page_number)
    if built is not None:
        if len(_CACHE) >= _CACHE_MAX:
            _CACHE.pop(next(iter(_CACHE)))
        _CACHE[key] = built
    return built


def _build(path: str, page_number: int) -> dict | None:
    page = _order(path, page_number)
    if page is None:
        return None
    grouped = page.get("blocks") or []
    try:
        rotation = int(page.get("rotation") or 0) % 360
    except (TypeError, ValueError):
        rotation = 0

    wanted: set[int] = set()
    for block in grouped:
        for line in block.get("lines") or []:
            for span in line.get("spans") or []:
                for ch in span.get("chars") or []:
                    idx = ch.get("char_idx")
                    if isinstance(idx, int):
                        wanted.add(idx)
    try:
        geom = _geometry(path, page_number, wanted) if wanted else {}
    except Exception:
        return None

    blocks = []
    for block in grouped:
        lines = []
        for line in block.get("lines") or []:
            spans = []
            for span in line.get("spans") or []:
                font = span.get("font") or {}
                size = float(font.get("size") or 0.0)
                chars = []
                colors: dict[int, int] = {}
                for ch in span.get("chars") or []:
                    text = str(ch.get("char", ""))
                    if not text:
                        continue
                    g = geom.get(ch.get("char_idx"))
                    box = (g or {}).get("bbox")
                    if box is None:
                        b = ch.get("bbox") or [0.0, 0.0, 0.0, 0.0]
                        box = (float(b[0]), float(b[1]), float(b[2]), float(b[3]))
                    origin = (g or {}).get("origin")
                    if origin is None:
                        # No origin from PDFium: fall back on the descender share of the box.
                        origin = (box[0], box[3] - _DESCENDER * (size or (box[3] - box[1])))
                    color = (g or {}).get("color", 0)
                    colors[color] = colors.get(color, 0) + 1
                    chars.append({
                        "c": text,
                        "bbox": box,
                        "origin": origin,
                        "ink": (g or {}).get("ink"),
                        "generated": bool((g or {}).get("generated")),
                        "map_error": bool((g or {}).get("map_error")),
                    })
                if not chars:
                    continue
                spans.append({
                    "font": str(font.get("name") or ""),
                    "size": size,
                    "flags": _mupdf_flags(font, bool(span.get("superscript"))),
                    # PyMuPDF reports one colour per span; take the span's most common.
                    "color": max(colors.items(), key=lambda kv: kv[1])[0] if colors else 0,
                    "chars": chars,
                })
            if not spans:
                continue
            direction = _line_dir(line, rotation)
            for piece in _split_at_gaps(spans, direction):
                lines.append({
                    "dir": direction,
                    "bbox": _union(piece),
                    "spans": piece,
                })
        if lines:
            blocks.append({"type": 0, "lines": lines})
    # The marker tells the stages downstream that the extra per-character keys ("ink",
    # "generated") are present, so they can be read from here instead of from MuPDF.
    return {"blocks": blocks, "source": "pdftext"}


def _gap_limit() -> float:
    """How wide a gap ends a line, as a multiple of the font size. 0 disables splitting."""
    try:
        return float(os.environ.get("TRUEDOC_LINE_GAP", _LINE_GAP))
    except (TypeError, ValueError):
        return _LINE_GAP


def _split_at_gaps(spans: list, direction: tuple[float, float] = (1.0, 0.0)) -> list:
    """Cut a run of text into the pieces the layout stage expects.

    pdftext reports one line per visual row: a table row arrives as
    "Jagger 23.0 Jagger 23.6 2137 32.3". TrueDoc's column finder needs the cells
    separately, because it reads columns off where each fragment starts and ends -
    given whole rows it finds no columns and the table is lost. Splitting on the gap
    is worth 18 checks of the quick gate on its own (72 to 90 of 128).

    The gap is measured along the line's own direction, so the test holds for the
    vertical text of a rotated page as well as for level text.

    pdftext also welds text at quite different heights into one line - a journal
    page's "G Model" and "ARTICLE IN PRESS" arrive as one 24pt-tall line spanning
    the page. A companion rule that ended a line on a baseline step was written and
    measured, and moved the gate by nothing at any threshold from 0.3 to 0.6, so it
    was taken out again rather than carried as an unearned knob.

    This is deliberately *not* an attempt to reproduce MuPDF's grouping. Measured over
    23 table and multi-column pages, MuPDF's own line breaks match neither a gap rule
    (best case 5,068 disagreements in 67,591 adjacent pairs) nor the PDF's text objects
    (6,345); it keeps characters together across a 95x gap and splits at small ones,
    because it follows the file's text-showing runs. Agreement with it is not the goal,
    and is a metric this project has already found worthless. The threshold below was
    chosen on the benchmark score.
    """
    limit = _gap_limit()
    if limit <= 0:
        return [spans]
    dx, dy = direction
    flat = [(si, c) for si, sp in enumerate(spans) for c in sp["chars"]]
    cuts: set[int] = set()
    prev = None       # (index in flat, end along the line, scale)
    for i, (si, c) in enumerate(flat):
        if c["c"].isspace():
            continue
        x0, y0, x1, y1 = c["bbox"]
        ends = [x0 * dx + y0 * dy, x1 * dx + y0 * dy, x0 * dx + y1 * dy, x1 * dx + y1 * dy]
        start, end = min(ends), max(ends)
        # Not the reported size: a Type 3 font reports its matrix scale instead (1.0 here,
        # which would make every gap look enormous), so take the taller of the two.
        scale = max(float(spans[si]["size"] or 0.0), y1 - y0)
        if prev is not None and scale > 0 and start - prev[1] >= limit * max(scale, prev[2]):
            cuts.add(i)
        prev = (i, end, scale)
    if not cuts:
        return [spans]
    pieces, current = [], []
    for i, (si, c) in enumerate(flat):
        if i in cuts and current:
            pieces.append(current)
            current = []
        current.append((si, c))
    if current:
        pieces.append(current)
    out = []
    for piece in pieces:
        # blanks stranded at either end of a cut belong to the gap, not to the text
        while piece and piece[0][1]["c"].isspace():
            piece = piece[1:]
        while piece and piece[-1][1]["c"].isspace():
            piece = piece[:-1]
        rebuilt: list[tuple[int, list]] = []
        for si, c in piece:
            if rebuilt and rebuilt[-1][0] == si:
                rebuilt[-1][1].append(c)
            else:
                rebuilt.append((si, [c]))
        made = [dict(spans[si], chars=chars) for si, chars in rebuilt if chars]
        if made:
            out.append(made)
    return out or [spans]


def clipped_blocks(path: str, page_number: int, rect) -> list | None:
    """What PyMuPDF's `get_text("dict", clip=rect)` returns, for the ruled-table cell reader.

    Only the keys that reader touches are filled: a bbox and a text per line. A character
    counts as inside when its box overlaps the rectangle, which is how MuPDF's clip behaves
    for the cell-sized rectangles this is asked for.
    """
    built = build(path, page_number)
    if built is None:
        return None
    x0, y0, x1, y1 = (float(rect[0]), float(rect[1]), float(rect[2]), float(rect[3]))
    blocks = []
    for block in built.get("blocks", []):
        lines = []
        for ln in block.get("lines", []):
            spans = []
            for sp in ln.get("spans", []):
                inside = [c for c in sp.get("chars", [])
                          if c["bbox"][0] < x1 and c["bbox"][2] > x0 and c["bbox"][1] < y1 and c["bbox"][3] > y0]
                if inside:
                    spans.append({"text": "".join(c["c"] for c in inside), "chars": inside})
            if not spans:
                continue
            xs = [c["bbox"][0] for s in spans for c in s["chars"]]
            ys = [c["bbox"][1] for s in spans for c in s["chars"]]
            xe = [c["bbox"][2] for s in spans for c in s["chars"]]
            ye = [c["bbox"][3] for s in spans for c in s["chars"]]
            lines.append({"bbox": (min(xs), min(ys), max(xe), max(ye)), "spans": spans})
        if lines:
            blocks.append({"lines": lines})
    return blocks


def _line_dir(line: dict, page_rotation: int = 0) -> tuple[float, float]:
    """PyMuPDF's writing-direction vector from pdftext's char angle.

    Two steps. pdftext carries `FPDFText_GetCharAngle`, counter-clockwise radians in PDF space; the
    y flip turns a counter-clockwise angle into a clockwise one, so within pdftext's own display
    space the direction is (cos, -sin). But pdftext then rotates the whole page into display space
    and PyMuPDF does not, so that has to be undone: pdftext maps an unrotated (x, y) to
    (-y, x) at 90 degrees, (-x, -y) at 180 and (y, -x) at 270, and this inverts it. A level line on
    a 90-degree page reads (0, -1), which is what PyMuPDF reports for it.
    """
    try:
        theta = float(line.get("rotation") or 0.0)
    except (TypeError, ValueError):
        theta = 0.0
    a, b = (1.0, 0.0) if not theta else (math.cos(theta), -math.sin(theta))
    if page_rotation == 90:
        a, b = b, -a
    elif page_rotation == 180:
        a, b = -a, -b
    elif page_rotation == 270:
        a, b = -b, a
    return (round(a, 6) + 0.0, round(b, 6) + 0.0)


def _union(spans: list) -> tuple:
    xs0 = [c["bbox"][0] for s in spans for c in s["chars"]]
    ys0 = [c["bbox"][1] for s in spans for c in s["chars"]]
    xs1 = [c["bbox"][2] for s in spans for c in s["chars"]]
    ys1 = [c["bbox"][3] for s in spans for c in s["chars"]]
    return (min(xs0), min(ys0), max(xs1), max(ys1))
