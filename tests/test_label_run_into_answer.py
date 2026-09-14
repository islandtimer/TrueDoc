"""A label run together with its answer across a real gap is divided where the other rows start their answers.

CGU's contents sheets set "Actions of the sea" and its "No" 11.5pt apart, and WFI's "Items away from" and its "Yes" 9.8pt
apart; in both the answer starts exactly where every other row's answer starts, and the text layer runs the pair into
one line. Every other row reaches the table with its label and answer already apart, so no cut is voted between those
columns, and the one line stayed whole in the label's column with its answer cell empty. A word space is not divided,
and nor is a gap whose far side starts where no other row starts.
"""
from truedoc.model import BBox, Line, Word
from truedoc.tables.aligned import table_from_lines


def _segment(y, *words):
    ws = [Word(text=t, bbox=BBox(x0, y, x1, y + 10)) for t, x0, x1 in words]
    return Line(words=ws, bbox=BBox.union_all(w.bbox for w in ws))


def _rows(table):
    assert table is not None
    return [[(c.text if c else "") for c in row] for row in table.grid()]


def _event(y, label, answer, exclusion, wraps=()):
    """A label, its answer and its exclusions apart, then the exclusions' wrapped lines and any second line of the label."""
    lines = [_segment(y, *label), _segment(y, exclusion[0], *exclusion[1:])]
    if answer:
        lines.append(_segment(y, answer))
    for k, (label_tail, words) in enumerate(wraps, start=1):
        if label_tail:
            lines.append(_segment(y + 11 * k, label_tail))
        lines.append(_segment(y + 11 * k, *words))
    return lines


def _sheet(middle):
    """Seven events set apart as a Key Facts Sheet sets them, around the row under test at y 400."""
    return (_event(100, [("Flood", 50, 76)], ("Yes", 141, 157), [("Excludes", 194, 234), ("walls.", 237, 264)],
                   [(None, [("and", 194, 211), ("paths.", 214, 241)])])
            + _event(140, [("Storm", 50, 78)], ("Yes", 141, 157), [("Excludes", 194, 234), ("rain", 237, 256)],
                     [(None, [("entering", 194, 233), ("the", 236, 251), ("home", 254, 280)]),
                      (None, [("and", 194, 211), ("hail.", 214, 236)])])
            + _event(180, [("Theft", 50, 74), ("and", 77, 94)], ("Yes", 141, 157), [("Excludes", 194, 234), ("theft", 237, 259)],
                     [(("Burglary", 50, 90), [("by", 194, 204), ("tenants", 207, 242), ("or", 245, 255)]),
                      (None, [("their", 194, 216), ("guests.", 219, 252)])])
            + _event(230, [("Malicious", 50, 94)], ("Yes", 141, 157), [("Excludes", 194, 234), ("damage", 237, 273)],
                     [(("Damage", 50, 88), [("by", 194, 204), ("a", 207, 212), ("tenant.", 215, 249)])])
            + _event(270, [("Escape", 50, 82), ("of", 85, 94)], ("Yes", 141, 157), [("Excludes", 194, 234), ("the", 237, 252)],
                     [(("liquid", 50, 76), [("item", 194, 214), ("which", 217, 243), ("leaked.", 246, 280)]),
                      (None, [("and", 194, 211), ("mould.", 214, 246)])])
            + _event(320, [("Lightning", 50, 94)], ("Yes", 141, 157), [("Includes", 194, 232), ("power", 235, 262)],
                     [(None, [("surges", 194, 225), ("from", 228, 248), ("strikes", 251, 283)]),
                      (None, [("near", 194, 215), ("the", 218, 233), ("home.", 236, 264)])])
            + _event(360, [("Impacts", 50, 86)], ("Yes", 141, 157), [("Includes", 194, 232), ("falling", 235, 264)],
                     [(None, [("trees", 194, 217), ("and", 220, 237), ("aircraft", 240, 276)]),
                      (None, [("from", 194, 214), ("above.", 217, 247)])])
            + list(middle))


def test_an_answer_run_on_from_its_label_across_a_real_gap_is_its_own_cell():
    # CGU: "No" 11pt after "sea", starting where every other row's answer starts.
    middle = [_segment(400, ("Actions", 50, 85), ("of", 88, 97), ("the", 100, 114), ("sea", 117, 130), ("No", 141, 154)),
              _segment(400, ("Covered", 194, 230), ("for", 233, 244), ("tsunami.", 247, 285))]
    rows = _rows(table_from_lines(_sheet(middle), 10.0, trusted=True))
    assert any(r[0] == "Actions of the sea" and r[1] == "No" for r in rows), rows


