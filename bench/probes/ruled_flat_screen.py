"""Screen `tables/ruled._flat`: on which cells does joining a ruled cell's lines with the shared joiner differ
from what the builder did before - turning every line break into a space?

The old behaviour was an inline expression, not a function, so there is nothing to load from a worktree: it is
written here as it stood (`(value or "").replace("\\n", " ").strip()`) and compared with `_flat` on every call of
every conversion. Differences in white space alone are counted apart - the old join kept a doubled space.

usage (repo root): ruled_flat_screen.py <out.jsonl> kfs|insurance|bench [workers]
"""
import concurrent.futures
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "bench", "probes"))
FOUND = []


def _install():
    from truedoc.tables import ruled
    if getattr(ruled, "_flat_screen", False):
        return
    ruled._flat_screen = True
    flat = ruled._flat

    def asked(value):
        now = flat(value)
        before = (value or "").replace("\n", " ").strip()
        if now != before:
            FOUND.append({"before": before[-90:], "now": now[-90:], "space_only": re.sub(r"\s+", " ", before) == now})
        return now

    ruled._flat = asked


def screen(job):
    label, path, number, secret = job
    _install()
    del FOUND[:]
    from truedoc.pipeline import ConvertOptions, load_document
    try:
        load_document(path, ConvertOptions(frontmatter=False, pages=[number]))
    except Exception as exc:
        return [{"page": label, "error": repr(exc)[:100]}]
    return [dict(r, page=label, held_out=secret, **({"before": "(held out)", "now": "(held out)"} if secret else {})) for r in FOUND]


if __name__ == "__main__":
    from orphan_row_census import jobs
    out, which = sys.argv[1], sys.argv[2]
    todo = list(jobs(which))
    print(len(todo), "pages", flush=True)
    with open(out, "w", encoding="utf-8") as f, concurrent.futures.ProcessPoolExecutor(max_workers=int(sys.argv[3]) if len(sys.argv) > 3 else 6) as pool:
        for rows in pool.map(screen, todo, chunksize=2):
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    rows = [json.loads(l) for l in open(out, encoding="utf-8")]
    errors = [r for r in rows if "error" in r]
    rows = [r for r in rows if "now" in r]
    real = [r for r in rows if not r["space_only"]]
    print("cells joined differently: %d on %d pages, of which white space alone %d; in words: %d cells on %d pages (held-out pages, counted only: %d); conversion errors: %d"
          % (len(rows), len({r["page"] for r in rows}), len(rows) - len(real), len(real), len({r["page"] for r in real}),
             len({r["page"] for r in real if r["held_out"]}), len(errors)))
    seen = set()
    for r in real:
        if r["held_out"]:
            continue
        key = (r["before"], r["now"])
        if key in seen:
            continue
        seen.add(key)
        if len(seen) > 60:
            break
        print("   %-34s %r\n   %-34s -> %r" % (r["page"][-34:], r["before"][-70:], "", r["now"][-70:]))
