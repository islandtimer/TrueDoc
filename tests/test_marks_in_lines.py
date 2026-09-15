"""A mark the page draws, set into a line by the marks reader, is a symbol in the text and never maths.

Budget Direct's home PDS puts a white arrow cut out of a green square before each page link ("page 50"). Once the mark
reader reads the square as an arrow, it sets "→" at the head of the line - and the inline maths pass took the arrow for a
relation sign, writing the link as "\\(\\overline{\\rightarrow}\\) page 50". A table cell never meets that pass, so the
same arrow read right there.
"""
from truedoc.math.extract import inline_math_text
from truedoc.model import BBox, Char, Line, Word


def _word(text, x0, font="Helvetica"):
    chars = [Char(text=ch, bbox=BBox(x0 + 5 * i, 50, x0 + 5 * (i + 1), 60), font=font, size=10.0, origin_y=58.0)
             for i, ch in enumerate(text)]
    return Word(text=text, bbox=BBox(x0, 50, x0 + 5 * len(text), 60), chars=chars)


def _arrow(font):
    # As pipeline._attach_marks sets a mark at the head of a line: one character, the mark's own box, font "mark".
    box = BBox(50, 50, 60, 60)
    return Word(text="→", bbox=box, chars=[Char(text="→", bbox=box, font=font, size=10.0, origin_y=60.0)])


def _line(first):
    return Line(words=[first, _word("page", 64), _word("50", 88)], bbox=BBox(50, 50, 98, 60))


def test_a_drawn_arrow_leading_a_line_is_text_not_maths():
    shaft = BBox(52, 54.5, 58, 55.5)   # the stroke cut through the square, a short horizontal rule inside the mark
    assert inline_math_text(_line(_arrow("mark")), []) == "→ page 50"
    assert inline_math_text(_line(_arrow("mark")), [shaft]) == "→ page 50"


def test_the_same_arrow_set_in_a_maths_font_is_still_maths():
    assert inline_math_text(_line(_arrow("CMSY10")), []).startswith(r"\(")
