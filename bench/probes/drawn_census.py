"""Pages on which `fill_grid.drawn_grids` reads at least one table - the only pages `redraw_tables` can change.

`redraw_tables` leaves a page's blocks as they are unless a group of filled cells there reads as a table, so this lists,
from the page objects and the text layer alone (no layout model), every page where that happens, with each grid's size.

On 15 Sept, with the rule as committed: drawn tables on 24 of the benchmark's 1,403 pages, and on 83 of the 380 Key Facts
Sheet pages kfs_grade converts (pages 1 and 2 of 190 sheets), most of those a 2 x 3 grid - the prescribed header drawn as
coloured cells.

usage (repo root): drawn_census.py bench | kfs [...] [--workers 2]     (truedoc from PYTHONPATH)
"""
import concurrent.futures
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO + "/bench/probes")
sys.path.insert(0, REPO + "/bench/tools")
sys.stdout.reconfigure(encoding="utf-8")


def scan(task):
    path, numbers = task
    from truedoc.extract import pdfium_objects
    from truedoc.extract.handle import open_pdf
    from truedoc.extract.textlayer import extract_page
    from truedoc.tables import fill_grid as fg
    from truedoc.tables import ruled_pdfium as rp
    from truedoc.tables.aligned import _join_lines

    hits, errors = [], 0
    try:
        doc = open_pdf(path)
    except Exception:
        return path, hits, len(numbers)
    try:
        for n in numbers:
            if n > len(doc):
                continue
            try:
                objs = pdfium_objects.page_objects(path, n) or []
                pdf_page = doc[n - 1]
                w, h = float(pdf_page.rect.width), float(pdf_page.rect.height)
                if len(fg.fills_from(objs, w, h)) < 4:
                    continue
                edges = rp._clip_to_page(rp._edges_from_objects(objs, None), (0.0, 0.0, w, h))
                page = extract_page(pdf_page, n)
                lines = sorted((l for l in page.lines if not l.rotated), key=lambda l: (round(l.bbox.cy, 1), l.bbox.x0))
                grids = fg.drawn_grids(objs, edges, lines, w, h, _join_lines)
                if grids:
                    hits.append((n, [(len(ys) - 1, len(xs) - 1) for xs, ys, cells in grids]))
            except Exception:
                errors += 1
    finally:
        doc.close()
    return path, hits, errors


def tasks(name):
    if name == "bench":
        import joined_rules_census as jr
        return jr.tasks_for("bench")
    if name == "kfs":
        from kfs_grade import sheets
        return [(path, [1, 2]) for _, path in sheets()]
    raise SystemExit(f"unknown corpus {name}")


def main():
    import truedoc
    print("truedoc from", truedoc.__file__, flush=True)
    args = sys.argv[1:]
    workers = int(args[args.index("--workers") + 1]) if "--workers" in args else 2
    names = [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or args[i - 1] != "--workers")]
    for name in names:
        todo = tasks(name)
        pages = sum(len(n) for _, n in todo)
        found, errors = [], 0
        with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
            for path, hits, err in pool.map(scan, todo, chunksize=4):
                errors += err
                found.extend((path, n, g) for n, g in hits)
        print(f"== {name}: {pages} pages ({errors} unread); drawn tables on {len(found)} page(s)", flush=True)
        for path, n, g in found:
            print(f"   {os.path.basename(path)[:70]} p{n}: " + ", ".join(f"{r} x {c}" for r, c in g), flush=True)


if __name__ == "__main__":
    main()
