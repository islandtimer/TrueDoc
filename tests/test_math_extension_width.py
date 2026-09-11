"""A maths-extension glyph keeps the ink's height and takes the metric box's width (2503.03905 page 7).

The ink is used for these glyphs because the font box is one line tall where the drawn bracket is
three; it measures the height. Its left edge follows the shape, though: the middle piece of a brace
has its point 3pt left of the other pieces. The merge that stacks an extensible bracket's pieces
sorts them by the left edge and needs neighbours within 0.15 em of each other, so the middle piece
sorted first, the run broke at once, and the brace read as three - one brace per row where MuPDF,
whose design boxes start at the metric box, builds one cases environment (four arXiv pages)."""
from truedoc.extract.textlayer import _extension_box
from truedoc.math.reconstruct import _merge_extensible_pieces, glyph
from truedoc.model import BBox, Char

SIZE = 12.0
X0, X1 = 262.3, 273.1          # every piece's metric box, left and right
TOP, EXTENDER, MIDDLE, BOTTOM = "\uf8f1", "\uf8f4", "\uf8f2", "\uf8f3"   # cmex's brace pieces: top, extender, middle, bottom


def _piece(ch: str, ink_x0: float, ink_x1: float, y0: float, y1: float, oy: float):
    return glyph(ch, "CMEX10", SIZE, BBox(X0, y0 - 0.5, X1, y0 + 35.4), oy, BBox(ink_x0, y0, ink_x1, y1))


def _brace():
    """The five pieces of the page's brace as PDFium reports them: metric box, ink box, origin."""
    return [
        _piece(TOP, 267.0, 271.0, 492.8, 503.7, 492.8),
        _piece(EXTENDER, 267.0, 268.0, 503.5, 507.3, 503.6),
        _piece(MIDDLE, 264.0, 268.0, 507.1, 528.8, 507.2),     # its point further left
        _piece(EXTENDER, 267.0, 268.0, 528.6, 532.4, 528.7),
        _piece(BOTTOM, 267.0, 271.0, 532.2, 543.0, 532.3),
    ]


def test_an_extension_glyph_keeps_the_ink_height_and_the_metric_width():
    middle = _brace()[2]
    assert (middle.bbox.x0, middle.bbox.x1) == (X0, X1), middle.bbox
    assert (middle.bbox.y0, middle.bbox.y1) == (507.1, 528.8), middle.bbox


def test_a_brace_drawn_in_five_pieces_is_one_brace():
    merged = _merge_extensible_pieces(_brace())
    assert len(merged) == 1, [(g.latex, g.bbox) for g in merged]
    assert merged[0].bbox.y0 == 492.8 and merged[0].bbox.y1 == 543.0, merged[0].bbox


def test_the_text_layers_box_for_an_extension_glyph_is_as_wide_as_its_metric_box():
    """The text layer gives every maths-extension glyph this box before any line is built; the
    maths stage then starts from it."""
    c = Char(text=MIDDLE, bbox=BBox(X0, 506.7, X1, 542.6), font="CMEX10", size=SIZE, origin_y=507.2,
             ink=BBox(264.0, 507.1, 268.0, 528.8))
    box = _extension_box(c)
    assert (box.x0, box.x1) == (X0, X1), box
    assert (box.y0, box.y1) == (507.1, 528.8), box
