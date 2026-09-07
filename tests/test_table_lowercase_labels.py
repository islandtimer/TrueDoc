"""A table whose labels start lowercase is not one wrapped row.

A Polish scoring sheet lists six body parts beside their point limits ("typ | do 15 pkt.",
"głowę i szyję | do 5 pkt.", ...). Every line starts lowercase, so the wrapped-cell rule read
lines 2 to 6 as the continuation of line 1 and folded the table into a single row of two
six-phrase cells. A line whose value cell carries a number under a value that carries a number
is an entry of its own (found 7 Sept 2026, run 48's no-table census).
"""
from truedoc.tables.aligned import _Row, _merge_wrapped_rows


def _rows(n, y0=473.0, pitch=12.5, h=9.0):
    return [_Row(segments=[], y0=y0 + i * pitch, y1=y0 + i * pitch + h) for i in range(n)]


def test_lowercase_label_value_rows_stay_rows():
    grid = [
        ["typ", "do 15 pkt."],
        ["głowę i szyję", "do 5 pkt."],
        ["kłodę", "do 15 pkt."],
        ["kończyny przednie", "do 10 pkt."],
        ["kończyny tylne", "do 10 pkt."],
        ["kopyta", "do 10 pkt."],
    ]
    merged, geom = _merge_wrapped_rows([list(r) for r in grid], _rows(6), 9.0)
    assert merged == grid
    assert len(geom) == 6


def test_wrapped_lists_and_broken_numbers_still_fold():
    # A comma or a hyphen at the end of the cell above is a wrapped cell however
    # many numbers the lines carry (a course list, a design-level range).
    grid = [
        ["Requirement", "Units"],
        ["ENGR 250, ENGR 261, ENGR 335, ENGR 350A,", "15"],
        ["ENGR 370A", ""],
        ["Complete Final Design (approx. 90-", "March 8, 2003"],
        ["95% design level)", ""],
    ]
    merged, geom = _merge_wrapped_rows([list(r) for r in grid], _rows(5, pitch=11.0), 9.0)
    assert merged == [
        ["Requirement", "Units"],
        ["ENGR 250, ENGR 261, ENGR 335, ENGR 350A, ENGR 370A", "15"],
        ["Complete Final Design (approx. 90-95% design level)", "March 8, 2003"],
    ]


def test_wrapped_text_cells_still_fold():
    # Both columns wrap: each second line continues the phrase above it, and no
    # number sits under a number.
    grid = [
        ["Eligibility", "Contact"],
        ["US Citizens and", "Please visit the"],
        ["Permanent Residents", "program website"],
    ]
    merged, geom = _merge_wrapped_rows([list(r) for r in grid], _rows(3, pitch=11.0), 9.0)
    assert merged == [["Eligibility", "Contact"], ["US Citizens and Permanent Residents", "Please visit the program website"]]
    assert len(geom) == 2
