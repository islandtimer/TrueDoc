"""Name the glyphs PDFium cannot map, from the PDF's own font dictionaries (M18, D007).

A font's /Encoding /Differences array names each code's glyph, and PDFium resolves those names
through the Adobe Glyph List. Names built from parts - "f_i", "f_f_i", "T_h", the OpenType
convention Adobe's fonts use for their ligatures - are not in that list, and PDFium hands the
character back as its bare code with a mapping error: a page of Minion and Myriad lost every
"fi", "fl" and "Th" ("non uorescent", "de nes", "us" for "Thus"). MuPDF reads the name itself.

The names are in the PDF, not in PDFium's API, so they are read with pypdf (BSD-3) and turned
into text with fontTools' glyph list (MIT), which knows the AGL, uniXXXX, and names in parts.
Measured on the two benchmark pages that lost checks to this: every one of the 77 unmapped
characters resolved, and every one agreed with MuPDF's reading (the ligatures expanded).

Two font resources can share a base name and differ in their tables (MinionPro-Regular twice,
one with "/fraction" on code 31 and one with "/f_l"); PDFium names the font but not the
resource, so the glyph's advance settles it: the loose box PDFium reports is the /Widths entry
of the resource that drew it.
"""
from __future__ import annotations

import os
import re
from collections import defaultdict

_SUBSET = re.compile(r"^[A-Z]{6}\+")
_CACHE: dict[tuple, dict] = {}
_CACHE_MAX = 4


def available() -> bool:
    try:
        import pypdf  # noqa: F401
        from fontTools import agl  # noqa: F401
    except Exception:
        return False
    return True


def _differences(path: str, page_number: int) -> dict[str, list[tuple[dict[int, str], list[float], int]]]:
    """{base font name: [(code -> glyph name, /Widths, /FirstChar), ...]} for one page's fonts."""
    import pypdf

    out: dict[str, list] = defaultdict(list)
    reader = pypdf.PdfReader(path)
    page = reader.pages[page_number - 1]
    resources = page.get("/Resources") or {}
    if hasattr(resources, "get_object"):
        resources = resources.get_object()
    fonts = resources.get("/Font") or {}
    if hasattr(fonts, "get_object"):
        fonts = fonts.get_object()
    for _key, ref in fonts.items():
        try:
            f = ref.get_object() if hasattr(ref, "get_object") else ref
            base = _SUBSET.sub("", str(f.get("/BaseFont", "")).lstrip("/"))
            enc = f.get("/Encoding")
            if hasattr(enc, "get_object"):
                enc = enc.get_object()
            diffs = enc.get("/Differences") if isinstance(enc, dict) else None
            names: dict[int, str] = {}
            if diffs:
                code = 0
                for item in diffs:
                    if isinstance(item, (int, float)):
                        code = int(item)
                    else:
                        names[code] = str(item).lstrip("/")
                        code += 1
            widths = [float(w) for w in (f.get("/Widths") or [])]
            first = int(f.get("/FirstChar", 0) or 0)
            if not names and not widths:
                continue
            # A Type 3 font's widths are in its own glyph space, which its /FontMatrix maps to
            # text space; every other font's are thousandths of an em. Kept as thousandths
            # either way, so a width reads the same whatever the font.
            scale = 1.0
            if str(f.get("/Subtype", "")) == "/Type3":
                fm = [float(v) for v in (f.get("/FontMatrix") or [0.001, 0, 0, 0.001, 0, 0])]
                scale = (abs(fm[0]) + abs(fm[1])) * 1000.0 if len(fm) >= 2 else 1.0
                widths = [w * scale for w in widths]
            out[base].append((names, widths, first))
        except Exception:
            continue
    return out


def page_glyph_names(path: str, page_number: int) -> dict | None:
    """The page's /Differences tables by base font name, cached; None when they cannot be read."""
    if not path or not available():
        return None
    try:
        st = os.stat(path)
        key = (os.path.abspath(path), page_number, st.st_mtime_ns, st.st_size)
    except (OSError, TypeError):
        return None
    if key in _CACHE:
        return _CACHE[key]
    try:
        tables = _differences(path, page_number)
    except Exception:
        tables = {}
    if len(_CACHE) >= _CACHE_MAX:
        _CACHE.pop(next(iter(_CACHE)))
    _CACHE[key] = tables
    return tables


def advance_for(tables: dict | None, font: str, code: int) -> float | None:
    """A glyph's advance from the PDF's own /Widths, in thousandths of an em, or None.

    MuPDF's box for a character is its origin plus this advance. PDFium's is too, except for a
    character it could not map to Unicode, whose advance it looks up by Unicode and so cannot
    find: its loose box is then the glyph's ink, and cmex's brace pieces - 4pt of ink on an
    advance of 10 - stood out of line with each other and a cases brace read as three braces.
    """
    if not tables or not font:
        # A font with no name cannot be told from another with none: a TeX page set in seven
        # Type 3 fonts, none with a /BaseFont, matched the first of them for every glyph.
        return None
    for _names, widths, first in tables.get(_SUBSET.sub("", font), []):
        i = code - first
        if 0 <= i < len(widths):
            return widths[i]
    return None


def text_for(tables: dict | None, font: str, code: int, advance_per_em: float | None = None) -> str | None:
    """The text a glyph's name gives, or None when the page has no name for it.

    `advance_per_em` is the character's advance in thousandths of an em, used to choose
    between resources of the same name that both define the code.
    """
    if not tables or not font:
        return None
    from fontTools import agl

    candidates = [c for c in tables.get(_SUBSET.sub("", font), []) if code in c[0]]
    if not candidates:
        return None
    if len(candidates) > 1 and advance_per_em is not None:
        def distance(c) -> float:
            names, widths, first = c
            i = code - first
            return abs(widths[i] - advance_per_em) if 0 <= i < len(widths) else 1e9
        candidates.sort(key=distance)
    name = candidates[0][0][code]
    text = agl.toUnicode(name)
    if not text:
        return None
    # The glyph list's Ohm sign for "Omega" and its one-character ligatures for "fi" and "fl"
    # fold to the letters, which is what the MuPDF path delivers (ligatures expanded).
    import unicodedata
    return unicodedata.normalize("NFKC", text)
