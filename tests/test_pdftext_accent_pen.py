"""An accent PDFium emits out of order, and leaves standing over its letter, does not move the pen
(2503.07532 page 14)."""
import glob

import pytest

from truedoc.extract import pdftext_rawdict as A

PAGE = next(iter(sorted(glob.glob("bench/data/olmocr-bench/bench_data/pdfs/arxiv_math/2503.07532_pg14.pdf"))), None)


@pytest.mark.skipif(PAGE is None, reason="benchmark page not present")
def test_the_word_with_bars_stays_on_one_line():
    """The bars of "e c d c-bar d-bar e-bar a b a-bar b-bar e" come out of order; the bar of e-bar stands
    back over the e, and the bar of a-bar after it, 30pt on, was measured from that bar as a jump of
    2.9 em and cut the word - its tail went after the next line. MuPDF reads the line whole."""
    A._CACHE.clear()
    raw = A.build(PAGE, 1)
    assert raw is not None
    lines = ["".join(c["c"] for sp in ln["spans"] for c in sp["chars"]) for b in raw["blocks"] for ln in b["lines"]]
    assert any("labelled by the word" in line and "Note that" in line for line in lines), \
        [line for line in lines if "labelled" in line or "Note that" in line]
