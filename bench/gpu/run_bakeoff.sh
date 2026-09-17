#!/usr/bin/env bash
# Reader bake-off on a rented GPU machine (Linux; one 141 GB card, or two 80 GB cards):
# Infinity-Parser2-Flash and -Pro (Apache-2.0) and dots.mocr (MIT) over the same one-page
# benchmark PDFs, each through its authors' own client, so a reading is what they would publish.
#
#   bash run_bakeoff.sh <pdf_root> <out_root> [flash] [pro] [dots]      (default: flash pro)
#
# <pdf_root> holds one folder per page set - pdfs/ (whole pages), and crops_failing/ and crops/
# when they have been uploaded - each with the benchmark's category subfolders. It leaves
#
#   <out_root>/markdown/<model>/<set>/inference.jsonl    Infinity: the model's RAW markdown, a line per PDF
#   <out_root>/markdown/<model>/<set>/<category>/*.md    Infinity: after its authors' post-processing, which
#                                                        is keyed on the benchmark's category names
#   <out_root>/markdown/dots/<set>/<category>/<stem>/    dots.mocr: <stem>*.md and <stem>*_nohf.md
#
# and a log per server under <out_root>/. Stages are independent: one that fails is reported and
# the next still runs. Expects the vast.ai PyTorch template or the like: root, CUDA 12.8 drivers
# or newer, internet access for pip, GitHub and Hugging Face.
set -uo pipefail

PDFROOT=${1:?pdf root}
OUT=${2:?output root}
shift 2
STAGES=${*:-flash pro}
HERE=$(cd "$(dirname "$0")" && pwd)
VENV=~/venv-inf
PORT=8000
mkdir -p "$OUT"

echo "== system"
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv || true
NGPU=$(nvidia-smi -L 2>/dev/null | wc -l)
df -h ~ | tail -1
df -h /dev/shm | tail -1

echo "== link speed, because a slow host wastes more than it costs (lesson of 8 September)"
curl -4 -s -L -o /dev/null -w 'pypi: %{http_code} %{speed_download} B/s\n' --max-time 8 \
  https://files.pythonhosted.org/packages/py3/p/pip/pip-24.0-py3-none-any.whl || true
curl -4 -s -L -o /dev/null -w 'huggingface: %{http_code} %{speed_download} B/s\n' --max-time 8 \
  https://huggingface.co/infly/Infinity-Parser2-Pro/resolve/main/config.json || true

echo "== dependencies"
export DEBIAN_FRONTEND=noninteractive
SUDO=$(command -v sudo || true)
$SUDO apt-get update -qq >/dev/null 2>&1 && $SUDO apt-get install -y -qq git curl >/dev/null 2>&1 || true
if [ ! -x "$VENV/bin/python" ]; then
  # infinity_parser2 wants Python 3.12 and the image may not have it: uv brings its own.
  # The vast.ai image ships uv; its system pip refuses to install anything (PEP 668).
  UV=$(command -v uv || true)
  if [ -z "$UV" ]; then
    python3 -m pip install -q --break-system-packages uv
    UV=$(python3 -c 'import uv; print(uv.find_uv_bin())')
  fi
  "$UV" venv --seed --python 3.12 "$VENV"
fi
source "$VENV/bin/activate"
python --version
# The order and the pins are the model card's own; flash-attn is left out because only the
# transformers backend uses it and we serve with vLLM.
pip install -q torch==2.10.0 torchvision==0.25.0 --index-url https://download.pytorch.org/whl/cu128
pip install -q vllm==0.17.1
pip install -q infinity_parser2 hf_transfer
python -c "import torch, vllm, transformers; print('torch', torch.__version__, 'cuda', torch.cuda.is_available(), 'vllm', vllm.__version__, 'transformers', transformers.__version__)"
export HF_HUB_ENABLE_HF_TRANSFER=1 HF_XET_HIGH_PERFORMANCE=1

if [ ! -d ~/INF-MLLM ]; then
  git clone -q --depth 1 --filter=blob:none --sparse https://github.com/infly-ai/INF-MLLM.git ~/INF-MLLM
  (cd ~/INF-MLLM && git sparse-checkout set Infinity-Parser2/evaluation)
fi
echo "INF-MLLM at $(cd ~/INF-MLLM && git rev-parse --short HEAD)"

echo "== pages"
if [ -f "$HERE/pages.txt" ]; then
  python "$HERE/fetch_pages.py" "$HERE/pages.txt" "$PDFROOT/pdfs" | tail -3
fi
# SETS=rest reads the rest of the benchmark, the pages that have a text layer: pages_rest.txt is
# every benchmark page pages.txt does not list. BATCH is how many pages the client sends at once.
SETS=${SETS:-pdfs crops_failing crops}
BATCH=${BATCH:-8}
case " $SETS " in *" rest "*)
  python "$HERE/fetch_pages.py" "$HERE/pages_rest.txt" "$PDFROOT/rest" | tail -3;;
esac
for set in $SETS; do
  [ -d "$PDFROOT/$set" ] && echo "$set: $(find "$PDFROOT/$set" -name '*.pdf' | wc -l) pdfs"
done

# The big download starts now and runs behind the first model's reading.
case " $STAGES " in *" pro "*)
  nohup hf download infly/Infinity-Parser2-Pro > "$OUT/download_pro.log" 2>&1 &
  echo "== Pro weights downloading in the background (pid $!)";;
esac

stop_server() {
  pkill -f "[v]llm serve" 2>/dev/null
  for _ in $(seq 1 60); do
    used=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | sort -n | tail -1)
    [ "${used:-0}" -lt 2000 ] && return 0
    sleep 5
  done
  pkill -9 -f "vllm" 2>/dev/null; sleep 10
}

