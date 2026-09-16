"""What sits at a page's edge that no page beside prints there is kept as the document's imprint (D029).

A running head or foot runs. At the edge of a first page nothing runs, so what stands there is the document's own
imprint - a copyright line, an issuing body, an insurance cover's issuer, ABN and licence. It stays out of the body,
exactly as before, and is recorded in the front matter with its page, so nothing the document says is thrown away.
These tests pin both halves: that it is recorded, and that the body does not move.
"""

import pymupdf

from truedoc.model import BlockKind
from truedoc.pipeline import ConvertOptions, _record_imprint, convert, load_document, process_page

BODY = ["Home Building Insurance",
        "Product Disclosure Statement and Policy Booklet",
        "Please read this booklet and keep it with your policy papers."]
OFF = ConvertOptions(layout=False, ocr=False, math=False, marks=False, tables=False)
BODYLESS = ConvertOptions(layout=False, ocr=False, math=False, marks=False, tables=False, frontmatter=False)
ISSUER = "AAI Limited ABN 48 005 297 807 AFSL 230859 trading as AAMI"
RUNNING = "Home Insurance Product Disclosure Statement and Policy Booklet"


def _document(tmp_path, feet, size=9):
    """One page for each foot: the same body lines on every page, each page's own line at its foot."""
    doc = pymupdf.open()
    for foot in feet:
        page = doc.new_page(width=405, height=573)
        for j, text in enumerate(BODY):
            page.insert_text((14, 120 + 14 * j), text, fontsize=10)
        page.insert_text((14, 545), foot, fontsize=size)
    path = tmp_path / "pds.pdf"
    doc.save(str(path))
    doc.close()
    return str(path)


def _imprint(tmp_path, feet):
    doc = load_document(_document(tmp_path, feet), OFF)
    return [e["text"] for e in (doc.metadata.get("imprint") or [])]


def test_a_cover_imprint_no_page_beside_prints_is_kept(tmp_path):
    assert ISSUER in _imprint(tmp_path, [ISSUER, "Page 2 of 3", "Page 3 of 3"])


def test_the_imprint_stays_out_of_the_body(tmp_path):
    # The point of keeping it in the front matter: the body is what it was, so no absent check can move.
    body = convert(_document(tmp_path, [ISSUER, "Page 2 of 3", "Page 3 of 3"]), BODYLESS)
    assert "AFSL 230859" not in body, body[:400]


def test_a_running_foot_is_not_imprint(tmp_path):
    # It runs, so it is furniture of the artifact, not a line the document prints once.
    assert _imprint(tmp_path, [RUNNING] * 3) == []


def test_a_page_number_is_not_imprint(tmp_path):
    # A folio counts the artifact's pages; it says nothing the document says.
    assert _imprint(tmp_path, ["1", "2", "3"]) == []


def test_a_folio_the_layout_model_calls_a_footer_is_not_imprint(tmp_path):
    # The model labels some folios page footers ("Page 1 of 3" on a two-page TMD), which the kind alone would let
    # through; the same test that names a page number keeps it out. The model is not run here - the kind is set by
    # hand - because what is under test is the imprint pass, not the model.
    path = _document(tmp_path, ["Page 1 of 3", "Underwritten by Hollard", "Prepared 15 October 2025"])
    pdf = pymupdf.open(path)
    page = process_page(pdf[0], 1, OFF)
    page.meta.pop("imprint", None)
    for b in page.blocks:
        if "Page 1 of 3" in b.text:
            b.kind = BlockKind.FOOTER
    _record_imprint(page, list(page.blocks), pdf[0])
    assert (page.meta.get("imprint") or []) == [], page.meta.get("imprint")


def test_with_no_page_beside_to_ask_nothing_is_recorded(tmp_path):
    # A one-page file - every olmOCR-bench file is one - cannot show whether a line runs, so nothing is claimed.
    assert _imprint(tmp_path, [ISSUER]) == []
