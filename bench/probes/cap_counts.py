"""Which characters the reader's width cap cuts back, page by page, on whichever reader is on the path.

A version of the cap that only narrows another reads a page the same as the wider one unless it declines a cut the
wider one made. This patches a counting copy of the reader's `_geometry` in memory (as `cap_fires.py` does), asks it
about every character of each page - a superset of what the reader asks about, and each character's cut depends only
on it and the one after - and writes one JSON line a page: the PDF, the page, and the indices of the characters it cut
back. Run it once on each reader (a worktree on PYTHONPATH), then --compare the two files: the pages that differ are the
only ones that can read differently, and so the only ones to convert again (`bench/tools/convert_compare.py`). The
third version of the cap, which stops only at a character beside the glyph, was checked against the second this way
over the benchmark, the insurance set and the Key Facts Sheets.

usage (repo root):
    PYTHONPATH=<worktree> cap_counts.py --out <file.jsonl> bench | insurance | kfs | from:<wider.jsonl> | <pdf>@<page> [...]
    cap_counts.py --compare <wider.jsonl> <narrower.jsonl>
`from:` reads only the pages an earlier run cut on, since a narrower version cuts nowhere else.
"""
import glob
import inspect
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BENCH = os.path.join(REPO, "bench", "data", "olmocr-bench", "bench_data", "pdfs")
SUBSETS = ("tables", "multi_column", "long_tiny_text", "headers_footers", "arxiv_math", "old_scans", "old_scans_math")
MANIFEST = os.path.join(REPO, "bench", "out", "insurance_set", "manifest.json")
LIB = os.path.join("C:/", "Users", "griff", "OneDrive", "Documents", "10 Have a crack",
                   "25 InsurancePlatform", "uploads", "PDS Docs")       # as in kfs_grade.py
ASSIGN = "                                    advance = ox2.value - x_off - origin[0]\n"
COUNTED = "                                    CAP_LOG.append(i)\n" + ASSIGN


def page_count(path: str) -> int:
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(path)
    try:
        return len(doc)
    finally:
        doc.close()


def targets(names):
    for name in names:
        if name == "bench":
            for subset in SUBSETS:
                for path in sorted(glob.glob(os.path.join(BENCH, subset, "*.pdf"))):
                    yield path, 1
        elif name == "insurance":
            manifest = json.load(open(MANIFEST, encoding="utf-8"))
            items = manifest if isinstance(manifest, list) else next(v for v in manifest.values() if isinstance(v, list))
            for e in items:
                yield e["pdf"], int(e["page"])
        elif name == "kfs":
            for path in sorted(glob.glob(os.path.join(LIB, "*", "*", "*.pdf"))):
                base = os.path.basename(path).lower()
                insurer = path.replace("\\", "/").split("/")[-3]
                if ("kfs" in base or "key-fact" in base or "key_fact" in base) and not insurer.startswith("zz_"):
                    for number in range(1, page_count(path) + 1):
                        yield path, number
        elif name.startswith("from:"):
            for row in map(json.loads, open(name[len("from:"):], encoding="utf-8")):
                if row.get("cuts"):
                    yield row["pdf"], int(row["page"])
        else:
            path, number = name.rsplit("@", 1)
            yield path, int(number)


def count(out: str, names: list[str]) -> None:
    import pypdfium2 as pdfium
    from truedoc.extract import pdftext_rawdict as prd
    source = inspect.getsource(prd._geometry)
    if source.count(ASSIGN) != 1:
        sys.exit(f"the cap's cut found {source.count(ASSIGN)} times in {prd.__file__}")
    print(f"reader: {prd.__file__}", flush=True)
    prd.__dict__["CAP_LOG"] = []
    exec(compile(source.replace(ASSIGN, COUNTED), prd.__file__, "exec"), prd.__dict__)
    done = 0
    with open(out, "w", encoding="utf-8") as fh:
        for path, number in targets(names):
            row = {"pdf": path.replace("\\", "/"), "page": number}
            try:
                doc = pdfium.PdfDocument(path)
                try:
                    page = doc[number - 1]
                    tp = page.get_textpage()
                    n = tp.count_chars()
                    tp.close()
                    page.close()
                finally:
                    doc.close()
                prd.CAP_LOG.clear()
                prd._geometry(path, number, set(range(n)))
                row["cuts"] = sorted(prd.CAP_LOG)
            except Exception as exc:
                row["error"] = repr(exc)[:200]
            fh.write(json.dumps(row) + "\n")
            fh.flush()
            done += 1
            if done % 200 == 0:
                print(f"  {done} pages", flush=True)
    print(f"{done} pages written to {out}", flush=True)


def compare(wider: str, narrower: str) -> None:
    def load(name):
        return {(r["pdf"], r["page"]): r for r in map(json.loads, open(name, encoding="utf-8"))}
    wide, narrow = load(wider), load(narrower)
    differ, errors, widened = [], 0, 0
    for key in sorted(wide):
        w, n = wide[key], narrow.get(key)
        if "cuts" not in w or (n is not None and "cuts" not in n) or (n is None and w["cuts"]):
            errors += 1
            continue
        if n is None:
            continue    # a page the wider reader did not cut: the narrower cannot cut it either
        if not set(n["cuts"]) <= set(w["cuts"]):
            widened += 1
            print(f"  NOT A NARROWING: {key[0].rsplit('/', 1)[-1]} p{key[1]}")
        if n["cuts"] != w["cuts"]:
            differ.append((key, len(w["cuts"]), len(n["cuts"])))
    print(f"{len(wide)} pages; cut on {sum(1 for r in wide.values() if r.get('cuts'))} by the wider reader, "
          f"{sum(1 for r in narrow.values() if r.get('cuts'))} by the narrower; {errors} unread or missing; "
          f"{widened} not a narrowing; {len(differ)} read differently:")
    for (pdf, page), a, b in differ:
        print(f"  {a:4d} -> {b:4d}  {pdf}@{page}")


def main() -> None:
    args = sys.argv[1:]
    if args[:1] == ["--compare"]:
        compare(args[1], args[2])
    elif args[:1] == ["--out"]:
        count(args[1], args[2:])
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
