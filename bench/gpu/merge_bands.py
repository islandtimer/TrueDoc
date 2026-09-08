"""Stitch a page's band readings back into one reading, dropping the lines the overlap repeats.

`bench/gpu/select_bands.py` cuts a dense page into overlapping bands; the model reads each band
on its own. The bands are read back in order and joined: where the end of one band repeats the
start of the next (the overlap), the repeat is dropped once, matching on the words alone so a
line the model spelled differently in the two readings still counts as the same line.

    python bench/gpu/merge_bands.py <bands readings folder> <out candidate folder>

The readings folder holds `<category>/<stem>__b<i>.md` as the GPU wrote them, beside the
`manifest.json` that `select_bands.py` produced. The output is a candidate folder of whole-page
readings (`<category>/<stem>_pg1_repeat1.md`), which `--vision-endpoint file:<folder>` reads like
any other, so the banded reading can be scored against the whole-page one on the same checks.
"""
from __future__ import annotations

import difflib
import json
import os
import re
import sys


def words_of(line: str) -> list[str]:
    return re.findall(r"[^\W_]+", line.lower())


def strip_front_matter(text: str) -> str:
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            return parts[2].lstrip("\n")
    return text


def join(prev: list[str], nxt: list[str], max_overlap: int = 12) -> list[str]:
    """`nxt` with its opening lines dropped where they repeat the close of `prev`."""
    best_n, best_score = 0, 0.0
    for n in range(1, min(max_overlap, len(prev), len(nxt)) + 1):
        a = " ".join(w for line in prev[-n:] for w in words_of(line))
        b = " ".join(w for line in nxt[:n] for w in words_of(line))
        if not a or not b:
            continue
        score = difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()
        if score >= 0.75 and score >= best_score:
            best_n, best_score = n, score
    return prev + nxt[best_n:]


def main() -> None:
    src, out = sys.argv[1], sys.argv[2]
    manifest = json.load(open(os.path.join(src, "manifest.json"), encoding="utf-8"))
    by_page: dict[str, list[dict]] = {}
    for entry in manifest:
        by_page.setdefault(entry["page"], []).append(entry)
    written = 0
    for page, entries in by_page.items():
        sub, name = page.split("/")
        lines: list[str] = []
        missing = False
        for entry in sorted(entries, key=lambda e: e["order"]):
            stem = os.path.basename(entry["crop"])[:-4]
            found = None
            for pat in (stem + "_pg1_repeat1.md", stem + "_pg1.md", stem + ".md"):
                f = os.path.join(src, sub, pat)
                if os.path.exists(f):
                    found = f
                    break
            if found is None:
                missing = True
                break
            band = [l.rstrip() for l in strip_front_matter(open(found, encoding="utf-8").read()).splitlines()]
            band = [l for l in band if l.strip()]
            lines = band if not lines else join(lines, band)
        if missing or not lines:
            print(f"  skipped {page}: a band has no reading")
            continue
        os.makedirs(os.path.join(out, sub), exist_ok=True)
        with open(os.path.join(out, sub, name[:-4] + "_pg1_repeat1.md"), "w", encoding="utf-8") as fh:
            fh.write("\n\n".join(lines) + "\n")
        written += 1
    print(f"{written} pages stitched into {out}")


if __name__ == "__main__":
    main()
