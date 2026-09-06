"""Convert benchmark pages with the current code and compare their checks with a past run.

usage: python bench/tools/page_check.py <run_dir> <page_stem> [<page_stem> ...]
   or: python bench/tools/page_check.py <run_dir> --controls '<latex substring>' N <page_stem> ...
         (adds up to N arxiv_math pages whose *passing* checks in <run_dir> contain the substring,
          so a rule aimed at that construct is also checked where it already works)

A page stem is the PDF name without ".pdf" (any subset: arxiv_math, tables, long_tiny_text, ...);
a prefix matches the first PDF that starts with it, and "subset/name.pdf" names one page exactly.
<run_dir> is a bench/runs/<candidate>-<stamp>/ folder holding failed_tests.jsonl.
Writes pf_<stem>.md into bench/out/page_check/ (git-ignored); prints per-page counts, GAIN/LOSS
lines and a total. This is how a rule is verified before a full benchmark run.
"""
import glob
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
B = os.path.join(REPO, "bench", "data", "olmocr-bench", "bench_data")
OUT = os.path.join(REPO, "bench", "out", "page_check")
PY = sys.executable


def main():
    run_dir = sys.argv[1]
    args = sys.argv[2:]
    from olmocr.bench.tests import load_tests
    os.makedirs(OUT, exist_ok=True)
    failed = set()
    for line in open(os.path.join(run_dir, "failed_tests.jsonl"), encoding="utf-8"):
        if line.strip():
            t = json.loads(line)
            failed.add((t["pdf"], t.get("id")))
    tests_by_subset = {}

    def tests_for(subset):
        if subset not in tests_by_subset:
            name = "table_tests" if subset == "tables" else subset
            tests_by_subset[subset] = load_tests(os.path.join(B, name + ".jsonl"))
        return tests_by_subset[subset]

    stems = []
    if args and args[0] == "--controls":
        sub, n = args[1], int(args[2])
        args = args[3:]
        seen = []
        for t in tests_for("arxiv_math"):
            if sub in (t.math or "") and (t.pdf, t.id) not in failed:
                stem = os.path.basename(t.pdf).split(".pdf")[0]
                if stem not in seen and stem not in args:
                    seen.append(stem)
                if len(seen) >= n:
                    break
        stems += seen
    stems += args
    total_now = total_before = 0
    for s in stems:
        if "/" in s:   # an exact "subset/name.pdf"
            pdfs = [os.path.join(B, "pdfs", s.replace("/", os.sep))]
            if not os.path.exists(pdfs[0]):
                pdfs = []
        else:
            pdfs = glob.glob(os.path.join(B, "pdfs", "*", s + "*.pdf"))
        if not pdfs:
            print(s, "no pdf")
            continue
        pdf = pdfs[0]
        subset = os.path.basename(os.path.dirname(pdf))
        out = os.path.join(OUT, "pf_%s.md" % s.replace("/", "_"))
        r = subprocess.run([PY, "-m", "truedoc.cli", "convert", pdf, "--no-frontmatter", "-o", out],
                           cwd=REPO, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            print(s, "convert failed:", r.stderr[-300:])
            continue
        md = open(out, encoding="utf-8").read()
        name = os.path.basename(pdf)
        mine = [t for t in tests_for(subset) if t.pdf.endswith(name)]
        now = sum(1 for t in mine if t.run(md)[0])
        before = sum(1 for t in mine if (t.pdf, t.id) not in failed)
        total_now += now
        total_before += before
        print("%s (%s): now %d/%d  before %d/%d" % (s, subset, now, len(mine), before, len(mine)))
        for t in mine:
            ok = t.run(md)[0]
            was = (t.pdf, t.id) not in failed
            if ok != was:
                desc = getattr(t, "math", None) or getattr(t, "text", None) or getattr(t, "cell", None) or t.type
                print("    %s %s" % ("GAIN" if ok else "LOSS", str(desc)[:90]))
    print("total", total_now, "vs", total_before)
    print("done")


if __name__ == "__main__":
    main()
