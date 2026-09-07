"""On the GPU machine: fetch the listed benchmark pages straight from Hugging Face.

    python3 fetch_pages.py pages.txt ~/gpu/pdfs

pages.txt holds one "category/stem<TAB>kind" per line (written by the kinds census on the
owner's machine). The benchmark's PDFs are public (dataset allenai/olmOCR-bench, files under
bench_data/pdfs/<category>/<stem>.pdf), so the rented machine downloads them itself at
datacentre speed instead of receiving them over the owner's uplink (46 MB took 12 minutes on
3 September). Falls back gracefully: any page that cannot be fetched is listed at the end, and
those can still be sent with scp.
"""
import os
import shutil
import sys
import time

from huggingface_hub import hf_hub_download

REPO_ID = "allenai/olmOCR-bench"
list_path, out_dir = sys.argv[1], sys.argv[2]
pages = [line.split("\t")[0].strip() for line in open(list_path, encoding="utf-8") if line.strip()]
print("pages to fetch:", len(pages))
missing = []
t0 = time.time()
for i, page in enumerate(pages, 1):
    cat, stem = page.split("/", 1)
    target_dir = os.path.join(out_dir, cat)
    os.makedirs(target_dir, exist_ok=True)
    target = os.path.join(target_dir, stem + ".pdf")
    if os.path.exists(target):
        continue
    try:
        got = hf_hub_download(repo_id=REPO_ID, repo_type="dataset", filename="bench_data/pdfs/%s/%s.pdf" % (cat, stem))
        shutil.copyfile(got, target)
    except Exception as e:  # noqa: BLE001
        missing.append((page, repr(e)[:120]))
    if i % 50 == 0:
        print("  %d/%d after %.0fs" % (i, len(pages), time.time() - t0), flush=True)
print("fetched %d of %d in %.0fs" % (len(pages) - len(missing), len(pages), time.time() - t0))
for page, err in missing:
    print("MISSING", page, err)
