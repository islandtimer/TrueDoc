"""Display-maths decisions: what counts as a displayed formula, and which boxes merge."""

from truedoc.math.extract import block_is_display_math
from truedoc.model import BBox, Block, BlockKind, Char, Line, Page, Word
from truedoc.pipeline import _apply_math


def word(text, x, oy, font="CMMI10", size=10.0):
    chars = []
    cx = x
    for ch in text:
        chars.append(Char(text=ch, bbox=BBox(cx, oy - 0.7 * size, cx + 5, oy + 0.2 * size), font=font, size=size, origin_y=oy))
        cx += 5
    return Word(text=text, bbox=BBox.union_all(c.bbox for c in chars), chars=chars)


def text_block(words):
    line = Line(words=words, bbox=BBox.union_all(w.bbox for w in words))
    return Block(kind=BlockKind.TEXT, bbox=line.bbox, lines=[line], provenance="test")


def test_sentence_with_formulas_is_not_a_display():
    words = [word("x", 10, 100), word("=", 20, 100, font="CMR10"), word("y", 30, 100), word("variables", 45, 100, font="CMR10"), word("and", 100, 100, font="CMR10"), word("z", 130, 100)]
    assert not block_is_display_math(text_block(words))


def test_formula_line_is_a_display():
    words = [word("x", 10, 100), word("=", 20, 100, font="CMR10"), word("y", 30, 100), word("+", 40, 100, font="CMR10"), word("z", 50, 100)]
    assert block_is_display_math(text_block(words))


def test_formula_boxes_do_not_merge_across_the_column_gutter():
    page = Page(number=1, width=600, height=800)
    page.body_font_size = 10.0
    left = text_block([word("x", 50, 100), word("=", 200, 100, font="CMR10"), word("y", 280, 100)])
    right = text_block([word("a", 310, 100), word("=", 400, 100, font="CMR10"), word("b", 540, 100)])
    page.chars = [c for b in (left, right) for l in b.lines for w in l.words for c in w.chars]
    blocks = _apply_math(page, [left, right], [])
    formulas = [b for b in blocks if b.kind == BlockKind.FORMULA]
    assert len(formulas) == 2
    assert all(b.bbox.width < 300 for b in formulas)
