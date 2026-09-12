"""A row is not a heading just because the row below it is wordier.

The aligned table builder ends the heading at the first row holding a cell of more than
six words. On a fee table whose third course is named in seven words and whose first two
are named in five, that read the first two courses as heading lines and merged them into
one row: two courses and their fees became a single cell each, and three checks on
tables/937a90b2 page 7 failed with the rows they name missing (runs 83 to 87).

A row above the long cell that has the same shape - the same cells filled, the same cells
opening with a number, and a label in the first column - is another body row. A genuine
stacked heading, whose lines do not look like the body, is untouched.
"""
from truedoc.tables.aligned import _header_row_count

FEES = [
    ["Doctor of Dental Science (Orthodontics)", "3,854 (14,099 for overseas students)"],
    ["Doctor of Dental Science (Endodontics)", "13,556 (20,940 for overseas students)"],
    ["Doctor of Dental Science (Special Care Dentistry)", "3,244 (14,099 for overseas students)"],
    ["MRes Biomedical Sciences and Translational Medicine", "3,000"],
    ["MRes Clinical Science", "3,000"],
    ["Dip Bovine Reproduction", "1,195"],
]


def test_rows_shaped_like_the_body_are_not_a_heading():
    # Before: 2, which merged the Orthodontics and Endodontics rows into one.
    assert _header_row_count(FEES) == 1


def test_a_wrapped_column_heading_is_still_a_heading():
    # The heading wraps over two lines and neither line looks like the body: the second
    # line has no label in the first column, and no cell opens with a number.
    grid = [
        ["Region", "Gross domestic", "Population"],
        ["", "product (US$m)", "(thousands)"],
        ["Northern Territory of Australia", "1,234", "245"],
        ["Queensland", "5,678", "5,100"],
    ]
    assert _header_row_count(grid) == 2


def test_a_word_heading_over_numeric_rows_stays_one_row():
    grid = [
        ["Topic", "Number of questions*"],
        ["Glomerulonephritis, tubulointerstitial nephritis (incl. vasculitis)", "30"],
        ["Acute kidney injury and renal replacement therapy in the unit", "26"],
    ]
    assert _header_row_count(grid) == 1


def test_a_year_heading_over_labelled_rows_keeps_its_one_row():
    # The heading and the body have the same shape here - a label, then numbers - so the
    # walk-back runs all the way to the top and stops there: a table always keeps one
    # heading row, which is what markdown can write and what the checker reads as row 0.
    grid = [
        ["Region", "2011", "2012"],
        ["North", "1,234", "2,345"],
        ["The southern districts and their outlying islands", "5,678", "6,789"],
    ]
    assert _header_row_count(grid) == 1


def test_the_rule_needs_a_number_to_go_on():
    # Three rows of plain words: nothing opens with a number, so the long-cell reading
    # stands and the first two rows are still read as the heading.
    grid = [
        ["Course", "Award"],
        ["Full time", "Certificate"],
        ["Doctor of Dental Science in Special Care Dentistry", "Doctorate"],
    ]
    assert _header_row_count(grid) == 2
