"""No invented blank between a script-sized glyph and a full-size one in a gap MuPDF leaves closed
(2503.09195 page 13)."""
import glob

import pytest

from truedoc.extract import pdftext_rawdict as A

PAGE = next(iter(sorted(glob.glob("bench/data/olmocr-bench/bench_data/pdfs/arxiv_math/2503.09195_pg13.pdf"))), None)


@pytest.mark.skipif(PAGE is None, reason="benchmark page not present")
def test_a_subscript_and_its_closing_parenthesis_stay_together():
    """PDFium puts a zero-width blank in the 0.98pt gap after the 7pt subscript of "(S, D_S)-connected" -
    0.14 em of the subscript, 0.10 em of the parenthesis - and the maths span ended at it."""
    A._CACHE.clear()
    raw = A.build(PAGE, 1)
    assert raw is not None
    lines = ["".join(c["c"] for sp in ln["spans"] for c in sp["chars"]) for b in raw["blocks"] for ln in b["lines"]]
    assert any("DS)-connected" in line for line in lines), [line for line in lines if "connected" in line]
