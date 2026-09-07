"""Evidence ceiling census (read-only; no conversions).

For every failing present / order / table check of a run, asks two questions:
  1. Is the wanted text in the PDF's OWN raw text layer (PyMuPDF get_text, no TrueDoc)?
  2. Is the wanted text in our output for that page?
and sorts each check into a bucket:
  A  out_empty  : our output is empty (page rejected or unreadable)
  B  in_raw     : wanted text is in the raw layer but not in our output   -> mechanical (we dropped or garbled it)
  C  in_out     : wanted text is in our output, the check still fails     -> mechanical (structure, order, heading)
  D  neither    : page has a layer, wanted text in neither                 -> the layer is wrong (hidden OCR) or the reference is
  E  no layer   : page has no text layer and our OCR did not get it       -> pixel-bound
A check is "in" a text when the official checker's own matching would accept it (same normalisation,
partial_ratio for present/table, fuzzysearch for order).

Run from the repository root:
  .venv/Scripts/python bench/out/swarm/ceiling_census.py [failed_tests.jsonl] [outputs_dir]
Defaults: run 48's failed tests and outputs. Writes bench/out/swarm/ceiling_results.json.
Written for the lateral-thinking round of 7 September 2026 (ideas_contrarian.md).
"""
import collections
import json
import os
import sys
import warnings

warnings.filterwarnings("ignore")
import fitz  # PyMuPDF
from fuzzysearch import find_near_matches
from olmocr.bench.tests import normalize_text
from rapidfuzz import fuzz

FAILED = sys.argv[1] if len(sys.argv) > 1 else "bench/runs/truedoc47-20260907-090140/failed_tests.jsonl"
OUTS = sys.argv[2] if len(sys.argv) > 2 else "bench/data/olmocr-bench/bench_data/truedoc47"
PDFS = "bench/data/olmocr-bench/bench_data/pdfs"
RESULTS = "bench/out/swarm/ceiling_results.json"
SLASH = chr(92)


def present(query, content, max_diffs, case_sensitive=True):
    q, c = normalize_text(query), normalize_text(content)
    if not case_sensitive:
        q, c = q.lower(), c.lower()
    if not q or not c:
        return False, len(q)
    ratio = fuzz.partial_ratio(q, c) / 100.0
    return ratio >= 1.0 - max_diffs / len(q), round((1.0 - ratio) * len(q))


def near(query, content, max_diffs):
    q, c = normalize_text(query), normalize_text(content)
    return bool(q and c and find_near_matches(q, c, max_l_dist=max_diffs))


def raw_text(pdfrel, pageno):
    try:
        return fitz.open(os.path.join(PDFS, pdfrel))[pageno - 1].get_text("text")
    except Exception:
        return ""


def our_output(pdfrel):
    sec, name = pdfrel.split("/")
    path = os.path.join(OUTS, sec, f"{name[:-4]}_pg1_repeat1.md")
    if not os.path.exists(path):
        return None
    txt = open(path, encoding="utf-8", errors="replace").read()
    if txt.startswith("---"):
        i = txt.find("\n---", 3)
        if i > 0:
            txt = txt[i + 4:]
    return txt


results = []
for line in open(FAILED, encoding="utf-8"):
    line = line.strip()
    if not line:
        continue
    d = json.loads(line)
    t = d["type"]
    if t not in ("present", "order", "table"):
        continue
    pdfrel = d["pdf"].replace(SLASH, "/")
    raw = raw_text(pdfrel, d.get("page", 1))
    out = our_output(pdfrel) or ""
    md = d.get("max_diffs", 0)
    rec = dict(sec=pdfrel.split("/")[0], pdf=pdfrel, id=d["id"], type=t,
               out_empty=not out.strip(), raw_empty=len(raw.strip()) < 20)
    if t == "present":
        cs = d.get("case_sensitive", True)
        rec["in_raw"], rec["e_raw"] = present(d["text"], raw, md, cs)
        rec["in_out"], rec["e_out"] = present(d["text"], out, md, cs)
    elif t == "order":
        rec["in_raw"] = near(d["before"], raw, md) and near(d["after"], raw, md)
        rec["in_out"] = near(d["before"], out, md) and near(d["after"], out, md)
        rec["e_raw"] = max(present(d["before"], raw, md)[1], present(d["after"], raw, md)[1])
        rec["e_out"] = max(present(d["before"], out, md)[1], present(d["after"], out, md)[1])
    else:
        cell = d.get("cell") or ""
        rec["in_raw"], rec["e_raw"] = present(cell, raw, md)
        rec["in_out"], rec["e_out"] = present(cell, out, md)
    results.append(rec)

json.dump(results, open(RESULTS, "w"), indent=1)

print(f'{"section":16s} {"type":8s} {"total":>5s} {"A_empty":>7s} {"B_raw":>6s} {"C_out":>6s} {"D_neither":>9s} {"E_noLayer":>9s}')
for sec, t in sorted({(r["sec"], r["type"]) for r in results}):
    rs = [r for r in results if r["sec"] == sec and r["type"] == t]
    a = [r for r in rs if r["out_empty"]]
    rest = [r for r in rs if not r["out_empty"]]
    c = [r for r in rest if r["in_out"]]
    b = [r for r in rest if not r["in_out"] and r["in_raw"]]
    e = [r for r in rest if not r["in_out"] and not r["in_raw"] and r["raw_empty"]]
    dd = [r for r in rest if not r["in_out"] and not r["in_raw"] and not r["raw_empty"]]
    print(f"{sec:16s} {t:8s} {len(rs):5d} {len(a):7d} {len(b):6d} {len(c):6d} {len(dd):9d} {len(e):9d}")

print("\nBucket D, edits between the wanted text and its nearest match in the raw layer (small = artefact or 1-2 wrong letters):")
for sec in ("multi_column", "long_tiny_text", "tables"):
    hist = collections.Counter()
    for r in results:
        if r["sec"] == sec and not r["out_empty"] and not r["in_out"] and not r["in_raw"] and not r["raw_empty"]:
            e = r["e_raw"]
            hist["0-1" if e <= 1 else "2-3" if e <= 3 else "4-6" if e <= 6 else "7-15" if e <= 15 else "16+"] += 1
    print(f"  {sec:16s}", dict(sorted(hist.items())))
print(f"\nPer-check results written to {RESULTS}")
