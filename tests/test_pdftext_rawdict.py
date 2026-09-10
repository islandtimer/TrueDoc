"""The PDFium reader adapter (M18, D007): the parts that were measured wrong before they were right.

Each test here stands for a defect found by measuring the adapter against PyMuPDF on real pages:
coordinates rotated twice, font flags read with the wrong bit meanings, a baseline guessed when it
could be read, and whole visual rows arriving as single lines so no table could be found in them.
"""

import math

from truedoc.extract import pdftext_rawdict as A


def _span(chars, size=10.0, font="Test", flags=0):
    return {"font": font, "size": size, "flags": flags, "color": 0, "chars": chars}


def _char(text, x0, x1, y0=0.0, y1=10.0):
    return {"c": text, "bbox": (x0, y0, x1, y1), "origin": (x0, y1), "ink": None,
            "generated": False, "map_error": False}


# --- line splitting -------------------------------------------------------------------

def test_a_table_row_is_cut_into_its_cells():
    """pdftext hands back "Jagger 23.0 Jagger 23.6" as one line; the column finder needs the cells."""
    chars = [_char("A", 0, 10), _char(" ", 10, 14), _char("B", 90, 100)]
    pieces = A._split_at_gaps([_span(chars)])
    assert len(pieces) == 2, pieces
    assert "".join(c["c"] for c in pieces[0][0]["chars"]) == "A"
    assert "".join(c["c"] for c in pieces[1][0]["chars"]) == "B"


def test_ordinary_word_spacing_is_not_a_cut():
    chars = [_char("A", 0, 10), _char(" ", 10, 14), _char("B", 14, 24)]
    assert len(A._split_at_gaps([_span(chars)])) == 1


def test_a_type_3_font_reporting_size_one_does_not_shatter_the_line():
    """The real defect: pdftext reports the font matrix scale (1.0) as the size for some fonts,
    which made a 1.5x threshold 1.5pt wide and split between almost every letter."""
    chars = [_char("A", 0, 10), _char("n", 12, 22), _char("n", 24, 34)]
    assert len(A._split_at_gaps([_span(chars, size=1.0)])) == 1


def test_the_gap_is_measured_along_the_line_not_across_the_page():
    """On a rotated page text runs down the page, so a sideways rule would never find the gap."""
    down = [{"c": "A", "bbox": (0, 0, 10, 10), "origin": (0, 10), "ink": None, "generated": False, "map_error": False},
            {"c": "B", "bbox": (0, 90, 10, 100), "origin": (0, 100), "ink": None, "generated": False, "map_error": False}]
    assert len(A._split_at_gaps([_span(down)], (1.0, 0.0))) == 1      # nothing apart sideways
    assert len(A._split_at_gaps([_span(down)], (0.0, 1.0))) == 2      # far apart along the line


def test_splitting_can_be_turned_off():
    chars = [_char("A", 0, 10), _char("B", 900, 910)]
    assert len(A._split_at_gaps([_span(chars)])) == 2
    import os
    os.environ["TRUEDOC_LINE_GAP"] = "0"
    try:
        assert len(A._split_at_gaps([_span(chars)])) == 1
    finally:
        del os.environ["TRUEDOC_LINE_GAP"]


# --- font flags -----------------------------------------------------------------------

def test_pdfium_serif_is_not_pymupdf_italic():
    """PDFium's 0x2 is Serif and PyMuPDF's 0x2 is italic; passing one through as the other made
    every serif face italic."""
    assert A._mupdf_flags({"flags": 0x2, "name": "Times", "weight": 400}, False) & 2 == 0
    assert A._mupdf_flags({"flags": 0x2, "name": "Times", "weight": 400}, False) & 4 == 4


def test_italic_comes_from_the_italic_bit_or_the_name():
    assert A._mupdf_flags({"flags": 0x40, "name": "X", "weight": 400}, False) & 2
    assert A._mupdf_flags({"flags": 0, "name": "Arial-Oblique", "weight": 400}, False) & 2


def test_bold_comes_from_the_name_not_the_weight():
    """PDFium's weight is the descriptor's stem width in disguise: 640-820 on every TeX face, so a
    weight rule made whole arXiv pages bold and their run-in theorem headings into headings.
    Measured against MuPDF's flag over 7,469 (page, font) pairs, the name disagrees on 369 and a
    weight of 600 on 2,265."""
    assert not A._mupdf_flags({"flags": 0, "name": "CMR12", "weight": 732}, False) & 16
    assert not A._mupdf_flags({"flags": 0, "name": "CMTI12", "weight": 800}, False) & 16
    assert A._mupdf_flags({"flags": 0, "name": "Arial-BoldMT", "weight": 400}, False) & 16
    assert A._mupdf_flags({"flags": 0, "name": "ABCDEF+Frutiger-SemiBold", "weight": 400}, False) & 16
    assert A._mupdf_flags({"flags": 0x40000, "name": "X", "weight": 400}, False) & 16      # the descriptor's ForceBold


