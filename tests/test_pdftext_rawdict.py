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
    """On a rotated page text runs down the page, so a sideways rule would never find the gap.
    (The level case sits the second glyph a third of an em lower, not nine ems: nine ems down
    is another line by the baseline rule, whatever the direction.)"""
    near = [{"c": "A", "bbox": (0, 0, 10, 10), "origin": (0, 10), "ink": None, "generated": False, "map_error": False},
            {"c": "B", "bbox": (0, 3, 10, 13), "origin": (0, 13), "ink": None, "generated": False, "map_error": False}]
    down = [{"c": "A", "bbox": (0, 0, 10, 10), "origin": (0, 10), "ink": None, "generated": False, "map_error": False},
            {"c": "B", "bbox": (0, 90, 10, 100), "origin": (0, 100), "ink": None, "generated": False, "map_error": False}]
    assert len(A._split_at_gaps([_span(near)], (1.0, 0.0))) == 1      # nothing apart sideways
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

def test_the_reader_is_on_unless_asked_off():
    """The default since run 71 (D023): 84.0 with every PDFium switch on, level with the MuPDF
    run overall and above it on the held-out fifth. `TRUEDOC_READER=mupdf` reads the old way."""
    import os
    was = os.environ.pop("TRUEDOC_READER", None)
    try:
        assert A.enabled()
        os.environ["TRUEDOC_READER"] = "pdftext"
        assert A.enabled()
        os.environ["TRUEDOC_READER"] = "mupdf"
        assert not A.enabled()
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


def test_a_gap_at_a_text_object_boundary_ends_the_line_at_a_smaller_width():
    """MuPDF follows the file's text-showing runs: a table row drawn as two runs with a 1.1-em
    gap between them ("Listening to speech or lecture" then "118") is two lines to it and one
    row to pdftext, and the column finder then read one cell (5bdc8382, 105e91a0). A gap at a
    run boundary ends the line at the object-gap threshold; the same gap inside one run does not."""
    import os
    a = dict(_char("A", 0, 10), order=1)
    b = dict(_char("B", 18, 28), order=2)          # 0.8 em on, in another text object
    same = dict(_char("B", 18, 28), order=1)       # the same gap inside one object
    os.environ["TRUEDOC_OBJECT_GAP"] = "0.6"
    try:
        assert len(A._split_at_gaps([_span([a, b])])) == 2
        assert len(A._split_at_gaps([_span([a, same])])) == 1
        os.environ["TRUEDOC_OBJECT_GAP"] = "0"
        assert len(A._split_at_gaps([_span([a, b])])) == 1      # off: only the 1.5-em rule
    finally:
        del os.environ["TRUEDOC_OBJECT_GAP"]


def test_a_blank_pdfium_invents_beside_a_dash_between_digits_is_dropped():
    """PDFium invents a blank at a tenth of an em after the en dash of "1726–1728", where MuPDF's
    own blanks start at 0.16 em; the page then read "1726– 1728". A range of numbers has no blank
    at its dash. Any other invented blank stays: dropping every one in a narrow gap was measured
    and cost five gate checks on a tightly set page whose word gaps are narrower than that."""
    dash = [_char("6", 0, 4), _char("–", 4.5, 8), dict(_char(" ", 8.5, 8.5), generated=True), _char("1", 8.8, 12)]
    words = [_char("t", 0, 4), dict(_char(" ", 4.5, 4.5), generated=True), _char("2", 4.8, 8)]
    drawn = [_char("6", 0, 4), _char("–", 4.5, 8), _char(" ", 8.5, 8.5), _char("1", 8.8, 12)]
    for chars, kept in ((dash, "6–1"), (words, "t 2"), (drawn, "6– 1")):
        spans = [_span(chars)]
        A._drop_tight_blanks(spans, (1.0, 0.0))
        assert "".join(c["c"] for sp in spans for c in sp["chars"]) == kept, (chars, kept)


def test_the_join_refuses_a_run_that_starts_an_em_past_the_line():
    """PDFium ends a line where the next run starts far to the right. On a page with a 44pt drop
    cap (0e5f0c34) the first line of column one and the line of column two, on the same baseline
    1.44 em apart across the gutter, were welded into one line and the column finder lost the
    page. A run within an em of the line's end still joins (a word torn at a superscript); one
    beyond it is the next thing on the page. Off with the object-gap knob at 0."""
    import os
    prev = [_span([_char("i", 0, 4), _char("s", 4, 8)])]
    near = [_span([_char("m", 11, 18)])]           # 0.3 em on, the same baseline
    far = [_span([_char("m", 22, 29)])]            # 1.4 em on, the same baseline
    level = (1.0, 0.0)
    was = os.environ.pop("TRUEDOC_OBJECT_GAP", None)
    try:
        assert A._continues(prev, near, level)
        assert not A._continues(prev, far, level)
        os.environ["TRUEDOC_OBJECT_GAP"] = "0"
        assert A._continues(prev, far, level)
    finally:
        os.environ.pop("TRUEDOC_OBJECT_GAP", None)
        if was is not None:
            os.environ["TRUEDOC_OBJECT_GAP"] = was


