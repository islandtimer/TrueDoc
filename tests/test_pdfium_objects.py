"""What is drawn on a page, read through PDFium instead of PyMuPDF (M18, D007, D022).

The rulings, the picture regions, the shapes the mark reader hunts for and the covers that hide
text all come from one question - what is on this page - which MuPDF answers through three
different views. D022 asks that the replacement be proved against a quantity the two libraries must
agree on, so these build a page with known shapes on it and check both that PDFium finds what was
drawn and that it agrees with PyMuPDF about where.

Measured over 60 benchmark pages when this was written: image boxes agree 122 of 122, and the
per-page path match rate has a median of 1.000, a tenth percentile of 1.000, and 20 of 22 pages at
or above 0.95. The two that disagree are dense vector artwork, where MuPDF splits a compound path
into its subpaths and PDFium keeps it whole - a difference in what counts as one drawing, not in
where anything is. On the benchmark's quick gate the two readers score the same, 100 of 128.
"""

import os
import tempfile

import pymupdf
import pytest

from truedoc.extract import render
from truedoc.extract.pdfium_objects import available, page_objects

pytestmark = pytest.mark.skipif(not available(), reason="pypdfium2 not installed")

# A stroked line, a filled blue rectangle, a 2x2 grey image, and a form holding a green square.
_CONTENT = (b"1 0 0 RG 2 w 20 700 m 180 700 l S\n"
            b"0 0 1 rg 30 100 60 40 re f\n"
            b"q 50 0 0 50 100 300 cm /Im0 Do Q\n"
            b"/Fm0 Do\n")
_FORM = b"0 1 0 rg 10 500 20 20 re f\n"


def _pdf() -> bytes:
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 800] /Resources << /XObject "
        b"<< /Im0 5 0 R /Fm0 6 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(_CONTENT)).encode() + b" >>\nstream\n" + _CONTENT + b"\nendstream",
        b"<< /Type /XObject /Subtype /Image /Width 2 /Height 2 /ColorSpace /DeviceGray "
        b"/BitsPerComponent 8 /Length 4 >>\nstream\n" + bytes([0, 90, 180, 255]) + b"\nendstream",
        b"<< /Type /XObject /Subtype /Form /BBox [0 0 200 800] /Length "
        + str(len(_FORM)).encode() + b" >>\nstream\n" + _FORM + b"\nendstream",
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


@pytest.fixture()
def drawn():
    fd, path = tempfile.mkstemp(suffix=".pdf")
    with os.fdopen(fd, "wb") as fh:
        fh.write(_pdf())
    try:
        objs = page_objects(path, 1)
        assert objs is not None, "the hand-built PDF did not parse"
        yield path, objs
    finally:
        render.close_documents()
        os.unlink(path)


def test_every_kind_of_thing_on_the_page_is_found(drawn):
    _, objs = drawn
    kinds = [o.kind for o in objs]
    assert kinds.count("image") == 1, kinds
    # the stroked line, the blue rectangle, and the green square inside the form
    assert kinds.count("path") == 3, kinds


def test_a_form_is_flattened_rather_than_reported_as_one_lump(drawn):
    """MuPDF reports the shapes inside a form as if drawn on the page; PDFium nests them."""
    _, objs = drawn
    assert not any(o.kind == "form" for o in objs)
    greens = [o for o in objs if o.fill and o.fill[1] > 0.9 and o.fill[0] < 0.1]
    assert len(greens) == 1, [o.fill for o in objs]
    # drawn at y 500..520 from the bottom of an 800pt page, so 280..300 from the top
    assert greens[0].bbox[1] == pytest.approx(280.0, abs=1.0)
    assert greens[0].bbox[3] == pytest.approx(300.0, abs=1.0)


