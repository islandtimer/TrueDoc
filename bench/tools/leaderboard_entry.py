"""Build the olmOCR-bench leaderboard entry for run 97 as a folder ready to upload to a Hugging Face
model repository: the page outputs, the scorer's files, .eval_results/olmocrbench.yaml, RESULTS.md and
the model card. Nothing here uploads.

usage: python bench/tools/leaderboard_entry.py . <out folder> awmg/TrueDoc   (then leaderboard_publish.py <out folder> awmg/TrueDoc)
"""
import json
import os
import shutil
import sys

repo, out, hf_id = sys.argv[1], sys.argv[2], sys.argv[3]
RUN = os.path.join(repo, "bench", "runs", "truedoc96-20260918-162004")
CAND = os.path.join(repo, "bench", "data", "olmocr-bench", "bench_data", "truedoc96")
REV = "54a96a6fb6a2bd3b297e59869491db4d3625b711"
DATE = "2026-09-18"
GITHUB = "https://github.com/islandtimer/TrueDoc"
TAG = "run-97"
COMMIT = "9f9b77b"

if os.path.exists(out):
    shutil.rmtree(out)
os.makedirs(os.path.join(out, ".eval_results"))
os.makedirs(os.path.join(out, "scoring"))

# 1. the page outputs, in the scorer's own layout
n = 0
for cat in sorted(os.listdir(CAND)):
    src = os.path.join(CAND, cat)
    if not os.path.isdir(src):
        continue
    dst = os.path.join(out, "outputs", cat)
    os.makedirs(dst)
    for f in sorted(os.listdir(src)):
        if f.endswith(".md"):
            shutil.copy2(os.path.join(src, f), os.path.join(dst, f))
            n += 1
assert n == 1403, n

# 2. the scorer's files
for f in ("summary.json", "score_output.txt", "failed_tests.jsonl", "conversion.json"):
    shutil.copy2(os.path.join(RUN, f), os.path.join(out, "scoring", f))

# 3. the values, from the counts
s = json.load(open(os.path.join(RUN, "summary.json"), encoding="utf-8"))
vals = {k: 100 * v["passed"] / v["total"] for k, v in s["categories"].items()}
overall = sum(vals.values()) / len(vals)
ci = s["ci"]

source_url = f"https://huggingface.co/{hf_id}/blob/main/RESULTS.md"
source_name = "TrueDoc run 97: official scorer, all 1,403 page outputs and the scoring log in this repository"
user = hf_id.split("/")[0]
note_common = (
    "TrueDoc is a conversion pipeline, not a model: the PDF's own text layer is read on CPU for the 1,122 pages that "
    "have one (no model); Infinity-Parser2-Flash (2.2B) reads the 281 pages without a text layer, Infinity-Parser2-Pro "
    "(35B) the 102 of those the pipeline's own OCR cannot read, and olmOCR-2-7B-1025 92 picture regions on digital "
    "pages. Model readings were recorded on a rented GPU on 17 September 2026 and replayed from disk. Official scorer "
    "at dataset revision 54a96a6f, all eight sections, no post-processing keyed on the benchmark's folder names. "
    f"Code: {GITHUB} at tag {TAG}."
)
entries = [{
    "dataset": {"id": "allenai/olmOCR-bench", "task_id": "overall", "revision": REV},
    "value": round(overall, 4), "date": DATE,
    "source": {"url": source_url, "name": source_name, "user": user},
    "notes": f"Macro-average of the eight sections; 95% bootstrap CI {ci[0]}-{ci[1]}. " + note_common,
}]
for k in ("arxiv_math", "baseline", "headers_footers", "long_tiny_text", "multi_column", "old_scans", "old_scans_math", "table_tests"):
    entries.append({
        "dataset": {"id": "allenai/olmOCR-bench", "task_id": k, "revision": REV},
        "value": round(vals[k], 4), "date": DATE,
        "source": {"url": source_url, "name": source_name, "user": user},
        "notes": f"{s['categories'][k]['passed']} of {s['categories'][k]['total']} checks. " + note_common,
    })


def yaml_str(v: str) -> str:
    return json.dumps(v)  # a JSON string is a valid YAML double-quoted scalar


with open(os.path.join(out, ".eval_results", "olmocrbench.yaml"), "w", encoding="utf-8", newline="\n") as f:
    for e in entries:
        f.write("- dataset:\n")
        f.write(f"    id: {e['dataset']['id']}\n")
        f.write(f"    task_id: {e['dataset']['task_id']}\n")
        f.write(f"    revision: {e['dataset']['revision']}\n")
        f.write(f"  value: {e['value']}\n")
        f.write(f"  date: {yaml_str(e['date'])}\n")
        f.write("  source:\n")
        f.write(f"    url: {e['source']['url']}\n")
        f.write(f"    name: {yaml_str(e['source']['name'])}\n")
        f.write(f"    user: {e['source']['user']}\n")
        f.write(f"  notes: {yaml_str(e['notes'])}\n\n")

