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
import re
import unicodedata

from truedoc.extract import pdfium_objects

_DESCENDER = 0.21       # last-resort baseline estimate, used only where PDFium will not give an origin
_TEX_BOLD = re.compile(r"^(?:[a-z]{6}\+)?(?:cmb|cmbx|cmbsy|cmmib|cmssbx|sfbx|sfbi|eufb)\d")   # TeX's bold faces
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
    out = 1 if superscript else 0
    if pf & 0x40 or "italic" in name or "oblique" in name:
        out |= 2
    if pf & 0x2:
        out |= 4
    if pf & 0x1:
        out |= 8
    # Bold is a matter of the name, not of PDFium's weight. The weight comes from the descriptor's
    # stem width, and on TeX's fonts that reads 640-820 for every face - CMR, CMTI, CMSY alike -
    # so every line of an arXiv page was bold and its run-in theorem headings became headings.
    # Measured against MuPDF's own flag over 7,469 (page, font) pairs: a weight of 600 disagrees
    # on 2,265, "bold" in the name on 369, the name plus TeX's bold faces on 273. MuPDF does not
    # call "Black" or "Heavy" bold, and calls CMBX bold only when the embedded program says so,
    # which nothing PDFium reports can tell; the name is the best of what can be seen.
    if pf & 0x40000 or "bold" in name or _TEX_BOLD.match(name):
        out |= 16
    return out


# TeX's maths symbol fonts have no useful ToUnicode, and the two libraries part company on what to
# do about it: MuPDF resolves the glyph *name* through the Adobe Glyph List, PDFium hands back the
# glyph's *code* as if it were a character - "k" for the parallel sign, "h" and "i" for the angle
# brackets, a backtick for the script ell. Run 66 lost 91 arXiv checks to that: the maths rebuild
# never saw a single symbol. These are the standard OMS (cmsy) and OML (cmmi) encodings, code to
# the character the glyph name would have given; only codes that differ from ASCII are listed, and
# the table is consulted only where PDFium itself reports the mapping broken (`map_error`).
_OMS: dict[int, str] = {
    0x00: "−", 0x01: "⋅", 0x02: "×", 0x03: "∗", 0x04: "÷", 0x05: "⋄",
    0x06: "±", 0x07: "∓", 0x08: "⊕", 0x09: "⊖", 0x0a: "⊗", 0x0b: "⊘",
    0x0c: "⊙", 0x0d: "◯", 0x0e: "∘", 0x0f: "∙", 0x10: "≍", 0x11: "≡",
    0x12: "⊆", 0x13: "⊇", 0x14: "≤", 0x15: "≥", 0x16: "≼", 0x17: "≽",
    0x18: "∼", 0x19: "≈", 0x1a: "⊂", 0x1b: "⊃", 0x1c: "≪", 0x1d: "≫",
    0x1e: "≺", 0x1f: "≻", 0x20: "←", 0x21: "→", 0x22: "↑", 0x23: "↓",
    0x24: "↔", 0x25: "↗", 0x26: "↘", 0x27: "≃", 0x28: "⇐", 0x29: "⇒",
    0x2a: "⇑", 0x2b: "⇓", 0x2c: "⇔", 0x2d: "↖", 0x2e: "↙", 0x2f: "∝",
    0x30: "′", 0x31: "∞", 0x32: "∈", 0x33: "∋", 0x34: "△", 0x35: "▽",
    # 0x36 is the negation slash, a combining mark that MuPDF hangs on the character before it
    # ("0̸"); 0x37, the mapsto stem, MuPDF leaves as "7" for the maths stage to join to its arrow
    # (`reconstruct._merge_mapsto`), so it is deliberately absent here.
    0x36: "̸", 0x38: "∀", 0x39: "∃", 0x3a: "¬", 0x3b: "∅", 0x3c: "ℜ",
    0x3d: "ℑ", 0x3e: "⊤", 0x3f: "⊥", 0x40: "ℵ",
    0x5b: "∪", 0x5c: "∩", 0x5d: "⊎", 0x5e: "∧", 0x5f: "∨", 0x60: "⊢",
    0x61: "⊣", 0x62: "⌊", 0x63: "⌋", 0x64: "⌈", 0x65: "⌉", 0x66: "{",
    0x67: "}", 0x68: "⟨", 0x69: "⟩", 0x6a: "|", 0x6b: "∥", 0x6c: "↕",
    0x6d: "⇕", 0x6e: "\\", 0x6f: "≀", 0x70: "√", 0x71: "∐", 0x72: "∇",
    0x73: "∫", 0x74: "⊔", 0x75: "⊓", 0x76: "⊑", 0x77: "⊒", 0x78: "§",
    0x79: "†", 0x7a: "‡", 0x7b: "¶", 0x7c: "♣", 0x7d: "♦", 0x7e: "♥",
    0x7f: "♠",
}
_OML: dict[int, str] = {
    0x00: "Γ", 0x01: "Δ", 0x02: "Θ", 0x03: "Λ", 0x04: "Ξ", 0x05: "Π",
    0x06: "Σ", 0x07: "Υ", 0x08: "Φ", 0x09: "Ψ", 0x0a: "Ω", 0x0b: "α",
    0x0c: "β", 0x0d: "γ", 0x0e: "δ", 0x0f: "ϵ", 0x10: "ζ", 0x11: "η",
    0x12: "θ", 0x13: "ι", 0x14: "κ", 0x15: "λ", 0x16: "μ", 0x17: "ν",
    0x18: "ξ", 0x19: "π", 0x1a: "ρ", 0x1b: "σ", 0x1c: "τ", 0x1d: "υ",
    0x1e: "φ", 0x1f: "χ", 0x20: "ψ", 0x21: "ω", 0x22: "ε", 0x23: "ϑ",
    0x24: "ϖ", 0x25: "ϱ", 0x26: "ς", 0x27: "ϕ", 0x28: "↼", 0x29: "↽",
    0x2a: "⇀", 0x2b: "⇁", 0x2c: "↪", 0x2d: "↩", 0x2e: "▹", 0x2f: "◃",
    0x3a: ".", 0x3b: ",", 0x3c: "<", 0x3d: "/", 0x3e: ">", 0x3f: "⋆", 0x40: "∂",
    0x5b: "♭", 0x5c: "♮", 0x5d: "♯", 0x5e: "⌣", 0x5f: "⌢", 0x60: "ℓ",
    0x7b: "ı", 0x7c: "ȷ", 0x7d: "℘",
}


