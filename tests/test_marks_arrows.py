"""An arrow head is a mark that carries meaning, like a tick and a cross.

The AAMI home building PDS chains three statements down a page with arrows in filled circles:
"If you have a sum insured shown on your certificate of insurance", then an arrow, then "The most
we will pay ... is the sum insured shown", then an arrow, then the exception. The arrow supplies
the word "then": without it the first line is a condition with no consequence and the paragraphs
read as unrelated statements. It came out as an empty figure placeholder.

The reading machinery already handled it - the knockout pass pulls a clean chevron out of the
disc - and only the vocabulary was short: the templates knew tick, cross, dot, circle, square and
box, so the chevron matched nothing and the disc underneath was reported as a dot. An arrow is a
universal symbol like a tick, so this is a vocabulary entry rather than a rule about one document.
"""

import pymupdf

from truedoc.pipeline import ConvertOptions, load_document
from truedoc.render.okf import render_block
from truedoc import marks
from truedoc.model import BBox, Block, BlockKind


def _chain_page(tmp_path):
    """The AAMI shape: a white chevron painted over a filled grey disc, between two paragraphs."""
    doc = pymupdf.open()
    page = doc.new_page(width=420, height=300)
    page.insert_text((40, 60), "If you have a sum insured shown on your certificate.", fontsize=9)
    cx, cy, r = 210.0, 90.0, 8.2
    page.draw_circle((cx, cy), r, color=(0.5, 0.5, 0.5), fill=(0.5, 0.5, 0.5))
    page.draw_polyline([(cx - 5.9, cy - 3.0), (cx, cy + 3.4), (cx + 5.9, cy - 3.0)],
                       color=(1, 1, 1), width=2.2)
    page.insert_text((40, 130), "The most we will pay is that sum insured.", fontsize=9)
    path = tmp_path / "chain.pdf"
    doc.save(str(path))
    doc.close()
    return str(path)


def test_a_chevron_knocked_out_of_a_disc_reads_as_an_arrow(tmp_path):
    path = _chain_page(tmp_path)
    doc = pymupdf.open(path)
    mark = marks.classify_mark(doc[0], BBox(201.8, 81.8, 218.2, 98.2), None)
    doc.close()
    assert mark is not None, "no mark found at all"
    assert mark.kind == "arrow-down", "a chevron in a disc is an arrow, not a %s" % mark.kind
    assert mark.text == "↓", mark.text


def test_the_arrow_is_read_and_recorded_on_the_page(tmp_path):
    """End to end as far as the page: found, classified, and kept in the page's own record."""
    doc = load_document(_chain_page(tmp_path), ConvertOptions(frontmatter=False, layout=False, ocr=False))
    found = doc.pages[0].meta.get("marks") or []
    assert [m["kind"] for m in found] == ["arrow-down"], found


def test_a_picture_that_is_only_a_mark_renders_as_that_mark():
    """The placement half: an arrow between two paragraphs lands inside a picture region, and a
    picture whose whole content is one readable mark renders as the mark rather than as an
    anonymous placeholder. On the real page this is the difference between "then" and nothing."""
    block = Block(kind=BlockKind.FIGURE, bbox=BBox(195.0, 75.0, 225.0, 105.0))
    assert render_block(block) == "![](figure)"
    block.meta["mark_only"] = "↓"
    assert render_block(block) == "↓"


def test_a_cross_is_still_a_cross_not_an_arrow(tmp_path):
    """The guard that matters: an X reaches all four corners, a chevron only two."""
    doc = pymupdf.open()
    page = doc.new_page(width=200, height=120)
    page.draw_line((40, 40), (56, 56), color=(0.85, 0.2, 0.2), width=1.8)
    page.draw_line((40, 56), (56, 40), color=(0.85, 0.2, 0.2), width=1.8)
    path = tmp_path / "cross.pdf"
    doc.save(str(path))
    doc.close()
    d = pymupdf.open(str(path))
    mark = marks.classify_mark(d[0], BBox(39, 39, 57, 57), None)
    d.close()
    assert mark is not None and mark.kind == "cross", mark.kind if mark else None
