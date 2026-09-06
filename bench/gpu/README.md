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
