"""The blocks at the foot of a page, line by line: where each line starts and ends, and what decided the block.

Written while deciding what makes a block at the foot of a page a running foot. For every block in the bottom fifth
of each page it prints the block's kind, provenance, size and each line's left and right edge, then the left edges
the page's body starts on and any page-number blocks - so a judgement about a foot (set flush left as the text is,
centred under the page, flush right beside a logo) can be checked in points. With --compact, only the blocks the
footer rule took out of the feet and footers of more than two lines.

usage (repo root): foot_geometry.py [--compact] <subset>/<markdown name> | <pdf path>@<page> [...]
"""
import collections
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
from truedoc.model import BlockKind  # noqa: E402
from truedoc.pipeline import ConvertOptions, load_document  # noqa: E402

PDFS = os.path.join("bench", "data", "olmocr-bench", "bench_data", "pdfs")
BODY = (BlockKind.TEXT, BlockKind.HEADING, BlockKind.LIST_ITEM, BlockKind.TABLE)


def resolve(arg: str) -> tuple[str, int]:
    if "@" in arg:
        path, page = arg.rsplit("@", 1)
        return path, int(page)
    subset, name = arg.split("/", 1)
    return os.path.join(PDFS, subset, name[:-3] if name.endswith(".md") else name), 1


def main() -> None:
    compact = "--compact" in sys.argv
    for arg in (a for a in sys.argv[1:] if a != "--compact"):
        path, number = resolve(arg)
        doc = load_document(path, ConvertOptions(frontmatter=False, pages=[number]))
        for page in doc.pages:
            H = page.height
            blocks = page.blocks
            body = page.body_font_size or 10.0
            print(f"== {os.path.basename(path)[:60]} p{number}: {page.width:.0f} x {H:.0f}, body {body:.1f}")
            for b in blocks:
                if b.bbox.y1 < 0.8 * H or not b.lines:
                    continue
                if compact and not (b.provenance == "footer-not-repeated" or (b.kind == BlockKind.FOOTER and len(b.lines) > 2)):
                    continue
                size = b.size or body
                print(f"   {str(b.kind):22s} {str(b.provenance)[:24]:24s} size {size:4.1f} lines {len(b.lines)}"
                      f" words {len(b.text.split())}  y {b.bbox.y0 / H:.3f}-{b.bbox.y1 / H:.3f}")
                for line in b.lines:
                    print(f"      x {line.bbox.x0:6.1f}-{line.bbox.x1:6.1f}  | {' '.join(line.text.split())[:60]}")
            edges = collections.Counter(round(b.bbox.x0) for b in blocks if b.kind in BODY and b.bbox.y1 < 0.8 * H)
            print("   body left edges (x: blocks):", dict(sorted(edges.items())))
            numbers = [(round(b.bbox.x0), round(b.bbox.y0 / H, 3), b.text.strip()[:10])
                       for b in blocks if b.kind == BlockKind.PAGE_NUMBER]
            print("   page numbers:", numbers)


if __name__ == "__main__":
    main()
