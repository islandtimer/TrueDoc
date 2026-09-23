"""A side label is read immediately before the block it heads.

A few words set in a narrow column at the left, the top of the label's first line level with the top of the first line
of the block beside it: a "yes" beside what is covered and a "no" beside what is not, a term beside its definition, a
step's number beside the step. The reading-order cut got it wrong two ways. A label column this narrow is not split off
as a column, so the label was weighed against the wide line beside it by their centres, and a label whose box reached a
fraction of a point lower was read after the first line it governs - which then read as the last line of the group
above, an exclusion as a thing covered. A wider label column was split off and read whole, every label before any of
the text it heads. And the shapes it must leave alone: a paper's section heading level by chance with a line of the
other column, a list set in two columns of short entries, a figure beside a heading, a word a justified line's wide
spaces cut loose, and a row of cells, where a label is read with the next cell and not a later one.
"""
from truedoc.model import BBox, Block, BlockKind, Line, Word
from truedoc.segment import order
from truedoc.segment.order import assign_reading_order

W = 420.0


def _line(x0, y0, x1, y1, text):
    words = text.split()
    step = (x1 - x0) / max(1, len(words))
    return Line(words=[Word(text=w, bbox=BBox(x0 + i * step, y0, x0 + (i + 1) * step, y1)) for i, w in enumerate(words)],
                bbox=BBox(x0, y0, x1, y1))


def _block(*lines, kind=BlockKind.TEXT):
    ls = [_line(*l) for l in lines]
    return Block(kind=kind, bbox=BBox.union_all(l.bbox for l in ls), lines=ls)


def _ordered(blocks, width=W):
    assign_reading_order(blocks, page_width=width, body_size=9.0)
    return sorted(blocks, key=lambda b: b.order)


def _heads(ordered, label, block):
    return ordered.index(label) + 1 == ordered.index(block)


def _cut_alone(blocks):
    """The order the cut gives, before any label is seated: what a shape the rule must leave alone keeps."""
    return order._cut(list(blocks), max(4.0, 0.6 * 9.0), depth=0)


def test_a_label_a_hair_lower_than_its_line_is_read_before_it():
    intro = _block((45, 66, 360, 76.7, "an opening paragraph running the full measure of the page from edge to edge"),
                   (45, 76.8, 273, 87.5, "and on to a second line that stops short"))
    first = _block((45.4, 96.3, 58.7, 107.6, "Alpha"), kind=BlockKind.HEADING)
    first_text = _block((82.7, 96.4, 299.2, 107.1, "the one line this first label heads"))
    second = _block((45.4, 112.0, 58.0, 123.3, "Beta"), kind=BlockKind.HEADING)
    second_text = _block((83.1, 112.1, 191.8, 122.8, "the second label heads these lines:"))
    item_one = _block((99.2, 124.3, 348.6, 135.0, "an item under the second label that runs on to"),
                      (110.6, 135.1, 218.0, 145.8, "a second line of its own"), kind=BlockKind.LIST_ITEM)
    item_two = _block((99.2, 147.3, 347.9, 158.0, "and another item under the second label"), kind=BlockKind.LIST_ITEM)
    third = _block((45.4, 341.1, 68.8, 352.4, "Gamma"), kind=BlockKind.HEADING)
    third_text = _block((84.0, 341.1, 364.9, 351.9, "the third label heads this line and the one below"))
    last = _block((84.0, 356.9, 276.0, 367.7, "the last line of the third group"))
    blocks = [intro, first, second, first_text, second_text, item_one, item_two, third_text, last, third]
    ordered = _ordered(blocks)
    assert _heads(ordered, first, first_text)
    assert _heads(ordered, second, second_text)
    assert _heads(ordered, third, third_text)
    assert ordered.index(first_text) < ordered.index(second) and ordered.index(item_two) < ordered.index(third)
    assert ordered.index(third_text) < ordered.index(last)


