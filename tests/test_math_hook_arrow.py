"""cmmi's left hook touching an arrow is \\hookrightarrow, whichever reader named it (2503.06194 page 10).

TeX draws the arrow as cmmi's hook (slot 0x2C) touching cmsy's arrow. MuPDF's text reports the hook
as a comma; PDFium names the glyph and reports U+21AA, and the page read "Z^d ↪ \\rightarrow Z_p^d".
The pair below is the page's, at its measured positions."""
from truedoc.math.reconstruct import _merge_mapsto, glyph
from truedoc.model import BBox

HOOK_PDFIUM, HOOK_MUPDF = "↪", ","
SIZE = 11.96
BASE = 445.7


def _pair(hook: str):
    h = glyph(hook, "CMMI12", SIZE, BBox(414.6, 437.4, 417.9, 448.0), BASE)
    arrow = glyph("→", "CMSY10", SIZE, BBox(415.9, 436.7, 427.8, 448.0), BASE)
    return [h, arrow]


def test_the_hook_as_pdfium_names_it_makes_a_hookrightarrow():
    out = _merge_mapsto(_pair(HOOK_PDFIUM))
    assert [g.latex for g in out] == [r"\hookrightarrow"], [(g.ch, g.latex) for g in out]


def test_the_hook_as_mupdf_reports_it_makes_a_hookrightarrow():
    out = _merge_mapsto(_pair(HOOK_MUPDF))
    assert [g.latex for g in out] == [r"\hookrightarrow"], [(g.ch, g.latex) for g in out]
