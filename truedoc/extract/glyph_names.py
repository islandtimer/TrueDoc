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
            probe = None
            if str(f.get("/Subtype", "")) == "/Type3":
                fm = [float(v) for v in (f.get("/FontMatrix") or [0.001, 0, 0, 0.001, 0, 0])]
                scale = (abs(fm[0]) + abs(fm[1])) * 1000.0 if len(fm) >= 2 else 1.0
                widths = [w * scale for w in widths]
                # PDFium answers `FPDFFont_GetGlyphWidth` for every code of a Type 3 font with
                # its first /Widths entry (measured on 0b65b6a5: 0.770, 0.718 and 0.437 for its
                # three unnamed fonts, each the first width times the font matrix). A quirk,
                # and the one thing that tells three fonts with no name apart.
                probe = widths[0] if widths else None
            out[base].append((names, widths, first, probe))
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
    if not tables or not _named(tables, font):
        return None
    for _names, widths, first, *_ in tables.get(_SUBSET.sub("", font), []):
        i = code - first
        if 0 <= i < len(widths):
            return widths[i]
    return None


def _named(tables: dict, font: str) -> bool:
    """A font with no name cannot be told from another with none - a TeX page set in seven
    Type 3 fonts, none with a /BaseFont, matched the first of them for every glyph - unless
    the tables hold exactly one such font, or `narrow` has already picked it out."""
    return bool(font) or len(tables.get("", [])) == 1


def narrow(tables: dict | None, font: str, probe: float | None) -> dict | None:
    """The one resource of this name whose first width is `probe` (thousandths of an em), as a
    table of its own, or None when none or several match.

    PDFium reports a Type 3 font's first /Widths entry as the width of every glyph, which is
    useless as an advance and decisive as a fingerprint: with it, a page's unnamed fonts can be
    told apart and each glyph read from its own font's /Differences and /Widths."""
    if not tables or probe is None:
        return None
    key = _SUBSET.sub("", font)
    hits = [entry for entry in tables.get(key, []) if entry[3] is not None and abs(entry[3] - probe) <= 0.01 * max(abs(probe), 1.0)]
    if len(hits) != 1:
        return None
    return {key: hits}


def text_for(tables: dict | None, font: str, code: int, advance_per_em: float | None = None) -> str | None:
    """The text a glyph's name gives, or None when the page has no name for it.

    `advance_per_em` is the character's advance in thousandths of an em, used to choose
    between resources of the same name that both define the code.
    """
    if not tables or not _named(tables, font):
        return None
    from fontTools import agl

    candidates = [c for c in tables.get(_SUBSET.sub("", font), []) if code in c[0]]
    if not candidates:
        return None
    if len(candidates) > 1 and advance_per_em is not None:
        def distance(c) -> float:
            names, widths, first = c[0], c[1], c[2]
            i = code - first
            return abs(widths[i] - advance_per_em) if 0 <= i < len(widths) else 1e9
        candidates.sort(key=distance)
    name = candidates[0][0][code]
    text = agl.toUnicode(name)
    if not text and name.isdigit():
        # A name that is nothing but a decimal number is the character's code: dvips names
        # a Type 3 font's glyphs that way ("/76" for L, "/111" for o on 0b65b6a5), the glyph
        # list knows no such name, and MuPDF reads the page. Measured against MuPDF's text of
        # that page: the decimal reading gives its words.
        try:
            value = int(name)
            text = chr(value) if 0x20 <= value < 0x110000 else ""
        except (ValueError, OverflowError):
            text = ""
    if not text:
        return None
    # The glyph list's Ohm sign for "Omega" and its one-character ligatures for "fi" and "fl"
    # fold to the letters, which is what the MuPDF path delivers (ligatures expanded).
    import unicodedata
    return unicodedata.normalize("NFKC", text)


def _to_unicode_map(font) -> dict[int, str]:
    """A simple font's ToUnicode map, single codes and ranges (a range given as an array is not read)."""
    stream = font.get("/ToUnicode")
    if stream is None:
        return {}
    if hasattr(stream, "get_object"):
        stream = stream.get_object()
    try:
        text = stream.get_data().decode("latin-1", "replace")
    except Exception:
        return {}
    out: dict[int, str] = {}
    for block in re.findall("beginbfchar(.*?)endbfchar", text, re.S):
        for a, b in re.findall("<([0-9A-Fa-f]+)>[ ]*<([0-9A-Fa-f]+)>", block):
            try:
                out[int(a, 16)] = bytes.fromhex(b).decode("utf-16-be")
            except ValueError:
                continue
    for block in re.findall("beginbfrange(.*?)endbfrange", text, re.S):
        for a, b, c in re.findall("<([0-9A-Fa-f]+)>[ ]*<([0-9A-Fa-f]+)>[ ]*<([0-9A-Fa-f]+)>", block):
            lo, hi, start = int(a, 16), int(b, 16), int(c, 16)
            for k in range(lo, min(hi, lo + 255) + 1):
                if start + k - lo < 0x110000:
                    out[k] = chr(start + k - lo)
    return out


_LIGATURE_DOCS: dict[tuple, dict] = {}
_LIGATURE_DOCS_MAX = 2


