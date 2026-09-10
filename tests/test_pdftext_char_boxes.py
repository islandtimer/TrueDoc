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


def _pdf() -> bytes:
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 200] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(_CONTENT)).encode() + b" >>\nstream\n" + _CONTENT + b"\nendstream",
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
