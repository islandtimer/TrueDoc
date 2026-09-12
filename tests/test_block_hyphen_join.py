"""A word the column break cuts in two is closed up, list item or paragraph.

A journal's reference list is a column of numbered entries, and an entry that runs over the
column break leaves its last word split: "Pancreatic car-" at the foot of one column and
"cinogenesis. Pancreatology 2008" at the head of the next. The joining rule was already here,
with this very case in its comment, but it asked both blocks to be plain text - and a
reference list is list items, so it never fired. 29 words are cut that way across the
benchmark, 27 of them on pages we read ourselves; the reader sees "car- cinogenesis".

Two list items that are not a broken word stay two list items: only a previous half ending
in a hyphen with a lowercase half after it is joined.
"""
from truedoc.model import BBox, Block, BlockKind, Document, Line, Page, Word
from truedoc.render.okf import RenderOptions, render_document


def _line(text: str, y: float) -> Line:
    x = 0.0
    words = []
    for tok in text.split():
        words.append(Word(text=tok, bbox=BBox(x, y, x + 5 * len(tok), y + 10)))
        x += 5 * len(tok) + 5
    return Line(words=words, bbox=BBox(0, y, max(x, 10.0), y + 10))


def _doc(first: str, second: str, kind: BlockKind = BlockKind.LIST_ITEM) -> str:
    page = Page(number=1, width=400, height=800)
    # the foot of the left column, then the head of the right one
    a = Block(kind=kind, bbox=BBox(0, 700, 180, 720), lines=[_line(first, 700)])
    b = Block(kind=kind, bbox=BBox(200, 100, 380, 120), lines=[_line(second, 100)])
    a.order, b.order = 0, 1
    page.blocks = [a, b]
    return render_document(Document(path="x.pdf", pages=[page]), RenderOptions(frontmatter=False))


def test_a_reference_split_across_the_column_break_is_closed_up():
    body = _doc("23. Koorstra JB, Maitra A. Pancreatic car-", "cinogenesis. Pancreatology 2008; 8: 110-25.")
    assert "carcinogenesis" in body
    assert "car- cinogenesis" not in body and "car-\n\ncinogenesis" not in body


def test_the_same_repair_still_works_for_plain_paragraphs():
    body = _doc("the study found a positive and nega-", "tive effect on tumorigenesis.", BlockKind.TEXT)
    assert "negative effect" in body


def test_two_ordinary_list_items_are_not_joined():
    body = _doc("23. Koorstra JB, Maitra A. Pancreatic carcinogenesis.", "24. Massague J. G1 cell-cycle control.")
    assert "carcinogenesis. 24." not in body
