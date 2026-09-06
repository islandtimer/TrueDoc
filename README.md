# TrueDoc

**TrueDoc turns any PDF into machine-readable text (OKF markdown with a YAML front matter block) and is built to win on _meaning accuracy_: does the output say what a human reading the page would understand it to say?**

Status, plans and results live in `docs/` and are kept current:

| If you want to know... | Read |
|---|---|
| Where the project is right now, in plain English | [docs/STATUS.md](docs/STATUS.md) |
| What is coming next and why | [docs/ROADMAP.md](docs/ROADMAP.md) |
| How we measure "better than the other tools", and current scores | [docs/BENCHMARKS.md](docs/BENCHMARKS.md) |
| The output format we produce | [docs/OKF_SPEC.md](docs/OKF_SPEC.md) |
| Why things were built the way they were | [docs/DECISIONS.md](docs/DECISIONS.md) |
| The GPU experiment for scanned pages (run once, 3 Sept) and the optional vision stage | [docs/GPU_PLAN.md](docs/GPU_PLAN.md) |
| How the converter works, stage by stage (for developers) | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| The day-by-day working log (what was tried, what was learned) | [docs/PROGRESS_LOG.md](docs/PROGRESS_LOG.md) |

## The one-paragraph pitch

Existing converters fall into two camps. **Pipeline tools** (Marker, MinerU pipeline, Docling, Adobe Extract) read the PDF's own text and glue on layout models; they get characters right but often get structure wrong (tables, reading order, headers). **Vision models** (MinerU VLM, OvisOCR2, olmOCR, Chandra, GPT/Gemini) look at the page picture and rewrite it; they get structure right more often but can invent or drop text, and they are expensive at volume. TrueDoc is **evidence-first**: it treats the PDF's own text as ground truth wherever it exists, uses vision only to decide *structure* and to read pages that have no usable text, and cross-checks every model output against the raw evidence before believing it. Cheap where the document is easy, careful where it is hard.

## Quick start

```bash
py -3.13 -m venv .venv
.venv/Scripts/python -m pip install -e ".[bench,dev]"
.venv/Scripts/python -m pip install transformers rapidocr-onnxruntime   # layout model and OCR engine
.venv/Scripts/python -m truedoc.cli convert some.pdf -o some.md
```

Useful switches for `convert`: `--no-layout` (skip the layout model, much faster, less structure), `--no-math` (do not rebuild formulas), `--no-ocr` (never OCR image-only pages), `--page-markers`, `--pages 1,3-5`, `--no-frontmatter`.

The optional vision stage is off unless you switch it on: `--vision-endpoint http://localhost:8000` points at a served vision model (vLLM, see `docs/GPU_PLAN.md`), `--vision-endpoint anthropic` uses Anthropic's API with your `ANTHROPIC_API_KEY`. With it on, pages that have no readable text are read from their image, icons in table cells are given their meaning and figures a description, and every such piece is marked `[^inferred]` in the text and listed in the front matter (`docs/OKF_SPEC.md`, "Provenance marks"). `--vision-pages-only` limits it to unreadable pages.

The first run downloads the layout model weights (about 100 MB) from Hugging Face into the local cache. Everything runs on CPU; expect roughly 3-4 seconds a page with the layout model and about a second without it.

## Repository layout

```
truedoc/        the Python package (converter)
bench/          benchmark harness; datasets download into bench/data/ (git-ignored)
bench/tools/    the improvement loop's helpers: launch a scored run, check a rule page by page, diff two runs
tests/          unit tests
docs/           status, roadmap, decisions, benchmarks, format spec, progress log
```
