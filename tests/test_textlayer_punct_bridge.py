"""A lone punctuation mark is no filler for the text layer's bridge (2503.06630 page 14)."""
import glob

import pytest

PAGE = next(iter(sorted(glob.glob("bench/data/olmocr-bench/bench_data/pdfs/arxiv_math/2503.06630_pg14.pdf"))), None)


@pytest.mark.skipif(PAGE is None, reason="benchmark page not present")
def test_two_fractions_keep_their_denominators():
    """"(ii) w1/w2 , w2/w1 in L^inf": PDFium hands the comma between the fractions over as a segment of its
    own; taken for a filler it welded the two denominators into one segment no fraction bar covers, and
    both fractions read as underlines. Each denominator now joins the line under its own bar."""
    import pymupdf

    from truedoc.extract.textlayer import extract_page

    doc = pymupdf.open(PAGE)
    try:
        page = extract_page(doc[0], 1)
    finally:
        doc.close()
    item = [l.text for l in page.lines if l.text.startswith("(ii)")]
    assert item and sum(item[0].count(w) for w in ("w1", "w2")) == 4, item
