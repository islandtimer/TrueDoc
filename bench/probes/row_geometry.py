"""The text layer's own geometry for a few rows of a Key Facts Sheet: every line on the row, word by word, with the gaps.

CGU's contents sheets write "Actions of the sea No" into the label's cell and leave the answer's cell empty, while
the rows around it read right. Whether "No" is one run with its label or a separate line, how far it stands from
"sea" against the body size, and where it starts against the other rows' answers decides what kind of fault it is.
Nothing is changed: the document is loaded as the pipeline loads it and its lines are printed.

usage (repo root): row_geometry.py <cache-name fragment> <label> [<label> ...]
"""
import os
import sys

sys.path.insert(0, os.path.join("bench", "tools"))
from kfs_grade import cache_path, held_out, sheets  # noqa: E402
from truedoc.pipeline import ConvertOptions, load_document  # noqa: E402


def text_of(line) -> str:
    return " ".join(w.text for w in line.words)


def main() -> None:
    fragment, labels = sys.argv[1], sys.argv[2:]
    by_cache = {os.path.basename(cache_path(p)): p for _, p in sheets()}
    name = next(n for n in sorted(by_cache) if fragment in n)
    path = by_cache[name]
    if held_out(path):
        print(f"{name}: held out, not looked at")
        return
    print(f"===== {name}")
    doc = load_document(path, ConvertOptions(frontmatter=False, pages=[1, 2]))
    for page in doc.pages:
        for anchor in [l for l in page.lines if any(label in text_of(l) for label in labels)]:
            y0, y1 = anchor.bbox.y0 - 2.0, anchor.bbox.y1 + 2.0
            print(f"-- page {page.number}, row at y {anchor.bbox.y0:.1f}-{anchor.bbox.y1:.1f}")
            for line in sorted((l for l in page.lines if l.bbox.y1 > y0 and l.bbox.y0 < y1), key=lambda l: l.bbox.x0):
                size = getattr(line, "size", 0.0) or 1.0
                parts = []
                for i, w in enumerate(line.words):
                    if i:
                        gap = w.bbox.x0 - line.words[i - 1].bbox.x1
                        parts.append(f"<{gap:.1f}pt {gap / size:.2f}em>")
                    parts.append(f"{w.text}[{w.bbox.x0:.1f}-{w.bbox.x1:.1f}]")
                print(f"   line x {line.bbox.x0:.1f}-{line.bbox.x1:.1f} size {size:.1f}: " + " ".join(parts)[:400])


if __name__ == "__main__":
    main()
