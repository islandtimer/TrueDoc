"""Re-joining lines that a PDF producer emitted word by word."""

from truedoc.extract.textlayer import _reassemble_lines
from truedoc.model import BBox, Char, Line, Word


def _seg(text, x0, baseline, size=8.0, cw=4.0):
    words = []
    x = x0
    for tok in text.split():
        chars = [Char(text=c, bbox=BBox(x + i * cw, baseline - 0.8 * size, x + (i + 1) * cw, baseline + 0.2 * size), font="Times", size=size, origin_y=baseline) for i, c in enumerate(tok)]
        words.append(Word(text=tok, bbox=BBox(x, baseline - 0.8 * size, x + cw * len(tok), baseline + 0.2 * size), chars=chars))
        x += cw * len(tok) + cw
    return Line(words=words, bbox=BBox(x0, baseline - 0.8 * size, x - cw, baseline + 0.2 * size))


def test_word_by_word_justified_line_is_rejoined():
    # Eight single-word segments with a uniform stretched gap of 1.03 em.
    words = "Analyses were carried out using the standard image".split()
    x = 40.0
    segs = []
    for w in words:
        segs.append(_seg(w, x, 100.0))
        x += 4.0 * len(w) + 8.2
    out = _reassemble_lines(segs)
    assert len(out) == 1
    assert out[0].text == "Analyses were carried out using the standard image"


def test_margin_number_is_not_joined_to_the_line():
    number = _seg("419", 5.0, 100.0, size=6.0)
    body = _seg("body text of the line", 40.0, 100.0)
    out = _reassemble_lines([number, body])
    assert len(out) == 2


def test_table_cells_stay_separate():
    a = _seg("Jagger", 80.0, 100.0)
    b = _seg("23.0", 176.0, 100.0)   # gap of about 8 em
    out = _reassemble_lines([a, b])
    assert len(out) == 2
