"""A row of the body is not part of the heading because the heading's end was hard to see.

`_header_row_count` ends a heading at the first row that is two-fifths numbers, or at the first
long cell, or - when neither comes soon - after three rows. A body row with one number in it passes
under all three, and six benchmark tables had their first body rows written as heading (sized on
19 September 2026, `bench/probes/header_long_cell_census.py`; the grids below are theirs, cut short).
A row after the first that has a label and the shape of a labelled row further down - the same cells
filled, the same cells opening with a number, one at least beyond the label - is a row of the body.
"""

from truedoc.tables.aligned import _header_row_count

PARAMETERS = [
    ["Parameter", "Sign", "Initial amount", "Unit"],
    ["Depth", "H", "63", "μm"],
    ["Width of expansion", "WE", "50", "μm"],
    ["Width of contraction region", "WC", "350", "μm"],
    ["Length of the contraction region", "LC", "1200", "μm"],
    ["Length of the expansion region", "LE", "700", "μm"],
    ["Number of contraction region", "NC", "6", "-"],
    ["Degree between two inlet valves", "θ", "100", "deg"],
    ["Particle-fluid flowrate", "QP", "0.3", "ml/hr"],
]

COURSES = [
    ["Code", "Title", "Credits"],
    ["Foundation Courses", "", ""],
    ["ENGL 314", "Structure of English", "3"],
    ["ENGL 415", "Introduction to TESOL Methods", "3"],
    ["Second Language Acquisition and Pedagogy", "", ""],
    ["ENGL 318", "Second Language Acquisition", "3"],
    ["ENGL 515", "Techniques and Materials for TESOL", "3"],
    ["", "Students must take 3 credits of the following electives", "3"],
    ["ENGL 613", "TESOL: Pedagogical Grammar I", ""],
]

CASES = [
    ["Sexe", "Âge", "Côté", "Présentation Clinique", "Traitement", ""],
    ["Cas 1 Femme", "61", "Droit", "ischémie", "clopidrogrel", "angioplastie"],
    ["", "", "", "chronique", "+ aspirine, puis relais à 3 mois par AVK", "+ stent"],
    ["Cas 2 Homme", "63", "Droit", "ischémie", "HNF", "embolectomie"],
    ["", "", "", "aiguë", "+ aspirine", "Fogarty"],
]


def test_a_first_body_row_with_one_number_in_it_is_not_heading():
    assert _header_row_count(PARAMETERS) == 1


def test_nor_is_the_group_label_standing_alone_above_it():
    assert _header_row_count(COURSES) == 1


def test_nor_a_body_row_whose_second_line_holds_the_table_s_first_long_cell():
    assert _header_row_count(CASES) == 1


def test_a_second_heading_row_that_no_body_row_resembles_stays_heading():
    stacked = [
        ["Group", "Treatment", "Control", "All"],
        ["Measure", "mean (SD)", "mean (SD)", "mean (SD)"],
        ["Age", "34.1 (5.2)", "36.0 (6.1)", "35.0 (5.7)"],
        ["Weight", "71.3 (9.9)", "70.2 (8.7)", "70.8 (9.3)"],
    ]
    assert _header_row_count(stacked) == 2


def test_a_labelled_second_heading_row_with_a_number_in_it_stays_heading_when_no_body_row_has_its_shape():
    dosed = [
        ["Arm", "Dose", "Schedule", "Patients"],
        ["Unit", "10 mg steps", "weekly", ""],
        ["Arm A", "20", "weekly", "41"],
        ["Arm B", "40", "fortnightly", "39"],
        ["Arm C, the comparison arm of the trial as first registered", "0", "weekly", "40"],
    ]
    assert _header_row_count(dosed) == 2
