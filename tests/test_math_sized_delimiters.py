r"""A matched pair of sized delimiters is written the way the author typed it.

TeX picks a glyph for each size, so the page draws "\big(" where the source says "\left(";
the benchmark's references spell it \left ... \right, and so does anyone reading the LaTeX.
Only a pair this can match is rewritten: a bar opens and closes with the same glyph, so bars
are never touched; a delimiter whose partner is missing stays as drawn, because a \left with
no \right does not render at all and would cost the whole formula; and a pair that does not
sit inside one group is left alone for the same reason.

Measured on run 87's output: 7 failed maths checks pass with the rule and 3 passing ones fail
(their references spell the size themselves), over 444 of the run's 19,561 formulas.
"""
from truedoc.math.reconstruct import _pair_sized_delimiters


def test_a_matched_pair_becomes_left_and_right():
    assert _pair_sized_delimiters(r"\big( \frac{a}{b} \big)") == r"\left( \frac{a}{b} \right)"
    assert _pair_sized_delimiters(r"\bigg[ x \bigg]") == r"\left[ x \right]"
    assert _pair_sized_delimiters(r"\Bigg\{ x \Bigg\}") == r"\left\{ x \right\}"


def test_the_l_and_r_forms_are_read_too():
    assert _pair_sized_delimiters(r"\bigl( x \bigr)") == r"\left( x \right)"


def test_nested_pairs_are_both_rewritten():
    assert _pair_sized_delimiters(r"\big( \Big( x \Big) \big)") == r"\left( \left( x \right) \right)"


def test_a_pair_inside_one_group_is_rewritten():
    assert _pair_sized_delimiters(r"\frac{\big( x \big)}{y}") == r"\frac{\left( x \right)}{y}"


def test_a_delimiter_with_no_partner_stays_as_drawn():
    assert _pair_sized_delimiters(r"\big( x") == r"\big( x"
    assert _pair_sized_delimiters(r"x \big)") == r"x \big)"


def test_bars_are_never_touched():
    # The same glyph opens and closes, so there is no way to tell the pair apart.
    assert _pair_sized_delimiters(r"\Bigg| x \Bigg|") == r"\Bigg| x \Bigg|"


def test_a_pair_that_is_not_one_group_is_left_alone():
    assert _pair_sized_delimiters(r"\big( a \\ b \big)") == r"\big( a \\ b \big)"
    assert _pair_sized_delimiters(r"\big( a & b \big)") == r"\big( a & b \big)"
    assert _pair_sized_delimiters(r"{\big( a} b \big)") == r"{\big( a} b \big)"
    assert _pair_sized_delimiters(r"\frac{\big( a}{b \big)}") == r"\frac{\big( a}{b \big)}"


def test_a_formula_with_no_sized_delimiters_is_unchanged():
    assert _pair_sized_delimiters(r"(x) + [y]") == r"(x) + [y]"
