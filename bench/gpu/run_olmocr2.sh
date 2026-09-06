#!/usr/bin/env bash
# Run olmOCR 2 over a folder of PDFs on a rented GPU machine (Linux, one 24 GB GPU).
#
#   bash run_olmocr2.sh <pdf_folder> <output_folder>
#
# Produces one markdown file per PDF in <output_folder>/markdown/<category>/<stem>.md,
# mirroring the input folder's category subfolders. Expects: Ubuntu-style image
# with CUDA drivers, Python 3.10+, internet access for pip and Hugging Face.
set -euo pipefail

PDFS=${1:?pdf folder}
OUT=${2:?output folder}
# olmocr 0.4.27 defaults to the FP8 weights, which need an FP8-capable GPU (RTX 4090 / Ada or newer).
# On an RTX 3090 / Ampere card use the bf16 weights: MODEL=allenai/olmOCR-2-7B-1025
MODEL=${MODEL:-allenai/olmOCR-2-7B-1025-FP8}

echo "== system"
nvidia-smi --query-gpu=name,memory.total --format=csv || true
python3 --version

echo "== dependencies"
# vast.ai images log in as root, often without sudo installed.
SUDO=$(command -v sudo || true)
export DEBIAN_FRONTEND=noninteractive
# The Microsoft core fonts package is left out: its licence prompt needs a person to accept it, and the
# metric-compatible free fonts (Caladea, Carlito) cover the rendering of the benchmark pages.
$SUDO apt-get update -qq && $SUDO apt-get install -y -qq python3-venv poppler-utils fonts-crosextra-caladea fonts-crosextra-carlito gsfonts lcdf-typetools >/dev/null 2>&1 || true
python3 -m venv ~/olmocr-venv
source ~/olmocr-venv/bin/activate
pip install -q --upgrade pip
pip install -q "olmocr[gpu]" --extra-index-url https://download.pytorch.org/whl/cu128 || pip install -q "olmocr[gpu]"

echo "== run"
mkdir -p "$OUT"
for cat in "$PDFS"/*/; do
  name=$(basename "$cat")
  echo "-- $name ($(ls "$cat"/*.pdf 2>/dev/null | wc -l) pdfs)"
  python3 -m olmocr.pipeline "$OUT/work_$name" --markdown --model "$MODEL" --pdfs "$cat"/*.pdf
  mkdir -p "$OUT/markdown/$name"
  cp "$OUT/work_$name"/markdown/*.md "$OUT/markdown/$name/" 2>/dev/null || true
done
echo "== done: $(find "$OUT/markdown" -name '*.md' | wc -l) markdown files"
