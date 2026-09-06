"""Unruled-table finder on synthetic line geometry."""

from truedoc.model import BBox, Char, Line, Page, Word
from truedoc.tables.aligned import find_aligned_tables


def _line(text, x0, y0, size=10.0):
    words = []
    x = x0
    for tok in text.split():
        w = 5.0 * len(tok)
        chars = [Char(text=c, bbox=BBox(x + i * 5, y0, x + (i + 1) * 5, y0 + size), font="F", size=size, origin_y=y0 + 0.8 * size) for i, c in enumerate(tok)]
        words.append(Word(text=tok, bbox=BBox(x, y0, x + w, y0 + size), chars=chars))
        x += w + 4.0
    return Line(words=words, bbox=BBox(x0, y0, x - 4.0, y0 + size))


def _page(lines):
    page = Page(number=1, width=612, height=792)
    page.lines = lines
    page.body_font_size = 10.0
    return page


def test_simple_numeric_table_is_found():
    lines = []
    y = 200
    for label, val in [("Plot", "Yield"), ("North", "12.5"), ("South", "9.1"), ("East", "14.0"), ("West", "7.7")]:
        lines.append(_line(label, 100, y))
        lines.append(_line(val, 250, y))
        y += 14
    tables, remaining = find_aligned_tables(_page(lines), lines, 10.0)
    assert len(tables) == 1
    t = tables[0].table
    assert t.n_rows == 5 and t.n_cols == 2
    assert [c.text for c in t.cells if c.row == 2] == ["South", "9.1"]
    assert remaining == []


def test_two_column_prose_is_not_a_table():
    lines = []
    y = 200
    for i in range(12):
        lines.append(_line("the quick brown fox jumps over the lazy dog again", 60, y))
        lines.append(_line("another column of ordinary running prose text here", 330, y))
        y += 12
    tables, remaining = find_aligned_tables(_page(lines), lines, 10.0)
    assert tables == []
    assert len(remaining) == len(lines)


def test_line_numbered_prose_is_not_a_table():
    lines = []
    y = 200
    for i in range(12):
        lines.append(_line(str(400 + i), 5, y, size=6))
        lines.append(_line("body text of a manuscript page with line numbers in the margin", 40, y))
        y += 12
    tables, remaining = find_aligned_tables(_page(lines), lines, 10.0)
    assert tables == []


def test_grouped_header_does_not_erase_columns():
    # A booktabs-style table: a spanning group header above three data columns.
    lines = []
    y = 200
    lines.append(_line("Group", 60, y)); lines.append(_line("Mean values across tests", 160, y)); y += 14
    lines.append(_line("Item", 60, y)); lines.append(_line("A", 160, y)); lines.append(_line("B", 230, y)); lines.append(_line("C", 300, y)); y += 14
    for name, a, b, c in [("north", "1.2", "3.4", "5.6"), ("south", "2.3", "4.5", "6.7"), ("east", "3.4", "5.6", "7.8"), ("west", "4.5", "6.7", "8.9")]:
        lines.append(_line(name, 60, y)); lines.append(_line(a, 160, y)); lines.append(_line(b, 230, y)); lines.append(_line(c, 300, y)); y += 14
    tables, _ = find_aligned_tables(_page(lines), lines, 10.0)
    assert len(tables) == 1
    t = tables[0].table
    assert t.n_cols == 4
    # Two heading rows: the group heading spans the three data columns it sits
    # over, its sub-headings sit beneath it, and the corner labels join up.
    top = [c for c in t.cells if c.row == 0]
    assert [c.text for c in top] == ["Group Item", "Mean values across tests"]
    assert top[1].colspan == 3 and top[1].is_header and t.has_merged
    assert [c.text for c in t.cells if c.row == 1] == ["", "A", "B", "C"]
    assert [c.text for c in t.cells if c.row == 3] == ["south", "2.3", "4.5", "6.7"]


def test_two_line_header_is_merged():
    lines = []
    y = 200
    lines.append(_line("Var", 60, y)); lines.append(_line("(1)", 160, y)); lines.append(_line("(2)", 230, y)); y += 12
    lines.append(_line("Passed", 160, y)); lines.append(_line("Female", 230, y)); y += 14
    for name, a, b in [("Mean", "0.06", "0.93"), ("SD", "0.24", "0.25"), ("N", "120", "120")]:
        lines.append(_line(name, 60, y)); lines.append(_line(a, 160, y)); lines.append(_line(b, 230, y)); y += 14
    tables, _ = find_aligned_tables(_page(lines), lines, 10.0)
    assert len(tables) == 1
    t = tables[0].table
    # A column number "(1)" over its name is one heading, "(1) Passed": the
    # benchmark's checker matches each heading cell on its own, and a reader
    # says the two together (the qualifier-row form was tried first and lost
    # the checks on a regression table).
    assert [c.text for c in t.cells if c.row == 0] == ["Var", "(1) Passed", "(2) Female"]
    assert all(c.is_header for c in t.cells if c.row == 0)
    assert t.n_rows == 4
