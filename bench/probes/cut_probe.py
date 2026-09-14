"""Where `_refine_segments` puts its column cuts on the table holding given rows of any PDF page, and what each cut meets.

`sea_cut_probe.py` finds a Key Facts Sheet by name; this takes any PDF and page. The function is wrapped, not
re-implemented: for each table holding a row that starts with one of the given texts, it prints the cuts, the edge
splits of the run-together rule when the code has them, and for those rows and their neighbours every word's extent,
each segment, and where each cut falls - inside a word or in a gap, and how wide.

usage (repo root): cut_probe.py <pdf> <page number> <row text> [<row text> ...]
"""
import sys

from truedoc.pipeline import ConvertOptions, load_document
from truedoc.tables import aligned

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
    key = (tuple(round(c, 1) for c in cuts), tuple(texts[k] for k in hits), kw.get("second_look", True))
    if key in SEEN:
        return out
    SEEN.add(key)
    print(f"-- {len(rows)} rows, size {size:.1f}, second look {kw.get('second_look', True)}, cuts at x " + ", ".join(f"{c:.1f}" for c in cuts))
    splits = getattr(aligned, "_splits_at_shared_edges", None)
    if splits is not None:
        found = splits(rows, aligned._band_segments(rows, size), size)
        for k, r in enumerate(rows):
            for seg in r.segments:
                if id(seg) in found:
                    print(f"   edge split in row {k} at x " + ", ".join(f"{x:.1f}" for x in found[id(seg)]) + f": {' '.join(w.text for w in seg.words)[:60]}")
    for k in sorted({j for h in hits for j in (h - 1, h, h + 1) if 0 <= j < len(rows)}):
        words = sorted((w for seg in rows[k].segments for w in seg.words), key=lambda w: w.bbox.x0)
        print(f"   row {k}: " + "  ".join(f"{w.text}[{w.bbox.x0:.1f}-{w.bbox.x1:.1f}]" for w in words)[:280])
        print("      segments: " + " | ".join(f"[{s.bbox.x0:.1f}-{s.bbox.x1:.1f}] {' '.join(w.text for w in s.words)[:36]}" for s in rows[k].segments))
        for c in cuts:
            inside = [w for w in words if w.bbox.x0 < c < w.bbox.x1]
            if inside:
                print(f"      cut {c:.1f} falls inside {inside[0].text!r}")
                continue
            pair = next(((a, b) for a, b in zip(words, words[1:]) if a.bbox.x1 <= c <= b.bbox.x0), None)
            if pair:
                a, b = pair
                print(f"      cut {c:.1f} falls in the gap {a.text!r} | {b.text!r}, {(b.bbox.x0 - a.bbox.x1) / size:.2f} of the body size")
    return out


aligned._refine_segments = traced


def main() -> None:
    path, number = sys.argv[1], int(sys.argv[2])
    WANTED[:] = sys.argv[3:]
    load_document(path, ConvertOptions(frontmatter=False, pages=[number]))


if __name__ == "__main__":
    main()
