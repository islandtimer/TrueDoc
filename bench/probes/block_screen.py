"""Which pages the block builder groups differently from a commit's (23 September 2026).

`segment/blocks.build_blocks` turns a page's lines into blocks. Every page of a population is read once (the text layer,
no layout model), its lines grouped by the working tree's builder and by the committed one - loaded under another name
- and the two groupings compared line by line. The pages it names are the only ones whose blocks the change can reach
before the later stages, so they are the ones to convert both ways and to read. Held-out pages (the benchmark's
holdout.txt, the Key Facts oracle's fifth, the library's odd half) are counted, never named, and none of their text
kept.

usage (repo root, the project's venv):
    block_screen.py bench|kfs|insurance|library <out.jsonl> [workers] [--rev REV] [--now FILE]

`--now FILE` takes the builder to try from a file instead of the working tree, so a change can be screened before it is
written into the package; `TRUEDOC_ROOT=<folder>` reads the pages with the package in that folder (a copy holding the
change's other files).
"""
import concurrent.futures
import importlib.util
import json
import os
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.environ.get("TRUEDOC_ROOT", REPO)
sys.path.insert(0, os.path.join(REPO, "bench", "probes"))
from order_screen import jobs as page_jobs  # noqa: E402

_BEFORE = None
_NOW = None


def _now(path):
    global _NOW
    if _NOW is None:
        if not path:
            from truedoc.segment import blocks
            _NOW = blocks
        else:
            spec = importlib.util.spec_from_file_location("blocks_now", path)
            _NOW = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(_NOW)
    return _NOW


def _before(rev):
    global _BEFORE
    if _BEFORE is None:
        sys.path.insert(0, REPO)
        src = subprocess.run(["git", "show", f"{rev}:truedoc/segment/blocks.py"], cwd=REPO, capture_output=True,
                             check=True).stdout
        path = os.path.join(tempfile.mkdtemp(), "blocks_before.py")
        open(path, "wb").write(src)
        spec = importlib.util.spec_from_file_location("blocks_before", path)
        _BEFORE = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_BEFORE)
    return _BEFORE


def _grouping(blocks, lines):
    where = {id(l): i for i, l in enumerate(lines)}
    return sorted(sorted(where[id(l)] for l in b.lines if id(l) in where) for b in blocks)


def jobs(which):
    if which != "library":
        yield from page_jobs(which)
        return
    import side_label_icon_census as census
    import pymupdf
    for key, path, _pages, secret, _insurer, _k in census.jobs("library"):
        try:
            n = len(pymupdf.open(path))
        except Exception:
            continue
        for number in range(1, n + 1):
            yield (key + "#" + str(number), path, number, secret)


def screen(job):
    (label, path, number, secret), rev, now_path = job
    sys.path.insert(0, ROOT)
    from truedoc.extract.handle import open_pdf
    from truedoc.extract.textlayer import extract_page
    now = _now(now_path)

    try:
        pdf = open_pdf(path)
        try:
            page = extract_page(pdf[number - 1], number)
        finally:
            pdf.close()
        lines = sorted(page.lines, key=lambda l: (round(l.bbox.y0, 1), l.bbox.x0))
        a = _grouping(now.build_blocks(page, lines), lines)
        b = _grouping(_before(rev).build_blocks(page, lines), lines)
    except Exception as exc:
        return {"page": label, "held_out": secret, "error": repr(exc)[:100]}
    if a == b:
        return {"page": label, "held_out": secret, "same": True}
    moved = sum(1 for g in a if g not in b)
    return {"page": label, "held_out": secret, "same": False, "blocks_before": len(b), "blocks_now": len(a),
            "new_groups": moved}


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    rev = sys.argv[sys.argv.index("--rev") + 1] if "--rev" in sys.argv else "HEAD"
    now_path = sys.argv[sys.argv.index("--now") + 1] if "--now" in sys.argv else None
    args = [a for a in args if a not in (rev, now_path)]
    which, out = args[0], args[1]
    workers = int(args[2]) if len(args) > 2 else 6
    todo = [(j, rev, now_path) for j in jobs(which)]
    print(len(todo), "pages", flush=True)
    rows = []
    with open(out, "w", encoding="utf-8") as f, concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
        for n, r in enumerate(pool.map(screen, todo, chunksize=8), 1):
            rows.append(r)
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            if n % 1000 == 0:
                print(" ", n, flush=True)
    hit = [r for r in rows if r.get("same") is False]
    docs = {r["page"].split("#")[0] for r in hit}
    print("pages %d (failed %d) | grouped differently %d: tuned-on %d, held-out %d (counted, never named) | documents %d" % (
        len(rows), sum("error" in r for r in rows), len(hit), sum(not r["held_out"] for r in hit),
        sum(r["held_out"] for r in hit), len(docs)))
    for r in hit:
        if not r["held_out"]:
            print("  %-90s blocks %d -> %d" % (r["page"][-90:], r["blocks_before"], r["blocks_now"]))
