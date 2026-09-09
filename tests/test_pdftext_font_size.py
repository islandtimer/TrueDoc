"""The font size PDFium reports is not the size on the page (M18, D022).

PDFium hands back a font's *nominal* size - the number after `Tf` - and a PDF is free to scale
it by the text matrix afterwards. PyMuPDF folds the two together; PDFium does not. The reader
swap took the nominal size at face value, so on one benchmark page every character came back as
size 1.0 where the text is 8pt, and on another the body size computed to 35.0 where it is 5.9.
Nothing crashed: the pages simply lost every paragraph, because a stage that cannot tell a
heading from body text groups nothing.

These build the offending PDF by hand rather than lean on a benchmark file, so the case is
pinned whatever the corpus does.
"""

import os
import tempfile

import pytest

from truedoc.extract import pdftext_rawdict as A

pytestmark = pytest.mark.skipif(not A.available(), reason="pdftext/pypdfium2 not installed")


def _pdf(nominal: float, scale: float) -> bytes:
    """A one-page PDF drawing "Hi" at `nominal` points, scaled by `scale` in the text matrix."""
    content = (f"BT /F1 {nominal:g} Tf {scale:g} 0 0 {scale:g} 20 100 Tm (Hi) Tj ET").encode()
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream",
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


def _sizes(nominal: float, scale: float) -> list[float]:
    fd, path = tempfile.mkstemp(suffix=".pdf")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(_pdf(nominal, scale))
        raw = A.build(path, 1)
        assert raw is not None, "the hand-built PDF did not parse"
        return [sp["size"] for b in raw["blocks"] for ln in b["lines"] for sp in ln["spans"]]
    finally:
        os.unlink(path)


def test_text_scaled_by_the_matrix_reports_the_size_it_is_drawn_at():
    """The real defect: /F1 1 Tf with an 8x matrix is 8pt text, not 1pt text."""
    sizes = _sizes(nominal=1.0, scale=8.0)
    assert sizes, "no spans came back"
    assert all(abs(s - 8.0) < 0.1 for s in sizes), sizes


def test_the_same_holds_when_the_scaling_shrinks_the_text():
    """The other direction, which is how a small-print page reported 35pt for 5.9pt text."""
    sizes = _sizes(nominal=36.0, scale=0.25)
    assert sizes and all(abs(s - 9.0) < 0.1 for s in sizes), sizes


def test_unscaled_text_is_unaffected():
    sizes = _sizes(nominal=12.0, scale=1.0)
    assert sizes and all(abs(s - 12.0) < 0.1 for s in sizes), sizes
