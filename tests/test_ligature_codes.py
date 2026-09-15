"""A ligature the text layer spoils is read back from the glyph's own name.

RAA's landlord PDS maps the codes of its ff and fi ligatures to "f" in its ToUnicode map, so the file's own text reads
"ofer", "fnd" and "Cooling-of", while the encoding still names those glyphs "f_f" and "fi". The reader aligns the
content stream's codes with PDFium's characters and gives a character drawn with such a glyph the name's letters. A
map that already gives the ligature's letters is left as it is.
"""
import pymupdf

from truedoc.extract import pdftext_rawdict
from truedoc.extract.textlayer import extract_page


def _pdf(tmp_path, ff_unicode: str, fi_unicode: str) -> str:
    """One line of Helvetica, "We offer to find it", drawn with codes 30 (f_f) and 31 (fi) and a ToUnicode map."""
    content = b"BT /F1 12 Tf 20 100 Td (We o\x1eer to \x1fnd it) Tj ET"
    cmap = ("/CIDInit /ProcSet findresource begin 12 dict begin begincmap /CMapName /T1 def "
            "1 begincodespacerange <00> <FF> endcodespacerange "
            f"3 beginbfchar <1E> <{ff_unicode}> <1F> <{fi_unicode}> <20> <0020> endbfchar "
            "1 beginbfrange <41> <7A> <0041> endbfrange "
            "endcmap CMapName currentdict /CMap defineresource pop end end").encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 200] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding << /Type /Encoding /BaseEncoding /WinAnsiEncoding"
        b" /Differences [30 /f_f /fi] >> /ToUnicode 6 0 R >>",
        b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream",
        b"<< /Length %d >>\nstream\n" % len(cmap) + cmap + b"\nendstream",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    for offset in offsets:
        out += b"%010d 00000 n \n" % offset
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, xref)
    path = tmp_path / "ligatures.pdf"
    path.write_bytes(bytes(out))
    return str(path)


def _text(path: str) -> str:
    pdftext_rawdict._CACHE.clear()
    doc = pymupdf.open(path)
    try:
        page = extract_page(doc[0], 1)
        return " ".join(w.text for line in page.lines for w in line.words)
    finally:
        pdftext_rawdict._CACHE.clear()
        doc.close()


def test_a_ligature_the_map_spoils_reads_as_its_glyph_name(tmp_path):
    text = _text(_pdf(tmp_path, "0066", "0066"))
    assert "offer" in text and "find" in text, text


def test_a_ligature_the_map_already_spells_is_left_as_it_is(tmp_path):
    text = _text(_pdf(tmp_path, "00660066", "00660069"))
    assert "offer" in text and "find" in text and "offfer" not in text, text
