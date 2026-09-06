"""Italic theorem prose inside a formula becomes a text run; italic variables do not."""
from truedoc.math.reconstruct import glyph, reconstruct
from truedoc.model import BBox


def _letters(text: str, x0: float, font: str, size: float = 10.0, oy: float = 100.0) -> list:
    out = []
    x = x0
    for ch in text:
        if ch == " ":
            x += 0.35 * size
            continue
        out.append(glyph(ch, font, size, BBox(x, oy - 0.7 * size, x + 0.5 * size, oy + 0.2 * size), oy))
        x += 0.5 * size
    return out


def test_italic_words_become_text():
    gs = _letters("n", 100, "CMMI10") + _letters("is predictable and", 108, "CMTI10") + _letters("x", 210, "CMMI10")
    latex, _ = reconstruct(gs, [])
    assert "\\text{is predictable and}" in latex, latex
    assert latex.startswith("n"), latex


def test_two_italic_letters_stay_variables():
    gs = _letters("xy", 100, "NimbusRomNo9L-ReguItal")
    latex, _ = reconstruct(gs, [])
    assert "\\text" not in latex, latex
    assert "x" in latex and "y" in latex