# The AMS symbol fonts, measured rather than transcribed: over the 75 benchmark pages that use
# them, every code PDFium could not map was matched by position against the character MuPDF
# reads there (bench/out, 10 Sept). Only codes seen at least three times and consistent with the
# msam/msbm layouts are listed; a code MuPDF itself leaves raw ("9", "K", "[") stays raw.
_MSAM: dict[int, str] = {
    0x03: "□", 0x09: "⟲", 0x0d: "⊩", 0x2c: "≜", 0x2e: "≲", 0x36: "⩽", 0x3e: "⩾",
}
_MSBM: dict[int, str] = {
    0x7e: "ℏ",
}


def _tex_symbol(font: str, text: str) -> str | None:
    """The character MuPDF's glyph-name lookup would give for a raw TeX symbol-font code."""
    if len(text) != 1 or ord(text) > 0x7f:
        return None
    f = font.upper()
    if "CMSY" in f or "CMBSY" in f:
        return _OMS.get(ord(text))
    if "CMMI" in f:
        return _OML.get(ord(text))
    if "MSAM" in f:
        return _MSAM.get(ord(text))
    if "MSBM" in f:
        return _MSBM.get(ord(text))
    return None


def _looks_like_hyphen(g: dict | None) -> bool:
    """A control character whose drawn outline is a short flat bar a quarter-em up: a hyphen.

    Some producers' ToUnicode tables map the hyphen glyph to U+0002. MuPDF ignores a mapping into
    the control range and falls back on the glyph name; PDFium trusts it. Every end-of-line hyphen
    on such a page then arrives as U+0002, and the hyphenation repair - which looks for "-" - never
    rejoins a broken word: "Ipsilat\\x02" and "eral" instead of "Ipsilateral". Measured on two
    fonts (an AdvTT TrueType subset and CMR12): 0.26-0.32 em wide, 0.05-0.08 em tall, centred
    0.22-0.27 em above the baseline. Nothing else in a text font has that shape.
    """
    if not g or not g.get("ink") or not g.get("size") or not g.get("origin"):
        return False
    size = float(g["size"])
    x0, y0, x1, y1 = g["ink"]
    w, h = (x1 - x0) / size, (y1 - y0) / size
    rise = (float(g["origin"][1]) - (y0 + y1) / 2.0) / size   # y grows downwards
    return h <= 0.14 and 0.12 <= w <= 0.7 and 0.1 <= rise <= 0.5


