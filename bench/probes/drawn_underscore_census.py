"""Underscores a page DRAWS and its text layer does not hold: how many, and what do they sit between?

LaTeX sets `\\_` as a small rule at the baseline, not as a character: "Japanese_spaniel" in a table of class names
(benchmark tables/8bc04603..._pg1) is, in the PDF's text, the two words "Japanese" and "spaniel" with a drawn rule
between them, and TrueDoc writes "Japanese spaniel". Found on 20 September 2026 in the tables work list; it is not a
table fault - any identifier on any such page loses its underscores, in a table or out.

What marks one, in geometry: a horizontal rule (or a flat filled rectangle) no longer than a wide letter, lying at
the baseline of a text line, in the gap between two words of that line, close to both. A rule under a word
(underlining), a table rule, a fraction bar, a blank to be filled in ("Name: ______") are longer, or stand under
text, or touch nothing on one side. This census lists every candidate with its length in ems, its height against
the baseline, and the gaps to the words either side, so the bounds can be chosen from the population.

usage (repo root): drawn_underscore_census.py <out.jsonl> kfs|insurance|bench [workers]
"""
import concurrent.futures
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "bench", "probes"))


def census(job):
    label, path, number, secret = job
    from truedoc.pipeline import ConvertOptions, load_document
    try:
        doc = load_document(path, ConvertOptions(frontmatter=False, pages=[number], layout=False, tables=False, math=False))
    except Exception as exc:
        return [{"page": label, "error": repr(exc)[:100]}]
    found = []
    import pymupdf
    from truedoc.model import BBox, Drawing
    raw_page = pymupdf.open(path)[number - 1]
    if raw_page.rotation:
        return []                                          # a turned page's drawings and lines are in different frames here
    # The PDF's own drawings, not `page.drawings`: TrueDoc's summary drops the shortest rules, and an underscore in
    # six-point type is under two points long (benchmark tables/3331dcc1..._pg2).
    raw = []
    for dr in raw_page.get_drawings():
        for item in dr["items"]:
            if item[0] == "l":
                a, b = item[1], item[2]
                if abs(a.y - b.y) <= 0.4 and 0.8 <= abs(a.x - b.x) <= 14.0:
                    raw.append(Drawing(kind="hline", bbox=BBox(min(a.x, b.x), min(a.y, b.y), max(a.x, b.x), max(a.y, b.y)), width=dr.get("width") or 0.0))
            elif item[0] == "re":
                r = item[1]
                if r.height <= 1.5 and 0.8 <= r.width <= 14.0:
                    raw.append(Drawing(kind="rect", bbox=BBox(r.x0, r.y0, r.x1, r.y1), width=0.0, fill=bool(dr.get("fill"))))
    for page in doc.pages:
        rules = raw
        if not rules:
            continue
        for line in page.lines:
            if line.rotated or len(line.words) < 1:
                continue
            em = max(line.bbox.height, 4.0)
            base = line.baseline if hasattr(line, "baseline") else line.bbox.y1
            words = sorted(line.words, key=lambda w: w.bbox.x0)
            for r in rules:
                if not (line.bbox.y0 - 0.2 * em <= r.bbox.cy <= line.bbox.y1 + 0.35 * em):
                    continue
                if not (line.bbox.x0 - em <= r.bbox.cx <= line.bbox.x1 + em):
                    continue
                left = max((w for w in words if w.bbox.x1 <= r.bbox.x0 + 0.5), key=lambda w: w.bbox.x1, default=None)
                right = min((w for w in words if w.bbox.x0 >= r.bbox.x1 - 0.5), key=lambda w: w.bbox.x0, default=None)
                over = [w for w in words if w.bbox.x0 < r.bbox.x1 - 0.5 and w.bbox.x1 > r.bbox.x0 + 0.5]
                found.append({
                    "len_em": round(r.bbox.width / em, 2), "thick": round(max(r.bbox.height, r.width), 2),
                    "below_base": round((r.bbox.cy - base) / em, 2),
                    "gap_left": round((r.bbox.x0 - left.bbox.x1) / em, 2) if left is not None else None,
                    "gap_right": round((right.bbox.x0 - r.bbox.x1) / em, 2) if right is not None else None,
                    "under_a_word": bool(over),
                    # measured against the words either side, which is what an underscore is set in (a line's height
                    # overstates the em where the identifier is in smaller type than the line)
                    "len_word_em": round(r.bbox.width / max(max((w.bbox.height for w in (left, right) if w is not None), default=em), 3.0), 2),
                    "joins_alnum": bool(left is not None and right is not None and left.text[-1:].isalnum() and right.text[:1].isalnum()),
                    "left": left.text[-14:] if left is not None else "", "right": right.text[:14] if right is not None else "",
                })
    return [dict(r, page=label, held_out=secret, **({"left": "(held out)", "right": "(held out)"} if secret else {})) for r in found]


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
    rows = [r for r in rows if "len_em" in r]
    print("short flat rules lying in a text line: %d on %d pages" % (len(rows), len({r["page"] for r in rows})))
    between = [r for r in rows if not r["under_a_word"] and r["gap_left"] is not None and r["gap_right"] is not None
               and r["gap_left"] <= 0.35 and r["gap_right"] <= 0.35]
    print("  between two words of the line, within a third of an em of both, under neither: %d on %d pages (held-out pages, counted only: %d)"
          % (len(between), len({r["page"] for r in between}), len({r["page"] for r in between if r["held_out"]})))
    import collections
    fingerprint = [r for r in between if r["joins_alnum"] and r["gap_right"] <= 0.03 and r["gap_left"] <= 0.10 and -0.06 <= r["below_base"] <= 0.20]
    print("  ... joining two alphanumeric ends, touching the word on its right, on or just under the baseline: %d on %d pages; their length in the words' own ems: %s"
          % (len(fingerprint), len({r["page"] for r in fingerprint}), sorted(collections.Counter(round(r["len_word_em"], 1) for r in fingerprint).items())))
    for r in fingerprint:
        if not r["held_out"]:
            print("      %-40s len %.2f (of words %.2f) base %+.2f gaps %.2f/%.2f  %s_%s" % (r["page"][-40:], r["len_em"], r["len_word_em"], r["below_base"], r["gap_left"], r["gap_right"], r["left"], r["right"]))
    for name, key in (("length in ems", "len_em"), ("height against the baseline, in ems (+ is below)", "below_base")):
        c = collections.Counter(round(r[key], 1) for r in between)
        print("   %s: %s" % (name, sorted(c.items())))
    seen = set()
    for r in between:
        if r["held_out"]:
            continue
        key = (r["page"], r["left"], r["right"])
        if key in seen:
            continue
        seen.add(key)
        if len(seen) > 45:
            break
        print("   %-40s len %.2f base %+.2f gaps %.2f/%.2f   %s _ %s" % (r["page"][-40:], r["len_em"], r["below_base"], r["gap_left"], r["gap_right"], r["left"], r["right"]))
