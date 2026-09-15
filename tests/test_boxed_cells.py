"""A table the text built across boxes its page strokes keeps a name one box holds in one cell.

Budget Direct's optional covers are cards: each name in a stroked box, on one line or two ("Unspecified" over "Personal
Effects"), an armchair and a lamp drawn beside it, a page link under the box. The aligned finder made each line of a
name a row, so "Unspecified Personal Effects" was nowhere in the markdown. Rows one box holds together, as one run of
text, are one row - even where a box reaches well past the table's text, and with an icon's strokes between the lines.
A frame round the whole table, a list or two sentences in one box, a rule across the lines, lines of different sizes,
and a column whose rows keep values of their own are all left as the table has them.
"""
import pymupdf

from truedoc.extract.handle import open_pdf
from truedoc.extract.textlayer import extract_page
from truedoc.model import BBox, Block, BlockKind, Table, TableCell
from truedoc.tables import boxed_cells

GREEN = (0.0, 0.6, 0.3)
LEFT, RIGHT = (46, 210, 194, 251), (212, 210, 360, 251)


def _page(tmp_path, boxes, texts, rules=()):
    """Boxes stroked green, text as (x, baseline, text, size), rules as (x0, y, x1)."""
    doc = pymupdf.open()
    page = doc.new_page(width=400, height=300)
    for box in boxes:
        page.draw_rect(pymupdf.Rect(*box), color=GREEN, width=2)
    for x0, y, x1 in rules:
        page.draw_line((x0, y), (x1, y), color=GREEN, width=1)
    for x, y, text, size in texts:
        page.insert_text((x, y), text, fontsize=size)
    # A file of its own for each page: the object reader keeps a page's PDF open, and Windows will not save over it.
    path = tmp_path / f"cards{len(list(tmp_path.glob('*.pdf')))}.pdf"
    doc.save(str(path))
    doc.close()
    return str(path)


def _table(rows):
    """Three rows over two columns, cut as the aligned finder cut Budget Direct's cards: the table's box ends with its
    text at x 300, and the right-hand card's box runs on to 360."""
    bands = ((214, 230), (230, 246), (254, 270))
    cells = [TableCell(text=t, row=r, col=c, bbox=BBox((57, 180)[c], bands[r][0], (180, 301)[c], bands[r][1]))
             for r, row in enumerate(rows) for c, t in enumerate(row)]
    table = Table(n_rows=3, n_cols=2, cells=cells, bbox=BBox(58, 219, 300, 266), provenance="textlayer-aligned")
    return Block(kind=BlockKind.TABLE, bbox=table.bbox, table=table, provenance="textlayer-aligned")


def _joined(path, rows):
    doc = open_pdf(path)
    try:
        out = boxed_cells.join_boxed_rows(extract_page(doc[0], 1), doc[0], [_table(rows)])
    finally:
        doc.close()
    t = out[0].table
    grid = [[""] * t.n_cols for _ in range(t.n_rows)]
    for c in t.cells:
        grid[c.row][c.col] = c.text
    return grid


def _cards(upper=("Unspecified", "Specified"), lower=("Personal Effects", "Personal Effects"), sizes=(10, 10)):
    return [(59, 227, upper[0], sizes[0]), (225, 227, upper[1], sizes[0]),
            (59, 239, lower[0], sizes[1]), (225, 239, lower[1], sizes[1]),
            (86, 264, "page 47", 8.5), (252, 264, "page 47", 8.5)]


CARDS = [["Unspecified", "Specified"], ["Personal Effects", "Personal Effects"], ["page 47", "page 47"]]
JOINED = [["Unspecified Personal Effects", "Specified Personal Effects"], ["page 47", "page 47"]]


def test_a_name_on_two_lines_in_one_box_is_one_cell(tmp_path):
    assert _joined(_page(tmp_path, [LEFT, RIGHT], _cards()), CARDS) == JOINED


def test_an_icon_drawn_beside_the_name_is_not_a_rule_between_its_lines(tmp_path):
    icons = [(168, 231, 184), (334, 231, 350)]
    assert _joined(_page(tmp_path, [LEFT, RIGHT], _cards(), rules=icons), CARDS) == JOINED


def test_a_frame_round_the_whole_table_or_each_whole_column_joins_nothing(tmp_path):
    assert _joined(_page(tmp_path, [(40, 205, 370, 275)], _cards()), CARDS) == CARDS
    columns = [(46, 210, 194, 272), (212, 210, 360, 272)]
    assert _joined(_page(tmp_path, columns, _cards()), CARDS) == CARDS


def test_a_list_or_two_sentences_in_one_box_are_left_apart(tmp_path):
    listed = [["1. Tenant default", "Specified"], ["2. Theft", "Personal Effects"], ["page 52", "page 47"]]
    page = _page(tmp_path, [LEFT, RIGHT], _cards(upper=("1. Tenant default", "Specified"), lower=("2. Theft", "Personal Effects")))
    assert _joined(page, listed) == listed
    sentences = [["Call us.", "Specified"], ["Go to page 32.", "Personal Effects"], ["page 52", "page 47"]]
    page = _page(tmp_path, [LEFT, RIGHT], _cards(upper=("Call us.", "Specified"), lower=("Go to page 32.", "Personal Effects")))
    assert _joined(page, sentences) == sentences


def test_a_rule_across_the_lines_or_a_change_of_size_keeps_them_apart(tmp_path):
    ruled = _page(tmp_path, [LEFT, RIGHT], _cards(), rules=[(46, 231, 194), (212, 231, 360)])
    assert _joined(ruled, CARDS) == CARDS
    note = _page(tmp_path, [LEFT, RIGHT], _cards(sizes=(10, 7)))
    assert _joined(note, CARDS) == CARDS


def test_a_column_whose_rows_keep_their_own_values_is_not_folded(tmp_path):
    values = [["Unspecified", "$1,000"], ["Personal Effects", "$2,000"], ["page 47", "page 47"]]
    page = _page(tmp_path, [LEFT], _cards(upper=("Unspecified", "$1,000"), lower=("Personal Effects", "$2,000")))
    assert _joined(page, values) == values


def test_boxes_of_stacked_values_are_rows_not_a_run(tmp_path):
    stats = [["W", "0.46"], ["P value", "< 2.2e-16"], ["page 47", "page 47"]]
    page = _page(tmp_path, [LEFT, RIGHT], _cards(upper=("W", "0.46"), lower=("P value", "< 2.2e-16")))
    assert _joined(page, stats) == stats
