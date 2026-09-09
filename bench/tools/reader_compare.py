"""Does PDFium give us the same characters, in the same order, in the same places? (M18, D007)

The 8 September census compared the two readers' *text* and found them equal on all but about
twenty of the 1,403 pages. It never compared **geometry**, and every stage after extraction - line
grouping, columns, reading order, tables, superscripts - is built on the character boxes. If the
boxes disagree, the swap is not a swap but a rewrite of everything downstream.

Three things per page, each of which would sink the swap on its own:

  characters   the same glyphs, ignoring the spaces PDFium generates and PyMuPDF materialises
  order        the same reading order, which is what block and column detection inherits
  geometry     the same boxes, measured as the median and 95th percentile of the difference

PDFium is asked for its *loose* box, which is the font-metric box PyMuPDF reports by default. Its
tight box is the glyph's ink extent - what PyMuPDF only gives through a second, slower pass with
TEXT_ACCURATE_BBOXES, which the formula stage needs for tall brackets. That the tight box comes
free is an argument for the swap rather than against it.

    python bench/tools/reader_compare.py [--limit N] [--category arxiv_math]
"""
from __future__ import annotations

import argparse
import glob
import os
import statistics
import sys

import pymupdf

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from truedoc.extract import pdfium_reader as pr  # noqa: E402

B = "bench/data/olmocr-bench/bench_data/pdfs"


def mupdf_chars(page):
    flags = pymupdf.TEXTFLAGS_RAWDICT & ~pymupdf.TEXT_PRESERVE_LIGATURES | pymupdf.TEXT_MEDIABOX_CLIP
    try:
        raw = page.get_text("rawdict", flags=flags)
    except Exception:
        return []
    return [(ch["c"], ch["bbox"])
            for b in raw.get("blocks", []) if b.get("type") == 0
            for l in b.get("lines", []) for sp in l.get("spans", []) for ch in sp.get("chars", [])
            if not ch.get("c", " ").isspace()]


def compare(path: str) -> dict | None:
    try:
        doc = pymupdf.open(path)
        page = doc[0]
        mu = mupdf_chars(page)
        doc.close()
        pf = [c for c in pr.read(path, 0, loose=True) if not c.text.isspace()]
    except Exception as exc:
        return {"error": str(exc)[:60]}
    if not mu and not pf:
        return None                      # a scan: neither reader sees text, nothing to compare
    out = {"mupdf": len(mu), "pdfium": len(pf)}
    n = min(len(mu), len(pf))
    if not n:
        return out
    # Order has to be measured by alignment, not position: a single character inserted early
    # shifts every position after it, and a position-wise comparison then reports near-zero
    # agreement on two readings that are in fact identical. That mistake made a page whose first
    # sixty characters match exactly score 0.036.
    import difflib

    a = "".join(t for t, _b in mu)
    b_ = "".join(c.text for c in pf)
    sm = difflib.SequenceMatcher(None, a, b_, autojunk=False)
    blocks = sm.get_matching_blocks()
    out["order"] = sum(bl.size for bl in blocks) / max(len(a), len(b_), 1)
    # Geometry is compared only on characters the alignment pairs up, for the same reason.
    dx, dy = [], []
    for bl in blocks:
        for k in range(bl.size):
            mb = mu[bl.a + k][1]
            pc = pf[bl.b + k]
            dx.append(max(abs(pc.x0 - mb[0]), abs(pc.x1 - mb[2])))
            dy.append(max(abs(pc.y0 - mb[1]), abs(pc.y1 - mb[3])))
    if dx:
        out["dx_median"] = statistics.median(dx)
        out["dx_p95"] = sorted(dx)[int(0.95 * (len(dx) - 1))]
        out["dy_median"] = statistics.median(dy)
        out["dy_p95"] = sorted(dy)[int(0.95 * (len(dy) - 1))]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--category", default="")
    args = ap.parse_args()
    pat = os.path.join(B, args.category or "*", "*.pdf")
    pdfs = sorted(glob.glob(pat))
    if args.limit:
        pdfs = pdfs[:: max(1, len(pdfs) // args.limit)][: args.limit]
    rows, scans, errors = [], 0, 0
    for p in pdfs:
        r = compare(p)
        if r is None:
            scans += 1
            continue
        if "error" in r:
            errors += 1
            continue
        r["page"] = os.path.relpath(p, B)
        rows.append(r)
    print("pages with text compared: %d   (scans skipped %d, errors %d)" % (len(rows), scans, errors))
    if not rows:
        return
    same_count = [r for r in rows if r["mupdf"] == r["pdfium"]]
    print("same character count: %d of %d (%.0f%%)" % (len(same_count), len(rows), 100.0 * len(same_count) / len(rows)))
    orders = [r["order"] for r in rows if "order" in r]
    print("reading order agreement: median %.4f, worst %.3f" % (statistics.median(orders), min(orders)))
    for key in ("dx_median", "dx_p95", "dy_median", "dy_p95"):
        v = [r[key] for r in rows if key in r]
        if v:
            print("  %-10s median %.3f pt   p90 %.3f   worst %.2f" % (key, statistics.median(v), sorted(v)[int(0.9 * (len(v) - 1))], max(v)))
    print()
    print("worst pages by character-count difference:")
    for r in sorted(rows, key=lambda r: -abs(r["mupdf"] - r["pdfium"]))[:8]:
        print("   %-52s mupdf %5d  pdfium %5d  order %.2f" % (r["page"][:52], r["mupdf"], r["pdfium"], r.get("order", -1)))
    print()
    print("worst pages by reading-order disagreement:")
    for r in sorted(rows, key=lambda r: r.get("order", 1))[:8]:
        print("   %-52s order %.3f  (mupdf %d, pdfium %d)" % (r["page"][:52], r.get("order", -1), r["mupdf"], r["pdfium"]))


if __name__ == "__main__":
    main()