def test_a_wider_label_column_is_not_read_whole():
    # The right half of a page of definitions: terms in a column wide enough for the cut to split off.
    width = 612.0
    left = [_block((64, 60 + 40 * i, 460, 71 + 40 * i, "a long line of the left half of the page, running on")) for i in range(8)]
    terms = [_block((490, 171, 567, 182, "Term one")), _block((490, 221, 567, 232, "Term two")),
             _block((490, 305, 540, 316, "Term"))]
    texts = [_block((619, 171, 880, 182, "what the first term means, told in a sentence"),
                    (619, 183, 880, 194, "that runs on to a second line")),
             _block((619, 221, 880, 232, "what the second term means, told in a sentence"),
                    (619, 233, 880, 244, "that runs on to a second line"), (619, 245, 720, 256, "and a third")),
             _block((619, 305, 880, 316, "what the third term means, told in a sentence"),
                    (619, 317, 880, 328, "that runs on to a second line"))]
    ordered = _ordered(left + terms + texts, width=940.0)
    for term, text in zip(terms, texts):
        assert _heads(ordered, term, text)


def test_a_section_heading_in_a_column_of_body_text_stays_put():
    # Two columns of a paper; the left column's heading is level with a line of the right column by chance.
    left_above = _block((50, 100, 290, 111, "a line of the left column's body text, running"),
                        (50, 112, 290, 123, "the full width of the column, and another"))
    heading = _block((50, 140, 110, 151, "Introduction"), kind=BlockKind.HEADING)
    left_below = _block((50, 160, 290, 171, "the section's first paragraph, a full line of text"),
                        (50, 172, 290, 183, "and more of it, down the column"))
    right_top = _block((310, 100, 550, 111, "the right column's text runs from the top"),
                       (310, 112, 550, 123, "of the page, a paragraph that ends here."))
    right = _block((310, 140, 550, 151, "a new paragraph opens level with the heading opposite"),
                   (310, 152, 550, 163, "and runs on down the column"), (310, 164, 550, 175, "to its end"))
    blocks = [right, left_below, heading, left_above, right_top]
    ordered = _ordered(blocks, width=600.0)
    assert ordered == [left_above, heading, left_below, right_top, right] == _cut_alone(blocks)


def test_a_list_in_two_columns_of_short_entries_stays_put():
    left = [_block((70, 100 + 14 * i, 130, 110 + 14 * i, w), kind=BlockKind.LIST_ITEM)
            for i, w in enumerate(["first entry", "second entry", "third entry", "fourth entry", "fifth entry"])]
    right = _block((250, 100, 520, 110, "an entry of the other column, long enough to wrap"),
                   (250, 111, 400, 121, "on to a second line"), kind=BlockKind.LIST_ITEM)
    blocks = left + [right]
    assert _ordered(blocks, width=600.0) == _cut_alone(blocks)


def test_a_figure_beside_a_heading_stays_put():
    number = _block((40, 200, 58, 214, "05"))
    heading = _block((80, 200, 300, 214, "the title of the fifth stage of the process"), kind=BlockKind.HEADING)
    text = _block((80, 220, 380, 231, "what happens in the fifth stage, in a sentence"))
    blocks = [heading, text, number]
    assert _ordered(blocks) == _cut_alone(blocks)


def test_a_word_cut_loose_in_a_justified_line_stays_put():
    above = _block((120, 380, 550, 391, "a line of the paragraph above, set justified to the full measure"))
    left = _block((120, 393, 300, 404, "exist with respect"))
    loose = _block((330, 393, 390, 404, "to loading"))
    right = _block((420, 393, 550, 404, "and unloading and more"))
    below = _block((120, 406, 550, 417, "a line of the paragraph below, set justified to the full measure too"))
    blocks = [above, left, loose, right, below]
    assert _ordered(blocks, width=600.0) == _cut_alone(blocks)
    # Wherever the cut left the fragment, it is not moved to the words after it.
    mixed = [above, left, right, loose, below]
    assert order._seat_side_labels(mixed, 600.0, 9.0) == mixed


def test_a_label_in_a_row_of_cells_is_read_with_the_next_cell():
    author = _block((40, 300, 160, 311, "an author and a year"))
    model = _block((170, 300, 220, 311, "Rodent (40)"))
    between = _block((230, 300, 350, 311, "a wide cell"))
    far = _block((360, 300, 590, 311, "a later cell of the row, long enough to be read as text"))
    blocks = [author, model, between, far]
    assert _ordered(blocks, width=600.0) == _cut_alone(blocks) == [author, model, between, far]
