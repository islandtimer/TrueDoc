"""Merge a model candidate into a TrueDoc candidate by page class, then score.

    python merge_by_list.py <base> <model> <out> <kinds> [--score]

<kinds> is a comma list drawn from bench/gpu/pages.txt's kind column (none, ocr, suspect) or
"blank" (only pages whose base output is under 20 characters, the old rule) or "all" (every
page the model read). The model's page is taken for every listed page that it has a reading
for; every other page keeps TrueDoc's. With --score the official scorer and the held-out split
run and a one-line summary is printed, so several merges can be compared in one sitting.
"""
import os
import shutil
import subprocess
import sys
import time

REPO = r"C:\Users\griff\OneDrive\Documents\10 Have a crack\31b TrueDoc_Fable"
BENCH = os.path.join(REPO, "bench", "data", "olmocr-bench", "bench_data")
base, model, out, kinds = sys.argv[1:5]
score = "--score" in sys.argv
kinds = set(kinds.split(","))

pages = {}
for line in open(os.path.join(REPO, "bench", "gpu", "pages.txt"), encoding="utf-8"):
    if "\t" in line:
        page, kind = line.rstrip("\n").split("\t")
        pages[page] = kind

base_dir, model_dir, out_dir = (os.path.join(BENCH, n) for n in (base, model, out))
if os.path.exists(out_dir):
    shutil.rmtree(out_dir)
taken = kept = 0
for category in sorted(os.listdir(base_dir)):
    src = os.path.join(base_dir, category)
    if not os.path.isdir(src):
        continue
    os.makedirs(os.path.join(out_dir, category), exist_ok=True)
    for name in os.listdir(src):
        stem = name.replace("_pg1_repeat1.md", "")
        page = category + "/" + stem
        alt = os.path.join(model_dir, category, name)
        text = open(os.path.join(src, name), encoding="utf-8").read()
        # "all" means every page the census listed as non-digital; "any" means every page the
        # model has a reading for, digital ones included. Session 4's whole-page table sends are
        # digital pages (their table is a vector drawing), so "all" silently dropped them.
        want = ("any" in kinds) or ("all" in kinds and page in pages) or pages.get(page) in kinds or ("blank" in kinds and len(text.strip()) < 20)
        if want and os.path.exists(alt) and open(alt, encoding="utf-8").read().strip():
            shutil.copyfile(alt, os.path.join(out_dir, category, name))
            taken += 1
        else:
            shutil.copyfile(os.path.join(src, name), os.path.join(out_dir, category, name))
            kept += 1
print("%s: %d pages from %s, %d from %s (kinds %s)" % (out, kept, base, taken, model, ",".join(sorted(kinds))))

if score:
    run_dir = os.path.join(REPO, "bench", "runs", "%s-%s" % (out, time.strftime("%Y%m%d-%H%M%S")))
    os.makedirs(run_dir, exist_ok=True)
    py = os.path.join(REPO, ".venv", "Scripts", "python.exe")
    subprocess.run([py, "-c", "import sys; from truedoc.bench.olmocr import score_candidate; score_candidate(sys.argv[1], sys.argv[2])", out, run_dir],
                   cwd=REPO, capture_output=True, text=True, encoding="utf-8")
    ho = subprocess.run([py, os.path.join("bench", "holdout_score.py"), run_dir], cwd=REPO, capture_output=True, text=True, encoding="utf-8").stdout
    import json
    s = json.load(open(os.path.join(run_dir, "summary.json"), encoding="utf-8"))
    held = [l for l in ho.splitlines() if "held-out" in l]
    print("SCORE %s: overall %s | %s | %s" % (out, s.get("overall"), " ".join("%s %s" % (k, v) for k, v in sorted(s.items()) if k not in ("overall", "candidate", "run_dir", "ci")), held[-1].strip() if held else ""))
    print("run dir:", run_dir)
