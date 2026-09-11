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

The default reader since run 71 (D023): 84.0 on olmOCR-bench with every PDFium switch on,
level with the MuPDF run's 84.0 and above it on the held-out fifth (81.1 against 80.9), nine
checks up over 1,403 pages. `TRUEDOC_READER=mupdf` reads through MuPDF instead, for measurement.
"""
from __future__ import annotations

import ctypes
import math
import os
import re
import unicodedata

from truedoc.extract import glyph_names, pdfium_objects
from truedoc.math.symbols import is_extension_font


def _is_blank(c: dict) -> bool:
    """A blank: whitespace to Python that is a blank on the page as well.

    A code PDFium could not map is a glyph whatever Python calls it: cmex draws a tall bar from
    pieces on 0x0C, a form feed, and Adobe's fonts keep their ligatures on 0x1C-0x1F, all
    "whitespace" to `str.isspace`. Taking them for blanks folded five bracket pieces of a
    display formula into the sentence above it, whose box then reached 60pt into the formula
    and the maths stage swallowed the sentence (2503.03899); 79 benchmark pages carry such
    codes.
    """
    return c["c"].isspace() and not c.get("map_error")

_DESCENDER = 0.21       # last-resort baseline estimate, used only where PDFium will not give an origin
_TEX_BOLD = re.compile(r"^(?:[a-z]{6}\+)?(?:cmb|cmbx|cmbsy|cmmib|cmssbx|sfbx|sfbi|eufb)\d")   # TeX's bold faces
_LINE_GAP = 1.5         # a gap this many times the font size ends a line (see _split_at_gaps)
_SUBSET_TAG = re.compile(r"^[A-Z]{6}\+")   # "ABCDEE+Calibri": the subset tag MuPDF folds away
_BASELINE_STEP = 1.0    # a baseline this many ems from the last glyph's starts a line (a drop cap)
_OBJECT_GAP = 1.0       # ... and this many where the text object changes with it (measured: 0.5, 0.75
                        # and 1.0 each gain six table checks on the changed pages; 1.0 costs the fewest
                        # multi-column checks, one; 0 switches it off)

# One page's built structure is wanted by several stages (the main read, the maths ink pass, the
# ruled-table cell reader), so the last few are kept rather than parsed again. Plain dicts only:
# no PDFium handle is held open.
_CACHE: dict[tuple, dict] = {}
_CACHE_MAX = 4


def enabled() -> bool:
    """On by default since run 71 (D023); `TRUEDOC_READER=mupdf` reads through MuPDF instead."""
    return os.environ.get("TRUEDOC_READER", "pdftext").strip().lower() not in ("mupdf", "off", "0", "")


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


_BOLD_WEIGHTS = {"bold", "semibold", "black"}
_PROGRAM_STYLES: dict[bytes, tuple[bool, bool]] = {}     # a font program's digest -> (bold, italic)


def _program_style(data: bytes) -> tuple[bool, bool]:
    """A font's bold and italic, read from its embedded program the way MuPDF reads them.

    A font named "CIDFont+F2" with no style bits in its descriptor says nothing to the name and
    descriptor rule of `_mupdf_flags`, yet MuPDF reads it bold: 0be9ba92's heading lost its bold
    that way and the page's column order changed. Measured over 3,390 page-and-font pairs against
    MuPDF's span flags: a TrueType weight class of 600 or 700 is bold every time (465 of 465) and
    900 never (4 of 4); a CFF or Type 1 weight of Bold, Semibold or Black is bold every time (225 of
    225) and Heavy and Medium never; a non-zero italic angle in the program is italic. Taken with
    the name and descriptor rule, that fixes 31 bold and 10 italic flags and breaks none. The style
    bits in fsSelection and macStyle were mixed (10 fixed, 7 broken) and are not used, and the
    italic angle in the PDF's font descriptor fixed nothing. On forty of the insurance library's
    documents the name rule already agreed with MuPDF on every flag, and this changes none.
    """
    if not data:
        return False, False
    import hashlib
    key = hashlib.blake2b(data, digest_size=16).digest()
    hit = _PROGRAM_STYLES.get(key)
    if hit is not None:
        return hit
    style = (False, False)
    try:
        head = data[:4]
        if head in (b"\x00\x01\x00\x00", b"OTTO", b"true", b"ttcf"):
            import io
            from fontTools.ttLib import TTFont
            prog = TTFont(io.BytesIO(data), lazy=True, fontNumber=0)
            bold = "OS/2" in prog and int(getattr(prog["OS/2"], "usWeightClass", 0) or 0) in (600, 700)
            italic = "post" in prog and abs(float(prog["post"].italicAngle or 0)) > 0.5
            style = (bool(bold), bool(italic))
        elif data[:1] == b"\x01" and len(data) > 4:
            import io
            from fontTools.cffLib import CFFFontSet
            cff = CFFFontSet()
            cff.decompile(io.BytesIO(data), None)
            top = cff[cff.fontNames[0]]
            weight = str(getattr(top, "Weight", "") or "").strip().lower()
            style = (weight in _BOLD_WEIGHTS, abs(float(getattr(top, "ItalicAngle", 0) or 0)) > 0.5)
        else:
            text = data[:6000].decode("latin-1", "replace")
            if "%!" in text[:60] or "/FontName" in text:
                m = re.search(r"/Weight\s*\(([^)]*)\)", text)
                a = re.search(r"/ItalicAngle\s+(-?[\d.]+)", text)
                style = (bool(m) and m.group(1).strip().lower() in _BOLD_WEIGHTS,
                         bool(a) and abs(float(a.group(1))) > 0.5)
    except Exception:
        style = (False, False)
    if len(_PROGRAM_STYLES) >= 512:
        _PROGRAM_STYLES.pop(next(iter(_PROGRAM_STYLES)))
    _PROGRAM_STYLES[key] = style
    return style


def _style_of(raw_api, tp, index: int, cache: dict) -> tuple[bool, bool]:
    """(bold, italic) of a character's font from its embedded program, cached per font on the page."""
    obj = raw_api.FPDFText_GetTextObject(tp, index)
    font = raw_api.FPDFTextObj_GetFont(obj) if obj else None
    if not font:
        return False, False
    key = ctypes.cast(font, ctypes.c_void_p).value
    hit = cache.get(key)
    if hit is None:
        data = b""
        try:
            size = ctypes.c_size_t()
            if raw_api.FPDFFont_GetFontData(font, None, 0, ctypes.byref(size)) and size.value:
                buf = (ctypes.c_uint8 * size.value)()
                if raw_api.FPDFFont_GetFontData(font, buf, size.value, ctypes.byref(size)):
                    data = bytes(buf)
        except Exception:
            data = b""
        hit = cache[key] = _program_style(data)
    return hit


