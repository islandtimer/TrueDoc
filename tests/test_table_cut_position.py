"""A voted column cut sits at the right end of the empty range, not its midpoint.

A dated schedule: short task names on the left, dates in a column further
right. A wrapped task line has no date, so it never votes, and its words run
across the empty range that the dated rows leave; the range's midpoint fell in
one of its word spaces and moved "design level)" into the date column.
"""

from truedoc.model import BBox, Char, Line, Page, Word
from truedoc.tables.aligned import find_aligned_tables

SIZE = 10.0


def _line(text, x0, y0, space=3.0):
    # Word spaces of 0.3 em: below the 0.4 em that counts as a column vote.
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


def test_cut_sits_before_the_column_not_in_a_wrapped_word_space():
    lines = []
    y = 100
    lines.append(_line("Milestone", 60, y)); lines.append(_line("Date", 266, y)); y += 14
    for task, date in [("Plans", "2001"), ("Pre-design", "2002"), ("Operational", "2003"), ("Certificate", "2005"),
                       ("Notice to proceed", "2002"), ("Design development", "March 2003")]:
        lines.append(_line(task, 60, y)); lines.append(_line(date, 266, y)); y += 14
    # The wrapped continuation: 60..260, word spaces at 85, 118, 161, 194 and 227.
    # Six of the eight voting rows leave 123..266 empty ("Design review" ends at
    # 123), whose midpoint 194.5 is the space between "90-95%" and "design".
    lines.append(_line("Final design (approx. 90-95% design level)", 60, y - 2)); y += 12
    lines.append(_line("Design review", 60, y)); lines.append(_line("2003", 266, y)); y += 14
    tables, _ = find_aligned_tables(_page(lines), lines, SIZE)
    assert len(tables) == 1
    t = tables[0].table
    assert t.n_cols == 2
    dates = [c.text for c in t.cells if c.col == 1]
    tasks = [c.text for c in t.cells if c.col == 0]
    assert not any("level)" in d for d in dates), dates
    assert any("90-95% design level)" in s for s in tasks), tasks
    assert "March 2003" in dates
