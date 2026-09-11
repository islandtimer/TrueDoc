"""A spacing accent PDFium's text page emits after later glyphs does not end its line (2503.04407 page 3)."""
import glob

import pytest

from truedoc.extract import pdftext_rawdict as A

HAT_PAGE = next(iter(sorted(glob.glob("bench/data/olmocr-bench/bench_data/pdfs/arxiv_math/2503.04407_pg3.pdf"))), None)


def _lines(path: str) -> list[str]:
    A._CACHE.clear()
    raw = A.build(path, 1)
    assert raw is not None
    return ["".join(c["c"] for sp in ln["spans"] for c in sp["chars"]) for b in raw["blocks"] for ln in b["lines"]]


@pytest.mark.skipif(HAT_PAGE is None, reason="benchmark page not present")
def test_a_hat_emitted_after_later_glyphs_does_not_end_the_line():
    """TeX draws the hat of \\hat{v} before the v; PDFium's text page emits it after the theta that
    follows, and the backward-jump rule cut the sentence there, its tail on a line of its own.
    MuPDF reads "Consider a target at (hat tau, hat v, theta), where hat tau denotes the delay" as one line."""
    lines = _lines(HAT_PAGE)
    assert any("Consider a target at" in line and "where" in line for line in lines), \
        [line for line in lines if "target" in line or "where" in line]
