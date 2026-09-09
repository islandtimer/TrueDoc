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


def test_bold_comes_from_the_weight():
    assert A._mupdf_flags({"flags": 0, "name": "X", "weight": 700}, False) & 16
    assert not A._mupdf_flags({"flags": 0, "name": "X", "weight": 400}, False) & 16


def test_fixed_pitch_is_mono():
    assert A._mupdf_flags({"flags": 0x1, "name": "Courier", "weight": 400}, False) & 8


# --- direction and coordinates --------------------------------------------------------

def test_level_text_reads_left_to_right():
    assert A._line_dir({"rotation": 0.0}, 0) == (1.0, 0.0)


def test_a_rotated_page_is_not_rotated_twice():
    """pdftext turns its coordinates into display space and PyMuPDF does not, so the page
    rotation has to come back out or every box lands a median 210pt from where it belongs."""
    assert A._line_dir({"rotation": 0.0}, 90) == (0.0, -1.0)
    assert A._line_dir({"rotation": 0.0}, 180) == (-1.0, 0.0)
    assert A._line_dir({"rotation": 0.0}, 270) == (0.0, 1.0)


def test_text_set_at_an_angle_keeps_its_angle():
    dx, dy = A._line_dir({"rotation": math.pi / 2}, 0)
    assert abs(dx - 0.0) < 1e-6 and abs(dy + 1.0) < 1e-6


def test_pdf_space_is_flipped_about_the_crop_box():
    """PDFium measures up from the bottom left, PyMuPDF down from the top left of the crop box."""
    assert A._flip(10.0, 700.0, 20.0, 690.0, 0.0, 800.0) == (10.0, 100.0, 20.0, 110.0)


def test_the_flip_survives_a_shifted_crop_box():
    assert A._flip(30.0, 700.0, 40.0, 690.0, 20.0, 800.0) == (10.0, 100.0, 20.0, 110.0)


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
