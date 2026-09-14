"""A character's box stops at the next character's origin, however wide the font's lookup says the character is.

The text reader boxes a level character from its origin to its origin plus the advance PDFium's width lookup gives for
the character's Unicode value. RAA's landlord PDS maps its ff and fi ligatures to "f", and the lookup answered every
f with a ligature's width, nearly three times the f's own: each f's box ran over the space after it and into the next
word, and "If you" read "Ifyou". The box stops only at a character the file holds: on an Allianz PDS page PDFium put
the line breaks and spaces it makes up a fraction of a point after the origin of the letter before them, and a first
version cut word-final letters, ticks and bullets to that. And it stops only at a character beside the glyph, their ink
sharing some of the glyph's height, or one of them having no ink at all, as a space has none: an accent set over a
letter says nothing of where the letter ends, whatever character its font maps it to, and a second version cut
Jönsson's o short at its umlaut (mapped to "«") and TeX's letters at the hats and tildes over them. Each test gives
PDFium the fault seen on the real page, on a page of its own.
"""
import ctypes

import pymupdf
import pypdfium2.raw as raw

from truedoc.extract import pdftext_rawdict
from truedoc.extract.textlayer import extract_page

LINE = "If you do not tell us of these changes"


def _page(tmp_path, pieces):
    """A page from (x, y, text) pieces at 8.5pt."""
    doc = pymupdf.open()
    page = doc.new_page(width=300, height=200)
    for x, y, text in pieces:
        page.insert_text((x, y), text, fontsize=8.5)
    path = tmp_path / "f.pdf"
    doc.save(str(path))
    doc.close()
    return str(path)


def _words(path):
    pdftext_rawdict._CACHE.clear()
    doc = pymupdf.open(path)
    try:
        page = extract_page(doc[0], 1)
        return [w for line in page.lines for w in line.words]
    finally:
        pdftext_rawdict._CACHE.clear()
        doc.close()


def _mupdf_right_edges(path):
    doc = pymupdf.open(path)
    try:
        return {w[4]: w[2] for w in doc[0].get_text("words")}
    finally:
        doc.close()


def _chars(node):
    """Every character of a rawdict-shaped reading, in order."""
    if isinstance(node, dict):
        if "c" in node and "bbox" in node:
            yield node
        for value in node.values():
            yield from _chars(value)
    elif isinstance(node, list):
        for value in node:
            yield from _chars(value)


def _accent_page(tmp_path):
    """The name Jonsson in Helvetica with an umlaut set 0.2 em into its o, as Jönsson's page sets its umlaut: code 0xAB
    draws the dieresis glyph and the ToUnicode map sends that code to "«". The pen goes back to the o's end."""
    content = b"BT /F1 12 Tf 20 100 Td [(Jo) 356 <AB> -23 (nsson)] TJ ET"
    cmap = (b"/CIDInit /ProcSet findresource begin 12 dict begin begincmap /CMapName /T1 def "
            b"1 begincodespacerange <00> <FF> endcodespacerange "
            b"1 beginbfchar <AB> <00AB> endbfchar "
            b"1 beginbfrange <20> <7E> <0020> endbfrange "
            b"endcmap CMapName currentdict /CMap defineresource pop end end")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 200] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding << /Type /Encoding /BaseEncoding /WinAnsiEncoding"
        b" /Differences [171 /dieresis] >> /ToUnicode 6 0 R >>",
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
    path = tmp_path / "accent.pdf"
    path.write_bytes(bytes(out))
    return str(path)


def _ligature_wide_f(monkeypatch):
    """The width lookup answers "f" with a ligature's width, as on RAA's page."""
    real = raw.FPDFFont_GetGlyphWidth

    def lookup(font, glyph, size, width):
        ok = real(font, glyph, size, width)
        if ok and glyph == ord("f"):
            width.value *= 2.9
        return ok

    monkeypatch.setattr(raw, "FPDFFont_GetGlyphWidth", lookup)


def _spaces_without_ink(monkeypatch):
    """PDFium gives a space an ink box of no height, as it gives ArialMT's on CGU's and NRMA's Key Facts Sheets."""
    real = raw.FPDFText_GetCharBox

    def char_box(tp, index, left, right, bottom, top):
        ok = real(tp, index, left, right, bottom, top)
        if ok and raw.FPDFText_GetUnicode(tp, index) == 0x20:
            getattr(top, "_obj", top).value = getattr(bottom, "_obj", bottom).value
        return ok

    monkeypatch.setattr(raw, "FPDFText_GetCharBox", char_box)


def _made_up_characters_just_after_the_glyph(monkeypatch):
    """PDFium reports each character it makes up half a point after the origin of the one before, as on Allianz's page."""
    real = raw.FPDFText_GetCharOrigin

    def origin(tp, index, x, y):
        ok = real(tp, index, x, y)
        if ok and index > 0 and raw.FPDFText_IsGenerated(tp, index):
            px, py = ctypes.c_double(), ctypes.c_double()
            if real(tp, index - 1, px, py):
                x.value, y.value = px.value + 0.5, py.value
        return ok

    monkeypatch.setattr(raw, "FPDFText_GetCharOrigin", origin)


def test_the_line_reads_whole_with_a_true_lookup(tmp_path):
    assert LINE in " ".join(w.text for w in _words(_page(tmp_path, [(20, 100, LINE)])))


def test_an_f_the_lookup_answers_for_a_ligature_keeps_the_space_after_it(tmp_path, monkeypatch):
    path = _page(tmp_path, [(20, 100, LINE)])
    _ligature_wide_f(monkeypatch)
    text = " ".join(w.text for w in _words(path))
    assert "If you" in text and "of these" in text, text


def test_an_f_the_lookup_answers_for_a_ligature_keeps_the_space_after_it_when_the_space_has_no_ink(tmp_path, monkeypatch):
    path = _page(tmp_path, [(20, 100, LINE)])
    _ligature_wide_f(monkeypatch)
    _spaces_without_ink(monkeypatch)
    text = " ".join(w.text for w in _words(path))
    assert "If you" in text and "of these" in text, text


def test_a_word_at_a_line_end_keeps_its_last_letter_before_a_made_up_line_break(tmp_path, monkeypatch):
    path = _page(tmp_path, [(20, 100, "Your home buildings"), (20, 112, "Garages, carports and sheds")])
    theirs = _mupdf_right_edges(path)
    _made_up_characters_just_after_the_glyph(monkeypatch)
    ours = {w.text: w.bbox.x1 for w in _words(path)}
    assert abs(ours["buildings"] - theirs["buildings"]) < 0.5, (ours["buildings"], theirs["buildings"])


def test_a_letter_keeps_its_advance_under_an_accent_its_font_maps_to_another_character(tmp_path):
    path = _accent_page(tmp_path)
    doc = pymupdf.open(path)
    try:
        theirs = next(c for c in _chars(doc[0].get_text("rawdict")) if c["c"] == "o")
    finally:
        doc.close()
    pdftext_rawdict._CACHE.clear()
    try:
        ours = next(c for c in _chars(pdftext_rawdict.build(path, 1)) if c["c"] == "o")
    finally:
        pdftext_rawdict._CACHE.clear()
    assert abs(ours["bbox"][2] - theirs["bbox"][2]) < 0.05, (ours["bbox"], theirs["bbox"])
