"""Under a one-line cell: would the first word of the row below have fitted on that line?

Part B of the last-line-of-a-cell question (`orphan_row_census.py` is part A). A row with no label
and one filled cell, standing flush under a cell of ONE line, has no leading to be compared with:

    For an extra premium cover can be purchased to cover   |  | | Accidental Damage.       (a wrap)
    -0.05                                                  |  | | -0.06                    (two rows)
    ...Go to page 42.                                      |  | | Note: eligibility...     (two rows)

The typesetter's own definition separates them without reading a word: a line break is a *wrap*
only if the next word would not have fitted on the line above - the line's right edge, a word
space and the word's width pass the column's right edge, which is where the widest line in that
column of the table ends. This census measures that slack for every such row, so the rule can be
judged on its population before it is written.

usage (repo root): orphan_row_fit_census.py <out.jsonl> kfs|insurance|bench [workers]
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
    if getattr(aligned, "_fit_census", False):
        return
    aligned._fit_census = True
    merge0 = aligned._merge_wrapped_rows

    def merge(grid, rows, size, columns=None, joined=None):
        out, out_rows = merge0(grid, rows, size, columns, joined)
        if not columns:
            return out, out_rows
        right = {}                                         # where the widest line of each column ends
        for r in rows:
            for s in r.segments:
                if s.text.strip():
                    c = aligned._column_of(s.bbox, columns)
                    right[c] = max(right.get(c, 0.0), s.bbox.x1)
        steps = sorted(b.y0 - a.y0 for a, b in zip(rows, rows[1:]) if b.y0 - a.y0 > 0.5 * size)
        leading = steps[len(steps) // 4] if steps else None   # the lower quartile: lines inside cells, not rows apart
        for k in range(1, len(out)):
            cells = out[k]
            filled = [i for i, c in enumerate(cells) if c]
            if cells[0] or len(filled) != 1 or not out[k - 1][filled[0]]:
                continue
            i = filled[0]
            mine = [s for s in out_rows[k].segments if s.text.strip()]
            above = [s for s in out_rows[k - 1].segments if s.text.strip() and aligned._column_of(s.bbox, columns) == i]
            tops = sorted({round(s.bbox.y0) for s in above})
            if len(mine) != 1 or not above or len(tops) != 1 or not mine[0].words:
                continue
            line, last = mine[0], max(above, key=lambda s: s.bbox.x1)
            word = line.words[0].bbox.width
            gaps = [b.bbox.x0 - a.bbox.x1 for a, b in zip(last.words, last.words[1:]) if b.bbox.x0 > a.bbox.x1]
            space = sorted(gaps)[len(gaps) // 2] if gaps else 0.25 * size
            slack = right.get(i, last.bbox.x1) - (last.bbox.x1 + space + word)
            FOUND.append({
                "text": cells[i][:50], "above": out[k - 1][i][-44:], "dx": round(line.bbox.x0 - min(s.bbox.x0 for s in above), 1),
                "slack": round(slack, 1), "word": round(word, 1), "column_width": round(right.get(i, 0) - min(s.bbox.x0 for s in above), 1),
                "step": round((line.bbox.y0 - last.bbox.y0) / leading, 2) if leading else None,
                "band": bool(aligned._is_band(k, out, out_rows, columns, aligned._band_segments(out_rows, size), size)),
                "bullet": bool(aligned._BULLET_START.match(cells[i])),
            })
        return out, out_rows

    aligned._merge_wrapped_rows = merge


def census(job):
    label, path, number, secret = job
    _install()
    del FOUND[:]
    from truedoc.pipeline import ConvertOptions, load_document
    try:
        load_document(path, ConvertOptions(frontmatter=False, pages=[number]))
    except Exception as exc:
        return [{"page": label, "error": repr(exc)[:100]}]
    return [dict(r, page=label, held_out=secret, **({"text": "(held out)", "above": "(held out)"} if secret else {})) for r in FOUND]


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
    rows = [r for r in rows if "slack" in r]
    flush = [r for r in rows if abs(r["dx"]) <= 1.5 and not r["band"] and not r["bullet"]]
    print("one-cell rows with no label under a ONE-line cell: %d | flush left, not a band, no tick or cross: %d" % (len(rows), len(flush)))
    wrap = [r for r in flush if r["slack"] < 0]
    fits = [r for r in flush if r["slack"] >= 0]
    print("  the first word would NOT have fitted above (a wrap): %d | it would have fitted (a break meant): %d" % (len(wrap), len(fits)))
    for title, group in (("WOULD NOT HAVE FITTED", wrap), ("would have fitted", fits)):
        print("  --", title)
        seen = set()
        for r in sorted(group, key=lambda r: r["slack"]):
            key = (r["text"], r["above"])
            if key in seen:
                continue
            seen.add(key)
            if len(seen) > 22:
                break
            print("     slack %6.1f step %-5s %-44s | ...%-32s | %s" % (r["slack"], r["step"], r["page"][-44:], r["above"][-32:], r["text"][:40]))
