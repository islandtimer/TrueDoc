"""For every page of the tables work list: each failing check, and what the benchmark's checker says about it.

The work list is what `tables_gap_against_pro.py` writes - the table checks of tuned-on digital pages that TrueDoc
fails and Infinity-Parser2-Pro passes. Sorting them into kinds starts from the checker's own words ("no cell
matching ...", "relationships were not satisfied: ..."), then the page.

usage (repo root, the project's venv): tables_gap_dossier.py <work list json> [candidate folder name, default truedoc97]
"""
import collections
import glob
import json
import os
import sys

import difflib
import re

from olmocr.bench.tests import load_tests


def _cells(md):
    """Every table cell we wrote, markdown or HTML, as plain text."""
    out = []
    for line in md.splitlines():
        if line.startswith("|") and not re.match(r"^\|[\s:|-]+\|\s*$", line):
            out += [c.strip().replace(chr(92) + "$", "$") for c in line.strip().strip("|").split("|")]
    out += [re.sub(r"<[^>]+>", " ", c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", md, re.S)]
    return [c for c in out if c.strip()]


REPO =os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
B = os.path.join(REPO, "bench", "data", "olmocr-bench", "bench_data")
work = json.load(open(sys.argv[1], encoding="utf-8"))
candidate = sys.argv[2] if len(sys.argv) > 2 else "truedoc97"
wanted = {(pdf, t["id"]) for pdf, ts in work.items() for t in ts}
tests = {}
for f in glob.glob(os.path.join(B, "*.jsonl")):
    try:
        for t in load_tests(f):
            if (t.pdf, t.id) in wanted:
                tests[(t.pdf, t.id)] = t
    except Exception:
        pass
kinds = collections.Counter()
for pdf in sorted(work, key=lambda p: -len(work[p])):
    found = glob.glob(os.path.join(B, candidate, pdf[:-4] + "*.md"))
    md = open(found[0], encoding="utf-8").read() if found else ""
    n_tables = md.count("<table>") + sum(1 for l in md.splitlines() if l.startswith("| ---"))
    print("== %s  (%d checks; our page: %d chars, %d tables)" % (pdf, len(work[pdf]), len(md), n_tables))
    for rec in work[pdf]:
        t = tests.get((pdf, rec["id"]))
        ok, why = t.run(md) if t is not None else (False, "test not loaded")
        kind = ("no such cell" if "No cell matching" in why else "no table at all" if "No tables" in why or "no table" in why.lower()
                else "relation not satisfied" if "relationships" in why else "passes now" if ok else "other")
        kinds[kind] += 1
        rel = {k: rec[k] for k in ("up", "down", "left", "right", "top_heading", "left_heading") if rec.get(k)}
        print("     %-24s cell %-22r %s" % (kind, (rec.get("cell") or "")[:22], json.dumps(rel, ensure_ascii=False)[:90]))
        if kind in ("relation not satisfied", "other"):
            print("          %s" % why[:200])
        if kind == "no such cell":
            # what we wrote instead: the cells of ours that hold the expected words, or the one most like them
            want = " ".join((rec.get("cell") or "").split()).lower()
            cells = [" ".join(c.split()) for c in _cells(md)]
            holding = [c for c in cells if want and want in c.lower()]
            if holding:
                print("          held inside our cell: %r" % holding[0][:150])
            elif cells:
                best = max(cells, key=lambda c: difflib.SequenceMatcher(None, want, c.lower()[:3 * len(want) + 10]).ratio())
                print("          nearest cell of ours: %r (%.2f alike)" % (best[:120], difflib.SequenceMatcher(None, want, best.lower()).ratio()))
                if want.replace(" ", "") in md.lower().replace(" ", "").replace(chr(92), ""):
                    print("          (the words are on our page, outside any table cell or split across cells)")
print("by what the checker says:", dict(kinds))
