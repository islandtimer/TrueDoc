"""The last line of a wrapped cell is part of the cell, whatever it says.

Read against their pages on 18 September 2026, three of the owner's Key Facts Sheets had rows that
are not rows: `| | | 51-52 |` under "...if you rent out your home. PDS pg.", `| | | PDS pg.31. |`,
"'Portable Contents'." under "...anywhere in the world under". The merger folds a wrapped line on
what it says, and a capital, a digit or a quotation mark says nothing. Where the line stands does:
at the left edge of the lines above it, one leading below the last.

Both halves are needed. On the same sheets 37 of the 40 one-cell rows that sit one leading below
the cell above are the band laid across the table, which is centred - those tables have no padding
between their rows (`bench/probes/orphan_row_census.py`).
"""

from truedoc.model import BBox, Line, Word
from truedoc.tables.aligned import _Row, _merge_wrapped_rows

COLUMNS = [(40.0, 150.0), (150.0, 210.0), (210.0, 560.0)]        # event | yes / no | conditions
LEADING = 11.5


def _line(text, x0, y0, width=None):
    width = width if width is not None else 5.0 * len(text)
    box = BBox(x0, y0, x0 + width, y0 + 10.0)
    return Line(words=[Word(text=text, bbox=box)], bbox=box)


def _rows(*specs):
    """Each spec is a list of (text, x0) and a top; one text line a row, as the builder hands them over."""
    grid, rows = [], []
    for cells, top in specs:
        segments = [_line(text, x0, top) for text, x0 in cells]
        row = [""] * len(COLUMNS)
        for text, x0 in cells:
            row[next(i for i, (lo, hi) in enumerate(COLUMNS) if lo <= x0 < hi)] = text
        grid.append(row)
        rows.append(_Row(segments=segments, y0=top, y1=top + 10.0))
    return grid, rows


def _merged(*specs):
    grid, rows = _rows(*specs)
    out, _geometry = _merge_wrapped_rows(grid, rows, 10.0, COLUMNS)
    return out


HEAD = ([("Event", 42.0), ("Yes/No", 152.0), ("Some examples of conditions", 212.0)], 100.0)


def test_a_page_reference_that_wrapped_onto_a_line_of_its_own_stays_in_its_cell():
    out = _merged(
        HEAD,
        ([("Accidental Breakage", 42.0), ("Yes", 152.0), ("Yes - we pay for glass that is accidentally broken.", 212.0)], 120.0),
        ([("We also cover accidental damage if you rent out your home. PDS pg.", 212.0)], 120.0 + LEADING),
        ([("51-52", 212.0)], 120.0 + 2 * LEADING),
        ([("Earthquake", 42.0), ("Yes", 152.0), ("We cover your home if an earthquake causes loss.", 212.0)], 120.0 + 3 * LEADING + 6.0),
    )
    assert [r[0] for r in out] == ["Event", "Accidental Breakage", "Earthquake"]
    assert out[1][2].endswith("PDS pg. 51-52")


def test_a_capitalised_last_line_does_too():
    out = _merged(
        HEAD,
        ([("Items away", 42.0), ("Optional", 152.0), ("Contents are only covered inside the home.", 212.0)], 120.0),
        ([("We offer optional cover for items anywhere in the world under", 212.0)], 120.0 + LEADING),
        ([("‘Portable Contents’.", 212.0)], 120.0 + 2 * LEADING),
    )
    assert len(out) == 2 and out[1][2].endswith("anywhere in the world under ‘Portable Contents’.")


def test_a_band_across_the_table_one_leading_below_is_still_a_row_of_its_own():
    # The census's warning: in a table with no padding between rows the band sits exactly one
    # leading below the last line of the cell above. It is centred, not flush with that cell.
    out = _merged(
        HEAD,
        ([("Escape of liquid", 42.0), ("Yes", 152.0), ("We refer to escape of liquid as leaks, from a", 212.0)], 120.0),
        ([("terrarium, fishbowl, bucket.", 212.0)], 120.0 + LEADING),
        ([("Cover for valuables, collections and items away", 100.0)], 120.0 + 2 * LEADING),
        ([("High value items", 42.0), ("Optional", 152.0), ("Specified items only.", 212.0)], 120.0 + 3 * LEADING),
    )
    assert [r for r in out if any("Cover for valuables" in c for c in r)] != []
    assert not out[1][2].endswith("items away")
    assert len(out) == 4


def test_a_line_set_in_from_the_paragraph_is_not_its_next_line():
    out = _merged(
        HEAD,
        ([("Storm", 42.0), ("Yes", 152.0), ("You are not covered while you are renovating", 212.0)], 120.0),
        ([("your home, unless the damage is from wind.", 212.0)], 120.0 + LEADING),
        ([("Excess applies", 240.0)], 120.0 + 2 * LEADING),          # two words: the lexical rule leaves it be
    )
    assert len(out) == 3 and out[2][2] == "Excess applies"


def test_a_line_further_down_than_the_leading_is_not_its_next_line():
    out = _merged(
        HEAD,
        ([("Storm", 42.0), ("Yes", 152.0), ("You are not covered while you are renovating", 212.0)], 120.0),
        ([("your home, unless the damage is from wind.", 212.0)], 120.0 + LEADING),
        ([("Excess applies", 212.0)], 120.0 + 2 * LEADING + 5.0),
    )
    assert len(out) == 3


def test_under_a_one_line_cell_nothing_is_decided_here():
    # "Accidental Damage." under "...can be purchased to cover": no leading to compare with. A
    # stack of values under a blank label looks the same from here, and those are rows.
    out = _merged(
        HEAD,
        ([("Flood", 42.0), ("Optional", 152.0), ("For an extra premium cover can be purchased to cover", 212.0)], 120.0),
        ([("Accidental Damage.", 212.0)], 120.0 + LEADING),
    )
    assert len(out) == 3


def test_an_entry_opened_by_a_cross_is_never_the_tail_of_the_cell_above():
    out = _merged(
        HEAD,
        ([("Not covered", 42.0), ("No", 152.0), ("Loss caused by the sea, including", 212.0)], 120.0),
        ([("erosion and king tides.", 212.0)], 120.0 + LEADING),
        ([("✗ Pontoons", 212.0)], 120.0 + 2 * LEADING),
    )
    assert len(out) == 3 and out[2][2] == "✗ Pontoons"
