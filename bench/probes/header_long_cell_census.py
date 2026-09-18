"""A heading ended by the first long cell: how often is that cell a label-less line of the entry above?

`tables/aligned._header_row_count` ends a table's heading at the first row with numbers in it or,
failing that, at the first cell of more than six words. On a benchmark page (multi_column
019a8841...page_2, read 19 September 2026) that cost a body row:

    Sexe        | Age | Cote  | Presentation Clinique | Traitement                         |
    Cas 1 Femme | 61  | Droit | ischemie              | clopidrogrel                       | angioplastie
                |     |       | chronique             | + aspirine, puis relais a 3 mois.. | + stent

The long cell is on the *second line* of Cas 1's entry, a line with no label in a table that labels
its rows, so the heading was counted as two rows and "Cas 1 Femme | 61 | ..." was written into it.

The candidate: when the long cell stands on a line with no label, in a table that labels its rows,
under a line that has one, that line above opens the entry the long cell belongs to - it is body, and
the heading ends before it. This census lists every table on which the count would change, with the
rows concerned, so the rule can be judged on its population before it is written.

usage (repo root): header_long_cell_census.py <out.jsonl> kfs|insurance|bench [workers]
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
    from truedoc.tables import aligned
    if getattr(aligned, "_header_census", False):
        return
    aligned._header_census = True
    count0 = aligned._header_row_count

    def count(grid):
        n = count0(grid)
        if n >= 2 and len(grid) > n:
            row, above = grid[n], grid[n - 1]
            long_cell = any(len(c.split()) > 6 for c in row if c)
            earlier_long = any(len(c.split()) > 6 for r in grid[:n] for c in r if c)
            if long_cell and not earlier_long and not row[0] and above[0] and any(r[0] for r in grid[1:]):
                FOUND.append({"n": n, "rows": [[c[:28] for c in r] for r in grid[:n + 2]], "columns": len(grid[0]), "body_rows": len(grid) - n})
        return n

    aligned._header_row_count = count


def census(job):
    label, path, number, secret = job
    _install()
    del FOUND[:]
    from truedoc.pipeline import ConvertOptions, load_document
    try:
        load_document(path, ConvertOptions(frontmatter=False, pages=[number]))
    except Exception as exc:
        return [{"page": label, "error": repr(exc)[:100]}]
    return [dict(r, page=label, held_out=secret, **({"rows": "(held out)"} if secret else {})) for r in FOUND]


if __name__ == "__main__":
    from orphan_row_census import jobs
    out, which = sys.argv[1], sys.argv[2]
    todo = list(jobs(which))
    print(len(todo), "pages", flush=True)
    with open(out, "w", encoding="utf-8") as f, concurrent.futures.ProcessPoolExecutor(max_workers=int(sys.argv[3]) if len(sys.argv) > 3 else 6) as pool:
        for rows in pool.map(census, todo, chunksize=2):
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    rows = [json.loads(l) for l in open(out, encoding="utf-8")]
    rows = [r for r in rows if "n" in r]
    print("tables whose heading the candidate would end a row sooner: %d on %d pages (held-out sheets among them, counted and never listed: %d)"
          % (len(rows), len({r["page"] for r in rows}), sum(1 for r in rows if r["held_out"])))
    seen = set()
    for r in rows:
        if r["held_out"]:
            continue
        key = json.dumps(r["rows"], ensure_ascii=False)
        if key in seen:
            continue
        seen.add(key)
        print("  --", r["page"][-52:], "| heading rows now:", r["n"], "| body rows:", r["body_rows"])
        for cells in r["rows"]:
            print("       | " + " | ".join(cells))
