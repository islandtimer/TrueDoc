"""Rows `_headings_in_order` re-reads in order: how far does it move a segment from where it stands?

`tables/aligned._headings_in_order` is for a row of short headings set a shade left of the narrow
columns beneath them ("BM BF WM ... Total" over "4 4 7 ... 25"): by position two headings share a
column and another has none, so the row is read in order, one heading a column. On CGU's Key Facts
Sheet (read 19 September 2026) it fires on a row that is nothing of the kind -

    and collections | Accidental Damage Home | $2,500/item 20% of Contents SI or $7,500 (...)

- the second and third lines of a table nested in the third column: by position [0, 2, 2], in
order [0, 1, 2], and "Accidental Damage Home" is written into the Yes/No column, 18 points from
anything that column holds. A heading set "a shade left" is moved a shade. This census measures,
for every row the rule fires on, how far each moved segment stands from the column it is moved
into, so that a bound can be chosen from the population.

usage (repo root): headings_in_order_census.py <out.jsonl> kfs|insurance|bench [workers]
"""
import concurrent.futures
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "bench", "probes"))
FOUND = []
LAST = {}


def _install():
    from truedoc.tables import aligned
    if getattr(aligned, "_order_census", False):
        return
    aligned._order_census = True
    column_of0, in_order0 = aligned._column_of, aligned._headings_in_order

    def column_of(bbox, columns):
        LAST["columns"] = columns
        return column_of0(bbox, columns)

    def in_order(row, cols):
        yes = in_order0(row, cols)
        columns = LAST.get("columns")
        if yes and columns:
            moved = []
            for seg, was, now in zip(row.segments, cols, range(cols[0], cols[0] + len(cols))):
                if was != now:
                    lo, hi = columns[now]
                    away = max(lo - seg.bbox.x1, seg.bbox.x0 - hi, 0.0)      # 0 when the segment reaches into the column
                    moved.append({"text": seg.text[:30], "from": was, "to": now, "away": round(away, 1), "width": round(seg.bbox.width, 1)})
            size = max((s.size or 0) for s in row.segments) or 10.0
            FOUND.append({"moved": moved, "row": [s.text[:24] for s in row.segments], "size": round(size, 1),
                          "furthest": max((m["away"] for m in moved), default=0.0),
                          "longest_words": max(len(s.text.split()) for s in row.segments)})
        return yes

    aligned._column_of = column_of
    aligned._headings_in_order = in_order


def census(job):
    label, path, number, secret = job
    _install()
    del FOUND[:]
    from truedoc.pipeline import ConvertOptions, load_document
    try:
        load_document(path, ConvertOptions(frontmatter=False, pages=[number]))
    except Exception as exc:
        return [{"page": label, "error": repr(exc)[:100]}]
    return [dict(r, page=label, held_out=secret, **({"moved": "(held out)", "row": "(held out)"} if secret else {})) for r in FOUND]


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
    rows = [r for r in rows if "furthest" in r]
    print("rows read in order: %d on %d pages (held-out sheets among them, counted and never listed: %d)" % (len(rows), len({r["page"] for r in rows}), sum(1 for r in rows if r["held_out"])))
    for lo, hi in ((0, 0.01), (0.01, 2), (2, 5), (5, 10), (10, 20), (20, 999)):
        print("   furthest moved segment stands %5.2f to %6.2f points from its new column: %d rows" % (lo, hi, sum(1 for r in rows if lo <= r["furthest"] < hi)))
    seen = set()
    for r in sorted(rows, key=lambda r: -r["furthest"]):
        if r["held_out"]:
            continue
        key = json.dumps(r["row"], ensure_ascii=False)
        if key in seen:
            continue
        seen.add(key)
        if len(seen) > 40:
            break
        print("   away %5.1f size %4.1f words %2d %-40s %s" % (r["furthest"], r["size"], r["longest_words"], r["page"][-40:], " | ".join(r["row"])[:110]))
