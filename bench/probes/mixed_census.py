"""Digital pages whose body is a picture: little text, a large image. Which sections, and how many failing checks sit on them?"""
import glob, json, os, sys, time, collections
import pymupdf
sys.path.insert(0, ".")
from truedoc.extract.textlayer import extract_page
B = "bench/data/olmocr-bench/bench_data/pdfs"
kinds = dict(l.rstrip("\n").split("\t") for l in open("bench/gpu/pages.txt", encoding="utf-8") if "\t" in l)
failing = collections.Counter()
for l in open("bench/runs/truedoc54-20260907-232523/failed_tests.jsonl", encoding="utf-8"):
    if l.strip():
        t = json.loads(l); failing[t["pdf"].replace(".pdf", "")] += 1
out = open(sys.argv[1], "w", encoding="utf-8"); t0 = time.time(); rows = []
for pdf in sorted(glob.glob(os.path.join(B, "*", "*.pdf"))):
    sub = os.path.basename(os.path.dirname(pdf)); stem = os.path.basename(pdf)[:-4]
    if sub + "/" + stem in kinds:
        continue    # not digital
    try:
        doc = pymupdf.open(pdf); page = extract_page(doc[0], 1); q = page.quality
        rows.append((sub, stem, len(page.words), round(q.image_coverage, 2), failing.get(sub + "/" + stem, 0))); doc.close()
    except Exception as e:
        print("ERR", sub, stem, repr(e)[:80], file=out)
for r in rows:
    print("%s\t%s\t%d\t%.2f\t%d" % r, file=out)
print("", file=out); print("digital pages: %d in %.0fs" % (len(rows), time.time() - t0), file=out)
for maxw, minimg in ((40, 0.5), (80, 0.5), (150, 0.6), (300, 0.7)):
    sel = [r for r in rows if r[2] <= maxw and r[3] >= minimg]
    by = collections.Counter(r[0] for r in sel)
    print("words <= %d and image >= %.1f: %d pages, %d failing checks; by section %s" % (maxw, minimg, len(sel), sum(r[4] for r in sel), dict(by)), file=out)
out.close()
print("done")
