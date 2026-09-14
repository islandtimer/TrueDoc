"""Print the shape features of every mark candidate on a page.

    python mark_probe.py <pdf> <page> [max_x]
"""
import sys

import pymupdf

from truedoc.marks import _best_template, _candidates, _drop_specks, _erase_ring, _features, _has_ring, _ink, _tight
from truedoc.pipeline import ConvertOptions, process_page

pdf, pno = sys.argv[1], int(sys.argv[2])
max_x = float(sys.argv[3]) if len(sys.argv) > 3 else 1e9
doc = pymupdf.open(pdf)
pdf_page = doc[pno - 1]
page = process_page(pdf_page, pno, ConvertOptions(layout=False, ocr=False, marks=False))
cands = [b for b in _candidates(pdf_page, page, None) if b.x0 <= max_x]
print("candidates:", len(cands))
for b in cands[:14]:
    mask, colour = _ink(pdf_page, b, None)
    if mask is None:
        print("  no ink"); continue
    ring = _has_ring(mask)
    core = _erase_ring(mask) if ring else mask
    tight = _tight(_drop_specks(core))
    f = _features(tight)
    kind, score = _best_template(core)
    print(f"  ({b.x0:.0f},{b.y0:.0f}) {b.width:.1f}pt ring={ring} fill={f['fill']:.2f} ul={f['ul']:.2f} ur={f['ur']:.2f} ll={f['ll']:.2f} lr={f['lr']:.2f} diag={f['diag']:.2f} axis={f['axis']:.2f} -> {kind} {score}")
