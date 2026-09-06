"""Block classification heuristics."""

from truedoc.classify.blocks import classify_blocks
from truedoc.model import BBox, Block, BlockKind, Char, Line, Page, Word


def _block(text, x0, y0, size=10.0):
    chars = [Char(text=c, bbox=BBox(x0 + i * 5, y0, x0 + (i + 1) * 5, y0 + size), font="Times", size=size, origin_y=y0 + size * 0.8) for i, c in enumerate(text)]
    word = Word(text=text, bbox=BBox(x0, y0, x0 + 5 * len(text), y0 + size), chars=chars)
    line = Line(words=[word], bbox=word.bbox)
    return Block(kind=BlockKind.TEXT, bbox=line.bbox, lines=[line])


def test_margin_line_numbers_are_dropped_per_side():
    page = Page(number=1, width=600, height=800)
    page.body_font_size = 10.0
    blocks = []
    for i in range(8):
        blocks.append(_block(str(100 + i), 5, 100 + i * 60, size=6))     # left margin, increasing
        blocks.append(_block(str(300 + i), 585, 100 + i * 60, size=6))   # right margin, increasing
    body = _block("Ordinary body text line", 60, 100)
    blocks.append(body)
    classify_blocks(page, blocks)
    assert all(b.kind == BlockKind.PAGE_NUMBER for b in blocks if b is not body)
    assert body.kind == BlockKind.TEXT


def test_running_header_and_page_number():
    page = Page(number=1, width=600, height=800)
    page.body_font_size = 10.0
    header = _block("Journal of Things 2020", 60, 20, size=8)
    number = _block("42", 300, 780, size=9)
    body = _block("Body text of the page which is long enough to be text", 60, 300)
    blocks = [header, number, body]
    classify_blocks(page, blocks)
    assert header.kind == BlockKind.HEADER
    assert number.kind == BlockKind.PAGE_NUMBER
    assert body.kind == BlockKind.TEXT
