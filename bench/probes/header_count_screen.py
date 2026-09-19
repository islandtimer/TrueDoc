"""Screen a change to `_header_row_count`: on which pages does any table's heading count differ between two code states?

The count is a pure function of a table's grid, so both states can be asked about the same grid in
one conversion: the working tree's function runs as usual, and the other state's is loaded from
its own `aligned.py` (a worktree) under another module name and called beside it. Pages where the
two ever disagree are the only pages the change can touch; convert those both ways and read them.

usage (repo root): header_count_screen.py <other code root> <out.jsonl> kfs|insurance|bench [workers]
"""
import concurrent.futures
import importlib.util
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "bench", "probes"))
FOUND = []
OTHER = None


def _install(other_root):
    from truedoc.tables import aligned
    if getattr(aligned, "_count_screen", False):
        return
    aligned._count_screen = True
    spec = importlib.util.spec_from_file_location("aligned_other_state", os.path.join(other_root, "truedoc", "tables", "aligned.py"))
    other = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = other                       # its dataclasses look their module up by name
    spec.loader.exec_module(other)
    count_now = aligned._header_row_count

    def count(grid):
        n = count_now(grid)
        m = other._header_row_count([list(r) for r in grid])
        if n != m:
            FOUND.append({"now": n, "other": m, "rows": [[c[:26] for c in r] for r in grid[:max(n, m) + 1]], "body_rows": len(grid) - n})
        return n

    aligned._header_row_count = count


def screen(job):
    other_root, (label, path, number, secret) = job
    _install(other_root)
    del FOUND[:]
    from truedoc.pipeline import ConvertOptions, load_document
    try:
        load_document(path, ConvertOptions(frontmatter=False, pages=[number]))
    except Exception as exc:
        return [{"page": label, "error": repr(exc)[:100]}]
    return [dict(r, page=label, held_out=secret, **({"rows": "(held out)"} if secret else {})) for r in FOUND]


if __name__ == "__main__":
    from orphan_row_census import jobs
    other_root, out, which = sys.argv[1], sys.argv[2], sys.argv[3]
    todo = [(other_root, j) for j in jobs(which)]
    print(len(todo), "pages", flush=True)
    with open(out, "w", encoding="utf-8") as f, concurrent.futures.ProcessPoolExecutor(max_workers=int(sys.argv[4]) if len(sys.argv) > 4 else 6) as pool:
        for rows in pool.map(screen, todo, chunksize=2):
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    rows = [json.loads(l) for l in open(out, encoding="utf-8")]
    errors = [r for r in rows if "error" in r]
    rows = [r for r in rows if "now" in r]
    print("tables whose heading count differs: %d on %d pages (held-out sheets among them, counted and never listed: %d); conversion errors: %d"
          % (len(rows), len({r["page"] for r in rows}), sum(1 for r in rows if r["held_out"]), len(errors)))
    seen = set()
    for r in rows:
        if r["held_out"]:
            continue
        key = json.dumps(r["rows"], ensure_ascii=False)
        if key in seen:
            continue
        seen.add(key)
        print("  --", r["page"][-56:], "| heading rows: other state", r["other"], "-> now", r["now"], "| body rows:", r["body_rows"])
        for cells in r["rows"]:
            print("       | " + " | ".join(cells)[:190])
