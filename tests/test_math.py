"""Formula reconstruction on hand-built glyph layouts (no PDF needed)."""

from truedoc.math.reconstruct import glyph, reconstruct
from truedoc.model import BBox


def g(ch, x, baseline, size=10.0, font="CMR10", w=None):
    w = w or 0.5 * size
    return glyph(ch, font, size, BBox(x, baseline - 0.7 * size, x + w, baseline + 0.2 * size), baseline)


def test_subscript_and_superscript():
    gs = [g("x", 0, 100, font="CMMI10"), g("i", 5.5, 102, size=7, font="CMMI7"), g("2", 9, 96, size=7, font="CMR7")]
    latex, _ = reconstruct(gs, [])
    assert latex == "x_{i}^{2}"


def test_fraction_from_rule():
    num = [g("a", 12, 90, font="CMMI10")]
    den = [g("b", 12, 110, font="CMMI10")]
    gs = [g("y", 0, 100, font="CMMI10"), g("=", 6, 100)] + num + den
    latex, _ = reconstruct(gs, [BBox(10, 97.5, 20, 98)])
    assert latex == r"y= \frac{a}{b}"


def test_sqrt_from_radical_and_rule():
    radical = glyph("q", "CMEX10", 10.0, BBox(0, 91, 6, 103), 91.5)  # cmex radical: top at the rule
    gs = [radical, g("x", 7, 100, font="CMMI10")]
    latex, _ = reconstruct(gs, [BBox(6.5, 91, 13, 91.4)])
    assert latex == r"\sqrt{x}"


def test_greek_and_symbols():
    gs = [g("ψ", 0, 100, font="CMMI10"), g("→", 8, 100, font="CMSY10"), g("∞", 16, 100, font="CMSY10")]
    latex, _ = reconstruct(gs, [])
    assert latex == r"\psi\rightarrow\infty"


def test_integral_limits_by_visual_centre():
    # cmex integral: origin at the top, glyph hanging below; limits sit to the upper and lower right
    integral = glyph("Z", "CMEX10", 10.0, BBox(0, 100, 6, 118), 100.5)
    upper = g("b", 7, 99, size=7, font="CMMI7")
    lower = g("a", 7, 121, size=7, font="CMMI7")
    body = g("x", 14, 109, font="CMMI10")
    latex, _ = reconstruct([integral, upper, lower, body], [])
    assert latex == r"\int_{a}^{b}x"


def test_equation_number_stripped():
    gs = [g("x", 0, 100, font="CMMI10"), g("(", 200, 100), g("3", 205, 100), g(")", 210, 100)]
    latex, eq = reconstruct(gs, [])
    assert latex == "x" and eq == "3"


def test_dots_normalised():
    gs = [g("a", 0, 100, font="CMMI10"), g("·", 6, 100, font="CMSY10"), g("·", 9, 100, font="CMSY10"), g("·", 12, 100, font="CMSY10"), g("b", 16, 100, font="CMMI10")]
    latex, _ = reconstruct(gs, [])
    assert latex == r"a\cdots b"


def test_matrix_from_tall_parens():
    # The text layer recodes cmex's size-4 "(" (code 0x20, a space) onto a private-use
    # character, so that a plain space in the font can stay the blank MuPDF inserts.
    lp = glyph(chr(0xE000 + 0x20), "CMEX10", 10.0, BBox(0, 88, 4, 122), 88.5)   # size-4 "(" (3em tall by design)
    rp = glyph("\x21", "CMEX10", 10.0, BBox(30, 88, 34, 122), 88.5)  # size-4 ")"  # tall ")"
    cells = [g("a", 8, 100, font="CMMI10"), g("b", 22, 100, font="CMMI10"), g("c", 8, 114, font="CMMI10"), g("d", 22, 114, font="CMMI10")]
    latex, _ = reconstruct([lp, rp] + cells, [])
    assert latex == r"\begin{pmatrix} a & b \\ c & d \end{pmatrix}"


