"""TrueDoc's PDF handle reads a page's size and turn exactly as PyMuPDF did (M18, D007, D022).

The product opens PDFs through PDFium now. A page handle carries the size the page is drawn at, its
rotation, and the matrix that turns the readers' unrotated coordinates into drawn ones. Get the
matrix wrong and nothing crashes: on a turned page every box lands off the part of the page it came
from. PyMuPDF builds that matrix from the /CropBox as written - not from the drawn page, which is the
crop box cut to the media box - and the handle does the same, so no coordinate moves.
"""
import os
import tempfile

import pytest

from truedoc.extract.handle import open_pdf

# Page 1 inherits its boxes and a quarter turn from the page tree; page 2 has its own boxes; page 3
# writes a crop box that reaches past its media box (a journal page in the benchmark, b2ca8e00, does:
# an A4 crop box around a 430 by 660 media box).
_PAGES = (
    b"<< /Type /Pages /Kids [3 0 R 4 0 R 5 0 R] /Count 3 /MediaBox [0 0 600 800] "
    b"/CropBox [10 20 500 700] /Rotate 90 >>",
    b"<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 7 0 R >> >> /Contents 6 0 R >>",
    b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 400 300] /CropBox [5 5 395 290] /Rotate 0 "
    b"/Resources << /Font << /F1 7 0 R >> >> /Contents 6 0 R >>",
    b"<< /Type /Page /Parent 2 0 R /MediaBox [82.5 90 512.5 750] /CropBox [0 0 595.276 841.89] "
    b"/Rotate 0 /Resources << /Font << /F1 7 0 R >> >> /Contents 6 0 R >>",
)


def _pdf() -> str:
    content = b"BT /F1 12 Tf 100 200 Td (Hello) Tj ET"
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>", *_PAGES,
            b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
            b"<< /Title (Policy wording) >>"]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objs, start=1):
        offsets.append(len(out))
        out += str(i).encode() + b" 0 obj\n" + body + b"\nendobj\n"
    start = len(out)
    out += b"xref\n0 " + str(len(objs) + 1).encode() + b"\n0000000000 65535 f \n"
    for off in offsets:
        out += ("%010d 00000 n \n" % off).encode()
    out += (b"trailer\n<< /Size " + str(len(objs) + 1).encode() + b" /Root 1 0 R /Info 8 0 R >>\n"
            b"startxref\n" + str(start).encode() + b"\n%%EOF\n")
    fd, path = tempfile.mkstemp(suffix=".pdf")
    with os.fdopen(fd, "wb") as fh:
        fh.write(bytes(out))
    return path


def test_size_rotation_and_matrix_are_pymupdfs_at_every_turn():
    pymupdf = pytest.importorskip("pymupdf")
    path = _pdf()
    mu, pdf = pymupdf.open(path), open_pdf(path)
    try:
        assert len(pdf) == len(mu) == 3
        for i in range(3):
            m, p = mu[i], pdf[i]
            for turn in (None, 0, 90, 180, 270):
                if turn is not None:
                    m.set_rotation(turn)
                    p.set_rotation(turn)
                assert p.rotation == m.rotation, (i, turn)
                assert tuple(p.rect) == tuple(m.rect), (i, turn)
                assert tuple(p.rotation_matrix) == tuple(m.rotation_matrix), (i, turn)
        assert pdf.metadata.get("title") == mu.metadata.get("title") == "Policy wording"
    finally:
        mu.close()
        pdf.close()
        os.unlink(path)


def test_the_turn_is_the_handles_own_and_the_file_keeps_its_own():
    """A quarter turn swaps the drawn size; the file, opened again, is still as it was."""
    path = _pdf()
    pdf = open_pdf(path)
    try:
        page = pdf[1]
        assert (page.rotation, tuple(page.rect)) == (0, (0.0, 0.0, 390.0, 285.0))
        page.set_rotation(90)
        assert (page.rotation, tuple(page.rect)) == (90, (0.0, 0.0, 285.0, 390.0))
        assert tuple(page.rotation_matrix) == (0.0, 1.0, -1.0, 0.0, 285.0, 0.0)
        assert pdf[1].rotation == 0
    finally:
        pdf.close()
        os.unlink(path)


def test_the_old_readers_calls_see_the_page_turned_the_same_way():
    """Anything else asked of a page is the old reader's and goes to PyMuPDF's copy, turned to match -
    whether the turn came before that copy was opened or after."""
    pytest.importorskip("pymupdf")
    path = _pdf()
    pdf = open_pdf(path)
    try:
        page = pdf[1]
        page.set_rotation(90)
        assert tuple(page.bound()) == tuple(page.rect)
        page.set_rotation(180)
        assert tuple(page.bound()) == tuple(page.rect)
        assert "Hello" in page.get_text("text")
    finally:
        pdf.close()
        os.unlink(path)


def test_a_page_reads_the_same_through_either_handle_at_every_turn():
    """The whole reading of a page through PDFium's handle must equal the reading through PyMuPDF's page,
    as filed and at every turn. Stage C first failed this silently: the text layer turned character
    origins with PyMuPDF's Point, which takes TrueDoc's matrix for the identity."""
    pymupdf = pytest.importorskip("pymupdf")
    from truedoc.extract import render
    from truedoc.extract.textlayer import extract_page

    def reading(page, number):
        p = extract_page(page, number)
        return ([(c.text, c.bbox.x0, c.bbox.y0, c.bbox.x1, c.bbox.y1, c.origin_y) for c in p.chars],
                [w.text for w in p.words], (p.width, p.height, p.rotation), p.quality.kind)

    path = _pdf()
    mu, pdf = pymupdf.open(path), open_pdf(path)
    try:
        for i in range(3):
            for turn in (None, 90, 180, 270):
                m, p = mu[i], pdf[i]
                if turn is not None:
                    m.set_rotation(turn)
                    p.set_rotation(turn)
                assert reading(p, i + 1) == reading(m, i + 1), (i, turn)
    finally:
        render.close_documents()
        mu.close()
        pdf.close()
        os.unlink(path)
