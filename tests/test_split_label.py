"""A label that wraps continues its row, whatever the column beside it begins with.

Labels and long text wrap; a short value never does. On a Key Facts Sheet "Escape" sits over "of liquid"
with a "Yes" beside the first line only, and the exclusions beside the second line open a new sentence
("...certain items." over "Not covered for..."). The merger asked every filled column whether it
continues the cell above; the exclusions said no, and "of liquid" was left as a row of its own - an event
with no answer under a label that means nothing on its own. The label column decides instead: a lowercase
tail of a few words, under a label not closed, on a row that leaves empty the short value above it, is
the second line of that label. A row that fills its value is an entry, whatever case it starts in, and so
is a line carrying a number under a line carrying a number - the merger's own guard, which the label column
does not escape: an index read as two columns glued "permeability 454, 457, 465" to the entry above.
"""
from truedoc.model import BBox, Line, Word
from truedoc.tables.aligned import table_from_lines


def _segment(y, *words):
    ws = [Word(text=t, bbox=BBox(x0, y, x1, y + 10)) for t, x0, x1 in words]
    return Line(words=ws, bbox=BBox.union_all(w.bbox for w in ws))


def _rows(table):
    assert table is not None
    return [[(c.text if c else "") for c in row] for row in table.grid()]


def _sheet(second_line):
    return [_segment(100, ("Fire", 40, 58), ("and", 61, 77), ("Explosion", 80, 122)),
            _segment(100, ("Yes", 140, 156)),
            _segment(100, ("Excludes", 200, 240), ("scorching.", 243, 290)),
            _segment(130, ("Escape", 40, 70)),
            _segment(130, ("Yes", 140, 156)),
            _segment(130, ("Excludes", 200, 240), ("damage", 243, 277), ("to", 280, 290), ("certain", 293, 325), ("items.", 328, 356)),
            *second_line,
            _segment(172, ("Storm", 40, 68)),
            _segment(172, ("Yes", 140, 156)),
            _segment(172, ("Excludes", 200, 240), ("rain", 243, 262), ("damage.", 265, 300))]


def test_the_second_line_of_a_label_continues_its_row():
    tail = [_segment(142, ("of", 40, 50), ("liquid", 53, 78)),
            _segment(142, ("Not", 200, 216), ("covered", 219, 255), ("for", 258, 272), ("leaks.", 275, 302))]
    rows = _rows(table_from_lines(_sheet(tail), 10.0, trusted=True))
    assert any(r[0] == "Escape of liquid" for r in rows), rows
    assert not any(r[0] == "of liquid" for r in rows), rows


def test_a_row_that_fills_its_value_is_an_entry_of_its_own():
    entry = [_segment(142, ("hail", 40, 58)),
             _segment(142, ("No", 140, 152)),
             _segment(142, ("Not", 200, 216), ("covered.", 219, 258))]
    rows = _rows(table_from_lines(_sheet(entry), 10.0, trusted=True))
    assert any(r[0] == "hail" for r in rows), rows


def test_a_number_under_a_number_is_the_next_entry():
    # A back-of-book index read as two columns: "permeability 454, 457, 465" opens the next entry, though it
    # starts in lower case, sits tight under "perfluorocarbon 455, 458, 479" and leaves the right column empty.
    lines = [_segment(100, ("PCTP", 40, 62), ("125,", 65, 83), ("143-4", 86, 110)),
             _segment(100, ("pyrolysis", 260, 300), ("431-2", 303, 327)),
             _segment(112, ("perfluorocarbon", 40, 110), ("455,", 113, 131), ("458,", 134, 152), ("479", 155, 170)),
             _segment(112, ("pyrophosphate", 260, 320), ("anions", 323, 350), ("372", 353, 368)),
             _segment(124, ("permeability", 40, 95), ("454,", 98, 116), ("457,", 119, 137), ("465", 140, 155)),
             _segment(136, ("peroxidases", 40, 92), ("373,", 95, 113), ("374", 116, 131)),
             _segment(136, ("quantum", 260, 297), ("dots", 300, 318), ("458", 321, 336))]
    rows = _rows(table_from_lines(lines, 10.0, trusted=True))
    assert any(r[0] == "permeability 454, 457, 465" for r in rows), rows
