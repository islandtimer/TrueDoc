"""A cell that holds a table is read as that table (D038, the owner's decision of 20 September 2026).

CGU's Key Facts Sheet sets a small table in the third cell of "High value items and collections" - Policy / Item
Limit / Overall Limit over three rows - and another, with no heading of its own, in "Items away from insured
address". The geometry below is theirs (`bench/probes/nested_table_census.py` sized the signal: every line of the
cell broken at a wide gap, the pieces after it starting at one place).
"""
from truedoc.model import BBox, Line, Word
from truedoc.tables.cell_tables import read_inner_table

SIZE = 9.0
BOX = BBox(190.0, 660.0, 575.0, 725.0)


def _line(pieces, y):
    """One text line of pieces set at given x, each word five points a character, a space one character wide."""
    words = []
    for text, x in pieces:
        for token in text.split(" "):
            words.append(Word(text=token, bbox=BBox(x, y, x + 4.6 * len(token), y + SIZE)))
            x += 4.6 * (len(token) + 1)
    return Line(words=words, bbox=BBox(words[0].bbox.x0, y, words[-1].bbox.x1, y + SIZE))


def _lines(rows):
    return [_line(pieces, 666.6 + 14.2 * i) for i, pieces in enumerate(rows)]


LIMITS = [
    [("Policy", 193.6), ("Item Limit", 315.2), ("Overall Limit", 373.0)],
    [("Accidental Damage Home", 193.6), ("$2,500/item", 315.2), ("20% of Contents SI or $7,500", 373.0)],
    [("Listed Events Home", 193.6), ("$2,500/item", 315.2), ("20% of Contents SI or $5,000", 373.0)],
    [("Fundamentals Home", 193.6), ("$1,000/item", 315.2), ("$2,000", 373.0)],
]
AWAY = [
    [("Accidental Damage Home", 193.6), ("Australia & New Zealand", 315.2)],
    [("Listed Events Home", 193.6), ("Australia up to 90 consecutive days", 315.2)],
    [("Fundamentals Home", 193.6), ("Not Covered", 315.2)],
]


def _flat(rows):
    return " ".join(text for pieces in rows for text, _x in pieces)


def _grid(table):
    return [[(c.text if c is not None else "") for c in r] for r in table.grid()]


def test_a_cell_set_as_a_table_is_read_as_one_with_the_heading_it_has():
    inner = read_inner_table(_lines(LIMITS), _flat(LIMITS), SIZE, BOX)
    assert inner is not None and (inner.n_rows, inner.n_cols) == (4, 3)
    assert _grid(inner)[0] == ["Policy", "Item Limit", "Overall Limit"]
    assert _grid(inner)[3] == ["Fundamentals Home", "$1,000/item", "$2,000"]
    assert [c.is_header for c in inner.cells if c.row == 0] == [True, True, True]     # it names; the rows beneath count
    assert not any(c.is_header for c in inner.cells if c.row > 0)


def test_a_first_row_that_is_a_row_like_the_others_is_not_a_heading():
    inner = read_inner_table(_lines(AWAY), _flat(AWAY), SIZE, BOX)
    assert inner is not None and (inner.n_rows, inner.n_cols) == (3, 2)
    assert not any(c.is_header for c in inner.cells)


def test_running_text_in_a_cell_is_not_a_table():
    prose = [[("Covered for fire and explosion. Not covered for loss or damage caused by a bushfire or", 193.6)],
             [("grassfire within 48 hours of the start of your policy. Exceptions apply to renewals and", 193.6)],
             [("where the policy replaces another with no break in cover.", 193.6)]]
    assert read_inner_table(_lines(prose), _flat(prose), SIZE, BOX) is None


def test_a_list_inside_a_cell_is_left_to_the_list_reader():
    # Every line of a list breaks after its mark at the same place too; D028 owns those cells.
    listed = [[("✓", 193.6), ("Fixed ceiling, wall and floor coverings", 215.0)],
              [("✓", 193.6), ("Garages, carports and sheds", 215.0)],
              [("✓", 193.6), ("Swimming pools and spas", 215.0)]]
    assert read_inner_table(_lines(listed), _flat(listed), SIZE, BOX) is None


def test_two_lines_are_not_enough_to_call_it_a_table():
    assert read_inner_table(_lines(AWAY[:2]), _flat(AWAY[:2]), SIZE, BOX) is None


def test_the_inner_table_must_say_what_the_cell_said():
    # The cell's text is what the table builders settled on; an inner reading that differs from it is not taken.
    assert read_inner_table(_lines(LIMITS), _flat(LIMITS).replace("$2,000", "$2,500"), SIZE, BOX) is None
