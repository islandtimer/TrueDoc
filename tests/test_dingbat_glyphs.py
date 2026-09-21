"""A dingbat font's Latin letter is a code, not a letter: it is read by what the font draws.

Wingdings, Webdings, ZapfDingbats, Marlett and Monotype Sorts hold no letters at all. Australian Seniors' landlord PDS
bullets every item with Wingdings' "n", a filled square, and the letter is what reaches the reader: "n admit guilt,
fault or liability except to the police". Woolworths' target market determination uses Wingdings U+009F, which renders
as nothing at all, so its items lose their markers entirely. Over sixty documents of the owner's library, twelve pages
each: 242 such characters over 27 pages and seven distinct documents, every one opening a line.

The private-use rule already reads a glyph by its drawing; these join it. A character whose code is already a mark is
left alone, so a font that names its bullet correctly keeps what it says, and the Symbol family - which spells Greek
and maths - is not a dingbat font.
"""
import pymupdf
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen

from truedoc.extract.textlayer import _dingbat_font, extract_page
from tests.test_private_glyphs import SQUARE, TICK, _disc

BULLET = _disc(500, 450, 200)


def _font(path, outlines, family, advance=1000):
    """A TrueType font of the given family name whose codes draw the outlines given: {code: outline}."""
    names = {code: "g{}".format(i) for i, code in enumerate(outlines)}
    builder = FontBuilder(1000, isTTF=True)
    builder.setupGlyphOrder([".notdef"] + list(names.values()))
    builder.setupCharacterMap(names)
    glyphs = {".notdef": TTGlyphPen(None).glyph()}
    for code, outline in outlines.items():
        pen = TTGlyphPen(None)
        pen.moveTo(outline[0])
        for point in outline[1:]:
            pen.lineTo(point)
        pen.closePath()
        glyphs[names[code]] = pen.glyph()
    builder.setupGlyf(glyphs)
    builder.setupHorizontalMetrics({name: (advance if name != ".notdef" else 500, 0) for name in glyphs})
    builder.setupHorizontalHeader(ascent=900, descent=-100)
    builder.setupNameTable({"familyName": family, "styleName": "Regular"})
    builder.setupOS2(sTypoAscender=900, sTypoDescender=-100, usWinAscent=900, usWinDescent=100)
    builder.setupPost()
    builder.save(str(path))
    return str(path)


def _read(tmp_path, code, outline, family, words_after="", advance=1000, gap=6.0, size=12):
    font = _font(tmp_path / "ding.ttf", {code: outline}, family, advance)
    doc = pymupdf.open()
    page = doc.new_page(width=300, height=200)
    page.insert_font(fontname="ding", fontfile=font)
    page.insert_text((40, 100), chr(code), fontname="ding", fontsize=size)
    if words_after:
        page.insert_text((40 + size * advance / 1000 + gap, 100), words_after, fontsize=10)
    path = tmp_path / "ding.pdf"
    doc.save(str(path))
    doc.close()
    doc = pymupdf.open(str(path))
    try:
        return extract_page(doc[0], 1)
    finally:
        doc.close()


def test_a_wingdings_letter_that_draws_a_square_is_a_square(tmp_path):
    page = _read(tmp_path, ord("n"), SQUARE, "Wingdings-Regular")
    assert [c.text for c in page.chars] == ["■"]


def test_the_square_leads_the_words_it_marks(tmp_path):
    page = _read(tmp_path, ord("n"), SQUARE, "Wingdings", words_after="admit guilt, fault or liability")
    assert page.lines[0].text.startswith("■ admit guilt"), page.lines[0].text


def test_a_code_that_renders_as_nothing_is_read_from_its_drawing_too(tmp_path):
    """Woolworths' marker is Wingdings U+009F - a control code, invisible, and its items lost their markers."""
    page = _read(tmp_path, 0x9F, BULLET, "Wingdings-Regular", words_after="is tenanted or expected to be")
    assert page.lines[0].text.startswith("● is tenanted"), page.lines[0].text


def test_a_zapf_dingbats_letter_is_read_as_what_it_draws(tmp_path):
    page = _read(tmp_path, ord("4"), TICK, "ZapfDingbatsITC")
    assert [c.text for c in page.chars] == ["✓"]


def test_a_letter_in_an_ordinary_font_is_left_alone(tmp_path):
    page = _read(tmp_path, ord("n"), SQUARE, "Helvetica-Clone")
    assert [c.text for c in page.chars] == ["n"]


def test_a_character_that_is_already_a_mark_keeps_what_it_says(tmp_path):
    """SymbolMT names its bullet U+2022 and means it - 157 of them in the library sample. Nothing to re-read."""
    page = _read(tmp_path, 0x2022, TICK, "Wingdings-Regular")
    assert [c.text for c in page.chars] == ["•"]


def test_which_fonts_draw_symbols_and_which_spell():
    assert _dingbat_font("ABCDEF+Wingdings-Regular")
    assert _dingbat_font("Wingdings 2")
    assert _dingbat_font("ZapfDingbatsITC")
    assert _dingbat_font("Webdings")
    assert _dingbat_font("Monotype Sorts")
    # Symbol spells Greek and mathematics; its letters are letters.
    assert not _dingbat_font("SymbolMT")
    assert not _dingbat_font("Symbol")
    assert not _dingbat_font("Helvetica")


# Webdings' right-pointing triangle, as its font draws it: small and solid (drawn from webdings.ttf, 21 September 2026).
TRIANGLE = [(330, 200), (700, 450), (330, 700)]


def test_a_webdings_4_is_the_triangular_bullet_it_draws(tmp_path):
    """Budget Direct's home PDS of 2016 bullets its list with Webdings' "4", and it came out "4 INSURANCE CERTIFICATE".
    The glyph reader takes the triangle for an arrow head, which it does not write; the code names it (D013)."""
    page = _read(tmp_path, ord("4"), TRIANGLE, "Webdings", words_after="INSURANCE CERTIFICATE")
    assert page.lines[0].text.startswith("‣ INSURANCE CERTIFICATE"), page.lines[0].text


def test_the_triangle_is_named_whichever_way_the_text_layer_gives_its_code(tmp_path):
    page = _read(tmp_path, 0xF034, TRIANGLE, "Webdings")
    assert [c.text for c in page.chars] == ["‣"]


def test_the_triangle_is_named_even_where_its_item_reaches_into_its_box(tmp_path):
    """A storm exclusion's list: the item's first letter starts 1.1 points inside the bullet's box, and the glyph reader
    reads nothing where other ink reaches into a glyph's box. The code does not depend on the drawing."""
    page = _read(tmp_path, ord("4"), TRIANGLE, "Webdings", words_after="artificial grass or turf", gap=-1.1, size=10)
    assert [c.text for c in page.chars][0] == "‣"
    assert "4" not in "".join(l.text for l in page.lines)
    # and it stays a word of its own: the pass that joins touching pieces of one word made "‣artificial" of it
    assert [w.text for w in page.words][:2] == ["‣", "artificial"], [w.text for w in page.words]


def test_the_table_is_webdings_own(tmp_path):
    """Wingdings' "4" draws something else altogether; Webdings' codes name nothing in another font."""
    page = _read(tmp_path, ord("4"), TRIANGLE, "Wingdings-Regular")
    assert "‣" not in [c.text for c in page.chars]
