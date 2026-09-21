"""Characters set in symbol fonts across the owner's library: which codes of which fonts, how often, where.

Written to size the Webdings bullet read as "4" (21 September 2026). A symbol font's code is not the character its
text layer names - Webdings' "4" draws a triangle - and TrueDoc reads such a character by its drawing only when the
drawing is a tick, cross, dot, circle, square or box. This counts every character of a dingbat font (TrueDoc's own
list, `textlayer._DINGBAT_FONTS`) on every page of the library, by font family and code: characters, pages, documents,
insurers (the library's top folder), and whether it opens a line (a bullet's place). The sealed 19 are never opened;
documents held out by the meaning test or the Key Facts oracle are counted, never named. PyMuPDF's raw characters, a
reader independent of TrueDoc's.

usage (repo root, the project's venv):
    dingbat_census.py <out.json> [workers]
"""
import collections
import concurrent.futures
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "bench", "tools"))
_DINGBAT_FONTS = ("wingding", "webding", "dingbat", "marlett", "monotypesorts", "zapfdingbat")


def family(font: str) -> str | None:
    name = (font or "").split("+")[-1].lower().replace("-", "").replace(" ", "").replace("_", "")
    for key in _DINGBAT_FONTS:
        if key in name:
            if key == "wingding":
                return "wingdings3" if "3" in name else "wingdings2" if "2" in name else "wingdings"
            return key
    return None


def scan(path):
    import pymupdf
    found = collections.Counter()           # (family, code, opens_line) -> characters
    pages_with = collections.defaultdict(set)
    try:
        doc = pymupdf.open(path)
    except Exception as exc:
        return path, None, repr(exc)[:80]
    for number, page in enumerate(doc, 1):
        try:
            raw = page.get_text("rawdict")
        except Exception:
            continue
        for block in raw.get("blocks", []):
            for line in block.get("lines", []):
                first = True
                for span in line.get("spans", []):
                    fam = family(span.get("font", ""))
                    for ch in span.get("chars", []):
                        c = ch.get("c", "")
                        if not c or c.isspace():
                            continue
                        if fam:
                            cp = ord(c[0])
                            code = cp - 0xF000 if 0xF000 <= cp <= 0xF0FF else cp
                            found[(fam, code, first)] += 1
                            pages_with[(fam, code)].add(number)
                        first = False
    doc.close()
    return path, {"found": [[f, c, o, n] for (f, c, o), n in found.items()],
                  "pages": {"%s|%d" % k: sorted(v) for k, v in pages_with.items()}}, None


if __name__ == "__main__":
    import doc_library
    from word_check import held_out
    out = sys.argv[1]
    workers = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    root = doc_library.root()
    sealed = {l.strip().replace("\\", "/") for l in open(os.path.join(REPO, "bench", "insurance_holdout.txt"), encoding="utf-8")
              if l.strip() and not l.startswith("#")}
    sealed_names = {os.path.basename(s) for s in sealed}
    pdfs = sorted(os.path.join(d, f).replace("\\", "/") for d, _, fs in os.walk(root) for f in fs if f.lower().endswith(".pdf"))
    pdfs = [p for p in pdfs if doc_library.relative(p) not in sealed and os.path.basename(p) not in sealed_names]
    print(len(pdfs), "documents (the sealed 19 left out)", flush=True)
    per_key = collections.defaultdict(lambda: {"chars": 0, "opening": 0, "pages": 0, "docs": set(), "insurers": set(),
                                               "held_docs": 0, "example": None})
    errors = 0
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
        for path, res, err in pool.map(scan, pdfs, chunksize=4):
            if err:
                errors += 1
                continue
            secret = held_out(path)
            rel = doc_library.relative(path)
            # the brand's folder: the archive keeps its brands one level down ("zz_Archive/Aussie/..."), and counting
            # the archive as one insurer made three brands of one design look like two insurers (21 September 2026)
            parts = rel.split("/")
            insurer = parts[1] if parts[0].lower().startswith("zz_archive") and len(parts) > 2 else parts[0]
            keys_here = set()
            for fam, code, opening, n in res["found"]:
                k = (fam, code)
                per_key[k]["chars"] += n
                per_key[k]["opening"] += n if opening else 0
                keys_here.add(k)
            for k in keys_here:
                e = per_key[k]
                e["pages"] += len(res["pages"]["%s|%d" % k])
                e["insurers"].add(insurer)
                if secret:
                    e["held_docs"] += 1
                else:
                    e["docs"].add(rel)
                    if e["example"] is None:
                        e["example"] = [rel, res["pages"]["%s|%d" % k][0]]
    rows = []
    for (fam, code), e in sorted(per_key.items(), key=lambda kv: -kv[1]["chars"]):
        rows.append({"family": fam, "code": code, "char": chr(code) if 0x20 <= code < 0x110000 else "", "chars": e["chars"],
                     "opening_a_line": e["opening"], "pages": e["pages"], "tuned_docs": len(e["docs"]),
                     "held_docs": e["held_docs"], "insurers": len(e["insurers"]), "example": e["example"]})
    json.dump({"documents": len(pdfs), "errors": errors, "rows": rows}, open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("errors:", errors)
    print("%-12s %6s %-4s %7s %8s %6s %6s %6s %8s  %s" % ("font", "code", "chr", "chars", "opening", "pages", "docs", "held", "insurers", "example (tuned-on)"))
    for r in rows[:45]:
        print("%-12s 0x%04X %-4s %7d %8d %6d %6d %6d %8d  %s" % (r["family"], r["code"], r["char"] if r["char"].isprintable() else "?",
              r["chars"], r["opening_a_line"], r["pages"], r["tuned_docs"], r["held_docs"], r["insurers"],
              ("%s p%d" % (r["example"][0][-50:], r["example"][1])) if r["example"] else "-"))
