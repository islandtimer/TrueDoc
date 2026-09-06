"""List the benchmark pages that need a vision model: those TrueDoc could not read.

    python bench/gpu/select_pages.py --candidate truedoc6 [--out bench/gpu/pages.txt]

A page qualifies when the candidate's output for it is empty (no usable text
layer and no confident OCR) or when its text layer was judged unusable. The
list is written as one "category/stem" per line, plus a copy of the PDFs into
bench/gpu/pdfs/ so a single folder can be shipped to the GPU machine.
"""

from __future__ import annotations

import argparse
import os
import shutil

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BENCH = os.path.join(REPO, "bench", "data", "olmocr-bench", "bench_data")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate", required=True)
    ap.add_argument("--out", default=os.path.join(REPO, "bench", "gpu", "pages.txt"))
    ap.add_argument("--copy", action="store_true", help="copy the PDFs into bench/gpu/pdfs/<category>/")
    ap.add_argument("--min-bytes", type=int, default=200, help="outputs shorter than this count as unread")
    args = ap.parse_args()

    cand = os.path.join(BENCH, args.candidate)
    chosen: list[str] = []
    for cat in sorted(os.listdir(cand)):
        cat_dir = os.path.join(cand, cat)
        if not os.path.isdir(cat_dir):
            continue
        for name in sorted(os.listdir(cat_dir)):
            if not name.endswith("_pg1_repeat1.md"):
                continue
            stem = name[: -len("_pg1_repeat1.md")]
            size = os.path.getsize(os.path.join(cat_dir, name))
            if size < args.min_bytes:
                chosen.append(f"{cat}/{stem}")
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(chosen) + "\n")
    print(f"{len(chosen)} pages listed in {args.out}")
    if args.copy:
        dst_root = os.path.join(REPO, "bench", "gpu", "pdfs")
        for item in chosen:
            cat, stem = item.split("/", 1)
            src = os.path.join(BENCH, "pdfs", cat, stem + ".pdf")
            dst = os.path.join(dst_root, cat)
            os.makedirs(dst, exist_ok=True)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(dst, stem + ".pdf"))
        print(f"PDFs copied under {dst_root}")


if __name__ == "__main__":
    main()
