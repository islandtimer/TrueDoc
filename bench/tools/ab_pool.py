"""Score benchmark subsets with the working tree as it stands, many pages at once, for an A/B.

Why this exists. `ab_pages.py` starts `python -m truedoc.cli convert` for every page, so every page
pays for loading the layout model again; three subsets sharing the machine converted at 51 to 76
seconds a page (14 September), which put one gate - two code states over three subsets - at the best
part of a working day. This keeps a pool of worker processes alive and converts in them, so the model
loads once per worker.

It measures the same thing, and that was checked rather than assumed. The CLI builds `ConvertOptions`
from its own options, whose defaults are the dataclass's, and writes the returned string unchanged;
three pages the CLI had written came out identical byte for byte when converted in-process on the same
working tree. Even so, use it for *both* sides of a comparison - never one side from this and the
other from `ab_pages.py` - so that the only thing that differs is the code.

Each page is matched to the PDF its tests name exactly, not by prefix. A folder that already holds
pages is refused unless `--resume` is given, because silently reusing pages converted by a different
code state is precisely the kind of mistake an A/B exists to rule out. Folders are
`bench/out/ab/<label>_<subset>/` with `ab_pages.py`'s layout, so `ab_pages.py --compare` reads them.

Processes, not threads: the converter keeps global state (PDFium, the layout model, the OCR engine)
and fails silently in a thread. On Windows each worker starts by re-importing this script, hence the
`__main__` guard.

usage (repo root):
    ab_pool.py <label> --subset tables [--subset multi_column ...] [--workers 5] [--resume]
    ab_pages.py --compare <label>_<subset> <other label>_<subset>
"""
import concurrent.futures
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
B = os.path.join(REPO, "bench", "data", "olmocr-bench", "bench_data")
AB = os.path.join(REPO, "bench", "out", "ab")


def convert_one(job: tuple) -> tuple:
    pdf, md_path = job
    if os.path.exists(md_path) and os.path.getsize(md_path) > 0:
        return pdf, md_path, "kept"
    from truedoc.pipeline import ConvertOptions, convert
    try:
        md = convert(pdf, ConvertOptions(frontmatter=False))
    except Exception as exc:
        return pdf, md_path, "FAILED: " + repr(exc)[:120]
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write(md)
    return pdf, md_path, "converted"


def tests_by_pdf(subset: str) -> dict:
    """The subset's tests, grouped by the file name of the PDF each one names."""
    from olmocr.bench.tests import load_tests
    name = "table_tests" if subset == "tables" else subset
    grouped: dict[str, list] = {}
    for t in load_tests(os.path.join(B, name + ".jsonl")):
        grouped.setdefault(os.path.basename(t.pdf), []).append(t)
    return grouped


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0].startswith("--"):
        raise SystemExit(__doc__)
    label = args[0]
    subsets = [args[i + 1] for i, a in enumerate(args) if a == "--subset" and i + 1 < len(args)]
    workers = int(args[args.index("--workers") + 1]) if "--workers" in args else 5
    resume = "--resume" in args
    if not subsets:
        raise SystemExit("name at least one --subset")

    plan, jobs = [], []
    for subset in subsets:
        grouped = tests_by_pdf(subset)
        out_dir = os.path.join(AB, f"{label}_{subset}")
        if os.path.isdir(out_dir) and any(n.endswith(".md") for n in os.listdir(out_dir)) and not resume:
            raise SystemExit(f"{out_dir} already holds pages from some earlier run; "
                             "choose a new label, or pass --resume if they are this code state's")
        os.makedirs(out_dir, exist_ok=True)
        for name, tests in sorted(grouped.items()):
            pdf = os.path.join(B, "pdfs", subset, name)
            if not os.path.exists(pdf):
                print(f"no pdf on disk for {subset}/{name}", flush=True)
                continue
            md_path = os.path.join(out_dir, name + ".md")
            plan.append((subset, name, tests, md_path))
            jobs.append((pdf, md_path))
    print(f"{len(jobs)} pages over {', '.join(subsets)}, {workers} workers", flush=True)

    started = time.time()
    failures = 0
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
        for n, (pdf, md_path, note) in enumerate(pool.map(convert_one, jobs), 1):
            if note.startswith("FAILED"):
                failures += 1
                print(f"  {os.path.basename(pdf)[:50]}: {note}", flush=True)
            if n % 25 == 0 or n == len(jobs):
                rate = (time.time() - started) / n
                print(f"  {n:4d}/{len(jobs)}  {rate:4.1f} s a page", flush=True)

    for subset in subsets:
        scores = {}
        for s, name, tests, md_path in plan:
            if s != subset:
                continue
            md = open(md_path, encoding="utf-8").read() if os.path.exists(md_path) else ""
            passed = sum(1 for t in tests if t.run(md)[0])
            scores[name.split(".pdf")[0]] = (passed, len(tests))
        out_dir = os.path.join(AB, f"{label}_{subset}")
        with open(os.path.join(out_dir, "scores.json"), "w", encoding="utf-8") as fh:
            json.dump(scores, fh, indent=1)
        total = sum(p for p, _ in scores.values())
        of = sum(t for _, t in scores.values())
        print(f"{label}_{subset}: {total}/{of} over {len(scores)} pages", flush=True)
    print(f"done in {(time.time() - started) / 60:.1f} min, {failures} conversion failure(s)", flush=True)


if __name__ == "__main__":
    main()
