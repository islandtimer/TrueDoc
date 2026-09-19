"""What D024's escaped dollar costs on the benchmark: every check of every page of run 98, as written and with the
escape taken out again (the scorer reads a cell's text literally).

usage (repo root, the project's venv): escaped_dollar_cost.py [candidate folder name, default truedoc97]"""
import collections
import glob
import os

from olmocr.bench.tests import load_tests

import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CANDIDATE = sys.argv[1] if len(sys.argv) > 1 else "truedoc97"
B = os.path.join(REPO, "bench/data/olmocr-bench/bench_data")
ESCAPED = chr(92) + "$"
tests = []
for f in glob.glob(os.path.join(B, "*.jsonl")):
    try:
        tests += load_tests(f)
    except Exception:
        pass
by_pdf = collections.defaultdict(list)
for t in tests:
    by_pdf[t.pdf].append(t)
gain = collections.Counter()
lost = collections.Counter()
pages = 0
for pdf, ts in by_pdf.items():
    stem = pdf[:-4]
    found = glob.glob(os.path.join(B, CANDIDATE, stem + "_pg1_repeat1.md")) or glob.glob(os.path.join(B, CANDIDATE, stem + "*.md"))
    if not found:
        continue
    md = open(found[0], encoding="utf-8").read()
    if ESCAPED not in md:
        continue
    pages += 1
    plain = md.replace(ESCAPED, "$")
    for t in ts:
        a, b = t.run(md)[0], t.run(plain)[0]
        if b and not a:
            gain[(t.type, pdf.split("/")[0])] += 1
        if a and not b:
            lost[(t.type, pdf.split("/")[0])] += 1
print("pages of run 98 that hold an escaped dollar: %d" % pages)
print("checks that pass only with the escape taken out:", dict(gain), "=", sum(gain.values()))
print("checks that pass only WITH the escape:", dict(lost), "=", sum(lost.values()))
