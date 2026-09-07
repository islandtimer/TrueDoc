"""Pictures that may hold text on otherwise digital pages: crop them into one-page PDFs for a vision model.

Run 55 (7 September 2026) showed the largest remaining table family on digital pages to be tables
that exist only as pictures: a sideways scan of a vehicle list, a pay-advice screenshot, a map
figure with an embedded table, a web page's people list. The page's own text is exact and stays;
the picture has no text layer, so a model reads the picture alone (D019 applied to a region).

    python bench/gpu/select_regions.py [--min-area 0.10] [--out bench/gpu/crops]

For every benchmark page with a digital text layer (pages not listed in bench/gpu/pages.txt),
every image whose area is at least `--min-area` of the page and which holds fewer than five words
of the page's own text is written as `<out>/<category>/<stem>__r<i>.pdf` (the region embedded at
its own size), and `<out>/manifest.json` maps each crop to its page and bbox in page points.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

import pymupdf

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, REPO)
from truedoc.extract.textlayer import extract_page  # noqa: E402

BENCH = os.path.join(REPO, "bench", "data", "olmocr-bench", "bench_data")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-area", type=float, default=0.10, help="smallest image, as a fraction of the page area")
    ap.add_argument("--max-words-inside", type=int, default=4, help="an image with more of the page's own words inside is a text page with a background")
    ap.add_argument("--out", default=os.path.join(REPO, "bench", "gpu", "crops"))
    ap.add_argument("--failed", default=None, help="a run's failed_tests.jsonl: only look at pages with a failing check (a two-minute pass instead of thirty)")
    args = ap.parse_args()
    listed = {l.split("\t")[0] for l in open(os.path.join(REPO, "bench", "gpu", "pages.txt"), encoding="utf-8") if "\t" in l}
    only: set[str] | None = None
    if args.failed:
        only = set()
        for line in open(args.failed, encoding="utf-8"):
            if line.strip():
                only.add(json.loads(line)["pdf"].replace(".pdf", ""))
    manifest: list[dict] = []
    n_pages = 0
    for pdf in sorted(glob.glob(os.path.join(BENCH, "pdfs", "*", "*.pdf"))):
        cat = os.path.basename(os.path.dirname(pdf))
        stem = os.path.basename(pdf)[:-4]
        if f"{cat}/{stem}" in listed or (only is not None and f"{cat}/{stem}" not in only):
            continue
        doc = pymupdf.open(pdf)
        try:
            page = extract_page(doc[0], 1)
            area = max(1.0, page.width * page.height)
            crops = []
            for img in page.images:
                b = img.bbox
                if b.width * b.height < args.min_area * area or b.width < 40 or b.height < 30:
                    continue
                inside = sum(1 for w in page.words if b.x0 <= w.bbox.cx <= b.x1 and b.y0 <= w.bbox.cy <= b.y1)
                if inside > args.max_words_inside:
                    continue
                if any(c.overlap_fraction(b) > 0.6 for c in crops):
                    continue
                crops.append(b)
            for i, b in enumerate(crops):
                clip = pymupdf.Rect(max(0, b.x0 - 2), max(0, b.y0 - 2), min(page.width, b.x1 + 2), min(page.height, b.y1 + 2))
                out_dir = os.path.join(args.out, cat)
                os.makedirs(out_dir, exist_ok=True)
                name = f"{stem}__r{i}.pdf"
                crop = pymupdf.open()
                cp = crop.new_page(width=clip.width, height=clip.height)
                cp.show_pdf_page(cp.rect, doc, 0, clip=clip)
                crop.save(os.path.join(out_dir, name))
                crop.close()
                manifest.append({"crop": f"{cat}/{name}", "page": f"{cat}/{stem}", "bbox": [round(b.x0, 1), round(b.y0, 1), round(b.x1, 1), round(b.y1, 1)],
                                 "area_share": round(b.width * b.height / area, 3)})
            if crops:
                n_pages += 1
        finally:
            doc.close()
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1)
    by_cat: dict[str, int] = {}
    for m in manifest:
        by_cat[m["page"].split("/")[0]] = by_cat.get(m["page"].split("/")[0], 0) + 1
    print(f"{len(manifest)} crops on {n_pages} digital pages -> {args.out}; by category {by_cat}")


if __name__ == "__main__":
    main()
