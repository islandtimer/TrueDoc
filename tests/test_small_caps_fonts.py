"""A small-caps font prints lowercase letters as small capitals; the page reads as capitals."""

from truedoc.extract.textlayer import _small_caps


def test_small_caps_font_reads_as_capitals():
    assert _small_caps("TimesTen-RomanSC", "Rottier S., Piette J.") == "ROTTIER S., PIETTE J."
    assert _small_caps("ABCDEF+TimesTen-RomanSC", "Roudil") == "ROUDIL"
    assert _small_caps("MinionPro-SemiboldItSC", "thevenot") == "THEVENOT"
    assert _small_caps("Garamond-SmallCaps", "époque") == "ÉPOQUE"


def test_other_fonts_and_non_letters_are_untouched():
    assert _small_caps("TimesNewRomanPSMT", "Rottier") == "Rottier"
    assert _small_caps("Escrow", "abc") == "abc"          # "sc" inside a name is not a small-caps mark
    assert _small_caps("TimesTen-RomanSC", "(2012)") == "(2012)"
    assert _small_caps("TimesTen-RomanSC", "") == ""
