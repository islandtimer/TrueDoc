"""Rows a table is left with that hold one cell and no label: are they the last line of the cell above?

`tables/aligned._merge_wrapped_rows` folds a wrapped line into the row above on what it *says* - it
starts in lower case, or the cell above ends on a connector or a comma. Reading the owner's Key
Facts Sheets against their pages (18 September 2026) found the lines that test cannot know:

    ...cover can be purchased to cover        |  | | Accidental Damage.
    ...anywhere in the world under            |  | | 'Portable Contents'.
    ...if you rent out your home. PDS pg.     |  | | 51-52

Words cannot settle it ("Accidental Damage" is as good a label as a continuation). The page can: a
wrapped line sits one *leading* under the line above it, and a new row starts after the row's
padding. This census measures that for every such row the merger leaves standing - how many lines
the cell above has in that column, their pitch, and the pitch from its last line to the orphan -
so a rule can be chosen from the population and not from three sheets.

usage (repo root): orphan_row_census.py <out.jsonl> kfs|insurance|bench [workers]
"""
import concurrent.futures
import glob
import json
import os
import statistics
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "bench", "tools"))
FOUND = []


def _install():
    from truedoc.tables import aligned
    if getattr(aligned, "_census", False):
        return
    aligned._census = True
    merge0 = aligned._merge_wrapped_rows

    def merge(grid, rows, size, columns=None, joined=None):
        out, out_rows = merge0(grid, rows, size, columns, joined)
        for k in range(1, len(out)):
            cells = out[k]
            filled = [i for i, c in enumerate(cells) if c]
            if cells[0] or len(filled) != 1 or len(cells) < 2:
                continue
            i = filled[0]
            here = [s for s in out_rows[k].segments if s.text.strip()]
            if not here or not out[k - 1][i]:
                continue
            x0, x1 = min(s.bbox.x0 for s in here), max(s.bbox.x1 for s in here)
            above = sorted((s for s in out_rows[k - 1].segments if s.bbox.x1 > x0 - 2 and s.bbox.x0 < x1 + 60 and s.bbox.x0 > x0 - 40),
                           key=lambda s: s.bbox.y0)
            tops, lefts = [], []
            for s in above:                                 # one top, and one left edge, per printed line of the cell above
                if not tops or s.bbox.y0 - tops[-1] > 0.5 * size:
                    tops.append(s.bbox.y0)
                    lefts.append(s.bbox.x0)
            pitches = [b - a for a, b in zip(tops, tops[1:])]
            leading = statistics.median(pitches) if pitches else None
            step = here[0].bbox.y0 - tops[-1] if tops else None
            nxt = next((out_rows[j] for j in range(k + 1, len(out)) if out[j][0]), None)
            text = cells[i]
            first = text.lstrip("‘'\"“(")[:1]
            FOUND.append({
                "text": text[:60], "above_ends": out[k - 1][i][-40:], "column": i, "columns": len(cells),
                "lines_above": len(tops), "leading": round(leading, 2) if leading else None,
                "step": round(step, 2) if step is not None else None,
                "ratio": round(step / leading, 3) if leading and step is not None else None,
                "next_row_step": round((nxt.y0 - here[0].bbox.y0) / leading, 3) if leading and nxt is not None else None,
                "size": round(size, 1), "words": len(text.split()),
                # the other half of "the next line of the same paragraph": it starts where the lines above start
                "dx": round(x0 - lefts[-1], 1) if lefts else None,
                "dx_right": round(x1 - max(s.bbox.x1 for s in above), 1) if above else None,
                "starts": "digit" if first.isdigit() else "capital" if first.isupper() else "lower" if first.islower() else "other",
                "above_ends_sentence": out[k - 1][i].rstrip()[-1:] in ".!?",
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
    rows = []
    for r in FOUND:
        if secret:
            r = dict(r, text="(held out)", above_ends="(held out)")
        rows.append(dict(r, page=label, held_out=secret))
    return rows


def jobs(which):
    if which == "kfs":
        import doc_library
        import kfs_grade
        from truedoc.pipeline import first_pages
        for _ins, p in kfs_grade.sheets():
            for n in first_pages(p, 2):
                yield ("%s@%d" % (doc_library.relative(p), n), p, n, kfs_grade.held_out(p))
    elif which == "insurance":
        m = json.load(open(os.path.join(REPO, "bench", "out", "insurance_set", "manifest.json"), encoding="utf-8"))
        for e in (m if isinstance(m, list) else next(v for v in m.values() if isinstance(v, list))):
            yield (e["name"], e["pdf"], e["page"], False)
    else:
        b = os.path.join(REPO, "bench", "data", "olmocr-bench", "bench_data", "pdfs")
        scans = {l.split("\t")[0].strip() for l in open(os.path.join(REPO, "bench", "gpu", "pages.txt"), encoding="utf-8") if l.strip()}
        # The benchmark's held-out pages are counted and never listed, as the held-out sheets are: a census that prints
        # what a page says would otherwise put a held-out page's words in front of whoever writes the next rule.
        held = {l.strip()[:-4] for l in open(os.path.join(REPO, "bench", "holdout.txt"), encoding="utf-8")
                if l.strip() and not l.startswith("#")}
        for p in sorted(glob.glob(os.path.join(b, "*", "*.pdf"))):
            label = os.path.basename(os.path.dirname(p)) + "/" + os.path.basename(p)[:-4]
            if label not in scans:
                yield (label, p, 1, label in held)


if __name__ == "__main__":
    out, which = sys.argv[1], sys.argv[2]
    todo = list(jobs(which))
    print(len(todo), "pages", flush=True)
    with open(out, "w", encoding="utf-8") as f, concurrent.futures.ProcessPoolExecutor(max_workers=int(sys.argv[3]) if len(sys.argv) > 3 else 6) as pool:
        for n, rows in enumerate(pool.map(census, todo, chunksize=2), 1):
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
            if n % 200 == 0:
                print(" ", n, flush=True)
    rows = [json.loads(l) for l in open(out, encoding="utf-8")]
    rows = [r for r in rows if "text" in r]
    print("rows left standing with no label and one cell: %d on %d pages" % (len(rows), len({r["page"] for r in rows})))
    multi = [r for r in rows if r["lines_above"] >= 2 and r["ratio"] is not None]
    print("  ... under a cell of two lines or more (a leading to compare with): %d" % len(multi))
    for lo, hi in ((0, 0.9), (0.9, 1.1), (1.1, 1.3), (1.3, 2.0), (2.0, 99)):
        band = [r for r in multi if lo <= r["ratio"] < hi]
        print("      step / leading in [%.1f, %.1f): %3d" % (lo, hi, len(band)))
    near = [r for r in multi if 0.9 <= r["ratio"] < 1.1]
    flush = [r for r in near if r["dx"] is not None and abs(r["dx"]) <= 1.5]
    print("  of the %d one leading below: %d start at the left edge of the lines above (within 1.5 pt), %d do not" % (len(near), len(flush), len(near) - len(flush)))
    seen = set()
    print("  -- flush left, one leading below (distinct texts):")
    for r in sorted(flush, key=lambda r: r["page"]):
        if r.get("held_out"): continue               # counted above, never listed
        key = (r["text"], r["above_ends"])
        if key in seen: continue
        seen.add(key)
        print("     dx %5s ratio %.2f lines %d %-7s %-46s | ...%-28s | %s" % (r["dx"], r["ratio"], r["lines_above"], r["starts"], r["page"][-46:], r["above_ends"][-28:], r["text"][:44]))
    seen = set()
    print("  -- one leading below but NOT flush left (distinct texts, first 12):")
    for r in sorted([r for r in near if r not in flush], key=lambda r: r["page"]):
        if r.get("held_out"): continue
        key = r["text"]
        if key in seen: continue
        seen.add(key)
        if len(seen) > 12: break
        print("     dx %5s ratio %.2f %-46s | %s" % (r["dx"], r["ratio"], r["page"][-46:], r["text"][:50]))
    single = [r for r in rows if r["lines_above"] < 2]
    print("  -- under a one-line cell (no leading of its own to compare): %d; flush left %d" % (len(single), sum(1 for r in single if r["dx"] is not None and abs(r["dx"]) <= 1.5)))
    for r in [r for r in single if not r.get("held_out")][:10]:
        print("     dx %5s %-46s | ...%-28s | %s" % (r["dx"], r["page"][-46:], r["above_ends"][-28:], r["text"][:44]))
