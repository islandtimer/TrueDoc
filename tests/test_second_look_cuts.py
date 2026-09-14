"""A second look at the column cuts the vote missed: it sharpens a table, and it will not only split phrases.

`_refine_segments` finds column boundaries by a vote across a table's rows. Its second look judges a
range only by the rows with words on both sides of it, because a row lying wholly to one side can say
nothing about a boundary there: on a Key Facts Sheet the wrapped lines of the exclusions column had
out-voted the gap between each event and its "Yes". A lower bar needs limits, and each is tested here
against the geometry that showed the need for it:

- a cut whose only work is to split text running across it on a word space is refused. On the benchmark
  the second look had cut "Groups at | Risk" and "quimicos | e" on gaps of about half the body size, each
  the one piece of text its cut divided; every other row already stood apart. Where the text layer has
  run cells together across real gaps, the cut is proven, and a label set tight against its answer on the
  same sheet ("Accidental Breakage | Yes", 0.46 of the body size) is divided with the rest;
- in the text-layer finder, where no ruling and no layout model says a table is there, the second look
  only sharpens a table the first look finds (on a court form its cut made one table of an address box
  and the claim box beside it).
"""
from truedoc.model import BBox, Line, Page, Word
from truedoc.tables.aligned import _build_table, _Candidate, _cluster_rows, find_aligned_tables, table_from_lines

EVENTS = [([("Fire", 40, 58), ("and", 61, 77), ("Explosion", 80, 122)], ("Yes", 140, 156)),
          ([("Flood", 40, 66)], ("Optional", 140, 178)),
          ([("Storm", 40, 68)], ("Yes", 140, 156)),
          ([("Earthquake", 40, 92)], ("Yes", 140, 156))]


def _segment(y, *words, height=10):
    """A text-layer segment of (text, x0, x1) words."""
    ws = [Word(text=t, bbox=BBox(x0, y, x1, y + height)) for t, x0, x1 in words]
    return Line(words=ws, bbox=BBox.union_all(w.bbox for w in ws))


def _cells(table):
    return [c.text for row in table.grid() for c in row if c and c.text]


def _key_facts_sheet(*extra, apart=False):
    """Four events and two wrapped lines of exclusions under each: twelve rows with words, only four of them
    reaching across the gap in front of the answers - too few for the vote, enough for the second look.
    Each label and its answer are one segment, as the text layer ran them together, unless `apart`."""
    lines = []
    for i, (label, answer) in enumerate(EVENTS):
        y = 100 + 40 * i
        lines.extend([_segment(y, *label), _segment(y, answer)] if apart else [_segment(y, *label, answer)])
        lines.append(_segment(y, ("Excludes", 200, 240), ("damage", 243, 277)))
        lines.append(_segment(y + 12, ("caused", 200, 232), ("by", 235, 245), ("scorching", 248, 290)))
        lines.append(_segment(y + 24, ("or", 200, 210), ("melting", 213, 247)))
    return lines + list(extra)


def test_the_second_look_divides_an_answer_column_the_vote_missed():
    table = table_from_lines(_key_facts_sheet(), 10.0, trusted=True)
    assert table is not None
    cells = _cells(table)
    assert "Fire and Explosion" in cells and "Yes" in cells, cells


def test_a_label_set_tight_against_its_answer_is_divided_with_the_rest():
    # "Breakage" ends 4.6pt before its "Yes": under 0.6 of the body size, on the answers' own edge.
    tight = [_segment(260, ("Accidental", 40, 90), ("Breakage", 93, 135.4), ("Yes", 140, 156)),
             _segment(260, ("Excludes", 200, 240), ("scratching", 243, 290))]
    table = table_from_lines(_key_facts_sheet(*tight), 10.0, trusted=True)
    assert table is not None
    cells = _cells(table)
    assert "Accidental Breakage" in cells and "Fire and Explosion" in cells, cells


def test_a_cut_that_would_only_split_a_phrase_is_refused():
    # The labels already stand apart from their answers; the one segment the cut would divide is a phrase
    # whose "to" ends at 134 and whose "glass" starts at 139, enough of a gap to vote for a column there.
    phrase = [_segment(260, ("Accidental", 40, 90), ("damage", 93, 125), ("to", 128, 134), ("glass", 139, 162)),
              _segment(260, ("Excludes", 200, 240), ("scratching", 243, 290))]
    table = table_from_lines(_key_facts_sheet(*phrase, apart=True), 10.0, trusted=True)
    assert table is not None
    cells = _cells(table)
    assert any("Accidental damage to glass" in c for c in cells), cells
    assert "glass" not in cells, cells


def _court_form():
    """An address box and, beside it, the claim box of a court form, set out as the scan's text layer gave
    them (olmOCR-bench tables/f2ad0cd0): each row pairs a line of one box with a line of the other."""
    rows = [(114.0, [("To", 100, 112), ("[Claimant][Defendant]['s", 115, 230), ("solicitor]", 233, 265)],
             [[("Claim", 314, 343), ("No.", 346, 358), ("CL-2016-000631", 381, 456)]]),
            (128.2, [("Malabu", 103, 140), ("Oil", 143, 158), ("&", 161, 168), ("Gas", 171, 190), ("Limited", 193, 228)], []),
            (140.9, [("A", 103, 110), ("company", 113, 155), ("Incorporated", 158, 220), ("under", 223, 250), ("the", 253, 267)],
             [[("Claimant", 313, 356)]]),
            (153.4, [("Laws", 102, 125), ("of", 128, 137), ("the", 140, 155), ("federal", 158, 190), ("Republic", 193, 238), ("of", 241, 252)],
             [[("(including", 313, 356), ("The", 381, 400), ("federal", 403, 437), ("Republic", 440, 475), ("of", 478, 489)]]),
            (166.1, [("Nigeria", 102, 136)], [[("ref.)", 312, 330)], [("Nigeria", 381, 414)]]),
            (178.8, [("35", 102, 114), ("Kingsway", 117, 160), ("Road", 163, 189)], [[("Defendant", 312, 360)]]),
            (191.3, [("Ikoyi", 101, 126)],
             [[("(including", 312, 355), ("Malabu", 380, 414), ("Oil", 417, 432), ("&", 435, 442), ("Gas", 445, 465), ("Limited", 468, 497)]]),
            (204.0, [("Lagos", 101, 129)], [[("ref.)", 311, 329)]])]
    lines = []
    for y, left, right in rows:
        lines.append(_segment(y, *left, height=12))
        lines.extend(_segment(y, *seg, height=12) for seg in right)
    return lines


def test_the_second_look_does_not_make_one_table_of_two_boxes_side_by_side():
    lines = _court_form()
    cand = _Candidate(rows=_cluster_rows(lines, 11.0), bbox=BBox.union_all(l.bbox for l in lines))
    # The case itself: no table to the first look, three columns once the second look cuts "Claim No."
    # from "CL-2016-000631".
    assert _build_table(cand, 11.0, second_look=False) is None
    assert _build_table(cand, 11.0) is not None
    tables, _ = find_aligned_tables(Page(number=1, width=596, height=842), lines, 11.0)
    assert not tables, [_cells(b.table) for b in tables]
