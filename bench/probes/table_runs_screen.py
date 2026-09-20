"""Where do two code states of `tables/aligned._find_runs` gather a page's rows into different candidate tables?

The sibling of `column_cut_screen.py`. The function's answer holds rows of the module's own classes, which never
compare equal across two loaded copies of the module, so each candidate is reduced to what can be compared: how many
rows it has and the box they fill. The working tree's function runs as usual inside a whole conversion; the other
state's, loaded from a worktree under another module name, is asked the same question beside it, and a page is named
when the two ever differ. Those are the only pages the change can touch: convert them both ways and read them.

usage (repo root): table_runs_screen.py <other code root> <out.jsonl> kfs|insurance|bench [workers]
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


def _shape(candidates):
    return [(len(c.rows), [round(v) for v in (c.bbox.x0, c.bbox.y0, c.bbox.x1, c.bbox.y1)]) for c in candidates]


def _install(other_root):
    from truedoc.tables import aligned
    if getattr(aligned, "_runs_screen", False):
        return
    aligned._runs_screen = True
    spec = importlib.util.spec_from_file_location("other_state_aligned", os.path.join(other_root, "truedoc", "tables", "aligned.py"))
    other = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = other
    spec.loader.exec_module(other)
    now, then = aligned._find_runs, other._find_runs

    def asked(rows, size):
        before = _shape(then(copy.deepcopy(rows), size))
        out = now(rows, size)
        if before != _shape(out):
            mine = _shape(out)
            changed = [c for c in out if (len(c.rows), [round(v) for v in (c.bbox.x0, c.bbox.y0, c.bbox.x1, c.bbox.y1)]) not in before]
            FOUND.append({"other": before, "now": mine,
                          "first": " || ".join(" | ".join(s.text for s in c.rows[0].segments)[:60] for c in changed)[:160]})
        return out

    aligned._find_runs = asked


def screen(job):
    other_root, (label, path, number, secret) = job
    _install(other_root)
    del FOUND[:]
    from truedoc.pipeline import ConvertOptions, convert
    try:
        convert(path, ConvertOptions(frontmatter=False, pages=[number]))
    except Exception as exc:
        return [{"page": label, "error": repr(exc)[:100]}]
    return [dict(r, page=label, held_out=secret, **({"first": "(held out)"} if secret else {})) for r in FOUND]


if __name__ == "__main__":
    from orphan_row_census import jobs
    other_root, out, which = sys.argv[1:4]
    todo = [(other_root, j) for j in jobs(which)]
    print(len(todo), "pages", flush=True)
    with open(out, "w", encoding="utf-8") as f, concurrent.futures.ProcessPoolExecutor(max_workers=int(sys.argv[4]) if len(sys.argv) > 4 else 6) as pool:
        for n, rows in enumerate(pool.map(screen, todo, chunksize=2), 1):
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
            if n % 100 == 0:
                print(" ", n, flush=True)
    rows = [json.loads(l) for l in open(out, encoding="utf-8")]
    errors = [r for r in rows if "error" in r]
    rows = [r for r in rows if "now" in r]
    print("the candidate tables differ on %d calls, %d pages (held-out pages among them, counted and never listed: %d); conversion errors: %d"
          % (len(rows), len({r["page"] for r in rows}), len({r["page"] for r in rows if r["held_out"]}), len(errors)))
    for page in sorted({r["page"] for r in rows if not r["held_out"]}):
        for r in [r for r in rows if r["page"] == page][:2]:
            print("   %-44s rows before %s now %s  %s" % (page[-44:], [n for n, _ in r["other"]], [n for n, _ in r["now"]], r["first"][:90]))