def _ligature_document(path: str) -> dict | None:
    """The file read once for the ligature reading and kept for its later pages: its pypdf reader, and each font
    object's codes as `_font_codes` finds them, by object number. Read into memory, so no file handle is held.

    Opening the file with pypdf for every page cost RAA's 60-page PDS about 600 ms a page, pages with nothing to mend
    included - 44% of the reader's time."""
    try:
        import io

        import pypdf

        st = os.stat(path)
        key = (os.path.abspath(path), st.st_mtime_ns, st.st_size)
        doc = _LIGATURE_DOCS.get(key)
        if doc is None:
            with open(path, "rb") as fh:
                data = fh.read()
            doc = {"reader": pypdf.PdfReader(io.BytesIO(data)), "fonts": {}}
            if len(_LIGATURE_DOCS) >= _LIGATURE_DOCS_MAX:
                _LIGATURE_DOCS.pop(next(iter(_LIGATURE_DOCS)))
            _LIGATURE_DOCS[key] = doc
        return doc
    except Exception:
        return None


def _font_codes(doc: dict, ref) -> tuple[dict[int, str], dict[int, str]] | None:
    """A simple font's ToUnicode map and {code: letters} for each code whose glyph name gives more letters than the map,
    beginning with the map's ("f_f" mapped to "f"); cached by object number. None for a font without /Differences or
    with two-byte codes."""
    number = getattr(ref, "idnum", None)
    if number is not None and number in doc["fonts"]:
        return doc["fonts"][number]
    import unicodedata

    from fontTools import agl

    f = ref.get_object() if hasattr(ref, "get_object") else ref
    found = None
    if str(f.get("/Subtype", "")) != "/Type0":
        enc = f.get("/Encoding")
        if hasattr(enc, "get_object"):
            enc = enc.get_object()
        diffs = enc.get("/Differences") if isinstance(enc, dict) else None
        if diffs:
            unicode_map = _to_unicode_map(f)
            spoiled: dict[int, str] = {}
            code = 0
            for item in diffs:
                if isinstance(item, (int, float)):
                    code = int(item)
                    continue
                letters = unicodedata.normalize("NFKC", agl.toUnicode(str(item).lstrip("/")) or "")
                mapped = unicode_map.get(code)
                if mapped and len(letters) > len(mapped) and letters.startswith(mapped):
                    spoiled[code] = letters
                code += 1
            found = (unicode_map, spoiled)
    if number is not None:
        doc["fonts"][number] = found
    return found


def lossy_ligature_letters(path: str, page_number: int, pdfium_chars: list[tuple[int, str]]) -> dict[int, str]:
    """{PDFium character index: letters} for the characters drawn with a ligature glyph the text layer spoils.

    RAA's landlord PDS maps the codes of its ff and fi ligatures to "f" in its ToUnicode map, so the file's own text
    reads "ofer", "fnd" and "Cooling-of"; the encoding still names those glyphs "f_f" and "fi". PDFium reports a
    character's Unicode but not its code, and not in the content stream's order and number, so the content stream is
    read here with pypdf, each code through its font's ToUnicode map, and that text aligned with PDFium's: a character
    drawn with a code whose name gives more letters than the map, beginning with the map's, takes the name's letters.
    On RAA's page 22 all 2,035 characters pair and all 14 such glyphs land on their f's. The file is read once per
    document and each font's codes worked out once, so a page whose fonts spoil nothing costs a few lookups; only a page
    that has such a code reads its content stream. An alignment that pairs fewer than nine in ten of PDFium's
    characters is not trusted. Simple fonts only: a two-byte font's codes are not read, nor text inside a form XObject.

    `pdfium_chars` is (index, text) for each character PDFium did not make up, in PDFium's order.
    """
    if not path or not pdfium_chars or not available():
        return {}
    try:
        import difflib

        from pypdf.generic import ByteStringObject, ContentStream, TextStringObject

        doc = _ligature_document(path)
        if doc is None:
            return {}
        reader = doc["reader"]
        page = reader.pages[page_number - 1]
        resources = page.get("/Resources") or {}
        if hasattr(resources, "get_object"):
            resources = resources.get_object()
        fonts = resources.get("/Font") or {}
        if hasattr(fonts, "get_object"):
            fonts = fonts.get_object()
        maps: dict[str, dict[int, str]] = {}
        spoiled: dict[str, dict[int, str]] = {}
        for key, ref in fonts.items():
            codes = _font_codes(doc, ref)
            if codes is None:
                continue
            maps[str(key)] = codes[0]
            if codes[1]:
                spoiled[str(key)] = codes[1]
        if not spoiled:
            return {}
        stream: list[tuple[str, str | None, int]] = []     # (character, font resource, code), as drawn
        font = None
        for operands, op in ContentStream(page.get_contents(), reader).operations:
            if op == b"Tf" and operands:
                font = str(operands[0])
                continue
            if op in (b"Tj", b"'", b'"') and operands:
                items = operands[-1:]
            elif op == b"TJ" and operands:
                items = [x for x in operands[0] if isinstance(x, (TextStringObject, ByteStringObject))]
            else:
                continue
            for item in items:
                data = bytes(item.original_bytes) if hasattr(item, "original_bytes") else bytes(item)
                for code in data:
                    for ch in maps.get(font, {}).get(code) or "?":
                        stream.append((ch, font, code))
        ours = [text for _, text in pdfium_chars]
        blocks = difflib.SequenceMatcher(None, [s[0] for s in stream], ours, autojunk=False).get_matching_blocks()
        if sum(b.size for b in blocks) < 0.9 * len(ours):
            return {}
        out: dict[int, str] = {}
        for b in blocks:
            for k in range(b.size):
                _ch, font_key, code = stream[b.a + k]
                letters = spoiled.get(font_key or "", {}).get(code)
                if letters and ours[b.b + k] == maps[font_key].get(code):
                    out[pdfium_chars[b.b + k][0]] = letters
        return out
    except Exception:
        return {}
