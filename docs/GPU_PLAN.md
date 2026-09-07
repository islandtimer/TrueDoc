# Plan: vision model for image-only pages (needs a rented GPU)

_Status: proposal, not started. Nothing has been spent._

## Why

281 of the 1,403 benchmark pages have no digital text layer (measured 7 September: 183 with no layer at all, 76 with a hidden OCR layer, 22 suspect; old scans 98, old-scan maths 36, tiny text 46, headers 39, multi-column 38, tables 24): old scans, old maths textbooks, some tiny-text and table pages. Classical OCR reads typewritten pages but not handwriting, and it cannot produce formulas from a scan. The two old-scans sections are a quarter of the overall score, and every tool at the top of the leaderboard uses a document vision model for them. The same is true for real users: scanned contracts, letters and old reports.

## What would run

One machine on vast.ai with a single consumer GPU (24 GB class), for a few hours:

1. Render the image-only pages (and, as a second experiment, all pages) to images.
2. Run an open-source document vision model over them and keep the markdown it produces.
3. Bring the outputs back and score them with the official scorer, both on their own and merged into TrueDoc's output using the evidence-first rule: where a page has a text layer, TrueDoc's own text wins and the model only supplies structure or fills gaps; where it has none, the model's text is used but sentences that repeat or look invented are dropped.

Candidate models (licences to be re-checked at the time; all are downloadable weights, no API):

| Model | Size | Why it is a candidate |
|---|---|---|
| PaddleOCR-VL | 0.9B | Top of OmniDocBench, tiny, fast; Apache-2.0 [recalled] |
| olmOCR 2 | 7B | Built for exactly this benchmark's document types; Apache-2.0 [recalled] |
| dots.ocr | 3B | Strong tables and layout; MIT [recalled] |
| GLM-OCR | 0.9B | Strong formulas; licence to verify |

## Cost estimate

| Item | Estimate |
|---|---|
| GPU rental (RTX 4090 class) | roughly 0.3 to 0.6 US dollars per hour |
| Model download and warm-up | 20 to 40 minutes |
| 250 pages through a 1B-7B model | 10 to 60 minutes |
| All 1,403 pages (second experiment) | 1 to 3 hours |
| **Total for both experiments** | **under 5 US dollars** |

## What I need from the owner

_Update 3 Sept: the owner has agreed in principle and offered to help with the setup. The scripts live in `bench/gpu/` (see its README). The concrete one-off steps, to be done when asked:_

1. Create a vast.ai account and add a small credit (10 US dollars is plenty for both experiments).
2. Add the SSH public key found at `~/.ssh/truedoc_vast.pub` on this machine to the account (Account, SSH Keys). Only the public half leaves this machine.
3. When asked, rent one on-demand instance: an RTX 4090 or RTX 3090 (24 GB), at least 60 GB of disk, the vast.ai "PyTorch" template, and paste the instance's SSH connection line (host and port) into the chat. Everything after that (copying the pages over, installing the model, running it, bringing the results back) happens over that connection from here.
4. Stop the instance when told the results are back (an idle instance keeps billing by the hour).

## What stays true regardless

TrueDoc's default path stays CPU-only and free. The vision model is an optional stage for pages that cannot be read any other way, and its output is always checked against whatever evidence the page has.

## Result of the first run (3 September 2026)

The 111 benchmark pages run 9 left empty were read by olmOCR 2 (7B, FP8) on a rented RTX 4090: 110 pages read, one failed inside the model's pipeline; 12 minutes of model time, about 55 minutes of instance time in all (upload and software installation were the bulk), cost under one US dollar.

Merged into run 9 by `bench/gpu/merge.py` (TrueDoc's page wherever it has text, the model's page only where TrueDoc left the page empty): **67.8 against 62.2**. Old scans 20.7 to 34.0, old-scan maths 4.1 to 23.1, tables 65.7 to 70.0, multi-column 70.7 to 72.6; the per-page baseline checks 93.4 to 99.9 because an empty page fails its baseline check.

What this says: TrueDoc's own OCR (a small CPU model) is the weak point on old scans, and a vision model on a GPU reads them far better. The candidate product shape is unchanged: text layer first (exact characters), CPU OCR as the fallback, and an *optional* vision stage for pages that have no usable text, run on a GPU when the owner enables it. Whether to make that stage part of the product is the owner's call (cost, GPU dependency).

## Result of the second measurement (7 September 2026)

No GPU was rented: the readings from 3 September were dropped onto the pages run 54 (67.4) leaves blank, with `bench/gpu/merge.py`, and scored with the official scorer.

| Candidate | Pages from the model | Overall | Old scans | Old-scan maths | Tables | Held-out |
|---|---|---|---|---|---|---|
| Run 54 | 0 | 67.4 | 21.5 | 4.1 | 80.0 | 65.0 |
| `truedoc53_vlm`: model on the 78 blank pages | 78 | **72.2** | 34.8 | 23.1 | 80.9 | 66.6 |
| `truedoc53_vlmall`: model on every page it read | 110 | **72.6** | 34.8 | 23.1 | 82.9 | 66.6 |

