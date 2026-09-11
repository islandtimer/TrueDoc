"""A character's box is its advance box, whichever library reads it (M18, D022).

The word builder decides a break from the gap between one character's right edge and the next's
left: above `max(0.13 x size, 0.9pt)` is a word space. MuPDF's right edge is the glyph's *advance*.
PDFium's "loose" box is not quite - on a glyph whose ink overhangs its advance, the letter f above
all, it runs further right. On a 7pt line that was 0.44pt: MuPDF read a gap of 1.31pt and broke
the word, PDFium read 0.87 and did not, and "of the" came out "ofthe". Run 66 lost small-type
checks to it, and the size fix that preceded it was necessary and not sufficient.

PDFium exposes the advance (`FPDFFont_GetGlyphWidth`), so the right edge is origin plus advance
and the box is MuPDF's by construction. Times has an overhanging f, and it is one of the fonts
every reader carries, so the case can be pinned without embedding anything.
"""

import os
import tempfile

import pymupdf
import pytest

from truedoc.extract import pdftext_rawdict as A
from truedoc.extract import render

pytestmark = pytest.mark.skipif(not A.available(), reason="pdftext/pypdfium2 not installed")

# "\256" is the fi ligature in StandardEncoding, so "\256xtures" draws one glyph for "fi" - the
# case where taking a lone f's advance opens a gap inside the word.
_CONTENT = b"BT /F1 7 Tf 20 100 Td (one of the finest offers and \\256xtures) Tj ET\n"


def _pdf(content: bytes = _CONTENT) -> bytes:
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 200] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Times-Roman >>",
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


def _boxes() -> tuple[list, list]:
    """(PDFium chars, MuPDF chars) as (text, x0, x1), non-space, in reading order."""
    fd, path = tempfile.mkstemp(suffix=".pdf")
    with os.fdopen(fd, "wb") as fh:
        fh.write(_pdf())
    try:
        raw = A.build(path, 1)
        assert raw is not None
        pf = [(c["c"], c["bbox"][0], c["bbox"][2]) for b in raw["blocks"] for ln in b["lines"]
              for sp in ln["spans"] for c in sp["chars"] if not c["c"].isspace()]
        doc = pymupdf.open(path)
        try:
            flags = pymupdf.TEXTFLAGS_RAWDICT & ~pymupdf.TEXT_PRESERVE_LIGATURES | pymupdf.TEXT_MEDIABOX_CLIP
            mu = [(c["c"], c["bbox"][0], c["bbox"][2]) for blk in doc[0].get_text("rawdict", flags=flags)["blocks"]
                  if blk.get("type") == 0 for ln in blk["lines"] for sp in ln["spans"] for c in sp["chars"]
                  if not c["c"].isspace()]
        finally:
            doc.close()
        return pf, mu
    finally:
        render.close_documents()
        os.unlink(path)


def test_the_readers_agree_on_every_right_edge_including_the_overhanging_f():
    pf, mu = _boxes()
    assert [c for c, _, _ in pf] == [c for c, _, _ in mu], "the two readers should see the same text"
    worst = max(abs(a[2] - b[2]) for a, b in zip(pf, mu))
    fs = [(a[2], b[2]) for a, b in zip(pf, mu) if a[0] == "f"]
    assert fs, "the sample has no f"
    assert worst < 0.05, f"right edges differ by up to {worst:.3f}pt; f: {fs}"


def test_the_readers_agree_on_every_left_edge():
    pf, mu = _boxes()
    worst = max(abs(a[1] - b[1]) for a, b in zip(pf, mu))
    assert worst < 0.05, f"left edges differ by up to {worst:.3f}pt"


