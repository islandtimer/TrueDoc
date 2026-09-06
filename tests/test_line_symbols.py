"""Line reassembly around maths: bracket-only fragments and interleaved segments."""

from truedoc.extract.textlayer import _reassemble_lines
from truedoc.model import BBox, Char, Line, Word


def word(text, x, oy, size=10.0, font="CMR10", width=None):
    width = width if width is not None else 5.0 * len(text)
    chars = []
    cx = x
    for ch in text:
        w = width / len(text)
        chars.append(Char(text=ch, bbox=BBox(cx, oy - 0.7 * size, cx + w, oy + 0.2 * size), font=font, size=size, origin_y=oy))
        cx += w
    return Word(text=text, bbox=BBox.union_all(c.bbox for c in chars), chars=chars)


def line(*words):
    return Line(words=list(words), bbox=BBox.union_all(w.bbox for w in words))


def test_stacked_bar_pieces_fold_into_the_text_line():
    # "u |_Γ = 0": the tall bar is two cmex pieces whose origins sit on other baselines.
    text = line(word("is", 10, 100), word("u", 30, 100, font="CMMI10"))
    tail = line(word("=", 44, 100), word("0", 52, 100))
    top = line(word("", 36, 94, font="CMEX10", width=2.0))
    bottom = line(word("", 36, 101, font="CMEX10", width=2.0))
    out = _reassemble_lines([top, text, bottom, tail])
    assert len(out) == 1
    assert "".join(w.text for w in out[0].words) == "isu=0"


def test_interleaved_segments_are_one_line():
    # "(λ_1^{-1}, λ_2^{-1})": MuPDF emits overlapping segments when scripts interleave.
    a = line(word("(λ", 100, 100, font="CMMI10", width=10))
    b = line(word("1", 108, 101.5, size=7.0, width=3), word(",", 118, 100, width=3), word("λ", 124, 100, font="CMMI10", width=5))
    c = line(word("−1", 110, 96.5, size=7.0, font="CMSY7", width=6), word("−1", 129, 96.5, size=7.0, font="CMSY7", width=6))
    d = line(word("2", 129, 101.5, size=7.0, width=3), word(")", 136, 100, width=3))
    out = _reassemble_lines([a, b, c, d])
    main_lines = [l for l in out if l.size >= 8.5]
    assert len(main_lines) == 1
    assert main_lines[0].bbox.x0 == 100 and main_lines[0].bbox.x1 >= 139


def test_duplicated_layer_is_not_merged():
    # The same words drawn twice at the same place (a fake-bold layer) must not double the text.
    a = line(word("Hello", 10, 100), word("world", 40, 100))
    b = line(word("Hello", 10, 100), word("world", 40, 100))
    out = _reassemble_lines([a, b])
    assert len(out) == 2
