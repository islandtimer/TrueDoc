"""Do PyMuPDF and PDFium agree about what is drawn on a page? (M18, D022)

The rulings, the picture regions, the small shapes the mark reader hunts for and the covers that
hide text all come from the same question - what is on this page, and in what order. D022 asks for
a quantity the two libraries must agree on before the answer is taken from a different one, and
here that quantity is the set of drawn shapes and where they sit.

    python bench/tools/objects_compare.py [--pages 60] [--seed 5]

One systematic difference is expected and is reported separately: PDFium's bounds for a stroked
path include the width of the stroke, where PyMuPDF reports the path itself, so a hairline comes
back about half a stroke wider on each side. The run reports agreement with and without allowing
for it, so the choice of whether to compensate is made on a number.
"""
from __future__ import annotations

import argparse
import glob
import os
import random
import statistics

import pymupdf

from truedoc.extract.pdfium_objects import page_objects

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BENCH = os.path.join(REPO, "bench", "data", "olmocr-bench", "bench_data")


def _shrink(o) -> tuple:
    """A stroked path's bounds pulled in by its stroke, to match PyMuPDF's path rect.

    Measured on a 2pt rule: PyMuPDF gives (20, 100, 180, 100) and PDFium (18, 98, 182, 102), so the
    ink extends a full stroke width beyond the path on each side, not half of one.
    """
    h = o.stroke_width if o.stroke is not None else 0.0
    x0, y0, x1, y1 = o.bbox
    return (x0 + h, y0 + h, max(x0 + h, x1 - h), max(y0 + h, y1 - h))


def _near(a: tuple, b: tuple, tol: float) -> bool:
    return all(abs(p - q) <= tol for p, q in zip(a, b))


def _match(mine: list, theirs: list, tol: float) -> int:
    """How many of `theirs` have a partner in `mine`, each used once.

    Bucketed by rounded top-left corner rather than compared pair by pair: a generated page can
    carry tens of thousands of paths, and the obvious nested loop turns that into an afternoon.
    """
    buckets: dict[tuple, list] = {}
    step = max(tol, 0.5) * 2.0
    for m in mine:
        buckets.setdefault((int(m[0] // step), int(m[1] // step)), []).append(m)
    hits = 0
    for t in theirs:
        cx, cy = int(t[0] // step), int(t[1] // step)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                pool = buckets.get((cx + dx, cy + dy))
                if not pool:
                    continue
                for i, m in enumerate(pool):
                    if _near(m, t, tol):
                        pool.pop(i)
                        hits += 1
                        break
                else:
                    continue
                break
            else:
                continue
            break
    return hits


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=60)
    ap.add_argument("--seed", type=int, default=5)
    ap.add_argument("--tol", type=float, default=1.0)
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(BENCH, "pdfs", "*", "*.pdf")))
    random.Random(args.seed).shuffle(files)

    counts = {"pdfium paths": 0, "mupdf paths": 0, "pdfium images": 0, "mupdf images": 0}
    matched_raw = matched_shrunk = total_paths = 0
    matched_img = total_img = 0
    used = 0
    page_gaps: list[float] = []
    per_page: list[tuple] = []
    for path in files[:args.pages]:
        try:
            objs = page_objects(path, 1)
            doc = pymupdf.open(path)
            page = doc[0]
            mu_paths = [tuple(float(v) for v in d["rect"]) for d in page.get_drawings()]
            mu_imgs = [tuple(float(v) for v in i["bbox"]) for i in page.get_image_info()]
            doc.close()
        except Exception:
            continue
        if objs is None:
            continue
        used += 1
        pf_paths = [o for o in objs if o.kind == "path"]
        pf_imgs = [o.bbox for o in objs if o.kind == "image"]
        counts["pdfium paths"] += len(pf_paths)
        counts["mupdf paths"] += len(mu_paths)
        counts["pdfium images"] += len(pf_imgs)
        counts["mupdf images"] += len(mu_imgs)
        total_paths += len(mu_paths)
        raw = _match([o.bbox for o in pf_paths], mu_paths, args.tol)
        shrunk = _match([_shrink(o) for o in pf_paths], mu_paths, args.tol)
        matched_raw += raw
        matched_shrunk += shrunk
        total_img += len(mu_imgs)
        matched_img += _match(pf_imgs, mu_imgs, args.tol)
        if mu_paths:
            page_gaps.append(abs(len(pf_paths) - len(mu_paths)) / len(mu_paths))
            per_page.append((max(raw, shrunk) / len(mu_paths), len(mu_paths), len(pf_paths),
                             os.path.basename(path)))

    print(f"{used} pages\n")
    for k, v in counts.items():
        print(f"  {k:16s}{v:8d}")
    print()
    if total_paths:
        print(f"  paths matched within {args.tol}pt, PDFium bounds as they come : "
              f"{matched_raw}/{total_paths} = {matched_raw / total_paths:.3f}")
        print(f"  paths matched within {args.tol}pt, pulled in by half a stroke  : "
              f"{matched_shrunk}/{total_paths} = {matched_shrunk / total_paths:.3f}")
    if total_img:
        print(f"  images matched within {args.tol}pt                            : "
              f"{matched_img}/{total_img} = {matched_img / total_img:.3f}")
    if page_gaps:
        print(f"\n  per-page difference in how many paths were found: median "
              f"{statistics.median(page_gaps):.3f}, worst {max(page_gaps):.3f}")
    if per_page:
        rates = sorted(r for r, _, _, _ in per_page)
        print(f"\n  per-page path match rate: median {statistics.median(rates):.3f}, "
              f"p10 {rates[int(0.1 * len(rates))]:.3f}, worst {rates[0]:.3f}")
        print(f"  pages at or above 0.95: {sum(1 for r in rates if r >= 0.95)}/{len(rates)}")
        print("\n  worst pages (match rate, mupdf paths, pdfium paths):")
        for rate, nm, npf, name in sorted(per_page)[:6]:
            print(f"    {rate:.3f}  {nm:7d} {npf:7d}  {name[:52]}")


if __name__ == "__main__":
    main()
