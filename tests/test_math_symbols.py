"""Symbol-level behaviour of the formula rebuild: font-specific spellings and glyph codes."""

from truedoc.math.reconstruct import glyph, reconstruct
from truedoc.math.symbols import cmex_code, latex_for_char
from truedoc.model import BBox


def g(ch, x, oy, size=10.0, font="CMR10", width=5.0):
    return glyph(ch, font, size, BBox(x, oy - 0.7 * size, x + width, oy + 0.2 * size), oy)


def test_tex_phi_glyph_is_phi_not_varphi():
    # TeX's \phi glyph is *named* "phi" and so is reported as U+03C6; KaTeX draws
    # that code for \varphi, so for TeX-encoded fonts the two are swapped.
    assert latex_for_char("φ", "CMMI10") == r"\phi"
    assert latex_for_char("ϕ", "CMMI10") == r"\varphi"
    assert latex_for_char("φ", "STIXMathItalic") == r"\varphi"


def test_phi_is_told_from_varphi_by_its_width():
    # cmmi's straight phi is 0.596 em wide, the curly varphi 0.654 em; the Unicode
    # attached to the two glyphs varies by TeX distribution, the width does not.
    assert g("φ", 0, 100, font="CMMI10", width=5.96).latex == r"\phi"
    assert g("ϕ", 0, 100, font="CMMI10", width=5.96).latex == r"\phi"
    assert g("φ", 0, 100, font="CMMI10", width=6.54).latex == r"\varphi"
    assert g("ϕ", 0, 100, font="LMMathItalic12-Regular", size=12.0, width=7.7).latex == r"\varphi"
    assert g("ϕ", 0, 100, font="LMMathItalic12-Regular", size=12.0, width=6.96).latex == r"\phi"
    # Not a TeX font: the character decides, as before.
    assert g("φ", 0, 100, font="STIXMathItalic", width=6.0).latex == r"\varphi"


def test_epsilon_is_told_from_varepsilon_by_its_width():
    # cmmi's lunate epsilon is 0.406 em wide, the curly varepsilon 0.472 em, whatever
    # Unicode the PDF attaches (U+03B5, U+03F5 or even U+01EB).
    for ch in ("ε", "ϵ", "ǫ"):
        assert g(ch, 0, 100, font="CMMI10", width=4.06).latex == r"\epsilon", ch
        assert g(ch, 0, 100, font="CMMI10", width=4.72).latex == r"\varepsilon", ch
    assert g("ε", 0, 100, font="CMMI8", size=8.0, width=3.44).latex == r"\epsilon"
    assert g("ε", 0, 100, font="CMMI8", size=8.0, width=3.92).latex == r"\varepsilon"
    assert g("ϵ", 0, 100, font="LMMathItalic12-Regular", size=12.0, width=4.7).latex == r"\epsilon"
    # Pazo's epsilon is wide by design: the character decides there.
    assert g("ϵ", 0, 100, font="PazoMath-Italic", width=4.7).latex == r"\epsilon"


def test_truncated_surrogate_codes_give_the_maths_letter_back():
    # newtx and STIX PDFs write U+1D6FC (italic alpha) as U+D6FC, a Hangul syllable.
    assert latex_for_char("훼", "NewTXMI") == r"\alpha"
    assert latex_for_char("푋", "NewTXMI7") == "X"
    assert latex_for_char("푡", "STIXMath-Italic") == "t"
    # A real Korean syllable in a Korean font is left alone.
    assert latex_for_char("한", "NanumGothic") == "한"


def test_mathematical_alphanumerics_become_plain_letters_with_a_style():
    assert latex_for_char("𝑛", "CambriaMath") == "n"
    assert latex_for_char("𝛾", "CambriaMath") == r"\gamma"
    assert latex_for_char("𝐀", "CambriaMath") == r"\mathbf{A}"
    assert latex_for_char("𝜷", "CambriaMath") == r"\boldsymbol{\beta}"
    assert latex_for_char("𝒜", "CambriaMath") == r"\mathcal{A}"
    assert latex_for_char("ℝ", "CambriaMath") in (r"\mathbb{R}",)  # a letterlike symbol, already mapped
    assert latex_for_char("𝔸", "CambriaMath") == r"\mathbb{A}"
    assert latex_for_char("𝔞", "CambriaMath") == r"\mathfrak{a}"
    assert latex_for_char("𝟏", "CambriaMath") == r"\mathbf{1}"


