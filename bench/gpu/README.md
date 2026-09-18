# GPU step: a vision model for pages TrueDoc cannot read

Everything here is for the optional vision-model stage described in `docs/GPU_PLAN.md`. The default converter stays CPU-only.

## Files

- `select_pages.py` lists the benchmark pages whose TrueDoc output is empty (no usable text layer and no confident OCR) and copies their PDFs into `pdfs/<category>/`.
- `run_olmocr2.sh` runs olmOCR 2 over that folder on the rented machine and leaves one markdown file per page under `<out>/markdown/<category>/`.
- `pages.txt` is the page list produced by `select_pages.py` (regenerated per run).

## The steps, in order

1. On this machine: `python bench/gpu/select_pages.py --candidate <latest run> --copy` (about 100 pages after run 6; the exact number depends on the run).
2. Ship `bench/gpu/` to the GPU machine with `scp -r` (the PDFs are small).
3. On the GPU machine: `bash run_olmocr2.sh ~/gpu/pdfs ~/gpu/out`.
4. Bring the results back: `scp` every `~/gpu/out/work_<category>/results/*.jsonl` into `bench/gpu/out/work_<category>/results/` (the pipeline's own `markdown/` copies land under a nested `root/gpu/pdfs/...` path, so the JSONL records are the reliable source). Then `python bench/gpu/merge.py place --candidate olmocr2` writes them as a benchmark candidate.
5. Merge: `python bench/gpu/merge.py merge --base <truedoc candidate> --model olmocr2 --out <name>` keeps TrueDoc's page wherever it has real text and takes the model's page where TrueDoc left the page empty (evidence first). Score the merged candidate with `score_candidate`.

## What the owner is asked to do (one-off, a few minutes)

- Create a vast.ai account and add a small credit (10 US dollars covers this comfortably).
- Add the SSH public key from `~/.ssh/truedoc_vast.pub` on this machine to the account (Account, SSH Keys).
- When asked, rent one on-demand instance: an RTX 4090 (24 GB; preferred, the default FP8 model needs it) or an RTX 3090 (24 GB; works with the bf16 model, set `MODEL=allenai/olmOCR-2-7B-1025`), at least 60 GB disk, a recent PyTorch/CUDA image (the vast.ai "PyTorch" template is fine), and paste the instance's SSH connection line (host and port) into the chat.
- Stop the instance when told the results are back.

## What happened on 3 September 2026 (first run)

RTX 4090 (48 GB) on vast.ai at US$0.335/hour, `PyTorch (Vast)` template. Upload of 46 MB took 12 minutes (slow link), `pip install olmocr[gpu]`
25 minutes, the model itself read 110 of 111 pages in about 12 minutes including a model reload per category (the script runs the pipeline
once per category folder). One page failed inside the pipeline. Total instance time about 55 minutes.

## Before uploading anything: test the link (lesson of 8 September 2026)

A Japanese host advertised at 540 Mbps ran at half a megabyte a second to PyPI and had no working IPv6 route to the package host; its install sat for twenty minutes with two packages, and the arithmetic (three gigabytes of packages, eight and a half of model weights) said hours. Ten cents lost, then a North Carolina RTX 4090 did PyPI at 15 MB/s. So, first thing after connecting:

    curl -4 -s -L -o /dev/null -w '%{http_code} %{speed_download} B/s
' --max-time 8 https://files.pythonhosted.org/packages/py3/p/pip/pip-24.0-py3-none-any.whl
    curl -4 -s -L -o /dev/null -w '%{http_code} %{speed_download} B/s
' --max-time 8 https://download.pytorch.org/whl/cu128/torch-2.7.1%2Bcu128-cp312-cp312-manylinux_2_28_x86_64.whl

Under a few megabytes a second, destroy the instance and rent another; prefer European or US hosts. The listing's bandwidth figure is no guide. If IPv6 is the trouble, `echo 'precedence ::ffff:0:0/96  100' >> /etc/gai.conf` makes the container prefer IPv4.

## What happened on 7 September 2026 (second run)

RTX 4090 (24 GB) in Hungary at US$0.382/hour, `PyTorch (Vast)` template; 33 minutes of instance time, 85 cents. New pieces: `fetch_pages.py` (the rented machine fetches the listed pages from the public Hugging Face dataset itself: 281 pages in 290 s, no upload), `poll_remote.sh <port> <host>` (a poll loop for the Monitor tool; run the file, an inline script breaks on quoting), `merge_by_list.py <base> <model> <out> <kinds> [--score]` (merge by page class and score), and `pages.txt` now carries each page's text-layer kind after a tab, written from the kinds census (`select_pages.py` still writes the old one-column form). Start the remote job with `ssh -n` or detach its stdin, or the session hangs until the job ends. Results were placed as candidate `olmocr2b` (raw JSONL in `out2/`) so the 3 September candidate `olmocr2` stays. Result: 82.7 with the model on all 281 non-digital pages (`docs/GPU_PLAN.md`).

## Picture regions on digital pages (prepared 8 September 2026, for a third session)

`select_regions.py [--min-area 0.10] [--failed <run>/failed_tests.jsonl] [--out bench/gpu/crops]` writes every picture of at least the given share of a digital page that holds none of the page's own words as a one-page PDF (`<category>/<stem>__r<i>.pdf`) with a `manifest.json` of page ids and bboxes. Run 55's failing pages at a 2% floor gave 92 crops on 60 pages (`crops_failing/`); all digital pages at a 10% floor gave 107 crops on 89 pages (`crops/`). Ship a crops folder like `pdfs/` and run `run_olmocr2.sh` over it; the readings come back keyed by crop name, which the manifest maps to page and bbox. Both folders are git-ignored.

### Session 3, step by step

1. `scp -r bench/gpu/crops_failing bench/gpu/crops root@<host>:~/gpu/` (43 MB and 34 MB; or fetch nothing: the crops are local files).
2. On the machine: `bash run_olmocr2.sh ~/gpu/crops_failing ~/gpu/out_crops` (and the same for `crops`).
3. Back here: `python bench/gpu/merge.py place --out bench/gpu/out3 --candidate olmocr2c`, then copy `bench/gpu/crops_failing/manifest.json` (and `crops/manifest.json`, concatenated) to `bench/data/olmocr-bench/bench_data/olmocr2c/manifest.json`.
4. Run 58: `EXTRA="--vision-endpoint file:bench/data/olmocr-bench/bench_data/olmocr2b+bench/data/olmocr-bench/bench_data/olmocr2c" nohup bash bench/tools/launch_run.sh 58 truedoc57 56 > bench/out/launch/nohup58.log 2>&1 &` (no `--vision-pages-only`: the region questions must be on; icons and figure descriptions come back empty from disk, picture transcriptions come from the crops).

## Session 4, step by step (prepared 8 September 2026, after run 62; not yet run)

The question: on the densest pages the model leaves text unread (77 failing checks, about 1.9
points). Does reading a third of a page at a time recover it? The pages chosen already have
whole-page readings, so the answer is a direct comparison, not a guess.

1. On this machine, cut the worst pages into bands (about 72 one-page PDFs, a few megabytes):

       python bench/gpu/select_bands.py --failed bench/runs/<latest run>/failed_tests.jsonl

2. Rent an RTX 4090 on vast.ai as before, **test the link first** (the section above), then
   upload `bench/gpu/bands/` and run `run_olmocr2.sh` over it exactly as session 3 ran the crops.
3. Fetch the readings back into `bench/gpu/out4/`, keeping the `<category>/<stem>__b<i>.md`
   layout, and copy `bench/gpu/bands/manifest.json` beside them.
4. Stitch the bands into whole-page readings and place them as a candidate folder:

       python bench/gpu/merge_bands.py bench/gpu/out4 bench/data/olmocr-bench/bench_data/olmocr2d

5. Score the banded readings against the whole-page ones on the same pages:

       python bench/gpu/merge_by_list.py <base candidate> olmocr2d <out candidate> any --score

   Use `any`, not `all`. `all` means "every page the census listed as non-digital", and the eight
   whole-page table sends are *digital* pages, so `all` discards their readings without a word:
   on 8 September that hid the only part of session 4 that worked. `any` means "every page the
   model has a reading for". Check the merge's own line ("N from olmocr2d") against the number of
   pages the stitcher wrote before believing any score.

   A gain says the treatment works and should go to every dense page; no gain says the model's
   limit is the model, and the next rental should serve a stronger one instead.

## What happened on 8 September 2026 (session 4: the answer is no)

RTX 4090 (48 GB) in California at US$0.657/hour, chosen for its link rather than its price: the
listing showed 8762 Mbps down and the pre-flight test gave 14 MB/s from both PyPI and Hugging
Face, so dependencies and the 8.5 GB of weights took **nine minutes against twenty-five in the
first session**. Eighteen minutes of instance time in all, about 40 cents. 80 bands read with
zero pipeline failures; three bands produced no file because they were near-empty page bottoms
(re-reading one returned the single word "Hubbard"), and the stitcher skipped the two pages whose
last band was empty, so 30 of 32 pages were scored.

**Result: 84.2 against run 64's 84.0.** Eleven net checks on pages that held 136 failing ones,
where the census projected 3.0 points. Old scans +5, tiny text +4, old-scan maths **-4**, the
vector-drawn tables sent whole **+5**, baseline +1. Two readings of it:

- **Banding is a wash.** It recovers text at the bottom of a dense scan and loses maths, because
  a formula cut across a band boundary is unreadable in both halves. Any rollout would have to
  exempt maths pages, and the remainder is not worth changing the vision path for.
- **It did not generalise.** Eight of the 30 pages are held-out and carry 30 of the 136 checks;
  the held-out score was identical before and after (1058 of 1255 both times). Every net gain
  landed on a tuned-on page.

Worth keeping: the eight vector-drawn-table pages. Their readings are on disk and cost nothing
more, and they point at a product rule — a digital page whose content is a table drawn as vector
paths should go to the model, the way picture-text regions already do (`select_regions.py` cannot
see them: it looks for image objects and there are none). The next rental serves a stronger model
(PaddleOCR-VL, Apache-2.0), which is where the remaining 5.5 points sit; plan it before renting.

**Also send these eight pages whole** (step 1 above): their table is a *vector drawing*, so
`select_regions.py` never cropped them (it looks for image objects, and there is none) and no
model has seen them; together they hold about twenty failing table checks.

    python bench/gpu/select_bands.py --failed bench/runs/<latest run>/failed_tests.jsonl \
        --also-whole f5e5d540,fbeb6edc,94f7559a,3d780cdc,4db371ae,8bb41f19,9921f236,8160caa0

A page sent whole arrives as a single band, so the stitcher passes its reading straight through.

## Session 5 (17 September 2026): two stronger open readers, and how to run it again

The question: the leaderboard's gap sits on the pages a model reads, so what do Infinity-Parser2-Flash (2.2B) and
-Pro (35B), both Apache-2.0, score as TrueDoc's reader? The answer is in `docs/PROGRESS_LOG.md` (run 93: 86.4
against run 92's 84.2). This is the recipe.

**The machine.** Pro's weights are about 70 GB, so one card of 140 GB or two of 80 GB (the script shards across
whatever it finds). We used 1x H200 NVL, vast.ai, Czechia datacentre, US$4.37 an hour, `PyTorch (Vast)` template,
200 GB disk, Max CUDA 13.0. Choose the host by Max CUDA 12.8 or more, x86 (never a GH200, which is ARM), a download
speed in the gigabits, and reliability; not by the template's CUDA badge, which is only the image's toolkit and
is not used. **Cost: US$12.03 for 2 h 10 min, disk and some 80 GB of downloads included - quote the owner the
all-in figure, not the GPU time.** Flash alone fits a 24 GB card.