def test_a_characters_box_is_the_fonts_ascent_and_descent():
    """MuPDF boxes every character from the baseline by the font's ascender and descender;
    PDFium's loose box uses something smaller above the baseline - 1.4pt lower on 8pt Arial -
    and by an amount that varies with the glyphs, so a table's header line and the "Item"
    label centred over it changed rows in the rebuild and two columns fused (fa18a15c).
    `FPDFFont_GetAscent` and `GetDescent` are the metrics MuPDF uses; the box is built from
    them, level text only. On a hand-built page the two libraries substitute different faces
    for a font that is not embedded (0.891 against 1.053 em of ascent for Times), so what is
    pinned here is the construction: one top and one bottom for every character of a size,
    at the font's ascent and descent. The embedded-font page below pins the agreement."""
    import ctypes

    import pypdfium2 as pdfium
    import pypdfium2.raw as raw_api
    content = b"BT /F1 8 Tf 1 0 0 1 20 100 Tm (Item) Tj ET\nBT /F1 8 Tf 1 0 0 1 60 105 Tm (Aug 21,) Tj ET\nBT /F1 12 Tf 1 0 0 1 20 60 Tm (Big) Tj ET"
    fd, path = tempfile.mkstemp(suffix=".pdf")
    with os.fdopen(fd, "wb") as fh:
        fh.write(_pdf(content))
    try:
        doc = pdfium.PdfDocument(path)
        try:
            page = doc[0]
            tp = page.get_textpage()
            font = raw_api.FPDFTextObj_GetFont(raw_api.FPDFText_GetTextObject(tp.raw, 0))
            asc, desc = ctypes.c_float(), ctypes.c_float()
            assert raw_api.FPDFFont_GetAscent(font, 8.0, asc) and raw_api.FPDFFont_GetDescent(font, 8.0, desc)
            ascent8, descent8 = asc.value, desc.value
            tp.close()
            page.close()
        finally:
            doc.close()
        raw = A.build(path, 1)
        assert raw is not None
        by_size: dict[float, set] = {}
        for b in raw["blocks"]:
            for ln in b["lines"]:
                for sp in ln["spans"]:
                    for c in sp["chars"]:
                        if not c["c"].isspace():
                            by_size.setdefault(round(sp["size"]), set()).add((round(c["bbox"][1] - c["origin"][1], 2), round(c["bbox"][3] - c["origin"][1], 2)))
        assert len(by_size[8]) == 1 and len(by_size[12]) == 1, by_size      # one box per size, whatever the glyph
        (top8, bottom8), = by_size[8]
        assert abs(top8 + ascent8) < 0.05 and abs(bottom8 + descent8) < 0.05, (top8, bottom8, ascent8, descent8)
        (top12, bottom12), = by_size[12]
        assert abs(top12 - 1.5 * top8) < 0.05 and abs(bottom12 - 1.5 * bottom8) < 0.05, (top8, top12)
    finally:
        os.unlink(path)


_ARIAL_PAGE = os.path.join("bench", "data", "olmocr-bench", "bench_data", "pdfs", "tables",
                           "fa18a15c1dbbfcb71b1f1ea1b8f116e24b8a_pg2_pg1.pdf")


@pytest.mark.skipif(not os.path.exists(_ARIAL_PAGE), reason="benchmark page not present")
def test_an_embedded_fonts_boxes_agree_with_mupdf_to_the_hundredth():
    """The page it was measured on (Arial embedded): every level character's top and bottom
    within a twentieth of a point of MuPDF's."""
    raw = A.build(_ARIAL_PAGE, 1)
    assert raw is not None
    ours = {}
    for b in raw["blocks"]:
        for ln in b["lines"]:
            if ln["dir"] != (1.0, 0.0):
                continue
            for sp in ln["spans"]:
                for c in sp["chars"]:
                    if not c["c"].isspace() and c.get("origin"):
                        ours[(c["c"], round(c["origin"][0], 1), round(c["origin"][1], 1))] = (c["bbox"][1], c["bbox"][3])
    doc = pymupdf.open(_ARIAL_PAGE)
    try:
        theirs = {}
        for b in doc[0].get_text("rawdict")["blocks"]:
            for ln in b.get("lines", []):
                if tuple(ln["dir"]) != (1.0, 0.0):
                    continue
                for sp in ln["spans"]:
                    for c in sp["chars"]:
                        if not c["c"].isspace():
                            theirs[(c["c"], round(c["origin"][0], 1), round(c["origin"][1], 1))] = (c["bbox"][1], c["bbox"][3])
    finally:
        doc.close()
    matched = [(ours[k], theirs[k]) for k in ours if k in theirs]
    assert len(matched) > 500, len(matched)
    off = [k for k in ours if k in theirs and (abs(ours[k][0] - theirs[k][0]) > 0.05 or abs(ours[k][1] - theirs[k][1]) > 0.05)]
    assert len(off) <= 0.01 * len(matched), (len(off), len(matched), off[:5])


_SHEARED_PAGE = os.path.join("bench", "data", "olmocr-bench", "bench_data", "pdfs", "tables",
                             "b2a4c508f7839c1fbd2bb29a0d56c46bc00e_pg13_pg1.pdf")