def _geometry(path: str, page_number: int, wanted: set[int]) -> tuple[dict[int, dict], list]:
    """Every geometric fact PDFium holds for the wanted characters, in PyMuPDF's space, and the
    page's thin horizontal rules (for the line join)."""
    import pypdfium2 as pdfium
    import pypdfium2.raw as raw_api

    out: dict[int, dict] = {}
    bars: list[tuple[float, float, float, float]] = []
    doc = pdfium.PdfDocument(path)
    try:
        page = doc[page_number - 1]
        x_off, _y0, _x1, y_top = pdfium_objects.page_box(page)
        textpage = page.get_textpage()
        try:
            tp = textpage.raw
            ox, oy = ctypes.c_double(), ctypes.c_double()
            il, ir, ib, it = (ctypes.c_double() for _ in range(4))
            fr, fg, fb, fa = (ctypes.c_uint() for _ in range(4))
            loose = raw_api.FS_RECTF()
            matrix = raw_api.FS_MATRIX()
            scales: dict[int, float] = {}      # text object -> the scale its matrix applies
            styles: dict[int, tuple[bool, bool]] = {}   # font -> (bold, italic) from its program
            # Which drawn object each character belongs to, and where that object comes in the
            # painting order - what the hidden-text rules (D011) used MuPDF's text trace for. The
            # walk has to happen on this very page load: pypdfium2 reloads the page on every
            # `doc[i]`, and object pointers do not survive a reload. The order numbers do.
            handles: dict[int, int] = {}
            clips: dict[int, tuple] = {}       # text object -> its clip box, where it has one
            widths_tables: dict | None = None  # the page's /Widths, read only if a code needs them
            font_buf, font_flags = ctypes.create_string_buffer(256), ctypes.c_int()
            try:
                objects = pdfium_objects.walk_page(raw_api, page, handles, clips)
            except Exception:
                handles, objects = {}, []
            # The thin horizontal rules - fraction bars among them - from the same walk, for
            # the line join. (Not through `page_objects`, whose document cache would hold the
            # file open; a test's temporary page could then not be deleted.)
            for o in objects or []:
                if o.kind == "path":
                    for bx0, by0, bx1, by1 in (o.rects or [o.bbox]):
                        if by1 - by0 <= _BAR_MAX_HEIGHT and bx1 - bx0 >= 2.0:
                            bars.append((bx0, by0, bx1, by1))
            invisible_mode = getattr(raw_api, "FPDF_TEXTRENDERMODE_INVISIBLE", 3)
            count = raw_api.FPDFText_CountChars(tp)
            other = raw_api.FS_RECTF()
            ox2, oy2 = ctypes.c_double(), ctypes.c_double()

            def _shares_glyph(raw_api, tp, i, mine, mine_origin, count) -> bool:
                """True when a neighbouring character has this one's loose box or its origin: a
                ligature, one glyph that PDFium reports as two characters.

                Most share the box and the origin both (measured: every shared box on two pages
                was also a shared origin, and the pairs were fi and ff, plus the rotated arXiv
                watermark that the level-text test already excludes). Some share the origin
                only, the ink divided between the two: cefac431's "firmware" has its f from 82.8
                to 85.2 and its i from 85.2 to 87.6, both drawn at 82.7, and the advance of a
                lone i, laid from that origin, ended the i before the f - a zero-width box 3pt
                short of the r, which the word builder read as "fi rmware"."""
                for j in (i - 1, i + 1):
                    if 0 <= j < count and raw_api.FPDFText_GetLooseCharBox(tp, j, other):
                        if abs(other.left - mine.left) < 1e-3 and abs(other.right - mine.right) < 1e-3:
                            return True
                    # A blank PDFium makes up stands at the origin of the glyph after it, and is
                    # no ligature piece: taking it for one kept "al." on its loose box and the
                    # word gap before it closed (b2a4c508).
                    if (0 <= j < count and mine_origin is not None
                            and not raw_api.FPDFText_IsGenerated(tp, j)
                            and raw_api.FPDFText_GetCharOrigin(tp, j, ox2, oy2)
                            and abs(ox2.value - mine_origin[0]) < 1e-3 and abs(oy2.value - mine_origin[1]) < 1e-3):
                        return True
                return False

            for i in wanted:
                box = None
                probe = None
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
                # A NUL is never a character: PDFium maps a dvips Type 3 font's code 0 (its
                # first glyph, the capital A on 0b65b6a5) to U+0000 and reports no error, and
                # the line read "Lobo R\x00". An unmapped code, like any other.
                map_error = raw_api.FPDFText_HasUnicodeMapError(tp, i) == 1 or code == 0
                drawn = _drawn_size(raw_api, tp, i, matrix, scales)
                # The top and bottom are the font's ascent and descent from the baseline, which is
                # the box MuPDF reports for every character of a span. PDFium's loose box stops
                # short above the baseline - 1.4pt on 8pt Arial - and by an amount that varies
                # with the glyphs, so a table's header line and the "Item" centred over it swapped
                # rows in the rebuild and two columns fused (fa18a15c). `FPDFFont_GetAscent` and
                # `GetDescent`, asked at the drawn size, give the very metrics MuPDF uses (7.276
                # = 0.905 x 8.04, to the third place). Level text; not a Type 3 font, whose ascent
                # PDFium reports as 0 - those keep their glyph box and the line rule in `_build`.
                if (box is not None and origin is not None and drawn >= 1.0
                        and raw_api.FPDFText_GetMatrix(tp, i, matrix)
                        and abs(matrix.b) < 1e-6 and abs(matrix.c) < 1e-6):
                    metric_obj = raw_api.FPDFText_GetTextObject(tp, i)
                    metric_font = raw_api.FPDFTextObj_GetFont(metric_obj) if metric_obj else None
                    asc, desc = ctypes.c_float(), ctypes.c_float()
                    # ... at the y scale of the text matrix, not the overall size: where a page
                    # scales x and y differently (an OCR layer fitting words to their boxes) MuPDF's
                    # top and bottom follow the y scale on 92% of 73,318 such characters, the
                    # geometric mean on 17% (where the two coincide).
                    ysize = abs(float(raw_api.FPDFText_GetFontSize(tp, i))) * abs(matrix.d) or drawn
                    if (metric_font and raw_api.FPDFFont_GetAscent(metric_font, ysize, asc)
                            and raw_api.FPDFFont_GetDescent(metric_font, ysize, desc)
                            and 0.0 < asc.value <= 1.5 * ysize and -1.5 * ysize <= desc.value <= 0.0):
                        box = (box[0], origin[1] - asc.value, box[2], origin[1] - desc.value)
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
                        and abs(matrix.b) < 1e-6
                        and not _shares_glyph(raw_api, tp, i, loose, (ox.value, oy.value), count)):
                    if abs(matrix.c) >= 1e-6:
                        # Sheared text - an italic made by slanting an upright face - keeps the
                        # loose box's right edge: MuPDF's box there ends where the slanted advance
                        # box ends, which is what the loose box reports (123.5 both ways for the
                        # "a" of "al." on b2a4c508), and the origin plus the advance would stop
                        # 1.5pt short. Its left edge is the origin, as for every other glyph.
                        box = (origin[0], box[1], max(origin[0], box[2]), box[3])
                    else:
                        text_obj = raw_api.FPDFText_GetTextObject(tp, i)
                        font = raw_api.FPDFTextObj_GetFont(text_obj) if text_obj else None
                        adv_w = ctypes.c_float()
                        if font and code and raw_api.FPDFFont_GetGlyphWidth(font, code, abs(raw_api.FPDFText_GetFontSize(tp, i)), adv_w):
                            # ... at the x scale of the matrix: MuPDF's right edge is the origin
                            # plus the advance times the x scale on every one of 73,316 characters
                            # whose matrix scales x and y differently (the y scale on 8%).
                            advance = adv_w.value * (abs(matrix.a) or 1.0)
                            if advance > 0:
                                # The left edge is the origin as well: MuPDF's box runs from the
                                # glyph's origin to its advance, and the origin agrees with MuPDF's
                                # left edge on 99.7% of 316,152 matched characters against the
                                # loose box's 99.2% (level text, 120 pages). Where they differ the
                                # loose box starts a fraction left of the origin, and at 7pt that
                                # fraction closed the word gap MuPDF reads between "et" and "al."
                                # (b2a4c508, whose "et al." is sheared - see above).
                                box = (origin[0], box[1], origin[0] + advance, box[3])
                # A character PDFium could not map gets no advance from it either (the lookup
                # goes by Unicode), and its loose box is the glyph's ink. MuPDF's box is the
                # origin plus the advance in the PDF's own /Widths: cmex's brace pieces, 4pt of
                # ink on an advance of 10, stood out of line with each other and a cases brace
                # read as three braces (2503.09472); cmsy's mapstochar, advance 0, is a zero-width
                # box to MuPDF and was a 1.3pt one here.
                if (map_error and box is not None and origin is not None and drawn > 0
                        and raw_api.FPDFText_GetMatrix(tp, i, matrix)
                        and abs(matrix.b) < 1e-6 and abs(matrix.c) < 1e-6):
                    if widths_tables is None:
                        widths_tables = glyph_names.page_glyph_names(path, page_number) or {}
                    if widths_tables and raw_api.FPDFText_GetFontInfo(tp, i, font_buf, 256, font_flags):
                        font_name = font_buf.value.decode("latin-1", "replace")
                        tables = widths_tables
                        if not font_name:
                            # No name to look the font up by. PDFium answers the width of any
                            # glyph of a Type 3 font with the font's first /Widths entry, which
                            # picks the resource out (0b65b6a5: three unnamed fonts, three
                            # first widths); the same fingerprint names the glyph in `_build`.
                            probe_obj = raw_api.FPDFText_GetTextObject(tp, i)
                            probe_font = raw_api.FPDFTextObj_GetFont(probe_obj) if probe_obj else None
                            probe_w = ctypes.c_float()
                            # any code gives the same answer, but code 0 - dvips's first glyph,
                            # the capital A of 0b65b6a5 - gets no answer at all, so ask by a few
                            for probe_code in (code, 1, 32, 65):
                                if probe_font and raw_api.FPDFFont_GetGlyphWidth(probe_font, probe_code, 1.0, probe_w) and probe_w.value > 0:
                                    probe = probe_w.value * 1000.0
                                    break
                            tables = glyph_names.narrow(widths_tables, font_name, probe) or widths_tables
                        w = glyph_names.advance_for(tables, font_name, code)
                        if w is not None:
                            xsize = abs(float(raw_api.FPDFText_GetFontSize(tp, i))) * abs(matrix.a) or drawn
                            box = (origin[0], box[1], origin[0] + w * xsize / 1000.0, box[3])
                color, alpha = 0, 1.0
                if raw_api.FPDFText_GetFillColor(tp, i, fr, fg, fb, fa):
                    color = (fr.value << 16) | (fg.value << 8) | fb.value
                    alpha = fa.value / 255.0
                obj = raw_api.FPDFText_GetTextObject(tp, i)
                order, invisible, clipped = -1, False, False
                if obj:
                    pointer = ctypes.cast(obj, ctypes.c_void_p).value
                    order = handles.get(pointer, -1)
                    try:
                        invisible = raw_api.FPDFTextObj_GetTextRenderMode(obj) == invisible_mode
                    except Exception:
                        invisible = False
                    # Text clipped away by the page is text no reader sees. A Word-made PDF clips
                    # each paragraph to its box and a dot leader runs on past it: MuPDF's text
                    # leaves the rest out (one dot of thirteen on fa18a15c), PDFium's text page
                    # ignores clipping, and the leader reached into the next column. A character
                    # whose ink lies wholly outside its text object's clip box is not delivered.
                    clip = clips.get(pointer)
                    seen = ink or box
                    if clip is not None and seen is not None:
                        clipped = not (seen[0] < clip[2] and seen[2] > clip[0] and seen[1] < clip[3] and seen[3] > clip[1])
                out[i] = {
                    "bbox": box,
                    "ink": ink,
                    "origin": origin,
                    "color": color,
                    "alpha": alpha,
                    "order": order,
                    "invisible": invisible,
                    "size": drawn,
                    "generated": raw_api.FPDFText_IsGenerated(tp, i) == 1,
                    "map_error": map_error,
                    "clipped": clipped,
                    "code": code,
                    "probe": probe,         # an unnamed Type 3 font's fingerprint (see the widths rule)
                    "style": _style_of(raw_api, tp, i, styles),   # (bold, italic) from the font program
                    # the writing direction, as PDFium measures it: radians in the y-down page
                    # space, so (cos, sin) is MuPDF's direction vector (measured, see _line_dir).
                    # A negative font size turns the glyphs back round: a tax form (8e953483)
                    # sets its text with the matrix -1.333 0 0 -1.333 and a size of -4.43, so it
                    # reads upright and left to right, where PDFium's angle for it is pi; the
                    # line then voted right-to-left, every glyph was a backwards jump, and the
                    # page shattered into 1,290 one-character lines.
                    "angle": (float(raw_api.FPDFText_GetCharAngle(tp, i))
                              + (math.pi if raw_api.FPDFText_GetFontSize(tp, i) < 0 else 0.0)) % (2.0 * math.pi),
                }
        finally:
            textpage.close()
    finally:
        doc.close()
    return out, bars


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
        while j < n and chars[j]["bbox"] == chars[i]["bbox"] and not _is_blank(chars[j]):
            j += 1
        if j - i > 1 and not _is_blank(chars[i]):
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

    The scale is the square root of the matrix's determinant, not the length of its y axis. An
    OCR layer fits each word to its box by scaling x and y differently (`8.4 0 0 7.3 ... Tm`, or
    a `Tz`), and on 73,333 such characters over 30 benchmark pages - the tiny-text family among
    them - MuPDF's size is the geometric mean of the two scales every time, the y scale a fifth of
    the time (when it happens to be the mean). The y scale alone read 8.40 where MuPDF reads 7.28
    on 0091c5b2, and the rows of its table fused. For text turned or slanted the determinant is
    the same measure: 6.97 for the slanted "et al." of b2a4c508, as MuPDF reports.
    """
    obj = raw_api.FPDFText_GetTextObject(tp, index)
    if not obj:
        return 0.0
    if raw_api.FPDFText_GetMatrix(tp, index, matrix):
        scale = _det_scale(matrix)
    else:
        key = ctypes.cast(obj, ctypes.c_void_p).value
        scale = scales.get(key)
        if scale is None:
            scale = _det_scale(matrix) if raw_api.FPDFPageObj_GetMatrix(obj, matrix) else 1.0
            scales[key] = scale
    # The size's magnitude: a negative size mirrors the glyphs and turns their advance round,
    # which the angle above takes into account; a size below zero is no size for any rule.
    return abs(float(raw_api.FPDFText_GetFontSize(tp, index))) * scale


def _det_scale(matrix) -> float:
    """The overall scale of a text matrix: the square root of its determinant's magnitude."""
    return math.sqrt(abs(matrix.a * matrix.d - matrix.b * matrix.c)) or 1.0


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


