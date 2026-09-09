"""Find and check the pages the rotated-page clip bug actually touches (M18, D022).

Two stages in `truedoc/` photograph a patch of the page and look at the pixels: `_renders_uniform`
in `extract/textlayer.py`, which asks whether an area of the page is blank (the hidden-text rules
of D011), and `_ink` in `marks.py`, which reads a tick or a cross. Both take a box in the page's
*shown* coordinates, convert it to the page's *stored* coordinates, and then clip - but PyMuPDF's
`get_pixmap` wants the shown coordinates, so on a rotated page both photograph the wrong patch.
On an upright page the conversion does nothing, which is why it never showed.

The quick gate has no rotated page carrying a mark, so this exists to check the fix where it
matters instead of where it is convenient.

    python bench/tools/rotated_clip_check.py --find <folder>     # list rotated pages with marks
    python bench/tools/rotated_clip_check.py --check <listfile>  # read marks on each, for diffing

`--find` writes one `path\tpage` per line. Run `--check` before and after the fix and diff the two
outputs: any line that changes is a mark whose reading the fix altered.
"""
from __future__ import annotations

import argparse
import glob
import os
import sys

import pymupdf


def find(folder: str, limit: int) -> list[tuple[str, int]]:
    """Rotated pages that carry something the mark reader would look at."""
    out: list[tuple[str, int]] = []
    files = sorted(glob.glob(os.path.join(folder, "**", "*.pdf"), recursive=True))
    for n, path in enumerate(files):
        if limit and len(out) >= limit:
            break
        try:
            doc = pymupdf.open(path)
        except Exception:
            continue
        try:
            for i in range(doc.page_count):
                try:
                    page = doc[i]
                    if not page.rotation:
                        continue
                    # cheap proxy for "the mark reader has something to look at here"
                    drawings = len(page.get_drawings())
                    images = len(page.get_image_info())
                    if drawings + images:
                        out.append((path, i + 1))
                except Exception:
                    continue
        finally:
            doc.close()
        if n % 200 == 0:
            print(f"  ... {n} files, {len(out)} rotated pages so far", file=sys.stderr, flush=True)
    return out


def check(entries: list[tuple[str, int]]) -> None:
    """Print every mark read on each page, so two runs can be diffed."""
    from truedoc.extract.textlayer import extract_page
    from truedoc.marks import find_marks

    for path, number in entries:
        try:
            doc = pymupdf.open(path)
            pdf_page = doc[number - 1]
            page = extract_page(pdf_page, number)
            M = pdf_page.rotation_matrix if pdf_page.rotation else None
            marks = find_marks(pdf_page, page, M)
            hidden = len(page.hidden_text)
            got = ";".join(f"{m.text}@{m.bbox.x0:.0f},{m.bbox.y0:.0f}" for m in marks) or "-"
            print(f"{os.path.basename(path)}\tpg{number}\tmarks={len(marks)}\thidden={hidden}\t{got}")
            doc.close()
        except Exception as exc:
            print(f"{os.path.basename(path)}\tpg{number}\tFAILED\t{exc}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--find")
    ap.add_argument("--check")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    if args.find:
        for path, number in find(args.find, args.limit):
            print(f"{path}\t{number}")
    elif args.check:
        entries = []
        for line in open(args.check, encoding="utf-8"):
            if line.strip():
                path, number = line.rstrip("\n").split("\t")
                entries.append((path, int(number)))
        check(entries)
    else:
        ap.error("give --find <folder> or --check <listfile>")


if __name__ == "__main__":
    main()
