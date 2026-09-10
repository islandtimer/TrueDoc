"""A character's box is its advance box, whichever library reads it (M18, D022).

The word builder decides a break from the gap between one character's right edge and the next's
left: above `max(0.13 x size, 0.9pt)` is a word space. MuPDF's right edge is the glyph's *advance*.
PDFium's "loose" box is not quite - on a glyph whose ink overhangs its advance, the letter f above
all, it runs further right. On a 7pt line that was 0.44pt: MuPDF read a gap of 1.31pt and broke
the word, PDFium read 0.87 and did not, and "of the" came out "ofthe". Run 66 lost small-type
checks to it, and the size fix that preceded it was necessary and not sufficient.

PDFium exposes the advance (`FPDFFont_GetGlyphWidth`), so the right edge is origin plus advance
and the box is MuPDF's by construction. Times has an overhanging f, and it is one of the fonts
every reader carries, so the case can be pinned without embedding anything.
"""

import os
import tempfile

import pymupdf
import pytest

from truedoc.extract import pdftext_rawdict as A
from truedoc.extract import render

pytestmark = pytest.mark.skipif(not A.available(), reason="pdftext/pypdfium2 not installed")

# "\256" is the fi ligature in StandardEncoding, so "\256xtures" draws one glyph for "fi" - the
# case where taking a lone f's advance opens a gap inside the word.
_CONTENT = b"BT /F1 7 Tf 20 100 Td (one of the finest offers and \\256xtures) Tj ET\n"


def _pdf(content: bytes = _CONTENT) -> bytes:
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 200] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Times-Roman >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objs, start=1):
        offsets.append(len(out))
        out += str(i).encode() + b" 0 obj\n" + body + b"\nendobj\n"
    start = len(out)
    out += b"xref\n0 " + str(len(objs) + 1).encode() + b"\n0000000000 65535 f \n"
    for off in offsets:
        out += ("%010d 00000 n \n" % off).encode()
    out += (b"trailer\n<< /Size " + str(len(objs) + 1).encode() + b" /Root 1 0 R >>\n"
            b"startxref\n" + str(start).encode() + b"\n%%EOF\n")
    return bytes(out)


def _boxes() -> tuple[list, list]:
    """(PDFium chars, MuPDF chars) as (text, x0, x1), non-space, in reading order."""
    fd, path = tempfile.mkstemp(suffix=".pdf")
    with os.fdopen(fd, "wb") as fh:
        fh.write(_pdf())
    try:
        raw = A.build(path, 1)
        assert raw is not None
        pf = [(c["c"], c["bbox"][0], c["bbox"][2]) for b in raw["blocks"] for ln in b["lines"]
              for sp in ln["spans"] for c in sp["chars"] if not c["c"].isspace()]
        doc = pymupdf.open(path)
        try:
            flags = pymupdf.TEXTFLAGS_RAWDICT & ~pymupdf.TEXT_PRESERVE_LIGATURES | pymupdf.TEXT_MEDIABOX_CLIP
            mu = [(c["c"], c["bbox"][0], c["bbox"][2]) for blk in doc[0].get_text("rawdict", flags=flags)["blocks"]
                  if blk.get("type") == 0 for ln in blk["lines"] for sp in ln["spans"] for c in sp["chars"]
                  if not c["c"].isspace()]
        finally:
            doc.close()
        return pf, mu
    finally:
        render.close_documents()
        os.unlink(path)


def test_the_readers_agree_on_every_right_edge_including_the_overhanging_f():
    pf, mu = _boxes()
    assert [c for c, _, _ in pf] == [c for c, _, _ in mu], "the two readers should see the same text"
    worst = max(abs(a[2] - b[2]) for a, b in zip(pf, mu))
    fs = [(a[2], b[2]) for a, b in zip(pf, mu) if a[0] == "f"]
    assert fs, "the sample has no f"
    assert worst < 0.05, f"right edges differ by up to {worst:.3f}pt; f: {fs}"


def test_the_readers_agree_on_every_left_edge():
    pf, mu = _boxes()
    worst = max(abs(a[1] - b[1]) for a, b in zip(pf, mu))
    assert worst < 0.05, f"left edges differ by up to {worst:.3f}pt"


