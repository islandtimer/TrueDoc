"""Screen a change to a PURE function of `tables/aligned.py`: where do two code states answer differently?

`header_count_screen.py` made general. A function whose result depends on its arguments alone can be
asked twice about the same arguments inside one conversion: the working tree's runs as usual, and
the other state's is loaded from its own `aligned.py` (a worktree) under another module name and
called beside it with a copy of the arguments. Pages where the two ever disagree are the only pages
the change can touch; convert those both ways and read them.

Only for functions of plain arguments (lists of strings, numbers): the grid functions
`_header_row_count(grid)`, `_heading_wraps_on(grid, i)`, `_heading_hangs_open(grid, i)`, and of strings: `_join_lines(upper, lower)`.

usage (repo root): pure_function_screen.py <other code root> <function> <out.jsonl> kfs|insurance|bench [workers]
"""
import concurrent.futures
import copy
import importlib.util
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "bench", "probes"))
FOUND = []


def _install(other_root, name):
    from truedoc.tables import aligned
    if getattr(aligned, "_pure_screen", False):
        return
    aligned._pure_screen = True
    spec = importlib.util.spec_from_file_location("aligned_other_state", os.path.join(other_root, "truedoc", "tables", "aligned.py"))
    other = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = other                       # its dataclasses look their module up by name
    spec.loader.exec_module(other)
    now, then = getattr(aligned, name), getattr(other, name)

    def asked(*args):
        before = then(*copy.deepcopy(args))
        after = now(*args)
        if before != after:
            grid = args[0] if args and isinstance(args[0], list) else []
            FOUND.append({"other": before, "now": after,
                          "rest": [a[-60:] if isinstance(a, str) else a for a in (args if not grid else args[1:]) if isinstance(a, (int, float, str))],
                          "rows": [[str(c)[:30] for c in r] for r in grid[:4]], "n_rows": len(grid)})
        return after

    setattr(aligned, name, asked)


def screen(job):
    other_root, name, (label, path, number, secret) = job
    _install(other_root, name)
    del FOUND[:]
    from truedoc.pipeline import ConvertOptions, load_document
    try:
        load_document(path, ConvertOptions(frontmatter=False, pages=[number]))
    except Exception as exc:
        return [{"page": label, "error": repr(exc)[:100]}]
    hidden = {"rows": "(held out)", "rest": "(held out)"}
    return [dict(r, page=label, held_out=secret,
                 **(dict(hidden, **{k: "(held out)" for k in ("other", "now") if isinstance(r[k], str)}) if secret else {})) for r in FOUND]


if __name__ == "__main__":
    from orphan_row_census import jobs
    other_root, name, out, which = sys.argv[1:5]
    todo = [(other_root, name, j) for j in jobs(which)]
    print(len(todo), "pages", flush=True)
    with open(out, "w", encoding="utf-8") as f, concurrent.futures.ProcessPoolExecutor(max_workers=int(sys.argv[5]) if len(sys.argv) > 5 else 6) as pool:
        for rows in pool.map(screen, todo, chunksize=2):
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    rows = [json.loads(l) for l in open(out, encoding="utf-8")]
    errors = [r for r in rows if "error" in r]
    rows = [r for r in rows if "now" in r]
    pages = sorted({r["page"] for r in rows})
    print("%s answers differently on %d calls, %d pages (held-out sheets among them, counted and never listed: %d pages); conversion errors: %d"
          % (name, len(rows), len(pages), len({r["page"] for r in rows if r["held_out"]}), len(errors)))
    seen = set()
    for r in rows:
        if r["held_out"]:
            continue
        key = json.dumps([r["rows"], r["rest"]], ensure_ascii=False)
        if key in seen:
            continue
        seen.add(key)
        if len(seen) > 30:
            break
        print("  --", r["page"][-56:], "| other state", r["other"], "-> now", r["now"], "| args", r["rest"], "| rows", r["n_rows"])
        for cells in r["rows"]:
            print("       | " + " | ".join(cells)[:200])
