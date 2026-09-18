"""Pages whose horizontal rules are drawn in pieces meeting at the same x on several rows, with no vertical rule there.

QBE's home PDS page 16 sets a table of ticks and crosses with no vertical rules: each row's rule is three strokes that
meet at the two column edges, the same two x positions on every row. The ruled finder needs a vertical rule at every
crossing, builds no grid, and the eight marks the marks module reads have no cell to go to. A rule that read those joins
as column edges would fire on every page drawn that way. This counts them over the edges the finder itself reads
(`ruled_pdfium._edges_from_objects`, clipped to the page), before its merge joins the pieces back into one rule.

On 15 September: 3,213 of the insurance library's 23,870 pages, in 379 documents; 33 of the benchmark's 1,403;
5 of the insurance set's 25.

usage (repo root): PYTHONPATH=. joined_rules_census.py bench | insurance | library [...] [--workers 6]
"""
import collections
import concurrent.futures
import glob
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BENCH = os.path.join(REPO, "bench", "data", "olmocr-bench", "bench_data", "pdfs")
SUBSETS = ("tables", "multi_column", "long_tiny_text", "headers_footers", "arxiv_math", "old_scans", "old_scans_math")
MANIFEST = os.path.join(REPO, "bench", "out", "insurance_set", "manifest.json")
sys.path.insert(0, os.path.join(REPO, "bench", "tools"))
import doc_library  # noqa: E402
LIB = doc_library.root()
TOUCH = 1.0        # pieces meet: the next starts no more than this after the last ends
OVERLAP = 3.0      # ... or overlaps it by no more than this
MIN_PIECE = 10.0   # a dash is not a piece of a rule
SAME_Y = 0.75
SAME_X = 1.5
MIN_ROWS = 3


def joined_edges(path: str, number: int) -> list:
    import pypdfium2 as pdfium
    from truedoc.extract import pdfium_objects
    from truedoc.tables import ruled_pdfium as rp
    doc = pdfium.PdfDocument(path)
    try:
        w, h = doc[number - 1].get_size()
    finally:
        doc.close()
    objs = pdfium_objects.page_objects(path, number)
    if not objs:
        return []
    edges = rp._clip_to_page(rp._edges_from_objects(objs, None), (0.0, 0.0, float(w), float(h)))
    hs = sorted((e for e in edges if e["orientation"] == "h" and e["x1"] - e["x0"] >= MIN_PIECE), key=lambda e: (e["top"], e["x0"]))
    vs = [e for e in edges if e["orientation"] == "v"]
    rows = []
    for e in hs:
        if rows and abs(rows[-1][0]["top"] - e["top"]) <= SAME_Y:
            rows[-1].append(e)
        else:
            rows.append([e])
    joins = []
    for row in rows:
        pieces = sorted(row, key=lambda e: e["x0"])
        for a, b in zip(pieces, pieces[1:]):
            if -OVERLAP <= b["x0"] - a["x1"] <= TOUCH:
                joins.append(((a["x1"] + b["x0"]) / 2.0, a["top"]))
    joins.sort()
    found = []
    group = []
    for x, y in joins + [(1e9, 0.0)]:
        if group and x - group[-1][0] > SAME_X:
            ys = sorted({round(g[1], 1) for g in group})
            if len(ys) >= MIN_ROWS:
                gx = sum(g[0] for g in group) / len(group)
                crossed = any(abs(v["x0"] - gx) <= 2.0 and v["top"] <= ys[-1] and v["bottom"] >= ys[0] for v in vs)
                if not crossed:
                    found.append((round(gx, 1), len(ys), round(ys[0], 1), round(ys[-1], 1)))
            group = []
        group.append((x, y))
    return found


def scan_file(task):
    path, numbers = task
    hits, errors = [], 0
    for number in numbers:
        try:
            found = joined_edges(path, number)
        except Exception:
            errors += 1
            continue
        if found:
            hits.append((number, found))
    return path, len(numbers), hits, errors


def page_count(path: str) -> int:
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(path)
    try:
        return len(doc)
    finally:
        doc.close()


def tasks_for(name: str):
    if name == "bench":
        return [(p.replace(os.sep, "/"), [1]) for s in SUBSETS for p in sorted(glob.glob(os.path.join(BENCH, s, "*.pdf")))]
    if name == "insurance":
        manifest = json.load(open(MANIFEST, encoding="utf-8"))
        items = manifest if isinstance(manifest, list) else next(v for v in manifest.values() if isinstance(v, list))
        return [(e["pdf"], [int(e["page"])]) for e in items]
    if name == "library":
        paths = sorted(set(p.replace(os.sep, "/") for p in glob.glob(os.path.join(LIB, "**", "*.pdf"), recursive=True)
                           + glob.glob(os.path.join(LIB, "**", "*.PDF"), recursive=True)))
        out = []
        for p in paths:
            try:
                out.append((p, list(range(1, page_count(p) + 1))))
            except Exception:
                continue
        return out
    raise SystemExit(f"unknown corpus {name}")


def main() -> None:
    args = sys.argv[1:]
    workers = int(args[args.index("--workers") + 1]) if "--workers" in args else 6
    names = [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or args[i - 1] != "--workers")]
    for name in names:
        tasks = tasks_for(name)
        pages = errors = 0
        flagged = []
        with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
            for path, n, hits, err in pool.map(scan_file, tasks, chunksize=2):
                pages += n
                errors += err
                for number, found in hits:
                    flagged.append((path, number, found))
        documents = {p for p, _, _ in flagged}
        kfs = [f for f in flagged if any(k in f[0].lower().rsplit("/", 1)[-1] for k in ("kfs", "key-fact", "key_fact"))]
        print(f"== {name}: {pages} pages ({errors} unread); {len(flagged)} page(s) with rules joined at a shared x "
              f"and no vertical rule there, in {len(documents)} document(s); {len(kfs)} of them Key Facts Sheet pages", flush=True)
        for path, number, found in flagged[:25]:
            shown = path[len(LIB) + 1:] if path.startswith(LIB) else path.rsplit("/", 1)[-1]
            print(f"   {shown[:95]} p{number}: " + "; ".join(f"x {x} on {k} rules (y {a}-{b})" for x, k, a, b in found[:4]), flush=True)


if __name__ == "__main__":
    main()
