"""Dense model-read pages cut into overlapping bands, for a vision model to read a piece at a time.

Run 62's census of the 281 pages a model reads (D019) put 385 failing checks there, worth about
9.2 points of the benchmark's 100. Sorted by what the model's own reading shows:

    the model read the text but garbled it        219 checks   a better model would fix these
    the model never read that text                 77 checks   the page was too dense to finish
    the model read it exactly, in the wrong order  44 checks   the page's columns were mixed

The 77 misses cluster on the densest pages (a maths textbook page with eleven, a dictionary page
with five). A page cut into bands gives the model a fifth of the text at a time, which is the
cheapest thing to try before renting a bigger model; the bands overlap so a line split across a
cut survives whole in one of them.

    python bench/gpu/select_bands.py --failed bench/runs/<run>/failed_tests.jsonl

writes `<out>/<category>/<stem>__b<i>.pdf` (one page each, the band at its own size) and
`<out>/manifest.json` mapping each band to its page, its bbox in page points, and its order.
Read them on the GPU exactly as session 2 read whole pages (bench/gpu/README.md), place the
readings as a candidate folder, then `bench/gpu/merge_bands.py` stitches each page's bands back
into one reading, dropping the lines the overlap repeats.

This is an experiment, not a decision: the pages chosen are ones whose whole-page readings we
already hold, so the two readings can be scored against each other on the same checks.
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import os
import sys

import pymupdf

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "bench"))

BENCH = os.path.join(REPO, "bench", "data", "olmocr-bench", "bench_data")


def reading_for(pdf_rel: str, folder: str = "olmocr2b") -> str | None:
    sub, name = pdf_rel.split("/")
    for pat in (name[:-4] + "_pg1_repeat1.md", name[:-4] + "_pg1.md", name[:-4] + ".md"):
        f = os.path.join(BENCH, folder, sub, pat)
        if os.path.exists(f):
            return open(f, encoding="utf-8").read()
    return None


def missed_pages(failed_path: str, limit: int) -> list[tuple[str, int]]:
    """Pages whose failing checks name text the model's reading does not hold, worst first."""
    from fuzzysearch import find_near_matches
    from holdout_score import is_held_out
    from olmocr.bench.tests import load_tests, normalize_text

    failed = set()
    for line in open(failed_path, encoding="utf-8"):
        if line.strip():
            t = json.loads(line)
            failed.add((t["pdf"], t["id"]))
    misses: collections.Counter = collections.Counter()
    for sub in ("old_scans", "old_scans_math", "long_tiny_text", "multi_column", "headers_footers", "table_tests"):
        name = "tables" if sub == "table_tests" else sub
        for t in load_tests(os.path.join(BENCH, sub + ".jsonl")):
            if (t.pdf, t.id) not in failed or is_held_out(t.pdf):
                continue
            raw = reading_for(t.pdf)
            if raw is None:
                continue
            anchor = normalize_text(getattr(t, "text", None) or getattr(t, "before", None) or getattr(t, "math", None) or "")[:60]
            if not anchor:
                continue
            if not find_near_matches(anchor, normalize_text(raw), max_l_dist=max(1, len(anchor) // 4)):
                misses[t.pdf] += 1
    return misses.most_common(limit)


def bands_for(page: "pymupdf.Page", n: int, overlap: float) -> list[pymupdf.Rect]:
    r = page.rect
    height = r.height / n
    out = []
    for i in range(n):
        y0 = r.y0 + i * height - (overlap * height if i else 0.0)
        y1 = r.y0 + (i + 1) * height + (overlap * height if i < n - 1 else 0.0)
        out.append(pymupdf.Rect(r.x0, max(r.y0, y0), r.x1, min(r.y1, y1)))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--failed", required=True, help="a run's failed_tests.jsonl (chooses the pages the model missed text on)")
    ap.add_argument("--pages", type=int, default=24, help="how many pages to cut (worst first)")
    ap.add_argument("--bands", type=int, default=3, help="bands per page")
    ap.add_argument("--overlap", type=float, default=0.08, help="each band's overlap into its neighbour, as a fraction of a band's height")
    ap.add_argument("--out", default=os.path.join(REPO, "bench", "gpu", "bands"))
    ap.add_argument("--also-whole", default="", help="comma-separated page names (or name prefixes) to send whole, one crop each: "
                                                    "pages whose table is a vector drawing, which the picture-region tool cannot crop "
                                                    "because there is no image object to find (f5e5d540, fbeb6edc and six more after run 62)")
    args = ap.parse_args()

    chosen = missed_pages(args.failed, args.pages)
    whole: set[str] = set()
    if args.also_whole:
        wanted = [w.strip() for w in args.also_whole.split(",") if w.strip()]
        for pdf in glob.glob(os.path.join(BENCH, "pdfs", "*", "*.pdf")):
            rel = os.path.basename(os.path.dirname(pdf)) + "/" + os.path.basename(pdf)
            if any(os.path.basename(pdf).startswith(w) for w in wanted):
                whole.add(rel)
        chosen = chosen + [(rel, 0) for rel in sorted(whole) if rel not in {c for c, _ in chosen}]
    manifest = []
    for rel, n_missed in chosen:
        sub, name = rel.split("/")
        src = glob.glob(os.path.join(BENCH, "pdfs", sub, name))
        if not src:
            continue
        doc = pymupdf.open(src[0])
        page = doc[0]
        os.makedirs(os.path.join(args.out, sub), exist_ok=True)
        rects = [page.rect] if rel in whole else bands_for(page, args.bands, args.overlap)
        for i, rect in enumerate(rects):
            crop = pymupdf.open()
            new = crop.new_page(width=rect.width, height=rect.height)
            new.show_pdf_page(new.rect, doc, 0, clip=rect)
            stem = name[:-4] + "__b%d" % i
            out_pdf = os.path.join(args.out, sub, stem + ".pdf")
            crop.save(out_pdf)
            crop.close()
            manifest.append({"crop": f"{sub}/{stem}.pdf", "page": rel, "order": i,
                             "bbox": [rect.x0, rect.y0, rect.x1, rect.y1], "missed_checks": n_missed})
        doc.close()
    with open(os.path.join(args.out, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1)
    print(f"{len(chosen)} pages, {len(manifest)} bands written to {args.out}")
    print("worst pages:", ", ".join(f"{p.split('/')[-1]} ({n})" for p, n in chosen[:8]))


if __name__ == "__main__":
    main()