@pytest.mark.skipif(not os.path.exists(_SHEARED_PAGE), reason="benchmark page not present")
def test_sheared_text_starts_at_the_origin_and_ends_where_mupdf_ends_it():
    """An italic made by slanting an upright face ("et al." on b2a4c508, text matrix c = 2.09).
    MuPDF's box starts at the glyph's origin and ends where the slanted advance box ends; the
    loose box starts 0.44pt to the left, and that closed the word gap MuPDF reads between "et"
    and "al." (the check wants "Montgomery et al."). Every sheared character's left and right
    edge within a twentieth of a point of MuPDF's."""
    import ctypes
    import pypdfium2 as pdfium
    import pypdfium2.raw as raw_api
    doc = pdfium.PdfDocument(_SHEARED_PAGE)
    page = doc[0]
    tp = page.get_textpage()
    m = raw_api.FS_MATRIX()
    ox, oy = ctypes.c_double(), ctypes.c_double()
    height = page.get_height()
    sheared = set()
    for i in range(raw_api.FPDFText_CountChars(tp)):
        if (raw_api.FPDFText_GetMatrix(tp, i, m) and abs(m.b) < 1e-6 and abs(m.c) > 1e-3
                and raw_api.FPDFText_GetCharOrigin(tp, i, ox, oy)):
            sheared.add((round(ox.value, 1), round(height - oy.value, 1)))
    tp.close()
    page.close()
    doc.close()
    assert len(sheared) > 30, len(sheared)
    raw = A.build(_SHEARED_PAGE, 1)
    assert raw is not None
    ours = {}
    for b in raw["blocks"]:
        for ln in b["lines"]:
            for sp in ln["spans"]:
                for c in sp["chars"]:
                    o = c.get("origin")
                    if o and not c["c"].isspace() and (round(o[0], 1), round(o[1], 1)) in sheared:
                        ours[(c["c"], round(o[0], 1), round(o[1], 1))] = (c["bbox"][0], c["bbox"][2])
    mu = pymupdf.open(_SHEARED_PAGE)
    try:
        theirs = {}
        for b in mu[0].get_text("rawdict")["blocks"]:
            for ln in b.get("lines", []):
                for sp in ln["spans"]:
                    for c in sp["chars"]:
                        if not c["c"].isspace():
                            theirs[(c["c"], round(c["origin"][0], 1), round(c["origin"][1], 1))] = (c["bbox"][0], c["bbox"][2])
    finally:
        mu.close()
    matched = [k for k in ours if k in theirs]
    assert len(matched) > 30, len(matched)
    off = [(k, ours[k], theirs[k]) for k in matched
           if abs(ours[k][0] - theirs[k][0]) > 0.05 or abs(ours[k][1] - theirs[k][1]) > 0.05]
    assert len(off) <= 0.01 * len(matched), (len(off), len(matched), off[:5])


def test_text_scaled_differently_in_x_and_y_is_sized_and_boxed_as_mupdf_sizes_it():
    """An OCR layer fits each word to its box by scaling x and y differently. Measured on 73,333
    such characters over 30 benchmark pages: MuPDF's size is the geometric mean of the two
    scales (every time), its right edge the origin plus the advance at the x scale (every time),
    its top and bottom the ascent and descent at the y scale (92%). The y scale alone read 8.40
    where MuPDF reads 7.28 on 0091c5b2, and the rows of its table fused (three checks). The size
    and the x edges are pinned here; the top and bottom cannot be on a hand-built page, whose
    font is not embedded and so is a different face in each library."""
    content = b"BT /F1 1 Tf 8 0 0 10 20 100 Tm (Immunisation records) Tj ET\n"
    fd, path = tempfile.mkstemp(suffix=".pdf")
    with os.fdopen(fd, "wb") as fh:
        fh.write(_pdf(content))
    try:
        raw = A.build(path, 1)
        assert raw is not None
        ours = [(c["c"], c["bbox"], sp["size"]) for b in raw["blocks"] for ln in b["lines"]
                for sp in ln["spans"] for c in sp["chars"] if not c["c"].isspace()]
        doc = pymupdf.open(path)
        try:
            theirs = [(c["c"], c["bbox"], sp["size"]) for b in doc[0].get_text("rawdict")["blocks"]
                      for ln in b.get("lines", []) for sp in ln["spans"] for c in sp["chars"] if not c["c"].isspace()]
        finally:
            doc.close()
    finally:
        render.close_documents()
        os.unlink(path)
    assert [c for c, _, _ in ours] == [c for c, _, _ in theirs]
    assert ours[0][2] == pytest.approx(theirs[0][2], abs=0.02), (ours[0][2], theirs[0][2])
    assert theirs[0][2] == pytest.approx((8 * 10) ** 0.5, abs=0.05)
    for (c, ob, _), (_, tb, _) in zip(ours, theirs):
        assert ob[0] == pytest.approx(tb[0], abs=0.05) and ob[2] == pytest.approx(tb[2], abs=0.05), (c, ob, tb)


