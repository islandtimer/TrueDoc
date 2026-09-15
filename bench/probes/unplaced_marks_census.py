"""Readable drawn marks that no table cell and no line takes, standing in columns.

On QBE's home PDS page 16 the marks module reads a tick or a cross under "If you have buildings cover" and "If you
have contents cover" on every row, and all eight are lost: no table was built there (the page draws no vertical
rules), so no cell takes them, and none sits just left of a line. This counts, page by page, the readable marks (tick,
cross, dot, circle, square, box) whose centre falls in no table cell the reader built and that lead no line of text,
and how many of them stand in a column - two or more at the same x on different rows - the shape of a table the reader
missed. Pages are built without the layout model (tables are found before it runs).

On 15 September: the insurance set, 29 of 60 readable marks placed nowhere, 12 of them in columns on 3 pages;
a one-in-ten sample of the rest of the library (2,867 pages), 2,558 of 4,183, 541 in columns on 141 pages of 93
documents. Counted without the layout model, so a table the model's box builds is not seen: ALDI's household PDS
page 31 is one, where the marks do reach cells, but the wrong ones.

usage (repo root): PYTHONPATH=. unplaced_marks_census.py insurance | kfs | sample:N | <pdf>@<page> [...] [--workers 8]
"""
import concurrent.futures
import glob
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MANIFEST = os.path.join(REPO, "bench", "out", "insurance_set", "manifest.json")
LIB = "C:/Users/griff/OneDrive/Documents/10 Have a crack/25 InsurancePlatform/uploads/PDS Docs"
READABLE = {"tick", "cross", "dot", "circle", "square", "box"}


def is_kfs(path: str) -> bool:
    base = path.lower().replace(os.sep, "/").rsplit("/", 1)[-1]
    return "kfs" in base or "key-fact" in base or "key_fact" in base


def scan(task):
    path, number = task
    try:
        import pymupdf
        from truedoc.marks import find_marks
        from truedoc.model import BlockKind
        from truedoc.pipeline import ConvertOptions, process_page
        doc = pymupdf.open(path)
        try:
            pdf_page = doc[number - 1]
            page = process_page(pdf_page, number, ConvertOptions(layout=False, ocr=False, marks=False, math=False))
            M = pdf_page.rotation_matrix if pdf_page.rotation else None
            marks = [m for m in find_marks(pdf_page, page, M) if m.kind in READABLE]
            size = page.body_font_size or 10.0
            cells = [c.bbox for b in page.blocks if b.kind == BlockKind.TABLE and b.table is not None
                     for c in b.table.cells if c.bbox is not None]
            unplaced = []
            for m in marks:
                cx, cy = m.bbox.cx, m.bbox.cy
                if any(c.contains_point(cx, cy) for c in cells):
                    continue
                leads = any(l.bbox.x0 >= m.bbox.x1 - 1.0 and l.bbox.x0 <= m.bbox.x1 + 2.5 * size
                            and l.bbox.y0 - 0.5 * m.bbox.height <= cy <= l.bbox.y1 + 0.5 * m.bbox.height
                            for l in page.lines)
                if not leads:
                    unplaced.append(m)
            columns = []
            for m in sorted(unplaced, key=lambda m: m.bbox.cx):
                if columns and abs(columns[-1][-1].bbox.cx - m.bbox.cx) <= 3.0:
                    columns[-1].append(m)
                else:
                    columns.append([m])
            in_columns = [col for col in columns
                          if len({round(m.bbox.cy / max(m.bbox.height, 1.0)) for m in col}) >= 2]
            n_col_marks = sum(len(col) for col in in_columns)
            kinds = sorted({m.kind for col in in_columns for m in col})
            return path, number, len(marks), len(unplaced), n_col_marks, len(in_columns), kinds, None
        finally:
            doc.close()
    except Exception as exc:
        return path, number, 0, 0, 0, 0, [], repr(exc)[:100]


def page_count(path: str) -> int:
    import pypdfium2 as pdfium
    d = pdfium.PdfDocument(path)
    try:
        return len(d)
    finally:
        d.close()


def library_paths() -> list:
    found = glob.glob(os.path.join(LIB, "**", "*.pdf"), recursive=True) + glob.glob(os.path.join(LIB, "**", "*.PDF"), recursive=True)
    return sorted(set(p.replace(os.sep, "/") for p in found))


def tasks_for(name: str) -> list:
    if name == "insurance":
        manifest = json.load(open(MANIFEST, encoding="utf-8"))
        items = manifest if isinstance(manifest, list) else next(v for v in manifest.values() if isinstance(v, list))
        return [(e["pdf"], int(e["page"])) for e in items]
    if name == "kfs":
        return [(p, n) for p in library_paths() if is_kfs(p) for n in range(1, page_count(p) + 1)]
    if name.startswith("sample:"):
        step = int(name.split(":", 1)[1])
        return [(p, n) for p in library_paths() if not is_kfs(p) for n in range(1, page_count(p) + 1, step)]
    path, number = name.rsplit("@", 1)
    return [(path, int(number))]


def main() -> None:
    args = sys.argv[1:]
    workers = int(args[args.index("--workers") + 1]) if "--workers" in args else 8
    names = [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or args[i - 1] != "--workers")]
    for name in names:
        tasks = tasks_for(name)
        rows, errors = [], 0
        with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
            for row in pool.map(scan, tasks, chunksize=4):
                if row[7]:
                    errors += 1
                rows.append(row)
        with_marks = [r for r in rows if r[2]]
        lost = [r for r in rows if r[4]]
        docs = {r[0] for r in lost}
        print(f"== {name}: {len(rows)} pages ({errors} failed); readable marks on {len(with_marks)} pages, "
              f"{sum(r[2] for r in rows)} marks, {sum(r[3] for r in rows)} placed nowhere; "
              f"{sum(r[4] for r in rows)} of those stand in columns, on {len(lost)} page(s) of {len(docs)} document(s)", flush=True)
        for r in sorted(lost, key=lambda r: -r[4])[:25]:
            shown = r[0][len(LIB) + 1:] if r[0].startswith(LIB) else r[0].rsplit("/", 1)[-1]
            print(f"   {shown[:90]} p{r[1]}: {r[4]} marks in {r[5]} column(s), {r[2]} read, kinds {r[6]}", flush=True)
        for r in [r for r in rows if r[7]][:3]:
            print(f"   failed: {r[0].rsplit('/', 1)[-1][:60]} p{r[1]}: {r[7]}", flush=True)


if __name__ == "__main__":
    main()
