"""Score a run on the held-out fifth of the benchmark, separately from the rest.

Decision D016: a fifth of the benchmark pages is never looked at when tuning
rules, so its score is an honest check on overfitting. The split is fixed by a
hash of the PDF's name (no list to maintain, the same pages every time) and
written to bench/holdout.txt for reference.

    python bench/holdout_score.py <run_dir>          # e.g. bench/runs/truedoc10-20260903-152344
    python bench/holdout_score.py --list             # write bench/holdout.txt

The run folder must hold failed_tests.jsonl from the official scorer; the
category test files live in bench/data/olmocr-bench/bench_data/*.jsonl.
"""

from __future__ import annotations

import glob
import hashlib
import json
import os
import sys

BENCH = os.path.join("bench", "data", "olmocr-bench", "bench_data")
HOLDOUT_FILE = os.path.join("bench", "holdout.txt")


def is_held_out(pdf: str) -> bool:
    """True for about one page in five, chosen by a stable hash of the file name."""
    name = os.path.basename(pdf)
    return int(hashlib.sha1(name.encode("utf-8")).hexdigest(), 16) % 5 == 0


def all_tests() -> list[dict]:
    tests: list[dict] = []
    for path in sorted(glob.glob(os.path.join(BENCH, "*.jsonl"))):
        category = os.path.basename(path)[:-6]
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            t = json.loads(line)
            # Categories follow the test files. (The official "baseline" category is
            # made by the scorer itself, one check per page, and is not split here.)
            t["_category"] = category
            tests.append(t)
    return tests


def write_list() -> None:
    pdfs = sorted({t["pdf"] for t in all_tests()})
    held = [p for p in pdfs if is_held_out(p)]
    with open(HOLDOUT_FILE, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# Held-out benchmark pages (about one in five, by a stable hash of the file name). Never tune a rule on these.\n")
        for p in held:
            fh.write(p + "\n")
    print(f"{len(held)} of {len(pdfs)} pages held out; list written to {HOLDOUT_FILE}")


def score(run_dir: str) -> None:
    failed = set()
    for line in open(os.path.join(run_dir, "failed_tests.jsonl"), encoding="utf-8"):
        line = line.strip()
        if line:
            t = json.loads(line)
            failed.add((t["pdf"], t.get("id")))
    rows: dict[str, dict[str, list[int]]] = {}
    for t in all_tests():
        bucket = "held-out" if is_held_out(t["pdf"]) else "tuned-on"
        cell = rows.setdefault(t["_category"], {}).setdefault(bucket, [0, 0])
        cell[0] += 1
        cell[1] += 0 if (t["pdf"], t.get("id")) in failed else 1
    print(f"{'category':18} {'held-out':>14} {'tuned-on':>14}")
    totals = {"held-out": [0, 0], "tuned-on": [0, 0]}
    per_cat = {"held-out": [], "tuned-on": []}
    for cat in sorted(rows):
        parts = []
        for bucket in ("held-out", "tuned-on"):
            n, ok = rows[cat].get(bucket, [0, 0])
            totals[bucket][0] += n
            totals[bucket][1] += ok
            pct = 100.0 * ok / n if n else 0.0
            per_cat[bucket].append(pct)
            parts.append(f"{pct:5.1f} ({ok}/{n})")
        print(f"{cat:18} {parts[0]:>14} {parts[1]:>14}")
    # The official overall is the mean of the category scores, so do the same here.
    for bucket in ("held-out", "tuned-on"):
        pcts = per_cat[bucket]
        mean = sum(pcts) / len(pcts) if pcts else 0.0
        n, ok = totals[bucket]
        print(f"{bucket:18} mean of categories {mean:5.1f}   checks {ok}/{n}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--list":
        write_list()
    elif len(sys.argv) > 1:
        score(sys.argv[1])
    else:
        print(__doc__)
