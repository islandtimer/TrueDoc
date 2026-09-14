"""The benchmark's table checks that name a dollar amount, run on our markdown as written and with its escaped dollars
unescaped.

A pipe table writes a literal dollar as `\\$448` (D024), an HTML table cell writes `$448`, and the table check
compares the cell's text with the check's own. On one Wiley page every check that names a dollar amount failed in
the pipe table and passed once the same table came out as HTML. This counts how far that reaches: every table check
naming a dollar, on each pool folder's pages, as written and with each escaped dollar put back. Nothing is changed.

usage (repo root): dollar_cells.py <pool folder> [<pool folder> ...]   e.g. bench/out/ab/pg_tables
"""
import collections
import os
import sys

from olmocr.bench.tests import load_tests

B = os.path.join("bench", "data", "olmocr-bench", "bench_data")
ESCAPED = chr(92) + "$"
FIELDS = ("cell", "up", "down", "left", "right", "top_heading", "left_heading")


def main() -> None:
    tests = [t for t in load_tests(os.path.join(B, "table_tests.jsonl"))
             if any("$" in (getattr(t, f, None) or "") for f in FIELDS)]
    for folder in sys.argv[1:]:
        counted = as_written = unescaped = 0
        pages: collections.Counter = collections.Counter()
        for t in tests:
            stem = os.path.splitext(os.path.basename(t.pdf))[0]
            path = os.path.join(folder, stem + ".pdf.md")
            if not os.path.exists(path):
                continue
            md = open(path, encoding="utf-8").read()
            ok = bool(t.run(md)[0])
            ok_unescaped = bool(t.run(md.replace(ESCAPED, "$"))[0])
            counted += 1
            as_written += ok
            unescaped += ok_unescaped
            if ok_unescaped and not ok:
                pages[stem] += 1
            if "a769f9a3" in stem:
                print(f"   {t.id}: {getattr(t, 'cell', '')!r} as written {ok}, unescaped {ok_unescaped}")
        print(f"{folder}: {counted} table checks name a dollar; {as_written} pass as written, {unescaped} with the escapes "
              f"put back; {sum(pages.values())} checks on {len(pages)} pages fail only on the escape")
        for stem, n in pages.most_common(12):
            print(f"      {n:3d}  {stem}")


if __name__ == "__main__":
    main()
