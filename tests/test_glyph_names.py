"""Glyph names PDFium cannot map, read from the PDF's own font tables (M18, D007).

Adobe's fonts name their ligatures in parts - "f_i", "f_f_i", "T_h" - and PDFium's glyph list
has no such names, so a page of Minion and Myriad lost every "fi", "fl" and "Th". The names are
in the PDF's /Differences arrays; this reads them there.
"""

import os
import tempfile

import pytest

from truedoc.extract import glyph_names as G

pytestmark = pytest.mark.skipif(not G.available(), reason="pypdf/fontTools not installed")


def _pdf(fonts: list[bytes], content: bytes) -> bytes:
    """One page; `fonts` are font dictionaries, named /F1, /F2, ... in order."""
    refs = b" ".join(b"/F%d %d 0 R" % (i + 1, 4 + i) for i in range(len(fonts)))
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 200] /Resources << /Font << " + refs + b" >> >> /Contents "
        + str(4 + len(fonts)).encode() + b" 0 R >>",
        *fonts,
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


def _font(base: bytes, differences: bytes, widths: bytes = b"", first: int = 28) -> bytes:
    extra = b" /FirstChar %d /Widths [%s]" % (first, widths) if widths else b""
    return (b"<< /Type /Font /Subtype /Type1 /BaseFont /" + base
            + b" /Encoding << /Type /Encoding /BaseEncoding /WinAnsiEncoding /Differences [" + differences + b"] >>" + extra + b" >>")


def _with(pdf: bytes):
    fd, path = tempfile.mkstemp(suffix=".pdf")
    with os.fdopen(fd, "wb") as fh:
        fh.write(pdf)
    return path


def test_names_in_parts_become_their_letters():
    path = _with(_pdf([_font(b"ABCDEF+MinionPro-Regular", b"28 /T_h /f_f_i /f_l /f_i")], b"BT /F1 10 Tf 20 100 Td (\\034\\035) Tj ET"))
    try:
        tables = G.page_glyph_names(path, 1)
        assert tables is not None
        assert G.text_for(tables, "MinionPro-Regular", 28) == "Th"
        assert G.text_for(tables, "MinionPro-Regular", 29) == "ffi"
        assert G.text_for(tables, "MinionPro-Regular", 30) == "fl"
        assert G.text_for(tables, "MinionPro-Regular", 31) == "fi"
        assert G.text_for(tables, "MinionPro-Regular", 65) is None       # nothing renamed there
        assert G.text_for(tables, "SomeOtherFont", 28) is None
    finally:
        os.unlink(path)


def test_standard_and_uni_names_resolve_too():
    path = _with(_pdf([_font(b"Foo", b"28 /uni03BC /fraction /Omega")], b"BT /F1 10 Tf 20 100 Td (\\034) Tj ET"))
    try:
        tables = G.page_glyph_names(path, 1)
        assert G.text_for(tables, "Foo", 28) == "μ"
        assert G.text_for(tables, "Foo", 29) == "⁄"
        assert G.text_for(tables, "Foo", 30) == "Ω"
    finally:
        os.unlink(path)


def test_two_resources_of_one_name_are_told_apart_by_the_advance():
    """MinionPro-Regular twice on one benchmark page: code 31 is "/fraction" in one and "/f_l" in
    the other. PDFium names the font, not the resource; the glyph's advance picks the right one."""
    fonts = [
        _font(b"JLOLKY+MinionPro-Regular", b"31 /fraction", widths=b"167", first=31),
        _font(b"JLOLKY+MinionPro-Regular", b"31 /f_l", widths=b"559", first=31),
    ]
    path = _with(_pdf(fonts, b"BT /F1 10 Tf 20 100 Td (\\037) Tj ET BT /F2 10 Tf 60 100 Td (\\037) Tj ET"))
    try:
        tables = G.page_glyph_names(path, 1)
        assert G.text_for(tables, "MinionPro-Regular", 31, advance_per_em=170) == "⁄"
        assert G.text_for(tables, "MinionPro-Regular", 31, advance_per_em=555) == "fl"
    finally:
        os.unlink(path)


def test_a_document_without_a_path_is_left_alone():
    assert G.page_glyph_names("", 1) is None
    assert G.text_for(None, "X", 1) is None


def test_the_reader_reads_the_named_glyphs_as_their_letters():
    """Through the PDFium reader itself: a "Th" and an "fi" on codes PDFium cannot map come out as
    the letters, each name's characters sharing the one glyph's box the way an expanded ligature
    does (the first keeps the box, the rest sit at its right edge)."""
    from truedoc.extract import pdftext_rawdict as A
    if not A.available():
        pytest.skip("pdftext/pypdfium2 not installed")
    font = _font(b"ABCDEF+MinionPro-Regular", b"28 /T_h /f_i", widths=b"700 500", first=28)
    path = _with(_pdf([font], b"BT /F1 12 Tf 20 100 Td (\034us \035ne) Tj ET"))
    try:
        raw = A.build(path, 1)
        assert raw is not None
        chars = [c for b in raw["blocks"] for ln in b["lines"] for sp in ln["spans"] for c in sp["chars"]]
        text = "".join(c["c"] for c in chars)
        assert text.replace(" ", "") == "Thusfine", repr(text)
        t, h = chars[0], chars[1]
        assert t["c"] == "T" and h["c"] == "h"
        assert h["bbox"][0] == h["bbox"][2] == t["bbox"][2], (t["bbox"], h["bbox"])
    finally:
        os.unlink(path)
