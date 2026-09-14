"""Cell text and cell geometry shared by the ruled and aligned table builders and the layout path."""

import re

# Leader dots ("Bowbells.........." or ". . . . .") lead the eye from a label
# to its value across a column gap, and a printed rule of dashes does the same
# or underlines a heading ("---------------- Percent"). Neither is part of the
# cell's meaning. Three dots alone are an ellipsis and stay; underscores are
# the blanks of a form and stay too.
_LEADING_DOTS = re.compile(r"^(?:\.\s?){4,}\s*")
_TRAILING_DOTS = re.compile(r"\s*(?:\.\s?){4,}$")
_LEADING_RULE = re.compile(r"^(?:[-–—]\s?){4,}\s*")
_TRAILING_RULE = re.compile(r"\s*(?:[-–—]\s?){4,}$")
_MEANING = re.compile(r"[^\W_]")
# A statistic in brackets under a value: "(4.07)", "(-1.07)", "(.22)", "(0.0796)",
# "(7)", "(42.9%)", "[0.12]"; not "(n = 12)", "(a)" or "(2)".
_BRACKETED_STATISTIC = re.compile(r"^[\(\[]\s*[-+−–]?[\d,]*\.?\d+%?\s*[\)\]][*†‡]*$")


def is_bracketed_statistic(text: str) -> bool:
    """Is the cell a bracketed number, the shape of a standard error or t-value
    printed under its estimate?"""
    return bool(_BRACKETED_STATISTIC.match(text.strip()))


def clean_cell_text(text: str) -> str:
    """Strip leader dots and dash rules from the ends of a cell's text."""
    t = text.strip()
    if not t:
        return t
    core = _LEADING_RULE.sub("", _LEADING_DOTS.sub("", t))
    core = _TRAILING_RULE.sub("", _TRAILING_DOTS.sub("", core)).strip()
    # A cell that is only dots or dashes marks a blank; leave it as it was.
    if not core or not _MEANING.search(core):
        return t
    return core


def runs_across_columns(placed, size: float) -> bool:
    """Does a line of text cross from one column into the next on an ordinary word space?

    `placed` pairs every word of the line with the column it falls in, in any order. A row of cells moves
    from one column to the next across the gap between its cells; a sentence or a phrase moves across a
    word space. Judged on the geometry alone: under 0.6 of the body size is a word space.

    Two questions rest on it, each asked where an accident had let text through:
    - whether a line just above a table's box is the header row the box missed or a sentence spanning it
      (`layout.fuse._header_lines_above`): "Any amounts you claim include GST less any input tax
      credit..." crossed three columns of a Key Facts Sheet on word spaces of 2.8pt against a 10pt body;
    - whether a cut proposed by the cut-finder's second look does any work but split phrases
      (`tables.aligned._refine_segments`): on the benchmark the one segment each such cut divided ran
      across it on 0.23 to 0.51 of the body size ("Groups at | Risk", "quimicos | e"). A label set tight
      against its answer crosses on as little ("Accidental Breakage | Yes", 0.46), which is why the
      question is asked of everything a cut divides, never of one row alone.
    """
    ordered = sorted(placed, key=lambda p: p[0].bbox.x0)
    return any(ca != cb and b.bbox.x0 - a.bbox.x1 < 0.6 * size
               for (a, ca), (b, cb) in zip(ordered, ordered[1:]))