def test_a_characters_box_is_the_fonts_ascent_and_descent():
    """MuPDF boxes every character from the baseline by the font's ascender and descender;
    PDFium's loose box uses something smaller above the baseline - 1.4pt lower on 8pt Arial -
    and by an amount that varies with the glyphs, so a table's header line and the "Item"
    label centred over it changed rows in the rebuild and two columns fused (fa18a15c).
    `FPDFFont_GetAscent` and `GetDescent` are the metrics MuPDF uses; the box is built from
    them, level text only. On a hand-built page the two libraries substitute different faces
    for a font that is not embedded (0.891 against 1.053 em of ascent for Times), so what is
    pinned here is the construction: one top and one bottom for every character of a size,
    at the font's ascent and descent. The embedded-font page below pins the agreement."""
    import ctypes

    import pypdfium2 as pdfium
    import pypdfium2.raw as raw_api
    content = b"BT /F1 8 Tf 1 0 0 1 20 100 Tm (Item) Tj ET\nBT /F1 8 Tf 1 0 0 1 60 105 Tm (Aug 21,) Tj ET\nBT /F1 12 Tf 1 0 0 1 20 60 Tm (Big) Tj ET"
    fd, path = tempfile.mkstemp(suffix=".pdf")
    with os.fdopen(fd, "wb") as fh:
        fh.write(_pdf(content))
    try:
        doc = pdfium.PdfDocument(path)
        try:
            page = doc[0]
            tp = page.get_textpage()
            font = raw_api.FPDFTextObj_GetFont(raw_api.FPDFText_GetTextObject(tp.raw, 0))
            asc, desc = ctypes.c_float(), ctypes.c_float()
            assert raw_api.FPDFFont_GetAscent(font, 8.0, asc) and raw_api.FPDFFont_GetDescent(font, 8.0, desc)
            ascent8, descent8 = asc.value, desc.value
            tp.close()
            page.close()
        finally:
            doc.close()
        raw = A.build(path, 1)
        assert raw is not None
        by_size: dict[float, set] = {}
        for b in raw["blocks"]:
            for ln in b["lines"]:
                for sp in ln["spans"]:
                    for c in sp["chars"]:
                        if not c["c"].isspace():
                            by_size.setdefault(round(sp["size"]), set()).add((round(c["bbox"][1] - c["origin"][1], 2), round(c["bbox"][3] - c["origin"][1], 2)))
        assert len(by_size[8]) == 1 and len(by_size[12]) == 1, by_size      # one box per size, whatever the glyph
        (top8, bottom8), = by_size[8]
        assert abs(top8 + ascent8) < 0.05 and abs(bottom8 + descent8) < 0.05, (top8, bottom8, ascent8, descent8)
        (top12, bottom12), = by_size[12]
        assert abs(top12 - 1.5 * top8) < 0.05 and abs(bottom12 - 1.5 * bottom8) < 0.05, (top8, top12)
    finally:
        os.unlink(path)


_ARIAL_PAGE = os.path.join("bench", "data", "olmocr-bench", "bench_data", "pdfs", "tables",
                           "fa18a15c1dbbfcb71b1f1ea1b8f116e24b8a_pg2_pg1.pdf")


@pytest.mark.skipif(not os.path.exists(_ARIAL_PAGE), reason="benchmark page not present")
def test_an_embedded_fonts_boxes_agree_with_mupdf_to_the_hundredth():
    """The page it was measured on (Arial embedded): every level character's top and bottom
    within a twentieth of a point of MuPDF's."""
    raw = A.build(_ARIAL_PAGE, 1)
    assert raw is not None
    ours = {}
    for b in raw["blocks"]:
        for ln in b["lines"]:
            if ln["dir"] != (1.0, 0.0):
                continue
            for sp in ln["spans"]:
                for c in sp["chars"]:
                    if not c["c"].isspace() and c.get("origin"):
                        ours[(c["c"], round(c["origin"][0], 1), round(c["origin"][1], 1))] = (c["bbox"][1], c["bbox"][3])
    doc = pymupdf.open(_ARIAL_PAGE)
    try:
        theirs = {}
        for b in doc[0].get_text("rawdict")["blocks"]:
            for ln in b.get("lines", []):
                if tuple(ln["dir"]) != (1.0, 0.0):
                    continue
                for sp in ln["spans"]:
                    for c in sp["chars"]:
                        if not c["c"].isspace():
                            theirs[(c["c"], round(c["origin"][0], 1), round(c["origin"][1], 1))] = (c["bbox"][1], c["bbox"][3])
    finally:
        doc.close()
    matched = [(ours[k], theirs[k]) for k in ours if k in theirs]
    assert len(matched) > 500, len(matched)
    off = [k for k in ours if k in theirs and (abs(ours[k][0] - theirs[k][0]) > 0.05 or abs(ours[k][1] - theirs[k][1]) > 0.05)]
    assert len(off) <= 0.01 * len(matched), (len(off), len(matched), off[:5])
