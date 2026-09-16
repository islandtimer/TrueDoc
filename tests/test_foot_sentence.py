"""A sentence standing alone at the foot of a page is the page's own; a stamp there is furniture.

A supplementary PDS says all it has to say at the foot of its cover - "The insured event "Flood and/or run-off" under
the heading What you're covered for is deleted." - and the zone rule filed it as a running foot with the folio joined
to it. Asking the pages beside was not enough: GIO's "PDS preparation date 25/11/2020" stands as alone at its foot,
and the insurance set wants it gone. Over the whole one-in-fifty sample of the library the 194 feet no page beside
repeats hold three sentences and 191 stamps, codes, folios, dates and issuer lines; a line of at least eight words
with hardly a digit among them picks out the three. Both halves are needed: among the feet the pages beside do print,
that test fires on fifteen running feet.
"""

import pymupdf

from truedoc.model import BlockKind
from truedoc.pipeline import ConvertOptions, process_page

BODY = ["The following changes are made to the PDS:",
        "This supplementary product disclosure statement changes the policy documents it names.",
        "Read it with the product disclosure statement and keep both with your policy papers."]
OFF = ConvertOptions(layout=False, ocr=False, math=False, marks=False, tables=False)
DELETED = "The insured event Flood and or run-off under the heading What you are covered for is deleted."
STAMP = "PDS preparation date 25/11/2020"
RUNNING = "Insurance products issued by RACQ Insurance Limited and conditions may apply to them"


def _document(tmp_path, feet, size=9):
    """One page for each foot: the same body lines on every page, each page's own line at its foot."""
    doc = pymupdf.open()
    for foot in feet:
        page = doc.new_page(width=405, height=573)
        for j, text in enumerate(BODY):
            page.insert_text((14, 120 + 14 * j), text, fontsize=10)
        page.insert_text((14, 545), foot, fontsize=size)
    path = tmp_path / "spds.pdf"
    doc.save(str(path))
    doc.close()
    return str(path)


def _converted(tmp_path, feet, index, size=9):
    pdf_page = pymupdf.open(_document(tmp_path, feet, size))[index]
    return list(process_page(pdf_page, index + 1, OFF).blocks)


def _kinds(blocks):
    return [(b.kind, b.provenance, len(b.lines), b.text[:40]) for b in blocks]


def _named(blocks, text):
    found = [b for b in blocks if text in b.text]
    assert found, _kinds(blocks)
    return found


def test_a_sentence_at_the_foot_that_no_page_beside_prints_is_published(tmp_path):
    feet = ["The cover for accidental damage is added to every section of this policy.", DELETED,
            "The excess for storm damage is halved for every renewal of this policy."]
    blocks = _converted(tmp_path, feet, 1)
    assert all(b.kind not in (BlockKind.FOOTER, BlockKind.FOOTNOTE) for b in _named(blocks, "is deleted")), _kinds(blocks)


def test_a_sentence_the_pages_beside_print_at_their_feet_stays_a_foot(tmp_path):
    blocks = _converted(tmp_path, [RUNNING] * 3, 1)
    assert all(b.kind in (BlockKind.FOOTER, BlockKind.FOOTNOTE) for b in _named(blocks, "RACQ Insurance")), _kinds(blocks)


def test_a_stamp_alone_at_the_foot_stays_a_foot(tmp_path):
    # As alone as the sentence, and the insurance set wants it absent: what differs is what it is.
    feet = [STAMP, "Prepared on 1 September 2024. Page 2 of 4", "Prepared on 1 September 2024. Page 3 of 4"]
    blocks = _converted(tmp_path, feet, 0)
    assert all(b.kind in (BlockKind.FOOTER, BlockKind.FOOTNOTE) for b in _named(blocks, "preparation date")), _kinds(blocks)


def test_a_short_line_alone_at_the_foot_stays_a_foot(tmp_path):
    feet = ["Continued on next page.", "Page 2 of 4", "Page 3 of 4"]
    blocks = _converted(tmp_path, feet, 0)
    assert all(b.kind in (BlockKind.FOOTER, BlockKind.FOOTNOTE) for b in _named(blocks, "Continued")), _kinds(blocks)


def test_a_sentence_with_no_page_beside_it_to_ask_stays_a_foot(tmp_path):
    # A one-page file: nothing shows whether the line runs, so the zone decides, as before.
    blocks = _converted(tmp_path, [DELETED], 0)
    assert all(b.kind in (BlockKind.FOOTER, BlockKind.FOOTNOTE) for b in _named(blocks, "is deleted")), _kinds(blocks)
