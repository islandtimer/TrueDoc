"""Count benchmark pages by text-layer kind and section (no OCR run): sizes the vision session."""
import collections, glob, os, sys, time
import pymupdf
sys.path.insert(0, ".")
from truedoc.extract.textlayer import extract_page
B = "bench/data/olmocr-bench/bench_data/pdfs"
out = open(sys.argv[1], "w", encoding="utf-8")
c = collections.Counter(); t0 = time.time()
for pdf in sorted(glob.glob(os.path.join(B, "*", "*.pdf"))):
    sub = os.path.basename(os.path.dirname(pdf))
    try:
        doc = pymupdf.open(pdf); page = extract_page(doc[0], 1); kind = page.quality.kind; doc.close()
    except Exception as e:
        kind = "error"
    c[(sub, kind)] += 1
    print(sub, os.path.basename(pdf), kind, file=out, flush=True)
print("", file=out)
print("elapsed %.0fs" % (time.time() - t0), file=out)
secs = sorted({k[0] for k in c}); kinds = sorted({k[1] for k in c})
print("%-16s" % "section" + "".join("%10s" % k for k in kinds) + "%8s" % "total", file=out)
for s in secs:
    row = [c[(s, k)] for k in kinds]
    print("%-16s" % s + "".join("%10d" % v for v in row) + "%8d" % sum(row), file=out)
print("%-16s" % "all" + "".join("%10d" % sum(c[(s, k)] for s in secs) for k in kinds) + "%8d" % sum(c.values()), file=out)
out.close()
