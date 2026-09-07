"""A title running across a table never takes a column cut, even at a word space.

A two-column correlation table with its title set over both columns: the
title's word space happened to sit where the second column starts, and a cut
placed there split the title and lost the table.
"""

from truedoc.model import BBox, Char, Line, Page, Word
from truedoc.tables.aligned import table_from_lines

SIZE = 10.0


def _line(text, x0, y0, space=3.0):
    words = []
    x = x0
    for tok in text.split():
        w = 5.0 * len(tok)
        chars = [Char(text=c, bbox=BBox(x + i * 5, y0, x + (i + 1) * 5, y0 + SIZE), font="F", size=SIZE, origin_y=y0 + 0.8 * SIZE) for i, c in enumerate(tok)]
        words.append(Word(text=tok, bbox=BBox(x, y0, x + w, y0 + SIZE), chars=chars))
        x += w + space
    return Line(words=words, bbox=BBox(x0, y0, x - space, y0 + SIZE))


def _page(lines):
    page = Page(number=1, width=612, height=792)
    page.lines = lines
    page.body_font_size = SIZE
    return page


def test_title_over_both_columns_is_not_cut():
    lines = []
    y = 100
    # "Tabel 2 Table of Correlation Criteria": 69..244, with the space before
    # "Criteria" at 201..204, exactly where the second column starts (204).
    lines.append(_line("Tabel 2 Table of Correlation Criteria", 69, y)); y += 14
    lines.append(_line("Corelation", 60, y)); lines.append(_line("Indication", 204, y)); y += 14
    for a, b in [("0,80-1", "Very high"), ("0,60-0,79", "Tall"), ("0,40-0,59", "Currently"), ("0,20-0,39", "Low"), ("0,00-0,19", "Very low")]:
        lines.append(_line(a, 60, y)); lines.append(_line(b, 204, y)); y += 14
    # The region path (a layout model's table box) keeps the title inside the table.
    t = table_from_lines(lines, SIZE, trusted=True)
    assert t is not None
    assert t.n_cols == 2
    texts = [c.text for c in t.cells]
    assert "Tabel 2 Table of Correlation Criteria" in texts
    assert "Corelation" in texts and "Indication" in texts
    assert [c.text for c in t.cells if c.row == t.n_rows - 4] == ["0,60-0,79", "Tall"]
