r"""A bare ampersand inside a formula is escaped, so the formula still renders.

LaTeX reads "&" as an alignment character. A model transcribing an old textbook writes the
series as "1 - 3x + 6x^2 + &c." - the nineteenth-century abbreviation for "etc." - and that
one character stops the whole formula rendering: the reader is shown raw TeX, and the checks
on it fail. The benchmark's own references write it escaped.

A span that opens an environment keeps its ampersands: there they are the alignment the
environment is built from, and escaping them would break the formula this is meant to save.

Measured on run 87's output: old_scans_math/5_pg174 goes from 19 of 67 checks to 21, and it
holds the only two formulas in the whole run outside arXiv that will not render.
"""
from truedoc.render.okf import _escape_dollars


def test_a_bare_ampersand_in_a_formula_is_escaped():
    assert _escape_dollars(r"\(1 - 3x + 6x^2 + &c.\)") == r"\(1 - 3x + 6x^2 + \&c.\)"
    assert _escape_dollars(r"see \(\text{A&B}\) here") == r"see \(\text{A\&B}\) here"


def test_an_ampersand_already_escaped_is_left_alone():
    assert _escape_dollars(r"\(x + \&c.\)") == r"\(x + \&c.\)"


def test_an_environment_keeps_its_alignment():
    aligned = r"\[\begin{aligned} a &= b \\ c &= d \end{aligned}\]"
    assert _escape_dollars(aligned) == aligned
    cases = r"\[\begin{cases} 1 & x > 0 \\ 0 & x \le 0 \end{cases}\]"
    assert _escape_dollars(cases) == cases


def test_prose_ampersands_are_not_touched():
    # Outside a formula an ampersand is just an ampersand, and markdown shows it as it is.
    assert _escape_dollars("Marks & Spencer") == "Marks & Spencer"
    assert _escape_dollars("<td>Native Hawaiian & Other Pacific</td>") == "<td>Native Hawaiian & Other Pacific</td>"


def test_dollar_signs_still_work():
    # The ampersand rule rides on the same pass, so its neighbour must keep working (D024).
    assert _escape_dollars("it costs $5") == r"it costs \$5"
    assert _escape_dollars(r"\(x^2\) costs $5") == r"\(x^2\) costs \$5"