def _as_mupdf_would(text: str, font: str, g: dict | None) -> str:
    """PDFium's reading of a character, corrected to what MuPDF delivers for the same glyph."""
    if g and g.get("map_error"):
        mapped = _tex_symbol(font, text)
        if mapped is not None:
            return mapped
    elif text == "\x02":
        # PDFium's own mark for a hyphen it recognised at a line end, whatever glyph drew it.
        # Measured over the benchmark: 4,915 such characters on 691 pages, and MuPDF reads a
        # hyphen at 4,033 of them (most of the rest it does not see at all). The shape test below
        # had been the only route, and it fails on a Type 3 font, whose glyph box PDFium reports
        # from the font matrix: a scanned-era paper's "tech-" then read as "techΘ", the code
        # taken for the cmr Theta, and no line of it joined its paragraph (09f90a8f).
        return "-"
    if len(text) == 1 and ord(text) < 0x20 and not text.isspace() and _looks_like_hyphen(g):
        return "-"
    return text


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
            matrix = raw_api.FS_MATRIX()
            scales: dict[int, float] = {}      # text object -> the scale its matrix applies
            # Which drawn object each character belongs to, and where that object comes in the
            # painting order - what the hidden-text rules (D011) used MuPDF's text trace for. The
            # walk has to happen on this very page load: pypdfium2 reloads the page on every
            # `doc[i]`, and object pointers do not survive a reload. The order numbers do.
            handles: dict[int, int] = {}
            try:
                pdfium_objects.walk_page(raw_api, page, handles)
            except Exception:
                handles = {}
            invisible_mode = getattr(raw_api, "FPDF_TEXTRENDERMODE_INVISIBLE", 3)
            count = raw_api.FPDFText_CountChars(tp)
            other = raw_api.FS_RECTF()

            def _shares_glyph(raw_api, tp, i, mine, count) -> bool:
                """True when a neighbouring character has this one's loose box: a ligature.

                PDFium reports one "fi" glyph as two characters with the same box and origin
                (measured: every shared box on two pages was also a shared origin, and the pairs
                were fi and ff, plus the rotated arXiv watermark that the level-text test
                already excludes)."""
                for j in (i - 1, i + 1):
                    if 0 <= j < count and raw_api.FPDFText_GetLooseCharBox(tp, j, other):
                        if abs(other.left - mine.left) < 1e-3 and abs(other.right - mine.right) < 1e-3:
                            return True
                return False

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
                code = raw_api.FPDFText_GetUnicode(tp, i)
                map_error = raw_api.FPDFText_HasUnicodeMapError(tp, i) == 1
                # The right edge is the glyph's advance, which is what MuPDF reports. PDFium's loose
                # box is not quite that: on a glyph whose ink overhangs its advance - the letter f
                # above all - it runs further right, 0.44pt on a 7pt line, and the word builder's
                # gap rule then reads "of the" as one word. Measured on a small-print page: the
                # loose box matches MuPDF's right edge to 0.007pt at p95, origin plus advance to
                # 0.000, and 56 of the 68 glyphs that differ are f. Level text only; a turned
                # page's advance runs the other way and keeps the loose box.
                # ... and not on a ligature. One glyph "fi" is reported as two characters sharing
                # its box and origin; the advance of a lone f is narrower than the ligature, so
                # taking it opened a gap after the f and "fixtures" read "fi xtures" (12 such glyphs
                # on that page, 36 on an arXiv one). A character whose neighbour shares its box
                # keeps the loose box.
                # ... and not on a character PDFium could not map to Unicode. The width lookup
                # goes by Unicode, back to a character code, and for a code with no Unicode it
                # answers for some other glyph: cmsy's mapstochar (code 0x37, no mapping) was
                # given the minus sign's advance, its box grew to the minus's box, and the
                # ligature rule above then took the minus for the second half of a ligature and
                # zeroed it - so "\longmapsto" lost its shaft (2503.09133). The loose box PDFium
                # computes from the code itself is right for these.
                if (box is not None and origin is not None and not map_error
                        and raw_api.FPDFText_GetMatrix(tp, i, matrix)
                        and abs(matrix.b) < 1e-6 and abs(matrix.c) < 1e-6
                        and not _shares_glyph(raw_api, tp, i, loose, count)):
                    text_obj = raw_api.FPDFText_GetTextObject(tp, i)
                    font = raw_api.FPDFTextObj_GetFont(text_obj) if text_obj else None
                    adv_w = ctypes.c_float()
                    if font and code and raw_api.FPDFFont_GetGlyphWidth(font, code, raw_api.FPDFText_GetFontSize(tp, i), adv_w):
                        advance = adv_w.value * (math.hypot(matrix.b, matrix.d) or 1.0)
                        if advance > 0:
                            box = (box[0], box[1], max(box[0], origin[0] + advance), box[3])
                color, alpha = 0, 1.0
                if raw_api.FPDFText_GetFillColor(tp, i, fr, fg, fb, fa):
                    color = (fr.value << 16) | (fg.value << 8) | fb.value
                    alpha = fa.value / 255.0
                obj = raw_api.FPDFText_GetTextObject(tp, i)
                order, invisible = -1, False
                if obj:
                    order = handles.get(ctypes.cast(obj, ctypes.c_void_p).value, -1)
                    try:
                        invisible = raw_api.FPDFTextObj_GetTextRenderMode(obj) == invisible_mode
                    except Exception:
                        invisible = False
                out[i] = {
                    "bbox": box,
                    "ink": ink,
                    "origin": origin,
                    "color": color,
                    "alpha": alpha,
                    "order": order,
                    "invisible": invisible,
                    "size": _drawn_size(raw_api, tp, i, matrix, scales),
                    "generated": raw_api.FPDFText_IsGenerated(tp, i) == 1,
                    "map_error": map_error,
                    "code": code,
                    # the writing direction, as PDFium measures it: radians in the y-down page
                    # space, so (cos, sin) is MuPDF's direction vector (measured, see _line_dir)
                    "angle": float(raw_api.FPDFText_GetCharAngle(tp, i)),
                }
        finally:
            textpage.close()
    finally:
        doc.close()
    return out


