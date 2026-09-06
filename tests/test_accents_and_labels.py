"""Free-standing accent glyphs are composed with their letter; section numbers rejoin their headings."""

import re

import pymupdf

from truedoc.extract.textlayer import _compose_spacing_accents
from truedoc.model import BBox, Char
from truedoc.pipeline import ConvertOptions, convert


def _char(text, x0, x1, font="CMR10", size=10.0, y0=100.0, y1=110.0):
    return Char(text=text, bbox=BBox(x0, y0, x1, y1), font=font, size=size, origin_y=y1)


def test_accent_before_its_letter_is_composed():
    # TeX: the acute accent is drawn first, over the "o" that follows ("Ram´on").
    chars = [_char("R", 0, 7), _char("a", 7, 12), _char("m", 12, 20), _char("´", 22, 25, y0=97, y1=101), _char("o", 20, 25), _char("n", 25, 30)]
    assert "".join(c.text for c in _compose_spacing_accents(chars)) == "Ramón"


def test_accent_after_its_letter_is_composed():
    # Some producers draw the accent after the letter ("Geocieˆncias", "Evoluc¸a˜o").
    chars = [_char("c", 0, 5), _char("¸", 1, 4, y0=108, y1=112), _char("a", 5, 10), _char("˜", 6, 9, y0=97, y1=101), _char("o", 10, 15)]
    assert "".join(c.text for c in _compose_spacing_accents(chars)) == "ção"


def test_maths_accent_over_another_font_is_left_alone():
    # \hat{a}: the hat comes from the text font, the a from the maths italic font.
    chars = [_char("ˆ", 1, 4, font="CMR10", y0=96, y1=100), _char("a", 0, 5, font="CMMI10")]
    assert [c.text for c in _compose_spacing_accents(chars)] == ["ˆ", "a"]


def test_accent_not_over_a_letter_stays():
    chars = [_char("x", 0, 5), _char("¨", 12, 15), _char("y", 20, 25)]
    assert [c.text for c in _compose_spacing_accents(chars)] == ["x", "¨", "y"]


_OPTS = ConvertOptions(layout=False, math=False, marks=False, ocr=False, frontmatter=False)


def _page_with_heading(tmp_path, label, title, gap):
    doc = pymupdf.open()
    page = doc.new_page(width=400, height=300)
    page.insert_text((72, 100), label, fontname="hebo", fontsize=12)
    w = pymupdf.get_text_length(label, fontname="hebo", fontsize=12)
    page.insert_text((72 + w + gap, 100), title, fontname="hebo", fontsize=12)
    y = 124
    for t in ["We have presented total lightning characteristics over the region.", "The distribution is somewhat inhomogeneous across the area.", "Further work will extend the analysis to the whole decade."]:
        page.insert_text((72, y), t, fontname="helv", fontsize=10)
        y += 14
    p = tmp_path / "h.pdf"
    doc.save(str(p))
    return str(p)


def test_section_number_rejoins_its_title(tmp_path):
    md = convert(_page_with_heading(tmp_path, "VI.", "CONCLUSIONS", gap=10.0), _OPTS)
    assert re.search(r"^#+ VI\. CONCLUSIONS$", md, re.M), md


def test_decimal_number_rejoins_its_title(tmp_path):
    md = convert(_page_with_heading(tmp_path, "5.2.2", "Specific Heat", gap=9.0), _OPTS)
    assert re.search(r"^#+ 5\.2\.2 Specific Heat$", md, re.M), md


def test_far_apart_headings_stay_separate(tmp_path):
    md = convert(_page_with_heading(tmp_path, "3.", "Results", gap=60.0), _OPTS)
    assert not re.search(r"^#+ 3\. Results$", md, re.M), md
