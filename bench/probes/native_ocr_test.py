"""The one-hour test: does OCR at the scan's own resolution read more than the capped pass?

For each test page: (a) the current reader (300 dpi, capped at 2,000 px on the long side);
(b) the page rendered at the embedded image's own pixel size and read in full-width strips
2,000 px tall with a 200 px overlap, a line kept from the strip whose core holds its centre.
Each reading is scored against the page's benchmark checks (text presence, order, absence,
table) as a plain markdown of the lines in top-to-bottom order, and against run 48's actual
output for the page. Nothing here touches the repository.
"""
import glob
import json
import os
import sys
import time
from collections import Counter

import numpy as np
import pymupdf
from olmocr.bench.tests import load_tests

sys.path.insert(0, ".")
from truedoc.ocr import rapid

B = "bench/data/olmocr-bench/bench_data"
OUT48 = os.path.join(B, "truedoc47")
STRIP = 2000
OVERLAP = 200

PAGES = [("old_scans", n + ".pdf") for n in ["43", "30", "46", "17", "75", "74", "70", "10", "24", "63"]]
PAGES += [("long_tiny_text", n) for n in ["17_pg4_pg1.pdf", "17_pg17_pg1.pdf", "17_pg86_pg1.pdf"]]
PAGES += [("tables", "11e12a3d")]
if len(sys.argv) > 1:
    PAGES = [p for p in PAGES if any(a in p[1] for a in sys.argv[1:])]


def tests_for(subset, name):
    fname = "table_tests" if subset == "tables" else subset
    tests = load_tests(os.path.join(B, fname + ".jsonl"))
    return [t for t in tests if os.path.basename(t.pdf).startswith(name.replace(".pdf", ""))]


def native_scale(page):
    best = 0.0
    for info in page.get_image_info():
        r = pymupdf.Rect(info["bbox"])
        if r.width <= 0:
            continue
        s = info["width"] / r.width
        if r.width * r.height > 0.3 * page.rect.width * page.rect.height:
            best = max(best, s)
    return best


def read_strips(page, scale):
    engine = rapid._get_engine()
    pix = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), colorspace=pymupdf.csRGB, alpha=False)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
    H, W = img.shape[:2]
    lines = []
    y = 0
    n_strips = 0
    while True:
        y0 = y
        y1 = min(H, y0 + STRIP)
        core0 = 0 if y0 == 0 else y0 + OVERLAP // 2
        core1 = H if y1 == H else y1 - OVERLAP // 2
        result, _ = engine(np.ascontiguousarray(img[y0:y1]))
        n_strips += 1
        for box, text, score in result or []:
            score = float(score)
            text = str(text).strip()
            if not text or score < rapid._MIN_SCORE:
                continue
            ys = [p[1] + y0 for p in box]
            xs = [p[0] for p in box]
            cy = sum(ys) / 4.0
            if not (core0 <= cy < core1):
                continue
            lines.append((min(ys) / scale, min(xs) / scale, max(ys) / scale, max(xs) / scale, text, score))
        if y1 >= H:
            break
        y = y1 - OVERLAP
    return lines, (W, H, n_strips)


def as_markdown(lines):
    # top-to-bottom, left-to-right; lines on one baseline joined
    lines = sorted(lines, key=lambda l: (round(l[0] / 8.0), l[1]))
    return "\n".join(l[4] for l in lines)


def score(tests, md):
    by_type = Counter()
    tot = Counter()
    for t in tests:
        k = type(t).__name__.replace("Test", "")
        tot[k] += 1
        ok, _ = t.run(md)
        if ok:
            by_type[k] += 1
    return " ".join("%s %d/%d" % (k, by_type[k], tot[k]) for k in sorted(tot))


for subset, name in PAGES:
    paths = glob.glob(os.path.join(B, "pdfs", subset, name + "*")) if not name.endswith(".pdf") else [os.path.join(B, "pdfs", subset, name)]
    if not paths or not os.path.exists(paths[0]):
        print(subset, name, "missing")
        continue
    path = paths[0]
    tests = tests_for(subset, os.path.basename(path))
    doc = pymupdf.open(path)
    page = doc[0]
    scale = native_scale(page)
    t0 = time.time()
    base_lines, base_conf, _ = rapid.ocr_page_turn(page, want_turn=False)
    t_base = time.time() - t0
    base_md = "\n".join(l.text for l in sorted(base_lines, key=lambda l: (round(l.bbox.y0 / 8.0), l.bbox.x0)))
    t0 = time.time()
    nat_lines, (W, H, n_strips) = read_strips(page, scale) if scale else ([], (0, 0, 0))
    t_nat = time.time() - t0
    nat_md = as_markdown(nat_lines)
    nat_conf = sum(l[5] for l in nat_lines) / len(nat_lines) if nat_lines else 0.0
    stem = os.path.basename(path).replace(".pdf", "")
    outs = glob.glob(os.path.join(OUT48, subset, stem + "_pg1_repeat1.md"))
    run48 = open(outs[0], encoding="utf-8").read() if outs else ""
    print("%s/%s  native scale %.2f -> %dx%d px, %d strips" % (subset, stem, scale, W, H, n_strips))
    print("   run 48 output : %5d chars                       %s" % (len(run48), score(tests, run48)))
    print("   capped reader : %5d chars conf %.3f %4d lines %5.0fs %s" % (len(base_md), base_conf, len(base_lines), t_base, score(tests, base_md)))
    print("   native strips : %5d chars conf %.3f %4d lines %5.0fs %s" % (len(nat_md), nat_conf, len(nat_lines), t_nat, score(tests, nat_md)))
    sys.stdout.flush()
    doc.close()
