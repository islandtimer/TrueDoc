"""A word space in tiny type is judged against the line's own letter gaps."""

from truedoc.model import BBox, Char
from truedoc.extract.textlayer import _chars_to_words


def _chars(text, size, letter_gap, word_gap, x0=100.0, y0=600.0):
    """Lay out `text` without space characters: letters `letter_gap` apart,
    and each space in `text` becomes a bare gap of `word_gap`."""
    chars = []
    x = x0
    for i, ch in enumerate(text):
        if ch == " ":
            x += word_gap - letter_gap
            continue
        w = 0.5 * size
        if i:
            x += letter_gap
        chars.append(Char(text=ch, bbox=BBox(x, y0, x + w, y0 + size), font="StRyde-Bold", size=size, origin_y=y0 + 0.8 * size))
        x += w
    return chars


def test_tiny_bold_caption_breaks_at_its_small_gap():
    # 6.37 pt: letter boxes overlap by 0.06 pt, the word gap is 0.78 pt (0.12 em),
    # under the 0.9 pt absolute floor.
    words = _chars_to_words(_chars("James Norwood still favours", 6.37, -0.06, 0.78))
    assert [w.text for w in words] == ["James", "Norwood", "still", "favours"]


def test_uniform_tracking_is_not_a_word_gap():
    # Every letter 0.7 pt apart at 7 pt (loose tracking): no gap stands out.
    words = _chars_to_words(_chars("Annual", 7.0, 0.7, 0.7))
    assert [w.text for w in words] == ["Annual"]


def test_ordinary_text_is_unchanged():
    words = _chars_to_words(_chars("the quick brown fox", 10.0, 0.0, 2.5))
    assert [w.text for w in words] == ["the", "quick", "brown", "fox"]
