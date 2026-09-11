"""An accent found by baselines takes the glyph whose centre is nearest its own (2503.05183 page 15).

The hat of \\hat{\\lambda}_4 sits over the lambda, the "2" of "2\\hat{\\lambda}_4" just before it. MuPDF's
boxes are the font's full height, the lambda's top clears the hat's middle, and the glyph directly below
takes the hat. PDFium's metric boxes keep the lambda's top a quarter of a point below the hat's middle,
so the rule by baselines decides - and it took the first glyph that qualified, the "2". The rows are
the page's "( 2 ^ lambda 4" at its measured positions, once as each reader reports them."""
from truedoc.math.reconstruct import _attach_accents, glyph
from truedoc.model import BBox

BASE = 563.2


def _row(boxes: dict):
    paren = glyph("(", "CMR10", 10.0, BBox(*boxes["("]), BASE)
    two = glyph("2", "NimbusRomNo9L-Regu", 10.0, BBox(*boxes["2"]), BASE)
    hat = glyph("ˆ", "NimbusRomNo9L-Regu", 10.0, BBox(*boxes["hat"]), 560.3)
    lam = glyph("λ", "StandardSymL-Slant_167", 10.0, BBox(*boxes["lambda"]), BASE)
    four = glyph("4", "NimbusRomNo9L-Regu", 7.4, BBox(*boxes["4"]), 564.7)
    return [paren, two, hat, lam, four], two, lam


PDFIUM = {"(": (88.9, 556.3, 92.8, 565.2), "2": (92.8, 556.5, 97.8, 565.4), "hat": (98.8, 553.5, 102.1, 562.4),
          "lambda": (97.8, 558.2, 103.3, 565.6), "4": (103.3, 559.7, 107.0, 566.3)}
MUPDF = {"(": (88.9, 555.4, 92.8, 565.4), "2": (92.8, 555.6, 97.8, 565.6), "hat": (98.8, 552.7, 102.1, 562.7),
         "lambda": (97.8, 556.4, 103.3, 566.4), "4": (103.3, 559.1, 107.0, 566.5)}


def test_a_hat_over_a_lambda_after_a_digit_takes_the_lambda_with_pdfium_boxes():
    gs, two, lam = _row(PDFIUM)
    _, accents = _attach_accents(gs)
    assert id(lam) in accents and id(two) not in accents, accents


def test_the_same_hat_with_mupdf_boxes_takes_the_lambda_too():
    gs, two, lam = _row(MUPDF)
    _, accents = _attach_accents(gs)
    assert id(lam) in accents and id(two) not in accents, accents