def test_where_pdfium_ended_the_line_an_em_of_space_is_a_cut():
    """pdftext regroups characters by the band they overlap, so a 44pt drop cap's band took in the
    first line of column one and the line of column two beside it (0e5f0c34), 1.44 em apart -
    under the 1.5-em rule, and in one text object, so the run rule could not see it. PDFium had
    ended its own line at the gutter (a generated CR LF, remembered on the character before it);
    where it stopped and an em of space follows, the line is cut. The same gap with no line end
    stays, as before."""
    import os
    a = dict(_char("s", 0, 10), line_end=True)
    b = _char("m", 24, 34)                          # 1.4 em on, one text object
    plain = _char("s", 0, 10)
    was = os.environ.pop("TRUEDOC_OBJECT_GAP", None)
    try:
        assert len(A._split_at_gaps([_span([a, b])])) == 2
        assert len(A._split_at_gaps([_span([plain, b])])) == 1
        os.environ["TRUEDOC_OBJECT_GAP"] = "0"
        assert len(A._split_at_gaps([_span([a, b])])) == 1
    finally:
        os.environ.pop("TRUEDOC_OBJECT_GAP", None)
        if was is not None:
            os.environ["TRUEDOC_OBJECT_GAP"] = was


def test_a_baseline_an_em_away_starts_a_line_as_it_does_for_mupdf():
    """pdftext groups characters by the band they overlap, so a 44pt drop cap whose baseline
    sits 24pt below the text's went into the first line of its column (0e5f0c34): the line stood
    45pt tall, overlapped the neighbouring column's line, the two were joined downstream and the
    page's columns were lost. MuPDF sets the drop cap on a line of its own. A script steps a
    third to a half of an em and stays."""
    cap = {"c": "H", "bbox": (0, 0, 36, 45), "origin": (0, 34), "ink": None, "generated": False, "map_error": False}
    text = [_char(ch, 40 + 5 * k, 45 + 5 * k, 12, 22) for k, ch in enumerate("yperkal")]   # baseline 22, 12pt below
    assert len(A._split_at_gaps([_span([cap] + text)])) == 2
    script = [_char("x", 0, 10), dict(_char("2", 10, 15, -4, 6))]        # a superscript, 0.4 em up
    assert len(A._split_at_gaps([_span(script)])) == 1
    # a wrapped tail of six glyphs, four of them scripts (2503.06293): the text's size is the
    # yardstick, not the scripts', and the 0.7-em swing from a superscript to a subscript stays
    tail = [_char("χ", 0, 6), _char("-", 6, 9, -4, 6), _char("2", 9, 12, 3, 13), _char(",", 12, 14, 3, 13),
            _char("5", 14, 17, 3, 13), _char(".", 17, 20)]
    assert len(A._split_at_gaps([_span(tail)])) == 1


def test_a_list_marker_keeps_its_item_across_the_object_gap():
    """Word sets a numbered list's marker as a text object of its own, an em before its text
    ("1." then "Specific program requirements", 6767787c). The object-gap rule cut the marker
    off, the markers then stood as a column of their own, and the whitespace-table finder grew
    one eight-column table over the whole section. MuPDF keeps each item as one line. A short
    marker - a number or letter with its dot or bracket, or a bullet - stays with the text
    that follows within the general gap limit; a table row's first cell is not a marker."""
    import os
    marker = dict(_char("1", 0, 5), order=1); dot = dict(_char(".", 5, 8), order=1)
    text = [dict(_char(ch, 18 + 5 * k, 23 + 5 * k), order=2) for k, ch in enumerate("Specific")]
    cell = [dict(_char(ch, 0 + 5 * k, 5 + 5 * k), order=1) for k, ch in enumerate("Listening")]
    number = [dict(_char(ch, 56 + 5 * k, 61 + 5 * k), order=2) for k, ch in enumerate("118")]
    was = os.environ.pop("TRUEDOC_OBJECT_GAP", None)
    try:
        assert len(A._split_at_gaps([_span([marker, dot] + text)])) == 1
        assert len(A._split_at_gaps([_span(cell + number)])) == 2
    finally:
        if was is not None:
            os.environ["TRUEDOC_OBJECT_GAP"] = was