# The free-standing accents the text layer composes with the letter beside them: the same table as
# `textlayer._SPACING_ACCENTS`, kept here because that module imports this one.
_SPACING_ACCENTS = {"ˆ": "̂", "˜": "̃", "´": "́", "¨": "̈", "¸": "̧", "˚": "̊",
                    "¯": "̄", "ˇ": "̌", "˘": "̆", "˙": "̇", "˝": "̋"}


def _rehome_accents(grouped: list, geom: dict) -> None:
    """Put each free-standing accent PDFium strands away from its letter back just before it.

    TeX's accent command draws an accent as a glyph of its own. MuPDF orders it just before the
    letter it covers ("Radioˇzurn´al"), and the text layer composes the pair
    (`textlayer._compose_spacing_accents` joins an accent to the letter just before or just after
    it in its line). PDFium usually puts the accent just after its letter, which the composer
    joins too; but 153 times over the benchmark it emits it somewhere else - after the next word,
    or at the end of the line - and on 031a888e "Český" and "Radiožurnál" never formed, while the
    line splitter cut each stray accent off as a backwards jump. Measured before it was written.

    An accent moves only on the composer's own terms - the same font as the letter, its centre
    over the letter, the letter's baseline level with the accent's or up to 0.6 em below it (an
    accent over a capital is raised), and a precomposed form - so every accent moved is one the
    composer then joins. One already next to its letter in the line stays where it is.
    """
    flat = []
    for bi, block in enumerate(grouped):
        for li, line in enumerate(block.get("lines") or []):
            for span in line.get("spans") or []:
                font = _SUBSET_TAG.sub("", str((span.get("font") or {}).get("name") or ""))
                chars = span.get("chars") or []
                for ch in chars:
                    flat.append(((bi, li), chars, ch, font))
    accents = [r for r in flat if str(r[2].get("char", "")) in _SPACING_ACCENTS]
    if not accents:
        return
    position = {id(r[2]): k for k, r in enumerate(flat)}
    letters: dict[str, list] = {}
    for key, chars, ch, font in flat:
        t = str(ch.get("char", ""))
        g = geom.get(ch.get("char_idx")) or {}
        if len(t) == 1 and t.isalpha() and g.get("bbox") and g.get("origin"):
            letters.setdefault(font, []).append((key, chars, ch, g))
    taken: set[int] = set()
    for key, chars, ch, font in accents:
        g = geom.get(ch.get("char_idx")) or {}
        if g.get("generated") or not g.get("bbox") or not g.get("origin"):
            continue
        ax0, ay0, ax1, ay1 = g["bbox"]
        cx, base = (ax0 + ax1) / 2.0, g["origin"][1]
        size = max(float(g.get("size") or 0.0), ay1 - ay0, 1.0)
        comb = _SPACING_ACCENTS[str(ch.get("char"))]
        best = None
        for key2, chars2, b, gb in letters.get(font, ()):
            if id(b) in taken:
                continue
            bx0, _by0, bx1, _by1 = gb["bbox"]
            tol = 0.15 * max(float(gb.get("size") or 0.0), 1.0)
            if not (bx0 - tol <= cx <= bx1 + tol):
                continue
            dy = gb["origin"][1] - base
            if not (-0.15 * size <= dy <= 0.6 * size):
                continue
            if len(unicodedata.normalize("NFC", str(b.get("char")) + comb)) != 1:
                continue
            score = abs(dy) + abs((bx0 + bx1) / 2.0 - cx)
            if best is None or score < best[0]:
                best = (score, key2, chars2, b)
        if best is None:
            continue
        _, key2, chars2, b = best
        taken.add(id(b))
        if key2 == key and abs(position[id(ch)] - position[id(b)]) == 1:
            continue          # beside its letter already: the composer joins them where they stand
        del chars[next(i for i, x in enumerate(chars) if x is ch)]
        chars2.insert(next(i for i, x in enumerate(chars2) if x is b), ch)