def _divide_shared_boxes(chars: list) -> None:
    """Box the characters of a ligature the way MuPDF does with ligatures expanded.

    PDFium reports the one "fi" glyph as two characters that both carry the whole glyph's box
    and origin. MuPDF, asked to expand ligatures as TrueDoc asks it to, gives the *first*
    character the whole box and every later one a zero-width box at the glyph's right edge -
    measured on Times at 7pt: f 31.86-35.75, i 35.75-35.75, origin 35.75. (My first version cut
    the box into equal slices, which is what it looked like from one wrong edge; the direct
    measurement said otherwise.) Word building is indifferent either way; everything that reads
    a character's own left edge is not.
    """
    i = 0
    n = len(chars)
    while i < n:
        j = i + 1
        while j < n and chars[j]["bbox"] == chars[i]["bbox"] and not chars[j]["c"].isspace():
            j += 1
        if j - i > 1 and not chars[i]["c"].isspace():
            x0, y0, x1, y1 = chars[i]["bbox"]
            for c in chars[i + 1:j]:
                c["bbox"] = (x1, y0, x1, y1)
                if c.get("origin"):
                    c["origin"] = (x1, c["origin"][1])
        i = j


def _fill_blank_span_sizes(spans: list) -> None:
    """Give a span of nothing but generated blanks the size of the text either side of it.

    PDFium invents a character wherever it sees a gap, and an invented character has no text
    object and so no size. When a run of them lands in a span of its own, that span has nothing to
    measure - 906 such blanks on one small-print page, every one of them a space, all reporting the
    nominal 1.0pt and dragging the page's body text size down with them. MuPDF has no equivalent
    problem because its own synthetic spaces sit inside the surrounding span and carry its font, so
    this does the same thing: take the size of the nearest neighbour that was actually measured.
    """
    known = [s["size"] for s in spans]
    for i, span in enumerate(spans):
        if span["size"] > 0.0:
            span.pop("_fallback", None)
            continue
        near = 0.0
        for step in range(1, len(spans)):
            before = known[i - step] if i - step >= 0 else 0.0
            after = known[i + step] if i + step < len(spans) else 0.0
            near = before or after
            if near:
                break
        span["size"] = near or span.get("_fallback", 0.0)
        span.pop("_fallback", None)


