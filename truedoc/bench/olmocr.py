"""Run TrueDoc over olmOCR-bench and score it with the official scorer.

Layout expected by the official scorer (olmocr.bench.benchmark):

    bench_data/
      *.jsonl                      the tests
      pdfs/<category>/<name>.pdf   the inputs
      <candidate>/<category>/<name>_pg1_repeat1.md   one candidate's outputs

We write outputs there, then call the scorer with --candidate <name>.
Results are also copied to bench/runs/<candidate>-<timestamp>/.
"""

from __future__ import annotations

import datetime as _dt
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import time
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BENCH_DATA = os.path.join(REPO, "bench", "data", "olmocr-bench", "bench_data")
RUNS = os.path.join(REPO, "bench", "runs")


def _convert_one(pdf_path: str, out_path: str, layout: bool = True, ocr: bool = True, vision_endpoint: str | None = None, vision_regions: bool = True) -> tuple[str, float, str | None]:
    from truedoc.pipeline import ConvertOptions, convert

    t0 = time.time()
    err = None
    try:
        text = convert(pdf_path, ConvertOptions(frontmatter=False, page_markers=False, pages=[1], layout=layout, ocr=ocr, vision_endpoint=vision_endpoint, vision_regions=vision_regions))
    except Exception:
        text = ""
        err = traceback.format_exc()
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return pdf_path, time.time() - t0, err


def run_olmocr_bench(
    candidate: str = "truedoc",
    workers: int = 8,
    categories: list[str] | None = None,
    limit: int | None = None,
    score: bool = True,
    jsonl: str | None = None,
    layout: bool = True,
    ocr: bool = True,
    vision_endpoint: str | None = None,
    vision_regions: bool = True,
) -> dict | None:
    pdf_root = os.path.join(BENCH_DATA, "pdfs")
    if not os.path.isdir(pdf_root):
        raise SystemExit(f"benchmark PDFs not found at {pdf_root}; download the dataset first")
    cats = categories or sorted(os.listdir(pdf_root))
    jobs: list[tuple[str, str]] = []
    cand_root = os.path.join(BENCH_DATA, candidate)
    for cat in cats:
        pdfs = sorted(glob.glob(os.path.join(pdf_root, cat, "*.pdf")))
        if limit:
            pdfs = pdfs[:limit]
        for p in pdfs:
            stem = os.path.splitext(os.path.basename(p))[0]
            out = os.path.join(cand_root, cat, f"{stem}_pg1_repeat1.md")
            jobs.append((p, out))

    print(f"[bench] converting {len(jobs)} PDFs with {workers} workers -> {cand_root}")
    t0 = time.time()
    errors: list[tuple[str, str]] = []
    times: list[float] = []
    done = 0
    if layout:
        os.environ.setdefault("OMP_NUM_THREADS", "2")
        os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(_convert_one, p, o, layout, ocr, vision_endpoint, vision_regions) for p, o in jobs]
        for f in as_completed(futs):
            pdf_path, dt, err = f.result()
            times.append(dt)
            if err:
                errors.append((pdf_path, err))
            done += 1
            if done % 100 == 0 or done == len(jobs):
                print(f"[bench] {done}/{len(jobs)} done, {time.time() - t0:.0f}s elapsed")
    wall = time.time() - t0
    print(f"[bench] conversion finished in {wall:.0f}s; {len(errors)} errors; mean {sum(times)/max(1,len(times)):.2f}s/page")
    for p, e in errors[:5]:
        print(f"[bench] ERROR {p}\n{e}")

    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = os.path.join(RUNS, f"{candidate}-{stamp}")
    os.makedirs(run_dir, exist_ok=True)
    with open(os.path.join(run_dir, "conversion.json"), "w", encoding="utf-8") as fh:
        json.dump(
            {
                "candidate": candidate,
                "categories": cats,
                "n_pdfs": len(jobs),
                "wall_seconds": wall,
                "mean_seconds_per_page": sum(times) / max(1, len(times)),
                "errors": [{"pdf": p, "error": e[-2000:]} for p, e in errors],
            },
            fh,
            indent=2,
        )
    if not score:
        return None
    return score_candidate(candidate, run_dir, partial=bool(categories or limit), jsonl=jsonl)


def score_candidate(candidate: str, run_dir: str, partial: bool = False, jsonl: str | None = None) -> dict:
    """Run the official scorer and parse its summary."""
    target = BENCH_DATA if jsonl is None else os.path.join(BENCH_DATA, jsonl)
    cmd = [
        sys.executable,
        os.path.join(REPO, "bench", "score_olmocr.py"),
        "--dir",
        target,
        "--candidate",
        candidate,
        "--output_failed",
        os.path.abspath(os.path.join(run_dir, "failed_tests.jsonl")),  # the scorer resolves relative paths against its data folder
    ]
    if partial or jsonl is not None:
        cmd.append("--force")
    print("[bench] scoring:", " ".join(cmd))
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=REPO)
    out = proc.stdout + "\n" + proc.stderr
    with open(os.path.join(run_dir, "score_output.txt"), "w", encoding="utf-8") as fh:
        fh.write(out)
    summary = parse_score_output(out)
    summary["candidate"] = candidate
    summary["run_dir"] = run_dir
    with open(os.path.join(run_dir, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
    print(json.dumps(summary, indent=2))
    return summary


_CAT_LINE = re.compile(r"^\s*([\w\-]+\.jsonl|baseline)\s*:\s*([\d.]+)%\s*\((\d+)/(\d+) tests\)", re.M)
_AVG_LINE = re.compile(r"Average Score:\s*([\d.]+)%\s*\(95% CI:\s*\[([\d.]+)%,\s*([\d.]+)%\]\)")


def parse_score_output(text: str) -> dict:
    cats = {}
    for m in _CAT_LINE.finditer(text):
        cats[m.group(1).replace(".jsonl", "")] = {"score": float(m.group(2)), "passed": int(m.group(3)), "total": int(m.group(4))}
    avg = _AVG_LINE.search(text)
    return {
        "overall": float(avg.group(1)) if avg else None,
        "ci": [float(avg.group(2)), float(avg.group(3))] if avg else None,
        "categories": cats,
    }


if __name__ == "__main__":
    run_olmocr_bench()
