"""Second witness pass: OCR the head and foot strips of layer pages whose layer leaves a strip empty.

A hidden layer sometimes covers only part of the page (a publisher's download stamp at the foot
of an otherwise bare scan: the French journal page of the header losses). Where witness.json
has no top or no bottom lines for a layer-source page, run our engine on that strip alone and
add what it reads (source "ocr-strip"). Writes witness2.json.

    python witness_strips.py witness.json witness2.json
"""
import json
import os
import sys
import time

import pymupdf

sys.path.insert(0, ".")
from truedoc.model import BBox  # noqa: E402
from truedoc.ocr import rapid  # noqa: E402
from truedoc.vision.witness import STRIP  # noqa: E402

B = "bench/data/olmocr-bench/bench_data/pdfs"
w = json.load(open(sys.argv[1], encoding="utf-8"))
t0 = time.time()
added_top = added_bottom = pages = 0
for page_id, rec in w.items():
    if rec.get("source") != "layer" or (rec["top"] and rec["bottom"]):
        continue
    cat, stem = page_id.split("/", 1)
    doc = pymupdf.open(os.path.join(B, cat, stem + ".pdf"))
    pg = doc[0]
    H, W = float(pg.rect.height), float(pg.rect.width)
    pages += 1
    # The engine misses text near a crop's edge: read a taller crop, keep the strip's lines.
    if not rec["top"]:
        lines, conf, _ = rapid.ocr_region(pg, BBox(0.0, 0.0, W, 2 * STRIP * H))
        lines = [l for l in lines if l.bbox.y1 <= STRIP * H]
        for l in lines:
            rec["top"].append([l.text.strip(), round(l.bbox.y0, 1), round(l.bbox.y1, 1)])
        added_top += len(lines)
    if not rec["bottom"]:
        lines, conf, _ = rapid.ocr_region(pg, BBox(0.0, (1 - 2 * STRIP) * H, W, H))
        lines = [l for l in lines if l.bbox.y0 >= (1 - STRIP) * H]
        for l in lines:
            rec["bottom"].append([l.text.strip(), round(l.bbox.y0, 1), round(l.bbox.y1, 1)])
        added_bottom += len(lines)
    rec["strip_ocr"] = True
    doc.close()
json.dump(w, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print("layer pages with an empty strip: %d; strip lines added: top %d, bottom %d; %.0fs" % (pages, added_top, added_bottom, time.time() - t0))
