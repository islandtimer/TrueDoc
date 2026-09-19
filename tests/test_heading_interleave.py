"""A heading whose columns wrap by different amounts is one heading row.

Budget Direct's, Qantas's and ING's 2019 Key Facts Sheets centre each heading cell in its column, and the third
column's heading runs to three lines, so the lines interleave: "Some examples of specific conditions, exclusions or
limits that apply", then "Yes/No", then "Event/Cover" beside "to events/covers ...", then "Optional", then "of
others)*". The table built from the text gave each line a row, so the heading came out as five rows and its last line as
a row of its own. The line that carries a column on sits under an empty cell, and the lines break on no word that
cannot end a heading. A lowercase line two rows down is not always such a line: the first version of the rule folded a
two-level heading and two entries of a review table on the benchmark, and those shapes are kept apart.
"""
from truedoc.tables.aligned import _fold_wrapped_heading

HEADING = [
    ["", "", "Some examples of specific conditions, exclusions or limits that apply"],
    ["", "Yes/No", ""],
    ["Event/Cover", "", "to events/covers (see PDS and other policy documentation for details"],
    ["", "Optional", ""],
    ["", "", "of others)*"],
]
BODY = [
    ["Fire and Explosion", "Yes",
     "Excludes loss or damage caused by scorching or melting when there was heat but no flame."],
    ["Flood", "Optional", "Excludes damage to retaining walls, garden borders, driveways, paths, pavers or gardens."],
]


def test_a_heading_whose_columns_wrap_by_different_amounts_is_one_row():
    grid, _ = _fold_wrapped_heading([list(row) for row in HEADING + BODY], [])
    assert grid[0][0] == "Event/Cover"
    assert grid[0][1] == "Yes/No Optional"
    assert grid[0][2] == ("Some examples of specific conditions, exclusions or limits that apply to events/covers "
                          "(see PDS and other policy documentation for details of others)*")
    assert grid[1:] == BODY


def test_a_body_row_under_an_empty_cell_is_not_taken_into_the_heading():
    # The lowercase line a row further down must still be heading: a row that fills every column is a body row.
    grid = [
        ["", "", "Some examples of specific conditions, exclusions or limits that apply"],
        ["", "Yes/No", ""],
        ["Event/Cover", "Yes", "excludes loss or damage caused by scorching or melting"],
    ]
    folded, _ = _fold_wrapped_heading([list(row) for row in grid + BODY], [])
    assert folded[0] == ["", "", "Some examples of specific conditions, exclusions or limits that apply"]


def test_a_heading_of_two_levels_is_not_folded_into_one_row():
    # Group headings over "n | % | n | %" (tables 0cda549c on the benchmark): the lowercase "n" two rows down stacks
    # under a caption, and its row fills columns the group headings hold.
    grid = [
        ["Table 1 month follow-up interval", "Differences in diagnoses, gender and family status within the 12-",
         "", "", ""],
        ["", "", "Participants with no suicide attempt (n = 132)", "", "Participants with a suicide attempt (n = 43)"],
        ["", "n", "%", "n", "%"],
        ["Depression", "40", "30.3", "20", "46.5"],
    ]
    folded, _ = _fold_wrapped_heading([list(row) for row in grid], [])
    assert folded == grid


def test_the_wrapped_cells_of_two_entries_are_not_folded_into_one_row():
    # A review table's row whose long cell wraps two rows down beside the next entry's first line (tables 508eb272 on
    # the benchmark): "nani et al. (2012)" and "Rat (12)" stand in columns the row above holds.
    grid = [
        ["Cheng et al. (2020) [76] Gholipour-Ka-", "Porcine (4)", "Full thickness",
         "scarring and contraction, increased reepithelialization and no infec-"],
        ["", "", "Xe WJ-MSC,", ""],
        ["nani et al. (2012)", "Rat (12)", "", "tion, increased re-epithelialization and"],
        ["", "", "human", ""],
    ]
    folded, _ = _fold_wrapped_heading([list(row) for row in grid], [])
    assert folded == grid


# The heading's second line can open with a bracket instead of a lower-case word. On 23 of the 190 Key Facts Sheets
# (two insurers' templates, read 19 September 2026) the break falls before "(see PDS ...", and "Optional | (see PDS
# and other policy documentation for details of others)*" stood as the table's first body row.

BRACKETED = [
    ["Event/Cover", "Yes/No", "Some examples of conditions, exclusions and limits that apply to events/covers"],
    ["", "Optional", "(see PDS and other relevant policy documentation for details of others.)*"],
]


def test_a_heading_carried_on_by_a_bracket_opened_on_running_words_is_one_row():
    grid, _ = _fold_wrapped_heading([list(row) for row in BRACKETED + BODY], [])
    assert grid[0] == ["Event/Cover", "Yes/No Optional",
                       "Some examples of conditions, exclusions and limits that apply to events/covers "
                       "(see PDS and other relevant policy documentation for details of others.)*"]
    assert grid[1:] == BODY


def test_a_bracketed_count_or_statistic_under_a_long_heading_is_a_body_row():
    for under in ("(n = 45)", "(0.45)", "(see note 3)", "(a) first of the listed items"):
        grid = [
            ["Group", "Patients who completed the full twelve week course of treatment"],
            ["", under],
            ["Control", "(n = 41)"],
            ["Treated", "(n = 44)"],
        ]
        folded, _ = _fold_wrapped_heading([list(row) for row in grid], [])
        assert folded == grid, under
