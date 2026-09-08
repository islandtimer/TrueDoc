"""Aligned tables after run 60: a two-line heading beside single-line headings is not a title.

"Number of Agreement" sits over "(ranked 3 or 4)" in the middle column while "Item" and "I-CVI"
are set on one line each, level with the gap between them. Run 60's title-row rule took the
first line for a title spanning every column and left the second line stranded (3c0b540d, one
check). A title's column has nothing beneath it in the heading; a heading continued two rows
down in its own column is one heading in two lines.
"""
from truedoc.tables.aligned import find_aligned_tables

from tests.test_table_tail_run58 import SIZE, _page, _seg


def test_two_line_heading_beside_single_line_headings_is_one_heading():
    # The page's own geometry: the two-line heading's lines sit above and below the level of
    # "Item" and "I-CVI", so the three make three rows.
    lines = [_seg("Number of Agreement", 224, 322, 169),
             _seg("Item", 176, 198, 176), _seg("I-CVI", 371, 399, 176),
             _seg("(ranked 3 or 4)", 240, 306, 182)]
    for i, (n, a, v) in enumerate((("1", "9", "1.00"), ("2", "9", "1.00"), ("3", "8", "0.89"), ("4", "8", "0.89"), ("5", "7", "0.78"))):
        y = 197 + 13 * i
        lines += [_seg(n, 183, 191, y), _seg(a, 269, 277, y), _seg(v, 375, 395, y)]
    tables, _ = find_aligned_tables(_page(lines), lines, SIZE)
    assert len(tables) == 1
    t = tables[0].table
    heads = [(c.row, c.col, c.text, c.colspan) for c in t.cells if c.is_header and c.text]
    assert (0, 1, "Number of Agreement (ranked 3 or 4)", 1) in heads, heads
    assert any(text == "Item" for _, _, text, _ in heads) and any(text == "I-CVI" for _, _, text, _ in heads)
    assert not any(span > 1 for _, _, _, span in heads)
