"""One configuration's worth of conversions for reader_generalise.py.

Reads a JSON page list on stdin, converts and scores each page with whatever
TRUEDOC_READER / TRUEDOC_LINE_GAP the parent set, and writes one JSON line of
counts to stdout. Runs as a child process so the layout model is loaded once per
configuration and the environment switch is read at import time, cleanly.
"""
from __future__ import annotations

import json
import os
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BENCH = os.path.join(REPO, "bench", "data", "olmocr-bench", "bench_data")


def main() -> None:
    pages = json.loads(sys.stdin.read())
    from olmocr.bench.tests import load_tests
    from truedoc.pipeline import ConvertOptions, convert

    cache: dict[str, list] = {}
    passed = total = 0
    by_cat: dict[str, list] = {}
    for cat, stem, jsonl in pages:
        rel = f"{cat}/{stem}.pdf"
        if jsonl not in cache:
            cache[jsonl] = load_tests(os.path.join(BENCH, jsonl))
        tests = [t for t in cache[jsonl] if t.pdf == rel]
        if not tests:
            continue
        try:
            md = convert(os.path.join(BENCH, "pdfs", rel),
                         ConvertOptions(frontmatter=False, pages=[1], layout=True))
        except Exception as exc:                      # a crash is a zero, not a skip
            print(f"FAILED {rel}: {exc}", file=sys.stderr)
            md = ""
        p = sum(1 for t in tests if t.run(md)[0])
        passed += p
        total += len(tests)
        slot = by_cat.setdefault(cat, [0, 0])
        slot[0] += p
        slot[1] += len(tests)
        print(f"  {rel:70s} {p}/{len(tests)}", file=sys.stderr)
    print(json.dumps({"passed": passed, "total": total, "by_cat": by_cat}))


if __name__ == "__main__":
    main()