def test_coordinates_are_measured_down_from_the_top_like_pymupdf(drawn):
    """PDFium measures up from the bottom left; everything downstream expects MuPDF's convention.

    The two do not report an identical box for a *stroked* path and are not expected to: PyMuPDF
    gives the path itself, PDFium the ink it lays down, which is wider by the stroke on every side.
    So the invariant is containment with a bounded slack, not equality - a zero-height rule at
    y=100 drawn 2pt wide is `(20, 100, 180, 100)` to one and `(18, 98, 182, 102)` to the other, and
    both are right.
    """
    path, objs = drawn
    doc = pymupdf.open(path)
    try:
        mu = [tuple(float(v) for v in d["rect"]) for d in doc[0].get_drawings()]
    finally:
        doc.close()
    paths = [o for o in objs if o.kind == "path"]
    for box in mu:
        assert any(
            o.bbox[0] <= box[0] + 0.5 and o.bbox[1] <= box[1] + 0.5
            and o.bbox[2] >= box[2] - 0.5 and o.bbox[3] >= box[3] - 0.5
            and all(abs(p - q) <= max(1.0, o.stroke_width) + 0.5 for p, q in zip(box, o.bbox))
            for o in paths), (
            f"PyMuPDF drew something at {box} that PDFium did not report in the same place")


def test_fill_colour_and_stroke_width_come_back(drawn):
    _, objs = drawn
    blues = [o for o in objs if o.fill and o.fill[2] > 0.9 and o.fill[0] < 0.1]
    assert len(blues) == 1, [o.fill for o in objs]
    strokes = [o for o in objs if o.stroke is not None]
    assert len(strokes) == 1 and strokes[0].stroke_width == pytest.approx(2.0, abs=0.01)


def test_a_filled_rectangle_is_reported_as_a_rectangle_not_just_a_bounding_box(drawn):
    """`_Visibility` needs the rectangles a path fills: a box border drawn as a filled path spans
    the whole box while painting only its edges, so its bounds would hide text plainly visible."""
    _, objs = drawn
    blue = next(o for o in objs if o.fill and o.fill[2] > 0.9 and o.fill[0] < 0.1)
    assert len(blue.rects) == 1, blue.rects
    x0, y0, x1, y1 = blue.rects[0]
    assert (x1 - x0) == pytest.approx(60.0, abs=1.0)
    assert (y1 - y0) == pytest.approx(40.0, abs=1.0)


def test_things_come_back_in_the_order_they_were_painted(drawn):
    _, objs = drawn
    assert [o.order for o in objs] == sorted(o.order for o in objs)
    assert objs[0].stroke is not None, "the stroked line is drawn first"


def test_the_object_reader_is_on_unless_asked_off():
    """The default since run 71 (D023); `TRUEDOC_OBJECTS=mupdf` reads drawings the old way."""
    from truedoc.extract import pdfium_objects
    was = os.environ.pop("TRUEDOC_OBJECTS", None)
    try:
        assert pdfium_objects.enabled()
        os.environ["TRUEDOC_OBJECTS"] = "pdfium"
        assert pdfium_objects.enabled()
        os.environ["TRUEDOC_OBJECTS"] = "mupdf"
        assert not pdfium_objects.enabled()
    finally:
        os.environ.pop("TRUEDOC_OBJECTS", None)
        if was is not None:
            os.environ["TRUEDOC_OBJECTS"] = was


def test_a_stroked_path_hands_back_its_own_segments_not_its_inflated_bounds(drawn):
    """PDFium's bounds inflate a stroked path by its line width on every side, so a 3pt rule
    reads as a 6pt-high box and fails a thin test (f1774abd lost the rule under its header,
    and its table a row). The straight segments the path actually draws come back as well,
    measured in the page's space, which is what PyMuPDF's table finder reads (D022)."""
    _, objs = drawn
    stroke = next(o for o in objs if o.stroke is not None)
    assert len(stroke.lines) == 1, stroke.lines
    x0, y0, x1, y1 = stroke.lines[0]
    assert (x0, x1) == pytest.approx((20.0, 180.0), abs=0.01)
    assert y0 == pytest.approx(100.0, abs=0.01) and y1 == pytest.approx(100.0, abs=0.01)
    bx0, by0, bx1, by1 = stroke.bbox
    assert bx0 < 20.0 and bx1 > 180.0 and by0 < 100.0 < by1, stroke.bbox
