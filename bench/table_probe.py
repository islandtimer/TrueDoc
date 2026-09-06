"""Probe why table pages produce no table: layout region vs structure building.

For each PDF (or the pages of a failed-tests file that produced no table), report
whether the layout model finds a TABLE region, whether the geometry finder finds
a table, and whether `table_from_lines` builds one from the lines inside the
region. Run when the CPU is free (the layout model takes a few seconds a page).

    python bench/table_probe.py --failed bench/runs/<run>/failed_tests.jsonl --candidate truedoc2
    python bench/table_probe.py tables/<stem>.pdf ...
"""

from __future__ import annotations

import argparse
import collections
import json
import os

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BENCH = os.path.join(REPO, "bench", "data", "olmocr-bench", "bench_data")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdfs", nargs="*")
    ap.add_argument("--failed")
    ap.add_argument("--candidate", default="truedoc")
    ap.add_argument("--limit", type=int, default=60)
    args = ap.parse_args()
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")

    import pymupdf
    from olmocr.bench.tests import parse_html_tables, parse_markdown_tables
    from truedoc.extract.render import render_page
    from truedoc.extract.textlayer import extract_page
    from truedoc.layout.base import RegionKind
    from truedoc.layout.docling_layout import get_detector
    from truedoc.tables.aligned import find_aligned_tables, table_from_lines

    pdfs = list(args.pdfs)
    weights: dict[str, int] = collections.Counter()
    if args.failed:
        for line in open(args.failed, encoding="utf-8"):
            t = json.loads(line)
            if t["type"] != "table":
                continue
            md_path = os.path.join(BENCH, args.candidate, t["pdf"][:-4] + "_pg1_repeat1.md")
            md = open(md_path, encoding="utf-8").read() if os.path.exists(md_path) else ""
            if not (parse_markdown_tables(md) + parse_html_tables(md)):
                weights[t["pdf"]] += 1
        pdfs = [p for p, _ in weights.most_common(args.limit)]

    det = get_detector()
    outcomes: collections.Counter = collections.Counter()
    weighted: collections.Counter = collections.Counter()
    for rel in pdfs:
        doc = pymupdf.open(os.path.join(BENCH, "pdfs", rel))
        page = extract_page(doc[0], 1)
        if not page.quality.usable:
            key = "no text layer"
        else:
            img, scale = render_page(doc[0], dpi=120)
            regions = [r for r in det.detect(img, scale) if r.kind == RegionKind.TABLE and r.score >= 0.5]
            geo, _ = find_aligned_tables(page, list(page.lines), page.body_font_size)
            built = 0
            for r in regions:
                inside = [l for l in page.lines if r.bbox.contains_point(l.bbox.cx, l.bbox.cy)]
                if table_from_lines(inside, page.body_font_size) is not None:
                    built += 1
            if geo:
                key = "geometry finds a table"
            elif not regions:
                key = "no table region, no geometry"
            elif built:
                key = "region + structure built (should now work)"
            else:
                key = "region found but structure failed"
        outcomes[key] += 1
        weighted[key] += weights.get(rel, 1)
        print(f"{key:45s} {weights.get(rel, 0):3d} fails  {rel}")
    print("\npages:", dict(outcomes))
    print("failed tests:", dict(weighted))


if __name__ == "__main__":
    main()
