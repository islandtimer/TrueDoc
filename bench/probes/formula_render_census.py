r"""Which formulas does TrueDoc write that no renderer can read? Every \(...\) and \[...\] span in a run's
markdown, put through the benchmark's own KaTeX renderer; the ones that fail are counted by the reason
KaTeX itself gives. A formula that will not render is a meaning defect on its own - the reader sees raw
TeX - and on a maths page it also costs the check.

Corrected 12 Sept: the first version counted a failure as `render_equation(...) is None`, which never
happens. The renderer hands back an object with `.error` set and no spans, so the old census reported zero
failures whatever the formulas held.

usage (repo root): formula_render_census.py <candidate folder> [subdir glob] [limit] [--list <n>]"""
import collections
import glob
import os
import re
import sys

from olmocr.bench.katex.render import render_equation

cand = sys.argv[1]
where = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else "*"
limit = int(sys.argv[3]) if len(sys.argv) > 3 and not sys.argv[3].startswith("--") else 0
show = int(sys.argv[sys.argv.index("--list") + 1]) if "--list" in sys.argv else 0
B = os.path.join("bench", "data", "olmocr-bench", "bench_data", cand)
SPAN = re.compile(r"\\\[(.*?)\\\]|\\\((.*?)\\\)", re.S)


def reason_of(err: str) -> str:
    """KaTeX's message, cut back to the part that names the fault (it appends the formula itself)."""
    text = " ".join(str(err or "").split())
    text = text.replace("KaTeX parse error: ", "")
    for cut in (" at position", " at end of input"):
        if cut in text:
            text = text.split(cut)[0]
    return text[:80] or "unknown"


pages = sorted(glob.glob(os.path.join(B, where, "*.md")))
if limit:
    pages = pages[:limit]

total = bad = 0
by_reason = collections.Counter()
by_page = collections.Counter()
examples = collections.defaultdict(list)
for path in pages:
    md = open(path, encoding="utf-8").read()
    for m in SPAN.finditer(md):
        body = (m.group(1) or m.group(2) or "").strip()
        if not body:
            continue
        total += 1
        try:
            r = render_equation(body)
            err = None if r is None else getattr(r, "error", None)
            ok = r is not None and not err
        except Exception as exc:  # a renderer crash is a failure to render like any other
            err, ok = repr(exc), False
        if not ok:
            bad += 1
            page = os.path.relpath(path, B).replace(chr(92), "/")
            by_page[page] += 1
            reason = reason_of(err)
            by_reason[reason] += 1
            if len(examples[reason]) < 3:
                examples[reason].append((page, " ".join(body.split())[:120]))

print(f"{total} formulas over {len(pages)} pages; {bad} will not render ({100.0 * bad / max(1, total):.1f}%)")
print("by the reason KaTeX gives:")
for reason, n in by_reason.most_common(20):
    print(f"   {n:5d}  {reason}")
    for page, body in examples[reason][:show or 1]:
        print(f"          {page}")
        print(f"          {body}")
print("worst pages:")
for page, n in by_page.most_common(12):
    print(f"   {n:4d}  {page}")