**The files.**
- `run_bakeoff.sh <pdf_root> <out_root> [flash] [pro] [dots]` - the remote job. Builds a Python 3.12 venv with the
  image's `uv`, installs the model card's own pins (torch 2.10.0 cu128, vLLM 0.17.1, `infinity_parser2`), fetches
  the pages, starts Pro's download behind the first model, serves each model with the flags of its authors'
  olmOCR-bench guide and reads each page set through their `infer.py`. `SETS="rest own repeat"` chooses the page
  sets (folders under `<pdf_root>`), `BATCH=32` how many pages go at once, and `CUSTOM_PROMPT=<file>` reads the crops
  again under a prompt of ours through `infer_custom.py`. The `dots` stage was written and never run.
- `pages.txt` (the 281 pages without a digital text layer) and `pages_rest.txt` (the other 1,122): the rented
  machine fetches both from Hugging Face itself.
- `build_own_sets.py <folder>` - one-page PDFs of the owner's library (insurance set, Key Facts Sheets pages 1 and
  2, 100 random pages), the sealed slice excluded by name, with the `manifest.json` that names every page. The
  owner agreed these may go to a rented machine (D032). They have to be uploaded, at about 50 KB a second.
- `poll_bakeoff.sh <port> <host>` - the watch for the Monitor tool: stage markers, anything that reads as a
  failure, a line per hundred pages.
