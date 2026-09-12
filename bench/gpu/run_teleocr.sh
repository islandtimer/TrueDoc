#!/usr/bin/env bash
# Read benchmark pages with TeleOCR on a rented GPU machine (Linux, one 24 GB card is plenty:
# the model is 1.2B, about 2.8 GB of weights).
#
#   bash run_teleocr.sh <pdf_folder> <output_folder>
#
# Writes <output_folder>/whole/<stem>.md   - one call for the whole page, comparable with the
#                                            numbers we already have for olmOCR and Claude
#        <output_folder>/layout/<stem>.md  - TeleOCR's own pipeline: layout, then a question per
#                                            block, which is how it is meant to be used
#
# Expects a recent PyTorch/CUDA image with internet access for pip and Hugging Face.
set -euo pipefail

PDFS=${1:?pdf folder}
OUT=${2:?output folder}

echo "== system"
nvidia-smi --query-gpu=name,memory.total --format=csv || true
python3 --version

echo "== link speed, because a slow host wastes more than it costs (lesson of 8 September)"
curl -4 -s -L -o /dev/null -w 'pypi: %{http_code} %{speed_download} B/s\n' --max-time 8 \
  https://files.pythonhosted.org/packages/py3/p/pip/pip-24.0-py3-none-any.whl || true
curl -4 -s -L -o /dev/null -w 'huggingface: %{http_code} %{speed_download} B/s\n' --max-time 8 \
  https://huggingface.co/StarDoc-AI/TeleOCR/resolve/main/config.json || true

echo "== dependencies"
python3 -m pip install -q --upgrade pip
python3 -m pip install -q "transformers>=4.49" accelerate pypdfium2 pillow
python3 -c "import torch; print('torch', torch.__version__, 'cuda', torch.cuda.is_available())"

echo "== reading $(find "$PDFS" -name '*.pdf' | wc -l) pages"
mkdir -p "$OUT"
python3 teleocr_pages.py "$PDFS" "$OUT" 2>&1 | tee "$OUT/run.log"

echo "== done; bring back $OUT/whole and $OUT/layout"
du -sh "$OUT"/whole "$OUT"/layout 2>/dev/null || true
