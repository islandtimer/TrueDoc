"""Place the vision model's output as a benchmark candidate, and merge it into a
TrueDoc candidate, evidence first.

Steps (run from the repository root):

  1. Copy the GPU machine's output folder to bench/gpu/out (see README.md).
  2. python bench/gpu/merge.py place --out bench/gpu/out --candidate olmocr2
     Reads every results/*.jsonl the olmOCR pipeline wrote (one record per PDF)
     and writes bench_data/olmocr2/<category>/<stem>_pg1_repeat1.md.
  3. python bench/gpu/merge.py merge --base truedoc9 --model olmocr2 --out truedoc9_vlm
     For every page: TrueDoc's markdown when it has real text, else the model's.

Nothing here changes the converter; the merge is a benchmark experiment that
tells us what a vision model adds on the pages TrueDoc cannot read.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import shutil

BENCH = os.path.join("bench", "data", "olmocr-bench", "bench_data")


def place(out_dir: str, candidate: str) -> None:
    written = 0
    for path in glob.glob(os.path.join(out_dir, "work_*", "results", "*.jsonl")):
        category = os.path.basename(os.path.dirname(os.path.dirname(path)))[len("work_"):]
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            source = rec.get("metadata", {}).get("Source-File", "")
            stem = os.path.splitext(os.path.basename(source))[0]
            if not stem:
                continue
            text = rec.get("text") or ""
            target_dir = os.path.join(BENCH, candidate, category)
            os.makedirs(target_dir, exist_ok=True)
            with open(os.path.join(target_dir, f"{stem}_pg1_repeat1.md"), "w", encoding="utf-8", newline="\n") as fh:
                fh.write(text.rstrip() + "\n" if text.strip() else "")
            written += 1
    print(f"placed {written} pages under {os.path.join(BENCH, candidate)}")


def merge(base: str, model: str, out: str, min_chars: int = 20) -> None:
    base_dir, model_dir, out_dir = (os.path.join(BENCH, name) for name in (base, model, out))
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    taken = kept = 0
    for category in sorted(os.listdir(base_dir)):
        src = os.path.join(base_dir, category)
        if not os.path.isdir(src):
            continue
        dst = os.path.join(out_dir, category)
        os.makedirs(dst, exist_ok=True)
        for name in os.listdir(src):
            text = open(os.path.join(src, name), encoding="utf-8").read()
            alt = os.path.join(model_dir, category, name)
            if len(text.strip()) < min_chars and os.path.exists(alt):
                shutil.copyfile(alt, os.path.join(dst, name))
                taken += 1
            else:
                shutil.copyfile(os.path.join(src, name), os.path.join(dst, name))
                kept += 1
    print(f"merged into {out_dir}: {kept} pages from {base}, {taken} pages from {model}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("place")
    p.add_argument("--out", default=os.path.join("bench", "gpu", "out"))
    p.add_argument("--candidate", default="olmocr2")
    m = sub.add_parser("merge")
    m.add_argument("--base", required=True)
    m.add_argument("--model", default="olmocr2")
    m.add_argument("--out", required=True)
    m.add_argument("--min-chars", type=int, default=20)
    args = ap.parse_args()
    if args.cmd == "place":
        place(args.out, args.candidate)
    else:
        merge(args.base, args.model, args.out, args.min_chars)


if __name__ == "__main__":
    main()