The second row is the product rule as decided (a model only reads pages TrueDoc cannot). The third replaces our own OCR on 28 typed pages it reads at 0.80-0.85 confidence, and the model wins 33 checks to 4 there: on a page with no text layer the model is the better reader even where the classical engine is confident. Two losses in both rows are running heads the model transcribed; the header rules should run over the model's text too when the stage is built into the pipeline. The proper run, with `--vision-endpoint` on inside the converter, still needs a served model: one rental hour, or the on-demand endpoint below.

## Result of the third measurement (7 September 2026, GPU session 2)

The owner rented an RTX 4090 (24 GB) on vast.ai for 33 minutes: the machine fetched the 281 pages without a digital text layer from Hugging Face itself (`bench/gpu/fetch_pages.py`, 290 s), installed olmOCR (6 minutes), and read the pages in 21 minutes; 85 cents in all. Merged into run 54 by page class (`bench/gpu/merge_by_list.py`):

| Pages given to the model | Overall | Old-scan maths | Old scans | Tiny text | Multi-column | Tables | Held-out |
|---|---|---|---|---|---|---|---|
| none (run 54) | 67.4 | 4.1 | 21.5 | 81.2 | 73.9 | 80.0 | 65.0 |
| blank pages only, the current rule (77) | 72.2 | 23.8 | 34.8 | 81.2 | 74.1 | 80.6 | 66.6 |
| no layer at all (183) | 77.1 | 43.2 | 46.6 | 85.3 | 76.0 | 82.2 | 74.9 |
| hidden OCR layer only (76) | 72.0 | 34.1 | 21.5 | 83.7 | 77.4 | 81.0 | 69.8 |
| suspect layer only (22) | 68.4 | 11.8 | 21.5 | 81.2 | 74.4 | 80.4 | 64.7 |
| **all 281** | **82.7** | 80.8 | 46.6 | 87.8 | 80.1 | 83.6 | 79.4 |

The hybrid beats the model alone (olmOCR's published 82.4) because the 1,122 digital pages keep their exact text (arXiv formulas 87.0 against the model's 83.0). Losses against run 54: 53 checks, mostly running heads the model transcribes and tiny-text references that carry the hidden layer's own OCR errors. Rule D019 in `docs/DECISIONS.md`, agreed by the owner.

## Design: the vision stage as a service (agreed 3 September 2026)

The converter gets one setting, the model endpoint address, and one switch per conversion. Providers behind one interface: (1) an open model served on an on-demand GPU endpoint (billed per second, nothing to start or stop), used for pages with no usable text; (2) a frontier model API, used for "inferred" work where understanding matters. A non-technical user sees only the switch; renting an instance by hand stays a development convenience. Pages sent to a frontier vendor must be disclosed to the user.

## Using the vision stage (built 3 September 2026)

TrueDoc now takes `--vision-endpoint <url>` (and `--vision-model <name>`, default `olmocr`). For every page that has no usable text of its own, it renders the page (longest side 1288 pixels), sends it with olmOCR 2's prompt to `<url>/v1/chat/completions`, and writes the model's reading as that page's text, marked as inferred (a note at the top of the page, `truedoc.pages_with_model` and `truedoc.inferred` in the front matter, one footnote definition at the end). Pages with text are never sent. The benchmark runner takes the same option (`truedoc bench --vision-endpoint <url>`), so a run with the endpoint switched on is the merged experiment done properly, in one pass.

Since the evening of 3 September the same switch also reads *regions* (decision D015, agreed by the owner): an icon-only table cell is asked what the icon means and gets `Covered[^inferred]`; a figure at least half an inch on a side is asked for a description, which becomes its alt text, `![A bar chart ...](figure)[^inferred]`. At most twelve regions per page. `--vision-pages-only` switches the region questions off. A frontier model can be used instead of the served one: `--vision-endpoint anthropic` (or `anthropic:claude-sonnet-5`) with the `ANTHROPIC_API_KEY` environment variable set by the owner; olmOCR 2 is trained for whole pages, so for region questions a general vision model (Anthropic, or a Qwen-VL-style model behind vLLM) is the better fit.

Serving the model on a rented GPU (the development path, until an on-demand endpoint exists):

    pip install "olmocr[gpu]" --extra-index-url https://download.pytorch.org/whl/cu128
    vllm serve allenai/olmOCR-2-7B-1025-FP8 --served-model-name olmocr --port 8000 --max-model-len 16384

then from this machine `ssh -L 8000:localhost:8000 -p <port> root@<host>` and `truedoc convert file.pdf --vision-endpoint http://localhost:8000`. The vLLM flags are the ones olmOCR's own pipeline uses [recalled, to be confirmed on the next rental]. Nothing is spent until an instance is rented.
