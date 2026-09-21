"""Words run together where a styled piece meets the next word (D040's first lesson of the first kind).

The word check's first sample of the owner's library found words run together on 16 of 149 pages, in two shapes.
A Key Facts Sheet sets its step number at 48 points between "STEP" at 16 and its heading at 12: the spaces beside the
numeral were judged against the numeral's size - under a tenth of 48 - and taken for kerning, so "STEP1Understanding"
came out, on AAMI's, Apia's, Qantas's and TIO's sheets alike. And a Webdings bullet set hard against its item, its box a
point into the next letter, made "4artificial grass or turf". The geometry below is those pages'.
"""
from truedoc.extract.textlayer import _chars_to_words, _fuse_touching_words
from truedoc.model import BBox, Char, Line


def _run(text, x, size, font="ArialMT", step=None, y=100.0):
    """Characters of `text` from `x`, each `step` wide (0.55 of the size by default)."""
    step = step or 0.55 * size
    out = []
    for ch in text:
        out.append(Char(text=ch, bbox=BBox(x, y - 0.8 * size, x + step, y + 0.2 * size), font=font, size=size, origin_y=y))
        x += step
    return out, x


def _words(chars):
    return [w.text for w in _fuse_touching_words(Line(words=_chars_to_words(chars), bbox=BBox(0, 0, 1, 1))).words]


def test_a_step_number_set_large_is_a_word_of_its_own_with_no_space_in_the_text():
    # Qantas's sheet: "STEP" at 16 ends at 84.3, the "1" at 48 starts at 87.6 - 3.3 points, no space character.
    step, x = _run("STEP", 42.5, 16.0, step=10.45)
    one, _ = _run("1", 87.6, 48.0, step=26.7)
    head, _ = _run("Understanding", 117.7, 12.0, step=6.0)
    assert _words(step + one + head) == ["STEP", "1", "Understanding"]


def test_a_step_number_whose_box_touches_its_heading():
    # Apia's and AAMI's: the "1"'s box ends at 144.9 and the "U" starts at 144.8 - a digit is a narrow glyph in a wide
    # box, and the page shows a clear space.
    step, _ = _run("STEP", 72.0, 16.0, step=10.4)
    one, _ = _run("1", 118.2, 48.0, step=26.7)
    head, _ = _run("Understanding", 144.8, 12.0, step=6.7)
    assert _words(step + one + head) == ["STEP", "1", "Understanding"]


def test_a_word_whose_box_touches_the_numeral_after_it():
    # AAMI's sheet of October 2023: "STEP" ends at 93.1 and the 47.7-point "1" starts at 94.1 - one point, though the
    # page shows a clear space. A letter never runs on into a numeral twice its size.
    step, _ = _run("STEP", 51.4, 16.0, step=10.43)
    one, _ = _run("1", 94.1, 47.7, step=26.4)
    head, _ = _run("Understanding", 124.9, 10.0, step=5.5)
    assert _words(step + one + head) == ["STEP", "1", "Understanding"]


def test_the_space_the_text_layer_does_give_beside_a_large_numeral_is_kept():
    # TIO's: a space character between "1" and "Understanding", 2.8 points wide - under 8% of 48, so it was dropped.
    one, x = _run("1", 75.3, 48.0, step=26.7)
    space = [Char(text=" ", bbox=BBox(x, 90, x + 2.8, 102), font="ArialMT", size=48.0, origin_y=100)]
    head, _ = _run("Understanding", x + 2.8, 10.0, step=5.5)
    assert _words(one + space + head) == ["1", "Understanding"]


def test_a_webdings_bullet_hard_against_its_item_is_not_part_of_the_word():
    bullet = [Char(text="4", bbox=BBox(210.9, 90, 220.9, 100), font="Webdings", size=10.0, origin_y=99)]
    item, _ = _run("artificial", 219.8, 9.0, font="MuseoSans-300", step=4.6)
    assert _words(bullet + item) == ["4", "artificial"]


def test_a_mark_already_named_stays_inside_its_word():
    # "INTMRK→BRDORT": a Wingdings arrow already read as "→" is one path of a model, and one word (4a58814).
    left, x = _run("INTMRK", 100.0, 8.0, font="Times New Roman", step=4.4)
    arrow = [Char(text="→", bbox=BBox(x, 93, x + 8.0, 101), font="Wingdings", size=8.0, origin_y=100)]
    right, _ = _run("BRDORT", x + 8.0, 8.0, font="Times New Roman", step=4.4)
    assert _words(left + arrow + right) == ["INTMRK→BRDORT"]


def test_a_drop_cap_letter_still_starts_its_word():
    # A large letter is not a numeral: it begins its word, and touching it stays joined.
    cap, x = _run("T", 50.0, 40.0, step=20.0)
    rest, _ = _run("he", x, 10.0, step=5.5)
    assert _words(cap + rest) == ["The"]


def test_an_ordinal_suffix_stays_on_its_number():
    # A small letter hard against a large numeral may be its suffix ("1st"): left to the gap, and there is none.
    one, x = _run("1", 50.0, 30.0, step=15.0)
    st, _ = _run("st", x, 12.0, step=6.0)
    assert _words(one + st) == ["1st"]
