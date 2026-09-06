"""Mac CE fonts read as Mac Roman: the Polish letters come back."""

from truedoc.extract.textlayer import _central_european


def test_polish_letters_restored_for_pl_fonts():
    font = "INDOHA+Latin725PL-Roman"
    assert "".join(_central_european(font, ch) for ch in "powo∏uje") == "powołuje"
    assert "".join(_central_european(font, ch) for ch in "nale˝y") == "należy"
    assert "".join(_central_european(font, ch) for ch in "ksi´g´ sk∏adaç koƒ prawid∏owoÊci najpóêniej") == "księgę składać koń prawidłowości najpóźniej"
    assert "".join(_central_european("AntiqueOliSCTCE-Medi", ch) for ch in "πódê") == "Łódź"


def test_advent_symbol_fonts():
    from truedoc.extract.textlayer import _symbol_font_mark

    f = "ABCDEF+AdvP4C4E74"
    assert "".join(_symbol_font_mark(f, ch) for ch in "\x01.34") == "−.34"
    assert "".join(_symbol_font_mark(f, ch) for ch in "(n ¼ 562)") == "(n = 562)"
    assert "".join(_symbol_font_mark(f, ch) for ch in "m tð Þ ¼ m0 þ mf") == "m t( ) = m0 + mf"
    g = "AdvP40271B"
    assert "".join(_symbol_font_mark(g, ch) for ch in "2 f0; 1g") == "∈ {0; 1}"
    assert _symbol_font_mark("Times-Roman", "\x01") == "\x01"
    assert _symbol_font_mark("Times-Roman", "¼") == "¼"
    assert _symbol_font_mark("AdvP641C", "f") == "f"   # a text face of the same family keeps its letters


def test_other_fonts_untouched():
    assert _central_european("Times-Roman", "∏") == "∏"
    assert _central_european("ABCDEF+Helvetica", "à") == "à"
    assert _central_european("INDOHA+Latin725PL-Roman", "ó") == "ó"
