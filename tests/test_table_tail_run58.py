"""Four table shapes from run 58's failures (8 September 2026), 14 checks between them.

1. A ruled statistics table stacks "Shapiro / W / P value" in its label cell beside "0.46 /
   < 2.2e-16": the label's first two lines are one wrapped label, so the cell has two rows
   like its neighbours, not three (bat metals, 29c8f321, 4 checks).
2. A one-row heading centred over a group of columns ("Program Committee" over two name
   columns) heads every column it covers (a committee roster, b10f6b51, 3 checks).
3. A label column filled on a few rows ("Emotion Type": Sequential, Prevalent, Inverse) is a
   column of its own, not whitespace from the table's edge to the next column (5bd8ff36, 2).
4. Rows of a table in the head strip join the body across a one-line group label between them
   ("9 Months | $1,298 | ..." above "Adjusted EPS*:" above "Q3 | 0.84 | ..."; a press release,
   a769f9a3, 5 checks).
"""
from truedoc.model import BBox, Char, Line, Page, Word
from truedoc.tables.aligned import find_aligned_tables
from truedoc.tables.ruled import split_multiline_row

SIZE = 11.0


def _seg(text, x0, x1, y0, size=SIZE):
    cw = (x1 - x0) / max(1, len(text))
    chars = [Char(text=c, bbox=BBox(x0 + i * cw, y0, x0 + (i + 1) * cw, y0 + size), font="F", size=size, origin_y=y0 + 0.8 * size) for i, c in enumerate(text)]
    words = []
    x = x0
    for tok in text.split(" "):
        w = cw * len(tok)
        words.append(Word(text=tok, bbox=BBox(x, y0, x + w, y0 + size), chars=[c for c in chars if x <= c.bbox.x0 < x + w + 0.01]))
        x += w + cw
    return Line(words=words, bbox=BBox(x0, y0, x1, y0 + size))


def _page(lines, height=792):
    page = Page(number=1, width=612, height=height)
    page.lines = lines
    page.body_font_size = SIZE
    return page


def test_wrapped_label_line_pairs_with_its_values():
    row = ["Cd", "Shapiro\nW\nP value", "0.46\n< 2.2e-16", "0.15\n< 2.2e-16", "-"]
    assert split_multiline_row(row, 5) == [["Cd", "Shapiro W", "0.46", "0.15", "-"], ["", "P value", "< 2.2e-16", "< 2.2e-16", ""]]
    # A three-line label beside one-line values is still one wrapped label, not rows.
    assert split_multiline_row(["Cd", "Bonferroni\nAdjusted p\nvalue", "1.2174e-06", "4.5140e-03"], 4) is None
    # Two stacks of different heights that are not a label wrap stay whole.
    assert split_multiline_row(["a\nb\nc", "1\n2", "x"], 3) is None


def test_one_row_heading_centred_over_a_group_heads_every_column():
    lines = [_seg("Program Committee", 150, 260, 100), _seg("Student Rep Attendance", 330, 470, 100)]
    names = [("Arnold, Mark", "Khandelwal, Sorabh", "Bashaw, Hillary", "Ho, Vincent"), ("Barin, Kamrin", "Kman, Nicholas", "Fu, Julia", "House, Melissa"),
             ("Bartholomew, Deb", "Ledford, Cindy", "Gerstman, Jacob", "Rose, Maggie"), ("Bourekas, Eric", "Letson, Alan", "Sauers, Lynn", "Vogt, Keith")]
    for i, (a, b, c, d) in enumerate(names):
        y = 118 + 14 * i
        lines += [_seg(a, 60, 60 + 5.5 * len(a), y), _seg(b, 210, 210 + 5.5 * len(b), y), _seg(c, 330, 330 + 5.5 * len(c), y), _seg(d, 440, 440 + 5.5 * len(d), y)]
    tables, _ = find_aligned_tables(_page(lines), lines, SIZE)
    assert len(tables) == 1
    t = tables[0].table
    assert t.n_cols == 4
    heads = {c.col: (c.text, c.colspan) for c in t.cells if c.row == 0}
    assert heads[0] == ("Program Committee", 2) and heads[2] == ("Student Rep Attendance", 2)
    assert t.has_merged


def test_sparse_label_column_is_a_column():
    lines = [_seg("Emotion Type", 123, 192, 100), _seg("Effect", 287, 316, 100), _seg("d.f.", 366, 381, 100), _seg("p", 426, 432, 100)]
    # Two labels in fourteen body rows: under the fifth of rows the channel finder tolerates.
    body = [("Sequential", "A", "1", ".056"), ("", "P", "1", "<.001"), ("", "E", "1", ".410"), ("", "A x P", "3", ".071"),
            ("", "A x E", "3", ".063"), ("", "P x E", "3", ".089"), ("", "A x P x E", "7", ".500"),
            ("Prevalent", "A", "1", ".430"), ("", "P", "1", ".560"), ("", "E", "1", ".078"), ("", "A x P", "3", ".870"),
            ("", "A x E", "3", ".494"), ("", "P x E", "3", ".065"), ("", "A x P x E", "7", ".524")]
    for i, (lab, eff, df, p) in enumerate(body):
        y = 118 + 14 * i
        if lab:
            lines.append(_seg(lab, 132, 132 + 5.5 * len(lab), y))
        lines += [_seg(eff, 297, 297 + 4 * len(eff), y), _seg(df, 370, 376, y), _seg(p, 418, 418 + 5.5 * len(p), y)]   # tight word gaps, as printed
    tables, _ = find_aligned_tables(_page(lines), lines, SIZE)
    assert len(tables) == 1
    t = tables[0].table
    assert t.n_cols == 4
    texts = {(c.row, c.col): c.text for c in t.cells}
    assert texts[(0, 0)] == "Emotion Type" and texts[(0, 1)] == "Effect"
    assert texts[(1, 0)] == "Sequential" and texts[(1, 1)] == "A" and texts[(8, 0)] == "Prevalent"