def _build(path: str, page_number: int) -> dict | None:
    page = _order(path, page_number)
    if page is None:
        return None
    grouped = page.get("blocks") or []

    names: dict | None = None       # the page's glyph-name tables, read only if a code needs them
    wanted: set[int] = set()
    for block in grouped:
        for line in block.get("lines") or []:
            for span in line.get("spans") or []:
                for ch in span.get("chars") or []:
                    idx = ch.get("char_idx")
                    if isinstance(idx, int):
                        wanted.add(idx)
    try:
        geom, bars = _geometry(path, page_number, wanted) if wanted else ({}, [])
    except Exception:
        return None
    _rehome_accents(grouped, geom)

    runs = []       # (block, direction, spans) per pdftext line, in order, before the joins and the gap cuts
    for block_index, block in enumerate(grouped):
        for line in block.get("lines") or []:
            spans = []
            last_added: dict | None = None      # the last character kept, across spans
            for span in line.get("spans") or []:
                font = span.get("font") or {}
                # Without the subset tag, as MuPDF names it: PDFium reports "ABCDEE+Calibri"
                # beside "Calibri" on 6767787c, and the two fonts where MuPDF sees one turned
                # two side-by-side course tables into a single six-column one downstream.
                font_name = _SUBSET_TAG.sub("", str(font.get("name") or ""))
                size = float(font.get("size") or 0.0)
                chars = []
                drawn_sizes: list[float] = []
                colors: dict[int, int] = {}
                span_style = (False, False)     # bold, italic from the font program (see _program_style)
                for ch in _join_surrogates(span.get("chars") or [], geom):
                    text = str(ch.get("char", ""))
                    if not text:
                        continue
                    g = geom.get(ch.get("char_idx"))
                    if g and g.get("style"):
                        span_style = (span_style[0] or g["style"][0], span_style[1] or g["style"][1])
                    if (g or {}).get("clipped"):
                        continue        # drawn outside its clip box: never on the page (see _geometry)
                    if text in ("\r", "\n") and (g or {}).get("generated"):
                        # PDFium's own line ends, not glyphs. They rode along as characters and
                        # were harmless until a Type 3 TeX page, where the raw-code recovery took
                        # the carriage return (0x0D) for cmr's "fl" ligature and an author block
                        # grew a column of "fl" cells (09f90a8f). A line end is a line end - and
                        # it is remembered on the character before it, because pdftext regroups
                        # by band and `_split_at_gaps` wants to know where PDFium stopped.
                        target = chars[-1] if chars else last_added
                        if target is not None:
                            target["line_end"] = True
                        continue
                    named = None
                    if (g and g.get("map_error") and len(text) == 1 and ord(text) == g.get("code", -1)
                            and not is_extension_font(font_name)):
                        # PDFium handed back the bare code: ask the PDF what the glyph is called
                        # before guessing from a TeX table. Adobe's fonts name their ligatures in
                        # parts ("f_i", "T_h"), which PDFium's glyph list lacks, and a page of
                        # Minion and Myriad read "non uorescent" and "us" for "Thus" (01ed6dcc);
                        # a dvips Type 3 font numbers its glyphs from 0 and names them by their
                        # codes, and the TeX guess had read its code 0 as cmr's Gamma ("Lobo RΓ",
                        # 0b65b6a5). The PDF's own name wins; the guess serves what has none.
                        # An extension font's codes stay raw: the maths stage decodes those itself.
                        if names is None:
                            names = glyph_names.page_glyph_names(path, page_number) or {}
                        adv = None
                        if (g or {}).get("bbox") and (g or {}).get("size"):
                            adv = (g["bbox"][2] - g["bbox"][0]) / g["size"] * 1000.0
                        # A font with no name is told from the others with none by the first
                        # width PDFium reports for it (see `_geometry`); with the resource picked
                        # out, its own /Differences name the glyph.
                        tables = (glyph_names.narrow(names, font_name, g.get("probe")) or names) if not font_name else names
                        named = glyph_names.text_for(tables, font_name, g["code"], adv)
                        if named:
                            text = named
                    if not named:
                        text = _as_mupdf_would(text, font_name, g)
                    box = (g or {}).get("bbox")
                    if len(text) == 1 and unicodedata.category(text) == "Mn":
                        # A combining mark - cmsy's negation slash, cmmi's vector arrow, a hat -
                        # stays a character of its own (every stage downstream assumes one code
                        # point per character) and takes a zero-width box at its own origin, which
                        # is where MuPDF boxes it (measured over the arXiv pages: at the origin
                        # every time, and the origin is usually the previous glyph's end - "0̸"
                        # then "="). Usually, not always: MnSymbol draws its tilde *before* the
                        # letter it covers, at the letter's start, and a box snapped to the
                        # previous glyph's end put it at the letter's end, where the maths stage
                        # hung it on the symbol after (06329: \tilde{=} for \tilde{L}). On PDFium's
                        # loose box it sat in the gap and attached to whatever followed.
                        prev = chars[-1] if chars else (spans[-1]["chars"][-1] if spans and spans[-1].get("chars") else None)
                        anchor = ((g or {}).get("origin") or (None,))[0]
                        if anchor is None and prev is not None:
                            anchor = prev["bbox"][2]
                        if anchor is not None and box is not None:
                            py0, py1 = box[1], box[3]
                            g = dict(g or {}, bbox=(anchor, py0, anchor, py1), origin=(anchor, (g or {}).get("origin", (anchor, py1))[1]))
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
                    # A name in parts is several characters on one glyph's box - "fi" from
                    # "f_i" - and they go in as a ligature's characters do, one box shared, for
                    # `_divide_shared_boxes` to lay out as MuPDF lays an expanded ligature out.
                    for piece in (list(text) if len(text) > 1 else [text]):
                        drawn_sizes.append(float((g or {}).get("size") or 0.0))
                        chars.append({
                            "c": piece,
                            "bbox": box,
                            "origin": origin,
                            "ink": (g or {}).get("ink"),
                            "generated": bool((g or {}).get("generated")),
                            "map_error": bool((g or {}).get("map_error")) and len(text) == 1,
                            # for the hidden-text rules: where in the painting order this
                            # character's object sits, whether it was drawn invisibly, and how
                            # opaque it is
                            "order": int((g or {}).get("order", -1)),
                            "invisible": bool((g or {}).get("invisible")),
                            "alpha": float((g or {}).get("alpha", 1.0)),
                        })
                    last_added = chars[-1]
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
                        "font": font_name,
                        "size": drawn,
                        "_fallback": size,
                        "flags": (_mupdf_flags(font, bool(span.get("superscript")))
                                  | (16 if span_style[0] else 0) | (2 if span_style[1] else 0)),
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
            _drop_tight_blanks(spans, direction)
            runs.append((block_index, direction, spans))
    blocks = []
    for block_index, direction, spans in _join_broken_lines(runs, bars):
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
    small = [c for sp in spans if 0.0 < float(sp.get("size") or 0.0) < 1.0 for c in sp["chars"] if not _is_blank(c)]
    if len(small) < 2:
        return
    y0 = min(c["bbox"][1] for c in small)
    y1 = max(c["bbox"][3] for c in small)
    for c in small:
        c["bbox"] = (c["bbox"][0], y0, c["bbox"][2], y1)