def test_texs_bold_faces_are_bold():
    """MuPDF calls CMBX bold when the embedded program says so, which PDFium cannot report; the
    name is what can be seen, and it settles more pages than it loses (273 disagreements against
    369 without it)."""
    for name in ("CMBX12", "ABCDEF+CMBX10", "CMMIB10", "CMBSY10", "SFBX1200"):
        assert A._mupdf_flags({"flags": 0, "name": name, "weight": 500}, False) & 16, name
    for name in ("CMR10", "CMSY10", "MSBM10", "CMTI10", "Stag-Black"):
        assert not A._mupdf_flags({"flags": 0, "name": name, "weight": 700}, False) & 16, name


def test_fixed_pitch_is_mono():
    assert A._mupdf_flags({"flags": 0x1, "name": "Courier", "weight": 400}, False) & 8


# --- direction and coordinates --------------------------------------------------------

def _run(angles, blanks=()):
    """A run of characters with the given PDFium angles; `blanks` are indices that are
    made-up spaces (level, whatever the text is)."""
    chars = [{"char": " " if i in blanks else "x", "char_idx": i} for i in range(len(angles))]
    geom = {i: {"angle": a, "generated": i in blanks} for i, a in enumerate(angles)}
    return chars, geom


def test_level_text_reads_left_to_right():
    assert A._line_dir(*_run([0.0, 0.0, 0.0])) == (1.0, 0.0)


def test_the_direction_is_cos_sin_of_pdfiums_angle():
    """Measured against MuPDF's `dir` (test_pdftext_maths_pages pins the same on real pages):
    4.71 is text running up the page, (0, -1); 1.57 runs down it; 3.14 is upside down."""
    dx, dy = A._line_dir(*_run([3 * math.pi / 2] * 4))
    assert abs(dx) < 1e-6 and abs(dy + 1.0) < 1e-6
    dx, dy = A._line_dir(*_run([math.pi / 2] * 4))
    assert abs(dx) < 1e-6 and abs(dy - 1.0) < 1e-6
    dx, dy = A._line_dir(*_run([math.pi] * 4))
    assert abs(dx + 1.0) < 1e-6 and abs(dy) < 1e-6


def test_made_up_blanks_do_not_vote_on_the_direction():
    """PDFium's invented spaces are level whatever the text around them is; a turned line with
    three of them is still a turned line."""
    chars, geom = _run([3 * math.pi / 2, 0.0, 3 * math.pi / 2, 0.0, 0.0, 3 * math.pi / 2], blanks=(1, 3, 4))
    dx, dy = A._line_dir(chars, geom)
    assert abs(dx) < 1e-6 and abs(dy + 1.0) < 1e-6


def test_pdf_space_is_flipped_about_the_crop_box():
    """PDFium measures up from the bottom left, PyMuPDF down from the top left of the crop box."""
    assert A._flip(10.0, 700.0, 20.0, 690.0, 0.0, 800.0) == (10.0, 100.0, 20.0, 110.0)


def test_the_flip_survives_a_shifted_crop_box():
    assert A._flip(30.0, 700.0, 40.0, 690.0, 20.0, 800.0) == (10.0, 100.0, 20.0, 110.0)


# --- what MuPDF would have delivered --------------------------------------------------

def test_tex_symbol_font_codes_become_the_symbols_mupdf_names():
    """PDFium hands back a cmsy glyph's code as a letter - "k" for the parallel sign - where MuPDF
    resolves the glyph name. Run 66 lost 91 arXiv checks to the maths rebuild never seeing a symbol."""
    assert A._tex_symbol("CMSY10", "k") == "∥"
    assert A._tex_symbol("CMSY10", "h") == "⟨" and A._tex_symbol("CMSY10", "i") == "⟩"
    assert A._tex_symbol("CMSY7", "\x14") == "≤"
    assert A._tex_symbol("CMMI10", "`") == "ℓ"
    assert A._tex_symbol("CMMI10", "\x0b") == "α"


def test_real_letters_and_other_fonts_are_left_alone():
    assert A._tex_symbol("CMMI10", "x") is None          # an italic x is an x
    assert A._tex_symbol("CMSY10", "A") is None          # calligraphic A arrives as "A" both ways
    assert A._tex_symbol("Helvetica", "k") is None
    assert A._as_mupdf_would("k", "Helvetica", {"map_error": True}) == "k"


