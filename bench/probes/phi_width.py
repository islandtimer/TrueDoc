"""Does the glyph width tell TeX's straight phi (cmmi "phi", 0.596 em) from the curly
varphi ("phi1", 0.724 em)? For every arxiv page whose references use one spelling
only, list the widths (bbox width / size) of the phi characters on the page.

    python phi_width.py
"""
import collections
import json
import os
import re

import pymupdf

B = r"bench/data/olmocr-bench/bench_data"
BS = chr(92)
PHI = re.compile(BS + BS + "phi" + BS + "b")
VARPHI = re.compile(BS + BS + "varphi" + BS + "b")

refs = [json.loads(l) for l in open(os.path.join(B, "arxiv_math.jsonl"), encoding="utf-8") if l.strip()]
by_pdf = collections.defaultdict(list)
for r in refs:
    if r.get("math"):
        by_pdf[r["pdf"]].append(r["math"])

rows = []
for pdf, maths in by_pdf.items():
    n_phi = sum(len(PHI.findall(m)) for m in maths)
    n_var = sum(len(VARPHI.findall(m)) for m in maths)
    if not (n_phi or n_var) or (n_phi and n_var):
        continue
    want = "phi" if n_phi else "varphi"
    try:
        doc = pymupdf.open(os.path.join(B, "pdfs", pdf))
        raw = doc[0].get_text("rawdict")
        doc.close()
    except Exception:
        continue
    widths = collections.defaultdict(list)
    for b in raw["blocks"]:
        for l in b.get("lines", []):
            for s in l.get("spans", []):
                for c in s.get("chars", []):
                    if c["c"] in ("φ", "ϕ"):
                        x0, y0, x1, y1 = c["bbox"]
                        widths[(s["font"].split("+")[-1], c["c"])].append(round((x1 - x0) / max(s["size"], 1), 2))
    for key, ws in widths.items():
        rows.append((want, key[0], key[1], sorted(collections.Counter(ws).items())[:4], os.path.basename(pdf)))

for want, font, ch, ws, pdf in sorted(rows):
    print(f"{want:7s} {font:26s} {ch} widths {ws}  {pdf}")