- `place_bakeoff.py infinity <set folder> <name>` - writes `<name>_raw` (the model's own markdown, from
  `inference.jsonl`) and `<name>_post` (after the authors' category-keyed post-processing) as benchmark candidates.
  Then `merge_by_list.py truedoc88 <name>_raw <out> all --score` for a number in minutes, and a full run with
  `--vision-endpoint file:<name>_raw+<olmocr2c>` for the number that counts. `--vision-deep file:<folder>` replays
  a second reader through D025's router the same way.

**Start it** with stdin detached, the log where the watch looks, and an exit line:

    ssh -n ... "(nohup bash -c 'SETS=... bash ~/gpu/run_bakeoff.sh ~/gpu/pdfs ~/gpu/out flash pro; echo \"== exit \$? \$(date +%H:%M:%S)\"' > ~/gpu/run.log 2>&1 < /dev/null &)"

Upload a changed script under a new name while a job is running: bash reads a script as it goes.

**What went wrong, once each.** A fresh vLLM server takes fifteen seconds over its first request and the authors'
client gives up its connection check after five, so the first pass wrote nothing - and a filter of mine on the log
hid the traceback (the script now warms the server and shows the client's last lines). `pkill -f run_bakeoff`
killed the shell that ran it; write `'[r]un_bakeoff'`. The image's system pip refuses to install (PEP 668). pip
reports vLLM 0.17.1 as wanting transformers below 5 and the authors' package installs 5.17; that pairing is
theirs and it works. Eight pages at a time left the card idle; 32 tripled the rate. The authors' client hands
back raw layout JSON when it cannot make markdown (a picture with nothing to read, a page of running heads, a
reading its parser chokes on): `place_bakeoff.py` turns it back into text. The scorer hung twice, for over two
hours, on the Pro-alone candidate while two conversions shared the machine: score one category at a time.

**What is on disk** (`out5/`, all of it in git, the readings of the owner's pages included - D032): Flash and Pro
on the 281 pages and the 199 crops;
Pro on the other 1,122 pages, on 505 pages of the owner's library, on the 134 old-scan pages a second time, and on
the crops under TrueDoc's picture-text prompt; `environment.txt` (every package, both model snapshots); the logs.
**Not done:** dots.mocr; Flash on none. Flash under our picture-text prompt and on a small card: session 6.

## Session 6 (18 September 2026): Flash asked our picture-text question, and how small a card it needs

D033's last check. One RTX 4090 (24 GB) on vast.ai, US, US$0.386 an hour, `PyTorch (Vast)` template, 70 GB disk,
Max CUDA 13.0; about 55 minutes of instance time. Only `crops_failing` went up (42 MB as one tarball, 32 minutes
at 20-25 KB/s - the owner's uplink, slower than earlier sessions; a second parallel stream did not clearly help,
and re-cutting the crops on the instance was declined so that every reader sees the same 92 crops). The installs
ran during the upload: `bash run_bakeoff.sh ~/gpu/pdfs ~/gpu/out prep` - an unknown stage name builds the venv
and installs the pins and does nothing else - followed by `hf download infly/Infinity-Parser2-Flash`. Then:

    SETS=none CUSTOM_PROMPT=$HOME/gpu/picture_text_prompt.txt FIT_GB="6 8 12 16" bash run_bakeoff.sh ~/gpu/pdfs ~/gpu/out flash

Server up in five minutes, 92 crops read in ten, none failed. Back here: `place_bakeoff.py infinity
bench/gpu/out5/flash_custom/crops_failing inf2flash_custom` (the custom `inference.jsonl` places like the
authors'), copy `olmocr2c/manifest.json` beside it, and convert the 60 crop pages three ways with
`bench/tools/ab_pool.py <label> --subset ... --pages <the manifest's pages> --vision file:inf2flash_raw+<crops>`.
The result is in `docs/DECISIONS.md` (D033): Flash reads most crops well and turns two of 92 into thousands of
invented words, so olmOCR 2 keeps the crops.

**The fit stage.** Flash does not serve in 6 GB of card memory; it serves in 8 (weights 4.25 GiB, KV cache 1.84
GiB at a 32k context, 8.6 GB in use), 12 and 16. **A flaw to fix before the stage is used again:** its reads all
failed with "requested 32768 output tokens" - the authors' client asks for 32k output tokens by default, and the
stage serves with `--max-model-len 32768`, so nothing fits; serve the fit budgets at the full 65536 context (which
needs a larger KV cache, so the smallest budget may move) or cap the client's output length. "Serves in 8 GB" is
shown; "reads in 8 GB" is not.

**What is on disk:** `out5/flash_custom/crops_failing/inference.jsonl` (the readings) and `out6/` (run and prep
logs, every serve log, the fit-stage outputs, `environment.txt`).
