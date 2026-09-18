"""One-page PDFs of the owner's documents for a model to read: the insurance set's 25 pages, pages 1
and 2 of every Key Facts Sheet, and one random page from each of 100 random library documents.
The sealed slice (bench/insurance_holdout.txt) is excluded by name and never opened.

    python bench/gpu/build_own_sets.py <output folder>      (repo root, the project's venv)

Writes <output folder>/insurance, /kfs and /library, and a manifest.json naming every page's
source PDF and page number - keep it beside the readings, which are keyed by these page names.
The owner agreed on 17 September 2026 that these pages may go to a rented machine (D032); the
folder itself is an input and costs nothing to remake, so it lives outside the repository.
PyMuPDF cuts the pages: this is a measurement tool, not the product path (D023)."""
import glob
import hashlib
import json
import os
import random
import sys

import pymupdf

sys.path.insert(0, os.path.join("bench", "tools"))
import kfs_grade  # noqa: E402

OUT = sys.argv[1]
sealed = {l.strip().lower() for l in open("bench/insurance_holdout.txt", encoding="utf-8") if l.strip() and not l.startswith("#")}
sealed_base = {os.path.basename(s.replace("\\", "/")) for s in sealed}


def is_sealed(path):
    return os.path.basename(path).lower() in sealed_base


def one_page(src, page, target):
    os.makedirs(os.path.dirname(target), exist_ok=True)
    doc = pymupdf.open(src)
    try:
        if page > doc.page_count:
            return False
        doc.select([page - 1])
        doc.save(target, garbage=4, deflate=True)
        return True
    finally:
        doc.close()


manifest = []
m = json.load(open("bench/out/insurance_set/manifest.json", encoding="utf-8"))
pages = m if isinstance(m, list) else next(v for v in m.values() if isinstance(v, list))
for p in pages:
    assert not is_sealed(p["pdf"]), "an insurance-set page is on the sealed list"
    if one_page(p["pdf"], p["page"], os.path.join(OUT, "insurance", p["name"] + ".pdf")):
        manifest.append({"set": "insurance", "name": p["name"], "pdf": p["pdf"], "page": p["page"]})

kfs_paths = set()
for insurer, path in kfs_grade.sheets():
    kfs_paths.add(os.path.normcase(path))
    if is_sealed(path):
        continue
    stem = os.path.splitext(os.path.basename(kfs_grade.cache_path(path)))[0]
    for page in (1, 2):
        name = "%s__p%d" % (stem, page)
        if one_page(path, page, os.path.join(OUT, "kfs", name + ".pdf")):
            manifest.append({"set": "kfs", "name": name, "pdf": path, "page": page, "held_out": kfs_grade.held_out(path)})

rng = random.Random(20260917)
docs = [p for p in sorted(glob.glob(os.path.join(kfs_grade.LIB, "*", "*", "*.pdf")))
        if os.path.normcase(p) not in kfs_paths and not is_sealed(p)
        and not p.replace("\\", "/").split("/")[-3].startswith("zz_")]
rng.shuffle(docs)
taken = 0
for path in docs:
    if taken >= 100:
        break
    try:
        n = pymupdf.open(path).page_count
    except Exception:
        continue
    page = rng.randint(1, n)
    stem = os.path.splitext(os.path.basename(path))[0][:60] + "_" + hashlib.sha1(path.encode("utf-8")).hexdigest()[:8]
    name = "%s__p%d" % (stem, page)
    if one_page(path, page, os.path.join(OUT, "library", name + ".pdf")):
        manifest.append({"set": "library", "name": name, "pdf": path, "page": page})
        taken += 1

# The manifest is committed with the readings, so it names each document relative to the library
# (doc_library.absolute puts this machine's root back).
for entry in manifest:
    entry["pdf"] = kfs_grade.doc_library.relative(entry["pdf"])
with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8") as f:
    json.dump(manifest, f, indent=1)
for s in ("insurance", "kfs", "library"):
    files = glob.glob(os.path.join(OUT, s, "*.pdf"))
    print("%-10s %4d pages  %6.1f MB" % (s, len(files), sum(os.path.getsize(x) for x in files) / 1e6))
print("sealed names excluded:", len(sealed_base), "| library documents eligible:", len(docs))
