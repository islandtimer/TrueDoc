"""xy-pic's diagram glyphs are drawing and do not enter the text layer (2503.05329 page 4)."""
import glob

import pytest

from truedoc.extract import pdftext_rawdict as A

PAGE = next(iter(sorted(glob.glob("bench/data/olmocr-bench/bench_data/pdfs/arxiv_math/2503.05329_pg4.pdf"))), None)


def test_xypic_font_names_are_recognised():
    assert A._is_xypic("AQSYMO+XYATIP-Medium") and A._is_xypic("XYLINE10")
    assert not A._is_xypic("CMMI10") and not A._is_xypic("ZapfDingbats")


@pytest.mark.skipif(PAGE is None, reason="benchmark page not present")
def test_a_commutative_diagram_leaves_no_dingbats_or_dollar_signs():
    """The diagram's arrows read as dingbats ("❜❜❜❜ ❨❨❨") and one arrow tip as a bare "$", which opened a
    formula in the markdown that paired with every later one."""
    A._CACHE.clear()
    raw = A.build(PAGE, 1)
    assert raw is not None
    fonts = [str(sp.get("font") or "") for b in raw["blocks"] for ln in b["lines"] for sp in ln["spans"] if sp["chars"]]
    text = "".join(c["c"] for b in raw["blocks"] for ln in b["lines"] for sp in ln["spans"] for c in sp["chars"])
    assert not any(A._is_xypic(f) for f in fonts), sorted(set(fonts))
    assert "$" not in text and "❜" not in text and "❨" not in text
