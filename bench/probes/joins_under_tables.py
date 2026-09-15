"""Where would a grid built from joined rules fire, if it fired only inside a confident table region with no table?

`joined_rules_census.py` found rules drawn in pieces that meet at a shared x on 3,213 library pages, most of them page
decoration, so the joins alone cannot be trusted. Gated by the layout model instead - a table region it scores 0.7 or
more, holding a join, over which the reader built no table - the rule would fire only where a table was plainly missed.
This takes the benchmark and insurance pages the census flags, converts each with the layout model, and lists, for every
trusted table region, the joins inside it and whether a table block already covers it.

On 15 September, of the 38 insurance and benchmark pages the census flags, the gate would fire in one region:
QBE's home PDS page 16.

usage (repo root): PYTHONPATH=. joins_under_tables.py      (joined_rules_census.py beside it)
"""
import concurrent.futures
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding="utf-8")


def main() -> None:
    import joined_rules_census as jr
    tasks = jr.tasks_for("insurance") + jr.tasks_for("bench")
    flagged = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=8) as pool:
        for path, n, hits, err in pool.map(jr.scan_file, tasks, chunksize=2):
            for number, found in hits:
                flagged.append((path, number, found))
    print(f"{len(flagged)} flagged page(s) of {len(tasks)}", flush=True)
    from truedoc.layout.base import RegionKind
    from truedoc.model import BlockKind
    from truedoc.pipeline import ConvertOptions, load_document
    fire = 0
    for path, number, found in flagged:
        name = path.replace(os.sep, "/").rsplit("/", 1)[-1][:60]
        try:
            doc = load_document(path, ConvertOptions(frontmatter=False, pages=[number]))
        except Exception as exc:
            print(f"== {name} p{number}: failed {exc!r}"[:160], flush=True)
            continue
        page = doc.pages[0]
        regions = [r for r in (page.meta.get("layout_regions") or []) if r.kind == RegionKind.TABLE and r.score >= 0.7]
        tables = [b for b in page.blocks if b.kind == BlockKind.TABLE]
        verdicts = []
        for r in regions:
            joins = [(x, k) for x, k, y0, y1 in found if r.bbox.x0 <= x <= r.bbox.x1 and y0 <= r.bbox.y1 and y1 >= r.bbox.y0]
            covered = any(b.bbox.overlap_fraction(r.bbox) > 0.5 or r.bbox.overlap_fraction(b.bbox) > 0.5 for b in tables)
            if joins and not covered:
                fire += 1
            verdicts.append(f"region {r.score:.2f} x {r.bbox.x0:.0f}-{r.bbox.x1:.0f} y {r.bbox.y0:.0f}-{r.bbox.y1:.0f}: "
                            f"{len(joins)} join(s){' - WOULD FIRE (no table there)' if joins and not covered else (' - table built' if covered else '')}")
        print(f"== {name} p{number}: {len(regions)} trusted table region(s), {len(tables)} table block(s)", flush=True)
        for v in verdicts:
            print(f"   {v}", flush=True)
    print(f"\nthe gated rule would fire in {fire} region(s)", flush=True)


if __name__ == "__main__":
    main()