def test_mapsto_is_one_arrow():
    # cmsy draws \mapsto as a short bar glued to an arrow; the bar comes back as "|" or its raw code.
    bar = g("|", 0, 100, font="LMMathSymbols10-Regular", width=2.0)
    arrow = g("→", 2.2, 100, font="LMMathSymbols10-Regular", width=9.0)
    latex, _ = reconstruct([g("x", -8, 100), bar, arrow, g("y", 13, 100)], [])
    assert r"\mapsto" in latex and r"\rightarrow" not in latex and "|" not in latex, latex
    raw = g("7", 0, 100, font="CMSY10", width=2.0)
    latex2, _ = reconstruct([raw, g("→", 2.2, 100, font="CMSY10", width=9.0)], [])
    assert latex2.strip() == r"\mapsto", latex2
    # A bar well apart from an arrow stays a bar.
    latex3, _ = reconstruct([g("|", 0, 100, font="CMSY10", width=2.0), g("→", 8.0, 100, font="CMSY10", width=9.0)], [])
    assert "|" in latex3 and r"\rightarrow" in latex3, latex3


def test_bar_size_counts_the_extender_pieces():
    from truedoc.math.reconstruct import _merge_extensible_pieces

    def piece(y):
        return glyph("\x0c", "CMEX10", 10.0, BBox(50, y, 52, y + 6.0), y)

    for n, want in ((2, r"\big|"), (3, r"\Big|"), (4, r"\bigg|"), (5, r"\Bigg|")):
        merged = _merge_extensible_pieces([piece(100 + 6.0 * i) for i in range(n)])
        assert len(merged) == 1 and merged[0].latex == want, (n, [m.latex for m in merged])


def test_cmsy_backslash_is_setminus():
    # cmsy's glyph at 0x6e is named "backslash": MuPDF reports it as that character.
    assert latex_for_char(chr(92), "CMSY10") == r"\setminus"


def test_cmex_whitespace_codes_survive_on_private_use_characters():
    assert cmex_code(chr(0xE000 + 0x20)) == 0x20
    # Fixed-size delimiters carry their size: code 0x20 is the size-4 parenthesis.
    assert latex_for_char(chr(0xE000 + 0x20), "CMEX10") == r"\Bigg("
    assert latex_for_char(chr(0xE000 + 0x09), "CMEX10") == r"\big\}"
    assert latex_for_char(chr(0xE000 + 0x10), "CMEX10") == r"\Big("
    assert latex_for_char(chr(0xE000 + 0x68), "CMEX10") == r"\Big["
    # a whitespace-coded bracket (recoded by the text layer) is not thrown away as a blank
    lp = glyph(chr(0xE000 + 0x20), "CMEX10", 10.0, BBox(0, 88, 8, 98), 88.5)
    latex, _ = reconstruct([lp, g("x", 10, 100, font="CMMI10")], [])
    assert latex == r"\Bigg(x"
    # a plain space credited to the extension font is the blank MuPDF inserts between words
    blank = glyph(" ", "CMEX10", 10.0, BBox(0, 88, 2.3, 98), 88.5)
    latex2, _ = reconstruct([g("t", -5, 100, font="CMMI10"), blank, g("W", 4, 100, font="CMMI10")], [])
    assert "Bigg" not in latex2 and "(" not in latex2, latex2


def test_cmex_bar_is_a_sized_bar():
    bar = glyph("\x0c", "CMEX10", 10.0, BBox(10, 90, 12, 100), 90.5)
    latex, _ = reconstruct([g("u", 0, 100, font="CMMI10"), bar, g("x", 14, 104, size=7.0, font="CMMI10")], [])
    assert latex == r"u\big|_{x}"


def test_cmex_box_comes_from_design_metrics_when_unmeasured():
    lp = glyph("\x12", "CMEX10", 10.0, BBox(0, 88, 4, 98), 88.5)  # size-3 "(": 2.4 em tall
    assert lp.bbox.height > 20


def test_zero_width_vector_accent_attaches_to_next_glyph_across_a_space():
    arrow = glyph("⃗", "CMMI10", 10.0, BBox(20, 93, 20, 102), 100.0)   # zero advance, reported at the previous glyph's end
    gs = [g(",", 17, 100), arrow, g("a", 38, 100, font="CMMI10"), g("2", 43.5, 101.5, size=7.0)]
    latex, _ = reconstruct(gs, [])
    assert latex == r",\vec{a}_{2}"


def test_not_in_spelling():
    slash = "̸"
    gs = [g("x", 0, 100, font="CMMI10"), g(slash, 8, 100, font="CMSY10", width=0.5), g("∈", 8, 100, font="CMSY10"), g("S", 16, 100, font="CMMI10")]
    latex, _ = reconstruct(gs, [])
    # The checker tells \notin from \not\in; the references write \not\in 11 to 5.
    assert latex == r"x\not\in S"


def test_symbol_font_letters_are_calligraphic_and_blackboard():
    from truedoc.math.symbols import latex_for_char

    assert latex_for_char("M", "CMSY10") == r"\mathcal{M}"
    assert latex_for_char("R", "MSBM10") == r"\mathbb{R}"
    # Ordinary letters in ordinary maths fonts stay themselves.
    assert latex_for_char("M", "CMMI10") == "M"
    assert latex_for_char("R", "CMR10") == "R"
