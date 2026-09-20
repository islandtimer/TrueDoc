"""An underscore TeX drew as a rule is a character of the word it sits in.

`\\_` is not a character in TeX's classic encodings: it is set as `\\kern.06em\\vbox{\\hrule width.3em}` - a rule three
tenths of an em long, 0.4 pt thick, on the baseline. The PDF's text therefore holds "Japanese" and "spaniel" and
nothing between them, and an identifier came out as two words (benchmark tables/8bc04603..._pg1, found 20 September
2026). The geometry below is that page's, in nine-point type.
"""
from truedoc.extract.textlayer import _tex_underscore_between
from truedoc.model import BBox, Char, Word

SIZE = 8.9664
BASE = 677.75


def _word(text, x0, x1):
    width = (x1 - x0) / len(text)
    chars = [Char(text=c, bbox=BBox(x0 + i * width, BASE - 0.7 * SIZE, x0 + (i + 1) * width, BASE + 0.2 * SIZE), font="NimbusRomNo9L-Regu",
                  size=SIZE, origin_y=BASE) for i, c in enumerate(text)]
    return Word(text=text, bbox=BBox(x0, BASE - 0.7 * SIZE, x1, BASE + 0.2 * SIZE), chars=chars)


JAPANESE, SPANIEL = _word("Japanese", 203.91, 235.78), _word("spaniel", 239.01, 264.41)
RULE = BBox(236.32, 677.36, 239.01, 677.76)             # 0.30 em long, 0.06 em after "Japanese", hard against "spaniel"


def test_tex_s_underscore_is_found_between_the_two_words():
    assert _tex_underscore_between(JAPANESE, SPANIEL, [RULE]) is RULE


def test_a_dash_of_a_dotted_underline_is_not_an_underscore():
    # under the baseline, a third of the length, thrice as thick ("she's at the", a transcript's notation)
    dash = BBox(236.5, 678.6, 237.7, 679.9)
    assert _tex_underscore_between(JAPANESE, SPANIEL, [dash]) is None


def test_a_longer_rule_between_two_words_is_not_an_underscore():
    assert _tex_underscore_between(JAPANESE, SPANIEL, [BBox(235.9, 677.36, 239.0, 677.76)]) is None       # no kern before it
    assert _tex_underscore_between(_word("Value", 200.0, 222.0), _word("Units", 230.4, 252.0), [BBox(222.0, 679.4, 230.4, 679.9)]) is None


def test_a_rule_at_mid_height_is_a_minus_sign_or_a_bar_not_an_underscore():
    assert _tex_underscore_between(JAPANESE, SPANIEL, [BBox(236.32, 674.9, 239.01, 675.3)]) is None


def test_it_joins_letters_and_digits_only():
    assert _tex_underscore_between(_word("Merkel,", 203.91, 235.78), SPANIEL, [RULE]) is None
    assert _tex_underscore_between(JAPANESE, _word("(n=3)", 239.01, 264.41), [RULE]) is None
