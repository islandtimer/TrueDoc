"""An arrow set in Wingdings is a character of the text: the code is private-use, and a renderer that strips it
writes "INTMRKBRDORT" where the page says "INTMRK→BRDORT" (benchmark tables/b5c5b866..._pg4, 20 September 2026)."""
from truedoc.extract.textlayer import _symbol_font_mark


def test_the_light_arrows():
    assert "".join(_symbol_font_mark("ABCDEF+Wingdings-Regular", chr(0xF000 + c)) for c in range(0xDF, 0xE7)) == "←→↑↓↖↗↙↘"


def test_the_heavy_and_the_open_arrows():
    assert _symbol_font_mark("Wingdings", chr(0xF0E8)) == "➡"
    assert _symbol_font_mark("Wingdings", chr(0xF0F0)) == "⇨"
    assert _symbol_font_mark("Wingdings", chr(0xF0F8)) == "⬂"


def test_wingdings_two_and_three_draw_other_things_at_these_codes():
    for font in ("Wingdings2", "Wingdings 3", "ABCDEF+Wingdings-3", "Wingdings_2"):
        assert _symbol_font_mark(font, chr(0xF0E0)) == chr(0xF0E0)


def test_the_marks_read_before_are_read_as_before():
    assert _symbol_font_mark("Wingdings", chr(0xF0FC)) == "✓"
    assert _symbol_font_mark("Wingdings", chr(0xF0FB)) == "✗"
    assert _symbol_font_mark("Wingdings", chr(0xF06C)) == "●"


def test_a_code_beside_the_arrows_is_left_alone():
    assert _symbol_font_mark("Wingdings", chr(0xF0DE)) == chr(0xF0DE)
    assert _symbol_font_mark("Wingdings", chr(0xF0F9)) == chr(0xF0F9)
    assert _symbol_font_mark("Times-Roman", chr(0xF0E0)) == chr(0xF0E0)
