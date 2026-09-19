"""A row cut where a second value starts: how often does a standing row carry a sentence on from the row above?

Reading the owner's Key Facts Sheets against their pages (18 September 2026) found one entry written
as two rows on AAMI's fire-and-theft sheets:

    | Fire and Explosion | Yes | Fire - no cover for loss or damage to contents from arcing, |
    |                    | No  | scorching, melting, or cigarette burns unless a fire spreads ... |

The answer cell holds two values, one a line ("Yes" for fire, "No" for explosion), and
`tables/aligned._merge_wrapped_rows` folds a line with several filled cells only when *every* one of
them reads as a continuation; "No" under "Yes" does not, so the sentence beside it is cut in two.
Pitch cannot decide it here (the table's next real row, "Flood", also starts one leading below).

The candidate: a row with no label in which one cell plainly carries a sentence on - the cell above
it stops without closing its sentence, and this one starts in lower case - is not a new row, since no
cell of a new row opens in the middle of a sentence. This census lists every row the merger leaves
standing that the candidate would fold, with what the *other* cells hold, so the rule can be judged
on its population before it is written.

usage (repo root): split_row_census.py <out.jsonl> kfs|insurance|bench [workers [pages.txt]]
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
    if getattr(aligned, "_split_census", False):
        return
    aligned._split_census = True
    merge0 = aligned._merge_wrapped_rows

    def merge(grid, rows, size, columns=None, joined=None):
        out, out_rows = merge0(grid, rows, size, columns, joined)
        bands = aligned._band_segments(out_rows, size)
        for k in range(1, len(out)):
            cells, prev = out[k], out[k - 1]
            filled = [i for i, c in enumerate(cells) if c]
            if cells[0] or len(filled) < 2 or len(cells) != len(prev):
                continue
            lines = sorted({round(s.bbox.y0) for s in out_rows[k].segments if s.text.strip()})
            first = min(lines) if lines else None
            head = {}                                      # each filled cell's FIRST line, which is where the row was cut
            for s in sorted(out_rows[k].segments, key=lambda s: (s.bbox.y0, s.bbox.x0)):
                if s.text.strip() and first is not None and s.bbox.y0 - first <= 0.5 * size:
                    c = aligned._column_of(s.bbox, columns) if columns else None
                    if c is not None:
                        head[c] = (head.get(c, "") + " " + s.text.strip()).strip()
            cut = [i for i in filled if prev[i] and prev[i].rstrip()[-1:] not in ".?!:" and head.get(i, cells[i])[:1].islower()
                   and not aligned._NUMERIC.match(head.get(i, cells[i]).strip())]
            if not cut:
                continue
            others = [i for i in filled if i not in cut]
            prev_y1 = max((s.bbox.y1 for s in out_rows[k - 1].segments if s.text.strip()), default=out_rows[k - 1].y1)
            FOUND.append({
                "cut": [[prev[i][-40:], head.get(i, cells[i])[:40]] for i in cut],
                "others": [[prev[i][-24:], head.get(i, cells[i])[:24]] for i in others],
                "others_above_empty": sum(1 for i in others if not prev[i]),
                "others_words": max((len(head.get(i, cells[i]).split()) for i in others), default=0),
                "gap": round((out_rows[k].y0 - prev_y1) / size, 2),
                "band": bool(aligned._is_band(k, out, out_rows, columns, bands, size)),
                "bullet": any(bool(aligned._BULLET_START.match(cells[i])) for i in filled),
                "columns": len(cells),
                # what a narrower gate would ask: does the table label its rows, does the row above open an entry,
                # is the carried-on cell running text, how does the cell above it end, how long are the other cells
                "label_share": round(sum(1 for r in out if r[0]) / max(1, len(out)), 2), "above_has_label": bool(prev[0]),
                "cut_words": [len(head.get(i, cells[i]).split()) for i in cut], "above_ends": [prev[i].rstrip()[-1:] for i in cut],
                "others_numeric": [bool(aligned._NUMERIC.match(head.get(i, cells[i]).strip())) for i in others],
                "others_word_counts": [len(head.get(i, cells[i]).split()) for i in others],
                "next_has_label": bool(out[k + 1][0]) if k + 1 < len(out) else None,
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
    return [dict(r, page=label, held_out=secret, **({"cut": "(held out)", "others": "(held out)"} if secret else {})) for r in FOUND]


if __name__ == "__main__":
    from orphan_row_census import jobs
    out, which = sys.argv[1], sys.argv[2]
    todo = list(jobs(which))
    if len(sys.argv) > 4:                                  # only the pages listed in a file, one label a line
        keep = {l.strip() for l in open(sys.argv[4], encoding="utf-8") if l.strip()}
        todo = [j for j in todo if j[0] in keep]
    print(len(todo), "pages", flush=True)
    with open(out, "w", encoding="utf-8") as f, concurrent.futures.ProcessPoolExecutor(max_workers=int(sys.argv[3]) if len(sys.argv) > 3 else 6) as pool:
        for rows in pool.map(census, todo, chunksize=2):
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    rows = [json.loads(l) for l in open(out, encoding="utf-8")]
    rows = [r for r in rows if "gap" in r]
    live = [r for r in rows if not r["band"] and not r["bullet"]]
    print("standing rows with no label, two cells or more, one of them carrying a sentence on: %d on %d pages (%d more are a band or open with a tick)"
          % (len(live), len({r["page"] for r in live}), len(rows) - len(live)))
    whole = [r for r in live if not r["others"]]
    print("  every filled cell carries on (the present rule should have folded these - why not?): %d" % len(whole))
    mixed = [r for r in live if r["others"]]
    print("  one cell carries on, another does not (the candidate's population): %d" % len(mixed))
    seen = set()
    for r in sorted(mixed, key=lambda r: (r["others_words"], r["page"])):
        if r["held_out"]:
            continue
        key = json.dumps([r["cut"], r["others"]], ensure_ascii=False)
        if key in seen:
            continue
        seen.add(key)
        if len(seen) > 60:
            break
        print("     gap %5.2f %-40s cut: ...%s || %s   others: %s" % (r["gap"], r["page"][-40:], r["cut"][0][0][-26:], r["cut"][0][1][:26],
                                                                       "; ".join("%s / %s" % (a[-14:], b[:16]) for a, b in r["others"])))
    print("  held-out sheets among them (counted, never listed): %d" % sum(1 for r in mixed if r["held_out"]))
