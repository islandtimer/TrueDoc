"""Three periods: TeX's \\ldots spaces them about 0.4 em apart; a typed "..." packs
them at the period's own width (0.28 em). The references keep the author's spelling."""
from truedoc.math.reconstruct import glyph, reconstruct
from truedoc.model import BBox


def g(ch, x, baseline, size=10.0, font="CMR10", w=None):
    w = w if w is not None else 0.5 * size
    return glyph(ch, font, size, BBox(x, baseline - 0.7 * size, x + w, baseline + 0.2 * size), baseline)


def test_spaced_periods_are_ldots():
    gs = [g("a", 0, 100, font="CMMI10"), g(".", 8, 100, w=2.8), g(".", 12.2, 100, w=2.8), g(".", 16.4, 100, w=2.8), g("b", 22, 100, font="CMMI10")]
    latex, _ = reconstruct(gs, [])
    assert latex == r"a\ldots b"


def test_touching_periods_are_typed_dots():
    gs = [g("a", 0, 100, font="CMMI10"), g(".", 8, 100, w=2.8), g(".", 10.8, 100, w=2.8), g(".", 13.6, 100, w=2.8), g("b", 19, 100, font="CMMI10")]
    latex, _ = reconstruct(gs, [])
    assert latex == "a...b"
