"""A statistic printed under its value ("0.150**" over "(4.07)") is one cell.

Regression tables set a t-value or a standard error in brackets on the line under each
estimate; a reader quotes the pair as one value, and so does the benchmark ("1.169 (0.59)").
Both table builders fold such a row into the row above: the ruled path from the table
finder's rows, the aligned path from the clustered rows. Eight checks on five pages in
run 48 (7 Sept 2026).
"""
from truedoc.tables.aligned import _NUMERIC, _Row, _header_row_count, _merge_wrapped_rows
from truedoc.tables.cells import is_bracketed_statistic
from truedoc.tables.ruled import fold_stacked_statistics


def test_a_value_with_its_statistic_is_a_number():
    # Significance stars sit on the value, before the bracket, and a layer may
    # set a space after the minus sign; three stars are common.
    for cell in ["− 0.0548*** (0.0175)", "0.0475** (0.0205)", "10.615 (1.06)", "-11.607 (-1.07)", "0.150**", "− 0.0796", "12 (4.5%)"]:
        assert _NUMERIC.match(cell), cell
    for cell in ["(1) Dropped Course", "Observations", "(Standardized)"]:
        assert not _NUMERIC.match(cell), cell


def test_folded_statistics_row_stays_a_body_row():
    grid = [
        ["", "(1) Dropped Course", "(2) Passed Course", "(3) Total Numeric Score(Standardized)"],
        ["URM*URM TA", "− 0.0548*** (0.0175)", "0.0475** (0.0205)", "− 0.0796 (0.0865)"],
        ["Observations", "4288", "4288", "4016"],
    ]
    assert _header_row_count(grid) == 1


def test_bracketed_statistic_shape():
    assert all(is_bracketed_statistic(t) for t in ["(4.07)", "(-1.07)", "(.22)", "(0.0796)", "(7)", "(42.9%)", "[0.12]", "(1,234)", "(0.59)*"])
    assert not any(is_bracketed_statistic(t) for t in ["(n = 12)", "(a)", "4.07", "(2.2e-16)", "", "(1) Chem"])


def test_ruled_rows_fold_statistics_into_their_values():
    rows = [
        ["", "(1)", "(2)"],
        ["Age", "0.268**", "0.150**"],
        ["", "(3.54)", "(4.07)"],
        ["Age squared", "-0.004**\nx", "-0.002**"],
        ["", "(-2.70)", "(-3.01)"],
        ["Observations", "836", "837"],
    ]
    assert fold_stacked_statistics(rows, 3) == [
        (["", "(1)", "(2)"], [0]),
        (["Age", "0.268** (3.54)", "0.150** (4.07)"], [1, 2]),
        (["Age squared", "-0.004** x (-2.70)", "-0.002** (-3.01)"], [3, 4]),
        (["Observations", "836", "837"], [5]),
    ]


def test_ruled_rows_that_are_not_stacked_statistics_stay():
    # Under the heading row, a labelled row of brackets, brackets under words.
    assert len(fold_stacked_statistics([["Model", "(1)", "(2)"], ["", "(0.1)", "(0.2)"]], 3)) == 2
    assert len(fold_stacked_statistics([["h", "a", "b"], ["x", "1", "2"], ["(SD)", "(1.1)", "(1.2)"]], 3)) == 3
    assert len(fold_stacked_statistics([["h", "a", "b"], ["x", "yes", "no"], ["", "(1)", "(2)"]], 3)) == 3
    # A bracket row under another bracket row is not a value's statistic.
    assert len(fold_stacked_statistics([["h", "a"], ["x", "1"], ["", "(1)"], ["", "(2)"]], 2)) == 3


def test_aligned_rows_fold_statistics_into_their_values():
    size = 9.0
    grid = [
        ["", "(1) Chem 1A GPA", "(2) Prior Cum. GPA"],
        ["URM * URM TA", "0.1026", "− 0.0142"],
        ["", "(0.0746)", "(0.0328)"],
        ["Observations", "836", "837"],
    ]
    rows = [_Row(segments=[], y0=100 + 12 * i, y1=109 + 12 * i) for i in range(4)]
    merged, geom = _merge_wrapped_rows(grid, rows, size)
    assert merged == [
        ["", "(1) Chem 1A GPA", "(2) Prior Cum. GPA"],
        ["URM * URM TA", "0.1026 (0.0746)", "− 0.0142 (0.0328)"],
        ["Observations", "836", "837"],
    ]
    assert (geom[1].y0, geom[1].y1) == (112, 133)


def test_aligned_rows_keep_a_bracket_row_under_words():
    size = 9.0
    grid = [["", "A", "B"], ["Group", "Yes", "No"], ["", "(12)", "(30)"]]
    rows = [_Row(segments=[], y0=100 + 12 * i, y1=109 + 12 * i) for i in range(3)]
    merged, _ = _merge_wrapped_rows(grid, rows, size)
    assert len(merged) == 3
