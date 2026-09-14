"""A block the layout model calls a page footer is published when no page beside it repeats it.

The pipeline's own margin rule calls nothing longer than two lines a running foot. The layout model does not ask: on
the Qantas home PDS cover it labelled the issuer, the ABN and the registered office - four lines and 34 words at the
foot of the page - a page footer, and they were published nowhere. A running foot runs: the same words at the same
height, page after page. So a longer block comes out of the feet when the pages beside it have text and none repeats
it; one repeated beside it stays a foot, and so does one with no page beside it to ask. A line or two stays the
running foot it is.
"""

import pymupdf

from truedoc.layout.base import Region, RegionKind
from truedoc.layout.fuse import apply_layout
from truedoc.model import BBox, BlockKind
from truedoc.pipeline import ConvertOptions, process_page

ISSUER = ["This document prepared on 1 March 2024", "Product Issuer: Example Insurance Company Limited",
          "ABN: 00 000 000 000 AFS Licence Number: 000000", "Registered Office: Level 1, 1 Example Street, Brisbane"]
RUNNING = ["Home and Contents Insurance PDS"]


def _document(tmp_path, feet):
    """One page for each foot: the same title on every page, and the foot's lines at the foot."""
    doc = pymupdf.open()
    for foot in feet:
        page = doc.new_page(width=405, height=573)
        page.insert_text((14, 380), "Home and Contents Insurance", fontsize=20)
        page.insert_text((14, 420), "Product Disclosure Statement", fontsize=12)
        for i, text in enumerate(foot):
            page.insert_text((14, 530 + 9.5 * i), text, fontsize=8)
    path = tmp_path / "pds.pdf"
    doc.save(str(path))
    doc.close()
    return str(path)


def _first_page_fused(tmp_path, feet):
    pdf_page = pymupdf.open(_document(tmp_path, feet))[0]
    page = process_page(pdf_page, 1, ConvertOptions(layout=False, ocr=False, math=False, marks=False, tables=False))
    region = Region(kind=RegionKind.PAGE_FOOTER, bbox=BBox(10, 520, 395, 565), score=0.8)
    return apply_layout(page, list(page.blocks), [region], pdf_page=pdf_page, ocr=False)


def _kinds(blocks):
    return [(b.kind, b.provenance, len(b.lines), b.text[:40]) for b in blocks]


def test_an_issuer_block_no_page_beside_repeats_is_not_a_running_foot(tmp_path):
    blocks = _first_page_fused(tmp_path, [ISSUER, RUNNING, RUNNING])
    foot = [b for b in blocks if "Registered Office" in b.text]
    assert foot and all(b.kind != BlockKind.FOOTER for b in foot), _kinds(blocks)


def test_a_long_foot_repeated_on_the_pages_beside_it_stays_a_foot(tmp_path):
    blocks = _first_page_fused(tmp_path, [ISSUER, ISSUER, ISSUER])
    foot = [b for b in blocks if "Registered Office" in b.text]
    assert foot and all(b.kind == BlockKind.FOOTER for b in foot), _kinds(blocks)


def test_a_long_foot_with_no_page_beside_it_to_ask_stays_a_foot(tmp_path):
    # A one-page file: nothing shows whether the block runs, so the layout model's label stands.
    blocks = _first_page_fused(tmp_path, [ISSUER])
    foot = [b for b in blocks if "Registered Office" in b.text]
    assert foot and all(b.kind == BlockKind.FOOTER for b in foot), _kinds(blocks)


def test_a_one_line_running_foot_stays_a_foot(tmp_path):
    blocks = _first_page_fused(tmp_path, [["Home PDS  Page 2 of 40"], RUNNING])
    foot = [b for b in blocks if "Page 2 of 40" in b.text]
    assert foot and all(b.kind == BlockKind.FOOTER for b in foot), _kinds(blocks)
