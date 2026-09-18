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
    # Until 18 September a bare letter was "not obviously maths" and stayed between dollars; the algebra
    # pages below showed that a model writes $z$ only when it means the variable z.
    got = normalise_math_delimiters(r"$x^2$ and $y_1$ and $z$")
    assert got == r"\(x^2\) and \(y_1\) and \(z\)"


def test_a_variable_or_a_function_of_one_is_maths_without_any_command():
    """old_scans_math/4_pg380 (18 September): an algebra textbook's "$f(x)$", "$P$", "$f(1)$" have no
    command, no script and no equals sign, and escaping them into text cost three checks on the page
    with every reader that writes maths between dollars."""
    got = normalise_math_delimiters(r"denoted by symbols of the form $f(x)$ , $P(x)$ , etc., and $P$ function of x; find $f(1)$ , $f(-1)$ .")
    assert got == r"denoted by symbols of the form \(f(x)\) , \(P(x)\) , etc., and \(P\) function of x; find \(f(1)\) , \(f(-1)\) ."


def test_an_expression_of_letters_and_brackets_is_maths():
    # old_scans_math/4_pg48: four checks lost the same way
    got = normalise_math_delimiters(r"12. $a + [b - (a - b)]$ . 17. $- [m - (m + n) - (m - n) - (-m + n)]$")
    assert got == r"12. \(a + [b - (a - b)]\) . 17. \(- [m - (m + n) - (m - n) - (-m + n)]\)"


def test_a_function_name_counts_as_maths_but_an_english_word_does_not():
    assert normalise_math_delimiters(r"so $\sin x$ and $log n$ and $x$") == r"so \(\sin x\) and \(log n\) and \(x\)"
    # a word between two prices is prose, and a number followed by a word is a price
    for prose in ("between $5 and $6", "$5 or $6", "$5 a $10 item", "$5 a day, $6 a week", "from $5, $6 and $7"):
        assert normalise_math_delimiters(prose) == prose, prose


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


def test_an_aligned_column_of_equations_is_one_display_formula_per_row():
    r"""old_scans_math/3_pg39 (18 September): the page prints three equations one under another, a
    model transcribes them as one aligned environment, and the reference holds each on its own."""
    reading = r"of the form $$\begin{aligned} x' &= ax + by + cz \\ y' &= dx + ey + fz \\ z' &= gx + hy + kz \end{aligned}$$ where"
    got = normalise_math_delimiters(reading)
    assert got == "of the form \\[x' = ax + by + cz\\]\n\n\\[y' = dx + ey + fz\\]\n\n\\[z' = gx + hy + kz\\] where"


def test_a_row_continuing_a_derivation_keeps_its_leading_equals_sign():
    got = normalise_math_delimiters(r"$$\begin{aligned} \int f &= \frac{1}{a} \\ &= \frac{2}{b} \end{aligned}$$")
    assert got == "\\[\\int f = \\frac{1}{a}\\]\n\n\\[= \\frac{2}{b}\\]"


def test_a_matrix_or_a_cases_brace_is_not_split():
    for body in (r"\begin{pmatrix} a & b \\ c & d \end{pmatrix}", r"f(x) = \begin{cases} 1 & x > 0 \\ 0 & x \le 0 \end{cases}"):
        assert normalise_math_delimiters("$$" + body + "$$") == "\\[" + body + "\\]"


def test_an_aligned_environment_with_one_row_is_left_alone():
    body = r"\begin{aligned} a &= b \end{aligned}"
    assert normalise_math_delimiters("$$" + body + "$$") == "\\[" + body + "\\]"


def test_an_expression_a_model_split_at_an_operator_is_joined():
    r"""old_scans_math/4_pg48: "$...- 7n\}$ $+ [9m - (3n + 4m) + 14n]$" is one sum on the page."""
    got = normalise_math_delimiters(r"28. $6m + \{4m - 7n\}$ $+ [9m - (3n + 4m) + 14n]$ . 29.")
    assert got == r"28. \(6m + \{4m - 7n\} + [9m - (3n + 4m) + 14n]\) . 29."
    got = normalise_math_delimiters(r"$a + b +$ $c$ and $x$ $y$")
    assert got == r"\(a + b + c\) and \(x\) \(y\)", "a seam without an operator may be two things"


def test_an_equation_number_on_a_row_of_its_own_stays_with_its_equation():
    # multi_column/0353b31c...: a model sets "& (12)" as the last row of the environment
    reading = r"$$\begin{aligned} \pi(t) &= \sum t_w w \\ &\quad - \sum t_w \xi \\ &\quad (12) \end{aligned}$$"
    got = normalise_math_delimiters(reading)
    assert got == "\\[\\pi(t) = \\sum t_w w\\]\n\n\\[\\quad - \\sum t_w \\xi \\quad (12)\\]"


def test_an_aligned_column_followed_by_an_alternative_in_brackets_is_split_too():
    # old_scans_math/3_pg39's second column: the bracketed "or" case after the environment is a
    # formula of its own, and the column's rows still come out one by one
    reading = r"$$\begin{aligned} A' &= a'A + d'B \\ B' &= b'A + e'B \end{aligned} & \left( \text{or} \quad A' = a'A \right)$$"
    got = normalise_math_delimiters(reading)
    assert got == "\\[A' = a'A + d'B\\]\n\n\\[B' = b'A + e'B\\]\n\n\\[\\left( \\text{or} \\quad A' = a'A \\right)\\]"
