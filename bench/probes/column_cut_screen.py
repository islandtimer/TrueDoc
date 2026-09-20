"""Where do two code states of `tables/aligned._refine_segments` cut a table's columns differently?

`pure_function_screen.py` compares whole answers, and this function's answer holds rows of the module's own classes,
which never compare equal across two loaded copies of the module. The cuts do: a list of x positions. The working
tree's function runs as usual inside a whole conversion; the other state's, loaded from a worktree under another
module name, is asked the same question beside it, and a page is named when the two lists of cuts ever differ.
Those are the only pages the change can touch: convert them both ways and read them.

usage (repo root): column_cut_screen.py <other code root> <out.jsonl> kfs|insurance|bench [workers]
"""
import concurrent.futures
import copy
import importlib.util
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "bench", "probes"))
FOUND = []


def _install(other_root):
    from truedoc.tables import aligned
    if getattr(aligned, "_cut_screen", False):
        return
    aligned._cut_screen = True
    spec = importlib.util.spec_from_file_location("other_state_aligned", os.path.join(other_root, "truedoc", "tables", "aligned.py"))
    other = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = other
    spec.loader.exec_module(other)
    now, then = aligned._refine_segments, other._refine_segments

    def asked(rows, size, second_look=True):
        before = then(copy.deepcopy(rows), size, second_look)[1]
        out, cuts = now(rows, size, second_look)
        # Riding along, a count for a change NOT made: how often does a cut that stands (in either state) lie in a
        # word space - between two words of one segment less than the voting gap (0.4 of the size) apart? The placer
        # refuses a place a word crosses, with a point's grace either side, so a two-point word space passes it.
        for c in cuts:
            for r in rows:
                for s in r.segments:
                    ws = sorted(s.words, key=lambda w: w.bbox.x0)
                    for a, b in zip(ws, ws[1:]):
                        if a.bbox.x1 <= c <= b.bbox.x0 and b.bbox.x0 - a.bbox.x1 < 0.4 * size:
                            FOUND.append({"word_space": round(c, 1), "gap": round(b.bbox.x0 - a.bbox.x1, 2), "size": size,
                                          "first": (a.text + " | " + b.text)[:60], "n_rows": len(rows)})
        if [round(c, 1) for c in before] != [round(c, 1) for c in cuts]:
            FOUND.append({"other": [round(c, 1) for c in before], "now": [round(c, 1) for c in cuts], "n_rows": len(rows),
                          "first": " | ".join(s.text for s in rows[0].segments)[:90] if rows else ""})
        return out, cuts

    aligned._refine_segments = asked


def screen(job):
    other_root, (label, path, number, secret) = job
    _install(other_root)
    del FOUND[:]
    from truedoc.pipeline import ConvertOptions, convert
    try:
        convert(path, ConvertOptions(frontmatter=False, pages=[number]))
    except Exception as exc:
        return [{"page": label, "error": repr(exc)[:100]}]
    return [dict(r, page=label, held_out=secret, **({"first": "(held out)"} if secret else {})) for r in FOUND]


if __name__ == "__main__":
    from orphan_row_census import jobs
    other_root, out, which = sys.argv[1:4]
    todo = [(other_root, j) for j in jobs(which)]
    print(len(todo), "pages", flush=True)
    with open(out, "w", encoding="utf-8") as f, concurrent.futures.ProcessPoolExecutor(max_workers=int(sys.argv[4]) if len(sys.argv) > 4 else 6) as pool:
        for n, rows in enumerate(pool.map(screen, todo, chunksize=2), 1):
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
            if n % 100 == 0:
                print(" ", n, flush=True)
    rows = [json.loads(l) for l in open(out, encoding="utf-8")]
    errors = [r for r in rows if "error" in r]
    spaces = [r for r in rows if "word_space" in r]
    print("cuts standing in a word space (a count, nothing is changed by it): %d on %d pages (held-out pages, counted only: %d)"
          % (len(spaces), len({r["page"] for r in spaces}), len({r["page"] for r in spaces if r["held_out"]})))
    for page in sorted({r["page"] for r in spaces if not r["held_out"]})[:25]:
        mine = [r for r in spaces if r["page"] == page]
        print("   %-44s %3d: %s" % (page[-44:], len(mine), "; ".join(sorted({"%s (%.1f)" % (r["first"], r["gap"]) for r in mine}))[:150]))
    rows = [r for r in rows if "now" in r]
    print("the cuts differ on %d calls, %d pages (held-out pages among them, counted and never listed: %d); conversion errors: %d"
          % (len(rows), len({r["page"] for r in rows}), len({r["page"] for r in rows if r["held_out"]}), len(errors)))
    for page in sorted({r["page"] for r in rows if not r["held_out"]}):
        for r in [r for r in rows if r["page"] == page][:3]:
            added = [c for c in r["now"] if c not in r["other"]]
            print("   %-44s rows %3d  new cuts %s (of %d)  %s" % (page[-44:], r["n_rows"], added, len(r["now"]), r["first"][:70]))
