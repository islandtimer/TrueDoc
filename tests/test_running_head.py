"""A line taken out at the head of a page is published when no page beside it prints it there.

Honey's household PDS sets each peril's name at the top of its page - "Animal damage", "Explosion", "Flood" - and the
layout model labelled each a page header, so no peril's page said which peril it describes. AAMI's definitions pages set
the defined term at the top of the page ("Incident", "Illegal drugs") and a building PDS opens a page on "This guarantee
does not apply:"; the margin clean-up took each for a running head. A running head runs: the same words at the same
height, page after page. So every rule that takes a line out as a running head - the layout model's label and its
margin tie, the zone rule, the clean-up's margin heading, top strip and header stack - takes it only when no page beside
it shows that it stops here. One repeated beside it stays a head, so does one set alternately on facing pages, and so
does one with no page beside it to ask. The height is measured down from the head of each page, so pages of another
height are asked at the same place.
"""

import pymupdf

from tests.test_classify import _block
from truedoc.layout.base import Region, RegionKind
from truedoc.layout.fuse import apply_layout
from truedoc.model import BBox, BlockKind, Page
from truedoc.pipeline import ConvertOptions, _margin_cleanup, process_page

BODY = ["You are covered for loss or damage to your home or your contents caused by this event.",
        "We will pay the reasonable cost to repair or replace the damaged part of your home.",
        "The most we will pay is the sum insured shown on your certificate of insurance."]
OFF = ConvertOptions(layout=False, ocr=False, math=False, marks=False, tables=False)


def _document(tmp_path, heads, heights=None, size=14, baseline=40):
    """One page for each head: the head at the top, the same body lines under it on every page."""
    doc = pymupdf.open()
    for i, head in enumerate(heads):
        page = doc.new_page(width=405, height=(heights[i] if heights else 573))
        page.insert_text((14, baseline), head, fontsize=size)
        for j, text in enumerate(BODY):
            page.insert_text((14, 120 + 14 * j), text, fontsize=10)
    path = tmp_path / "pds.pdf"
    doc.save(str(path))
    doc.close()
    return str(path)


def _fused(tmp_path, heads, index, heights=None):
    pdf_page = pymupdf.open(_document(tmp_path, heads, heights))[index]
    page = process_page(pdf_page, index + 1, OFF)
    region = Region(kind=RegionKind.PAGE_HEADER, bbox=BBox(10, 22, 395, 48), score=0.8)
    return apply_layout(page, list(page.blocks), [region], pdf_page=pdf_page, ocr=False)


def _converted(tmp_path, heads, index, size, baseline=40):
    pdf_page = pymupdf.open(_document(tmp_path, heads, size=size, baseline=baseline))[index]
    return list(process_page(pdf_page, index + 1, OFF).blocks)


def _kinds(blocks):
    return [(b.kind, b.provenance, len(b.lines), b.text[:40]) for b in blocks]


def _named(blocks, text):
    found = [b for b in blocks if text in b.text]
    assert found, _kinds(blocks)
    return found


# The layout model's label.

def test_a_title_at_the_head_that_no_page_beside_repeats_is_not_a_running_head(tmp_path):
    blocks = _fused(tmp_path, ["Animal damage", "Explosion", "Flood"], 1)
    assert all(b.kind != BlockKind.HEADER for b in _named(blocks, "Explosion")), _kinds(blocks)


def test_a_head_repeated_on_the_pages_beside_it_stays_a_head(tmp_path):
    blocks = _fused(tmp_path, ["Household Insurance Policy"] * 3, 1)
    assert all(b.kind == BlockKind.HEADER for b in _named(blocks, "Household Insurance Policy")), _kinds(blocks)


def test_a_head_set_alternately_on_facing_pages_stays_a_head(tmp_path):
    heads = ["Household Insurance Policy", "Your Cover", "Household Insurance Policy", "Your Cover", "Claiming"]
    blocks = _fused(tmp_path, heads, 2)
    assert all(b.kind == BlockKind.HEADER for b in _named(blocks, "Household Insurance Policy")), _kinds(blocks)


def test_a_head_with_no_page_beside_it_to_ask_stays_a_head(tmp_path):
    # A one-page file: nothing shows whether the block runs, so the layout model's label stands.
    blocks = _fused(tmp_path, ["Explosion"], 0)
    assert all(b.kind == BlockKind.HEADER for b in _named(blocks, "Explosion")), _kinds(blocks)


