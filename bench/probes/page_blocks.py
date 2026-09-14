"""Every block the pipeline keeps on one page: its kind, who decided it, how big it is and where it sits.

The Qantas home PDS cover drops its issuer, ABN and registered office; the log says the layout model labels that block
a page footer. This prints each block's kind and provenance, its lines and words, its top and bottom as a share of the
page's height, and its opening text, so the block and the rule that dropped it can be read off the page itself.
Nothing is changed.

usage (repo root): page_blocks.py <pdf> <page number>
"""
import sys

from truedoc.pipeline import ConvertOptions, load_document


def main() -> None:
    path, number = sys.argv[1], int(sys.argv[2])
    doc = load_document(path, ConvertOptions(frontmatter=False, pages=[number]))
    for page in doc.pages:
        blocks = getattr(page, "blocks", None)
        if blocks is None:
            sys.exit("the page keeps no blocks attribute")
        print(f"page {page.number}: {page.width:.0f} x {page.height:.0f}, body size {page.body_font_size}")
        for b in blocks:
            text = " ".join(b.text.split())
            words = len(text.split())
            print(f"  {str(b.kind):24s} {str(b.provenance)[:26]:26s} lines {len(b.lines):2d} words {words:3d}"
                  f"  y {b.bbox.y0 / page.height:.2f}-{b.bbox.y1 / page.height:.2f}  x {b.bbox.x0:.0f}-{b.bbox.x1:.0f}"
                  f"  | {text[:70]}")


if __name__ == "__main__":
    main()
