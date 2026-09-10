"""What the arXiv pages taught the PDFium reader (M18, D022).

Run 67 - every switch on - lost 78 maths checks against the MuPDF run, and the losses traced to
four habits of PDFium's text page that MuPDF does not share. Each is built by hand here, from a
one-page PDF, so the case is pinned whatever the corpus does; and where the two readers must
agree, the test asks both.

- A letter beyond the basic plane (a maths font's italic m is U+1D45A) comes back from PDFium as
  two UTF-16 halves, and pdftext writes each half as U+FFFD. One page read 496 of those, 21.6% of
  its text, and the quality gate sent the page to the model as a broken layer.
- A character PDFium cannot map to Unicode must keep the box PDFium computed for it: the advance
  lookup goes by Unicode and answers for some other glyph.
- One font drawn at two matrix scales is one nominal size to pdftext, so one span; the drawn sizes
  differ and MuPDF cuts the span there.
- PDFium ends a line wherever the baseline steps, so "R", "2", "n" and the words after a raised
  superscript arrive as four lines; MuPDF reads one.
"""

import ctypes
import os
import tempfile

import pytest

from truedoc.extract import pdftext_rawdict as A

pytestmark = pytest.mark.skipif(not A.available(), reason="pdftext/pypdfium2 not installed")


def _pdf(content: bytes, font_extra: bytes = b"", extra_objs: tuple = ()) -> bytes:
    """A one-page PDF drawing `content` with Helvetica as /F1. `font_extra` is spliced into the
    font dictionary; `extra_objs` are appended as objects 6, 7, ... for it to refer to."""
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 200] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica" + font_extra + b" >>",
        b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream",
        *extra_objs,
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


def _stream(body: bytes) -> bytes:
    return b"<< /Length " + str(len(body)).encode() + b" >>\nstream\n" + body + b"\nendstream"


class _File:
    def __init__(self, pdf: bytes):
        fd, self.path = tempfile.mkstemp(suffix=".pdf")
        with os.fdopen(fd, "wb") as fh:
            fh.write(pdf)

    def __enter__(self):
        return self.path

    def __exit__(self, *exc):
        os.unlink(self.path)


def _chars(raw: dict) -> list[dict]:
    return [c for b in raw["blocks"] for ln in b["lines"] for sp in ln["spans"] for c in sp["chars"]]


def _mupdf_chars(path: str) -> list[str]:
    import pymupdf
    doc = pymupdf.open(path)
    try:
        d = doc[0].get_text("rawdict")
        return [c["c"] for b in d["blocks"] for ln in b.get("lines", []) for sp in ln["spans"] for c in sp["chars"]]
    finally:
        doc.close()


# --- a code point beyond the basic plane --------------------------------------------------

_CMAP = (b"/CIDInit /ProcSet findresource begin 12 dict begin begincmap\n"
         b"/CMapName /Custom def\n1 begincodespacerange <00> <FF> endcodespacerange\n"
         b"1 beginbfchar <41> <D835DC5A> endbfchar\nendcmap CMapName currentdict /CMap defineresource pop end end\n")


def test_a_letter_beyond_the_basic_plane_is_one_character():
    """The A is mapped to U+1D45A (mathematical italic small m) through a ToUnicode CMap, the way
    a maths font's letters are. PDFium holds it as two UTF-16 halves; MuPDF as one character."""
    pdf = _pdf(b"BT /F1 12 Tf 1 0 0 1 20 100 Tm (A) Tj ET", font_extra=b" /ToUnicode 6 0 R", extra_objs=(_stream(_CMAP),))
    with _File(pdf) as path:
        raw = A.build(path, 1)
        assert raw is not None
        ours = [c["c"] for c in _chars(raw) if not c["c"].isspace()]
        assert ours == ["\U0001d45a"], ours
        assert "�" not in "".join(c["c"] for c in _chars(raw))
        theirs = [c for c in _mupdf_chars(path) if not c.isspace()]
        assert ours == theirs, (ours, theirs)


# --- a character PDFium cannot map ---------------------------------------------------------

