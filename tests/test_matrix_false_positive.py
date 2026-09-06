"""Tall parentheses around an operator with limits are not a matrix."""
from truedoc.math.reconstruct import glyph, reconstruct
from truedoc.model import BBox


def _g(ch, x0, y0, x1, y1, oy, font="CMMI10", size=10.0):
    return glyph(ch, font, size, BBox(x0, y0, x1, y1), oy)


# A \bigg( from cmex: its origin sits near the top of the glyph, and glyph()
# rebuilds its box from the font's extents (about 2.4 em tall).
def _paren(ch, x0):
    return _g(ch, x0, 84, x0 + 6, 108, 90, font="CMEX10")


def test_sum_with_limits_inside_tall_parens_is_not_a_matrix():
    # \left( \sum_{i=1}^{n} a_i \right): the sum sign has its own baseline, the
    # limits are script-sized rows above and below it, the summand sits on the
    # main line at the height of the sign's middle.
    gs = [
        _paren("\x12", 100),
        _g("X", 110, 92, 122, 110, 92, font="CMEX10"),              # display sum sign
        _g("n", 114, 82, 118, 88, 88, font="CMMI7", size=7.0),      # upper limit
        _g("i", 111, 112, 114, 118, 118, font="CMMI7", size=7.0),   # lower limit
        _g("=", 114, 112, 118, 118, 118, font="CMR7", size=7.0),
        _g("1", 118, 112, 122, 118, 118, font="CMR7", size=7.0),
        _g("a", 126, 96, 132, 104, 104),                             # summand on the main line
        _g("i", 132, 102, 135, 107, 107, font="CMMI7", size=7.0),
        _paren("\x13", 138),
    ]
    latex, _ = reconstruct(gs, [])
    assert "matrix" not in latex, latex
    assert "\\sum" in latex, latex


def test_two_text_rows_inside_tall_parens_is_a_matrix():
    gs = [
        _paren("\x12", 100),
        _g("1", 112, 88, 118, 98, 98, font="CMR10"),
        _g("0", 126, 88, 132, 98, 98, font="CMR10"),
        _g("0", 112, 104, 118, 114, 114, font="CMR10"),
        _g("1", 126, 104, 132, 114, 114, font="CMR10"),
        _paren("\x13", 138),
    ]
    latex, _ = reconstruct(gs, [])
    assert "pmatrix" in latex, latex
