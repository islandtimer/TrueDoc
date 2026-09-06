"""Quick formula check: convert a few arxiv_math pages and run the official MathTest on them.

    python bench/math_check.py 2503.04048_pg46 2503.03754_pg10 ...
    python bench/math_check.py --first 20 [--layout/--no-layout] [--show-fails]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BENCH = os.path.join(REPO, "bench", "data", "olmocr-bench", "bench_data")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("stems", nargs="*")
    ap.add_argument("--first", type=int, default=0)
    ap.add_argument("--category", default="arxiv_math")
    ap.add_argument("--layout", action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--show-fails", action="store_true")
    ap.add_argument("--show-output", action="store_true")
    args = ap.parse_args()

    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    from olmocr.bench.tests import load_tests
    from truedoc.pipeline import ConvertOptions, convert

    tests = load_tests(os.path.join(BENCH, f"{args.category}.jsonl"))
    by_pdf: dict[str, list] = {}
    for t in tests:
        by_pdf.setdefault(t.pdf, []).append(t)
    stems = args.stems
    if args.first:
        stems = sorted({os.path.splitext(os.path.basename(p))[0] for p in by_pdf})[: args.first]
    total = passed = 0
    per_type: dict[str, list[int]] = {}
    t0 = time.time()
    for stem in stems:
        pdf_rel = f"{args.category}/{stem}.pdf"
        pdf_tests = by_pdf.get(pdf_rel, [])
        md = convert(os.path.join(BENCH, "pdfs", pdf_rel), ConvertOptions(frontmatter=False, pages=[1], layout=args.layout))
        if args.show_output:
            print("=" * 30, stem)
            print(md)
        p = 0
        for t in pdf_tests:
            ok, reason = t.run(md)
            per_type.setdefault(t.type, [0, 0])
            per_type[t.type][1] += 1
            if ok:
                per_type[t.type][0] += 1
                p += 1
            elif args.show_fails:
                print(f"  FAIL [{t.type}] {getattr(t, 'math', getattr(t, 'text', ''))[:100]!r}\n        {reason[:160]}")
        total += len(pdf_tests)
        passed += p
        print(f"{stem}: {p}/{len(pdf_tests)}")
    print(f"\nTOTAL {passed}/{total} = {100.0 * passed / max(1, total):.1f}%  ({time.time() - t0:.0f}s)")
    for ty, (a, b) in sorted(per_type.items()):
        print(f"  {ty:8s} {a}/{b}")


if __name__ == "__main__":
    main()
