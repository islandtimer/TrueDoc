"""Equation numbers on either margin are taken off the formula."""
from truedoc.math.reconstruct import _strip_equation_number, glyph
from truedoc.model import BBox


def _row(text: str, x0: float, size: float = 10.0, font: str = "CMR10") -> list:
    out = []
    x = x0
    for ch in text:
        out.append(glyph(ch, font, size, BBox(x, 100, x + 0.5 * size, 110), 108))
        x += 0.5 * size
    return out


def test_number_on_the_right_is_stripped():
    gs = _row("x=y", 100) + _row("(3.1)", 300)
    rest, number = _strip_equation_number(gs)
    assert number == "3.1"
    assert "".join(g.ch for g in rest) == "x=y"


def test_number_on_the_left_is_stripped():
    gs = _row("(3.12)", 60) + _row("x=y", 200)
    rest, number = _strip_equation_number(gs)
    assert number == "3.12"
    assert "".join(g.ch for g in rest) == "x=y"


def test_bracketed_start_close_to_the_formula_stays():
    gs = _row("(1.2)", 100) + _row("x=y", 130)
    rest, number = _strip_equation_number(gs)
    assert number == ""
    assert len(rest) == len(gs)