def test_function_word_with_limits_below():
    # "lim" set upright with "n → ∞" underneath, as in display style
    l = g("l", 0, 100); i_ = g("i", 5, 100); m = g("m", 10, 100)
    n = g("n", 2, 109, size=7, font="CMMI7"); arrow = g("→", 7, 109, size=7, font="CMSY7"); inf = g("∞", 13, 109, size=7, font="CMSY7")
    x = g("x", 22, 100, font="CMMI10")
    latex, _ = reconstruct([l, i_, m, n, arrow, inf, x], [])
    assert latex == r"\lim_{n\rightarrow\infty}x"


def test_bare_radical_takes_next_argument():
    radical = glyph("q", "CMEX10", 10.0, BBox(0, 91, 6, 103), 91.5)
    n = g("n", 7, 100, font="CMMI10")
    latex, _ = reconstruct([radical, n], [])
    assert latex == r"\sqrt{n}"


def test_group_of_only_big_delimiters_does_not_crash():
    # Two tall cmex parentheses with a small fraction between them and no full-size letters.
    lp = glyph("\x20", "CMEX10", 10.0, BBox(0, 88, 4, 122), 88.5)   # size-4 "(" (3em tall by design)
    rp = glyph("\x21", "CMEX10", 10.0, BBox(30, 88, 34, 122), 88.5)  # size-4 ")"
    num = g("a", 14, 96, size=7, font="CMMI7"); den = g("b", 14, 112, size=7, font="CMMI7")
    latex, _ = reconstruct([lp, rp, num, den], [BBox(12, 102.5, 22, 103)])
    # Whether read as a fraction or a one-column matrix, it must come back intact.
    assert "a" in latex and "b" in latex


def test_lim_inf_is_one_operator():
    l = g("l", 0, 100); i_ = g("i", 5, 100); m = g("m", 10, 100)
    n_ = g("i", 17, 100); f = g("n", 22, 100); s = g("f", 27, 100)
    x = g("x", 36, 100, font="CMMI10")
    latex, _ = reconstruct([l, i_, m, n_, f, s, x], [])
    assert latex == r"\liminf x"


def test_accent_at_same_baseline_attaches_to_overlapping_letter():
    # TeX places the hat glyph at the letter's own baseline; the boxes simply overlap.
    hat = g("ˆ", 5.2, 100, font="CMR10")
    tau = g("τ", 5.0, 100, font="CMMI10")
    comma = g(",", 10.5, 100)
    latex, _ = reconstruct([hat, tau, comma], [])
    assert latex == r"\hat{\tau},"


def test_two_stacked_rows_become_one_aligned_block():
    from truedoc.math.extract import display_formula_blocks
    from truedoc.model import Page

    page = Page(number=1, width=600, height=800)
    page.body_font_size = 10.0
    row1 = [g("a", 100, 300, font="CMMI10"), g("=", 108, 300), g("b", 118, 300, font="CMMI10")]
    row2 = [g("c", 100, 314, font="CMMI10"), g("=", 108, 314), g("d", 118, 314, font="CMMI10")]
    from truedoc.model import Char

    page.chars = [Char(text=x.ch, bbox=x.bbox, font=x.font, size=x.size, origin_y=x.oy) for x in row1 + row2]
    blocks = display_formula_blocks(page, [BBox(90, 285, 140, 325)])
    assert len(blocks) == 1
    assert blocks[0].text_override == r"\[\begin{aligned} a&=b \\ c&=d \end{aligned}\]"


def test_upright_prose_inside_a_formula_becomes_text():
    # "x = 0 for all x" with "for all" in the upright text font, spaced as words.
    gs = [g("x", 0, 100, font="CMMI10"), g("=", 8, 100), g("0", 18, 100)]
    x = 30.0
    for word in ("for", "all"):
        for ch in word:
            gs.append(g(ch, x, 100, font="CMR10"))
            x += 5.0
        x += 3.5
    gs.append(g("x", x + 2, 100, font="CMMI10"))
    latex, _ = reconstruct(gs, [])
    assert latex == r"x=0\text{for all}x"
