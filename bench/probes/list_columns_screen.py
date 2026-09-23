"""Which tables the side-by-side list rebuild reads differently from a commit's (23 September 2026).

`tables.list_columns.rebuild_side_by_side_lists` runs once per page, on the tables the text built. Every page of a
population is converted once with the working tree; at that stage the committed module - loaded under another name -
is run on a copy of the same tables, and the two results compared table by table. The pages it names are the only ones
whose output the change can reach, so they are the ones to score both ways and to read. Held-out pages (the benchmark's
holdout.txt, the Key Facts oracle's fifth, the library's odd half) are counted, never named, and none of their text kept.

usage (repo root, the project's venv):
    list_columns_screen.py bench|kfs|insurance <out.jsonl> [workers] [--rev REV]
    list_columns_screen.py library <lists_screen.jsonl> <out.jsonl> [workers] [--rev REV] [--no-layout]
        (the library's pages flagged by `box_list_blank_census.py screen` for lists set side by side)

`--no-layout` converts without the layout model: about ten times faster, and it reaches only the tables the text layer
builds (`textlayer-aligned`), not the ones the model's regions build.
"""
import concurrent.futures
import copy
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
        src = subprocess.run(["git", "show", f"{rev}:truedoc/tables/list_columns.py"], cwd=REPO, capture_output=True,
                             check=True).stdout
        path = os.path.join(tempfile.mkdtemp(), "list_columns_before.py")
        open(path, "wb").write(src)
        spec = importlib.util.spec_from_file_location("list_columns_before", path)
        _BEFORE = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_BEFORE)
    return _BEFORE


def _shape(table):
    if table is None:
        return None
    return [(c.row, c.col, c.rowspan, c.colspan, c.text, c.is_header,
             None if c.listing is None else (c.listing.lead, [(i.text, i.children, i.tail) for i in c.listing.items],
                                             c.listing.note))
            for c in table.cells]


def screen(job):
    (label, path, number, secret), rev, layout = job
    sys.path.insert(0, REPO)
    from truedoc import pipeline
    from truedoc.model import BlockKind
    from truedoc.tables import list_columns

    found = []

    def both(page, blocks):
        before = _before(rev)
        marks = [m for m in page.meta.get("marks", []) if m.get("kind") in list_columns.MARK_TEXT]
        for b in blocks:
            if b.kind == BlockKind.TABLE and b.table is not None and b.table.provenance in list_columns.TEXT_BUILT:
                old = before.side_by_side(page, copy.deepcopy(b.table), marks)
                new = list_columns.side_by_side(page, copy.deepcopy(b.table), marks)
                if _shape(old) != _shape(new):
                    found.append({"rows": b.table.n_rows, "cols": b.table.n_cols, "before": old is not None,
                                  "now": new is not None,
                                  **({} if secret else {"text": [c.text[:40] for c in b.table.cells][:12],
                                                        "now_rows": None if new is None else new.n_rows})})
        list_columns.rebuild_side_by_side_lists(page, blocks)

    pipeline.rebuild_side_by_side_lists = both
    try:
        pipeline.load_document(path, pipeline.ConvertOptions(frontmatter=False, pages=[number], layout=layout))
    except Exception as exc:
        return {"page": label, "held_out": secret, "error": repr(exc)[:100]}
    return {"page": label, "held_out": secret, "changed": found}


def _library(screen_path):
    import side_label_icon_census as census
    paths = {j[0]: j[1] for j in census.jobs("library")}
    for line in open(screen_path, encoding="utf-8"):
        r = json.loads(line)
        if "error" not in r and r.get("lists"):
            yield (r["doc"] + "#" + str(r["page"]), paths[r["doc"]], r["page"], r["held_out"])


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    rev = sys.argv[sys.argv.index("--rev") + 1] if "--rev" in sys.argv else "HEAD"
    args = [a for a in args if a != rev]
    which = args[0]
    if which == "library":
        todo, out, rest = list(_library(args[1])), args[2], args[3:]
    else:
        todo, out, rest = list(jobs(which)), args[1], args[2:]
    workers = int(rest[0]) if rest else 6
    print(len(todo), "pages", flush=True)
    rows = []
    with open(out, "w", encoding="utf-8") as f, concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
        for n, r in enumerate(pool.map(screen, [(j, rev, "--no-layout" not in sys.argv) for j in todo], chunksize=2), 1):
            rows.append(r)
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            if n % 100 == 0:
                print(" ", n, flush=True)
    hit = [r for r in rows if r.get("changed")]
    print("pages %d (failed %d) | a table read differently on %d: tuned-on %d, held-out %d (counted, never named) | "
          "rebuilt now and not before %d, before and not now %d, both but differently %d" % (
              len(rows), sum("error" in r for r in rows), len(hit), sum(not r["held_out"] for r in hit),
              sum(r["held_out"] for r in hit),
              sum(1 for r in hit for t in r["changed"] if t["now"] and not t["before"]),
              sum(1 for r in hit for t in r["changed"] if t["before"] and not t["now"]),
              sum(1 for r in hit for t in r["changed"] if t["before"] and t["now"])))
    for r in hit:
        if not r["held_out"]:
            for t in r["changed"]:
                print("  %-80s %dx%d before %s now %s -> %s rows" % (r["page"][-80:], t["rows"], t["cols"], t["before"],
                                                                     t["now"], t.get("now_rows")))