wait_server() {  # <log> <served name> ; up to 40 minutes, since the first start may still be downloading weights
  for _ in $(seq 1 240); do
    if curl -s -o /dev/null "http://127.0.0.1:$PORT/v1/models"; then
      # A fresh server takes some fifteen seconds over its first request, and the authors' client
      # gives up its connection check after five: the first request is ours.
      curl -s -o /dev/null --max-time 300 "http://127.0.0.1:$PORT/v1/chat/completions" -H 'Content-Type: application/json' \
        -d "{\"model\":\"$2\",\"messages\":[{\"role\":\"user\",\"content\":\"ping\"}],\"max_tokens\":1}"
      return 0
    fi
    pgrep -f "[v]llm serve" >/dev/null || { echo "server died:"; tail -n 25 "$1"; return 1; }
    sleep 10
  done
  echo "server never came up:"; tail -n 25 "$1"; return 1
}

infinity() {  # <tag> <model> [extra vllm flags]
  local tag=$1 model=$2; shift 2
  echo "== $tag: serving $model"
  # The flags are the ones in the authors' olmOCR-bench guide, less the two that only change speed
  # (--mm-encoder-tp-mode data, --mm-processor-cache-type shm: a rented container's /dev/shm is small).
  if pgrep -f "[v]llm serve $model" >/dev/null; then
    echo "a server for $model is already running; using it"
  else
    nohup vllm serve "$model" --trust-remote-code \
      --default-chat-template-kwargs '{"enable_thinking": false}' \
      --chat-template-content-format openai --host 127.0.0.1 --port $PORT \
      --gpu-memory-utilization 0.85 --max-model-len 65536 --max-num-batched-tokens 32768 \
      --enable-prefix-caching --served-model-name inf-mllm "$@" > "$OUT/serve_$tag.log" 2>&1 &
  fi
  if ! wait_server "$OUT/serve_$tag.log" inf-mllm; then echo "== $tag FAILED to serve"; stop_server; return 1; fi
  echo "== $tag: server up $(date +%H:%M:%S)"
  for set in $SETS; do
    [ -d "$PDFROOT/$set" ] || continue
    echo "-- $tag $set"
    (cd ~/INF-MLLM/Infinity-Parser2/evaluation/olmocr-bench && \
      python infer.py --pdf_dir "$PDFROOT/$set" --output_dir "$OUT/markdown/$tag/$set" --batch_size "$BATCH" 2>&1 | grep -a -v "^\[infer\] batch" | tail -n 12 | cut -c1-300 )
  done
  if [ -n "${CUSTOM_PROMPT:-}" ]; then
    # The picture crops again, under TrueDoc's own question instead of the authors' layout task.
    for set in crops_failing crops; do
      [ -d "$PDFROOT/$set" ] || continue
      echo "-- $tag $set, custom prompt"
      python "$HERE/infer_custom.py" "$PDFROOT/$set" "$OUT/markdown/${tag}_custom/$set" "$CUSTOM_PROMPT" 2>&1 | grep -a "FAILED\|\[custom\]" | tail -n 8 | cut -c1-300
    done
  fi
  stop_server
  echo "== $tag: done $(date +%H:%M:%S), $(find "$OUT/markdown/$tag" -name '*.md' | wc -l) markdown files"
}

dots() {
  echo "== dots: serving rednote-hilab/dots.mocr"
  [ -d ~/dots_mocr_repo ] || git clone -q --depth 1 https://github.com/rednote-hilab/dots.mocr.git ~/dots_mocr_repo
  echo "dots.mocr at $(cd ~/dots_mocr_repo && git rev-parse --short HEAD)"
  CUDA_VISIBLE_DEVICES=0 nohup vllm serve rednote-hilab/dots.mocr --tensor-parallel-size 1 \
    --gpu-memory-utilization 0.9 --chat-template-content-format string --served-model-name model \
    --trust-remote-code --host 127.0.0.1 --port $PORT > "$OUT/serve_dots.log" 2>&1 &
  if ! wait_server "$OUT/serve_dots.log" model; then echo "== dots FAILED to serve"; stop_server; return 1; fi
  echo "== dots: server up $(date +%H:%M:%S)"
  for set in $SETS; do
    [ -d "$PDFROOT/$set" ] || continue
    for cat in "$PDFROOT/$set"/*/; do
      name=$(basename "$cat")
      echo "-- dots $set/$name"
      # The authors' parser takes one file at a time; eight at once keeps the card busy.
      (cd ~/dots_mocr_repo && find "$cat" -name '*.pdf' -print0 | \
        PYTHONPATH=~/dots_mocr_repo xargs -0 -P 8 -I{} python dots_mocr/parser.py {} \
          --output "$OUT/markdown/dots/$set/$name" --num_thread 1 > "$OUT/dots_${set}_$name.log" 2>&1)
      grep -a -E "Traceback|Error" "$OUT/dots_${set}_$name.log" | sort | uniq -c | head -5
    done
  done
  stop_server
  echo "== dots: done $(date +%H:%M:%S), $(find "$OUT/markdown/dots" -name '*.md' | wc -l) markdown files"
}

for stage in $STAGES; do
  case $stage in
    flash) CUDA_VISIBLE_DEVICES=0 infinity flash infly/Infinity-Parser2-Flash ;;
    pro)   echo "== waiting for the Pro weights"; wait; tail -n 2 "$OUT/download_pro.log"
           if [ "$NGPU" -gt 1 ]; then infinity pro infly/Infinity-Parser2-Pro --tensor-parallel-size "$NGPU"
           else infinity pro infly/Infinity-Parser2-Pro; fi ;;
    dots)  dots ;;
    *)     echo "unknown stage $stage" ;;
  esac
done
echo "== done: $(find "$OUT/markdown" -name '*.md' | wc -l) markdown files"
