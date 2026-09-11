"""Text objects PDFium's text page reports no character for still keep a line whole (00f6c2ee page 10).

The gap in "where | refers to the number of visual" holds a Cambria Math glyph and a zero-width Times
object whose object text PDFium never reports. MuPDF traces them as glyphs, its pen crosses the gap,
and it reads one line; the reader's gap rules cut the sentence there, and its halves read as two
columns (one check)."""
import glob

import pytest

from truedoc.extract import pdftext_rawdict as A

PAGE = next(iter(sorted(glob.glob(
    "bench/data/olmocr-bench/bench_data/pdfs/multi_column/00f6c2eea6b51fb1bf637b5f8a850588d7e2_page_10*.pdf"))), None)


def _lines(path: str) -> list[str]:
    A._CACHE.clear()
    raw = A.build(path, 1)
    assert raw is not None
    return [" ".join("".join(c["c"] for sp in ln["spans"] for c in sp["chars"]).split())
            for b in raw["blocks"] for ln in b["lines"]]


@pytest.mark.skipif(PAGE is None, reason="benchmark page not present")
def test_a_glyph_the_text_page_does_not_report_keeps_the_line_whole():
    lines = _lines(PAGE)
    assert any("where" in line and "refers to" in line for line in lines), \
        [line for line in lines if "refers" in line or "where" in line]