def _drawn_size(raw_api, tp, index: int, matrix, scales: dict[int, float]) -> float:
    """The size the character is actually drawn at, which is not the size PDFium reports.

    `FPDFText_GetFontSize` gives the *nominal* size - the number after `Tf` - and the PDF is then
    free to scale it by the text matrix. PyMuPDF folds the two together and PDFium does not, so
    taking the nominal size at face value made an 8pt page report 1.0 and a 5.9pt page report 35.8.
    The scale is a property of the text object, not the character, so it is cached per object;
    measured on two benchmark pages there is roughly one object per span.

    Returns 0.0 - not a size - for a character PDFium generated to fill a gap. Those have no text
    object and so no scale, and reporting the nominal size for them put 906 phantom 1.0pt
    characters on one small-print page, all of them spaces, which dragged the page's body size
    down with them. A size we did not measure is better left unstated.

    The scale comes from `FPDFText_GetMatrix`, the *effective* matrix for the character, and not
    from the text object's own matrix. The first version read the object's matrix, which was
    exact on a page that scales through `Tm` and wrong by exactly 4/3 on a page that scales through
    the graphics state (`0.7492 0 0 0.7492 0 0 cm`): every text object there reports an identity
    matrix, and 9.30 came back where MuPDF reads 6.97. Small type at 4/3 its real size glues its
    words together, because the word-gap rule is relative to size. Run 66 lost 13 tiny-text checks
    to it. The effective matrix reproduces MuPDF on both kinds of page and on an unscaled one.
    """
    obj = raw_api.FPDFText_GetTextObject(tp, index)
    if not obj:
        return 0.0
    if raw_api.FPDFText_GetMatrix(tp, index, matrix):
        scale = math.hypot(matrix.b, matrix.d) or 1.0
    else:
        key = ctypes.cast(obj, ctypes.c_void_p).value
        scale = scales.get(key)
        if scale is None:
            scale = math.hypot(matrix.b, matrix.d) if raw_api.FPDFPageObj_GetMatrix(obj, matrix) else 1.0
            scales[key] = scale
    return float(raw_api.FPDFText_GetFontSize(tp, index)) * scale


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
    if not path:
        return None    # a document opened from memory has no file to read; MuPDF takes it
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

    runs = []       # (block, direction, spans) per pdftext line, in order, before the joins and the gap cuts
    for block_index, block in enumerate(grouped):
        for line in block.get("lines") or []:
            spans = []
            for span in line.get("spans") or []:
                font = span.get("font") or {}
                size = float(font.get("size") or 0.0)
                chars = []
                drawn_sizes: list[float] = []
                colors: dict[int, int] = {}
                for ch in _join_surrogates(span.get("chars") or [], geom):
                    text = str(ch.get("char", ""))
                    if not text:
                        continue
                    g = geom.get(ch.get("char_idx"))
                    if text in ("\r", "\n") and (g or {}).get("generated"):
                        # PDFium's own line ends, not glyphs. They rode along as characters and
                        # were harmless until a Type 3 TeX page, where the raw-code recovery took
                        # the carriage return (0x0D) for cmr's "fl" ligature and an author block
                        # grew a column of "fl" cells (09f90a8f). A line end is a line end.
                        continue
                    text = _as_mupdf_would(text, str(font.get("name") or ""), g)
                    box = (g or {}).get("bbox")
                    if len(text) == 1 and unicodedata.category(text) == "Mn":
                        # A combining mark - cmsy's negation slash - belongs with the character
                        # before it, which is where MuPDF keeps it ("0̸" then "="); on its own box
                        # it sat in the gap and attached to whatever followed, "0" then "̸=". It
                        # stays a character of its own (every stage downstream assumes one code
                        # point per character) and takes a zero-width box at the previous
                        # character's right edge, as the later characters of a ligature do, so no
                        # gap opens before it and the real gap stays after it. The previous
                        # character is usually in the *previous* span: the 0 is CMR, the slash CMSY.
                        prev = chars[-1] if chars else (spans[-1]["chars"][-1] if spans and spans[-1].get("chars") else None)
                        if prev is not None and box is not None:
                            px1, py0, py1 = prev["bbox"][2], box[1], box[3]
                            g = dict(g or {}, bbox=(px1, py0, px1, py1), origin=(px1, (g or {}).get("origin", (px1, py1))[1]))
                            box = g["bbox"]
                    if box is None:
                        b = ch.get("bbox") or [0.0, 0.0, 0.0, 0.0]
                        box = (float(b[0]), float(b[1]), float(b[2]), float(b[3]))
                    origin = (g or {}).get("origin")
                    if origin is None:
                        # No origin from PDFium: fall back on the descender share of the box.
                        origin = (box[0], box[3] - _DESCENDER * (size or (box[3] - box[1])))
                    color = (g or {}).get("color", 0)
                    colors[color] = colors.get(color, 0) + 1
                    drawn_sizes.append(float((g or {}).get("size") or 0.0))
                    chars.append({
                        "c": text,
                        "bbox": box,
                        "origin": origin,
                        "ink": (g or {}).get("ink"),
                        "generated": bool((g or {}).get("generated")),
                        "map_error": bool((g or {}).get("map_error")),
                        # for the hidden-text rules: where in the painting order this character's
                        # object sits, whether it was drawn invisibly, and how opaque it is
                        "order": int((g or {}).get("order", -1)),
                        "invisible": bool((g or {}).get("invisible")),
                        "alpha": float((g or {}).get("alpha", 1.0)),
                    })
                if not chars:
                    continue
                _divide_shared_boxes(chars)
                # The drawn size, not the nominal one pdftext passes on from PDFium; and one span
                # per drawn size, as MuPDF cuts them. pdftext cuts spans on the nominal size, so a
                # page that sets "D_{2k}" as one font at two matrix scales hands over one span
                # holding a 14pt letter and 9pt subscripts (2503.06102); a single figure for it
                # made the subscripts full-size and the formula lost its structure. A span of
                # nothing but generated blanks has no drawn size at all and takes 0.0 here, filled
                # in from its neighbours below.
                for run, drawn in _size_runs(chars, drawn_sizes):
                    spans.append({
                        "font": str(font.get("name") or ""),
                        "size": drawn,
                        "_fallback": size,
                        "flags": _mupdf_flags(font, bool(span.get("superscript"))),
                        # PyMuPDF reports one colour per span; take the span's most common.
                        "color": max(colors.items(), key=lambda kv: kv[1])[0] if colors else 0,
                        "chars": run,
                    })
            if not spans:
                continue
            _fill_blank_span_sizes(spans)
            direction = _line_dir([c for sp in line.get("spans") or [] for c in sp.get("chars") or []], geom)
            if direction == (1.0, 0.0):
                _level_type3_boxes(spans)
            runs.append((block_index, direction, spans))
    blocks = []
    for block_index, direction, spans in _join_broken_lines(runs):
        lines = [{"dir": direction, "bbox": _union(piece), "spans": piece} for piece in _split_at_gaps(spans, direction)]
        if not lines:
            continue
        if blocks and blocks[-1]["_block"] == block_index:
            blocks[-1]["lines"].extend(lines)
        else:
            blocks.append({"type": 0, "lines": lines, "_block": block_index})
    for b in blocks:
        b.pop("_block")
    # The marker tells the stages downstream that the extra per-character keys ("ink",
    # "generated") are present, so they can be read from here instead of from MuPDF.
    return {"blocks": blocks, "source": "pdftext"}


