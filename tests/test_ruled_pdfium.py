"""Ruled tables found from our own geometry, with pdfplumber's algorithm (M18, D007, D022).

PyMuPDF's table finder is a port of pdfplumber's and says so in its own source header, so the
algorithm was always MIT - only the copy of it was AGPL. What does *not* work is using pdfplumber
as a library: it reads the page through pdfminer, so "lines_strict" means "the lines my own reader
found", and on one benchmark page PyMuPDF finds two tables where pdfplumber finds none. The
algorithm has to be taken without the reader, and fed the rules and characters TrueDoc already has.

These build a small ruled table by hand and check both halves of that: the grid comes out with the
right shape, and the cell text comes out of TrueDoc's own words rather than a third engine's.
The grid is deliberately not square - two rows by three - because a square one reads the same
transposed and so cannot catch a table built in the wrong space.

The rotated case matters on its own: the rules come out of the file in the page's unrotated
space, and PyMuPDF's finder reports its cells in the rendered one (measured on a 90-degree page),
so the grid is built in the rendered space and the two must agree there, cell for cell.
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
def test_a_turned_page_reads_as_pymupdf_reads_it(rotate):
    """Rows are what a reader sees as rows. The grid is built in the rendered space, as PyMuPDF
    builds it (measured: its first cell on a 90-degree benchmark page holds the word "Table" only
    once the word is turned by the rotation matrix), and the cells are filled from TrueDoc's
    words, which already follow their line's direction. Building in the unrotated space read a
    real 90-degree page as 7 rows by 8 where PyMuPDF reads 8 by 7. The quantity both must agree
    on (D022): the rows, cell for cell."""
    for found, mu in _tables(rotate):
        assert len(found) == len(mu) == 1, (found, mu)
        ours = [[(c or "").strip() for c in r] for r in found[0].extract()]
        theirs = [[(c or "").strip() for c in r] for r in mu[0].extract()]
        assert ours == theirs, (ours, theirs)


def test_small_type_keeps_its_word_spaces_inside_cells():
    """Run 67 read "TypeofTask" and "Week8 Term1" in a 9pt table: pdfplumber's extractor breaks
    words at an absolute 3pt gap, and PDFium supplies fewer synthetic spaces than MuPDF, so a
    2.5pt word gap was not a break. The threshold is now relative to the size."""
    import os
    from truedoc.tables.ruled import find_ruled_tables
    small = _CONTENT.replace(b"/F1 10 Tf", b"/F1 7 Tf").replace(b"(Alpha)", b"(Type of Task)")
    fd, path = tempfile.mkstemp(suffix=".pdf")
    body = _pdf().replace(_CONTENT, small).replace(
        b"/Length " + str(len(_CONTENT)).encode(), b"/Length " + str(len(small)).encode())
    with os.fdopen(fd, "wb") as fh:
        fh.write(body)
    was = os.environ.get("TRUEDOC_OBJECTS")
    os.environ["TRUEDOC_OBJECTS"] = "pdfium"
    doc = pymupdf.open(path)
    try:
        page = extract_page(doc[0], 1)
        blocks = find_ruled_tables(doc[0], page)
        assert blocks and blocks[0].provenance == "pdfium-lines", blocks
        texts = [c.text for c in blocks[0].table.cells]
        assert "Type of Task" in texts, texts
    finally:
        os.environ.pop("TRUEDOC_OBJECTS", None)
        if was is not None:
            os.environ["TRUEDOC_OBJECTS"] = was
        render.close_documents()
        doc.close()
        os.unlink(path)


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


def test_a_table_with_no_left_rule_still_closes_its_left_column():
    """Rules between the rows, a rule down the middle and one down the right, none on the left:
    pdfplumber's cell finder needs a crossing at every corner and closed the right column only,
    4 cells for PyMuPDF's 10 on a benchmark page. The outline of the rules' cluster supplies the
    missing side, as PyMuPDF's port does. The quantity both must agree on (D022): the grid."""
    content = (
        b"0 0 0 RG 1 w\n"
        b"100 700 m 400 700 l S\n100 650 m 400 650 l S\n100 600 m 400 600 l S\n"
        b"250 600 m 250 700 l S\n400 600 m 400 700 l S\n"
        b"BT /F1 10 Tf 110 675 Td (Alpha) Tj ET\nBT /F1 10 Tf 260 675 Td (Beta) Tj ET\n"
        b"BT /F1 10 Tf 110 625 Td (Gamma) Tj ET\nBT /F1 10 Tf 260 625 Td (Delta) Tj ET\n"
    )
    fd, path = tempfile.mkstemp(suffix=".pdf")
    body = _pdf().replace(_CONTENT, content).replace(
        b"/Length " + str(len(_CONTENT)).encode(), b"/Length " + str(len(content)).encode())
    with os.fdopen(fd, "wb") as fh:
        fh.write(body)
    doc = pymupdf.open(path)
    try:
        page = extract_page(doc[0], 1)
        found = ruled_pdfium.find_tables(doc[0], page)
        assert found is not None and len(found) == 1, found
        ours = [[(c or "").strip() for c in r] for r in found[0].extract()]
        assert ours == [["Alpha", "Beta"], ["Gamma", "Delta"]], ours
    finally:
        render.close_documents()
        doc.close()
        os.unlink(path)


