"""Convert PDFs with whichever truedoc is on the path and compare each with a markdown file already on disk.

For a rule that can only change what an earlier version changed: convert just those pages with the new code (a
worktree on PYTHONPATH) and check each against the base's conversion, or the earlier version's, byte for byte after
universal newlines. It prints where truedoc was imported from, so a worktree that is not on the path shows at once.

usage (repo root): convert_compare.py [--pages 1,2] <pdf>=<markdown file> [...]
    e.g. PYTHONPATH=bench/out/wt_x convert_compare.py bench/data/olmocr-bench/bench_data/pdfs/tables/a.pdf=bench/out/ab/pguard_tables/a.pdf.md
"""
import difflib
import os
import sys

import truedoc
from truedoc.pipeline import ConvertOptions, convert


def main() -> None:
    args = sys.argv[1:]
    pages = None
    if "--pages" in args:
        i = args.index("--pages")
        pages = [int(p) for p in args[i + 1].split(",")]
        del args[i:i + 2]
    print("truedoc from:", os.path.dirname(truedoc.__file__))
    same = 0
    for pair in args:
        pdf, expected = pair.rsplit("=", 1)
        opts = ConvertOptions(frontmatter=False, pages=pages) if pages else ConvertOptions(frontmatter=False)
        md = convert(pdf, opts)
        old = open(expected, encoding="utf-8").read()
        if md == old:
            same += 1
            print("same      ", os.path.basename(expected)[:70])
        else:
            print("DIFFERENT ", os.path.basename(expected)[:70])
            for line in list(difflib.unified_diff(old.splitlines(), md.splitlines(), lineterm="", n=0))[2:12]:
                print("     ", line[:160])
    print(f"{same} of {len(args)} the same")


if __name__ == "__main__":
    main()
