"""A zero-width combining mark finds its letter whichever reader placed it (2503.06329 page 24).

MnSymbol's tilde has no advance and is drawn as a text object of its own, raised over the letter
it covers. PDFium reports it there; MuPDF's text moves it to where the previous glyph ended, on
that glyph's baseline (MuPDF's own glyph trace draws it at 273.6, 248.0; its text says 271.2,
250.8). The rows below are the page's "x R~ a1a5 =" at its measured positions, once as each
reader reports them."""
from truedoc.math.reconstruct import _attach_accents, glyph
from truedoc.model import BBox

SIZE = 10.91
BASE = 250.8


def _row(mark_x: float, mark_oy: float):
    times = glyph("×", "MnSymbol10", SIZE, BBox(264.6, 243.5, 271.2, 253.3), BASE)
    r = glyph("R", "CMMI10", SIZE, BBox(271.9, 243.0, 280.2, 253.2), BASE)
    mark = glyph("̃", "MnSymbol10", SIZE, BBox(mark_x, mark_oy - 16.7, mark_x, mark_oy + 11.2), mark_oy)
    a = glyph("a", "CMMI8", 7.97, BBox(280.2, 246.8, 284.7, 254.1), 252.5)
    one = glyph("1", "CMR6", 5.98, BBox(284.6, 249.5, 288.3, 253.7), 253.6)
    eq = glyph("=", "CMR10", SIZE, BBox(296.0, 243.5, 304.5, 253.3), BASE)
    return [times, r, mark, a, one, eq], r


def test_a_mark_drawn_over_its_letter_takes_that_letter():
    """PDFium: the tilde where it is drawn, 1.7pt inside the italic R and 2.8pt above its baseline.
    The rule for a moved mark - the next glyph to the right, from 0.15 em left of the mark -
    refused the R and hung the tilde on the "=" after the R's subscript."""
    gs, r = _row(273.6, 248.04)
    _, accents = _attach_accents(gs)
    assert accents == {id(r): "tilde"}, accents


def test_a_mark_moved_to_the_previous_glyphs_end_takes_the_next_letter():
    """MuPDF: the same tilde at the end of the times sign, on the line's baseline."""
    gs, r = _row(271.2, BASE)
    _, accents = _attach_accents(gs)
    assert accents == {id(r): "tilde"}, accents