_DASHES = "-–—‐‑‒"


def _drop_tight_blanks(spans: list, direction) -> None:
    """Take out a blank PDFium makes up beside a dash in a run of digits.

    PDFium invents a blank at a tenth of an em - after the en dash of "1726–1728" on a page of
    references, which then read "1726– 1728" and failed its check; MuPDF's own blanks start at
    0.16 em. A range of numbers never has a blank at its dash, so that one goes.

    The general rule - drop every invented blank in a gap under a word space - was written and
    measured, and cost five checks on one quick-gate page (26076dc, "Birthweight2690 g",
    "Elective forcephalopelvic"): a tightly set page's word gaps measure under 0.15 em between
    glyph boxes though not between pen positions, and there PDFium's blanks were right. The
    gap between boxes is not the measure MuPDF uses, so the blanket rule is not safe.
    """
    flat = [(sp, c) for sp in spans for c in sp["chars"]]
    for k, (sp, c) in enumerate(flat):
        if not (c.get("generated") and c["c"] == " ") or k == 0 or k == len(flat) - 1:
            continue
        before, after = flat[k - 1][1]["c"], flat[k + 1][1]["c"]
        if (before in _DASHES and after.isdigit()) or (after in _DASHES and before.isdigit()):
            sp["chars"].remove(c)
    for sp in list(spans):
        if not sp["chars"]:
            spans.remove(sp)


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
            if not _is_blank(c):
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
            if o and not _is_blank(c):
                by_size.setdefault(s, []).append(-o[0] * dy + o[1] * dx)
    if not by_size:
        return 0.0, None
    size = max(by_size, key=lambda s: len(by_size[s]))
    bases = sorted(by_size[size])
    return size, bases[len(bases) // 2]


_BAR_MAX_HEIGHT = 1.5   # a fraction bar is a filled rectangle no taller than this, in points


def _over_a_bar(spans: list, bars: list, direction) -> bool:
    """Does this run sit on a fraction bar - a rule just beneath it, spanning most of it?

    A numerator in text style rises 0.39 em, a superscript 0.41: nothing in the baseline tells
    them apart, and welding the numerator into the text line tore every inline fraction on
    four sample pages (the denominator, which starts back under it, could not follow). The
    bar can tell them apart. Level lines only.
    """
    if not bars or direction != (1.0, 0.0):
        return False
    x0, y0, x1, y1 = _union(spans)
    width = x1 - x0
    if width <= 0:
        return False
    reach = max(y1 - y0, 1.0)
    for bx0, by0, bx1, by1 in bars:
        if y1 - 0.2 * reach <= by0 <= y1 + 0.8 * reach and min(x1, bx1) - max(x0, bx0) >= 0.6 * width:
            return True
    return False


def _continues(prev: list, spans: list, direction, bars: list | None = None) -> bool:
    """Does this run carry straight on from the last one - the same line, cut by PDFium?"""
    a = _edge_glyph(prev, first=False)
    b = _edge_glyph(spans, first=True)
    if a is None or b is None:
        return False
    if bars and _over_a_bar(spans, bars, direction):
        return False
    (ca, sa), (cb, sb) = a, b
    size = max(sa, sb, ca["bbox"][3] - ca["bbox"][1], cb["bbox"][3] - cb["bbox"][1], 1.0)
    # It starts no further back than the last glyph (a subscript stacked under a superscript
    # starts level with it), ...
    if _along(cb["bbox"], direction)[0] < _along(ca["bbox"], direction)[0] - 0.1 * size:
        return False
    # ... and no further on than an em beyond the line's end. PDFium ended the line there for
    # a reason: on a page with a 44pt drop cap (0e5f0c34) the first line of column one and the
    # line of column two on the same baseline, 1.44 em apart across the gutter, were welded
    # into one line and the column finder lost the page. A superscript or a torn fraction
    # starts within the line; a run that begins an em past it is the next thing on the page.
    gap = _object_gap()
    if gap > 0 and _along(cb["bbox"], direction)[0] - _along(ca["bbox"], direction)[1] > gap * size:
        return False
    # ... and its baseline is within half an em of the line's, or of the last glyph's. A
    # superscript rises a third to a half of an em and stays; a fraction's numerator rises
    # two thirds and starts a line of its own - as it does for MuPDF - so that the maths stage
    # can pair it with the bar and the denominator beneath (a "script-sized" clause that
    # welded any small raised run tore every inline fraction on four sample pages: the
    # numerator went into the text line and the denominator could not follow). The rows of
    # a matrix are full-size text on baselines of their own, and stay lines of their own.
    oa, ob = ca.get("origin"), cb.get("origin")
    if oa and ob:
        dx, dy = direction
        a_base, b_base = -oa[0] * dy + oa[1] * dx, -ob[0] * dy + ob[1] * dx
        main_size, main_base = _line_main(prev, direction)
        on_line = main_base is not None and abs(b_base - main_base) <= 0.5 * max(main_size, sb)
        on_last = abs(b_base - a_base) <= 0.5 * max(sa, sb, 1.0)
        if not (on_line or on_last):
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
    # A word's gap between the two halves keeps a blank, as MuPDF would have put one. So does
    # a run that starts back under the last glyph: a fraction's denominator under its
    # numerator, which PDFium had already set on the text line ("n-" then "1"). Without the
    # blank the word builder, which measures gaps forward, read the pair as one word "14"
    # and the maths stage never saw a fraction (2503.03899). MuPDF puts a blank at any jump.
    if a is not None and b is not None:
        (ca, sa), (cb, sb) = a, b
        size = max(sa, sb, ca["bbox"][3] - ca["bbox"][1], 1.0)
        gap = _along(cb["bbox"], direction)[0] - _along(ca["bbox"], direction)[1]
        if gap >= _WORD_GAP * size or gap < -0.1 * size:
            x0, y0, x1, y1 = ca["bbox"]
            prev[-1]["chars"].append(dict(ca, c=" ", bbox=(x1, y0, x1, y1), origin=(x1, (ca.get("origin") or (x1, y1))[1]),
                                          ink=None, generated=True))
    prev.extend(spans)


def _join_broken_lines(runs: list, bars: list | None = None) -> list:
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
    joining = os.environ.get("TRUEDOC_LINE_JOIN", "1").strip() != "0"     # off, for measuring
    out: list[tuple[int, tuple[float, float], list]] = []
    for block_index, direction, spans in runs:
        if out and _edge_glyph(spans, first=True) is None:
            # Nothing but blanks - the space PDFium makes up between two words of turned
            # text, which it files as a level line of its own and so cuts the text at every
            # word. It belongs to the run before it, as the blank it is.
            out[-1][2].extend(spans)
        elif joining and out and out[-1][1] == direction and _continues(out[-1][2], spans, direction, bars):
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


def _object_gap() -> float:
    """How wide a gap ends a line where the text object changes with it, as a multiple of the
    font size. 0 disables the rule."""
    try:
        return float(os.environ.get("TRUEDOC_OBJECT_GAP", _OBJECT_GAP))
    except (TypeError, ValueError):
        return _OBJECT_GAP


# A number or letter with its dot or bracket, or a bullet. Not a dash or an asterisk: a table
# puts those in a cell of their own (an empty value, a significance mark), and the column finder
# needs that cell apart from the next.
_LIST_MARKER = re.compile(r"^(\(?\d{1,3}[.)]|\(?[A-Za-z][.)]|[•·▪◦‣])$")


def _is_list_marker(flat: list, start: int, end: int) -> bool:
    """Is the run from `start` to `end` a list's marker - "1.", "a)", a bullet - and nothing else?

    Word sets a numbered list's marker as a text object of its own, an em before its text
    ("1." then "Specific program requirements" on 6767787c), and the object-gap rule cut the
    marker off; the markers then stood as a column of their own, and the whitespace-table
    finder grew one eight-column table over the whole section. MuPDF keeps each item as one
    line. A marker stays with the text that follows it; a table row's first cell is not one."""
    text = "".join(c["c"] for _, c in flat[start:end] if not _is_blank(c)).strip()
    return 0 < len(text) <= 4 and bool(_LIST_MARKER.match(text))


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
    object_gap = _object_gap()
    dx, dy = direction
    flat = [(si, c) for si, sp in enumerate(spans) for c in sp["chars"]]
    sizes = sorted(max(float(spans[si]["size"] or 0.0), c["bbox"][3] - c["bbox"][1])
                   for si, c in flat if not _is_blank(c))
    # The line's own size, for the baseline rule below: the upper quartile of its glyphs. The
    # median failed on a wrapped tail of six glyphs, four of them scripts ("χ⁻₂,₅." on
    # 2503.06293), where it fell to the script size and a script's step looked like a line;
    # the upper quartile is the text's size there, and still the text's on a line that holds
    # one 44pt drop cap among twenty letters.
    line_size = sizes[(3 * len(sizes)) // 4] if sizes else 0.0
    cuts: set[int] = set()
    piece_start = 0   # where the piece being built began: the last cut, or the line's start
    prev = None       # (index in flat, end along the line, scale, start along the line, text object)
    for i, (si, c) in enumerate(flat):
        if _is_blank(c):
            continue
        x0, y0, x1, y1 = c["bbox"]
        ends = [x0 * dx + y0 * dy, x1 * dx + y0 * dy, x0 * dx + y1 * dy, x1 * dx + y1 * dy]
        start, end = min(ends), max(ends)
        # Not the reported size: a Type 3 font reports its matrix scale instead (1.0 here,
        # which would make every gap look enormous), so take the taller of the two.
        scale = max(float(spans[si]["size"] or 0.0), y1 - y0)
        ox, oy = c.get("origin") or (x0, y1)
        base = -ox * dy + oy * dx
        if prev is not None and scale > 0 and start - prev[1] >= limit * max(scale, prev[2]):
            cuts.add(i)
        # A baseline a whole em away is another line, as it is for MuPDF. pdftext groups by the
        # band a character overlaps, so a 44pt drop cap, its baseline 24pt below the text's,
        # went into the first line of its column (0e5f0c34): the line stood 45pt tall, overlapped
        # the neighbouring column's line, and the two were joined downstream and the page's
        # columns lost. MuPDF sets the drop cap on a line of its own. Scripts step a third to
        # a half of an em and stay (a step rule at 0.3 to 0.6 was measured and moved nothing);
        # an em is beyond any script. Measured in ems of the line's own size - the median of its
        # glyphs - not of either glyph at the step: the drop cap's 44pt would hide a 24pt step
        # that is nearly three ems of the text beside it, and a 5pt superscript's own size would
        # make the 7pt return to the 10pt text look like a line of its own.
        elif prev is not None and line_size > 0 and abs(base - prev[6]) > _BASELINE_STEP * line_size:
            cuts.add(i)
        # A pen that jumps backwards starts a new line, as it does for MuPDF. pdftext files
        # every span that overlaps a line's band in that line whatever its order, so a table
        # row drawn right to left arrived as one line with its characters running backwards -
        # "0.658", "0.77**", "0.31*" - and the word builder, which measures each gap from the
        # character before, glued them into one word and one cell (b5c5b866, the quick gate).
        # Kerning pulls a glyph back a fraction of an em at most; half an em is a jump.
        elif prev is not None and scale > 0 and start < prev[3] - 0.5 * max(scale, prev[2]):
            cuts.add(i)
        # A smaller gap ends a line where the file's own text run ends with it: MuPDF follows
        # the text-showing runs, and a table row it read as "Listening to speech or lecture"
        # and "118" (two runs, a 1.1-em gap) arrived from pdftext as one line, and the column
        # finder then read one cell (5bdc8382, 105e91a0). Off at 0; the threshold is measured.
        # ... or where PDFium's own text page ended a line. pdftext regroups characters by the
        # band they overlap, so a 44pt drop cap's band took in the first line of column one and
        # the line of column two beside it (0e5f0c34), 1.44 em apart - under the 1.5-em rule,
        # and in one text object, so the run rule could not see it either. PDFium had stopped
        # the line at the gutter; where it stopped and an em of space follows, so does this.
        # A list's marker is the exception: "1." set as a text object of its own, an em before
        # its item, stays with it (see `_is_list_marker`; the general limit above still cuts).
        elif (prev is not None and scale > 0 and object_gap > 0
              and (c.get("order", -1) != prev[4] or prev[5])
              and start - prev[1] >= object_gap * max(scale, prev[2])
              and not _is_list_marker(flat, piece_start, i)):
            cuts.add(i)
        if i in cuts:
            piece_start = i
        prev = (i, end, scale, start, c.get("order", -1), bool(c.get("line_end")), base)
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
        while piece and _is_blank(piece[0][1]):
            piece = piece[1:]
        while piece and _is_blank(piece[-1][1]):
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
        if prev is not None and not _is_blank(c) and not _is_blank(prev):
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
        if (str(c.get("char", "")).isspace() and not g.get("map_error")) or g.get("generated"):
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
