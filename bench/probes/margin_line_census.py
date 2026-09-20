"""Of the lone lines a loose rule called "beside the table", which are what the words mean?

The loose rule (parked, never committed: `_beside_the_run` in a copy of tables/aligned.py) stepped over any lone line
standing two sizes clear of a run's width. It gave benchmark tables/e82a04c6..._pg5 its heading row back - the line
was "year", the second line of a caption set in the margin - and on arXiv 2503.07452_pg8 it stepped over "The k
residual constraint, defined as:", body text standing left of a run of centred numbered equations, and the sentence
came out above the wrong equation. What the margin line IS: the continuation of a text block that stands beside the
table - a line directly above it, one leading away, flush with it, and itself clear of the run.

This census runs the loose rule (from <code root>, a tree that holds it) on the pages its screen named and says, for
each line it stepped over, whether that definition holds. Held-out pages are counted and never listed.

usage (repo root): margin_line_census.py <code root holding the loose rule> <file of category/stem pages> [...more files]
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = sys.argv[1]
sys.path.insert(0, ROOT)
from truedoc.pipeline import ConvertOptions, convert
from truedoc.tables import aligned

assert hasattr(aligned, "_beside_the_run"), "the code root does not hold the loose rule"
held = {l.strip()[:-4] for l in open(os.path.join(REPO, "bench", "holdout.txt"), encoding="utf-8") if l.strip() and not l.startswith("#")}
PAGE_LINES, STEPPED = [], []
real_find, real_beside = aligned.find_aligned_tables, aligned._beside_the_run


def find(page, lines, body_size):
    PAGE_LINES[:] = [l for l in lines if not l.rotated]
    return real_find(page, lines, body_size)


def beside(row, run, after, size):
    answer = real_beside(row, run, after, size)
    if answer:
        multi = [r for r in run + after if aligned._is_multicell(r, size)]
        STEPPED.append((row.segments[0], min(s.bbox.x0 for r in multi for s in r.segments), max(s.bbox.x1 for r in multi for s in r.segments)))
    return answer


aligned.find_aligned_tables, aligned._beside_the_run = find, beside
import truedoc.pipeline as pipeline
for module in list(sys.modules.values()):
    if getattr(module, "__name__", "").startswith("truedoc") and getattr(module, "find_aligned_tables", None) is real_find:
        module.find_aligned_tables = find

pages = [l.strip() for f in sys.argv[2:] for l in open(f, encoding="utf-8") if l.strip()]
totals = {"stepped over": 0, "a continuation of a block beside the table": 0}
hidden = 0
for name in pages:
    del STEPPED[:]
    convert(os.path.join(REPO, "bench", "data", "olmocr-bench", "bench_data", "pdfs", name + ".pdf"), ConvertOptions(frontmatter=False, pages=[1]))
    seen = set()
    for seg, x0, x1 in STEPPED:
        key = (round(seg.bbox.x0), round(seg.bbox.y0))
        if key in seen:
            continue
        seen.add(key)
        h = max(seg.bbox.height, 1.0)
        above = [l for l in PAGE_LINES if l is not seg and abs(l.bbox.x0 - seg.bbox.x0) <= 1.5
                 and 0.8 * h <= seg.bbox.y0 - l.bbox.y0 <= 1.7 * h and (l.bbox.x1 <= x0 or l.bbox.x0 >= x1)]
        totals["stepped over"] += 1
        totals["a continuation of a block beside the table"] += bool(above)
        if name in held:
            hidden += 1
            continue
        print("%-34s %-5s %-44r x %3.0f-%3.0f, run %3.0f-%3.0f | above it: %r" % (
            name[-34:], "YES" if above else "no", seg.text[:42], seg.bbox.x0, seg.bbox.x1, x0, x1, above[0].text[:30] if above else None))
print(totals, "| on held-out pages (counted, never listed):", hidden)
