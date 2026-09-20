"""Tables with a column that never holds text of its own: how many, where, from which reader?

Benchmark tables/9e3b179d..._pg2 is a permit-fee form, fully ruled, whose vertical rules are staggered between
sections: the code | description divider stands about 16 points further left under the first three rows than beside
them, and the fee column's likewise. A grid built from every rule has five columns where a reader sees three, and two
of them are slivers: in every row a sliver is either empty, or covered by the same spanning cell as the column beside
it. The benchmark's checker takes a cell's top heading as the first non-empty cell of its column from the top, and
its neighbour as the next column, so both of that page's checks fail through the slivers ("cell to the right ''").

A column like that can be fused with its neighbour without losing or moving a word, by construction. This census
says how common it is: every table we build on a population, each column tested against each neighbour.

    fusable with neighbour n: in every row, the cell over (row, k) is the very cell over (row, n), or it is empty

Held-out pages are counted and never listed.

usage (repo root): sliver_column_census.py <out.jsonl> kfs|insurance|bench [workers]
"""
import concurrent.futures
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "bench", "probes"))


def slivers(table):
    grid = table.grid()
    found = []
    for k in range(table.n_cols):
        own = any(c is not None and c.col == k and c.colspan == 1 and (c.text or "").strip() for row in grid for c in [row[k]])
        if own:
            continue
        for n in (k - 1, k + 1):
            if not (0 <= n < table.n_cols):
                continue
            rows_ok, shared = True, 0
            for row in grid:
                here, there = row[k], row[n]
                if here is not None and here is there:
                    shared += 1
                elif here is None or not (here.text or "").strip():
                    continue
                else:
                    rows_ok = False
                    break
            if rows_ok:
                found.append({"column": k, "into": n, "rows_shared": shared})
                break
    return found


def census(job):
    label, path, number, secret = job
    from truedoc.model import BlockKind
    from truedoc.pipeline import ConvertOptions, load_document
    try:
        doc = load_document(path, ConvertOptions(frontmatter=False, pages=[number]))
    except Exception as exc:
        return [{"page": label, "error": repr(exc)[:100]}]
    out = []
    for page in doc.pages:
        for i, block in enumerate(b for b in page.blocks if b.kind == BlockKind.TABLE and b.table is not None):
            t = block.table
            found = slivers(t)
            out.append({"page": label, "held_out": secret, "table": i, "reader": block.provenance or t.provenance, "cols": t.n_cols,
                        "rows": t.n_rows, "slivers": found,
                        "first": "(held out)" if secret else " | ".join((c.text or "")[:16] for c in t.grid()[0] if c is not None)[:90]})
    return out


if __name__ == "__main__":
    from orphan_row_census import jobs
    out, which = sys.argv[1], sys.argv[2]
    todo = list(jobs(which))
    print(len(todo), "pages", flush=True)
    with open(out, "w", encoding="utf-8") as f, concurrent.futures.ProcessPoolExecutor(max_workers=int(sys.argv[3]) if len(sys.argv) > 3 else 6) as pool:
        for n, rows in enumerate(pool.map(census, todo, chunksize=2), 1):
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
            if n % 100 == 0:
                print(" ", n, flush=True)
    rows = [json.loads(l) for l in open(out, encoding="utf-8")]
    errors = [r for r in rows if "error" in r]
    tables = [r for r in rows if "slivers" in r]
    hit = [r for r in tables if r["slivers"]]
    print("tables built: %d on %d pages | with a sliver column: %d on %d pages (held-out pages, counted only: %d) | errors: %d"
          % (len(tables), len({r["page"] for r in tables}), len(hit), len({r["page"] for r in hit}), len({r["page"] for r in hit if r["held_out"]}), len(errors)))
    by_reader = {}
    for r in hit:
        by_reader[r["reader"]] = by_reader.get(r["reader"], 0) + 1
    print("by reader:", by_reader)
    for r in [r for r in hit if not r["held_out"]]:
        print("   %-44s %-18s %2d cols %3d rows  slivers %s | %s" % (r["page"][-44:], r["reader"][:18], r["cols"], r["rows"],
              [(s["column"], s["into"], s["rows_shared"]) for s in r["slivers"]], r["first"][:60]))
