"""Every cell that `tables/cell_tables.table_cells` reads as a table of its own (D038), on every page of a population.

The stage changes a page's output only where `read_inner_table` returns a table, so hooking it names exactly the
pages that can change; convert those both ways and read them.

usage (repo root): inner_table_screen.py <out.jsonl> kfs|insurance|bench [workers]
"""
import concurrent.futures
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "bench", "probes"))
FOUND = []


def _install():
    from truedoc.tables import cell_tables
    if getattr(cell_tables, "_screened", False):
        return
    cell_tables._screened = True
    read0 = cell_tables.read_inner_table

    def read(lines, cell_text, size, box):
        inner = read0(lines, cell_text, size, box)
        if inner is not None:
            FOUND.append({"rows": inner.n_rows, "cols": inner.n_cols, "heading": any(c.is_header for c in inner.cells),
                          "first_row": [c.text[:24] for c in sorted((c for c in inner.cells if c.row == 0), key=lambda c: c.col)],
                          "text": cell_text[:60]})
        return inner

    cell_tables.read_inner_table = read


def screen(job):
    label, path, number, secret = job
    _install()
    del FOUND[:]
    from truedoc.pipeline import ConvertOptions, load_document
    try:
        load_document(path, ConvertOptions(frontmatter=False, pages=[number]))
    except Exception as exc:
        return [{"page": label, "error": repr(exc)[:100]}]
    return [dict(r, page=label, held_out=secret, **({"first_row": "(held out)", "text": "(held out)"} if secret else {})) for r in FOUND]


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
    rows = [r for r in rows if "cols" in r]
    print("cells read as a table of their own: %d on %d pages (held-out pages, counted only: %d); conversion errors: %d"
          % (len(rows), len({r["page"] for r in rows}), len({r["page"] for r in rows if r["held_out"]}), len(errors)))
    for r in rows:
        if not r["held_out"]:
            print("   %-40s %d x %d heading %-5s first row: %s" % (r["page"][-40:], r["rows"], r["cols"], r["heading"], " | ".join(r["first_row"])[:90]))
