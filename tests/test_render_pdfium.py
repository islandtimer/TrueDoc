"""With PDFium switched on, PDFium must actually draw the page, turned or not (M18, D007, D023).

The renderer falls back to MuPDF whenever PDFium declines or raises, so a page PDFium cannot draw still
converts. The fallback is silent, and that hid a fault for two days: on 10 Sept (commit 905f456) the
renderer's document function was renamed and one call kept the old name, so every PDFium render raised a
NameError, the fallback caught it, and runs 66 to 81 had every page drawn by MuPDF while the switch read
PDFium. Pages turned in memory went to MuPDF by design until run 83. These tests fail if either returns.
"""
import os
import tempfile

import pytest
from PIL import Image

from truedoc.extract import render
from truedoc.extract.handle import open_pdf

pytestmark = pytest.mark.skipif(not render.available(), reason="pypdfium2 not installed")


def _pdf() -> str:
    # a line of text across the middle and a solid block in one corner, so a page drawn the wrong way
    # round cannot pass for the right one
    content = b"BT /F1 24 Tf 40 100 Td (Drawn by PDFium) Tj ET 0 0 0 rg 20 20 80 60 re f"
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 200] "
            b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
            b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
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
    fd, path = tempfile.mkstemp(suffix=".pdf")
    with os.fdopen(fd, "wb") as fh:
        fh.write(bytes(out))
    return path


def _refuse(*args, **kwargs):
    raise AssertionError("the MuPDF fallback was taken")


def _mean_difference(a: Image.Image, b: Image.Image) -> float:
    assert a.size == b.size, (a.size, b.size)
    return sum(abs(x - y) for x, y in zip(a.getdata(), b.getdata())) / (a.size[0] * a.size[1])


def test_pdfium_draws_an_upright_page_itself(monkeypatch):
    monkeypatch.setenv("TRUEDOC_RENDERER", "pdfium")
    path = _pdf()
    pdf = open_pdf(path)
    try:
        img = render._render_pdfium(pdf[0], 2.0, None, False)
        assert img is not None, "PDFium declined an ordinary upright page"
        assert img.size == (600, 400)
        assert min(img.convert("L").getdata()) < 128, "nothing was drawn"
    finally:
        pdf.close()
        render.close_documents()
        os.unlink(path)


def test_an_upright_page_never_reaches_mupdf(monkeypatch):
    """Whole-page and clipped renderings of an upright page, with the MuPDF fallback made to fail."""
    monkeypatch.setenv("TRUEDOC_RENDERER", "pdfium")
    monkeypatch.setattr(render, "_render_mupdf", _refuse)
    path = _pdf()
    pdf = open_pdf(path)
    try:
        page = pdf[0]
        assert render.render_image(page, 1.0).size == (300, 200)
        assert render.render_image(page, 3.0, clip=(40, 80, 140, 110), grey=True).size == (300, 90)
    finally:
        pdf.close()
        render.close_documents()
        os.unlink(path)


def test_a_page_turned_in_memory_is_drawn_by_pdfium_turned_clockwise(monkeypatch):
    """A page that lay on its side is turned in memory (`pipeline._turn_page`), and PDFium draws it turned -
    clockwise, as /Rotate is - instead of handing it to MuPDF. The drawing must match the upright drawing
    turned clockwise, and be far from the same drawing turned the other way."""
    monkeypatch.setenv("TRUEDOC_RENDERER", "pdfium")
    monkeypatch.setattr(render, "_render_mupdf", _refuse)
    path = _pdf()
    pdf = open_pdf(path)
    try:
        upright = render.render_image(pdf[0], 1.0).convert("L")
        page = pdf[0]
        page.set_rotation(90)
        turned = render.render_image(page, 1.0).convert("L")
        assert turned.size == (200, 300)
        right = _mean_difference(turned, upright.transpose(Image.Transpose.ROTATE_270))
        wrong = _mean_difference(turned, upright.transpose(Image.Transpose.ROTATE_90))
        assert right < 5 and wrong > 5 * right, (right, wrong)
        # a clip is in the turned page's own space, as every caller gives it
        assert render.render_image(page, 2.0, clip=(20, 30, 120, 230)).size == (200, 400)
    finally:
        pdf.close()
        render.close_documents()
        os.unlink(path)
