"""PyMuPDF and PDFium must draw the same page (M18, D007, D022).

D022 asks that every stage moved off PyMuPDF be proved against a quantity the two libraries must
agree on because it describes the same thing. For drawing, that quantity is the picture, so these
render the same page both ways and compare it.

The two libraries say "clip" differently - PyMuPDF takes a rectangle, PDFium four insets from the
edges of the bitmap after rotation - and the conversion in `render.py` is what is really under
test here. Rotations are covered explicitly, because the two readings coincide on an upright page
and only a turned one tells them apart.
"""

import os
import tempfile

import numpy as np
import pymupdf
import pytest
from PIL import Image

from truedoc.extract import render

pytestmark = pytest.mark.skipif(not render.available(), reason="pypdfium2 not installed")


def _pdf(rotate: int) -> bytes:
    """A 200x400 page with a black square near one corner, turned by `rotate` degrees."""
    content = b"0 0 0 rg 20 300 40 40 re f\n"
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 400] /Rotate "
        + str(rotate).encode() + b" /Contents 4 0 R >>",
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


def _both(rotate: int, scale: float = 1.0, clip=None, grey: bool = False):
    """The same rendering from each library, as arrays."""
    fd, path = tempfile.mkstemp(suffix=".pdf")
    with os.fdopen(fd, "wb") as fh:
        fh.write(_pdf(rotate))
    doc = pymupdf.open(path)
    was = os.environ.get("TRUEDOC_RENDERER")
    try:
        page = doc[0]
        os.environ["TRUEDOC_RENDERER"] = "mupdf"
        a = np.asarray(render.render_image(page, scale, clip, grey))
        os.environ["TRUEDOC_RENDERER"] = "pdfium"
        render.close_documents()
        b = np.asarray(render.render_image(page, scale, clip, grey))
        return a, b
    finally:
        render.close_documents()
        os.environ.pop("TRUEDOC_RENDERER", None)
        if was is not None:
            os.environ["TRUEDOC_RENDERER"] = was
        doc.close()
        os.unlink(path)


def _ink_box(arr: np.ndarray):
    """Where the black square sits in a rendered image, as (x0, y0, x1, y1) in pixels."""
    dark = arr.min(axis=2) < 128 if arr.ndim == 3 else arr < 128
    ys, xs = np.nonzero(dark)
    assert xs.size, "nothing was drawn"
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


@pytest.mark.parametrize("rotate", [0, 90, 180, 270])
def test_the_whole_page_comes_out_the_same_size_and_shape(rotate):
    a, b = _both(rotate)
    assert abs(a.shape[0] - b.shape[0]) <= 2 and abs(a.shape[1] - b.shape[1]) <= 2, (a.shape, b.shape)
    assert _ink_box(a) == pytest.approx(_ink_box(b), abs=2)


@pytest.mark.parametrize("rotate", [0, 90, 180, 270])
def test_a_clip_lands_on_the_same_part_of_the_page(rotate):
    """The conversion from a rectangle to PDFium's edge insets, which upright pages cannot test."""
    fd, path = tempfile.mkstemp(suffix=".pdf")
    with os.fdopen(fd, "wb") as fh:
        fh.write(_pdf(rotate))
    doc = pymupdf.open(path)
    try:
        page = doc[0]
        full = np.asarray(render.render_image(page, 1.0))
        x0, y0, x1, y1 = _ink_box(full)
        clip = (float(x0) - 3, float(y0) - 3, float(x1) + 4, float(y1) + 4)
    finally:
        doc.close()
        os.unlink(path)
    a, b = _both(rotate, 1.0, clip)
    assert abs(a.shape[0] - b.shape[0]) <= 2 and abs(a.shape[1] - b.shape[1]) <= 2, (a.shape, b.shape)
    # both must have caught the square, not a blank patch somewhere else
    for arr, who in ((a, "mupdf"), (b, "pdfium")):
        dark = (arr.min(axis=2) < 128).mean() if arr.ndim == 3 else (arr < 128).mean()
        assert dark > 0.3, f"{who} clipped to somewhere without the square (rotation {rotate})"


def test_a_clip_reaching_off_the_page_is_clamped_not_refused():
    """PDFium will not take a negative inset; PyMuPDF simply intersects with the page."""
    a, b = _both(0, 1.0, (-50.0, -50.0, 120.0, 120.0))
    assert a.size and b.size
    assert abs(a.shape[0] - b.shape[0]) <= 2 and abs(a.shape[1] - b.shape[1]) <= 2, (a.shape, b.shape)


def test_grey_rendering_agrees_too():
    a, b = _both(0, 1.0, None, True)
    assert a.ndim == b.ndim == 2
    assert _ink_box(a) == pytest.approx(_ink_box(b), abs=2)


def test_a_scaled_rendering_agrees():
    a, b = _both(90, 2.0)
    assert abs(a.shape[0] - b.shape[0]) <= 2 and abs(a.shape[1] - b.shape[1]) <= 2, (a.shape, b.shape)
    assert _ink_box(a) == pytest.approx(_ink_box(b), abs=3)


def test_the_renderer_is_on_unless_asked_off():
    """The default since run 71 (D023); `TRUEDOC_RENDERER=mupdf` draws with MuPDF instead."""
    was = os.environ.pop("TRUEDOC_RENDERER", None)
    try:
        assert render.enabled()
        os.environ["TRUEDOC_RENDERER"] = "pdfium"
        assert render.enabled()
        os.environ["TRUEDOC_RENDERER"] = "mupdf"
        assert not render.enabled()
    finally:
        os.environ.pop("TRUEDOC_RENDERER", None)
        if was is not None:
            os.environ["TRUEDOC_RENDERER"] = was