def test_an_unmapped_character_keeps_pdfiums_own_box():
    """Code 65 is renamed to a glyph no table knows, as cmsy's mapstochar is. PDFium reports the
    character with a mapping error, and its box must be the one PDFium computed - not widened
    to the advance of whatever glyph the Unicode lookup lands on."""
    import pypdfium2 as pdfium
    import pypdfium2.raw as raw_api
    pdf = _pdf(b"BT /F1 12 Tf 1 0 0 1 20 100 Tm (A) Tj ET",
               font_extra=b" /Encoding << /Type /Encoding /Differences [65 /mapstochar] >>")
    with _File(pdf) as path:
        doc = pdfium.PdfDocument(path)
        try:
            page = doc[0]
            tp = page.get_textpage()
            assert raw_api.FPDFText_HasUnicodeMapError(tp.raw, 0) == 1, "the fixture no longer reproduces a mapping error"
            rect = raw_api.FS_RECTF()
            assert raw_api.FPDFText_GetLooseCharBox(tp.raw, 0, rect)
            loose_right = rect.right
            tp.close()
            page.close()
        finally:
            doc.close()
        raw = A.build(path, 1)
        assert raw is not None
        c = next(c for c in _chars(raw) if not c["c"].isspace())
        assert c["map_error"] is True
        assert abs(c["bbox"][2] - loose_right) < 1e-3, (c["bbox"], loose_right)


# --- one font at two scales ---------------------------------------------------------------

def test_one_font_at_two_scales_is_two_sizes():
    """/F1 1 Tf drawn at 10x and then 7x: one nominal size, two drawn sizes. pdftext hands over
    one span; the reader must cut it where the size changes, as MuPDF does."""
    pdf = _pdf(b"BT /F1 1 Tf 10 0 0 10 20 100 Tm (Big) Tj 7 0 0 7 45 100 Tm (small) Tj ET")
    with _File(pdf) as path:
        page = A._order(path, 1)
        nominal = {round(float((sp.get("font") or {}).get("size") or 0), 2)
                   for b in page["blocks"] for ln in b["lines"] for sp in ln["spans"]}
        assert nominal == {1.0}, f"the fixture no longer shows one nominal size: {nominal}"
        raw = A.build(path, 1)
        assert raw is not None
        by_char = {c["c"]: sp["size"] for b in raw["blocks"] for ln in b["lines"] for sp in ln["spans"] for c in sp["chars"]}
        assert abs(by_char["B"] - 10.0) < 0.1 and abs(by_char["g"] - 10.0) < 0.1, by_char
        assert abs(by_char["s"] - 7.0) < 0.1 and abs(by_char["l"] - 7.0) < 0.1, by_char


# --- a line broken at a superscript -------------------------------------------------------

_RAISED = (b"BT /F1 10 Tf 1 0 0 1 20 100 Tm (R) Tj ET\n"
           b"BT /F1 7 Tf 1 0 0 1 27.22 104 Tm (2) Tj ET\n"
           b"BT /F1 5 Tf 1 0 0 1 31.11 107 Tm (n) Tj ET\n"
           b"BT /F1 10 Tf 1 0 0 1 36 100 Tm (\\(by abuse\\)) Tj ET\n")


def _line_texts(raw: dict) -> list[str]:
    return ["".join(c["c"] for sp in ln["spans"] for c in sp["chars"]) for b in raw["blocks"] for ln in b["lines"]]


def test_a_line_pdfium_breaks_at_a_superscript_is_one_line():
    """R, a raised 2, a higher and smaller n, and the words after: MuPDF reads one line."""
    import pymupdf
    with _File(_pdf(_RAISED)) as path:
        page = A._order(path, 1)
        pdftext_lines = sum(len(b["lines"]) for b in page["blocks"])
        assert pdftext_lines >= 2, "the fixture no longer reproduces PDFium's break"
        raw = A.build(path, 1)
        assert raw is not None
        texts = _line_texts(raw)
        assert len(texts) == 1, texts
        doc = pymupdf.open(path)
        try:
            mu = [ln for b in doc[0].get_text("rawdict")["blocks"] for ln in b.get("lines", [])]
        finally:
            doc.close()
        assert len(mu) == len(texts) == 1


