"""Two columns' halves of a joined line stay apart whichever sorts first.

MuPDF joins a left-column line and a right-column line across a narrow gutter; the gutter
splitter parts them again, and the re-joiner must not glue them back. It did when the right
half sorted first (its baseline a tenth of a point higher, as a maths glyph's often is): the
gap then measured negative, the gutter test was skipped, and the "interleaved formula"
path joined the two (0145cc39b0, 0853d8a05f, 0904c70713 in run 61). The gutter test now
asks whether the two halves lie on opposite sides of a gutter, whatever their order.
"""
from tests.test_columns import line, two_column_page, word
from truedoc.extract.textlayer import _column_gutters, _reassemble_lines
from truedoc.model import BBox, Char


def _halves(oy):
    left = line(*(word(t, x, oy) for t, x in (("refractive", 130), ("index", 190), ("is", 222), ("modu-", 238))))
    right_words = [word(t, x, oy - 0.06) for t, x in (("vector", 262), ("k", 300), ("to", 312), ("photons", 330))]
    # a maths-font glyph on the right half: the formula path is what used to join them
    k = right_words[1]
    k.chars[0] = Char(text="k", bbox=BBox(300, oy - 7, 305, oy + 2), font="CMMI10", size=10.0, origin_y=oy - 0.06)
    right = line(*right_words)
    return left, right


def test_halves_on_either_side_of_a_gutter_stay_apart_whichever_sorts_first():
    lines = two_column_page(rows=20)
    left, right = _halves(100 + 12 * 20)
    lines += [right, left]
    gutters = _column_gutters(lines)
    assert len(gutters) == 1
    out = _reassemble_lines(lines, gutters)
    texts = [l.text for l in out]
    assert "refractive index is modu-" in texts and "vector k to photons" in texts, [t for t in texts if "modu" in t or "vector" in t]