def test_a_negative_font_size_under_a_flipped_matrix_reads_left_to_right():
    """A tax form (8e953483, headers) draws its text with the matrix -1.333 0 0 -1.333 and a
    font size of -4.43: two negations, so the glyphs stand upright and run left to right,
    but PDFium's angle for them is pi, the reader voted right-to-left, every step was a
    backwards jump and the page shattered into 1,290 one-character lines. The sign of the
    size is part of the direction; MuPDF reads one line running (1, 0)."""
    content = b"BT /F1 -10 Tf -1 0 0 -1 40 100 Tm (Hello there) Tj ET\n"
    fd, path = tempfile.mkstemp(suffix=".pdf")
    with os.fdopen(fd, "wb") as fh:
        fh.write(_pdf(content))
    try:
        raw = A.build(path, 1)
        assert raw is not None
        lines = [ln for b in raw["blocks"] for ln in b["lines"]]
        assert len(lines) == 1, [("".join(c["c"] for sp in ln["spans"] for c in sp["chars"])) for ln in lines]
        assert lines[0]["dir"] == (1.0, 0.0), lines[0]["dir"]
        text = "".join(c["c"] for sp in lines[0]["spans"] for c in sp["chars"])
        assert text.replace(" ", "") == "Hellothere", text
        assert all(sp["size"] > 0 for sp in lines[0]["spans"]), [sp["size"] for sp in lines[0]["spans"]]
        doc = pymupdf.open(path)
        try:
            mu = [ln for b in doc[0].get_text("rawdict")["blocks"] for ln in b.get("lines", [])]
            assert len(mu) == 1 and tuple(mu[0]["dir"]) == (1.0, 0.0)
        finally:
            doc.close()
    finally:
        render.close_documents()
        os.unlink(path)


def test_a_crop_box_wider_than_the_media_box_measures_from_their_intersection():
    """b2ca8e00 (headers) has a CropBox of 595 by 842 around a MediaBox of 430 by 660. MuPDF
    measures every coordinate from the top-left of the two boxes' intersection (its page
    rect); PDFium's crop box call gives the raw box, and measuring from it put every
    character 82.5pt right and 92pt down of where MuPDF has it - the running head sat at
    y = 121 instead of 28, outside the page-edge band, and was kept."""
    content = b"BT /F1 10 Tf 124.3 715 Td (Running head) Tj ET\n"
    body = _pdf(content).replace(b"/MediaBox [0 0 300 200]", b"/MediaBox [82.5 90 512.5 750] /CropBox [0 0 595 842]")
    fd, path = tempfile.mkstemp(suffix=".pdf")
    with os.fdopen(fd, "wb") as fh:
        fh.write(body)
    try:
        raw = A.build(path, 1)
        assert raw is not None
        ours = next(c for b in raw["blocks"] for ln in b["lines"] for sp in ln["spans"] for c in sp["chars"] if c["c"] == "R")
        doc = pymupdf.open(path)
        try:
            theirs = next(c for b in doc[0].get_text("rawdict")["blocks"] for ln in b.get("lines", [])
                          for sp in ln["spans"] for c in sp["chars"] if c["c"] == "R")
        finally:
            doc.close()
        assert ours["origin"][0] == pytest.approx(theirs["origin"][0], abs=0.05), (ours["origin"], theirs["origin"])
        assert ours["origin"][1] == pytest.approx(theirs["origin"][1], abs=0.05), (ours["origin"], theirs["origin"])
    finally:
        render.close_documents()
        os.unlink(path)


_SUBSET_PAGE = os.path.join("bench", "data", "olmocr-bench", "bench_data", "pdfs", "tables",
                            "6767787c7d1b64b777ddab83e3e88569ae24_pg1.pdf")


@pytest.mark.skipif(not os.path.exists(_SUBSET_PAGE), reason="benchmark page not present")
def test_font_names_carry_no_subset_tag_as_mupdf_names_them():
    """PDFium reports an embedded subset's tag in the font's name ("ABCDEE+Calibri", 214
    characters of 6767787c) beside the plain "Calibri" of the rest; MuPDF folds the tag away
    and sees one font. Two fonts where MuPDF sees one turned two side-by-side course tables
    into a single six-column one downstream (one check). The names the reader reports are the
    set MuPDF reports."""
    raw = A.build(_SUBSET_PAGE, 1)
    assert raw is not None
    # spans that hold text: a span of made-up blanks has no font of its own in either reader
    ours = {sp["font"] for b in raw["blocks"] for ln in b["lines"] for sp in ln["spans"]
            if any(not c["c"].isspace() for c in sp["chars"])}
    assert not any("+" in name for name in ours), ours
    doc = pymupdf.open(_SUBSET_PAGE)
    try:
        theirs = {sp["font"] for b in doc[0].get_text("rawdict")["blocks"] for ln in b.get("lines", []) for sp in ln["spans"]
                  if any(not c["c"].isspace() for c in sp["chars"])}
    finally:
        doc.close()
    assert ours == theirs, (ours, theirs)


