"""A heading wrapped over two lines is one heading.

Headings are set with wider leading than body text, so the segmenter gives each line of a
wrapped heading a block of its own and the classifier makes two headings of them: "4
Determination of the electrical" over "parameters", "Foreign Tax Credit (Individual, Estate,
Trust, or" over "Nonresident Alien Individual)". Run 60's output held 98 headings starting with
a lowercase letter on 56 pages, most of them the second line of a wrapped heading.
"""
from truedoc.model import BBox, Block, BlockKind, Char, Line, Word
from truedoc.pipeline import _merge_wrapped_headings

BODY = 10.0


def _line(text, x0, y0, size=12.0, font="Arial-BoldMT"):
    cw = 0.5 * size
    chars = [Char(text=c, bbox=BBox(x0 + i * cw, y0, x0 + (i + 1) * cw, y0 + size), font=font, size=size, origin_y=y0 + 0.8 * size) for i, c in enumerate(text)]
    words = []
    x = x0
    for tok in text.split(" "):
        w = cw * len(tok)
        words.append(Word(text=tok, bbox=BBox(x, y0, x + w, y0 + size), chars=[c for c in chars if x <= c.bbox.x0 < x + w + 0.01]))
        x += w + cw
    return Line(words=words, bbox=BBox(x0, y0, x0 + cw * len(text), y0 + size))


def _heading(text, x0, y0, size=12.0, font="Arial-BoldMT"):
    line = _line(text, x0, y0, size, font)
    return Block(kind=BlockKind.HEADING, bbox=line.bbox, lines=[line])


def _texts(blocks):
    return [(b.kind, " ".join(b.text.split())) for b in blocks]


def test_lowercase_second_line_joins_the_heading_above():
    a = _heading("4 Determination of the electrical", 57, 100)
    b = _heading("parameters", 57, 116)
    body = Block(kind=BlockKind.TEXT, bbox=BBox(57, 140, 290, 200), lines=[_line("The table cannot move.", 57, 140, 10.0, "TimesNewRomanPSMT")])
    out = _merge_wrapped_headings([a, b, body], BODY)
    assert _texts(out) == [(BlockKind.HEADING, "4 Determination of the electrical parameters"), (BlockKind.TEXT, "The table cannot move.")]
    assert out[0].bbox.y1 == b.bbox.y1 and len(out[0].lines) == 2


def test_open_bracket_and_connective_join_the_lines():
    a = _heading("Foreign Tax Credit (Individual, Estate, Trust, or", 42, 100)
    b = _heading("Nonresident Alien Individual)", 42, 116)
    out = _merge_wrapped_headings([a, b], BODY)
    assert _texts(out) == [(BlockKind.HEADING, "Foreign Tax Credit (Individual, Estate, Trust, or Nonresident Alien Individual)")]


def test_aligned_title_case_lines_of_one_style_join():
    a = _heading("Panteion University of Social & Political", 112, 100, 9.1, "Cambria-Bold")
    b = _heading("Sciences Department of Social Anthropology", 112, 112, 9.1, "Cambria-Bold")
    out = _merge_wrapped_headings([a, b], BODY)
    assert len(out) == 1 and " ".join(out[0].text.split()) == "Panteion University of Social & Political Sciences Department of Social Anthropology"


def test_headings_of_different_sizes_or_ended_by_a_stop_stay_apart():
    title = _heading("A Study of Tables", 100, 100, 18.0)
    sub = _heading("Methods and Materials", 100, 124, 12.0)
    assert len(_merge_wrapped_headings([title, sub], BODY)) == 2
    a = _heading("1. Introduction.", 57, 100)
    b = _heading("Background", 57, 116)
    assert len(_merge_wrapped_headings([a, b], BODY)) == 2
    a = _heading("Results", 57, 100)
    c = _heading("2 Discussion", 57, 116)
    assert len(_merge_wrapped_headings([a, c], BODY)) == 2, "a numbered heading starts a heading of its own"


def test_two_run_in_headings_with_a_text_line_between_stay_apart():
    # "Tucson International Airport (TUS); however, lower fares" and, a line later,
    # "International Airport (PHX). Tucson is approximately a 40" are run-in headings of
    # one paragraph whose middle line is plain text (03ccfe8bb1, run 62).
    a = _heading("Tucson International Airport (TUS); however, lower fares", 36, 331, 9.5)
    between = Block(kind=BlockKind.TEXT, bbox=BBox(36, 342, 288, 355), lines=[_line("can sometimes be found by flying into Phoenix Sky Harbor", 36, 342, 9.5, "TimesNewRomanPSMT")])
    b = _heading("International Airport (PHX). Tucson is approximately a 40", 36, 353, 9.5)
    out = _merge_wrapped_headings([a, between, b], 9.5)
    assert len(out) == 3


def test_a_heading_far_below_or_beside_is_not_a_continuation():
    a = _heading("Regional offices", 57, 100)
    far = _heading("and their staff", 57, 160)     # four lines further down
    beside = _heading("and their staff", 300, 100)  # the next column
    assert len(_merge_wrapped_headings([a, far], BODY)) == 2
    assert len(_merge_wrapped_headings([a, beside], BODY)) == 2
