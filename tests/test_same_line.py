"""A running head is the same line page after page, not the same bag of words.

`_repeated_beside` asked whether 60% of a line's distinct words turned up anywhere in the same band on a page within
two, and ordinary words collide. AAMI's home building PDS heads its settlement decision tree with "If your policy has
a building sum insured"; two pages on, a different heading reads "When you have a building sum insured and we settle
your building claim we will not:", which shares building, if, insured, sum and your - five of the seven - so the
heading was filed as a running head and the page lost the line that says when the tree applies. Asking that the words
run in the same order tells the two apart, and lets a folio or a section number sit between them.
"""

import pymupdf

from truedoc.model import BlockKind
from truedoc.pipeline import ConvertOptions, process_page

BODY = ["You are covered for loss or damage to your home or your contents caused by this event.",
        "We will pay the reasonable cost to repair or replace the damaged part of your home.",
        "The most we will pay is the sum insured shown on your certificate of insurance."]
OFF = ConvertOptions(layout=False, ocr=False, math=False, marks=False, tables=False)
HEADING = "If your policy has a building sum insured"
COLLIDES = "If you have a building sum insured we settle your claim"          # 5 of the heading's 7 words, 71%


def _document(tmp_path, heads, size=11):
    """One page for each head: the head at the top, the same body lines under it on every page."""
    doc = pymupdf.open()
    for head in heads:
        page = doc.new_page(width=405, height=573)
        page.insert_text((14, 40), head, fontsize=size)
        for j, text in enumerate(BODY):
            page.insert_text((14, 120 + 14 * j), text, fontsize=10)
    path = tmp_path / "pds.pdf"
    doc.save(str(path))
    doc.close()
    return str(path)


def _blocks(tmp_path, heads, index, size=11):
    pdf_page = pymupdf.open(_document(tmp_path, heads, size))[index]
    return list(process_page(pdf_page, index + 1, OFF).blocks)


def _named(blocks, text):
    found = [b for b in blocks if text in b.text]
    assert found, [(b.kind, b.provenance, b.text[:40]) for b in blocks]
    return found


def test_a_heading_whose_words_collide_with_another_heading_is_published(tmp_path):
    blocks = _blocks(tmp_path, [COLLIDES, HEADING, COLLIDES], 1)
    assert all(b.kind not in (BlockKind.HEADER, BlockKind.PAGE_NUMBER) for b in _named(blocks, "If your policy")), \
        [(b.kind, b.provenance, b.text[:40]) for b in blocks]


def test_a_running_head_printed_beside_stays_furniture(tmp_path):
    blocks = _blocks(tmp_path, [HEADING, HEADING, HEADING], 1)
    assert all(b.kind == BlockKind.HEADER for b in _named(blocks, "If your policy")), \
        [(b.kind, b.provenance, b.text[:40]) for b in blocks]


def test_a_running_head_stays_furniture_when_the_pages_beside_add_a_section_number(tmp_path):
    # The words still run in order; a folio or a section number between them is not a difference.
    heads = ["Section one " + HEADING, HEADING, "Section three " + HEADING]
    blocks = _blocks(tmp_path, heads, 1)
    assert all(b.kind == BlockKind.HEADER for b in _named(blocks, "If your policy")), \
        [(b.kind, b.provenance, b.text[:40]) for b in blocks]


def test_a_head_whose_words_run_in_another_order_is_published(tmp_path):
    # Same words, different line: "Broken glass - home" against "Home insurance - broken glass cover".
    heads = ["Home insurance broken glass cover", "Broken glass home", "Home insurance broken glass cover"]
    blocks = _blocks(tmp_path, heads, 1)
    assert all(b.kind not in (BlockKind.HEADER, BlockKind.PAGE_NUMBER) for b in _named(blocks, "Broken glass home")), \
        [(b.kind, b.provenance, b.text[:40]) for b in blocks]
