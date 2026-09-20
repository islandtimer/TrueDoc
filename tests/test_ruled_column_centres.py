"""A ruled column's centre is the middle of the column, not of the first cell that starts in it.

A permit-fee form draws the divider between its codes and descriptions 16 points further left under its first three
rows than beside them, and its fee divider 10 points further right. The grid so has two sliver columns, and the first
cell to start in each is one that runs on across the next column; taken from that cell, the sliver's "centre" lay far
outside the sliver, the cells whose rectangles do cover it were given one column, and an empty cell was made up
beside each of them (benchmark tables/9e3b179d..._pg2, 20 September 2026). The geometry below is that page's.
"""
from truedoc.tables.ruled import column_spans

# the five column edges: 37 | 113 (sliver) | 129 | 490 (sliver) | 500 ... 586
TOP = [(37.2, 0, 128.8, 10), None, (128.8, 0, 490.4, 10), (490.4, 0, 586.2, 10), None]         # RESIDENTIAL | WORK ORDER CODES | MINIMUM FEE
LOWER = [(37.2, 20, 112.9, 30), (112.9, 20, 500.0, 30), None, None, (500.0, 20, 586.2, 30)]     # NEWB | New residential building ... | $100


def test_a_heading_takes_the_sliver_its_rectangle_covers():
    spans = column_spans([TOP, LOWER, LOWER], 5)
    assert spans[(0, 0)] == 2          # "RESIDENTIAL", 37-129, over the code column and the sliver beside it
    assert spans[(0, 3)] == 2          # "MINIMUM FEE $50", as before


def test_a_description_takes_both_slivers():
    spans = column_spans([TOP, LOWER, LOWER], 5)
    assert spans[(1, 1)] == 3 and spans[(2, 1)] == 3      # 113-500: the sliver, the column, the other sliver


def test_no_cell_is_left_to_be_made_up():
    # every column of every row is a cell's own or under a span
    spans = column_spans([TOP, LOWER, LOWER], 5)
    for ri, rects in enumerate([TOP, LOWER, LOWER]):
        covered = set()
        for ci, rect in enumerate(rects):
            if rect is not None:
                covered.update(range(ci, ci + spans.get((ri, ci), 1)))
        assert covered == set(range(5))


def test_a_plain_grid_with_one_spanning_heading_reads_as_it_did():
    head = [(0, 0, 100, 10), (100, 0, 300, 10), None]             # "Item" | "Amount" over two columns
    body = [(0, 10, 100, 20), (100, 10, 200, 20), (200, 10, 300, 20)]
    assert column_spans([head, body, body], 3) == {(0, 1): 2}
    # ... whichever row comes first
    assert column_spans([body, head, body], 3) == {(1, 1): 2}
