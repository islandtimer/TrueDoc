"""A second value on the second line of its cell does not start a row.

AAMI's fire-and-theft Key Facts Sheets answer "Fire and Explosion" with two values, one above the
other - "Yes" for fire, "No" for explosion - beside a sentence that runs on past the first line.
"No" under "Yes" continues nothing, so the second line stood as a row of its own and the sentence
was cut in two: `| Fire and Explosion | Yes | Fire - no cover ... from arcing, |` over
`| | No | scorching, melting, or cigarette burns unless ... |` (read against the page, 18 September
2026). No cell of a new row opens in the middle of a sentence.

Where the line stands cannot say so: the same table's next real row also starts one leading below.
"""

from truedoc.model import BBox, Line, Word
from truedoc.tables.aligned import _Row, _merge_wrapped_rows

COLUMNS = [(40.0, 150.0), (150.0, 210.0), (210.0, 560.0)]        # event | yes / no | conditions
LEADING = 11.5


def _line(text, x0, y0):
    words, x = [], x0
    for token in text.split(" "):
        if token:
            words.append(Word(text=token, bbox=BBox(x, y0, x + 5.0 * len(token), y0 + 10.0)))
        x += 5.0 * (len(token) + 1)
    return Line(words=words, bbox=BBox(x0, y0, x0 + 5.0 * len(text), y0 + 10.0))


def _merged(*specs):
    grid, rows = [], []
    for cells, top in specs:
        row = [""] * len(COLUMNS)
        for text, x0 in cells:
            row[next(i for i, (lo, hi) in enumerate(COLUMNS) if lo <= x0 < hi)] = text
        grid.append(row)
        rows.append(_Row(segments=[_line(text, x0, top) for text, x0 in cells], y0=top, y1=top + 10.0))
    out, _geometry = _merge_wrapped_rows(grid, rows, 10.0, COLUMNS)
    return out


HEAD = ([("Event", 42.0), ("Yes/No", 152.0), ("Some examples of conditions", 212.0)], 100.0)
FIRE = ([("Fire and Explosion", 42.0), ("Yes", 152.0), ("Fire - no cover for loss or damage to contents from arcing,", 212.0)], 120.0)
FLOOD = ([("Flood", 42.0), ("No", 152.0)], 120.0 + 4 * LEADING)


def test_the_second_answer_beside_a_running_sentence_is_the_entry_s_second_line():
    out = _merged(
        HEAD, FIRE,
        ([("No", 152.0), ("scorching, melting, or cigarette burns unless a fire spreads", 212.0)], 120.0 + LEADING),
        ([("from the initial burn spot.", 212.0)], 120.0 + 2 * LEADING),
        ([("There is no cover for Explosion.", 212.0)], 120.0 + 3 * LEADING),
        FLOOD,
    )
    assert [r[0] for r in out] == ["Event", "Fire and Explosion", "Flood"]
    assert out[1][1] == "Yes No"
    assert out[1][2] == ("Fire - no cover for loss or damage to contents from arcing, scorching, melting, or cigarette "
                         "burns unless a fire spreads from the initial burn spot. There is no cover for Explosion.")


def test_a_line_under_a_sentence_that_has_closed_is_a_row_still():
    closed = ([("Fire and Explosion", 42.0), ("Yes", 152.0), ("Fire - no cover for damage from arcing.", 212.0)], 120.0)
    out = _merged(HEAD, closed, ([("No", 152.0), ("scorching and melting are not fire", 212.0)], 120.0 + LEADING), FLOOD)
    assert len(out) == 4 and out[2][1] == "No"


def test_values_with_nothing_carried_on_beside_them_are_a_row():
    out = _merged(HEAD, FIRE, ([("No", 152.0), ("Explosion", 212.0)], 120.0 + LEADING), FLOOD)
    assert len(out) == 4 and out[2] == ["", "No", "Explosion"]


def test_a_number_beside_the_running_text_is_a_value_of_its_own_row():
    # The merger never folds a line that holds a number on what the line says: a number is a value.
    out = _merged(
        HEAD, FIRE,
        ([("250", 152.0), ("scorching, melting, or cigarette burns unless a fire spreads", 212.0)], 120.0 + LEADING),
        FLOOD,
    )
    assert len(out) == 4 and out[2][1] == "250"


def test_under_a_line_with_no_label_nothing_opens_an_entry_to_belong_to():
    unlabelled = ([("Yes", 152.0), ("Fire - no cover for loss or damage to contents from arcing,", 212.0)], 120.0)
    out = _merged(HEAD, unlabelled, ([("No", 152.0), ("scorching, melting, or cigarette burns unless a fire spreads", 212.0)], 120.0 + LEADING), FLOOD)
    assert [r[1] for r in out] == ["Yes/No", "Yes", "No", "No"]
