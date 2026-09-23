"""The text-layer verdict on every page, from the working tree and from a commit, side by side (23 September 2026).

`textlayer._assess_quality` decides which pages OCR and a vision reader read (`TextQuality.kind`). A change that must
leave that verdict alone is checked here page by page: each page is read by `extract_page` twice - once by the working
tree's module, once by the committed one loaded under another name - and every field of the verdict compared. It also
counts the pages the check turns down whose words read cleanly in their own scripts (`script_kind`). Held-out pages
(the benchmark's holdout.txt, the Key Facts oracle's fifth) are counted, never named.

usage (repo root, the project's venv):
    quality_kind_screen.py bench|kfs|insurance <out.jsonl> [workers] [--rev REV]
"""
import concurrent.futures
import dataclasses
import importlib.util
import json
import os
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "bench", "probes"))
from order_screen import jobs  # noqa: E402

_BEFORE = None


def _before(rev):
    global _BEFORE
    if _BEFORE is None:
        sys.path.insert(0, REPO)
        src = subprocess.run(["git", "show", f"{rev}:truedoc/extract/textlayer.py"], cwd=REPO, capture_output=True,
                             check=True).stdout
        path = os.path.join(tempfile.mkdtemp(), "textlayer_before.py")
        open(path, "wb").write(src)
        spec = importlib.util.spec_from_file_location("textlayer_before", path)
        _BEFORE = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_BEFORE)
    return _BEFORE


def screen(job):
    (label, path, number, secret), rev = job
    sys.path.insert(0, REPO)
    from truedoc.extract import textlayer
    from truedoc.extract.handle import open_pdf

    try:
        pdf = open_pdf(path)
        try:
            now = textlayer.extract_page(pdf[number - 1], number).quality
            then = _before(rev).extract_page(pdf[number - 1], number).quality
        finally:
            pdf.close()
    except Exception as exc:
        return {"page": label, "held_out": secret, "error": repr(exc)[:100]}
    a, b = dataclasses.asdict(now), dataclasses.asdict(then)
    a.pop("script_kind", None)
    b.pop("script_kind", None)
    return {"page": label, "held_out": secret, "kind": now.kind, "script_kind": now.script_kind,
            "same": a == b, "differs": sorted(k for k in a if a[k] != b.get(k))}


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    rev = sys.argv[sys.argv.index("--rev") + 1] if "--rev" in sys.argv else "HEAD"
    args = [a for a in args if a != rev]
    which, out = args[0], args[1]
    workers = int(args[2]) if len(args) > 2 else 6
    todo = [(j, rev) for j in jobs(which)]
    print(len(todo), "pages", flush=True)
    rows = []
    with open(out, "w", encoding="utf-8") as f, concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
        for n, r in enumerate(pool.map(screen, todo, chunksize=4), 1):
            rows.append(r)
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            if n % 200 == 0:
                print(" ", n, flush=True)
    ok = [r for r in rows if "error" not in r]
    moved = [r for r in ok if not r["same"]]
    read = [r for r in ok if r["kind"] == "suspect" and r["script_kind"] in ("digital", "ocr")]
    print("pages %d (failed %d) | verdict changed on %d | turned down but clean in their own scripts %d "
          "(tuned-on %d, held-out %d)" % (len(rows), len(rows) - len(ok), len(moved), len(read),
                                          sum(not r["held_out"] for r in read), sum(r["held_out"] for r in read)))
    for r in moved + read:
        if not r["held_out"]:
            print("  %-70s kind %-8s in its scripts %-8s %s" % (r["page"][-70:], r["kind"], r["script_kind"],
                                                              ",".join(r["differs"])))
