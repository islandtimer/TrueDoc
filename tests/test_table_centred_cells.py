"""A two-line cell set centred on its row: its first line rises above the row's other cells."""

from truedoc.model import BBox, Char, Line, Word
from truedoc.tables.aligned import _Row, _merge_wrapped_rows


def _line(text, x0, x1, y0, h=10.2):
    chars = [Char(text=ch, bbox=BBox(x0 + i * 4, y0, x0 + (i + 1) * 4, y0 + h), font="Arial", size=9.1, origin_y=y0 + 8) for i, ch in enumerate(text)]
    return Line(words=[Word(text=text, bbox=BBox(x0, y0, x1, y0 + h), chars=chars)], bbox=BBox(x0, y0, x1, y0 + h))


def _row(*segs):
    lines = [_line(t, x0, x1, y0) for t, x0, x1, y0 in segs]
    return _Row(segments=lines, y0=min(l.bbox.y0 for l in lines), y1=max(l.bbox.y1 for l in lines))


def test_centred_two_line_cell_joins_the_row_it_overlaps():
    # From a product specification sheet: "White to cream" / "powder" is one cell,
    # centred against "Appearance" and "Visual".
    rows = [
        _row(("CHARACTERISTIC", 94, 174, 311.1), ("SPECIFICATION", 209, 279, 311.1), ("METHOD OF ANALYSIS", 322, 424, 311.1)),
        _row(("AI, as Methomyl", 94, 159, 337.0), ("87.5 - 92.5 %", 209, 263, 337.0), ("High Performance Liquid Chromatography", 322, 491, 337.0)),
        _row(("pH (1 % in water)", 94, 164, 349.9), ("4.0 - 8.0", 209, 242, 349.9), ("pH-meter", 322, 360, 349.9)),
        _row(("White to cream", 209, 270, 361.7)),
        _row(("Appearance", 94, 143, 366.7), ("Visual", 322, 347, 366.7)),
        _row(("powder", 209, 239, 372.0)),
    ]
    grid = [
        ["CHARACTERISTIC", "SPECIFICATION", "METHOD OF ANALYSIS"],
        ["AI, as Methomyl", "87.5 - 92.5 %", "High Performance Liquid Chromatography"],
        ["pH (1 % in water)", "4.0 - 8.0", "pH-meter"],
        ["", "White to cream", ""],
        ["Appearance", "", "Visual"],
        ["", "powder", ""],
    ]
    merged, geom = _merge_wrapped_rows(grid, rows, 9.1)
    assert merged == [
        ["CHARACTERISTIC", "SPECIFICATION", "METHOD OF ANALYSIS"],
        ["AI, as Methomyl", "87.5 - 92.5 %", "High Performance Liquid Chromatography"],
        ["pH (1 % in water)", "4.0 - 8.0", "pH-meter"],
        ["Appearance", "White to cream powder", "Visual"],
    ], merged
    assert len(geom) == 4


def test_table_of_short_labels_is_not_taken_for_prose():
    from truedoc.model import Page
    from truedoc.tables.aligned import find_aligned_tables

    page = Page(number=1, width=612, height=792)
    spec = [
        ("Relevant Document", 90, 190, 148.0), ("Document Owner", 233, 320, 148.0), ("Reference", 374, 430, 148.0),
        ("BSC", 90, 112, 161.1), ("Elexon", 233, 266, 161.1), ("Separate Annex 2", 374, 465, 161.1),
        ("CUSC", 90, 120, 173.8), ("NGET", 233, 261, 173.8), ("Separate Annex 3", 374, 465, 173.8),
        ("DCUSA", 90, 128, 186.4), ("DCUSA Limited", 233, 309, 186.4), ("Separate Annex 4", 374, 465, 186.4),
        ("Distribution Code", 90, 188, 199.1), ("Distribution Licensees", 233, 343, 199.1), ("Separate Annex 5", 374, 465, 199.1),
        ("Grid Code", 90, 145, 223.9), ("NGET", 233, 261, 223.9), ("Separate Annex 6", 374, 465, 223.9),
        ("STC", 90, 111, 248.6), ("NGET, SPT and SHETL", 233, 345, 248.6), ("Separate Annex 7", 374, 465, 248.6),
        ("GBSQSS", 90, 135, 261.3), ("NGET, SPT and SHETL", 233, 345, 261.3), ("Separate Annex 8", 374, 465, 261.3),
    ]
    lines = [_line(t, x0, x1, y0, h=12.2) for t, x0, x1, y0 in spec]
    tables, rest = find_aligned_tables(page, lines, 10.0)
    assert len(tables) == 1 and tables[0].table.n_cols == 3 and tables[0].table.n_rows == 8, tables


def test_plain_wrapped_continuation_still_folds_upwards():
    rows = [
        _row(("Name", 50, 80, 100.0), ("Description", 150, 200, 100.0)),
        _row(("Alpha", 50, 80, 112.0), ("a long description that", 150, 250, 112.0)),
        _row(("wraps onto a second line", 150, 250, 123.0)),
        _row(("Beta", 50, 80, 135.0), ("short", 150, 180, 135.0)),
    ]
    grid = [["Name", "Description"], ["Alpha", "a long description that"], ["", "wraps onto a second line"], ["Beta", "short"]]
    merged, geom = _merge_wrapped_rows(grid, rows, 9.0)
    assert merged == [["Name", "Description"], ["Alpha", "a long description that wraps onto a second line"], ["Beta", "short"]], merged
