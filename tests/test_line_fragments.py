"""A short lowercase fragment cut off the end of a line by a wide gap belongs to that line.

Justified text in a newspaper's narrow columns stretches a word gap far enough for the
segment splitter to take "from the" off the end of "A sweet domestic comedy from the"; the
fragment then became a heading of its own, placed after the paragraph (20_pg39, run 60). A
fragment of at most three words starting with a lowercase letter, on the baseline of a line
that ends without punctuation and within six ems of its end, is the rest of that line.
"""
from truedoc.model import BBox, Char, Line, Page, Word
from truedoc.segment.blocks import build_blocks


def _line(text, x0, y0, size=6.4, font="StRydeRegular"):
    cw = 0.45 * size
    chars = [Char(text=c, bbox=BBox(x0 + i * cw, y0, x0 + (i + 1) * cw, y0 + size), font=font, size=size, origin_y=y0 + 0.8 * size) for i, c in enumerate(text)]
    words = []
    x = x0
    for tok in text.split(" "):
        w = cw * len(tok)
        words.append(Word(text=tok, bbox=BBox(x, y0, x + w, y0 + size), chars=[c for c in chars if x <= c.bbox.x0 < x + w + 0.01]))
        x += w + cw
    return Line(words=words, bbox=BBox(x0, y0, x0 + cw * len(text), y0 + size))


def _page():
    page = Page(number=1, width=622, height=824)
    page.body_font_size = 6.4
    return page


def test_lowercase_fragment_on_the_same_baseline_rejoins_its_line():
    lines = [
        _line("(Andy Hamilton, Guy Jenkin, 2014)", 358, 136),
        _line("A sweet domestic comedy", 358, 143),
        _line("from the", 432, 143),
        _line("makers of the sitcom Outnumbered,", 358, 150),
        _line("viewed from the children's focus", 358, 157),
    ]
    blocks = build_blocks(_page(), lines)
    assert len(blocks) == 1, [[l.text for l in b.lines] for b in blocks]
    assert [l.text for l in blocks[0].lines][1] == "A sweet domestic comedy from the"


def test_table_cells_and_capitalised_segments_stay_apart():
    # A value two columns away, a segment starting with a capital, and a fragment after a
    # full stop are not the rest of the line.
    page = _page()
    a, b = _line("Body weight", 60, 100), _line("mg", 200, 100)          # 34 ems away
    assert len(build_blocks(page, [a, b])) == 2
    a, b = _line("A sweet domestic comedy", 358, 143), _line("The End", 432, 143)
    assert len(build_blocks(page, [a, b])) == 2
    a, b = _line("It was a sweet comedy.", 358, 143), _line("from the", 432, 143)
    assert len(build_blocks(page, [a, b])) == 2


def test_a_fragment_heading_a_column_stays_there():
    # "he's massively successful." sits an em past the line's end, but two more lines start
    # where it does: it heads the next column (20_pg35).
    page = _page()
    lines = [_line("run of dates in a calendar year. The 2017 album", 60, 100),
             _line("he's massively successful.", 200, 100),
             _line("The singer's arena tour", 200, 107),
             _line("holds the record for the", 200, 114)]
    blocks = build_blocks(page, lines)
    assert [l.text for l in blocks[0].lines] == ["run of dates in a calendar year. The 2017 album"]


def test_a_fragment_in_the_next_column_stays_there():
    # "cohort." starts the next column's line on the same baseline, 2.5 ems past the block's
    # edge (0e5f0c3447); with a gutter recorded between them it is refused outright.
    page = _page()
    lines = [_line("prudent for patients with advanced chronic", 60, 100, size=10.0, font="Times"),
             _line("prudent for patients with", 60, 112, size=10.0, font="Times"),
             _line("cohort.", 268, 112, size=10.0, font="Times")]
    blocks = build_blocks(page, lines)
    assert len(blocks) == 2 and blocks[1].text == "cohort."
    page = _page()
    page.meta["column_gutters"] = [(256.0, 266.0)]
    lines = [_line("prudent for patients with advanced chronic", 60, 100, size=10.0, font="Times"),
             _line("prudent for patients with advanced", 60, 112, size=10.0, font="Times"),
             _line("cohort.", 268, 112, size=10.0, font="Times")]
    blocks = build_blocks(page, lines)
    assert len(blocks) == 2 and blocks[1].text == "cohort."
