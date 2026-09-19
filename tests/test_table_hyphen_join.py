"""Wrapped cell lines and stacked headings join at a hyphen without a space."""

from truedoc.tables.aligned import _join_lines, _merge_header_rows


def test_hyphen_joins():
    assert _join_lines("Automotive-", "Industrial") == "Automotive-Industrial"
    assert _join_lines("NON-", "RECURRING") == "NON-RECURRING"
    assert _join_lines("Diver-", "sity") == "Diversity"          # a word broken by the typesetter
    assert _join_lines("self-", "employed") == "self-employed"   # two common words: a compound
    assert _join_lines("Year Ended", "March 31, 2016") == "Year Ended March 31, 2016"
    assert _join_lines("Day 0 and 35 -", "Day 42") == "Day 0 and 35 - Day 42"   # a dash after a space is a dash
    assert _join_lines("", "Rate") == "Rate" and _join_lines("Rate", "") == "Rate"


def test_stacked_headings_join_at_the_hyphen():
    grid = [["", "NON-", "Diver-"], ["", "RECURRING", "sity"], ["A", "20.0", "1.2"], ["B", "30.0", "2.3"]]
    merged = _merge_header_rows(grid)
    assert merged[0] == ["", "NON-RECURRING", "Diversity"]
    assert merged[1:] == grid[2:]


def test_a_cell_s_line_break_is_repaired_as_a_paragraph_s_is():
    # "rent-" / "ed out": each half is in a word list, which the older test here took for a compound.
    from truedoc.tables.aligned import _join_lines

    assert _join_lines("if your home is being rent-", "ed out under the extra benefit") == "if your home is being rented out under the extra benefit"
    assert _join_lines("self-", "employed persons") == "self-employed persons"
    assert _join_lines("40-", "to 100 mm") == "40- to 100 mm"


def test_a_word_a_narrow_column_broke_with_no_hyphen_is_made_whole():
    # Huddle's Key Facts Sheet sets "Optiona" and, on a line of its own, "l" (read 19 September 2026).
    from truedoc.tables.aligned import _join_lines

    assert _join_lines("Yes/ No Optiona", "l") == "Yes/ No Optional"
    assert _join_lines("Plan", "a first visit") == "Plan a first visit"          # "plan" is a word, and so is "a"
    assert _join_lines("the insured", "address") == "the insured address"         # both fragments are words
    assert _join_lines("NSW", "only") == "NSW only"                                # capitals are not a broken word


def test_halves_that_make_a_word_are_the_word_even_when_the_second_is_a_function_word():
    from truedoc.tables.aligned import _join_lines

    assert _join_lines("in the spir-", "it of the agreement") == "in the spirit of the agreement"
    assert _join_lines("how-", "ever, the cover") == "however, the cover"
    assert _join_lines("both intra-", "and inter-layer") == "both intra- and inter-layer"        # a suspended hyphen
    assert _join_lines("a dual-", "unitary circuit") == "a dual-unitary circuit"                  # a compound the list lacks