def test_two_row_table_under_a_centred_title_keeps_its_title():
    # "Scale Reliability Statistics" centred over "Cronbach's α | McDonald's ω" over one value
    # row whose label wraps to "(CoRS)": a two-row table the run finder refused (it wants three
    # cells in each of two rows), and the title is its spanning heading (63d430cd, 3 checks).
    lines = [_seg("Table 1.4. CoRS' Reliability", 300, 470, 80), _seg("Scale Reliability Statistics", 310, 465, 100),
             _seg("Cronbach's α", 335, 425, 118), _seg("McDonald's ω", 548, 640, 118),
             _seg("Counterradicalism readiness Scale", 85, 245, 136), _seg("0.92", 365, 390, 136), _seg("0.93", 585, 610, 136),
             _seg("(CoRS)", 150, 180, 150)]
    tables, _ = find_aligned_tables(_page(lines), lines, SIZE)
    assert len(tables) == 1
    t = tables[0].table
    texts = {(c.row, c.col): (c.text, c.colspan) for c in t.cells}
    title = [(k, v) for k, v in texts.items() if v[0] == "Scale Reliability Statistics"]
    assert title and title[0][0][0] == 0 and title[0][1][1] >= 2
    assert any(v[0] == "Cronbach's α" and k[0] == 1 for k, v in texts.items())
    assert any(v[0] == "McDonald's ω" and k[0] == 1 for k, v in texts.items())
    assert any(v[0].startswith("Counterradicalism") for v in texts.values())


def test_value_block_beside_prose_is_a_table_of_its_own():
    # A figure's key values ("surface water | bottom water" over "TP 120 µg l-1 | TP 1500 µg l-1"
    # ...) set beside a prose column: one candidate, two channels, the wide one dividing
    # eleven-word prose from two-word cells. The block is a table on its own (b5d9db35, 5 checks).
    prose = ["carbon isotopes 13C and 12C expressed as d13C values from minus eighty to",
             "minus fifty and MOB are known to discriminate against the heavier isotope",
             "heavier 13C when metabolizing CH4 resulting in even lower values of the",
             "d13C values of MOB biomass these very low values do not occur in aquatic",
             "not occur in aquatic and terrestrial photosynthetic primary producers here"]
    block = [("surface water", "bottom water"), ("TP 120 µg l–1,", "TP 1500 µg l–1"), ("TN 2300 µg l–1", "TN 3600 µg l–1"), ("pH 8.0", "pH 6.9")]
    lines = []
    for i, p in enumerate(prose):
        y = 40 + 12 * i
        lines.append(_seg(p, 43, 283, y, size=9.0))
        if i < len(block):
            a, b = block[i]
            lines += [_seg(a, 327, 327 + 4.2 * len(a), y, size=9.0), _seg(b, 480, 480 + 4.2 * len(b), y, size=9.0)]
    page = _page(lines)
    page.body_font_size = 9.0
    tables, remaining = find_aligned_tables(page, lines, 9.0)
    assert len(tables) == 1
    t = tables[0].table
    texts = {(c.row, c.col): c.text for c in t.cells}
    assert t.n_cols == 2 and t.n_rows == 4
    assert texts[(0, 1)] == "bottom water" and texts[(3, 1)] == "pH 6.9" and texts[(2, 0)] == "TN 2300 µg l–1"
    assert all(l in remaining for l in lines if l.bbox.x0 < 300)     # the prose stays prose


def test_strip_rows_join_the_body_across_a_group_label():
    lines = [_seg("Revenue:", 50, 100, 8), _seg("Q3", 60, 72, 22), _seg("$448", 150, 174, 22), _seg("$427", 190, 214, 22), _seg("7%", 230, 244, 22),
             _seg("9 Months", 60, 105, 36), _seg("$1,298", 150, 186, 36), _seg("$1,263", 190, 226, 36), _seg("5%", 230, 244, 36),
             _seg("Adjusted EPS*:", 50, 130, 52),
             _seg("Q3", 60, 72, 76), _seg("0.84", 150, 174, 76), _seg("0.74", 190, 214, 76), _seg("22%", 230, 250, 76),
             _seg("9 Months", 60, 105, 90), _seg("2.44", 150, 174, 90), _seg("2.12", 190, 214, 90), _seg("20%", 230, 250, 90),
             _seg("Reported EPS", 50, 120, 106),
             _seg("Q3", 60, 72, 122), _seg("0.74", 150, 174, 122), _seg("0.71", 190, 214, 122), _seg("13%", 230, 250, 122),
             _seg("9 Months", 60, 105, 136), _seg("2.34", 150, 174, 136), _seg("1.95", 190, 214, 136), _seg("25%", 230, 250, 136)]
    tables, remaining = find_aligned_tables(_page(lines), lines, SIZE)
    assert len(tables) == 1
    t = tables[0].table
    texts = [c.text for c in t.cells]
    assert "$448" in texts and "$1,298" in texts and "2.34" in texts
    assert t.n_rows >= 7
