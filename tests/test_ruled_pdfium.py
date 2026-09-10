"""Ruled tables found from our own geometry, with pdfplumber's algorithm (M18, D007, D022).

PyMuPDF's table finder is a port of pdfplumber's and says so in its own source header, so the
algorithm was always MIT - only the copy of it was AGPL. What does *not* work is using pdfplumber
as a library: it reads the page through pdfminer, so "lines_strict" means "the lines my own reader
found", and on one benchmark page PyMuPDF finds two tables where pdfplumber finds none. The
algorithm has to be taken without the reader, and fed the rules and characters TrueDoc already has.

These build a small ruled table by hand and check both halves of that: the grid comes out with the
right shape, and the cell text comes out of TrueDoc's own characters rather than a third engine's.
The grid is deliberately not square - two rows by three - because a square one reads the same
transposed and so cannot catch a table built in the wrong space.

The rotated case matters on its own, because the geometry is in the page's unrotated space while
TrueDoc holds its characters rotated, and something has to turn them back.
"""

import os
import tempfile

import pymupdf
import pytest

from truedoc.extract import render
from truedoc.extract.textlayer import extract_page
from truedoc.tables import ruled_pdfium

pytestmark = pytest.mark.skipif(not ruled_pdfium.available(), reason="pdfplumber/pypdfium2 not installed")

# A 2-row, 3-column ruled grid, drawn 600..700 up an 800pt page. Deliberately not square: a
# square grid reads the same transposed, so it cannot catch a table built in the wrong space -
# which is exactly the fault that turned a rotated page into 7 rows by 8 where PyMuPDF read 8 by 7.
_CONTENT = (
    b"0 0 0 RG 1 w\n"
    b"100 700 m 400 700 l S\n100 650 m 400 650 l S\n100 600 m 400 600 l S\n"
    b"100 600 m 100 700 l S\n200 600 m 200 700 l S\n300 600 m 300 700 l S\n400 600 m 400 700 l S\n"
    b"BT /F1 10 Tf 110 675 Td (Alpha) Tj ET\n"
    b"BT /F1 10 Tf 210 675 Td (Beta) Tj ET\n"
    b"BT /F1 10 Tf 310 675 Td (Kappa) Tj ET\n"
    b"BT /F1 10 Tf 110 625 Td (Gamma) Tj ET\n"
    b"BT /F1 10 Tf 210 625 Td (Delta) Tj ET\n"
    b"BT /F1 10 Tf 310 625 Td (Omega) Tj ET\n"
)


def _pdf(rotate: int = 0) -> bytes:
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 400 800] /Rotate " + str(rotate).encode()
        + b" /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(_CONTENT)).encode() + b" >>\nstream\n" + _CONTENT + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
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


def _tables(rotate: int = 0):
    fd, path = tempfile.mkstemp(suffix=".pdf")
    with os.fdopen(fd, "wb") as fh:
        fh.write(_pdf(rotate))
    doc = pymupdf.open(path)
    try:
        pdf_page = doc[0]
        page = extract_page(pdf_page, 1)
        found = ruled_pdfium.find_tables(pdf_page, page)
        mu = list(pdf_page.find_tables(strategy="lines_strict").tables)
        yield found, mu
    finally:
        render.close_documents()
        doc.close()
        os.unlink(path)


def test_a_ruled_grid_is_found_with_the_right_shape():
    for found, _ in _tables():
        assert found is not None and len(found) == 1, found
        rows = found[0].extract()
        assert len(rows) == 2 and all(len(r) == 3 for r in rows), rows


def test_cell_text_comes_from_our_own_characters():
    for found, _ in _tables():
        rows = found[0].extract()
        assert [[(c or "").strip() for c in r] for r in rows] == [["Alpha", "Beta", "Kappa"], ["Gamma", "Delta", "Omega"]], rows


def test_it_agrees_with_pymupdf_about_the_grid():
    """The quantity the two must agree on (D022): how many tables, and of what shape."""
    for found, mu in _tables():
        assert len(found) == len(mu) == 1
        assert [len(r) for r in found[0].extract()] == [len(r) for r in mu[0].extract()]
        for ours, theirs in zip(found[0].rows, mu[0].rows):
            assert len(ours.cells) == len(theirs.cells)


def test_cell_boxes_come_back_for_the_mark_placer():
    """`deal_tall_cells`, `column_spans` and `row_spans` all read `t.rows[].cells`."""
    for found, _ in _tables():
        boxes = [c for row in found[0].rows for c in row.cells]
        assert len(boxes) == 6 and all(b is not None for b in boxes), boxes
        widths = {round(b[2] - b[0]) for b in boxes}
        assert widths == {100}, boxes


@pytest.mark.parametrize("rotate", [90, 180, 270])
def test_a_rotated_page_still_reads_its_cells(rotate):
    """The geometry is unrotated and TrueDoc's characters are not, so they must be turned back;
    without that the cells come out empty while the grid still looks right.

    Note what this does *not* claim. It asserts the grid as built in the page's unrotated space,
    which for a turned page is the transpose of what PyMuPDF reports - PyMuPDF reads a real
    90-degree benchmark page as 8 rows by 7 where this reads 7 by 8. Each cell's text is right;
    which cell it lands in is not, and that is a known gap rather than a settled answer (about a
    third of the tables category's remaining shortfall). Building in the rendered space instead
    was measured and is worse: the glyphs are turned too, so every cell stacks one letter to a
    line."""
    for found, _ in _tables(rotate):
        assert found and len(found) == 1, found
        text = [[(c or "").strip() for c in r] for r in found[0].extract()]
        assert text == [["Alpha", "Beta", "Kappa"], ["Gamma", "Delta", "Omega"]], text


def test_a_page_with_no_rules_yields_no_tables():
    fd, path = tempfile.mkstemp(suffix=".pdf")
    content = b"BT /F1 10 Tf 110 675 Td (nothing ruled here) Tj ET\n"
    body = _pdf().replace(_CONTENT, content).replace(
        b"/Length " + str(len(_CONTENT)).encode(), b"/Length " + str(len(content)).encode())
    with os.fdopen(fd, "wb") as fh:
        fh.write(body)
    doc = pymupdf.open(path)
    try:
        page = extract_page(doc[0], 1)
        assert ruled_pdfium.find_tables(doc[0], page) == []
    finally:
        render.close_documents()
        doc.close()
        os.unlink(path)
