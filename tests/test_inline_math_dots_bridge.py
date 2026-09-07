"""A run of dots and commas between two formula words is part of the formula.

A set written "{τ1, . . . , τN}" reaches the text layer as a maths word, five one-character
text-font words (a comma, three dots, a comma) and a maths word. The inline detector bridged a
single word between two formula words; a run of several punctuation words split the formula in
two ("$\\{\\tau_{1}$, . . . , $\\tau_{N}\\}$", arXiv 2503.08119 page 4, lost in the page checks of
7 Sept 2026 once the page's text face stopped counting as maths).
"""
from truedoc.math.extract import inline_math_text
from truedoc.model import BBox, Char, Line, Word

TEXT = "TeXGyreTermesX-Regular"
MATH = "NewTXMI"


def _word(text, x, font=TEXT, size=10.0, baseline=100.0):
    chars = [Char(text=ch, bbox=BBox(x + i * 5, baseline - 0.7 * size, x + (i + 1) * 5, baseline + 0.2 * size), font=font, size=size, origin_y=baseline) for i, ch in enumerate(text)]
    return Word(text=text, bbox=BBox(x, baseline - 0.7 * size, x + 5 * len(text), baseline + 0.2 * size), chars=chars)


def _line(words):
    return Line(words=words, bbox=BBox.union_all(w.bbox for w in words))


def test_dots_and_commas_between_formula_words_are_bridged():
    words = [_word("by", 0), _word("{τ1", 20, MATH), _word(",", 40), _word(".", 48), _word(".", 56), _word(".", 64), _word(",", 72), _word("τN}", 82, MATH), _word("as", 105), _word("before.", 120)]
    out = inline_math_text(_line(words), [])
    assert out.count("$") == 2, out
    assert out.startswith("by $") and out.endswith("$ as before."), out


def test_prose_between_formula_words_is_not_bridged():
    # Two formulas with a sentence between them stay two formulas.
    words = [_word("α", 0, MATH), _word("is", 15), _word("larger", 30), _word("than", 65), _word("the", 90), _word("value", 110), _word("β", 140, MATH)]
    out = inline_math_text(_line(words), [])
    assert out.count("$") == 4, out
