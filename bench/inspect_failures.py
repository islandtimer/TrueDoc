"""Summarise and inspect failed benchmark tests.

    python bench/inspect_failures.py bench/runs/<run>/failed_tests.jsonl            # summary by category and type
    python bench/inspect_failures.py bench/runs/<run>/failed_tests.jsonl --pdf X    # show failed tests for one PDF and our output
    python bench/inspect_failures.py bench/runs/<run>/failed_tests.jsonl --category tables --type table --n 20
"""

from __future__ import annotations

import argparse
import collections
import json
import os

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BENCH_DATA = os.path.join(REPO, "bench", "data", "olmocr-bench", "bench_data")


def load(path: str) -> list[dict]:
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def summary(tests: list[dict]) -> None:
    by_cat = collections.Counter()
    by_cat_type = collections.Counter()
    by_pdf = collections.Counter()
    for t in tests:
        cat = t["pdf"].split("/")[0]
        by_cat[cat] += 1
        by_cat_type[(cat, t["type"])] += 1
        by_pdf[t["pdf"]] += 1
    print("Failed tests by category:")
    for cat, n in by_cat.most_common():
        types = ", ".join(f"{ty}={m}" for (c, ty), m in by_cat_type.items() if c == cat)
        print(f"  {cat:18s} {n:5d}   ({types})")
    print("\nPDFs with most failures:")
    for pdf, n in by_pdf.most_common(15):
        print(f"  {n:4d}  {pdf}")


def show_pdf(tests: list[dict], pdf: str, candidate: str) -> None:
    mine = [t for t in tests if pdf in t["pdf"]]
    if not mine:
        print("no failed tests match", pdf)
        return
    full = mine[0]["pdf"]
    print(f"=== {full}: {len(mine)} failed tests")
    for t in mine:
        keys = {k: v for k, v in t.items() if k in ("type", "text", "before", "after", "cell", "up", "down", "left", "right", "top_heading", "left_heading", "math", "max_diffs")}
        print(json.dumps(keys, ensure_ascii=False))
    stem = os.path.splitext(full)[0]
    md = os.path.join(BENCH_DATA, candidate, f"{stem}_pg1_repeat1.md")
    print(f"\n--- our output: {md}")
    if os.path.exists(md):
        print(open(md, encoding="utf-8").read()[:6000])
    else:
        print("(missing)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("failed")
    ap.add_argument("--pdf")
    ap.add_argument("--category")
    ap.add_argument("--type")
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--candidate", default="truedoc")
    args = ap.parse_args()
    tests = load(args.failed)
    if args.pdf:
        show_pdf(tests, args.pdf, args.candidate)
        return
    if args.category or args.type:
        sel = [t for t in tests if (not args.category or t["pdf"].startswith(args.category + "/")) and (not args.type or t["type"] == args.type)]
        for t in sel[: args.n]:
            keys = {k: v for k, v in t.items() if k in ("pdf", "type", "text", "before", "after", "cell", "up", "down", "left", "right", "top_heading", "left_heading", "math", "max_diffs")}
            print(json.dumps(keys, ensure_ascii=False))
        print(f"\n{len(sel)} matching failed tests")
        return
    summary(tests)


if __name__ == "__main__":
    main()
