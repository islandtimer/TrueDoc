"""Units, measurements and Greek-lettered names in the text fonts are prose, not inline maths.

"1.54 μm", "≤260 μm", "IFN-γ" and "37 °C" sit in ordinary sentences of nineteen multi-column
pages whose checks failed in run 59 because the detector wrapped the Greek letter or the
relation sign in \\(...\\). A glyph from a maths font is still maths, and a lone Greek letter in
the text fonts (a variable) still is.
"""
from truedoc.math.extract import inline_math_text
from truedoc.model import BBox, Char, Line, Word

SIZE = 10.0


def _line(tokens, font="Times-Roman"):
    words = []
    x = 50.0
    for tok, f in tokens:
        cw = 5.0
        chars = [Char(text=c, bbox=BBox(x + i * cw, 100, x + (i + 1) * cw, 110), font=f, size=SIZE, origin_y=108) for i, c in enumerate(tok)]
        words.append(Word(text=tok, bbox=BBox(x, 100, x + cw * len(tok), 110), chars=chars))
        x += cw * len(tok) + cw
    return Line(words=words, bbox=BBox(50, 100, x, 110))


def test_measurements_and_units_stay_plain():
    line = _line([("intensity", "Times-Roman"), ("of", "Times-Roman"), ("1.54", "Times-Roman"), ("μm", "Symbol"), ("in", "Times-Roman")])
    assert inline_math_text(line, []) == "intensity of 1.54 μm in"
    line = _line([("distance", "Times-Roman"), ("≤260", "Symbol"), ("μm", "Symbol"), ("on", "Times-Roman")])
    assert "\\(" not in inline_math_text(line, [])
    line = _line([("at", "Times-Roman"), ("37", "Times-Roman"), ("°C", "Symbol"), ("overnight", "Times-Roman")])
    assert "\\(" not in inline_math_text(line, [])
    line = _line([("one", "Times-Roman"), ("≤5-year-old", "Symbol"), ("child", "Times-Roman")])   # a relation with a hyphenated tail
    assert "\\(" not in inline_math_text(line, [])


def test_greek_lettered_names_stay_plain():
    for name in ("IFN-γ", "TNF-α", "β-catenin"):
        line = _line([("increased", "Times-Roman"), (name, "Symbol"), ("levels", "Times-Roman")])
        assert "\\(" not in inline_math_text(line, []), name


def test_real_maths_is_still_maths():
    line = _line([("where", "Times-Roman"), ("λ", "CMMI10"), ("is", "Times-Roman")])
    assert "\\(" in inline_math_text(line, [])
    line = _line([("for", "Times-Roman"), ("λ", "Symbol"), ("we", "Times-Roman")])      # a lone Greek letter: a variable
    assert "\\(" in inline_math_text(line, [])
