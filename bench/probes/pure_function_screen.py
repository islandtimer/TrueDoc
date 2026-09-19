"""Screen a change to a PURE function of `tables/aligned.py`: where do two code states answer differently?

`header_count_screen.py` made general. A function whose result depends on its arguments alone can be
asked twice about the same arguments inside one conversion: the working tree's runs as usual, and
the other state's is loaded from its own `aligned.py` (a worktree) under another module name and
called beside it with a copy of the arguments. Pages where the two ever disagree are the only pages
the change can touch; convert those both ways and read them.

Only for functions of plain arguments (lists of strings, numbers): the grid functions
`_header_row_count(grid)`, `_heading_wraps_on(grid, i)`, `_heading_hangs_open(grid, i)`, and of strings: `_join_lines(upper, lower)`.

usage (repo root): pure_function_screen.py <other code root> [<dotted module>:]<function> <out.jsonl> kfs|insurance|bench [workers]
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


def _install(other_root, names):
    for one in names.split(","):                          # several functions ride one pass of conversions
        _install_one(other_root, one.strip())


def _install_one(other_root, name):
    # "<function>" is one of tables/aligned.py; "<dotted module>:<function>" names any other ("truedoc.render.okf:_join_at_hyphen")
    import importlib
    module_name, _, name = name.rpartition(":")
    aligned = importlib.import_module(module_name or "truedoc.tables.aligned")
    full = name
    if name in getattr(aligned, "_pure_screen", ()):
        return
    aligned._pure_screen = getattr(aligned, "_pure_screen", ()) + (name,)
    spec = importlib.util.spec_from_file_location("other_state_" + aligned.__name__.replace(".", "_"), os.path.join(other_root, *aligned.__name__.split(".")) + ".py")
    other = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = other                       # its dataclasses look their module up by name
    spec.loader.exec_module(other)
    now, then = getattr(aligned, name), getattr(other, name)

    def asked(*args):
        before = then(*copy.deepcopy(args))
        after = now(*args)
        if before != after:
            grid = args[0] if args and isinstance(args[0], list) else []
            FOUND.append({"function": name, "other": before, "now": after,
                          "rest": [a[-60:] if isinstance(a, str) else a for a in (args if not grid else args[1:]) if isinstance(a, (int, float, str))],
                          "rows": [[str(c)[:30] for c in r] for r in grid[:4]], "n_rows": len(grid)})
        return after

    # Every module that took the function by name holds its own reference (`from ...aligned import _join_lines` in
    # boxed_cells, fill_grid and rule_grid): load the pipeline so they all exist, then rebind each of them.
    import truedoc.pipeline  # noqa: F401
    rebound = 0
    for module in list(sys.modules.values()):
        if getattr(module, "__name__", "").startswith("truedoc") and getattr(module, name, None) is now:
            setattr(module, name, asked)
            rebound += 1
    aligned._pure_screen_rebound = rebound


def screen(job):
    other_root, name, (label, path, number, secret) = job
    _install(other_root, name)
    del FOUND[:]
    from truedoc.pipeline import ConvertOptions, convert
    try:
        convert(path, ConvertOptions(frontmatter=False, pages=[number]))      # the whole conversion: a renderer's function is only called when the page is written
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
        print("  --", r.get("function", ""), "|", r["page"][-56:], "| other state", r["other"], "-> now", r["now"], "| args", r["rest"], "| rows", r["n_rows"])
        for cells in r["rows"]:
            print("       | " + " | ".join(cells)[:200])
