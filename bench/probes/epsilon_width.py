"""Does the glyph width tell TeX's lunate epsilon (cmmi "epsilon", \\epsilon) from the
curly one ("epsilon1", \\varepsilon)? For every arxiv page whose references use one
spelling only, list the widths (bbox width / size) and the fonts of the epsilon characters.

    python epsilon_width.py
"""
import collections
import json
import os
import re

import pymupdf

B = r"bench/data/olmocr-bench/bench_data"
BS = chr(92)
EPS = re.compile(BS + BS + "epsilon" + BS + "b")
VAREPS = re.compile(BS + BS + "varepsilon" + BS + "b")

refs = [json.loads(l) for l in open(os.path.join(B, "arxiv_math.jsonl"), encoding="utf-8") if l.strip()]
by_pdf = collections.defaultdict(list)
for r in refs:
    if r.get("math"):
        by_pdf[r["pdf"]].append(r["math"])

rows = []
for pdf, maths in by_pdf.items():
    n_e = sum(len(EPS.findall(m)) for m in maths)
    n_v = sum(len(VAREPS.findall(m)) for m in maths)
    if not (n_e or n_v) or (n_e and n_v):
        continue
    want = "epsilon" if n_e else "varepsilon"
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
                    if c["c"] in ("ε", "ϵ", "ǫ"):
                        x0, y0, x1, y1 = c["bbox"]
                        widths[(s["font"].split("+")[-1], c["c"])].append(round((x1 - x0) / max(s["size"], 1), 2))
    for key, ws in widths.items():
        rows.append((want, key[0], key[1], sorted(collections.Counter(ws).items())[:4], os.path.basename(pdf)))

for want, font, ch, ws, pdf in sorted(rows):
    print(f"{want:10s} {font:26s} {ch} U+{ord(ch):04X} widths {ws}  {pdf}")
