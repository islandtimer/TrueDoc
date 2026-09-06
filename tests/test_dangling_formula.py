"""Arithmetic after a line break rejoins the formula that ended in a relation."""
from truedoc.render.okf import _join_dangling_formulas


def test_numbers_after_a_dangling_equals_join_the_formula():
    body = "yielding $\\text{maj}(\\sigma)=$ 2 + 1 + 1 + 1 = 5. The inversion triples"
    assert _join_dangling_formulas(body) == "yielding $\\text{maj}(\\sigma)=2+1+1+1=5$. The inversion triples"


def test_join_works_across_a_newline():
    body = "so $x+y=$\n3 and then"
    assert _join_dangling_formulas(body) == "so $x+y=3$ and then"


def test_a_closed_formula_is_left_alone():
    body = "we get $x=y$ 2 items and $a<b$ 3."
    assert _join_dangling_formulas(body) == body


def test_words_after_the_relation_are_not_pulled_in():
    body = "where $n=$ the number of rows"
    assert _join_dangling_formulas(body) == body
