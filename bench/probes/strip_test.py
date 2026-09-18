"""Hour test: the running-head witness applied to the all-pages merge, from disk.

Copies candidate truedoc53_v2all to truedoc53_v2strip, applies strip_running_heads to each of the
281 model pages with the witness lines from witness.json, scores the result, and prints what was
dropped and the score against v2all.
"""
import json
import os
import shutil
import subprocess
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)
from truedoc.vision.witness import strip_running_heads  # noqa: E402

BENCH = os.path.join(REPO, "bench", "data", "olmocr-bench", "bench_data")
witness = json.load(open(sys.argv[1], encoding="utf-8"))
src, dst = os.path.join(BENCH, "truedoc53_v2all"), os.path.join(BENCH, "truedoc53_v2strip")
if os.path.exists(dst):
    shutil.rmtree(dst)
shutil.copytree(src, dst)
n_pages = n_dropped_pages = n_lines = 0
examples = []
for page_id, rec in witness.items():
    cat, stem = page_id.split("/", 1)
    path = os.path.join(dst, cat, stem + "_pg1_repeat1.md")
    if not os.path.exists(path):
        continue
    text = open(path, encoding="utf-8").read()
    if not text.strip():
        continue
    n_pages += 1
    top = [t for t, _, _ in rec.get("top", [])]
    bottom = [t for t, _, _ in rec.get("bottom", [])]
    out, dropped = strip_running_heads(text, top, bottom)
    if dropped:
        n_dropped_pages += 1
        n_lines += len(dropped)
        if len(examples) < 25:
            examples.append((page_id[:40], rec.get("source"), [d[:70] for d in dropped]))
        open(path, "w", encoding="utf-8", newline="\n").write(out + "\n")
print("model pages %d; pages with a line dropped %d; lines dropped %d" % (n_pages, n_dropped_pages, n_lines))
for e in examples:
    print("  ", e)
run_dir = os.path.join(REPO, "bench", "runs", "truedoc53_v2strip-%s" % time.strftime("%Y%m%d-%H%M%S"))
os.makedirs(run_dir, exist_ok=True)
py = os.path.join(REPO, ".venv", "Scripts", "python.exe")
subprocess.run([py, "-c", "import sys; from truedoc.bench.olmocr import score_candidate; score_candidate(sys.argv[1], sys.argv[2])", "truedoc53_v2strip", run_dir], cwd=REPO, capture_output=True, text=True, encoding="utf-8")
subprocess.run([py, os.path.join("bench", "holdout_score.py"), run_dir], cwd=REPO, capture_output=True, text=True, encoding="utf-8")
prev = sorted(d for d in os.listdir(os.path.join(REPO, "bench", "runs")) if d.startswith("truedoc53_v2all-"))[-1]
res = subprocess.run([py, os.path.join("bench", "tools", "run_summary.py"), run_dir, os.path.join("bench", "runs", prev)], cwd=REPO, capture_output=True, text=True, encoding="utf-8")
print(res.stdout[:3000])