# 4. RESULTS.md - the page the entry cites
rows = "\n".join(
    f"| {k} | {vals[k]:.1f} | {s['categories'][k]['passed']} / {s['categories'][k]['total']} |"
    for k in ("arxiv_math", "old_scans_math", "table_tests", "old_scans", "headers_footers", "multi_column", "long_tiny_text", "baseline")
)
results = f"""# TrueDoc on olmOCR-bench: run 97

**Overall {overall:.1f}** (macro-average of the eight sections; 95% bootstrap CI {ci[0]}-{ci[1]}), scored on
{DATE} with the benchmark's official scorer (`olmocr` 0.4.27's `benchmark.py`) at dataset revision
`{REV}`, over all 1,403 pages and all 7,019 checks plus the 1,394 baseline checks.

| section | score | checks passed |
|---|---|---|
{rows}

## What produced these pages

TrueDoc is a PDF-to-markdown conversion pipeline, not a model. For this run:

- **1,122 pages with a digital text layer** were read from the PDF's own text on CPU, with a layout model
  (docling-layout-heron) for structure. No vision model read those pages.
- **281 pages with no text layer** (scans, photographs of paper) were read by **Infinity-Parser2-Flash**
  (2.2B, Apache-2.0). The **102** of those that the pipeline's own OCR could not read (its word-likeness gate)
  were read by **Infinity-Parser2-Pro** (35B, Apache-2.0) instead.
- **92 picture regions on digital pages** (pictures that hold text: a scanned table, a screenshot) were read by
  **olmOCR-2-7B-1025** (Apache-2.0).
- The model readings were recorded on a rented GPU on 17 September 2026 (Infinity-Parser2 through vLLM 0.17.1 with
  the settings of its authors' olmOCR-bench guide, raw markdown, none of their post-processing) and on 8 September
  2026 (olmOCR 2), and replayed from disk during the run. The readings are in the code repository.
- No post-processing keyed on the benchmark's category folder names. Every page was converted the same way.

The pipeline's code is at {GITHUB}, tag `{TAG}` (commit `{COMMIT}`); its README says how to reproduce this run
from the committed readings, and `docs/BENCHMARKS.md` there holds every run before this one.

## What is in this repository

- `outputs/<section>/<page>_pg1_repeat1.md`: the 1,403 page outputs exactly as scored, in the scorer's layout.
  Put the folder beside the dataset's `bench_data/pdfs` and run the scorer to re-score in minutes.
- `scoring/summary.json`, `scoring/score_output.txt`, `scoring/failed_tests.jsonl`: the scorer's own output, the
  bootstrap interval, and every failed check.
- `.eval_results/olmocrbench.yaml`: the entry the dataset's leaderboard reads.

## How to read the number

- It is a self-reported run of the official scorer, not an independent one. Everything needed to check it is
  here.
- A second scoring of the same pages moves a section by about three checks, so the tenth is not significant.
- A fifth of the benchmark's pages (`bench/holdout.txt` in the code repository) was never looked at while the
  pipeline's rules were built; that fifth scores 86.0 in this run, the rest 84.8.
- As of {DATE} this overall would rank second among the entries on the leaderboard by point estimate; the leading
  entry's 87.6 sits inside this run's interval. A live integration of the served readers (rather than replayed
  readings) is pending.
"""
with open(os.path.join(out, "RESULTS.md"), "w", encoding="utf-8", newline="\n") as f:
    f.write(results)

# 5. the model card
card = f"""---
license: apache-2.0
tags:
- ocr
- document-parsing
- pdf
- pipeline
- olmocr-bench
---

# TrueDoc: a PDF-to-markdown pipeline, measured on olmOCR-bench

**This repository holds a benchmark result, not model weights.** TrueDoc converts PDFs to markdown with a YAML
front matter (the Open Knowledge Format) and is built for *meaning accuracy*: does the output say what a reader of
the page would understand it to say? Its code is at {GITHUB} (Apache-2.0). The models it uses are other
people's: Infinity-Parser2-Flash and -Pro (infly), olmOCR-2-7B-1025 (allenai), docling-layout-heron
(docling-project), all Apache-2.0.

**olmOCR-bench, run 97: {overall:.1f}** (95% bootstrap CI {ci[0]}-{ci[1]}), official scorer, all eight sections,
dataset revision `54a96a6f`. [RESULTS.md](RESULTS.md) has the section scores, exactly what read which pages, and
how to re-score the 1,403 outputs in `outputs/` yourself.

The arrangement, in one line: the PDF's own text for the 1,122 pages that have it (no model), Infinity-Parser2-Flash
for the 281 that do not, Infinity-Parser2-Pro behind it for the 102 the pipeline's own OCR cannot read, olmOCR 2
for 92 picture regions; readings recorded on a rented GPU and replayed; no post-processing keyed on the
benchmark's folder names.
"""
with open(os.path.join(out, "README.md"), "w", encoding="utf-8", newline="\n") as f:
    f.write(card)

total = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(out) for f in fs)
print(f"built {out}: {n} outputs, {total/1e6:.1f} MB, overall {overall:.4f}")
