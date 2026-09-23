"""Which pages a change to the reading order can reach: every page of a population converted once, with the order
asked of both code states.

Reading order (`truedoc/segment/order.py`) is a function of the blocks a page is built with, so a change to it can
alter only the pages where the two states order the same blocks differently. This converts each page with the working
tree (layout model on, no vision reader - the A/B pool's options), and at the moment the pipeline orders a page's
blocks it asks the order module of the other state as well (a copy of the file, loaded under another name), and records
whether the two differ. The pages that differ are the only ones to score both ways and to read. Held-out pages (the
benchmark's holdout.txt, the Key Facts oracle's fifth) are counted, never named.

usage (repo root, the project's venv):
    order_screen.py <order_before.py> bench|kfs|insurance <out.jsonl> [workers]
"""
import concurrent.futures
import glob
import importlib.util
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "bench", "probes"))
sys.path.insert(0, os.path.join(REPO, "bench", "tools"))


def jobs(which):
    if which == "bench":
        b = os.path.join(REPO, "bench", "data", "olmocr-bench", "bench_data", "pdfs")
        held = {l.strip()[:-4] for l in open(os.path.join(REPO, "bench", "holdout.txt"), encoding="utf-8")
                if l.strip() and not l.startswith("#")}
        for p in sorted(glob.glob(os.path.join(b, "*", "*.pdf"))):
            label = os.path.basename(os.path.dirname(p)) + "/" + os.path.basename(p)[:-4]
            yield (label, p, 1, label in held)
    else:
        from orphan_row_census import jobs as population
        yield from population(which)


def screen(job, before_path):
    label, path, number, secret = job
    sys.path.insert(0, REPO)
    import truedoc
    import truedoc.pipeline as pipeline
    from truedoc.segment import order as new
    spec = importlib.util.spec_from_file_location("order_before", before_path)
    old = importlib.util.module_from_spec(spec)
    sys.modules["order_before"] = old
    spec.loader.exec_module(old)
    seen = []

    def both(blocks, width, body):
        old.assign_reading_order(blocks, width, body)
        was = [b.order for b in blocks]
        new.assign_reading_order(blocks, width, body)
        seen.append(was != [b.order for b in blocks])

    pipeline.assign_reading_order = both
    try:
        pipeline.load_document(path, pipeline.ConvertOptions(frontmatter=False, pages=[number]))
    except Exception as exc:
        return {"page": label, "held_out": secret, "error": repr(exc)[:100]}
    return {"page": label, "held_out": secret, "changed": any(seen), "code": os.path.dirname(truedoc.__file__)}


if __name__ == "__main__":
    before, which, out = sys.argv[1], sys.argv[2], sys.argv[3]
    workers = int(sys.argv[4]) if len(sys.argv) > 4 else 6
    todo = list(jobs(which))
    print(len(todo), "pages", flush=True)
    rows = []
    with open(out, "w", encoding="utf-8") as f, concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
        for n, r in enumerate(pool.map(screen, todo, [os.path.abspath(before)] * len(todo), chunksize=2), 1):
            rows.append(r)
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            if n % 100 == 0:
                print(" ", n, flush=True)
    changed = [r for r in rows if r.get("changed")]
    print("pages %d (failed %d) | order differs on %d: tuned-on %d, held-out %d (counted, never named) | code %s" % (
        len(rows), sum("error" in r for r in rows), len(changed), sum(not r["held_out"] for r in changed),
        sum(r["held_out"] for r in changed), {r.get("code") for r in rows} - {None}))
    for r in changed:
        if not r["held_out"]:
            print("  ", r["page"])