def _level_type3_boxes(spans: list) -> None:
    """Give a line's Type 3 characters one box height, as MuPDF gives them.

    A Type 3 font has no ascender or descender to report, and the two libraries fill the gap
    differently: MuPDF boxes every character in the font's own height, PDFium each glyph in its
    own, so an x stands 6.5pt tall and an E 9.7. The text layer takes a Type 3 character's size
    from its box (the reported size is the matrix scale, 0.12 here), and per-glyph boxes made a
    scanned-era paper's body text 3.7pt where MuPDF read 8: every line then stood two and a
    half of its own sizes from the next, and not one joined its paragraph (09f90a8f). The
    tallest glyph on the line stands in for the font's height; measured on that page it is
    within 3% of MuPDF's. Level lines only - a turned line's height runs the other way.
    """
    small = [c for sp in spans if 0.0 < float(sp.get("size") or 0.0) < 1.0 for c in sp["chars"] if not c["c"].isspace()]
    if len(small) < 2:
        return
    y0 = min(c["bbox"][1] for c in small)
    y1 = max(c["bbox"][3] for c in small)
    for c in small:
        c["bbox"] = (c["bbox"][0], y0, c["bbox"][2], y1)


def _join_surrogates(chars: list, geom: dict) -> list:
    """One character for a code point beyond the basic plane, as MuPDF reports it.

    A maths font's italic letters and Greek live at U+1D400 and up. PDFium's text page holds
    UTF-16, so each such letter is two entries - a high and a low surrogate on the same box -
    and pdftext, which cannot write a lone surrogate, turns each into U+FFFD. One arXiv page
    then read 496 replacement characters, 21.6% of its text, and the quality gate sent it to
    the model as a broken layer; the census found 14 arXiv pages, a header page and a table
    page like it. The pair becomes the one character MuPDF gives, on the first entry's box.
    """
    out = []
    i = 0
    while i < len(chars):
        ch = chars[i]
        hi = (geom.get(ch.get("char_idx")) or {}).get("code", 0)
        if 0xD800 <= hi <= 0xDBFF and i + 1 < len(chars):
            lo = (geom.get(chars[i + 1].get("char_idx")) or {}).get("code", 0)
            if 0xDC00 <= lo <= 0xDFFF:
                out.append(dict(ch, char=chr(0x10000 + ((hi - 0xD800) << 10) + (lo - 0xDC00))))
                i += 2
                continue
        out.append(ch)
        i += 1
    return out


def _size_runs(chars: list, drawn: list[float]) -> list[tuple[list, float]]:
    """Cut a span's characters into runs of one drawn size, each with that size.

    A blank has no size of its own and stays with the run it is in; a run of nothing but blanks
    reports 0.0 and is filled from its neighbours later.
    """
    runs: list[tuple[list, float]] = []
    current: list = []
    current_size = 0.0
    for c, d in zip(chars, drawn):
        if current and d > 0 and current_size > 0 and abs(d - current_size) > 0.05:
            runs.append((current, current_size))
            current, current_size = [], 0.0
        current.append(c)
        if d > 0 and current_size == 0.0:
            current_size = d
    if current:
        runs.append((current, current_size))
    return runs


def _along(box, direction) -> tuple[float, float]:
    """Where a box starts and ends along the line's direction."""
    dx, dy = direction
    x0, y0, x1, y1 = box
    ends = [x0 * dx + y0 * dy, x1 * dx + y0 * dy, x0 * dx + y1 * dy, x1 * dx + y1 * dy]
    return min(ends), max(ends)


def _across(box, direction) -> tuple[float, float]:
    """Where a box starts and ends across the line's direction."""
    dx, dy = direction
    x0, y0, x1, y1 = box
    ends = [-x0 * dy + y0 * dx, -x1 * dy + y0 * dx, -x0 * dy + y1 * dx, -x1 * dy + y1 * dx]
    return min(ends), max(ends)


def _edge_glyph(spans: list, first: bool) -> tuple[dict, float] | None:
    """The first (or last) character of a run that is not a blank, with its span's size."""
    order = spans if first else list(reversed(spans))
    for sp in order:
        chars = sp["chars"] if first else list(reversed(sp["chars"]))
        for c in chars:
            if not c["c"].isspace():
                return c, float(sp.get("size") or 0.0)
    return None


