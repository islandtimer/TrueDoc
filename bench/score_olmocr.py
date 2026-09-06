"""Windows-safe wrapper around the official olmOCR-bench scorer.

Two small adaptations, neither of which changes a scoring rule:

1. The official scorer compares paths produced by os.path.relpath (backslashes
   on Windows) with the forward-slash paths stored in the test JSONL files.
   Patching relpath to always return forward slashes makes the two agree.
2. The newer GitHub version of benchmark.py (vendored in bench/olmocr_ref/)
   restricts a single-JSONL run to the PDFs that file references, which lets us
   score one category quickly. We run that file, with its relative imports
   rewritten to absolute ones, against the installed olmocr package.

Usage (from the repo root, inside the venv):
    python bench/score_olmocr.py --dir bench/data/olmocr-bench/bench_data --candidate truedoc
    python bench/score_olmocr.py --dir bench/data/olmocr-bench/bench_data/table_tests.jsonl --candidate truedoc --force
"""

from __future__ import annotations

import os
import sys

_orig_relpath = os.path.relpath


def _relpath(path, start=os.curdir):
    return _orig_relpath(path, start).replace("\\", "/")


os.path.relpath = _relpath

HERE = os.path.dirname(os.path.abspath(__file__))
VENDORED = os.path.join(HERE, "olmocr_ref", "benchmark.py")


def _run_vendored() -> None:
    with open(VENDORED, encoding="utf-8") as fh:
        src = fh.read()
    src = src.replace("from .report import", "from olmocr.bench.report import")
    src = src.replace("from .tests import", "from olmocr.bench.tests import")
    src = src.replace("from .utils import", "from olmocr.bench.utils import")
    code = compile(src, VENDORED, "exec")
    ns = {"__name__": "__main__", "__file__": VENDORED}
    exec(code, ns)


if __name__ == "__main__":
    sys.argv = ["olmocr.bench.benchmark"] + sys.argv[1:]
    if os.path.exists(VENDORED):
        _run_vendored()
    else:
        import runpy

        runpy.run_module("olmocr.bench.benchmark", run_name="__main__", alter_sys=True)
