"""Inline maths detection on hand-built text lines."""

from truedoc.math.extract import inline_math_text
from truedoc.model import BBox, Char, Line, Word


def _word(text, x, font="NimbusRomNo9L-Regu", size=10.0, baseline=100.0, sizes=None):
    chars = []
    for i, ch in enumerate(text):
        sz = sizes[i] if sizes else size
        oy = baseline + (1.8 if sz < size else 0.0)
        chars.append(Char(text=ch, bbox=BBox(x + i * 5, oy - 0.7 * sz, x + (i + 1) * 5, oy + 0.2 * sz), font=font, size=sz, origin_y=oy))
    return Word(text=text, bbox=BBox(x, baseline - 0.7 * size, x + 5 * len(text), baseline + 0.2 * size), chars=chars)


def _line(words):
    return Line(words=words, bbox=BBox.union_all(w.bbox for w in words))


def test_plain_prose_untouched():
    line = _line([_word("In", 0), _word("2018,", 20), _word("12-15", 60), _word("cases", 100)])
    assert inline_math_text(line, []) == "In 2018, 12-15 cases"


def test_math_run_wrapped_and_punctuation_kept_outside():
    line = _line([_word("when", 0), _word("ψ", 30, font="CMMI10"), _word("→", 40, font="CMSY10"), _word("0,", 50), _word("we", 70)])
    out = inline_math_text(line, [])
    assert out == "when \\(\\psi\\rightarrow0\\), we"


def test_glued_prose_trimmed():
    line = _line([_word("length", 0), _word("nthat", 40, font="CMMI10"), _word("remains", 80)])
    # "n" (maths italic) glued to "that" (text font)
    w = line.words[1]
    for c in w.chars[1:]:
        c.font = "NimbusRomNo9L-Regu"
    out = inline_math_text(line, [])
    assert out == "length \\(n\\)that remains"


def test_colon_equals_bridges_two_maths_words():
    line = _line([_word("Let", 0), _word("K", 20, font="CMMI10"), _word(":=", 30), _word("C", 45, font="CMMI10"), _word("hold.", 60)])
    out = inline_math_text(line, [])
    assert out == "Let \\(K:=C\\) hold."
