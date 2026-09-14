"""For every page without a digital text layer, record the page's own lines in the head and foot
strips: the running-head witness for the model's text.

The witness is the hidden OCR layer where the page has one (kinds ocr, suspect), and our own
engine's lines where it has none (kind none), whether or not the acceptance gate would take
them. Output: JSON {page: {"kind", "height", "top": [[text, y0, y1], ...], "bottom": [...],
"all": n_lines}} for the 281 pages of bench/gpu/pages.txt.

    python witness_census.py <out.json>
"""
import json
import os
import sys
import time

import pymupdf

sys.path.insert(0, ".")
from truedoc.extract.textlayer import extract_page  # noqa: E402
from truedoc.ocr import rapid  # noqa: E402

B = "bench/data/olmocr-bench/bench_data/pdfs"
STRIP = 0.12   # a generous strip: the aligned finder uses 0.09, the header rules a little more
out = {}
t0 = time.time()
pages = [l.rstrip("\n").split("\t") for l in open("bench/gpu/pages.txt", encoding="utf-8") if "\t" in l]
for i, (page_id, kind) in enumerate(pages, 1):
    cat, stem = page_id.split("/", 1)
    pdf = os.path.join(B, cat, stem + ".pdf")
    rec = {"kind": kind, "top": [], "bottom": [], "all": 0, "source": ""}
    try:
        doc = pymupdf.open(pdf)
        pg = doc[0]
        page = extract_page(pg, 1)
        lines = list(page.lines)
        rec["source"] = "layer"
        if kind == "none" or not lines:
            lines, conf, turn = rapid.ocr_page_turn(pg, want_turn=True)
            if turn:
                pg.set_rotation((pg.rotation + turn) % 360)
                lines, conf, _ = rapid.ocr_page_turn(pg, want_turn=False)
            rec["source"] = "ocr"
            rec["conf"] = round(conf, 3)
        H = float(page.height)
        rec["height"] = H
        rec["all"] = len(lines)
        for l in lines:
            text = l.text.strip() if hasattr(l, "text") else " ".join(w.text for w in l.words).strip()
            if not text:
                continue
            if l.bbox.y1 <= STRIP * H:
                rec["top"].append([text, round(l.bbox.y0, 1), round(l.bbox.y1, 1)])
            elif l.bbox.y0 >= (1 - STRIP) * H:
                rec["bottom"].append([text, round(l.bbox.y0, 1), round(l.bbox.y1, 1)])
        doc.close()
    except Exception as e:  # noqa: BLE001
        rec["error"] = repr(e)[:200]
    out[page_id] = rec
    if i % 40 == 0:
        print("%d/%d after %.0fs" % (i, len(pages), time.time() - t0), flush=True)
json.dump(out, open(sys.argv[1], "w", encoding="utf-8"), ensure_ascii=False, indent=0)
n_top = sum(1 for r in out.values() if r["top"]); n_bot = sum(1 for r in out.values() if r["bottom"])
print("done %d pages in %.0fs; pages with head-strip lines %d, foot-strip lines %d, errors %d" % (len(out), time.time() - t0, n_top, n_bot, sum(1 for r in out.values() if "error" in r)))
