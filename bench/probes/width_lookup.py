"""RAA's landlord PDS page 22: the advance PDFium's width lookup gives an "f", against where the f really ends.

TrueDoc boxes a level character from its origin to its origin plus the advance `FPDFFont_GetGlyphWidth` returns for the
character's Unicode value (`pdftext_rawdict._geometry`). This page's font maps its ff and fi ligatures to "f" as well,
and asked for "f" PDFium answers with a ligature's width, 7.34pt, where the space after the f starts 2.54pt along: each
f's box ran over the space and "If you" read "Ifyou". For each place the file keeps a space after an "f" - and, to
compare, a letter before a space that was never lost - this prints the letter's origin, the lookup's advance and where
it ends, the loose box's right edge, and the origins of the space and of the next letter; then the boxes TrueDoc's own
reader gives the same characters (stopped at the next character since 15 September).

usage (repo root): width_lookup.py
"""
import ctypes
import os
import sys

import pypdfium2 as pdfium
import pypdfium2.raw as raw

from truedoc.extract import pdftext_rawdict

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import doc_library  # noqa: E402
PDF = doc_library.absolute("RAA/landlord-insurance/"
                           "raa-landlord-and-short-stay-insurance-pds-product-disclosure-statement-30-9-2021_0f6ceea4.pdf")
PATTERNS = ["If you", "of these", "of 21", "if due", "of your", "you or", "the "]


def lookup_part() -> None:
    doc = pdfium.PdfDocument(PDF)
    page = doc[21]
    tp = page.get_textpage()
    n = tp.count_chars()
    text = "".join(chr(raw.FPDFText_GetUnicode(tp.raw, i)) for i in range(n))
    ox, oy = ctypes.c_double(), ctypes.c_double()
    matrix = raw.FS_MATRIX()
    loose = raw.FS_RECTF()
    adv = ctypes.c_float()
    buf, flags = ctypes.create_string_buffer(256), ctypes.c_int()
    for pattern in PATTERNS:
        start = text.find(pattern)
        if start < 0:
            print(f"{pattern!r}: not found")
            continue
        i = start + pattern.index(" ") - 1
        code = raw.FPDFText_GetUnicode(tp.raw, i)
        raw.FPDFText_GetCharOrigin(tp.raw, i, ox, oy)
        origin = ox.value
        raw.FPDFText_GetMatrix(tp.raw, i, matrix)
        obj = raw.FPDFText_GetTextObject(tp.raw, i)
        font = raw.FPDFTextObj_GetFont(obj) if obj else None
        size = abs(raw.FPDFText_GetFontSize(tp.raw, i))
        ok = raw.FPDFFont_GetGlyphWidth(font, code, size, adv) if font else 0
        advance = adv.value * (abs(matrix.a) or 1.0)
        raw.FPDFText_GetLooseCharBox(tp.raw, i, loose)
        raw.FPDFText_GetCharOrigin(tp.raw, i + 1, ox, oy)
        space_origin = ox.value
        raw.FPDFText_GetCharOrigin(tp.raw, i + 2, ox, oy)
        next_origin = ox.value
        raw.FPDFText_GetFontInfo(tp.raw, i, buf, 256, flags)
        print(f"{pattern!r:11s} {chr(code)!r} font {buf.value.decode('latin-1')[:28]:28s} origin {origin:7.2f}"
              f"  advance {advance:5.2f} (ok {ok}) ends {origin + advance:7.2f}  loose right {loose.right:7.2f}"
              f"  space origin {space_origin:7.2f}  next origin {next_origin:7.2f}  scale {matrix.a:.3f}")
    tp.close()
    page.close()
    doc.close()


def reader_part() -> None:
    d = pdftext_rawdict.build(PDF, 22)
    if not d:
        print("the reader returned nothing")
        return
    for block in d.get("blocks", []):
        for line in block.get("lines", []):
            chars = [ch for span in line.get("spans", []) for ch in span.get("chars", [])]
            line_text = "".join(ch.get("c", "") for ch in chars)
            for pattern in ("Ifyou", "If you", "ofthese", "of these", "of21", "of 21"):
                at = line_text.find(pattern)
                if at < 0:
                    continue
                f_at = at + pattern.index("f")
                cells = [f"{ch.get('c', '')!r} {ch['bbox'][0]:.2f}-{ch['bbox'][2]:.2f}"
                         for ch in chars[max(0, f_at - 1):f_at + 3]]
                print(f"reader {pattern!r}: " + " | ".join(cells))


if __name__ == "__main__":
    lookup_part()
    reader_part()
