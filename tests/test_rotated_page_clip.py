"""Clipping a rotated page photographs the part of it you asked for (D022).

Two stages look at pixels rather than text: `_renders_uniform` in `extract/textlayer.py`, which
asks whether an area of the page is blank for the hidden-text rules of D011, and `_ink` in
`marks.py`, which reads a tick or a cross. Both were given a box in the rendered page's own space,
turned it back into the page's unrotated space, and clipped with that - but `get_pixmap` clips in
the *rendered* space, so on a rotated page both photographed the wrong patch. Upright pages were
unaffected, which is why it went unseen: the turn is a no-op when a page is not rotated.

The test states the invariant directly and needs no ground truth: wherever ink shows up in a full
render of the page, clipping to that same box must find ink there too.
"""

import os
import tempfile

import pymupdf
import pytest

from truedoc.extract.textlayer import _renders_uniform
from truedoc.extract import render
from truedoc.model import BBox


def _rotated_pdf(rotate: int) -> bytes:
    """A tall page carrying one black square near its top-left, turned by `rotate` degrees."""
    content = b"0 0 0 rg 20 300 40 40 re f\n"      # a filled square, in PDF units from the bottom
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


def _page(rotate: int):
    fd, path = tempfile.mkstemp(suffix=".pdf")
    with os.fdopen(fd, "wb") as fh:
        fh.write(_rotated_pdf(rotate))
    doc = pymupdf.open(path)
    return doc, doc[0], path


def _ink_box_from_render(page) -> BBox:
    """Where the square actually appears, read off a full render - the rendered page's own space."""
    pix = page.get_pixmap(alpha=False, colorspace=pymupdf.csGRAY)
    w, h, s = pix.width, pix.height, pix.samples
    xs = [x for y in range(h) for x in range(w) if s[y * w + x] < 128]
    ys = [y for y in range(h) for x in range(w) if s[y * w + x] < 128]
    assert xs and ys, "the test PDF drew nothing"
    sx, sy = page.rect.width / w, page.rect.height / h
    return BBox(min(xs) * sx, min(ys) * sy, (max(xs) + 1) * sx, (max(ys) + 1) * sy)


@pytest.mark.parametrize("rotate", [0, 90, 180, 270])
def test_clipping_finds_the_ink_where_the_render_shows_it(rotate):
    doc, page, path = _page(rotate)
    try:
        box = _ink_box_from_render(page)
        M = page.rotation_matrix if page.rotation else None
        assert _renders_uniform(page, box, M) is False, (
            f"rotation {rotate}: the square is visible at {box} in the render, "
            "so clipping there must not report a blank area")
    finally:
        doc.close()
        render.close_documents()   # PDFium holds the file open until it is let go
        os.unlink(path)


@pytest.mark.parametrize("rotate", [0, 90, 180, 270])
def test_an_empty_corner_still_reads_as_blank(rotate):
    """The other half of the invariant: the fix must not make everything look inked."""
    doc, page, path = _page(rotate)
    try:
        ink = _ink_box_from_render(page)
        r = page.rect
        # a strip along the far edge from the square, in the rendered page's space
        empty = (BBox(r.x0, r.y1 - 20, r.x1, r.y1) if ink.y0 < r.height / 2
                 else BBox(r.x0, r.y0, r.x1, r.y0 + 20))
        M = page.rotation_matrix if page.rotation else None
        assert _renders_uniform(page, empty, M) is True, f"rotation {rotate}: {empty} should be blank"
    finally:
        doc.close()
        render.close_documents()   # PDFium holds the file open until it is let go
        os.unlink(path)
