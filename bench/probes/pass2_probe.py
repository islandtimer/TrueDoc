"""Which cuts the second look in `_refine_segments` adds, and how the rows able to judge each one voted.

The first look is the function's own source with the second look cut out, so nothing is re-implemented.
usage (repo root): pass2_probe.py tables/f2ad0cd0 multi_column/019a8841 ...
"""
import inspect
import os
import sys

from truedoc.pipeline import ConvertOptions, load_document
from truedoc.tables import aligned

B = os.path.join("bench", "data", "olmocr-bench", "bench_data", "pdfs")
SRC = inspect.getsource(aligned._refine_segments)
HEAD, REST = SRC.split("    # A second look", 1)
TAIL = REST[REST.index("    cuts.sort()"):]
NS = dict(vars(aligned))
exec(HEAD.replace("def _refine_segments(", "def _pass_one(", 1) + TAIL, NS)
PASS_ONE = NS["_pass_one"]
ORIGINAL = aligned._refine_segments


def traced(rows, size):
    out = ORIGINAL(rows, size)
    cuts = out[1]
    first = PASS_ONE(rows, size)[1]
    new = [c for c in cuts if all(abs(c - f) > 0.01 for f in first)]
    if not new:
        return out
    worded = [sorted((w for seg in r.segments for w in seg.words), key=lambda w: w.bbox.x0) for r in rows]
    worded = [ws for ws in worded if len(ws) >= 2]
    print(f"  second look: {len(new)} new of {len(cuts)} cuts, {len(rows)} rows, size {size:.1f}")
    for c in new:
        able = [ws for ws in worded if ws[0].bbox.x1 <= c and ws[-1].bbox.x0 >= c]
        agree, lines = 0, []
        for ws in able:
            pair = next(((a, b) for a, b in zip(ws, ws[1:]) if a.bbox.x1 <= c <= b.bbox.x0), None)
            if pair is None:
                lines.append("        ?     a word edge within a point of the cut: " + " ".join(w.text for w in ws)[:60])
                continue
            a, b = pair
            gap = (b.bbox.x0 - a.bbox.x1) / size
            agree += gap >= 0.4
            lines.append(f"        {'gap  ' if gap >= 0.4 else 'SPACE'} {gap:4.2f}em  {a.text} | {b.text}    <- " + " ".join(w.text for w in ws)[:55])
        print(f"    cut at x {c:.1f}: {agree} of {len(able)} able rows leave a gap")
        for l in lines[:14]:
            print(l)
        if len(lines) > 14:
            print(f"        ... {len(lines) - 14} more")
    return out


aligned._refine_segments = traced


def main() -> None:
    for arg in sys.argv[1:]:
        subset, prefix = arg.split("/")
        name = next(n for n in os.listdir(os.path.join(B, subset)) if n.startswith(prefix))
        print(f"===== {subset}/{name[:44]}", flush=True)
        load_document(os.path.join(B, subset, name), ConvertOptions(frontmatter=False))


if __name__ == "__main__":
    main()
