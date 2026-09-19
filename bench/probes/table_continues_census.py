"""Two tables one under the other with the same columns: is the second the first one carrying on?

Markdown has no table without a heading row, so a table that the finder cut in two - at a band laid across it
("Cover for valuables, collections and items away from the insured address"), or at nothing at all - writes the
first DATA row of its second part as a heading. Read on the owner's Key Facts Sheets, 19 September 2026: six
tuned-on sheets, e.g. `| High value items and collections | Optional | ... |` over `| --- | --- | --- |`.

The candidate: a table directly under another, with the same number of columns starting at the same places, and
nothing between them but at most one line, is the same table. This census lists every such pair with the gap
between them, what lies in the gap, and the second table's first row, so the rule can be judged on its population.

usage (repo root): table_continues_census.py <out.jsonl> kfs|insurance|bench [workers]
"""
import concurrent.futures
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "bench", "probes"))


def _columns(table):
    """Left edge of each column: the least x0 of the cells that start in it and span one column."""
    edges = {}
    for c in table.cells:
        if c.bbox is not None and getattr(c, "colspan", 1) == 1 and c.text.strip():
            edges[c.col] = min(edges.get(c.col, c.bbox.x0), c.bbox.x0)
    return [edges.get(i) for i in range(table.n_cols)]


def census(job):
    label, path, number, secret = job
    from truedoc.model import BlockKind
    from truedoc.pipeline import ConvertOptions, load_document
    try:
        doc = load_document(path, ConvertOptions(frontmatter=False, pages=[number]))
    except Exception as exc:
        return [{"page": label, "error": repr(exc)[:100]}]
    found = []
    for page in doc.pages:
        size = page.body_font_size or 10.0
        tables = sorted((b for b in page.blocks if b.kind == BlockKind.TABLE and b.table is not None), key=lambda b: b.bbox.y0)
        for a, b in zip(tables, tables[1:]):
            overlap = min(a.bbox.x1, b.bbox.x1) - max(a.bbox.x0, b.bbox.x0)
            if overlap < 0.6 * min(a.bbox.width, b.bbox.width):
                continue                                             # side by side, or in different columns of the page
            gap = (b.bbox.y0 - a.bbox.y1) / size
            between = [x for x in page.blocks if x is not a and x is not b and x.bbox.y0 >= a.bbox.y1 - 0.3 * size
                       and x.bbox.y1 <= b.bbox.y0 + 0.3 * size and min(x.bbox.x1, a.bbox.x1) - max(x.bbox.x0, a.bbox.x0) > 0]
            ca, cb = _columns(a.table), _columns(b.table)
            same_count = a.table.n_cols == b.table.n_cols
            drift = max((abs(x - y) for x, y in zip(ca, cb) if x is not None and y is not None), default=None) if same_count else None
            first = [c.text[:26] for c in sorted((c for c in b.table.cells if c.row == 0), key=lambda c: c.col)]
            found.append({"gap": round(gap, 2), "same_count": same_count, "n_cols": [a.table.n_cols, b.table.n_cols],
                          "drift": round(drift, 1) if drift is not None else None,
                          "between": [(x.kind.name, (x.text or "")[:50]) for x in between][:4], "n_between": len(between),
                          "first_row": first, "provenance": [a.table.provenance, b.table.provenance],
                          "rows": [a.table.n_rows, b.table.n_rows]})
    return [dict(r, page=label, held_out=secret, **({"between": "(held out)", "first_row": "(held out)"} if secret else {})) for r in found]


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
    rows = [r for r in rows if "gap" in r]
    print("pairs of tables one under the other: %d on %d pages" % (len(rows), len({r["page"] for r in rows})))
    near = [r for r in rows if r["same_count"] and r["drift"] is not None and r["drift"] <= 3.0]
    print("  same number of columns, starting within 3 points of each other: %d on %d pages (held-out pages, counted only: %d)"
          % (len(near), len({r["page"] for r in near}), len({r["page"] for r in near if r["held_out"]})))
    for r in sorted(near, key=lambda r: (r["n_between"], r["gap"])):
        if r["held_out"]:
            continue
        print("   gap %5.2f between %d %-30s cols %d rows %s %-22s first row: %s%s" % (
            r["gap"], r["n_between"], r["page"][-30:], r["n_cols"][0], r["rows"], "/".join(p[:10] for p in r["provenance"]),
            " | ".join(r["first_row"])[:70], ("   [between: " + "; ".join("%s %s" % (k, t) for k, t in r["between"])[:80] + "]") if r["between"] else ""))
