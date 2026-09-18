# TrueDoc

**TrueDoc turns any PDF into machine-readable text (OKF markdown with a YAML front matter block) and is built to win on _meaning accuracy_: does the output say what a human reading the page would understand it to say?**

## Where it stands (18 September 2026)

| Measure | Score | What it means |
|---|---|---|
| [olmOCR-bench](https://huggingface.co/datasets/allenai/olmOCR-bench), all 1,403 pages, all eight sections | **86.8** (bootstrap CI 86.0-87.7) | our own run (97) of the benchmark's official scorer, at dataset revision `54a96a6f`. The CPU converter reads the 1,122 pages that have a digital text layer; the 281 that do not are read by Infinity-Parser2-Flash (2.2B, Apache-2.0), and the 102 of those the converter judges beyond its own OCR by Infinity-Parser2-Pro (35B). Second by point estimate against the leaderboard as read on 18 September (87.6, 85.8). Published as a self-reported entry with all 1,403 page outputs and the scorer's log: [huggingface.co/awmg/TrueDoc](https://huggingface.co/awmg/TrueDoc) |
| The same with Flash alone | 85.6 (CI 84.8-86.5) | run 94, for anyone who will not run a second tier |
| A held-out fifth of the benchmark, never looked at while building rules | 86.0 | `bench/holdout.txt`; the tuned-on four fifths score 84.8 |
| 229 checks over 25 pages of Australian insurance documents | 229 of 229 | the owner's own reading questions (`bench/insurance_holdout.txt` seals 19 further documents that were never opened) |
| 190 insurers' Key Facts Sheets, header and answers | 99% / 100% | `bench/tools/kfs_grade.py`, a fifth of the sheets held out |

The model readings those scores replay are committed under `bench/gpu/out5/`, so every number can be re-scored without a GPU ("Reproducing the benchmark number", below). `docs/BENCHMARKS.md` has every run, the leaderboard as read, and what each competitor's number was measured on.

Status, plans and results live in `docs/` and are kept current:

| If you want to know... | Read |
|---|---|
| Where the project is right now, in plain English | [docs/STATUS.md](docs/STATUS.md) |
| What is coming next and why | [docs/ROADMAP.md](docs/ROADMAP.md) |
| How we measure "better than the other tools", and current scores | [docs/BENCHMARKS.md](docs/BENCHMARKS.md) |
| What Marker and MinerU do, and which of their ideas are worth taking | [docs/M14_MARKER_MINERU.md](docs/M14_MARKER_MINERU.md) |
| The lateral-thinking round: facts it established, converging ideas, shortlist, owner decisions | [docs/LATERAL_ROUND_1.md](docs/LATERAL_ROUND_1.md) |
| The output format we produce | [docs/OKF_SPEC.md](docs/OKF_SPEC.md) |
| Why things were built the way they were | [docs/DECISIONS.md](docs/DECISIONS.md) |
| The GPU experiment for scanned pages (run once, 3 Sept) and the optional vision stage | [docs/GPU_PLAN.md](docs/GPU_PLAN.md) |
| How the converter works, stage by stage (for developers) | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| The day-by-day working log (what was tried, what was learned) | [docs/PROGRESS_LOG.md](docs/PROGRESS_LOG.md) |
| Which model reads which pages, and what each choice measured | [docs/MODEL_CHOICE.md](docs/MODEL_CHOICE.md) |
| The icons in the insurance library: what was measured, and why no icon reader was built | [docs/ICONS_REVIEW.md](docs/ICONS_REVIEW.md) |

## The one-paragraph pitch

Existing converters fall into two camps. **Pipeline tools** (Marker, MinerU pipeline, Docling, Adobe Extract) read the PDF's own text and glue on layout models; they get characters right but often get structure wrong (tables, reading order, headers). **Vision models** (MinerU VLM, OvisOCR2, olmOCR, Chandra, GPT/Gemini) look at the page picture and rewrite it; they get structure right more often but can invent or drop text, and they are expensive at volume. TrueDoc is **evidence-first**: it treats the PDF's own text as ground truth wherever it exists, uses vision only to decide *structure* and to read pages that have no usable text, and cross-checks every model output against the raw evidence before believing it. Cheap where the document is easy, careful where it is hard.

## Quick start

Python 3.11 or newer. On Windows (where TrueDoc is developed and tested; Linux and macOS are untested):

```bash
py -3.13 -m venv .venv
.venv/Scripts/python -m pip install -e ".[bench,dev]"
.venv/Scripts/python -m truedoc.cli convert some.pdf -o some.md
```

Elsewhere, `python3 -m venv .venv` and `.venv/bin/python` in place of `.venv/Scripts/python`. The install
pulls in the layout model's runtime (torch and transformers, the largest part of it) and the OCR engine;
the first conversion downloads the layout weights (about 100 MB) and the OCR weights from Hugging Face
into the local cache. `.venv/Scripts/python -m pytest -q` runs the test suite.

Useful switches for `convert`: `--no-layout` (skip the layout model, much faster, less structure), `--no-math` (do not rebuild formulas), `--no-ocr` (never OCR image-only pages), `--page-markers`, `--pages 1,3-5`, `--no-frontmatter`.

**How a conversion ended** is said three ways, because a body alone cannot say it: in the front matter (`truedoc.completion` - `complete`, `degraded` or `incomplete` - and `truedoc.issues`, each with a code and its pages), on stderr, and with `--status out.json` as a file for software. `--strict` exits with code 3 when the result is anything short of complete (the file is still written); a page selection the document cannot meet (`--pages 99` of a two-page file, `--pages 2-1`) is refused with exit code 2. From Python, `truedoc.pipeline.convert_with_status` returns the markdown with the same status.

The optional vision stage is off unless you switch it on: `--vision-endpoint http://localhost:8000` points at a served vision model (vLLM, see `docs/GPU_PLAN.md`), `--vision-endpoint anthropic` uses Anthropic's API with your `ANTHROPIC_API_KEY`. With it on, pages that have no readable text are read from their image, icons in table cells are given their meaning and figures a description, and every such piece is marked `[^inferred]` in the text and listed in the front matter (`docs/OKF_SPEC.md`, "Provenance marks"). `--vision-pages-only` limits it to unreadable pages.

The converter itself runs on CPU; expect roughly 3-4 seconds a page with the layout model and about a second without it. The vision readers run on a GPU or a hosted service, or are replayed from saved readings with `--vision-endpoint file:<folder>` (and `--vision-deep file:<folder>` for the second tier), which is how every benchmark run since run 55 was made.

## Reproducing the benchmark number

Everything needed is in this repository except the dataset (2 GB) and the scorer's test modules:

```bash
# 1. the dataset, at the revision the scores cite
.venv/Scripts/python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='allenai/olmOCR-bench', repo_type='dataset', revision='54a96a6fb6a2bd3b297e59869491db4d3625b711', local_dir='bench/data/olmocr-bench', allow_patterns=['bench_data/*.jsonl','bench_data/pdfs/**'])"
# 2. the official scorer's test modules (bench/olmocr_ref/benchmark.py drives them; NOTICE says how)
.venv/Scripts/python -m pip install olmocr==0.4.27
# 3. the saved model readings, placed as candidate folders (they rebuild byte for byte)
.venv/Scripts/python bench/gpu/place_bakeoff.py infinity bench/gpu/out5/flash/pdfs inf2flash
.venv/Scripts/python bench/gpu/place_bakeoff.py infinity bench/gpu/out5/pro/pdfs inf2pro
.venv/Scripts/python bench/gpu/merge.py place --out bench/gpu/out3 --candidate olmocr2c
cp bench/gpu/out3/crops_failing_manifest.json bench/data/olmocr-bench/bench_data/olmocr2c/manifest.json
# 4. convert the 1,403 pages and score them (about two hours on 16 cores)
B=bench/data/olmocr-bench/bench_data
.venv/Scripts/python -m truedoc.cli bench --candidate mine --workers 6 --vision-endpoint file:$B/inf2flash_raw+$B/olmocr2c --vision-deep file:$B/inf2pro_raw
```

`bench/runs/mine-<timestamp>/summary.json` then holds the overall score, the interval and the eight sections; `bench/holdout_score.py <run dir>` splits it into the held-out and tuned-on pages. A second scoring of the same pages moves a section by about three checks, so expect the tenth to differ. `bench/README.md` and `bench/gpu/README.md` have the rest: one category at a time, the A/B tools, and how the readings were made.

## Repository layout

```
truedoc/        the Python package (converter)
bench/          benchmark harness; datasets download into bench/data/ (git-ignored)
bench/tools/    the improvement loop's helpers: launch a scored run, check a rule page by page, diff two runs,
                A/B two code states, grade the Key Facts Sheets, read the pages a change moved
bench/probes/   one-off investigation scripts the docs cite as evidence
bench/gpu/      the rented-GPU sessions: scripts, recipes, and the saved readings the runs replay
bench/olmocr_ref/  the benchmark's own scorer, copied (Apache-2.0, AI2)
samples/        four insurers' documents kept as test cases
tests/          unit tests
docs/           status, roadmap, decisions, benchmarks, format spec, progress log
```

## Licence

Apache License 2.0 (`LICENSE`). `NOTICE` lists what the repository contains or fetches that is other people's work, and its terms; `docs/DECISIONS.md` (D007) records the licence check of everything on the conversion path - nothing on it is copyleft or commercial.
