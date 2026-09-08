"""Two segments that together fill a column's measure are one line.

A justified column stretches a line's word gaps; when one gap passes an em, the extractor
gives the line as two segments and the re-joiner (which allows up to an em) leaves them
apart. On 09f90a8fad the segment "Resisting the tempta-" then became a block of its own,
read after the other column, and five order checks failed (run 60). Segments on one
baseline in the same column whose union runs from the column's left edge to its right edge
are one line for gaps up to an em and a half; a wider gap (a table row) stays two.
"""
from tests.test_columns import line, two_column_page, word
from truedoc.extract.textlayer import _column_gutters, _reassemble_lines


def _row(oy, gap):
    left = [word(t, x, oy) for t, x in (("with", 262), ("the", 287), ("name,", 307), ("El", 337), ("Nino?", 352))]
    x = 352 + 5 * 5 + gap                      # the left segment ends at 377
    right = []
    for t in ("Resisting", "the", "tempta-"):  # 19 letters at 3.5 pt: the segment ends near the column's edge, 460
        right.append(word(t, x, oy, char_w=3.5))
        x += 3.5 * len(t) + 3.5
    return line(*left), line(*right)


def test_segments_filling_the_measure_join_across_a_stretched_gap():
    lines = two_column_page(rows=20)
    a, b = _row(100 + 12 * 20, gap=12.0)          # 1.2 em, past the ordinary limit
    lines += [a, b]
    gutters = _column_gutters(lines)
    out = _reassemble_lines(lines, gutters)
    texts = [l.text for l in out]
    assert "with the name, El Nino? Resisting the tempta-" in texts, [t for t in texts if "Nino" in t or "Resisting" in t]


def test_columns_sharing_a_measure_stay_apart_across_an_unfound_gutter():
    # Three columns; only the first gutter is known to the re-joiner, so the second and
    # third columns share a column index and their lines share baselines: their union spans
    # the measure, but a channel of white runs between them (no word on any nearby line
    # crosses it), so they are not one line (20_pg46 and 03ccfe8bb1 in run 62).
    texts = ["lorem ipsum dolor sit amet", "consectetur adipiscing elit sed", "do eiusmod tempor incididunt", "ut labore et dolore magna", "aliqua enim ad minim veniam"]
    lines = []
    for i in range(20):
        oy = 100 + 12 * i
        for k, (x0, x1) in enumerate(((50, 150), (170, 300), (314, 460))):   # a 14 pt gutter: past a word space, within the measure rule's reach
            ws = texts[(i + k) % 5].split()
            space = (x1 - x0 - sum(len(w) for w in ws) * 4.0) / (len(ws) - 1)
            x = x0
            words = []
            for w in ws:
                words.append(word(w, x, oy, char_w=4.0))
                x += len(w) * 4.0 + space
            lines.append(line(*words))
    out = _reassemble_lines(lines, [(150.0, 170.0)])
    assert len(out) == 60, "no two columns' lines were joined"
    assert all(l.bbox.x1 <= 301 or l.bbox.x0 >= 313 for l in out)


def test_a_wide_gap_or_a_short_line_stays_two_segments():
    lines = two_column_page(rows=20)
    a, b = _row(100 + 12 * 20, gap=26.0)          # 2.6 em: a table row
    lines += [a, b]
    gutters = _column_gutters(lines)
    out = _reassemble_lines(lines, gutters)
    assert any(l.text == "Resisting the tempta-" for l in out)
    lines = two_column_page(rows=20)
    a, b = _row(100 + 12 * 20, gap=12.0)
    b = line(*b.words[:2])                         # "Resisting the": the line stops short of the edge
    lines += [a, b]
    out = _reassemble_lines(lines, _column_gutters(lines))
    assert any(l.text == "Resisting the" for l in out)