def test_a_label_run_on_into_its_answer_is_divided_before_the_answer():
    # WFI: "Yes" 10pt after "from".
    middle = [_segment(400, ("Items", 50, 77), ("away", 80, 104), ("from", 107, 131), ("Yes", 141, 157)),
              _segment(400, ("We", 194, 209), ("offer", 212, 235), ("limited", 238, 267), ("cover.", 270, 297))]
    rows = _rows(table_from_lines(_sheet(middle), 10.0, trusted=True))
    assert any(r[0] == "Items away from" and r[1] == "Yes" for r in rows), rows


def test_a_word_space_before_the_answers_edge_is_not_divided():
    middle = [_segment(400, ("Actions", 50, 85), ("of", 88, 97), ("the", 100, 114), ("sea", 117, 138), ("No", 141, 154)),
              _segment(400, ("Covered", 194, 230), ("for", 233, 244), ("tsunami.", 247, 285))]
    rows = _rows(table_from_lines(_sheet(middle), 10.0, trusted=True))
    assert not any(r[1] == "No" for r in rows), rows


def test_a_gap_whose_far_side_starts_nowhere_the_rows_start_is_not_divided():
    middle = [_segment(400, ("Actions", 50, 85), ("of", 88, 97), ("the", 100, 114), ("sea", 117, 130), ("No", 147, 160)),
              _segment(400, ("Covered", 194, 230), ("for", 233, 244), ("tsunami.", 247, 285))]
    rows = _rows(table_from_lines(_sheet(middle), 10.0, trusted=True))
    assert not any(r[0] == "Actions of the sea" and r[1] == "No" for r in rows), rows


def test_a_line_whose_words_stand_evenly_apart_is_not_divided_at_an_edge():
    # A census profile set in a fixed-width face spaces every word 0.6 of the body size apart on a character grid, so
    # a word of its title starts where other rows' answers start after a gap as wide as the rule's measure. A gap that
    # is no wider than the line's own word spaces divides nothing.
    middle = [_segment(400, ("All", 50, 68), ("rows", 74, 98), ("of", 104, 116), ("the", 122, 135), ("table", 141, 171))]
    rows = _rows(table_from_lines(_sheet(middle), 10.0, trusted=True))
    assert any(r[0] == "All rows of the table" for r in rows), rows


def test_a_list_items_hanging_indent_is_not_a_column_edge():
    # Bank of Melbourne's building modifications table sets its condition as bullets, and the wrapped lines of each item
    # start on the list's hanging indent with nothing beside them. Counted as an edge, the indent cut "you were living in
    # the" off its bullet and filed it under "How much we will pay"; only a start with something to its left counts.
    lines = [_segment(121, ("When", 45, 68), ("we", 70, 82), ("pay", 83, 97)),
             _segment(121, ("How", 157, 174), ("much", 176, 198), ("we", 199, 211), ("will", 213, 227), ("pay", 228, 242)),
             _segment(121, ("What's", 268, 295), ("covered?", 297, 332)),
             _segment(139, ("We", 45, 57), ("will", 59, 71), ("pay", 73, 85), ("this", 87, 100), ("benefit", 102, 127)),
             _segment(139, ("We", 157, 169), ("will", 170, 182), ("pay", 184, 197), ("up", 199, 208), ("to", 210, 217), ("$10,000.", 219, 249)),
             _segment(139, ("Modifications", 268, 316), ("to", 317, 325), ("make", 326, 346), ("your", 348, 364)),
             _segment(151, ("when:", 45, 67)), _segment(151, ("home", 268, 289), ("building", 291, 320), ("accessible", 321, 357)),
             _segment(163, ("•", 57, 61), ("you", 68, 81), ("were", 83, 100), ("living", 102, 121), ("in", 123, 129), ("the", 131, 143)),
             _segment(163, ("for", 268, 278), ("your", 280, 296), ("disability.", 298, 330)),
             _segment(175, ("buildings", 68, 100), ("when", 102, 122), ("the", 124, 135)),
             _segment(187, ("insured", 68, 94), ("event", 96, 116), ("took", 118, 133)),
             _segment(199, ("place,", 68, 88), ("and", 90, 104)),
             _segment(211, ("•", 57, 61), ("we", 68, 79), ("receive", 80, 106)),
             _segment(223, ("confirmation", 68, 114), ("of", 116, 123)),
             _segment(235, ("your", 68, 84), ("paraplegia.", 86, 128))]
    rows = _rows(table_from_lines(lines, 9.0, trusted=True))
    assert not any(c.startswith("you were living") for r in rows for c in r[1:]), rows
    assert any("you were living in the" in r[0] for r in rows), rows
