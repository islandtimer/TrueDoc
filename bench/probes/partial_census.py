"""Sort the pages a run leaves blank into "typed but shaky" and "gibberish".

For every page of a candidate whose output is empty (under 20 characters, the merge's
definition), read it with our own OCR engine and record what the acceptance gate saw:
confidence, word-likeness, language-likeness, numeric share, line count, and the first
words. Then run the page's own benchmark checks (presence, order, table) against that
shaky reading, so the value of keeping it is counted per page. The baseline check (one per
page, failing while the page is empty) is not in the jsonl files; it is counted apart.

Usage: python partial_census.py <candidate> <out.txt>
"""
import glob
import os
import sys
import time

import pymupdf
from olmocr.bench.tests import load_tests

sys.path.insert(0, ".")
from truedoc.ocr import rapid  # noqa: E402

B = "bench/data/olmocr-bench/bench_data"
cand = sys.argv[1]
out_path = sys.argv[2]
out = open(out_path, "w", encoding="utf-8")


def say(*a):
    print(*a, file=out, flush=True)


tests_by_pdf = {}
for subset in ("arxiv_math", "headers_footers", "long_tiny_text", "multi_column", "old_scans", "old_scans_math", "table_tests"):
    for t in load_tests(os.path.join(B, subset + ".jsonl")):
        tests_by_pdf.setdefault(os.path.basename(t.pdf), []).append(t)

rows = []
t0 = time.time()
for md in sorted(glob.glob(os.path.join(B, cand, "*", "*.md"))):
    if len(open(md, encoding="utf-8").read().strip()) >= 20:
        continue
    subset = os.path.basename(os.path.dirname(md))
    stem = os.path.basename(md).replace("_pg1_repeat1.md", "")
    pdf = os.path.join(B, "pdfs", subset, stem + ".pdf")
    try:
        doc = pymupdf.open(pdf)
        page = doc[0]
        lines, conf, turn = rapid.ocr_page_turn(page, want_turn=True)
        if turn:
            page.set_rotation((page.rotation + turn) % 360)
            lines, conf, _ = rapid.ocr_page_turn(page, want_turn=False)
        doc.close()
    except Exception as e:  # noqa: BLE001
        say("ERROR", subset, stem, repr(e))
        continue
    if not lines:
        rows.append((subset, stem, 0.0, 0.0, 0.0, 0.0, 0, 0, turn, 0, 0, ""))
        continue
    wordlike = rapid._looks_like_text(lines)
    language_like = rapid._looks_like_language(lines)
    tokens = [w.text for l in lines for w in l.words]
    numeric = sum(1 for t in tokens if rapid._NUMBERISH.fullmatch(t)) / max(1, len(tokens))
    text = "\n".join(l.text for l in sorted(lines, key=lambda l: (round(l.bbox.y0 / 8.0), l.bbox.x0)))
    ts = tests_by_pdf.get(stem + ".pdf", [])
    won = sum(1 for t in ts if t.run(text)[0])
    sample = " ".join(text.split())[:90]
    rows.append((subset, stem, conf, wordlike, language_like, numeric, len(lines), len(tokens), turn, len(ts), won, sample))
    say("%-16s %-22s conf %.3f word %.2f lang %.2f num %.2f lines %3d checks %2d/%2d turn %d | %s" % (subset, stem[:22], conf, wordlike, language_like, numeric, len(lines), won, len(ts), turn, sample))

say("")
say("elapsed %.0fs, %d blank pages read" % (time.time() - t0, len(rows)))


def bucket(r):
    conf, word, lang = r[2], r[3], r[4]
    if r[6] == 0:
        return "nothing read"
    if conf >= 0.6 and (word >= 0.35 or lang >= 0.5):
        return "typed but shaky"
    return "gibberish"


for name in ("typed but shaky", "gibberish", "nothing read"):
    sel = [r for r in rows if bucket(r) == name]
    say("%-16s pages %3d  checks held %4d  checks the shaky read would pass %3d" % (name, len(sel), sum(r[9] for r in sel), sum(r[10] for r in sel)))
    by = {}
    for r in sel:
        by[r[0]] = by.get(r[0], 0) + 1
    say("    by section:", dict(sorted(by.items())))
say("")
say("confidence bands (all blank pages):")
for lo, hi in ((0.0, 0.5), (0.5, 0.6), (0.6, 0.7), (0.7, 0.75), (0.75, 0.8), (0.8, 1.01)):
    sel = [r for r in rows if lo <= r[2] < hi]
    say("  %.2f-%.2f: %3d pages, checks held %4d, would pass %3d" % (lo, hi, len(sel), sum(r[9] for r in sel), sum(r[10] for r in sel)))
out.close()
print("wrote", out_path)
