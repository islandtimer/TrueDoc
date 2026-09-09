"""Does the reader swap's quick-gate result hold on pages it was never tuned on? (M18)

The 1.5x line-splitting threshold in `truedoc/extract/pdftext_rawdict.py` was chosen on
`bench/quick_check.py`, which is 13 pages - and two of those 13 are pages I read while
diagnosing the fault. That is exactly the shape of an overfit, so this scores a much larger
sample that deliberately *excludes* the gate's pages, under several thresholds, and reports
each reader's pass rate per category.

    python bench/tools/reader_generalise.py [--pages 120] [--seed 7] [--gaps 1.0,1.5,2.25]

Two things to read off the output: whether pdftext's shortfall against MuPDF on unseen pages
matches its shortfall on the gate (if the gate is honest, they agree), and whether the
threshold plateau sits in the same place here as it did there (if it moves, 1.5 was fitted to
the gate's noise rather than to anything real).

Only pages with a digital text layer can tell us anything - a page sent to a model under D019
reads the same whichever text reader is installed - so the sample is drawn from the five
text-heavy categories and old scans are left out.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
import sys
import time

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BENCH = os.path.join(REPO, "bench", "data", "olmocr-bench", "bench_data")

CATEGORIES = [
    ("tables", "table_tests.jsonl"),
    ("multi_column", "multi_column.jsonl"),
    ("headers_footers", "headers_footers.jsonl"),
    ("long_tiny_text", "long_tiny_text.jsonl"),
    ("arxiv_math", "arxiv_math.jsonl"),
]

# The gate's own pages, excluded so this measures generalisation rather than repeating it.
GATE_STEMS = {
    "0953927d7a3f032c46a2e6d0ead837398a0b_pg20", "b5c5b8661b5a272e7a175cdb20d49e67ba0d_pg4",
    "26076dc369efd78b3087643cc7153509bd18_pg3_pg1", "05eac72b90295dbb76786d1fe5e2fe0db27d_page_6_pg1",
    "01566a951fd40f8c1a4b8190cc3d0f93c393_page_7_pg1", "07c14b471fd33c56b988cc7a58dae211d16f_page_13_pg1",
    "8ac1da6f81224e0e6ddc208cd4f0ca158f1f567c_page_14", "04cea54b5e3d95140c36cfa315a41be27b2434f9_page_1_processed",
    "11_pg146_pg1", "13_pg531_pg1", "2503.04048_pg46", "2503.03762_pg1", "10",
}


def sample(n: int, seed: int) -> list[tuple[str, str, str]]:
    """(category, stem, jsonl) for n pages, spread evenly over the categories."""
    rng = random.Random(seed)
    per = max(1, n // len(CATEGORIES))
    picked: list[tuple[str, str, str]] = []
    for cat, jsonl in CATEGORIES:
        folder = os.path.join(BENCH, "pdfs", cat)
        stems = sorted(f[:-4] for f in os.listdir(folder) if f.endswith(".pdf"))
        stems = [s for s in stems if s not in GATE_STEMS]
        rng.shuffle(stems)
        picked += [(cat, s, jsonl) for s in stems[:per]]
    return picked


def score(pages: list, reader: str, gap: str | None) -> dict:
    """Convert and score every page in one child process, so the layout model loads once."""
    env = dict(os.environ)
    env.pop("TRUEDOC_READER", None)
    env.pop("TRUEDOC_LINE_GAP", None)
    if reader:
        env["TRUEDOC_READER"] = reader
    if gap:
        env["TRUEDOC_LINE_GAP"] = gap
    env["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
    env["TRANSFORMERS_VERBOSITY"] = "error"
    child = os.path.join(os.path.dirname(__file__), "_generalise_worker.py")
    out = subprocess.run([sys.executable, child], input=json.dumps(pages),
                         capture_output=True, text=True, env=env, cwd=REPO)
    for line in reversed(out.stdout.splitlines()):
        if line.startswith("{"):
            return json.loads(line)
    raise SystemExit("worker produced no result:\n" + out.stdout[-3000:] + "\n" + out.stderr[-3000:])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=120)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--gaps", default="1.0,1.5,2.25")
    args = ap.parse_args()

    pages = sample(args.pages, args.seed)
    print(f"{len(pages)} pages, none of them the gate's, seed {args.seed}", flush=True)

    runs = [("MuPDF", "", None)] + [(f"pdftext gap {g}", "pdftext", g) for g in args.gaps.split(",")]
    results = {}
    for label, reader, gap in runs:
        t0 = time.time()
        results[label] = score(pages, reader, gap)
        r = results[label]
        print(f"  {label:20s} {r['passed']:5d}/{r['total']:<5d} "
              f"{100.0 * r['passed'] / max(1, r['total']):5.1f}%   ({time.time() - t0:.0f}s)", flush=True)

    base = results["MuPDF"]
    print("\nBy category (passed of total):")
    cats = sorted({c for c in base["by_cat"]})
    head = "  {:<16s}".format("") + "".join(f"{lbl:>18s}" for lbl, _, _ in runs)
    print(head)
    for cat in cats:
        row = f"  {cat:<16s}"
        for lbl, _, _ in runs:
            p, t = results[lbl]["by_cat"].get(cat, (0, 0))
            row += f"{p:>8d}/{t:<9d}"
        print(row)

    print("\nAgainst MuPDF:")
    for lbl, _, _ in runs[1:]:
        d = results[lbl]["passed"] - base["passed"]
        print(f"  {lbl:20s} {d:+5d} checks  ({100.0 * results[lbl]['passed'] / max(1, base['passed']):.1f}% of MuPDF)")


if __name__ == "__main__":
    main()
