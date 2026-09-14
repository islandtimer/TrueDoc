"""Render every page whose markdown differs between two pooled A/B labels, and print what changed on each.

For each changed page: the words lost or gained (only real table tags and pipe syntax stripped - a loose tag
pattern reads "p<0.05" as the start of a tag and swallows the caption after it), the table shapes before and
after, and the first changed lines. The page image goes to bench/out/review/<label>/<stem>.png, to be read
against the markdown before anything is called better, neutral or worse.

usage (repo root): review_pages.py <base label> <label>
"""
import collections
import difflib
import io
import os
import re
import sys

import pypdfium2 as pdfium

IMAGES = os.path.join("bench", "out", "review")
PDFS = os.path.join("bench", "data", "olmocr-bench", "bench_data", "pdfs")
TAG = re.compile("</?(?:table|tr|td|th)(?: [^>]*)?>")


def read(path: str) -> str:
    return io.open(path, encoding="utf-8").read()


def words(md: str) -> collections.Counter:
    return collections.Counter(w for w in TAG.sub(" ", md).split() if w not in ("|", "---"))


def shapes(md: str) -> list[str]:
    out = []
    for t in md.split("<table>")[1:]:
        rows = t.split("</table>")[0].split("<tr>")[1:]
        out.append(f"{len(rows)}x{max((r.count('<td') + r.count('<th') for r in rows), default=0)}")
    pipe_rows = sum(1 for l in md.splitlines() if l.startswith("|") and not l.startswith("| ---"))
    return out + ([f"pipe rows {pipe_rows}"] if pipe_rows else [])


def main() -> None:
    base, label = sys.argv[1], sys.argv[2]
    images = os.path.join(IMAGES, label)
    os.makedirs(images, exist_ok=True)
    for subset in ("tables", "multi_column", "long_tiny_text"):
        before_dir = os.path.join("bench", "out", "ab", f"{base}_{subset}")
        after_dir = os.path.join("bench", "out", "ab", f"{label}_{subset}")
        for name in sorted(os.listdir(after_dir)):
            if not name.endswith(".md"):
                continue
            before, after = read(os.path.join(before_dir, name)), read(os.path.join(after_dir, name))
            if before == after:
                continue
            lost, gained = words(before) - words(after), words(after) - words(before)
            print(f"== {subset}/{name[:44]}")
            print(f"   words lost {dict(lost) if lost else 0}; gained {dict(gained) if gained else 0}")
            print(f"   tables {shapes(before)} -> {shapes(after)}")
            changed = [l for l in difflib.unified_diff(before.splitlines(), after.splitlines(), lineterm="", n=0)
                       if l[:1] in "+-" and not l.startswith(("+++", "---"))]
            for line in changed[:10]:
                print("      " + line[:130])
            if len(changed) > 10:
                print(f"      ... {len(changed) - 10} more changed lines")
            pdf = pdfium.PdfDocument(os.path.join(PDFS, subset, name[:-3]))
            pdf[0].render(scale=1.6).to_pil().save(os.path.join(images, name[:-7] + ".png"))
    print(f"images in {images}")


if __name__ == "__main__":
    main()
