"""For every benchmark page that has a model reading on disk, run each check on the raw reading
and on our output (run 60): where the raw reading passes and ours fails, our processing lost it;
the reverse is a processing gain. Held-out pages are reported only as totals."""
import collections
import glob
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "bench"))
os.chdir(REPO)
from holdout_score import is_held_out          # noqa: E402
from olmocr.bench.tests import load_tests      # noqa: E402

B = os.path.join(REPO, "bench", "data", "olmocr-bench", "bench_data")
CAND = "truedoc59"
SUBSETS = ["arxiv_math", "headers_footers", "long_tiny_text", "multi_column", "old_scans", "old_scans_math", "table_tests"]


def reading_for(pdf):
    sub, name = pdf.split("/")
    stem = name[:-4]
    for folder in ("olmocr2b",):
        for pat in (f"{stem}_pg1_repeat1.md", f"{stem}_pg1.md", f"{stem}.md"):
            p = os.path.join(B, folder, sub, pat)
            if os.path.exists(p):
                return p
    return None


def strip_front(t):
    if t.startswith("---"):
        parts = t.split("---", 2)
        if len(parts) == 3:
            return parts[2]
    return t


losses = collections.defaultdict(list)
gains = collections.defaultdict(list)
totals = collections.Counter()
for sub in SUBSETS:
    tests = load_tests(os.path.join(B, sub + ".jsonl"))
    by_pdf = collections.defaultdict(list)
    for t in tests:
        by_pdf[t.pdf].append(t)
    for pdf, ts in by_pdf.items():
        rp = reading_for(pdf)
        if rp is None:
            continue
        stem = os.path.basename(pdf)[:-4]
        ours = glob.glob(os.path.join(B, CAND, pdf.split("/")[0], f"{stem}_pg1_repeat1.md"))
        if not ours:
            continue
        raw = strip_front(open(rp, encoding="utf-8").read())
        out = strip_front(open(ours[0], encoding="utf-8").read())
        held = is_held_out(pdf)
        for t in ts:
            try:
                r_ok, _ = t.run(raw)
                o_ok, why = t.run(out)
            except Exception as e:      # noqa: BLE001
                continue
            totals[("pages",)] = totals[("pages",)]
            key = "held" if held else "tuned"
            totals[(key, "raw", r_ok)] += 1
            totals[(key, "ours", o_ok)] += 1
            if r_ok and not o_ok:
                losses[pdf].append((t.type, getattr(t, "text", "") or getattr(t, "cell", "") or getattr(t, "before", ""), (why or "")[:100], held))
            elif o_ok and not r_ok:
                gains[pdf].append((t.type, getattr(t, "text", "") or getattr(t, "cell", "") or getattr(t, "before", ""), held))

print("checks on model pages: tuned-on raw pass", totals[("tuned", "raw", True)], "fail", totals[("tuned", "raw", False)],
      "| ours pass", totals[("tuned", "ours", True)], "fail", totals[("tuned", "ours", False)])
print("held-out: raw pass", totals[("held", "raw", True)], "fail", totals[("held", "raw", False)],
      "| ours pass", totals[("held", "ours", True)], "fail", totals[("held", "ours", False)])
n_loss = sum(len(v) for v in losses.values()); n_gain = sum(len(v) for v in gains.values())
print("processing losses (raw passes, ours fails):", n_loss, " gains:", n_gain)
print("\nLOSSES by page (tuned-on shown in full; held-out counted only):")
for pdf, items in sorted(losses.items(), key=lambda kv: -len(kv[1])):
    if items[0][3]:
        print(f"  {pdf}: {len(items)} (held-out)")
        continue
    print(f"  {pdf}: {len(items)}")
    for typ, text, why, _ in items[:6]:
        print(f"      {typ:8} {str(text)[:70]!r}  {why}")
print("\nGAINS by page:")
for pdf, items in sorted(gains.items(), key=lambda kv: -len(kv[1]))[:15]:
    print(f"  {pdf}: {len(items)}{' (held-out)' if items[0][2] else ''}")
