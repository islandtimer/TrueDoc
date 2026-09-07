"""Cell text clean-up shared by the ruled and the aligned table builders."""

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
