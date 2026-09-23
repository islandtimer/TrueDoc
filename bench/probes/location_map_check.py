"""The location map checked on real pages: every part found where the parts before it put it, ranges in order and
inside the text, every box inside its page, every written cell found, every emphasis range inside a block - and, for
the insurance set, the markdown byte for byte what a conversion without the map wrote (`--same-as <folder>`).

Held-out pages are counted, never named. Written 23 September 2026.

usage (repo root, the project's venv):
    location_map_check.py bench|insurance|library <out.json> [--every N] [--same-as <insurance_set folder>] [workers]
"""
import concurrent.futures
import json
import os
import random
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "bench", "probes"))
sys.path.insert(0, os.path.join(REPO, "bench", "tools"))


def check(job):
    label, path, number, secret, same_as = job
    sys.path.insert(0, REPO)
    from truedoc.pipeline import ConvertOptions, convert_with_status
    try:
        r = convert_with_status(path, ConvertOptions(frontmatter=False, pages=[number], location_map=True))
    except Exception as exc:
        return {"page": label, "held_out": secret, "error": repr(exc)[:120]}
    md, m = r.markdown, r.location_map
    faults = []
    sizes = {p["page"]: p["size"] for p in m["pages"]}
    last = m["markdown"]["body_start"]
    ranges = []
    for b in m["blocks"]:
        if b["range"] is None:
            faults.append("block not found")
            continue
        s, e = b["range"]
        if not (last <= s <= e <= len(md)):
            faults.append("block range out of order")
        last = e
        ranges.append((s, e))
        for box in b["boxes"]:
            if box["box"] is None:
                continue
            w, h = sizes[box["page"]]
            x0, y0, x1, y1 = box["box"]
            if not (-1 <= x0 <= x1 <= w + 1 and -1 <= y0 <= y1 <= h + 1):
                faults.append("box off its page")
    by_id = {b["id"]: b for b in m["blocks"]}
    for c in m["cells"]:
        table = by_id[c["table"]]["range"]
        if c["range"] is None:
            continue
        if table is None or not (table[0] <= c["range"][0] <= c["range"][1] <= table[1]):
            faults.append("cell outside its table")
    cells_missing = sum(1 for c in m["cells"] if c["range"] is None and not c.get("empty"))
    for kind in ("bold", "italic"):
        for s, e in m["emphasis"][kind]:
            if not any(a <= s and e <= b for a, b in ranges):
                faults.append(kind + " outside a block")
    out = {"page": label, "held_out": secret, "blocks": len(m["blocks"]), "cells": len(m["cells"]),
           "cells_not_found": cells_missing, "in_place": m["markdown"]["all_found_in_place"], "faults": sorted(set(faults)),
           "bold": len(m["emphasis"]["bold"]), "italic": len(m["emphasis"]["italic"])}
    if same_as:
        ref = os.path.join(same_as, label + ".md")
        if os.path.exists(ref):
            out["same_text"] = open(ref, encoding="utf-8").read() == md
    return out


if __name__ == "__main__":
    which, out = sys.argv[1], sys.argv[2]
    every = int(sys.argv[sys.argv.index("--every") + 1]) if "--every" in sys.argv else 1
    same_as = sys.argv[sys.argv.index("--same-as") + 1] if "--same-as" in sys.argv else None
    workers = int(sys.argv[-1]) if sys.argv[-1].isdigit() and sys.argv[-2] not in ("--every",) else 4
    if which == "library":
        from side_label_icon_census import jobs as library_jobs
        rng = random.Random(23)
        docs = list(library_jobs("library"))
        rng.shuffle(docs)
        todo = []
        import pypdfium2 as pdfium
        for key, path, _pages, secret, _ins, _k in docs[:every]:
            try:
                n = len(pdfium.PdfDocument(path))
            except Exception:
                continue
            todo.append((key, path, rng.randint(1, n), secret, None))
    else:
        from order_screen import jobs
        todo = [(l, p, n, s, same_as) for i, (l, p, n, s) in enumerate(jobs(which)) if i % every == 0]
    print(len(todo), "pages", flush=True)
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
        rows = list(pool.map(check, todo, chunksize=2))
    json.dump(rows, open(out, "w", encoding="utf-8"), indent=0)
    ok = [r for r in rows if "error" not in r]
    print("pages %d (failed to convert %d) | every part in place on %d | pages with a fault %d: %s" % (
        len(rows), len(rows) - len(ok), sum(r["in_place"] for r in ok), sum(bool(r["faults"]) for r in ok),
        sorted({f for r in ok for f in r["faults"]})))
    print("blocks %d | cells %d, not found %d | bold ranges %d, italic %d" % (
        sum(r["blocks"] for r in ok), sum(r["cells"] for r in ok), sum(r["cells_not_found"] for r in ok),
        sum(r["bold"] for r in ok), sum(r["italic"] for r in ok)))
    if same_as:
        print("markdown the same as the conversion without the map: %d of %d" % (
            sum(1 for r in ok if r.get("same_text")), sum(1 for r in ok if "same_text" in r)))
    for r in ok:
        if (r["faults"] or not r["in_place"] or r["cells_not_found"]) and not r["held_out"]:
            print("  %-70s in place %s  cells missing %d  %s" % (r["page"][-70:], r["in_place"], r["cells_not_found"], r["faults"]))
