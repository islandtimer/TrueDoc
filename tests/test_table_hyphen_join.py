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