_NO_LEFT_RULE_PAGE = os.path.join("bench", "data", "olmocr-bench", "bench_data", "pdfs", "tables",
                                  "3b18f8c75b5f8cae89fa5b0cf094949966d4_pg2_pg1.pdf")


@pytest.mark.skipif(not os.path.exists(_NO_LEFT_RULE_PAGE), reason="benchmark page not present")
def test_the_no_left_rule_benchmark_page_agrees_with_pymupdf():
    """The page the outline rule was measured on. PyMuPDF's finder answers nothing on the
    hand-built grid above (its own reasons - it wants more than rules and text), so the
    agreement is asked for where it can be had: 5 rows by 2 columns, both ways."""
    doc = pymupdf.open(_NO_LEFT_RULE_PAGE)
    try:
        page = extract_page(doc[0], 1)
        found = ruled_pdfium.find_tables(doc[0], page)
        mu = list(doc[0].find_tables(strategy="lines_strict").tables)
        assert found is not None and len(found) == len(mu) == 1, (found, mu)
        assert [len(r) for r in found[0].extract()] == [len(r) for r in mu[0].extract()] == [2] * 5
    finally:
        render.close_documents()
        doc.close()


def test_cell_text_reads_a_visual_row_left_to_right_whatever_the_drawing_order():
    """A raised "**" drawn before its number, on a line of its own to the reader, must follow the
    number as it does on the page: words of one visual row go left to right, rows top to bottom."""
    words = [
        {"line": 0, "order": 0, "text": "**", "x0": 30.0, "x1": 36.0, "top": 0.0, "bottom": 5.0},
        {"line": 1, "order": 0, "text": "0.78", "x0": 10.0, "x1": 28.0, "top": 2.0, "bottom": 10.0},
        {"line": 2, "order": 0, "text": "second", "x0": 10.0, "x1": 40.0, "top": 12.0, "bottom": 20.0},
        {"line": 2, "order": 1, "text": "row", "x0": 42.0, "x1": 56.0, "top": 12.0, "bottom": 20.0},
    ]
    assert ruled_pdfium._cell_text(words, (0.0, 0.0, 60.0, 22.0)) == "0.78 **\nsecond row"


def test_a_table_of_shaded_cells_with_no_drawn_lines_is_found():
    """A table whose cells are filled rectangles with no rule drawn between them (f1774abd, a
    row per shaded band): the boundary where two fills meet is a rule, and PyMuPDF's finder
    takes it as one on that page. A filled rectangle that meets no other - a page background -
    gives none. On this hand-built page PyMuPDF's strict strategy sees nothing and its plain
    "lines" strategy the 2x2; the real page below is where the two must agree."""
    content = (b"0.9 g\n"
               b"100 650 150 50 re f\n250 650 150 50 re f\n"
               b"0.8 g\n"
               b"100 600 150 50 re f\n250 600 150 50 re f\n"
               b"0 g\n"
               b"BT /F1 10 Tf 110 675 Td (Alpha) Tj ET\nBT /F1 10 Tf 260 675 Td (Beta) Tj ET\n"
               b"BT /F1 10 Tf 110 625 Td (Gamma) Tj ET\nBT /F1 10 Tf 260 625 Td (Delta) Tj ET\n")
    fd, path = tempfile.mkstemp(suffix=".pdf")
    body = _pdf().replace(_CONTENT, content).replace(
        b"/Length " + str(len(_CONTENT)).encode(), b"/Length " + str(len(content)).encode())
    with os.fdopen(fd, "wb") as fh:
        fh.write(body)
    doc = pymupdf.open(path)
    try:
        page = extract_page(doc[0], 1)
        found = ruled_pdfium.find_tables(doc[0], page)
        assert found is not None and len(found) == 1, found
        ours = [[(c or "").strip() for c in r] for r in found[0].extract()]
        assert ours == [["Alpha", "Beta"], ["Gamma", "Delta"]], ours
        mu = list(doc[0].find_tables(strategy="lines").tables)
        assert len(mu) == 1 and [[(c or "").strip() for c in r] for r in mu[0].extract()] == ours
    finally:
        render.close_documents()
        doc.close()
        os.unlink(path)


_SHADED_PAGE = os.path.join("bench", "data", "olmocr-bench", "bench_data", "pdfs", "tables",
                            "f1774abde9c6d1cae0f05bb2c6992e9cca85_pg4.pdf")


@pytest.mark.skipif(not os.path.exists(_SHADED_PAGE), reason="benchmark page not present")
def test_the_shaded_benchmark_page_agrees_with_pymupdf():
    """The page the rule was measured on: sixteen shaded cells, no drawn lines, and PyMuPDF's
    strict finder reads 4 rows by 4 from the boundaries between them."""
    doc = pymupdf.open(_SHADED_PAGE)
    try:
        page = extract_page(doc[0], 1)
        found = ruled_pdfium.find_tables(doc[0], page)
        mu = list(doc[0].find_tables(strategy="lines_strict").tables)
        assert found is not None and len(found) == len(mu) == 1, (found, mu)
        assert [len(r) for r in found[0].extract()] == [len(r) for r in mu[0].extract()] == [4] * 4
    finally:
        render.close_documents()
        doc.close()
