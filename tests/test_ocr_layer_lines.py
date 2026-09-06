"""Line reassembly for hidden OCR layers (archive.org style: one text object per phrase)."""

from truedoc.extract.textlayer import _reassemble_ocr_layer
from truedoc.model import BBox, Char, Line, Word


def _seg(text, x0, y0, h=8.0, cw=4.0):
    words = []
    x = x0
    for tok in text.split():
        chars = [Char(text=c, bbox=BBox(x + i * cw, y0, x + (i + 1) * cw, y0 + h), font="OCR", size=5.0, origin_y=y0 + h) for i, c in enumerate(tok)]
        words.append(Word(text=tok, bbox=BBox(x, y0, x + cw * len(tok), y0 + h), chars=chars))
        x += cw * len(tok) + cw
    return Line(words=words, bbox=BBox(x0, y0, x - cw, y0 + h))


def test_phrases_on_one_line_are_joined():
    lines = [_seg("PESTERED.", 20, 100), _seg("Crowded.", 62, 100), _seg("Peele,", 100, 100)]
    out = _reassemble_ocr_layer(lines)
    assert len(out) == 1 and out[0].text == "PESTERED. Crowded. Peele,"


def test_two_columns_are_not_joined():
    # Ten rows; each row has a left phrase ending near x=118 and a right phrase starting near x=126.
    lines = []
    for r in range(10):
        y = 100 + r * 10
        lines.append(_seg("left column text here", 20, y))
        lines.append(_seg("right column text here", 126, y))
    out = _reassemble_ocr_layer(lines)
    assert len(out) == 20
    assert all(("left" in l.text) != ("right" in l.text) for l in out)
