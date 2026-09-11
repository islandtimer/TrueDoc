"""A Type 3 font through the PDFium reader (M18, D022).

Scanned-era papers set their whole text in Type 3 bitmap fonts. MuPDF reports each such
character in a box of the font's height - the same for an E and an x - and its size as the
matrix scale (0.12), from which the text layer takes 0.8 of the box as the size (8pt). PDFium
reports each glyph in its own box, so an x stands 6.5pt tall and an E 9.7, and the same rule
then made the body text 3.7pt: every line of a two-column abstract was spaced two and a half of
its own sizes from the next and stood as a paragraph of its own (09f90a8f).

The font is built by hand here: two glyphs drawn as rectangles of different heights.
"""

import os
import tempfile

import pytest

from truedoc.extract import pdftext_rawdict as A

pytestmark = pytest.mark.skipif(not A.available(), reason="pdftext/pypdfium2 not installed")


def _stream(body: bytes) -> bytes:
    return b"<< /Length " + str(len(body)).encode() + b" >>\nstream\n" + body + b"\nendstream"


def _type3_pdf() -> bytes:
    """One page, one Type 3 font with E (700 units tall) and x (450 units tall), "ExEx" at 10pt."""
    widths = [0] * (120 - 69 + 1)
    widths[0] = 600          # E
    widths[-1] = 500         # x
    font = (b"<< /Type /Font /Subtype /Type3 /FontBBox [0 0 600 750] /FontMatrix [0.001 0 0 0.001 0 0] "
            b"/CharProcs 6 0 R /Encoding << /Type /Encoding /Differences [69 /E 120 /x] >> "
            b"/FirstChar 69 /LastChar 120 /Widths [" + " ".join(str(w) for w in widths).encode() + b"] "
            b"/Resources << >> >>")
    content = b"BT /F1 10 Tf 20 100 Td (ExEx) Tj ET"
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 200] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        font,
        _stream(content),
        b"<< /E 7 0 R /x 8 0 R >>",
        _stream(b"600 0 d0 0 0 500 700 re f"),
        _stream(b"500 0 d0 0 0 400 450 re f"),
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


def _with_pdf():
    fd, path = tempfile.mkstemp(suffix=".pdf")
    with os.fdopen(fd, "wb") as fh:
        fh.write(_type3_pdf())
    return path


def test_type3_characters_share_the_fonts_box_on_a_line():
    """The E and the x get one box height, the tallest glyph's, as MuPDF gives them one."""
    path = _with_pdf()
    try:
        raw = A.build(path, 1)
        assert raw is not None
        chars = [c for b in raw["blocks"] for ln in b["lines"] for sp in ln["spans"] for c in sp["chars"] if not c["c"].isspace()]
        assert [c["c"] for c in chars] == ["E", "x", "E", "x"], chars
        heights = {round(c["bbox"][3] - c["bbox"][1], 2) for c in chars}
        assert len(heights) == 1, heights
        # at least the E (700 units at 10pt), at most the font's declared box (750): PDFium uses
        # the declared box where the font has a sound one, and the glyph's own where it has not
        assert 6.9 <= next(iter(heights)) <= 7.6, heights
    finally:
        os.unlink(path)


def test_the_text_layer_sizes_type3_text_alike_under_both_readers():
    """The quantity that decides the body size and the line spacing: what `extract_page` calls
    the size of each character. MuPDF's box is the font's 750-unit bbox, PDFium's the tallest
    glyph's 700 - within a tenth of each other, where it was a factor of two."""
    import pymupdf
    from truedoc.extract import render
    from truedoc.extract.textlayer import extract_page
    path = _with_pdf()
    try:
        sizes = {}
        for reader in ("mupdf", "pdfium"):
            for k in ("TRUEDOC_READER", "TRUEDOC_RENDERER", "TRUEDOC_OBJECTS"):
                os.environ.pop(k, None)
            if reader == "pdfium":
                os.environ.update({"TRUEDOC_READER": "pdftext", "TRUEDOC_RENDERER": "pdfium", "TRUEDOC_OBJECTS": "pdfium"})
            doc = pymupdf.open(path)
            try:
                page = extract_page(doc[0], 1)
                sizes[reader] = sorted({round(c.size, 1) for c in page.chars if not c.text.isspace()})
            finally:
                render.close_documents()
                doc.close()
        for k in ("TRUEDOC_READER", "TRUEDOC_RENDERER", "TRUEDOC_OBJECTS"):
            os.environ.pop(k, None)
        assert len(sizes["pdfium"]) == 1 and len(sizes["mupdf"]) == 1, sizes
        assert abs(sizes["pdfium"][0] - sizes["mupdf"][0]) <= 0.1 * sizes["mupdf"][0], sizes
    finally:
        os.unlink(path)


_TEX_TYPE3_PAGE = os.path.join("bench", "data", "olmocr-bench", "bench_data", "pdfs", "multi_column",
                               "09f90a8fad0997f7cf454cbcbe79cab3bc0f_page_7_pg1.pdf")


@pytest.mark.skipif(not os.path.exists(_TEX_TYPE3_PAGE), reason="benchmark page not present")
def test_a_tex_page_in_unnamed_type3_fonts_keeps_its_words_whole():
    """Seven Type 3 fonts with no /BaseFont: the /Widths advance rule for unmapped glyphs took the
    first font's table for every glyph and, with the drawn size PDFium reports for Type 3 text
    (0.12), boxed every letter 0.007pt wide - the word builder then read "m ethods" and "w hen"
    and the page lost every check. A font with no name gets no advance from the tables."""
    raw = A.build(_TEX_TYPE3_PAGE, 1)
    assert raw is not None
    from truedoc.extract.textlayer import extract_page
    import pymupdf
    doc = pymupdf.open(_TEX_TYPE3_PAGE)
    try:
        page = extract_page(doc[0], 1)
        words = [w.text for ln in page.lines for w in ln.words]
    finally:
        doc.close()
    assert "methods" in words and "Quantitatively," in words, words[:40]
    assert "m" not in words[:200] or "ethods" not in words, [w for w in words if w in ("m", "ethods", "w", "hen")]
