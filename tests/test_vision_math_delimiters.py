r"""A model's dollar-delimited maths is rewritten into the delimiters the document uses.

Run 90's lesson. D024 escapes every literal dollar sign outside TrueDoc's own `\( \)` and `\[ \]` spans,
which is right for prose and safe because nothing of ours writes maths between dollars. A general model
does: asked to convert equations to LaTeX it answers in the convention it learned. On
old_scans_math/1_pg131 that meant fourteen integrals came out as `\$\int \dfrac{dx}{...}\$` - literal
text, no formula - and the category fell 80.8 to 64.0, seventy-seven checks, the largest single loss of
the project.

Only maths is translated. "It costs $5 and $6" must still be escaped, which is the whole point of D024.
"""
from truedoc.render.okf import _escape_dollars
from truedoc.vision.mathdelims import normalise_math_delimiters


def test_inline_maths_becomes_our_own_delimiters():
    assert normalise_math_delimiters(r"And $\int \frac{dx}{x}$ follows.") == r"And \(\int \frac{dx}{x}\) follows."


def test_display_maths_becomes_our_own_display_delimiters():
    assert normalise_math_delimiters(r"$$\sum_{i=1}^n a_i$$") == r"\[\sum_{i=1}^n a_i\]"


def test_several_formulas_on_a_line_are_all_translated():
    got = normalise_math_delimiters(r"$x^2$ and $y_1$ and $z$")
    assert got == r"\(x^2\) and \(y_1\) and $z$", "a bare letter is not obviously maths"


def test_prices_are_left_for_D024_to_escape():
    for prose in ("it costs $5", "between $5 and $6 today", "$1,200 a year", "a $5 note and a $10 note"):
        assert normalise_math_delimiters(prose) == prose, prose


def test_a_price_still_reaches_the_reader_as_a_dollar_sign():
    # the two rules together: money escaped, maths preserved (D024)
    out = _escape_dollars(normalise_math_delimiters(r"The fee is $5 and $\int x\,dx$ is the integral."))
    assert r"\$5" in out
    assert r"\(\int x\,dx\)" in out
    assert r"\$\int" not in out, "the formula must not have been escaped into literal text"


def test_the_run_90_page_survives_the_round_trip():
    reading = r"And $\int \dfrac{dx}{\sqrt{2ax + x^2}} = \log \{x + a + \sqrt{2ax + x^2}\},$"
    out = _escape_dollars(normalise_math_delimiters(reading))
    assert out.startswith(r"And \(\int")
    assert "\\$" not in out


def test_an_already_escaped_dollar_is_not_a_delimiter():
    assert normalise_math_delimiters(r"costs \$5 and \$6") == r"costs \$5 and \$6"


def test_text_without_dollars_is_untouched():
    for text in ("", "plain prose", r"\(already ours\)"):
        assert normalise_math_delimiters(text) == text


def test_a_lone_dollar_is_not_a_delimiter():
    assert normalise_math_delimiters("a $ sign alone") == "a $ sign alone"


def test_an_equation_with_no_command_in_it_is_still_maths():
    """From the same page: "let $p=x$ $dp = dx$" has no command and no script, and without the equals
    sign in the test those two equations were escaped into literal text (12 September)."""
    got = normalise_math_delimiters(r"let $p=x$    $dp = dx$, and so on")
    assert got == r"let \(p=x\)    \(dp = dx\), and so on"


def test_an_equals_sign_does_not_make_money_into_maths():
    # a price range has no equals sign between its two dollars
    assert normalise_math_delimiters("between $5 and $6") == "between $5 and $6"
