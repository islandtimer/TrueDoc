"""A hyphen at a line break is dropped only when the two halves make one word.

Run 60 joined "racist-" / "free" as "racistfree" and "third-" / "highest" as "thirdhighest"
(five multi-column and tiny-text checks). The English word list decides: the halves join
without the hyphen when together they are a word ("re-" / "search", and so British spellings
the American list lacks, "re-" / "cognise"); the hyphen stays when each half is a word on its
own ("racist-free", "cluster-level") or when the second half starts with a capital or a digit
("G-CSF"). A hyphen before a function word is a suspended one ("40- to 100-μm") and keeps its
space. Words outside the list ("tal-" / "kommunita", Maltese) still join: the list cannot tell
a compound from a broken word there, and a broken word is the commoner case.
"""
from truedoc.model import BBox, Line, Word
from truedoc.render.okf import join_lines


def _line(text, y0):
    return Line(words=[Word(text=t, bbox=BBox(0, y0, 10, y0 + 10)) for t in text.split(" ")], bbox=BBox(0, y0, 100, y0 + 10))


def _join(a, b):
    return join_lines([_line(a, 0), _line(b, 12)])


def test_halves_that_make_one_word_join_without_the_hyphen():
    assert _join("further re-", "search into the") == "further research into the"
    assert _join("comprise a single objec-", "t.") == "comprise a single object."
    assert _join("the guide-", "lines in February") == "the guidelines in February"
    assert _join("we re-", "cognise the") == "we recognise the"


def test_two_words_keep_their_hyphen():
    assert _join("to ensure racist-", "free campuses") == "to ensure racist-free campuses"
    assert _join("the third-", "highest total") == "the third-highest total"
    assert _join("each cluster-", "level node") == "each cluster-level node"
    assert _join("a well-", "known result") == "a well-known result"


def test_a_prefix_joins_its_word_unless_two_vowels_meet():
    assert _join("patients on pre-", "dialysis care") == "patients on predialysis care"
    assert _join("a non-", "linear model") == "a nonlinear model"
    assert _join("an anti-", "inflammatory drug") == "an anti-inflammatory drug"


def test_capitals_and_digits_keep_the_hyphen():
    assert _join("du récepteur du G-", "CSF (granulocyte") == "du récepteur du G-CSF (granulocyte"
    assert _join("results for 2019-", "2020 were") == "results for 2019-2020 were"


def test_a_suspended_hyphen_keeps_its_space():
    assert _join("beryllium crystals 40-", "to 100-μm thick") == "beryllium crystals 40- to 100-μm thick"
    assert _join("both pre-", "and post-operative care") == "both pre- and post-operative care"
