"""A private-use character is read by what its font draws.

A code in Unicode's private-use area carries no meaning of its own. RAC's 2021 premium, excess and discount guides tick
every pricing factor with FontAwesome's check, U+F00C, and an RAA landlord policy bullets a list inside a table cell
with a Wingdings square; both were stripped with the raw glyph codes, so the pricing table's columns came out empty and
the list ran on as one line. The glyph tests embed a small TrueType font whose private-use codes draw shapes, set the
codes on a page with PyMuPDF, and read the page. A glyph's mark must stand alone in its box; a dot, a square or a box
must be as wide at each height as at its mirror height - Suncorp's and Apia's flow arrows read as a cross and a dot;
only a glyph's tick is given room for strokes heavy enough to carry into its upper-left quarter; a mark read alone on
its line starts the words beside it; and a font that spells words with its private-use codes is not read at all.
"""
import math

import pymupdf
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen

from truedoc.extract.textlayer import extract_page
from truedoc.marks import _same_upside_down, classify_mark
from truedoc.model import BBox

TICK = [(60, 430), (190, 560), (380, 370), (830, 820), (960, 690), (380, 110)]
# FontAwesome's check as RAC's guides draw it, traced from its ink: strokes so heavy they carry into the upper-left
# quarter where they meet.
HEAVY_TICK = [(820, 900), (980, 732), (400, 102), (20, 501), (180, 690), (380, 480)]
SQUARE = [(300, 250), (300, 650), (700, 650), (700, 250)]
LEFT_TRIANGLE = [(150, 450), (850, 850), (850, 50)]

# The reader's ink grids, as it took them from the pages: Apia's 2012 landlord PDS, page 51, sets its flow arrows in
# Wingdings 3 (U+F0C8), a shaft standing on a head; Suncorp's contents PDS, page 51, bullets sub-items in Wingdings 2.
APIA_ARROW = [
    "..........############..........",
    "..........############..........",
    "..........############..........",
    "..........############..........",
    "..........############..........",
    "..........############..........",
    "..........############..........",
    "..........############..........",
    ".....#####################......",
    ".....#####################......",
    ".......##################.......",
    "........################........",
    ".........#############..........",
    "..........###########...........",
    "...........#########............",
    ".............######.............",
    "..............###...............",
    "...............#................",
]
SUNCORP_BULLET = [
    "..............####..............",
    "...........##########...........",
    ".........##############.........",
    "........################........",
    ".......##################.......",
    ".......##################.......",
    ".......##################.......",
    "........################........",
    "........###############.........",
    ".........#############..........",
    "............########............",
]


def _grid(rows):
    above = (32 - len(rows)) // 2
    blank = "." * 32
    lines = [blank] * above + rows + [blank] * (32 - above - len(rows))
    return [[1 if ch == "#" else 0 for ch in line] for line in lines]


def _disc(cx, cy, r, sides=24):
    return [(round(cx + r * math.cos(2 * math.pi * i / sides)), round(cy + r * math.sin(2 * math.pi * i / sides)))
            for i in range(sides)]


def _font(path, outlines, advance):
    """A TrueType font whose private-use codes draw the outlines given: {code: outline}."""
    names = {code: f"g{i}" for i, code in enumerate(outlines)}
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
    builder.setupNameTable({"familyName": "TestIcons", "styleName": "Regular"})
    builder.setupOS2(sTypoAscender=900, sTypoDescender=-100, usWinAscent=900, usWinDescent=100)
    builder.setupPost()
    builder.save(str(path))
    return str(path)


def _extract(tmp_path, doc):
    path = tmp_path / "glyphs.pdf"
    doc.save(str(path))
    doc.close()
    doc = pymupdf.open(str(path))
    try:
        return extract_page(doc[0], 1)
    finally:
        doc.close()


def _read(tmp_path, code, outline, words_after="", advance=1000, gap=6.0, size=12):
    font = _font(tmp_path / "icons.ttf", {code: outline}, advance)
    doc = pymupdf.open()
    page = doc.new_page(width=300, height=200)
    page.insert_font(fontname="icons", fontfile=font)
    page.insert_text((40, 100), chr(code), fontname="icons", fontsize=size)
    if words_after:
        # the words start `gap` points after the glyph's advance
        page.insert_text((40 + size * advance / 1000 + gap, 100), words_after, fontsize=10)
    return _extract(tmp_path, doc)


def test_a_private_use_glyph_that_draws_a_tick_is_a_tick(tmp_path):
    page = _read(tmp_path, 0xF00C, TICK)
    assert [c.text for c in page.chars] == ["✓"]


def test_a_heavy_tick_is_a_tick(tmp_path):
    page = _read(tmp_path, 0xF00C, HEAVY_TICK)
    assert [c.text for c in page.chars] == ["✓"]