_ACCENT_PAGE = os.path.join("bench", "data", "olmocr-bench", "bench_data", "pdfs", "multi_column",
                            "031a888e402c82517f213222ae97147dd7dc_page_3_pg1.pdf")


def _accented_words(reader: str) -> set:
    """The words holding a letter beyond ASCII, read through one library or the other."""
    from truedoc.extract.textlayer import extract_page
    keys = ("TRUEDOC_READER", "TRUEDOC_RENDERER", "TRUEDOC_OBJECTS")
    was = {k: os.environ.get(k) for k in keys}
    os.environ.update({"TRUEDOC_READER": "pdftext" if reader == "pdfium" else "mupdf",
                       "TRUEDOC_RENDERER": reader, "TRUEDOC_OBJECTS": reader})
    doc = pymupdf.open(_ACCENT_PAGE)
    try:
        page = extract_page(doc[0], 1)
        words = {w.text.strip(".,;:()") for ln in page.lines for w in ln.words}
    finally:
        render.close_documents()
        doc.close()
        for k, v in was.items():
            os.environ.pop(k, None)
            if v is not None:
                os.environ[k] = v
    return words


def _accent_words(words: set) -> tuple[set, set]:
    """(words holding an accented Latin letter - one with a canonical decomposition, so not a
    Greek letter of the maths - , words holding a spacing accent left on its own)."""
    import unicodedata
    accented = {w for w in words if any(ch.isalpha() and unicodedata.decomposition(ch) for ch in w)}
    stranded = {w for w in words if any(ch in "ˆ˜´¨¸˚¯ˇ˘˙˝" for ch in w)}
    return accented, stranded


@pytest.mark.skipif(not os.path.exists(_ACCENT_PAGE), reason="benchmark page not present")
def test_a_loose_accent_pdfium_strands_goes_back_before_its_letter():
    """TeX's accent command draws an accent as a glyph of its own. MuPDF orders it just before
    the letter it covers ("Radioˇzurn´al") and the text layer composes the pair; PDFium emits
    it several characters later - after "Radio", or at the end of the line - so the line
    splitter cut it off as a line of its own and "Radiožurnál" and "Český" never formed
    (031a888e, one check; 153 such accents over the benchmark). The accented words both
    readers produce on that page are the same words."""
    ours, ours_left = _accent_words(_accented_words("pdfium"))
    theirs, theirs_left = _accent_words(_accented_words("mupdf"))
    assert {"Radiožurnál", "Český"} <= theirs, theirs
    assert ours == theirs, (sorted(ours - theirs), sorted(theirs - ours))
    assert ours_left <= theirs_left, sorted(ours_left - theirs_left)


_STYLE_PAGE = os.path.join("bench", "data", "olmocr-bench", "bench_data", "pdfs", "multi_column",
                           "0be9ba925bc2e3164ce649b02e3e29a07239_page_5_pg1.pdf")


@pytest.mark.skipif(not os.path.exists(_STYLE_PAGE), reason="benchmark page not present")
def test_a_fonts_bold_and_italic_match_mupdf_when_its_name_says_nothing():
    """0be9ba92 page 5 sets its heading in "CIDFont+F2" and "CIDFont+F3" and its species names in
    "CIDFont+F5": names that say nothing and descriptors with no style bits. MuPDF reads F2 as bold,
    F3 as bold italic and F5 as italic from the fonts' own programs; the reader read all three
    plain, the heading lost its bold and the page's column order changed (one check)."""
    import collections

    def styles(spans_by_block):
        out = collections.defaultdict(set)
        for b in spans_by_block:
            for ln in b.get("lines", []):
                for sp in ln["spans"]:
                    if any(not c["c"].isspace() for c in sp["chars"]):
                        out[sp["font"]].add((bool(sp["flags"] & 16), bool(sp["flags"] & 2)))
        return out

    raw = A.build(_STYLE_PAGE, 1)
    assert raw is not None
    ours = styles(raw["blocks"])
    doc = pymupdf.open(_STYLE_PAGE)
    try:
        theirs = styles(doc[0].get_text("rawdict")["blocks"])
    finally:
        doc.close()
    for font in ("CIDFont+F2", "CIDFont+F3", "CIDFont+F5"):
        assert ours[font] == theirs[font], (font, ours[font], theirs[font])
