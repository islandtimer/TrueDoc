"""A layout region nested inside another of the same kind is the same thing seen smaller.

The model often offers a table's whole box and a box over one of its columns, and the column can score
higher. Keeping the column threw the table away: on the fees page tables/937a90b2 page 7 a table region
over the fee column scored 0.77 against 0.59 for the whole table, a two-column table could not be built
from the column alone, and the rows came out as prose - five checks, run 83.
"""
from truedoc.layout.base import Region, RegionKind
from truedoc.layout.fuse import clean_regions
from truedoc.model import BBox


def _table(x0, y0, x1, y1, score):
    return Region(kind=RegionKind.TABLE, bbox=BBox(x0, y0, x1, y1), score=score)


def test_the_bigger_of_two_nested_table_regions_is_kept():
    whole = _table(74, 459, 526, 547, 0.59)
    column = _table(328, 469, 526, 548, 0.77)
    for order in ([whole, column], [column, whole]):
        kept = clean_regions(list(order))
        assert len(kept) == 1, [(r.bbox.x0, r.score) for r in kept]
        assert (kept[0].bbox.x0, kept[0].bbox.x1) == (74, 526), (kept[0].bbox.x0, kept[0].bbox.x1)


def test_two_tables_on_the_same_page_both_survive():
    upper = _table(74, 185, 523, 322, 0.87)
    lower = _table(74, 459, 526, 547, 0.59)
    kept = clean_regions([upper, lower])
    assert len(kept) == 2, [(r.bbox.y0, r.bbox.y1) for r in kept]


def test_two_readings_of_one_box_keep_the_better():
    """Nesting is not disagreement: where the boxes are the same size, the better-ranked reading wins."""
    weak = _table(74, 459, 526, 547, 0.55)
    strong = _table(74, 459, 526, 547, 0.85)
    kept = clean_regions([weak, strong])
    assert len(kept) == 1 and kept[0].score == 0.85, [(r.score) for r in kept]


def test_a_table_inside_a_figure_is_still_both():
    """The rule this leaves alone: a panel of numbers inside a figure is a table as well as a figure."""
    figure = Region(kind=RegionKind.FIGURE, bbox=BBox(70, 100, 530, 400), score=0.9)
    table = _table(80, 150, 520, 380, 0.6)
    kept = clean_regions([figure, table])
    assert len(kept) == 2, [(r.kind, r.score) for r in kept]
