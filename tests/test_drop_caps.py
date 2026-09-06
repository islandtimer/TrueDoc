"""A drop cap rejoins the first word of its paragraph."""
from truedoc.extract.textlayer import _join_drop_caps
from truedoc.model import BBox, Char, Line, Word


def _word(text: str, x0: float, y0: float, size: float, font: str = "Calibri-Light") -> Word:
    chars = []
    x = x0
    for ch in text:
        chars.append(Char(text=ch, bbox=BBox(x, y0, x + 0.5 * size, y0 + size), font=font, size=size, origin_y=y0 + 0.8 * size))
        x += 0.5 * size
    return Word(text=text, bbox=BBox(x0, y0, x, y0 + size), chars=chars)


def _line(words: list[Word]) -> Line:
    return Line(words=words, bbox=BBox(min(w.bbox.x0 for w in words), min(w.bbox.y0 for w in words), max(w.bbox.x1 for w in words), max(w.bbox.y1 for w in words)))


def _paragraph() -> list[Line]:
    cap = _line([_word("L", 24, 241, 41, "DINCondensed-Bold")])
    first = _line([_word("e", 45, 247, 10), _word("gouvernement", 52, 247, 10), _word("cultive", 118, 247, 10)])
    second = _line([_word("quillement", 45, 258, 10), _word("le", 100, 258, 10), _word("chaos.", 112, 258, 10)])
    other = _line([_word("les", 266, 247, 10), _word("transports", 285, 247, 10)])
    return [cap, first, second, other]


def test_drop_cap_joins_first_word():
    lines = _join_drop_caps(_paragraph())
    texts = [l.text for l in lines]
    assert "Le gouvernement cultive" in texts
    assert "L" not in texts
    assert "quillement le chaos." in texts
    joined = next(l for l in lines if l.text.startswith("Le "))
    assert joined.bbox.x0 == 24  # the paragraph now starts at the cap's left edge
    assert joined.size == 10  # a single tall letter does not change the line's size


def test_initial_letter_of_ordinary_size_stays():
    cap = _line([_word("L", 40, 247, 10)])
    first = _line([_word("e", 46, 247, 10), _word("gouvernement", 52, 247, 10)])
    lines = _join_drop_caps([cap, first])
    assert [l.text for l in lines] == ["L", "e gouvernement"]


def test_far_letter_is_not_a_drop_cap():
    cap = _line([_word("L", 24, 241, 41, "DINCondensed-Bold")])
    first = _line([_word("e", 120, 247, 10), _word("gouvernement", 126, 247, 10)])
    lines = _join_drop_caps([cap, first])
    assert [l.text for l in lines] == ["L", "e gouvernement"]
