r"""What would escaping "&c" inside a formula win? On a run's own markdown, rerun every check of every page
that writes one, as written and with each "&c" escaped to "\&c" - the spelling the benchmark's expected
text uses and the only one KaTeX can read.
usage (repo root): etc_sim.py <candidate folder>"""
import glob
import os
import re
import sys

from olmocr.bench.tests import load_tests

cand = sys.argv[1]
B = os.path.join("bench", "data", "olmocr-bench", "bench_data")
SPAN = re.compile(r"(\\\[.*?\\\]|\\\(.*?\\\))", re.S)
ETC = re.compile(r"(?<!\\)&(\s*c\b)")


def fix(md: str) -> str:
    out, pos = [], 0
    for m in SPAN.finditer(md):
        out.append(md[pos:m.start()])
        out.append(ETC.sub(r"\\&\1", m.group(0)))
        pos = m.end()
    out.append(md[pos:])
    return "".join(out)


tests = []
for f in sorted(glob.glob(os.path.join(B, "*.jsonl"))):
    tests += load_tests(f)
pages = {}
for path in sorted(glob.glob(os.path.join(B, cand, "*", "*.md"))):
    md = open(path, encoding="utf-8").read()
    if fix(md) != md:
        rel = os.path.relpath(path, os.path.join(B, cand)).replace(chr(92), "/")
        pages[rel] = md
print(f"{len(pages)} pages change")
for rel, md in pages.items():
    stem = rel.split("_pg1")[0]
    mine = [t for t in tests if os.path.splitext(t.pdf)[0] == stem]
    if not mine:
        mine = [t for t in tests if os.path.splitext(t.pdf)[0].split("/")[-1] in rel]
    before = sum(bool(t.run(md)[0]) for t in mine)
    after = sum(bool(t.run(fix(md))[0]) for t in mine)
    print(f"   {rel}: {before}/{len(mine)} as written, {after}/{len(mine)} with the ampersand escaped")
