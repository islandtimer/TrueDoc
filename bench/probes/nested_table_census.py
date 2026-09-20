"""Which table cells hold a table of their own? (D038: such a cell is written as a table inside the cell.)

CGU's Key Facts Sheet sets, in the third cell of "High value items and collections":

    Policy                    Item Limit     Overall Limit
    Accidental Damage Home    $2,500/item    20% of Contents SI or $7,500 (whichever is higher)
    Listed Events Home        $2,500/item    20% of Contents SI or $5,000 (whichever is higher)

What marks it, in geometry alone: inside ONE cell, several lines each break at a wide gap, and the pieces after
the gaps start at the same places line after line. Running text does not do that - a wide gap inside a line is
rare, and two lines sharing one is rarer. This census measures, for every body cell of every table that holds two
lines or more: how many of its lines have a piece starting after a wide gap, and how many such starts are shared by
two lines or more - so a detector can be chosen from the population and not from three sheets.

usage (repo root): nested_table_census.py <out.jsonl> kfs|insurance|bench [workers]
"""
import concurrent.futures
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "bench", "probes"))
WIDE = 1.0          # of the line's own height: a gap this wide is no word space
SAME = 2.5          # points: two pieces start at the same place


def _pieces(line):
    """x0 of each piece of a line that holds letters or digits: its first word, and every word standing a wide gap
    after the one before. A mark at the head of a list item (a tick, a bullet, "a)") is no piece: a list inside a
    cell breaks every line at the same place too, and is D028's business, not this census's."""
    words = sorted((w for w in line.words if w.text.strip()), key=lambda w: w.bbox.x0)
    if not words:
        return []
    h = max(line.bbox.height, 1.0)
    groups = [[words[0]]]
    for a, b in zip(words, words[1:]):
        if b.bbox.x0 - a.bbox.x1 >= WIDE * h:
            groups.append([b])
        else:
            groups[-1].append(b)
    out = []
    for g in groups:
        text = " ".join(w.text for w in g)
        if sum(ch.isalnum() for ch in text) >= 2 and not (len(g) == 1 and len(text) <= 3 and not text[-1:].isalnum()):
            out.append(g[0].bbox.x0)
    return out


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
        lines = [l for l in page.lines if l.text.strip()]
        for block in page.blocks:
            if block.kind != BlockKind.TABLE or block.table is None:
                continue
            for cell in block.table.cells:
                if cell.bbox is None or cell.is_header or not cell.text.strip():
                    continue
                mine = [l for l in lines if cell.bbox.x0 - 1 <= l.bbox.cx <= cell.bbox.x1 + 1 and cell.bbox.y0 - 1 <= l.bbox.cy <= cell.bbox.y1 + 1]
                # a line the text layer already cut at a wide gap arrives as several `Line`s at one height: gather by row
                rows = {}
                for l in mine:
                    rows.setdefault(round(l.bbox.cy / 3.0), []).append(l)
                if len(rows) < 2:
                    continue
                starts_by_row = []
                for key in sorted(rows):
                    s = sorted(x for l in rows[key] for x in _pieces(l))
                    starts_by_row.append(s)
                inner = [s[1:] for s in starts_by_row]            # the pieces of a row that stand after a wide gap in it
                broken = sum(1 for s in inner if s)
                shared = []
                for x in sorted({round(x) for s in inner for x in s}):
                    n = sum(1 for s in inner if any(abs(x - y) <= SAME for y in s))
                    if n >= 2 and not any(abs(x - y) <= SAME for y, _ in shared):
                        shared.append((x, n))
                if broken >= 2:
                    found.append({"lines": len(rows), "broken": broken, "shared": shared, "n_shared_starts": len(shared),
                                  "most_lines_on_a_start": max((n for _, n in shared), default=0),
                                  "text": cell.text[:70], "row": cell.row, "col": cell.col, "n_cols": block.table.n_cols,
                                  "provenance": block.table.provenance})
    return [dict(r, page=label, held_out=secret, **({"text": "(held out)"} if secret else {})) for r in found]


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
    rows = [r for r in rows if "broken" in r]
    print("body cells of two lines or more with two lines broken at a wide gap: %d on %d pages" % (len(rows), len({r["page"] for r in rows})))
    strong = [r for r in rows if r["n_shared_starts"] >= 1]
    print("  ... where the pieces after the gap start at the same place on two lines or more: %d cells on %d pages (held-out pages, counted only: %d)"
          % (len(strong), len({r["page"] for r in strong}), len({r["page"] for r in strong if r["held_out"]})))
    for r in sorted(strong, key=lambda r: (-r["most_lines_on_a_start"], r["page"])):
        if r["held_out"]:
            continue
        print("   lines %2d broken %2d shared starts %s %-34s r%d c%d/%d %-12s %s" % (
            r["lines"], r["broken"], r["shared"], r["page"][-34:], r["row"], r["col"], r["n_cols"], r["provenance"][:12], r["text"][:60]))