def _line_main(spans: list, direction) -> tuple[float, float | None]:
    """The size most of a line is set in, and the baseline of that text (measured across the
    line's direction)."""
    dx, dy = direction
    by_size: dict[float, list[float]] = {}
    for sp in spans:
        s = round(float(sp.get("size") or 0.0), 1)
        if s <= 0:
            continue
        for c in sp["chars"]:
            o = c.get("origin")
            if o and not c["c"].isspace():
                by_size.setdefault(s, []).append(-o[0] * dy + o[1] * dx)
    if not by_size:
        return 0.0, None
    size = max(by_size, key=lambda s: len(by_size[s]))
    bases = sorted(by_size[size])
    return size, bases[len(bases) // 2]


def _continues(prev: list, spans: list, direction) -> bool:
    """Does this run carry straight on from the last one - the same line, cut by PDFium?"""
    a = _edge_glyph(prev, first=False)
    b = _edge_glyph(spans, first=True)
    if a is None or b is None:
        return False
    (ca, sa), (cb, sb) = a, b
    size = max(sa, sb, ca["bbox"][3] - ca["bbox"][1], cb["bbox"][3] - cb["bbox"][1], 1.0)
    # It starts no further back than the last glyph (a subscript stacked under a superscript
    # starts level with it), ...
    if _along(cb["bbox"], direction)[0] < _along(ca["bbox"], direction)[0] - 0.1 * size:
        return False
    # ... it is a script of the line, or sits on its baseline, or on the last glyph's - the
    # rows of a matrix are full-size text on baselines of their own, and stay lines of their
    # own, as the maths stage expects them, ...
    oa, ob = ca.get("origin"), cb.get("origin")
    if oa and ob:
        dx, dy = direction
        a_base, b_base = -oa[0] * dy + oa[1] * dx, -ob[0] * dy + ob[1] * dx
        main_size, main_base = _line_main(prev, direction)
        script = sb > 0 and main_size > 0 and sb < 0.85 * main_size
        on_line = main_base is not None and abs(b_base - main_base) <= 0.5 * max(main_size, sb)
        on_last = abs(b_base - a_base) <= 0.5 * max(sa, sb, 1.0)
        if not (script or on_line or on_last):
            return False
    # ... and it overlaps the band the line so far occupies.
    lo, hi = _across(_union(prev), direction)
    b_lo, b_hi = _across(cb["bbox"], direction)
    return min(hi, b_hi) - max(lo, b_lo) > 0


def _weld(prev: list, spans: list, direction) -> None:
    """Append a run to the line it continues, without the break PDFium made up."""
    a = _edge_glyph(prev, first=False)
    b = _edge_glyph(spans, first=True)
    # PDFium's own line ends and blanks at the seam go: they were the break.
    while prev and prev[-1]["chars"] and prev[-1]["chars"][-1]["c"].isspace() and prev[-1]["chars"][-1].get("generated"):
        prev[-1]["chars"].pop()
        if not prev[-1]["chars"]:
            prev.pop()
    while spans and spans[0]["chars"] and spans[0]["chars"][0]["c"].isspace() and spans[0]["chars"][0].get("generated"):
        spans[0]["chars"].pop(0)
        if not spans[0]["chars"]:
            spans.pop(0)
    if not prev or not spans:
        prev.extend(spans)
        return
    # A word's gap between the two halves keeps a blank, as MuPDF would have put one.
    if a is not None and b is not None:
        (ca, sa), (cb, sb) = a, b
        size = max(sa, sb, ca["bbox"][3] - ca["bbox"][1], 1.0)
        gap = _along(cb["bbox"], direction)[0] - _along(ca["bbox"], direction)[1]
        if gap >= _WORD_GAP * size:
            x0, y0, x1, y1 = ca["bbox"]
            prev[-1]["chars"].append(dict(ca, c=" ", bbox=(x1, y0, x1, y1), origin=(x1, (ca.get("origin") or (x1, y1))[1]),
                                          ink=None, generated=True))
    prev.extend(spans)


def _join_broken_lines(runs: list) -> list:
    """Rejoin the pieces of one line that PDFium's text page cut at a raised character.

    TeX sets R^{2^n} as three text runs on three baselines, and PDFium ends a line at each
    step: the page reads "R", "2", "n" and "(by abuse of notation" as four lines where MuPDF
    reads one. TrueDoc then bridged the strays into whichever neighbouring line their boxes
    touched, and a formula on the line below gained a superscript it never had (2503.04329:
    R^{2^n} read as R^2, and a stray n^n appeared two lines down). A run that carries on from
    where the last one stopped - starting no further back than its last glyph, script-sized or
    back on a baseline, inside the band the line occupies - is the same line, whichever of
    pdftext's blocks it was filed in (the words after a superscript land in a new block). The
    gap cut that follows still parts the cells of a table row, exactly as it does for the rows
    pdftext itself hands over whole.
    """
    out: list[tuple[int, tuple[float, float], list]] = []
    for block_index, direction, spans in runs:
        if out and _edge_glyph(spans, first=True) is None:
            # Nothing but blanks - the space PDFium makes up between two words of turned
            # text, which it files as a level line of its own and so cuts the text at every
            # word. It belongs to the run before it, as the blank it is.
            out[-1][2].extend(spans)
        elif out and out[-1][1] == direction and _continues(out[-1][2], spans, direction):
            _weld(out[-1][2], spans, direction)
        else:
            out.append((block_index, direction, spans))
    return out


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
    prev = None       # (index in flat, end along the line, scale, start along the line)
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
        # A pen that jumps backwards starts a new line, as it does for MuPDF. pdftext files
        # every span that overlaps a line's band in that line whatever its order, so a table
        # row drawn right to left arrived as one line with its characters running backwards -
        # "0.658", "0.77**", "0.31*" - and the word builder, which measures each gap from the
        # character before, glued them into one word and one cell (b5c5b866, the quick gate).
        # Kerning pulls a glyph back a fraction of an em at most; half an em is a jump.
        elif prev is not None and scale > 0 and start < prev[3] - 0.5 * max(scale, prev[2]):
            cuts.add(i)
        prev = (i, end, scale, start)
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


_WORD_GAP = 0.15        # a gap this share of the font size between glyphs is a word space


def _spaced_text(chars: list, size: float) -> str:
    """The characters as text, with a space wherever the glyphs stand a word's gap apart.

    PDFium invents fewer gap-filling spaces than MuPDF in small type, and a run of characters
    joined blindly then reads "TypeofTask". The threshold sits in the measured band between letter
    gaps (at most 0.04 x size at p95) and MuPDF's own spaces (from 0.16); the word builder's rule
    for the body text is the same shape.
    """
    out: list[str] = []
    prev = None
    for c in chars:
        if prev is not None and not c["c"].isspace() and not prev["c"].isspace():
            scale = max(size, c["bbox"][3] - c["bbox"][1], 0.5)
            if c["bbox"][0] - prev["bbox"][2] >= _WORD_GAP * scale:
                out.append(" ")
        out.append(c["c"])
        prev = c
    return "".join(out)


def clipped_blocks(path: str, page_number: int, rect, M=None) -> list | None:
    """What PyMuPDF's `get_text("dict", clip=rect)` returns, for the ruled-table cell reader.

    Only the keys that reader touches are filled: a bbox and a text per line. A character
    counts as inside when its box overlaps the rectangle, which is how MuPDF's clip behaves
    for the cell-sized rectangles this is asked for.

    The characters are held in the unrotated space. A caller working in the rendered space
    passes the page's rotation matrix `M`: the rectangle is turned back before the test, and
    the line boxes turned forward before they are returned.
    """
    built = build(path, page_number)
    if built is None:
        return None
    turn = None
    if M is not None:
        import pymupdf
        turn = pymupdf.Matrix(M)
        r = pymupdf.Rect(*rect) * ~turn
        r.normalize()
        rect = (r.x0, r.y0, r.x1, r.y1)
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
                    spans.append({"text": _spaced_text(inside, float(sp.get("size") or 0.0)), "chars": inside})
            if not spans:
                continue
            xs = [c["bbox"][0] for s in spans for c in s["chars"]]
            ys = [c["bbox"][1] for s in spans for c in s["chars"]]
            xe = [c["bbox"][2] for s in spans for c in s["chars"]]
            ye = [c["bbox"][3] for s in spans for c in s["chars"]]
            bbox = (min(xs), min(ys), max(xe), max(ye))
            if turn is not None:
                import pymupdf
                r = pymupdf.Rect(*bbox) * turn
                r.normalize()
                bbox = (float(r.x0), float(r.y0), float(r.x1), float(r.y1))
            lines.append({"bbox": bbox, "spans": spans})
        if lines:
            blocks.append({"lines": lines})
    return blocks


def _line_dir(chars: list, geom: dict) -> tuple[float, float]:
    """PyMuPDF's writing-direction vector for a run of characters, from PDFium's char angle.

    Measured against MuPDF's own `dir` on four hand-built pages and a benchmark one: text set
    with the matrix (0 1 -1 0) - running up the page - is angle 4.71 to PDFium and (0, -1) to
    MuPDF; (0 -1 1 0) is 1.57 and (0, 1); (-1 0 0 -1) is 3.14 and (-1, 0); level text is 0 and
    (1, 0). So the angle is already in the y-down page space MuPDF reports in, and the vector
    is (cos, sin). The page's own /Rotate plays no part: MuPDF reports a level line on a
    90-degree page as (1, 0), the unrotated direction, and PDFium's angle for it is 0.

    (An earlier version read a rotation pdftext was thought to carry per line, and turned the
    result by the page rotation on the strength of a docstring rather than a measurement.
    pdftext's dictionary output carries no line rotation at all, so every line read as level,
    and a page's turned text - a table's vertical headings - was cut into one-word lines and
    sorted top to bottom, which reads its words backwards.)

    The run's angle is the one most of its characters carry; blanks PDFium makes up are level
    whatever the text around them is, and do not vote.
    """
    votes: dict[float, list] = {}
    for c in chars:
        g = geom.get(c.get("char_idx")) or {}
        if str(c.get("char", "")).isspace() or g.get("generated"):
            continue
        theta = float(g.get("angle") or 0.0)
        votes.setdefault(round(theta, 2), []).append(theta)
    theta = max(votes.values(), key=len)[0] if votes else 0.0

    def snap(v: float) -> float:
        # MuPDF's vector for text turned by a right angle is exact; a float radian is not.
        for exact in (-1.0, 0.0, 1.0):
            if abs(v - exact) < 1e-3:
                return exact
        return round(v, 6) + 0.0

    return (snap(math.cos(theta)), snap(math.sin(theta)))


def _union(spans: list) -> tuple:
    xs0 = [c["bbox"][0] for s in spans for c in s["chars"]]
    ys0 = [c["bbox"][1] for s in spans for c in s["chars"]]
    xs1 = [c["bbox"][2] for s in spans for c in s["chars"]]
    ys1 = [c["bbox"][3] for s in spans for c in s["chars"]]
    return (min(xs0), min(ys0), max(xs1), max(ys1))