def test_a_private_use_bullet_leads_its_line_as_the_mark_it_draws(tmp_path):
    page = _read(tmp_path, 0xF0A7, SQUARE, "caused by rain, hail or wind")
    assert page.lines[0].text.startswith("■ caused by rain"), page.lines[0].text


def test_a_bullet_in_a_box_as_tall_as_its_line_is_a_dot(tmp_path):
    # Symbol's bullet, U+F0B7, comes in a box a third as wide as it is tall.
    page = _read(tmp_path, 0xF0B7, _disc(230, 400, 200), "the loss or damage", advance=460)
    assert page.lines[0].text.startswith("● the loss"), page.lines[0].text


def test_a_bullet_set_well_before_its_words_starts_their_line(tmp_path):
    # RACQ's supplementary PDS sets each Symbol bullet 13pt before its words, and the text layer gives the two as
    # separate lines: every bullet came out as an empty list item above its words.
    page = _read(tmp_path, 0xF0B7, _disc(230, 400, 200), "Mobile Phones;", advance=460, gap=13.4, size=10)
    assert [line.text for line in page.lines] == ["● Mobile Phones;"]


def test_a_private_use_glyph_the_reader_cannot_name_as_a_mark_stays_as_it_was(tmp_path):
    # CGU's page links point with a solid triangle: an arrow is a question of reading order, not a mark to write.
    page = _read(tmp_path, 0xE04F, LEFT_TRIANGLE)
    assert [c.text for c in page.chars] == [chr(0xE04F)]


def test_a_font_that_spells_words_with_its_private_use_codes_is_not_read(tmp_path):
    # txfonts' small capitals sit in the private-use area, every one inside a word; read one at a time, letters drawn
    # apart from their neighbours passed for boxes, crosses and ticks. Here the font spells a word of two of its codes,
    # and the one it also sets on its own is not read either.
    font = _font(tmp_path / "letters.ttf", {0xF761: SQUARE, 0xF762: TICK}, 1000)
    doc = pymupdf.open()
    page = doc.new_page(width=300, height=200)
    page.insert_font(fontname="letters", fontfile=font)
    page.insert_text((40, 100), chr(0xF761) + chr(0xF762), fontname="letters", fontsize=12)
    page.insert_text((40, 150), chr(0xF762), fontname="letters", fontsize=12)
    extracted = _extract(tmp_path, doc)
    assert [c.text for c in extracted.chars if c.bbox.y0 > 120] == [chr(0xF762)]


def test_a_glyph_is_not_read_where_other_drawing_reaches_its_box(tmp_path):
    # Suncorp's flow arrow, a triangle set in ZapfDingbats just above a rule, read with the rule as a cross. Two ticks,
    # the second with a rule inside the edge of its crop: read as glyphs, only the first is a mark.
    doc = pymupdf.open()
    page = doc.new_page(width=300, height=200)
    for x in (100, 200):
        page.draw_polyline([(x, 104), (x + 3.5, 108), (x + 10, 100)], color=(0, 0, 0), width=1.6)
    page.draw_line((190, 110.4), (220, 110.4), color=(0.1, 0.5, 0.4), width=0.8)
    path = tmp_path / "rule.pdf"
    doc.save(str(path))
    doc.close()
    doc = pymupdf.open(str(path))
    try:
        clear = classify_mark(doc[0], BBox(99, 98, 111, 110), glyph=True)
        ruled = classify_mark(doc[0], BBox(199, 98, 211, 110), glyph=True)
    finally:
        doc.close()
    assert clear is not None and clear.kind == "tick"
    assert ruled is None


def test_a_block_arrow_is_not_as_wide_at_each_height_as_its_mirror_and_a_bullet_is():
    # Read as a glyph, Apia's arrow came out as a dot in one render of its three.
    assert not _same_upside_down(_grid(APIA_ARROW))
    assert _same_upside_down(_grid(SUNCORP_BULLET))


def test_a_heavy_tick_is_given_its_room_only_as_a_glyph(tmp_path):
    # Given to drawn marks as well, two pieces of an Allianz illustration - a hand and a pen - read as ticks.
    doc = pymupdf.open()
    page = doc.new_page(width=300, height=200)
    page.draw_polyline([(100 + x * 0.012, 110 - y * 0.012) for x, y in HEAVY_TICK], color=None, fill=(0, 0, 0),
                       closePath=True)
    path = tmp_path / "heavy.pdf"
    doc.save(str(path))
    doc.close()
    doc = pymupdf.open(str(path))
    try:
        box = BBox(100, 99, 112, 109)
        drawn = classify_mark(doc[0], box)
        as_glyph = classify_mark(doc[0], box, glyph=True)
    finally:
        doc.close()
    assert drawn is None or drawn.kind != "tick"
    assert as_glyph is not None and as_glyph.kind == "tick"
