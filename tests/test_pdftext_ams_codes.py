"""AMS symbol-font codes PDFium leaves raw are read as MuPDF reads them (ams_census.py, 12 Sept)."""
import glob

import pytest

from truedoc.extract import pdftext_rawdict as A

PAGE = next(iter(sorted(glob.glob("bench/data/olmocr-bench/bench_data/pdfs/arxiv_math/2503.07281_pg12.pdf"))), None)


def test_the_three_codes_from_the_census():
    assert A._tex_symbol("MSBM10", "(") == "⊊"      # subsetneq, not cmsy's Leftarrow
    assert A._tex_symbol("MSBM10", "y") == "↷"      # curvearrowright
    assert A._tex_symbol("MSAM10", chr(8)) == "⟳"   # circlearrowright
    assert A._tex_symbol("MSAM10", chr(2)) is None   # MuPDF's registered sign contradicts the layout


@pytest.mark.skipif(PAGE is None, reason="benchmark page not present")
def test_a_proper_subset_sign_on_the_page():
    """2503.07281 page 12: "K^1_Theta (+) Theta H^1 proper-subset H^1_Theta" - PDFium reports msbm's code 0x28
    as "(", which the maths stage read as cmsy's Leftarrow."""
    A._CACHE.clear()
    raw = A.build(PAGE, 1)
    assert raw is not None
    msbm = [c["c"] for b in raw["blocks"] for ln in b["lines"] for sp in ln["spans"]
            if "MSBM" in str(sp.get("font") or "").upper() for c in sp["chars"]]
    assert "⊊" in msbm and "(" not in msbm, msbm
