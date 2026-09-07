"""A TeX Gyre text face is not a maths font; only the TeX Gyre Math faces are.

The newtx package sets body text in TeX Gyre Termes ("TeXGyreTermesX-Regular"). The hint
"TEXGYRE" in the maths-font list called every character of such a page maths, so the
display-maths test saw no ordinary words and turned a whole page of prose into one formula
with its spaces stripped (arXiv 2503.08283 page 7, found by the conservation census of
7 Sept 2026).
"""
from truedoc.math.reconstruct import is_math_font


def test_tex_gyre_text_faces_are_text():
    for name in ("TeXGyreTermesX-Regular", "TeXGyreTermesX-Bold", "TeXGyreHeros-Regular", "TeXGyrePagella-Italic", "ABCDEF+TeXGyreTermesX-Regular"):
        assert not is_math_font(name), name


def test_tex_gyre_math_and_the_usual_maths_faces_stay_maths():
    for name in ("TeXGyreTermesMath-Regular", "TeXGyrePagellaMath", "NewTXMI", "NewTXMI7", "txsys", "txmiaX", "CMMI10", "CMSY10", "CMEX10", "MSBM10", "LatinModernMath-Regular", "XITSMath"):
        assert is_math_font(name), name


def test_plain_text_faces_stay_text():
    for name in ("CMR10", "Times-Roman", "STIXGeneral", "Helvetica", "NimbusRomNo9L-Regu"):
        assert not is_math_font(name), name
