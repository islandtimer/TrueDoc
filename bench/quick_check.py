"""Quick regression check: official tests on a fixed dozen benchmark pages.

Runs in a minute or two (layout model included; maths rendering only where a
page has maths tests) and prints pass counts per page next to the last
recorded counts, so a change that silently breaks something shows up before
a full benchmark run.

    python bench/quick_check.py            # compare with bench/quick_expected.json
    python bench/quick_check.py --update   # record the current counts as expected
"""

from __future__ import annotations

import argparse
import json
import os
import time

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BENCH = os.path.join(REPO, "bench", "data", "olmocr-bench", "bench_data")
EXPECTED = os.path.join(REPO, "bench", "quick_expected.json")

PAGES = [
    ("tables", "0953927d7a3f032c46a2e6d0ead837398a0b_pg20", "table_tests.jsonl"),
    ("tables", "b5c5b8661b5a272e7a175cdb20d49e67ba0d_pg4", "table_tests.jsonl"),
    ("tables", "26076dc369efd78b3087643cc7153509bd18_pg3_pg1", "table_tests.jsonl"),
    ("multi_column", "05eac72b90295dbb76786d1fe5e2fe0db27d_page_6_pg1", "multi_column.jsonl"),
    ("multi_column", "01566a951fd40f8c1a4b8190cc3d0f93c393_page_7_pg1", "multi_column.jsonl"),
    ("multi_column", "07c14b471fd33c56b988cc7a58dae211d16f_page_13_pg1", "multi_column.jsonl"),
    ("headers_footers", "8ac1da6f81224e0e6ddc208cd4f0ca158f1f567c_page_14", "headers_footers.jsonl"),
    ("headers_footers", "04cea54b5e3d95140c36cfa315a41be27b2434f9_page_1_processed", "headers_footers.jsonl"),
    ("long_tiny_text", "11_pg146_pg1", "long_tiny_text.jsonl"),
    ("long_tiny_text", "13_pg531_pg1", "long_tiny_text.jsonl"),
    ("arxiv_math", "2503.04048_pg46", "arxiv_math.jsonl"),
    ("arxiv_math", "2503.03762_pg1", "arxiv_math.jsonl"),
    ("old_scans", "10", "old_scans.jsonl"),
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--update", action="store_true")
    ap.add_argument("--no-layout", action="store_true")
    args = ap.parse_args()
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
    from olmocr.bench.tests import load_tests
    from truedoc.pipeline import ConvertOptions, convert

    expected = json.load(open(EXPECTED, encoding="utf-8")) if os.path.exists(EXPECTED) else {}
    results: dict[str, list[int]] = {}
    total = passed = 0
    t0 = time.time()
    for cat, stem, jsonl in PAGES:
        pdf_rel = f"{cat}/{stem}.pdf"
        tests = [t for t in load_tests(os.path.join(BENCH, jsonl)) if t.pdf == pdf_rel]
        md = convert(os.path.join(BENCH, "pdfs", pdf_rel), ConvertOptions(frontmatter=False, pages=[1], layout=not args.no_layout))
        p = sum(1 for t in tests if t.run(md)[0])
        results[pdf_rel] = [p, len(tests)]
        total += len(tests)
        passed += p
        exp = expected.get(pdf_rel)
        flag = ""
        if exp:
            if p < exp[0]:
                flag = f"   <-- REGRESSION (was {exp[0]})"
            elif p > exp[0]:
                flag = f"   improved (was {exp[0]})"
        print(f"{pdf_rel:70s} {p:3d}/{len(tests):<3d}{flag}")
    print(f"\nTOTAL {passed}/{total}   ({time.time() - t0:.0f}s)")
    if args.update:
        json.dump(results, open(EXPECTED, "w", encoding="utf-8"), indent=2)
        print("expected counts updated")


if __name__ == "__main__":
    main()
