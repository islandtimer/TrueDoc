"""Score a whole benchmark category under the current code, no model, per page.
usage: cat_score.py <category> <out-name> [--mupdf] [KEY=VAL ...]  -> bench/out/lost/<out-name>.txt"""
import json, os, re, subprocess, sys, time
REPO = os.getcwd(); B = os.path.join(REPO, "bench", "data", "olmocr-bench", "bench_data")
WORKER = os.path.join(REPO, "bench", "tools", "_generalise_worker.py")
OUT = os.path.join(REPO, "bench", "out", "lost"); os.makedirs(OUT, exist_ok=True)
cat, name = sys.argv[1], sys.argv[2]
mupdf = "--mupdf" in sys.argv
kv = dict(a.split("=", 1) for a in sys.argv[3:] if "=" in a)
files = sorted(f for f in os.listdir(os.path.join(B, "pdfs", cat)) if f.endswith(".pdf"))
jsonl = {"tables": "table_tests.jsonl"}.get(cat, f"{cat}.jsonl")
plist = [[cat, f[:-4], jsonl] for f in files]
env = dict(os.environ); env.update({"HF_HUB_DISABLE_SYMLINKS_WARNING": "1", "TRANSFORMERS_VERBOSITY": "error"})
for k in ("TRUEDOC_READER", "TRUEDOC_RENDERER", "TRUEDOC_OBJECTS"): env.pop(k, None)
if not mupdf: env.update({"TRUEDOC_READER": "pdftext", "TRUEDOC_RENDERER": "pdfium", "TRUEDOC_OBJECTS": "pdfium"})
else: env.update({"TRUEDOC_READER": "mupdf", "TRUEDOC_RENDERER": "mupdf", "TRUEDOC_OBJECTS": "mupdf"})
env.update(kv)
t0 = time.time()
print(f"{cat}: {len(plist)} pages, {'mupdf' if mupdf else 'pdfium'} {kv}", flush=True)
r = subprocess.run([sys.executable, WORKER], input=json.dumps(plist), capture_output=True, text=True, env=env, cwd=REPO)
per = {}
for line in r.stderr.splitlines():
    m = re.match(r"\s+(\S+\.pdf)\s+(\d+)/(\d+)", line)
    if m: per[m.group(1)] = (int(m.group(2)), int(m.group(3)))
tot = next((json.loads(l) for l in reversed(r.stdout.splitlines()) if l.startswith("{")), None)
with open(os.path.join(OUT, f"{name}.txt"), "w", encoding="utf-8") as fh:
    for p, (a, b) in sorted(per.items()):
        fh.write(f"{p}  {a}/{b}\n")
    fh.write(f"TOTAL {tot and tot['passed']}/{tot and tot['total']}\n")
print(f"  TOTAL {tot and tot['passed']}/{tot and tot['total']}  pages reported {len(per)}  ({time.time()-t0:.0f}s)", flush=True)
if r.returncode: print(r.stderr[-1500:])
