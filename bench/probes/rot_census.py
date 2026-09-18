"""Census of benchmark pages whose content lies on its side.

For every benchmark PDF: the /Rotate attribute, whether it has a text layer, and
(a) for text-layer pages, the share of text-layer lines whose direction is vertical;
(b) for image-only pages, the OCR result as-is: line count, confidence, word-likeness,
    language-likeness and the share of OCR boxes that are taller than wide.
Also records whether run 37's output for the page is empty and how many checks the
page has and failed. Writes rot_census.json and prints the candidates.
"""
import glob
import json
import os
import sys
import time

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
import pymupdf  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)
from truedoc.ocr.rapid import ocr_page, _looks_like_text, _looks_like_language  # noqa: E402

B = os.path.join(REPO, "bench", "data", "olmocr-bench", "bench_data")
RUN = os.path.join(REPO, "bench", "runs", "truedoc36-20260905-034810")
CAND = "truedoc36"
HERE = os.path.dirname(os.path.abspath(__file__))

failed = {}
for line in open(os.path.join(RUN, "failed_tests.jsonl"), encoding="utf-8"):
    if line.strip():
        t = json.loads(line)
        failed.setdefault(t["pdf"], 0)
        failed[t["pdf"]] += 1
tests = {}
for jl in glob.glob(os.path.join(B, "*.jsonl")):
    for line in open(jl, encoding="utf-8"):
        if line.strip():
            t = json.loads(line)
            tests.setdefault(t["pdf"], 0)
            tests[t["pdf"]] += 1

rows = []
t0 = time.time()
pdfs = sorted(glob.glob(os.path.join(B, "pdfs", "*", "*.pdf")))
for i, pdf in enumerate(pdfs):
    subset = os.path.basename(os.path.dirname(pdf))
    name = os.path.basename(pdf)
    key = subset + "/" + name
    stem = name[:-4]
    out_md = os.path.join(B, CAND, subset, stem + "_pg1_repeat1.md")
    try:
        out_len = len(open(out_md, encoding="utf-8").read().strip()) if os.path.exists(out_md) else -1
    except Exception:
        out_len = -2
    row = {"pdf": key, "tests": tests.get(key, 0), "failed": failed.get(key, 0), "out_len": out_len}
    try:
        doc = pymupdf.open(pdf)
        pg = doc[0]
    except Exception as e:
        row["error"] = str(e)[:80]
        rows.append(row)
        continue
    row["rotate_attr"] = pg.rotation
    row["w"], row["h"] = round(pg.rect.width), round(pg.rect.height)
    d = pg.get_text("dict")
    n_lines = n_vert = n_chars = 0
    for b in d["blocks"]:
        for l in b.get("lines", []):
            txt = "".join(s["text"] for s in l["spans"]).strip()
            if len(txt) < 2:
                continue
            n_lines += 1
            n_chars += len(txt)
            dx, dy = l["dir"]
            if abs(dy) > abs(dx):
                n_vert += 1
    row["tl_lines"], row["tl_vertical"], row["tl_chars"] = n_lines, n_vert, n_chars
    if n_chars < 20:
        try:
            lines, conf = ocr_page(pg)
            row["ocr_lines"] = len(lines)
            row["ocr_conf"] = round(conf, 2)
            row["ocr_wordlike"] = round(_looks_like_text(lines), 2) if lines else 0
            row["ocr_langlike"] = round(_looks_like_language(lines), 2) if lines else 0
            row["ocr_vertical"] = sum(1 for l in lines if l.bbox.height > l.bbox.width)
            row["ocr_chars"] = sum(len(w.text) for l in lines for w in l.words)
        except Exception as e:
            row["ocr_error"] = str(e)[:80]
    rows.append(row)
    if (i + 1) % 100 == 0:
        print("...", i + 1, "of", len(pdfs), "%.0fs" % (time.time() - t0), flush=True)

json.dump(rows, open(os.path.join(HERE, "rot_census.json"), "w"), indent=0)
print("pages", len(rows), "time %.0fs" % (time.time() - t0))
print("\n== text-layer pages with mostly vertical lines ==")
for r in rows:
    if r.get("tl_lines", 0) >= 3 and r["tl_vertical"] >= 0.5 * r["tl_lines"]:
        print(r["pdf"], "lines", r["tl_lines"], "vertical", r["tl_vertical"], "rotate_attr", r["rotate_attr"], "tests", r["tests"], "failed", r["failed"], "out_len", r["out_len"])
print("\n== image-only pages with mostly vertical OCR boxes ==")
for r in rows:
    if r.get("ocr_lines", 0) >= 3 and r["ocr_vertical"] >= 0.5 * r["ocr_lines"]:
        print(r["pdf"], "ocr lines", r["ocr_lines"], "vertical", r["ocr_vertical"], "conf", r["ocr_conf"], "wordlike", r["ocr_wordlike"], "langlike", r["ocr_langlike"], "tests", r["tests"], "failed", r["failed"], "out_len", r["out_len"])
print("\n== image-only pages, all (for the record) ==")
n_img = sum(1 for r in rows if "ocr_lines" in r or "ocr_error" in r)
print("image-only pages", n_img, "empty outputs", sum(1 for r in rows if r["out_len"] == 0))
