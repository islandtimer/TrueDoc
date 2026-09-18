"""Pages across the whole insurance library whose text layer has lost letters to its ligatures, and whether the reader
reads them whole.

`lossy_ligatures.py` read 405 pages - the insurance set's and the Key Facts Sheets' first two - and found one, RAA's
landlord PDS page 22. This reads every page of every PDF in the library with PDFium and counts the words that are no
word until one of their f's is read as ff, fi, fl, ffi or ffl ("ofer", "Certifcate", "fnd"). For each page with at
least --min such words it reports the page's fonts by kind and the fonts inside its form XObjects (pypdf), builds the
page with the reader on PYTHONPATH (`pdftext_rawdict.build`, which reads spoiled ligatures back from their glyph names)
and checks the reader's text two ways: no such word is left, and each word they should have been ("offer",
"Certificate", "find") is there as many times as PDFium's text lost it, so an empty or failed reading cannot pass. On
15 September: 1,176 PDFs and 23,870 pages; 688 such words, and 130 pages with at least two in 6 documents - RAA's
landlord and home and contents PDSs, two editions of a CBA home insurance guide and two CBA target market
determinations - and the reader with the ligature repair read all 130 whole.

usage (repo root): PYTHONPATH=. library_ligatures.py [--min 2] [--workers 6]
"""
import collections
import concurrent.futures
import glob
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "bench", "tools"))
import doc_library  # noqa: E402
LIB = doc_library.root()                                                # as in kfs_grade.py
with open(os.path.join(REPO, "truedoc", "data", "en_common_words.txt"), encoding="utf-8") as fh:
    VOCAB = {w.strip().lower() for w in fh if w.strip()}
WORD = re.compile("[A-Za-z]+")
EXPANSIONS = ("ff", "fi", "fl", "ffi", "ffl")


def repair(token: str):
    low = token.lower()
    if low in VOCAB or "f" not in low or len(low) < 3:
        return None
    for i, ch in enumerate(low):
        if ch != "f":
            continue
        for e in EXPANSIONS:
            candidate = low[:i] + e + low[i + 1:]
            if candidate in VOCAB:
                return candidate
    return None


def lost_words(text: str) -> list:
    return [(tok, fixed) for tok in WORD.findall(text) if (fixed := repair(tok))]


def scan(path: str):
    import pypdfium2 as pdfium
    try:
        doc = pdfium.PdfDocument(path)
    except Exception as exc:
        return path, 0, [], repr(exc)[:80]
    hits, count = [], 0
    try:
        count = len(doc)
        for i in range(count):
            try:
                page = doc[i]
                tp = page.get_textpage()
                text = tp.get_text_bounded()
                tp.close()
                page.close()
            except Exception:
                continue
            words = lost_words(text)
            if words:
                hits.append((i + 1, words))
    finally:
        doc.close()
    return path, count, hits, None


def fonts_of(path: str, number: int) -> str:
    from pypdf import PdfReader
    try:
        page = PdfReader(path).pages[number - 1]
        resources = page.get("/Resources")
        resources = resources.get_object() if resources is not None else {}
        kinds = collections.Counter()
        for ref in (resources.get("/Font") or {}).values():
            kinds[str(ref.get_object().get("/Subtype"))] += 1
        forms = collections.Counter()
        for ref in (resources.get("/XObject") or {}).values():
            xobj = ref.get_object()
            if xobj.get("/Subtype") != "/Form":
                continue
            inner = xobj.get("/Resources")
            inner = inner.get_object() if inner is not None else {}
            for fref in (inner.get("/Font") or {}).values():
                forms[str(fref.get_object().get("/Subtype"))] += 1
        page_part = ", ".join(f"{k} x{v}" for k, v in sorted(kinds.items())) or "none"
        form_part = ", ".join(f"{k} x{v}" for k, v in sorted(forms.items())) or "none"
        return f"page fonts: {page_part}; fonts in forms: {form_part}"
    except Exception as exc:
        return f"fonts unread ({exc!r})"[:120]


def reader_text(path: str, number: int) -> str:
    from truedoc.extract import pdftext_rawdict as prd
    prd._CACHE.clear()
    built = prd.build(path, number) or {}
    lines = []
    for block in built.get("blocks", []):
        for line in block.get("lines", []):
            lines.append("".join(c.get("c", "") for span in line.get("spans", []) for c in span.get("chars", [])))
    return " ".join(lines)


def main() -> None:
    args = sys.argv[1:]
    least = int(args[args.index("--min") + 1]) if "--min" in args else 2
    workers = int(args[args.index("--workers") + 1]) if "--workers" in args else 6
    found_paths = (glob.glob(os.path.join(LIB, "**", "*.pdf"), recursive=True)
                   + glob.glob(os.path.join(LIB, "**", "*.PDF"), recursive=True))
    paths = sorted(set(p.replace(os.sep, "/") for p in found_paths))
    pages = words_seen = unread = 0
    flagged = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
        for n, (path, count, hits, error) in enumerate(pool.map(scan, paths, chunksize=4), 1):
            pages += count
            unread += error is not None
            for number, words in hits:
                words_seen += len(words)
                if len(words) >= least:
                    flagged.append((path, number, words))
            if n % 200 == 0:
                print(f"  {n}/{len(paths)} files, {pages} pages, {len(flagged)} flagged", flush=True)
    import truedoc
    documents = collections.Counter(p for p, _, _ in flagged)
    print(f"\n{len(paths)} PDFs ({unread} unreadable), {pages} pages; {words_seen} lost-letter words in all, "
          f"{len(flagged)} page(s) with at least {least}, in {len(documents)} document(s):")
    for path, k in sorted(documents.items()):
        print(f"   {k:3d}  {path[len(LIB) + 1:]}")
    print(f"reader: {os.path.dirname(truedoc.__file__)}")
    whole = partly = empty = 0
    fonts_seen = collections.Counter()
    for path, number, words in flagged:
        ours = reader_text(path, number)
        left = lost_words(ours)
        low = ours.lower()
        want = collections.Counter(fixed for _, fixed in words)
        found = sum(min(k, len(re.findall("(?<![a-z])" + re.escape(w) + "(?![a-z])", low))) for w, k in want.items())
        fonts = fonts_of(path, number)
        fonts_seen[fonts] += 1
        if not ours.strip():
            empty += 1
        elif not left and found == sum(want.values()):
            whole += 1
            continue
        else:
            partly += 1
        print(f"== {path[len(LIB) + 1:]} p{number}: {len(words)} lost, reader text {len(ours)} chars, {len(left)} left, "
              f"{found} of {sum(want.values())} repaired forms present; {fonts}")
    print("fonts on the flagged pages:")
    for fonts, k in sorted(fonts_seen.items(), key=lambda kv: -kv[1]):
        print(f"   {k:3d}  {fonts}")
    print(f"\nthe reader reads {whole} of {len(flagged)} flagged page(s) whole - no lost word left and every repaired "
          f"form present; {partly} partly; {empty} with no reader text")


if __name__ == "__main__":
    main()
