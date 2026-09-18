"""A transcription cannot hold more print than the region it transcribes.

A model asked to transcribe a picture, or a page, sometimes writes what is not there at length: on
18 September 2026 Infinity-Parser2-Flash turned a scatter plot 196 x 328 points into an 1,800-row
table of numbers, and a graph figure 438 x 270 points into one line repeated 4,095 times, to its
token limit. Nothing about the *words* marks those as wrong - the table is well formed, the line
is plausible - and on a picture there is no text layer to check them against (D021's corroboration
needs one). What marks them is the region: print smaller than about four points cannot be read,
so nothing is set in it, and a region holds at most its area divided by the area of a four-point
character. Both answers claimed more than twice that.

The bound is the definition, not a tuned number. It was measured before it was written
(`bench/probes/region_capacity.py`, and the three readers' whole-page readings): of 164 recorded
readings of picture regions the largest that is a real transcription uses 0.32 of its region's
capacity and the two runaways 2.2; of 843 whole-page readings the densest - tiny-print book scans,
all three readers agreeing - uses 0.66, and none exceeds 1. A count of *lines* was tried first and
is the wrong measure: a reader that writes an HTML table one cell a line exceeds it honestly.

It applies to a transcription - a whole page, or a picture's text. An icon's meaning and a
figure's description are the model's words about a region, not the region's own, and a sentence
about a twelve-point icon is longer than anything that fits inside it.
"""

from __future__ import annotations

import re

MIN_TYPE_PT = 4.0           # print smaller than this is not legible, so none is set
_CHAR_AREA = MIN_TYPE_PT * (MIN_TYPE_PT / 2.0)      # a character is about half as wide as it is tall

_YAML_BLOCK = re.compile(r"\A---\s*\n.*?\n---\s*\n", re.S)
_TAG = re.compile(r"<[^>]+>")
_RULE_LINE = re.compile(r"^[\s|:-]+$", re.M)             # a markdown table's rule: `| --- | :-: |`
_NOT_PRINT = re.compile(r"[|\s]")                        # table bars, and white space


def capacity(width: float, height: float) -> float:
    """The most characters a region of this size, in points, can hold in the smallest legible type."""
    return max(width, 0.0) * max(height, 0.0) / _CHAR_AREA


def printed_characters(text: str) -> int:
    """The characters of a reading that stand for print: markup, table bars and spacing do not."""
    text = _TAG.sub(" ", _YAML_BLOCK.sub("", text or "", count=1))
    return len(_NOT_PRINT.sub("", _RULE_LINE.sub("", text)))


def load(text: str, width: float, height: float) -> float:
    """How much of the region's capacity the reading claims; above 1 it cannot be a transcription."""
    room = capacity(width, height)
    return printed_characters(text) / room if room > 0 else 0.0


def holds_more_than_fits(text: str, width: float, height: float) -> bool:
    return load(text, width, height) > 1.0
