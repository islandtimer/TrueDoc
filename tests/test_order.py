from truedoc.model import BBox, Block, BlockKind
from truedoc.segment.order import assign_reading_order


def _blk(x0, y0, x1, y1, kind=BlockKind.TEXT):
    return Block(kind=kind, bbox=BBox(x0, y0, x1, y1))


def test_two_columns_with_spanning_title():
    title = _blk(50, 40, 550, 70)
    l1 = _blk(50, 100, 290, 300)
    l2 = _blk(50, 310, 290, 500)
    r1 = _blk(310, 100, 550, 300)
    r2 = _blk(310, 310, 550, 500)
    blocks = [r2, l2, title, r1, l1]
    assign_reading_order(blocks, page_width=600, body_size=10)
    ordered = sorted(blocks, key=lambda b: b.order)
    assert ordered == [title, l1, l2, r1, r2]


def test_full_width_figure_does_not_split_columns():
    l1 = _blk(50, 100, 290, 300)
    fig = _blk(50, 310, 550, 400, kind=BlockKind.FIGURE)
    l2 = _blk(50, 410, 290, 600)
    r1 = _blk(310, 100, 550, 300)
    r2 = _blk(310, 410, 550, 600)
    blocks = [r2, l2, fig, r1, l1]
    assign_reading_order(blocks, page_width=600, body_size=10)
    ordered = sorted(blocks, key=lambda b: b.order)
    # Left column is read fully before the right column; the figure lands on the side its centre falls.
    assert ordered.index(l1) < ordered.index(l2) < ordered.index(r1) < ordered.index(r2)


def test_headers_go_last():
    header = _blk(50, 10, 300, 20, kind=BlockKind.HEADER)
    body = _blk(50, 100, 550, 300)
    blocks = [header, body]
    assign_reading_order(blocks, page_width=600, body_size=10)
    assert body.order < header.order


def test_full_width_figure_is_inserted_before_the_text_below_it():
    l1 = _blk(50, 100, 290, 300)
    fig = _blk(50, 310, 550, 400, kind=BlockKind.FIGURE)
    l2 = _blk(50, 410, 290, 600)
    r1 = _blk(310, 100, 550, 300)
    r2 = _blk(310, 410, 550, 600)
    blocks = [r2, l2, fig, r1, l1]
    assign_reading_order(blocks, page_width=600, body_size=10)
    ordered = sorted(blocks, key=lambda b: b.order)
    assert ordered == [l1, fig, l2, r1, r2]
