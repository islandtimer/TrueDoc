"""A column cut goes in the channel no word crosses, even when headings stand over the range's ends and middle.

`_refine_segments` votes an x range that most rows leave empty and then places a cut in it: just before the words
that close it, else its middle, else its left end. A table whose second column is empty on a dozen rows votes a range
from the shortest label to the first value; "Triacylglycerols (%)" stood over its left end and its middle and "Palm
oil*" over its right end, all three places were refused, and the two headings came out as one over two columns -
though 9.2 points of clear page ran between them, against a word space of 2.0 (benchmark tables/c8cdd4c4..._pg3,
20 September 2026). The geometry below is that page's.
"""
from truedoc.model import BBox, Line, Word
from truedoc.tables.aligned import _cluster_rows, _refine_segments

# Short labels, so that the voted range opens at about 70 and its middle (about 111) lies squarely on
# "Triacylglycerols" - on the page it lay on that word's last 0.02 of a point.
LABELS = [("CCL", 70.9), ("CLL", 70.1), ("LLL", 69.4), ("LLM", 70.0), ("LLO", 69.8), ("LMM", 70.7),
          ("MMM", 71.0), ("MPL", 70.0), ("OOL", 70.5), ("MMP", 70.5), ("POL", 69.8), ("PPL", 69.0)]


def _segment(y, *words, height=8):
    ws = [Word(text=t, bbox=BBox(x0, y, x1, y + height)) for t, x0, x1 in words]
    return Line(words=ws, bbox=BBox.union_all(w.bbox for w in ws))


def _rows(heading_gap=9.2):
    palm = 133.0 + heading_gap
    lines = [_segment(100, ("Triacylglycerols", 60.8, 118.5), ("(%)", 120.5, 133.0), ("Palm", palm, palm + 18.6), ("oil*", palm + 20.6, palm + 34.0),
                      ("Palm", 186.5, 205.2), ("olein*", 207.2, 229.4))]
    for i, (label, x1) in enumerate(LABELS):
        y = 115 + 14 * i
        if i < 6:       # the rows whose only value stands in the last column
            lines += [_segment(y, (label, 60.7, x1)), _segment(y, ("6.8", 489.5, 499.5))]
        else:
            lines += [_segment(y, (label, 60.7, x1)), _segment(y, ("0.4", 152.1, 164.1)), _segment(y, ("0.6", 202.9, 212.9))]
    return _cluster_rows(lines, 8.0)


def _heading_cells(rows):
    return [seg.text for seg in rows[0].segments]


def test_the_cut_is_placed_between_the_two_headings():
    rows, cuts = _refine_segments(_rows(), 8.0)
    assert any(133.0 < c < 142.2 for c in cuts)
    assert _heading_cells(rows)[:2] == ["Triacylglycerols (%)", "Palm oil*"]


def test_a_line_is_not_divided_on_its_own_word_space():
    # The first version of the rule cut a table's sub-title, "Contributions from partners (thousands | of US$)": in
    # 5.6-point type its plain word spaces, 2.8 points, are half the size - wide enough to vote, and to pass for a
    # channel (benchmark tables/9a61fe78..._pg2). Here the title's words stand 4.0 apart, every one of them, in 8-point
    # type; they stand over the range's ends and middle as the headings did, and the title stays whole.
    lines = [_segment(100, ("Contributions", 60.0, 114.0), ("from", 118.0, 136.0), ("partners", 140.0, 170.0))]
    for i, (label, x1) in enumerate(LABELS):
        y = 115 + 14 * i
        if i < 6:
            lines += [_segment(y, (label, 60.7, x1)), _segment(y, ("6.8", 489.5, 499.5))]
        else:
            lines += [_segment(y, (label, 60.7, x1)), _segment(y, ("0.4", 152.1, 164.1)), _segment(y, ("0.6", 202.9, 212.9))]
    rows, cuts = _refine_segments(_cluster_rows(lines, 8.0), 8.0)
    assert not any(114.0 <= c <= 140.0 for c in cuts)
    assert _heading_cells(rows)[0] == "Contributions from partners"


def test_a_word_space_is_not_a_channel():
    # the same headings a word space apart are one heading: nothing in the range is wide enough to count as a vote
    rows, cuts = _refine_segments(_rows(heading_gap=2.0), 8.0)
    assert not any(118.5 < c < 142.2 for c in cuts)
    assert _heading_cells(rows)[0].startswith("Triacylglycerols (%) Palm")