def test_the_table_is_only_consulted_where_pdfium_reports_the_mapping_broken():
    assert A._as_mupdf_would("k", "CMSY10", {"map_error": False}) == "k"
    assert A._as_mupdf_would("k", "CMSY10", {"map_error": True}) == "∥"


def _glyph(w, h, rise, size=10.0):
    """A control character whose ink is `w` by `h` em, centred `rise` em above the baseline."""
    return {"size": size, "origin": (0.0, 100.0), "map_error": False,
            "ink": (0.0, 100.0 - (rise + h / 2) * size, w * size, 100.0 - (rise - h / 2) * size)}


def test_a_control_code_drawn_as_a_short_bar_is_a_hyphen():
    """Measured on an AdvTT subset and on CMR12: 0.26-0.32 em wide, 0.05-0.08 em tall, a quarter
    em up. Every end-of-line hyphen on such a page arrives as U+0002 and no broken word rejoins."""
    assert A._as_mupdf_would("\x02", "AdvTT31ea7dbe", _glyph(0.30, 0.07, 0.25)) == "-"
    assert A._as_mupdf_would("\x02", "CMR12", _glyph(0.26, 0.05, 0.22)) == "-"


def test_other_control_codes_keep_their_shape():
    """U+0002 is PDFium's hyphen marker and needs no shape; any other control code is a raw
    glyph code, a hyphen only when it is drawn as one."""
    assert A._as_mupdf_would("\x03", "X", _glyph(0.30, 0.07, 0.25)) == "-"        # a short bar a quarter em up
    assert A._as_mupdf_would("\x03", "X", _glyph(0.30, 0.07, 0.0)) == "\x03"     # on the baseline: an underscore
    assert A._as_mupdf_would("\x03", "X", _glyph(0.30, 0.60, 0.25)) == "\x03"    # tall: not a bar
    assert A._as_mupdf_would("\x03", "X", _glyph(0.90, 0.07, 0.25)) == "\x03"    # wide: a rule, not a hyphen
    assert A._as_mupdf_would("-", "X", _glyph(0.30, 0.07, 0.25)) == "-"          # a real hyphen is untouched
    assert A._as_mupdf_would(" ", "X", None) == " "


# --- the switch -----------------------------------------------------------------------

def test_the_reader_is_off_unless_asked_for():
    import os
    was = os.environ.pop("TRUEDOC_READER", None)
    try:
        assert not A.enabled()
        os.environ["TRUEDOC_READER"] = "pdftext"
        assert A.enabled()
    finally:
        os.environ.pop("TRUEDOC_READER", None)
        if was is not None:
            os.environ["TRUEDOC_READER"] = was


def test_pdfiums_hyphenation_marker_is_a_hyphen():
    """PDFium hands over U+0002 for a hyphen it recognised at a line end. Measured over the
    benchmark: MuPDF reads a hyphen at 4,033 of the 4,915 such characters, and a Type 3 font's
    glyph box defeats the shape test, so the marker itself is the evidence."""
    assert A._as_mupdf_would("\x02", "T15", {"map_error": False, "ink": None}) == "-"
    # ... unless PDFium says the character never mapped at all: then the code is a raw glyph code
    assert A._as_mupdf_would("\x02", "Advt93-r", {"map_error": True, "ink": None}) == "\x02"


def test_ams_symbol_font_codes_become_the_symbols_mupdf_reads():
    """msam's leqslant sits at code 0x36 ("6"), lesssim at 0x2E ("."), msbm's hslash at 0x7E.
    Measured by position against MuPDF over the 75 benchmark pages that use these fonts."""
    assert A._tex_symbol("MSAM10", "6") == "⩽"
    assert A._tex_symbol("MSAM10", ".") == "≲"
    assert A._tex_symbol("MSAM7", ">") == "⩾"
    assert A._tex_symbol("MSBM10", "~") == "ℏ"
    assert A._tex_symbol("MSAM10", "9") is None      # MuPDF leaves this one raw too


def test_a_pen_that_jumps_backwards_starts_a_new_line():
    """A table row drawn right to left - the cells "0.658", "0.77", "0.31" in that order, each
    to the left of the last - is three lines to MuPDF and was one line, read backwards, here.
    Kerning pulls a glyph back a fraction of an em; half an em is a jump."""
    row = [_char("C", 300, 306), _char("B", 200, 206), _char("A", 100, 106)]
    pieces = A._split_at_gaps([_span(row)])
    assert ["".join(c["c"] for c in p[0]["chars"]) for p in pieces] == ["C", "B", "A"], pieces
    kerned = [_char("T", 0, 7), _char("o", 5.5, 11)]        # a kerned pair overlaps, and stays
    assert len(A._split_at_gaps([_span(kerned)])) == 1