def test_the_join_keeps_the_words_apart_and_the_scripts_attached():
    """No blank between R and its superscripts - they touch, and are one word to MuPDF - and a
    blank before the words that follow, which stand a word's gap away."""
    with _File(_pdf(_RAISED)) as path:
        raw = A.build(path, 1)
        assert raw is not None
        text = _line_texts(raw)[0]
        compact = "".join(ch if not ch.isspace() else " " for ch in text).strip()
        assert compact.startswith("R2n "), repr(compact)
        assert "(by abuse)" in compact, repr(compact)
        sizes = {c["c"]: sp["size"] for b in raw["blocks"] for ln in b["lines"] for sp in ln["spans"] for c in sp["chars"]}
        assert abs(sizes["2"] - 7.0) < 0.1 and abs(sizes["n"] - 5.0) < 0.1, sizes


def test_a_new_line_further_down_is_still_a_new_line():
    """The join must not swallow the next line of a paragraph: it starts back at the margin."""
    content = (b"BT /F1 10 Tf 1 0 0 1 20 100 Tm (first line here) Tj ET\n"
               b"BT /F1 10 Tf 1 0 0 1 20 88 Tm (second line here) Tj ET\n")
    with _File(_pdf(content)) as path:
        raw = A.build(path, 1)
        assert raw is not None
        texts = [t.strip() for t in _line_texts(raw)]
        assert texts == ["first line here", "second line here"], texts


def test_a_full_size_run_on_its_own_baseline_stays_its_own_line():
    """Full-size text a line's height up, starting to the right of the "=" it follows - a
    fraction's numerator, a matrix row. PDFium breaks its line there (a smaller step it keeps,
    and so does the reader); the join must leave the break alone. Only a script, or text back on
    the baseline, carries a line on."""
    content = (b"BT /F1 10 Tf 1 0 0 1 20 100 Tm (Z = ) Tj ET\n"
               b"BT /F1 10 Tf 1 0 0 1 45 112 Tm (tw z) Tj ET\n"
               b"BT /F1 10 Tf 1 0 0 1 45 88 Tm (0 w) Tj ET\n")
    with _File(_pdf(content)) as path:
        page = A._order(path, 1)
        assert sum(len(b["lines"]) for b in page["blocks"]) == 3, "the fixture no longer reproduces PDFium's breaks"
        raw = A.build(path, 1)
        assert raw is not None
        texts = [t.strip() for t in _line_texts(raw)]
        assert texts == ["Z =", "tw z", "0 w"], texts


# --- turned text -----------------------------------------------------------------------------

def _mupdf_dirs(path: str) -> list[tuple[float, float]]:
    import pymupdf
    doc = pymupdf.open(path)
    try:
        return [tuple(ln["dir"]) for b in doc[0].get_text("rawdict")["blocks"] for ln in b.get("lines", [])]
    finally:
        doc.close()


@pytest.mark.parametrize("matrix, words", [
    (b"0 1 -1 0 100 50", (b"Source: Adapted from",)),      # running up the page
    (b"0 -1 1 0 100 150", (b"running down",)),
    (b"-1 0 0 -1 200 100", (b"upside down",)),
    (b"1 0 0 1 20 100", (b"level text",)),
])
def test_turned_text_reads_in_mupdfs_direction(matrix, words):
    """The quantity both readers must agree on (D022): the direction a line runs in. A table's
    vertical headings on one benchmark page came out one word to a line and read backwards
    because every line was taken as level."""
    content = b"".join(b"BT /F1 10 Tf " + matrix + b" Tm (" + w + b") Tj ET\n" for w in words)
    with _File(_pdf(content)) as path:
        raw = A.build(path, 1)
        assert raw is not None
        ours = [ln["dir"] for b in raw["blocks"] for ln in b["lines"]]
        theirs = _mupdf_dirs(path)
        assert len(ours) == len(theirs) == 1, (ours, theirs)
        assert all(abs(a - b) < 1e-6 for a, b in zip(ours[0], theirs[0])), (ours, theirs)


def test_turned_text_is_not_cut_at_its_word_spaces():
    """PDFium files the blank it makes up between two turned words as a level line of its own,
    and the text then arrives one word to a line. MuPDF reads the three words as one line."""
    content = b"BT /F1 10 Tf 0 1 -1 0 100 30 Tm (Source: Adapted from) Tj ET\n"
    with _File(_pdf(content)) as path:
        raw = A.build(path, 1)
        assert raw is not None
        texts = ["".join(c["c"] for sp in ln["spans"] for c in sp["chars"]).split() for b in raw["blocks"] for ln in b["lines"]]
        assert texts == [["Source:", "Adapted", "from"]], texts
        assert len(_mupdf_dirs(path)) == 1
