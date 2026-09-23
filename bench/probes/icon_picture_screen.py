"""Which pages the icon rule reaches: every page of a population converted once with the working tree, and the pictures
it declined to write as figures (`pipeline._icons_are_not_pictures`, recorded with the page's decisions) counted.

The rule only takes figure blocks out, so a page where it took none converts exactly as before; the pages it names are
the only ones to score both ways and to read. Held-out pages (the benchmark's holdout.txt, the Key Facts oracle's
fifth) are counted, never named. Written 23 September 2026.

usage (repo root, the project's venv):
    icon_picture_screen.py bench|kfs|insurance <out.jsonl> [workers]
"""
import concurrent.futures
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "bench", "probes"))
from order_screen import jobs


def screen(job):
    label, path, number, secret = job
    sys.path.insert(0, REPO)
    import truedoc
    from truedoc.pipeline import ConvertOptions, load_document
    try:
        doc = load_document(path, ConvertOptions(frontmatter=False, pages=[number]))
    except Exception as exc:
        return {"page": label, "held_out": secret, "error": repr(exc)[:100]}
    icons = [d for p in doc.pages for d in (p.meta.get("decisions") or []) if d.get("kind") == "icon"]
    return {"page": label, "held_out": secret, "icons": len(icons),
            "where": sorted({d["because"] for d in icons}), "code": os.path.dirname(truedoc.__file__)}


if __name__ == "__main__":
    which, out = sys.argv[1], sys.argv[2]
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 6
    todo = list(jobs(which))
    print(len(todo), "pages", flush=True)
    rows = []
    with open(out, "w", encoding="utf-8") as f, concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
        for n, r in enumerate(pool.map(screen, todo, chunksize=2), 1):
            rows.append(r)
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            if n % 100 == 0:
                print(" ", n, flush=True)
    hit = [r for r in rows if r.get("icons")]
    print("pages %d (failed %d) | icons kept out of the figures on %d: tuned-on %d, held-out %d (counted, never named); %d icons | code %s" % (
        len(rows), sum("error" in r for r in rows), len(hit), sum(not r["held_out"] for r in hit), sum(r["held_out"] for r in hit),
        sum(r["icons"] for r in hit), {r.get("code") for r in rows} - {None}))
    for r in hit:
        if not r["held_out"]:
            print("  %-70s %3d  %s" % (r["page"][-70:], r["icons"], "; ".join(w[27:] for w in r["where"])))