def test_a_head_is_asked_at_its_height_from_the_top_of_each_page(tmp_path):
    # The pages beside are taller: the same head stands at the same distance from their top, not from their foot.
    blocks = _fused(tmp_path, ["Household Insurance Policy"] * 3, 1, heights=[640, 573, 640])
    assert all(b.kind == BlockKind.HEADER for b in _named(blocks, "Household Insurance Policy")), _kinds(blocks)


def test_the_margin_tie_goes_to_the_section_header_when_no_page_beside_prints_it(tmp_path):
    # A heading in the page's top margin that the model rates as a section header and nearly as high as a page header.
    pdf_page = pymupdf.open(_document(tmp_path, ["Your excess", "About your premium", "Claims"], size=13.5,
                                      baseline=78))[1]
    page = process_page(pdf_page, 2, OFF)
    box = BBox(10, 62, 395, 84)
    page.meta["layout_regions"] = [Region(kind=RegionKind.SECTION_HEADER, bbox=box, score=0.8),
                                   Region(kind=RegionKind.PAGE_HEADER, bbox=box, score=0.75)]
    blocks = apply_layout(page, list(page.blocks), [Region(kind=RegionKind.SECTION_HEADER, bbox=box, score=0.8)],
                          pdf_page=pdf_page, ocr=False)
    assert all(b.kind == BlockKind.HEADING for b in _named(blocks, "About your premium")), _kinds(blocks)


# The pipeline's own rules.

def test_a_small_line_at_the_top_that_no_page_beside_prints_there_is_not_a_running_head(tmp_path):
    # Body-sized, so the zone rule and then the clean-up's top strip would each take it.
    heads = ["Your excess", "This guarantee does not apply:", "About your premium"]
    blocks = _converted(tmp_path, heads, 1, size=10)
    assert all(b.kind not in (BlockKind.HEADER, BlockKind.FOOTER) for b in _named(blocks, "does not apply")), \
        _kinds(blocks)


def test_a_small_line_at_the_top_of_every_page_is_still_a_running_head(tmp_path):
    blocks = _converted(tmp_path, ["Household Insurance Policy"] * 3, 1, size=10)
    assert all(b.kind == BlockKind.HEADER for b in _named(blocks, "Household Insurance Policy")), _kinds(blocks)


def test_a_heading_at_the_very_top_that_no_page_beside_repeats_stays_a_heading(tmp_path):
    # Larger than the zone rule takes, within the clean-up's margin heading.
    blocks = _converted(tmp_path, ["Incident", "Illegal drugs", "Insured events"], 1, size=13.5)
    assert all(b.kind == BlockKind.HEADING for b in _named(blocks, "Illegal drugs")), _kinds(blocks)


def test_a_heading_at_the_very_top_of_every_page_is_still_a_running_head(tmp_path):
    blocks = _converted(tmp_path, ["Home Insurance Guide"] * 3, 1, size=13.5)
    assert all(b.kind == BlockKind.HEADER for b in _named(blocks, "Home Insurance Guide")), _kinds(blocks)


def test_a_line_stacked_under_a_running_head_that_no_page_beside_prints_is_not_taken_with_it(tmp_path):
    # The running head repeats on every page; the line under it names the page's own section.
    doc = pymupdf.open()
    for section in ["Animal damage", "Explosion", "Flood"]:
        pdf = doc.new_page(width=405, height=573)
        pdf.insert_text((14, 36), "Household Insurance Policy", fontsize=10)
        pdf.insert_text((14, 56), section, fontsize=10)
    path = tmp_path / "stack.pdf"
    doc.save(str(path))
    doc.close()
    pdf_page = pymupdf.open(str(path))[1]
    page = Page(number=2, width=405, height=573)
    page.body_font_size = 10.0
    head = _block("Household Insurance Policy", 14, 27, size=10.0)
    head.kind = BlockKind.HEADER
    line = _block("Explosion", 14, 47, size=10.0)
    body = _block("You are covered for loss or damage to your home caused by an explosion.", 14, 112, size=10.0)
    blocks = [head, line, body]
    _margin_cleanup(page, blocks, pdf_page)
    assert head.kind == BlockKind.HEADER and line.kind == BlockKind.TEXT, _kinds(blocks)
