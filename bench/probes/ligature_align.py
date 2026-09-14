"""RAA's landlord PDS page 22: find each ligature glyph the content stream draws among PDFium's characters.

The page's Unicode map sends the ff, fi, fl and ffi glyphs' codes to "f", so the file's text reads "ofer" and "fnd";
the encoding's /Differences still names each code's glyph. PDFium reports each character's Unicode but not its code,
and its characters are not the codes drawn one for one: on this page the stream draws 2,078 codes where PDFium reports
2,035 characters it did not make up, in another order. Both texts come from the same ToUnicode map, so this walks the
page's content stream with pypdf (following the font each text operator sets), reads every code through the font's
ToUnicode map (single codes and ranges), aligns that text with PDFium's by sequence, and for each ligature glyph drawn
says which PDFium character it lands on and the text around it. On 15 September: all 2,035 characters paired, and all
14 ligature glyphs landed on their f's. Text drawn inside form XObjects is not walked; two-byte codes are not read.

usage (repo root): ligature_align.py
"""
import difflib
import os
import re
import sys

import pypdf
import pypdfium2 as pdfium
import pypdfium2.raw as raw
from pypdf.generic import ByteStringObject, ContentStream, TextStringObject

sys.stdout.reconfigure(encoding="utf-8")
PDF = os.path.join("C:/", "Users", "griff", "OneDrive", "Documents", "10 Have a crack", "25 InsurancePlatform",
                   "uploads", "PDS Docs", "RAA", "landlord-insurance",
                   "raa-landlord-and-short-stay-insurance-pds-product-disclosure-statement-30-9-2021_0f6ceea4.pdf")
PAGE = 22
LIGATURES = {"f_f": "ff", "ff": "ff", "f_i": "fi", "fi": "fi", "f_l": "fl", "fl": "fl",
             "f_f_i": "ffi", "ffi": "ffi", "f_f_l": "ffl", "ffl": "ffl"}


def obj(x):
    return x.get_object() if hasattr(x, "get_object") else x


def parse_cmap(text: str) -> dict[int, str]:
    out: dict[int, str] = {}
    for block in re.findall("beginbfchar(.*?)endbfchar", text, re.S):
        for a, b in re.findall("<([0-9A-Fa-f]+)>[ ]*<([0-9A-Fa-f]+)>", block):
            out[int(a, 16)] = bytes.fromhex(b).decode("utf-16-be", "replace")
    for block in re.findall("beginbfrange(.*?)endbfrange", text, re.S):
        for a, b, c in re.findall("<([0-9A-Fa-f]+)>[ ]*<([0-9A-Fa-f]+)>[ ]*<([0-9A-Fa-f]+)>", block):
            lo, hi, start = int(a, 16), int(b, 16), int(c, 16)
            for k in range(lo, hi + 1):
                out[k] = chr(start + k - lo)
    return out


def glyph_names(font) -> dict[int, str]:
    enc = obj(font.get("/Encoding"))
    names: dict[int, str] = {}
    if isinstance(enc, dict) and enc.get("/Differences"):
        code = 0
        for item in enc.get("/Differences"):
            if isinstance(item, (int, float)):
                code = int(item)
            else:
                names[code] = str(item).lstrip("/")
                code += 1
    return names


def raw_bytes(item) -> bytes:
    return bytes(item.original_bytes) if hasattr(item, "original_bytes") else bytes(item)


def main() -> None:
    reader = pypdf.PdfReader(PDF)
    page = reader.pages[PAGE - 1]
    fonts = obj(obj(page.get("/Resources")).get("/Font"))
    maps, names = {}, {}
    for key, ref in fonts.items():
        f = obj(ref)
        maps[str(key)] = parse_cmap(obj(f.get("/ToUnicode")).get_data().decode("latin-1", "replace")) if "/ToUnicode" in f else {}
        names[str(key)] = glyph_names(f)
    stream = []   # one element per character of text: (character, font resource, code, glyph name)
    font = None
    for operands, op in ContentStream(page.get_contents(), reader).operations:
        items = []
        if op == b"Tf":
            font = str(operands[0])
        elif op in (b"Tj", b"'", b'"'):
            items = [operands[-1]]
        elif op == b"TJ":
            items = [x for x in operands[0] if isinstance(x, (TextStringObject, ByteStringObject))]
        for item in items:
            for code in raw_bytes(item):
                for ch in maps.get(font, {}).get(code) or "?":
                    stream.append((ch, font, code, names.get(font, {}).get(code)))
    doc = pdfium.PdfDocument(PDF)
    tp = doc[PAGE - 1].get_textpage()
    chars = [(i, chr(raw.FPDFText_GetUnicode(tp.raw, i))) for i in range(tp.count_chars()) if not raw.FPDFText_IsGenerated(tp.raw, i)]
    a, b = [s[0] for s in stream], [c[1] for c in chars]
    to_pdfium, covered = {}, 0
    for block in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
        for k in range(block.size):
            to_pdfium[block.a + k] = block.b + k
        covered += block.size
    print(f"stream {len(a)} characters, PDFium {len(b)} not made up; aligned {covered} ({100.0 * covered / max(1, len(b)):.1f}% of PDFium's)")
    text_b = "".join(b)
    landed = 0
    for k, (ch, fk, code, name) in enumerate(stream):
        if name not in LIGATURES:
            continue
        j = to_pdfium.get(k)
        if j is None:
            print(f"   {name:6s} code {code:#04x}: not paired")
            continue
        landed += b[j] == "f"
        print(f"   {name:6s} code {code:#04x} -> PDFium character {chars[j][0]}: ...{text_b[max(0, j - 14):j]}[{b[j]}]{text_b[j + 1:j + 8]}..."
              f"  reads {LIGATURES[name]!r}")
    print(f"{landed} ligature glyph(s) landed on an f")
    tp.close()
    doc.close()


if __name__ == "__main__":
    main()
