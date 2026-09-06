"""Run one page's formula checks against candidate LaTeX strings.

usage: python bench/tools/pair_probe.py <page stem> '<candidate latex>' ['<candidate latex>' ...]
Each candidate is wrapped in $$...$$ and every maths check of that arxiv_math page is run on it;
prints PASS per check that passes, so a single spelling difference can be isolated (this is how
it was settled that the checker treats \\tfrac and \\frac as different, and \\left\\{ and \\{ as the same).
"""
import os
import sys

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, REPO)
from olmocr.bench.tests import load_tests  # noqa: E402

B = os.path.join(REPO, "bench", "data", "olmocr-bench", "bench_data")
stem = sys.argv[1]
tests = [t for t in load_tests(os.path.join(B, "arxiv_math.jsonl")) if stem in t.pdf and getattr(t, "math", None)]
for cand in sys.argv[2:]:
    print("== candidate:", cand)
    md = "$$" + cand + "$$"
    for t in tests:
        ok, reason = t.run(md)
        if ok:
            print("   PASS", t.math[:100])
