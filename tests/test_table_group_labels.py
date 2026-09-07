"""A row label written once beside a group of entries spans the group.

A survey table: "Education" sits centred beside three education levels,
"Gender" beside three answers, "Age" beside three bands. Each entry is a row
of its own (the checker asks for "Age" as the left heading of "18-29"), the
label spans its rows, and the first entry must not be folded into the
"Groups" heading above it.
"""

from truedoc.model import BBox, Char, Line, Word
from truedoc.tables.aligned import table_from_lines

SIZE = 11.0


def _line(text, x0, y0, space=3.0):
    words = []
    x = x0
    for tok in text.split():
        w = 5.0 * len(tok)
        chars = [Char(text=c, bbox=BBox(x + i * 5, y0, x + (i + 1) * 5, y0 + SIZE), font="F", size=SIZE, origin_y=y0 + 0.8 * SIZE) for i, c in enumerate(tok)]
        words.append(Word(text=tok, bbox=BBox(x, y0, x + w, y0 + SIZE), chars=chars))
        x += w + space
    return Line(words=words, bbox=BBox(x0, y0, x - space, y0 + SIZE))


ROWS = [
    ("Category", "Groups"),
    ("", "High school or less (107; 16.3%)"),
    ("Education", "Higher degree (288; 43.8%)"),
    ("", "Some college (262; 39.9%)"),
    ("", "Male (337; 51.3%)"),
    ("Gender", "Female (284; 43.2%)"),
    ("", "Other (36; 5.5%)"),
    ("", "18-29 (464; 70.6%)"),
    ("Age", "30-49 (156; 23.7%)"),
    ("", "Over 50 (37; 5.6%)"),
]


def test_centred_group_labels_span_their_entries():
    lines = []
    y = 100
    for label, entry in ROWS:
        if label:
            lines.append(_line(label, 60, y))
        lines.append(_line(entry, 200, y))
        y += 14
    t = table_from_lines(lines, SIZE, trusted=True)
    assert t is not None and t.n_cols == 2 and t.n_rows == 10
    assert [c.text for c in t.cells if c.row == 0] == ["Category", "Groups"]
    col1 = [c.text for c in sorted(t.cells, key=lambda c: c.row) if c.col == 1]
    assert col1[1:4] == ["High school or less (107; 16.3%)", "Higher degree (288; 43.8%)", "Some college (262; 39.9%)"]
    labels = {c.row: (c.text, c.rowspan) for c in t.cells if c.col == 0 and c.rowspan > 1}
    assert labels == {1: ("Education", 3), 4: ("Gender", 3), 7: ("Age", 3)}
    assert t.has_merged
    # The spanned rows carry no first-column cell of their own.
    assert not [c for c in t.cells if c.col == 0 and c.row in (2, 3, 5, 6, 8, 9)]
