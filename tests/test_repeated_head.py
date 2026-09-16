"""A line filed as furniture for repeating a running head's words must run where it stands.

The margin clean-up files a short line as furniture wherever it sits when its words repeat a running head's, so that a
form's label at the foot of its box goes with the head it repeats. But a contents PDS heads a grey box "We do not
cover" over three excluded items, and a home PDS marks a section "Optional cover" beside "Commercial Storage", in the
words their pages run at the head - and no page beside prints those words where the box stands. 66bdf98 asked the
pages beside a line whether a head runs; this asks the same question at the height the line stands.

Nothing else at a page's foot is asked, and each of those was measured first: the layout model's page-footer label
keeps its length test (a one-line foot no page beside prints is as often the document's code or folio as an issuer
line - 127 of the 190 Key Facts Sheets published one when the test was taken away), the zone rule's bottom branch
published a preparation-date stamp the insurance set wants absent, the contact rule gave back five date stamps against
four issuer blocks and a sentence, the margin heading's foot branch gave three brand straplines and a "Continued next
page..." against two product names, and the two bottom strips gave back nothing in 1,237 pages.
"""

import pymupdf

from tests.test_classify import _block
from truedoc.layout.base import Region, RegionKind
from truedoc.layout.fuse import apply_layout
from truedoc.model import BBox, BlockKind, Page
from truedoc.pipeline import ConvertOptions, _margin_cleanup, process_page

BODY = ["This policy covers the events set out in the table on the pages that follow.",
        "Read it with the product disclosure statement and keep both with your policy papers."]
OFF = ConvertOptions(layout=False, ocr=False, math=False, marks=False, tables=False)
ISSUER = "AAI Limited ABN 48 005 297 807 AFSL 230859 trading as AAMI"
CONTACT = "2649 Logan Road Eight Mile Plains Qld 4113 13 1905 racq.com"


def _pages(tmp_path, running_head, middle_line=None):
    """Three pages carrying the same running head, the middle one repeating its words in the body as well."""
    doc = pymupdf.open()
    for number in range(3):
        page = doc.new_page(width=405, height=573)
        page.insert_text((14, 36), running_head, fontsize=9)
        if middle_line and (number == 1 or middle_line == "every"):
            page.insert_text((14, 300), running_head, fontsize=9)
        for j, text in enumerate(BODY):
            page.insert_text((14, 380 + 14 * j), text, fontsize=9)
    path = tmp_path / "pds.pdf"
    doc.save(str(path))
    doc.close()
    return str(path)


def _cleaned(tmp_path, middle_line):
    """The margin clean-up over a head block and a box heading of the same words, with the file for the pages beside."""
    pdf_page = pymupdf.open(_pages(tmp_path, "We do not cover", middle_line))[1]
    page = Page(number=2, width=405, height=573)
    page.body_font_size = 9.0
    head = _block("We do not cover", 14, 27, size=9.0)
    head.kind = BlockKind.HEADER
    box = _block("We do not cover", 14, 291, size=9.0)
    body = _block("additional features on pages 26 to 35, and any incident not covered by your policy.", 14, 320, size=9.0)
    blocks = [head, box, body]
    _margin_cleanup(page, blocks, pdf_page)
    return head, box, blocks


def _document(tmp_path, feet, size=9, heads=None):
    doc = pymupdf.open()
    for i, foot in enumerate(feet):
        page = doc.new_page(width=405, height=573)
        if heads:
            page.insert_text((14, 40), heads[i], fontsize=size)
        for j, text in enumerate(BODY):
            page.insert_text((14, 120 + 14 * j), text, fontsize=10)
        page.insert_text((14, 545), foot, fontsize=size)
    path = tmp_path / "spds.pdf"
    doc.save(str(path))
    doc.close()
    return str(path)


def _converted(tmp_path, feet, index, size=9, heads=None):
    pdf_page = pymupdf.open(_document(tmp_path, feet, size, heads))[index]
    return list(process_page(pdf_page, index + 1, OFF).blocks)


def _fused(tmp_path, feet, index, size=9):
    pdf_page = pymupdf.open(_document(tmp_path, feet, size))[index]
    page = process_page(pdf_page, index + 1, OFF)
    region = Region(kind=RegionKind.PAGE_FOOTER, bbox=BBox(10, 528, 395, 560), score=0.8)
    return apply_layout(page, list(page.blocks), [region], pdf_page=pdf_page, ocr=False)


def _kinds(blocks):
    return [(b.kind, b.provenance, len(b.lines), b.text[:40]) for b in blocks]


def _named(blocks, text):
    found = [b for b in blocks if text in b.text]
    assert found, _kinds(blocks)
    return found


def test_a_line_repeating_a_running_head_away_from_the_margins_is_not_furniture(tmp_path):
    head, box, blocks = _cleaned(tmp_path, middle_line="one page")
    assert head.kind == BlockKind.HEADER and box.kind == BlockKind.TEXT, _kinds(blocks)


def test_a_line_the_pages_beside_print_at_that_height_is_still_furniture(tmp_path):
    head, box, blocks = _cleaned(tmp_path, middle_line="every")
    assert box.kind in (BlockKind.HEADER, BlockKind.FOOTER), _kinds(blocks)


def test_a_line_with_no_page_beside_it_to_ask_is_still_furniture(tmp_path):
    doc = pymupdf.open()
    page = doc.new_page(width=405, height=573)
    page.insert_text((14, 36), "We do not cover", fontsize=9)
    page.insert_text((14, 300), "We do not cover", fontsize=9)
    path = tmp_path / "one.pdf"
    doc.save(str(path))
    doc.close()
    pdf_page = pymupdf.open(str(path))[0]
    page_model = Page(number=1, width=405, height=573)
    page_model.body_font_size = 9.0
    head = _block("We do not cover", 14, 27, size=9.0)
    head.kind = BlockKind.HEADER
    box = _block("We do not cover", 14, 291, size=9.0)
    blocks = [head, box]
    _margin_cleanup(page_model, blocks, pdf_page)
    assert box.kind in (BlockKind.HEADER, BlockKind.FOOTER), _kinds(blocks)


# The feet this rule leaves alone, each measured before it was left.

def test_a_one_line_issuer_the_model_calls_a_page_footer_stays_a_foot(tmp_path):
    feet = [ISSUER, "Prepared on 1 September 2024. Page 2 of 4", "Prepared on 1 September 2024. Page 3 of 4"]
    blocks = _fused(tmp_path, feet, 0)
    assert all(b.kind == BlockKind.FOOTER for b in _named(blocks, "AAI Limited")), _kinds(blocks)


def test_a_cover_block_of_contact_details_stays_furniture(tmp_path):
    # Asked, this gave back four issuer blocks and a sentence against five "Effective Date" stamps.
    feet = ["Page 1 of 4", "Page 2 of 4", "Page 3 of 4"]
    blocks = _converted(tmp_path, feet, 0, heads=[CONTACT, "Household Insurance", "Household Insurance"])
    assert all(b.kind == BlockKind.HEADER for b in _named(blocks, "racq.com")), _kinds(blocks)
