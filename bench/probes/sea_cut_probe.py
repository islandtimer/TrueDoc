"""Where `_refine_segments` puts its column cuts on a row whose answer is glued to its label, and what straddles them.

CGU's contents sheets write "Actions of the sea No" into the label's cell and leave the answer's cell empty. The text
layer sets "No" 11.5pt after "sea", at the x where every other row's "Yes" starts, yet the two arrive as one line. A
column cut placed inside that gap would divide the line on a real gap; a cut placed left of "sea"'s right edge would
leave no gap to divide it at. This wraps the function itself - nothing re-implemented - and, for each table holding a
named row, prints the cuts and, for the named rows and their neighbours, every word's extent and what each cut meets.

usage (repo root): sea_cut_probe.py <cache-name fragment> <row text> [<row text> ...]
"""
import os
import sys

sys.path.insert(0, os.path.join("bench", "tools"))
from kfs_grade import cache_path, held_out, sheets  # noqa: E402
from truedoc.pipeline import ConvertOptions, load_document  # noqa: E402
from truedoc.tables import aligned  # noqa: E402

ORIGINAL = aligned._refine_segments
WANTED: list[str] = []
SEEN: set = set()


def traced(rows, size, **kw):
    out = ORIGINAL(rows, size, **kw)
    cuts = out[1]
    texts = [" ".join(w.text for w in sorted((w for seg in r.segments for w in seg.words), key=lambda w: w.bbox.x0)) for r in rows]
    hits = [k for k, t in enumerate(texts) if any(t.startswith(want) for want in WANTED)]
    if not hits:
        return out
    key = (tuple(round(c, 1) for c in cuts), tuple(texts[k] for k in hits))
    if key in SEEN:
        return out
    SEEN.add(key)
    print(f"-- {len(rows)} rows, size {size:.1f}, cuts at x " + ", ".join(f"{c:.1f}" for c in cuts))
    for k in sorted({j for h in hits for j in (h - 1, h, h + 1) if 0 <= j < len(rows)}):
        words = sorted((w for seg in rows[k].segments for w in seg.words), key=lambda w: w.bbox.x0)
        print(f"   row {k}: " + "  ".join(f"{w.text}[{w.bbox.x0:.1f}-{w.bbox.x1:.1f}]" for w in words)[:260])
        print(f"      segments: " + " | ".join(f"[{s.bbox.x0:.1f}-{s.bbox.x1:.1f}] {' '.join(w.text for w in s.words)[:40]}" for s in rows[k].segments))
        for c in cuts:
            inside = [w for w in words if w.bbox.x0 < c < w.bbox.x1]
            if inside:
                print(f"      cut {c:.1f} falls inside the word {inside[0].text!r} [{inside[0].bbox.x0:.1f}-{inside[0].bbox.x1:.1f}]")
                continue
            pair = next(((a, b) for a, b in zip(words, words[1:]) if a.bbox.x1 <= c <= b.bbox.x0), None)
            if pair:
                a, b = pair
                print(f"      cut {c:.1f} falls in the gap {a.text!r} | {b.text!r}, {(b.bbox.x0 - a.bbox.x1) / size:.2f}em")
    return out


aligned._refine_segments = traced


def main() -> None:
    fragment, WANTED[:] = sys.argv[1], sys.argv[2:]
    by_cache = {os.path.basename(cache_path(p)): p for _, p in sheets()}
    name = next(n for n in sorted(by_cache) if fragment in n)
    path = by_cache[name]
    if held_out(path):
        print(f"{name}: held out, not looked at")
        return
    print(f"===== {name}", flush=True)
    load_document(path, ConvertOptions(frontmatter=False, pages=[1, 2]))


if __name__ == "__main__":
    main()
