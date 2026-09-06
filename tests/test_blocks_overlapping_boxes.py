"""Hidden OCR layers report line boxes taller than the line pitch; blocks must still follow the baselines."""

from truedoc.model import BBox, Char, Line, Page, Word
from truedoc.segment.blocks import build_blocks


def _line(text, x0, x1, y0, h=16.3, base_off=12.2, size=8.8):
    chars = [Char(text=ch, bbox=BBox(x0 + i * 4, y0, x0 + (i + 1) * 4, y0 + h), font="OCR", size=size, origin_y=y0 + base_off) for i, ch in enumerate(text)]
    return Line(words=[Word(text=text, bbox=BBox(x0, y0, x1, y0 + h), chars=chars)], bbox=BBox(x0, y0, x1, y0 + h))


def test_short_paragraph_end_keeps_its_place_under_overlapping_boxes():
    # Four lines 10 pt apart with 16 pt boxes (from a scanned patent): the second is a
    # paragraph's short last line, the third starts the next paragraph.
    page = Page(number=1, width=557, height=818)
    page.quality.kind = "ocr"
    lines = [
        _line("or a write operation. (Note that in the case of an array object", 60, 276, 589.2),
        _line("the field is an array element.)", 60, 168, 599.7),
        _line("Next, the System identifies a marking bit associated with", 69, 276, 609.8),
        _line("the field (step 1204). In one embodiment of the present", 60, 276, 619.5),
    ]
    blocks = build_blocks(page, lines)
    order = [l.text[:12] for b in blocks for l in b.lines]
    assert order.index("the field is") < order.index("Next, the Sy")
    holder = [b for b in blocks if any(l.text.startswith("the field is") for l in b.lines)][0]
    assert any(l.text.startswith("or a write") for l in holder.lines), "the short line belongs with the paragraph it ends"


def test_erratic_box_heights_on_an_ocr_layer_stay_one_paragraph():
    # A dictionary page's hidden layer: nominal sizes 5-6 pt, box heights 7-11 pt, pitch 8 pt.
    page = Page(number=1, width=355, height=580)
    page.quality.kind = "ocr"
    spec = [('" Pestels of venison," Warner\'s Antiq. Culin.', 347.6, 8.1, 5.4),
            ("p. 98. Pestell of flesshe, Palsgrave.", 356.6, 6.9, 5.1), ("A pestle-pie is a large standing pie which con-", 361.4, 10.8, 5.0),
            ("tains a whole gammon, and sometimes a couple", 370.8, 8.5, 6.0)]
    lines = [_line(t, 190, 337, y0, h=h, base_off=h - 2.0, size=s) for t, y0, h, s in spec]
    blocks = build_blocks(page, lines)
    assert len(blocks) == 1, [[l.text[:12] for l in b.lines] for b in blocks]


def test_small_copyright_line_stays_out_of_the_footnote_block_on_an_ocr_layer():
    # An AMS journal page's hidden layer: a footnote at 8.9 pt, then the 5.9 pt copyright line.
    page = Page(number=1, width=500, height=684)
    page.quality.kind = "ocr"
    lines = [
        _line("Key words and phrases, von Neumann algebra, factor, trace.", 60, 400, 586.0, h=12.4, base_off=10.0, size=8.9),
        _line("Received by the editors March 3, 1975.", 60, 400, 598.0, h=12.4, base_off=10.0, size=8.9),
        _line("Copyright 1975, American Mathematical Society", 60, 300, 607.6, h=8.0, base_off=6.5, size=5.9),
    ]
    blocks = build_blocks(page, lines)
    assert len(blocks) == 2 and [l.text[:9] for l in blocks[1].lines] == ["Copyright"], [[l.text[:12] for l in b.lines] for b in blocks]


def test_a_line_on_the_same_baseline_does_not_join_the_block():
    page = Page(number=1, width=557, height=818)
    a = _line("left half of a line", 60, 150, 100.0)
    b = _line("right half, same baseline", 160, 276, 100.0)
    blocks = build_blocks(page, [a, b])
    assert len(blocks) == 2
