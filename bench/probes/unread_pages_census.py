"""What the pages the text-layer check rejects hold, and what TrueDoc's own OCR saw on them (23 September 2026).

A page whose text layer is rejected (`textlayer._assess_quality`) is reported `unreadable-pages` and ends its document
`incomplete`. Before a rule says which of them lost nothing, this counts, for every rejected page of a screen made by
`box_list_blank_census.py screen`:

- what the page draws: pictures, paths, and how many of the paths' segments are curves (a letter drawn as an outline
  is made of curves; a rule, a box or a ruled line for notes is not);
- what TrueDoc's OCR made of it with the product's options: nothing, a reading it rejected, or a reading it kept;
- the letters and digits OCR saw that the text layer does not hold - words on the page that nothing wrote;
- how the conversion ends.

Held-out pages are counted, never named, and none of their text is kept.

usage (repo root, the project's venv):
    unread_pages_census.py convert library|bench-all|insurance <screen.jsonl> <out.jsonl> [workers] [--suspect-or-no-picture]
    unread_pages_census.py report <out.jsonl> [<before.jsonl>]

`report` with a second file (the same pages converted by another code state) counts documents both ways: a document
ends `incomplete` without a vision reader exactly when one of its pages is reported unreadable, and a page the text
check accepts is never so reported, so the rejected pages decide it.
"""
import collections
import concurrent.futures
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "bench", "probes"))
sys.path.insert(0, os.path.join(REPO, "bench", "tools"))
from box_list_blank_census import f4_kind, jobs  # noqa: E402

_WORD = re.compile(r"[^\W_]+")


def curves(path: str, number: int) -> dict:
    """Paths on the page, and the curve segments among all their segments (forms opened)."""
    import pypdfium2 as pdfium
    import pypdfium2.raw as raw

    pdf = pdfium.PdfDocument(path)
    try:
        page = pdf[number - 1]
        paths = curved = segments = 0

        def walk(obj, depth=0):
            nonlocal paths, curved, segments
            kind = raw.FPDFPageObj_GetType(obj)
            if kind == raw.FPDF_PAGEOBJ_FORM and depth < 8:
                for i in range(raw.FPDFFormObj_CountObjects(obj)):
                    child = raw.FPDFFormObj_GetObject(obj, i)
                    if child:
                        walk(child, depth + 1)
            elif kind == raw.FPDF_PAGEOBJ_PATH:
                paths += 1
                n = raw.FPDFPath_CountSegments(obj)
                for i in range(min(n, 5000)):
                    seg = raw.FPDFPath_GetPathSegment(obj, i)
                    if seg:
                        segments += 1
                        curved += raw.FPDFPathSegment_GetType(seg) == raw.FPDF_SEGMENT_BEZIERTO

        for i in range(raw.FPDFPage_CountObjects(page.raw)):
            walk(raw.FPDFPage_GetObject(page.raw, i))
        return {"paths": paths, "segments": segments, "curves": curved}
    finally:
        pdf.close()


def convert_one(job):
    key, path, number, secret, insurer, kind, screen = job
    sys.path.insert(0, REPO)
    from truedoc.pipeline import ConvertOptions, convert_with_status, load_document

    row = {"doc": key, "page": number, "held_out": secret, "insurer": insurer, "f4": kind, "screen": screen}
    try:
        opts = ConvertOptions(frontmatter=False, pages=[number], layout=False)
        doc = load_document(path, opts)
        result = convert_with_status(path, opts)
    except Exception as exc:
        row["error"] = repr(exc)[:120]
        return row
    page = doc.pages[0]
    q, meta = page.quality, page.meta
    layer = {w.lower() for word in page.words for w in _WORD.findall(word.text)}
    witness = [t for (t, _y0, _y1) in meta.get("witness_lines") or []]
    unseen = [w for t in witness for w in _WORD.findall(t) if w.lower() not in layer]
    body = sum(1 for c in result.markdown if c.isalnum())
    row.update({
        "kind": q.kind, "usable": q.usable, "alnum": q.n_alnum, "garbage": round(q.garbage_fraction, 3),
        "images": len(page.images), "image_share": round(q.image_coverage, 3),
        "ocr": "kept" if q.kind == "ocr-truedoc" else "empty" if meta.get("ocr_empty") else
               "rejected" if meta.get("ocr_rejected") else "turned" if meta.get("ocr_turn") else "none",
        "ocr_alnum": sum(1 for t in witness for c in t if c.isalnum()),
        "ocr_unseen_alnum": sum(len(w) for w in unseen),
        "body_alnum": body, "completion": result.completion,
        "issues": sorted({i.code for i in result.issues}),
        **curves(path, number),
    })
    if not secret:
        row["unseen"] = unseen[:20]
        row["layer_text"] = " ".join(w.text for w in page.words)[:120]
    return row


def convert(pop, screen_path, out_path, workers=4, narrow=False):
    paths = {j[0]: j[1] for j in jobs(pop)}
    todo = []
    for line in open(screen_path, encoding="utf-8"):
        r = json.loads(line)
        if "error" in r or r["quality"]["usable"]:
            continue
        if narrow and r["objects"]["image"] and r["quality"]["kind"] != "suspect":
            continue                      # a scan: a picture may hold words, and OCR on each is slow
        screen = {"kind": r["quality"]["kind"], "alnum": r["quality"]["alnum"], "objects": r["objects"],
                  "scripts": r["scripts"]}
        todo.append((r["doc"], paths[r["doc"]], r["page"], r["held_out"], r["insurer"], f4_kind(r), screen))
    print("pages to convert:", len(todo), flush=True)
    with open(out_path, "w", encoding="utf-8") as out, \
            concurrent.futures.ProcessPoolExecutor(workers) as pool:
        for i, row in enumerate(pool.map(convert_one, todo, chunksize=2), 1):
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            if i % 25 == 0:
                print(i, "done", flush=True)


def _documents(rows):
    lost = {r["doc"] for r in rows if "unreadable-pages" in r.get("issues", [])}
    held = {r["doc"] for r in rows if r["held_out"]}
    insurers = {r["insurer"] for r in rows if r["doc"] in lost}
    return len(lost), len(lost & held), len(insurers)


def report(out_path, before_path=None):
    rows = [json.loads(l) for l in open(out_path, encoding="utf-8")]
    if before_path:
        before = [json.loads(l) for l in open(before_path, encoding="utf-8")]
        print("documents ending incomplete for a rejected page: before %d (held-out %d, insurers %d), "
              "now %d (held-out %d, insurers %d)" % (*_documents(before), *_documents(rows)))
        fates = collections.Counter(("blank" if "blank-pages" in r.get("issues", []) else
                                     "lost" if "unreadable-pages" in r.get("issues", []) else "read")
                                    for r in rows if "error" not in r and r.get("ocr") != "kept")
        print("rejected pages OCR did not replace, now:", dict(fates))
    ok = [r for r in rows if "error" not in r]
    print("pages %d (held-out %d), failed %d" % (len(rows), sum(r["held_out"] for r in rows), len(rows) - len(ok)))
    still = [r for r in ok if "unreadable-pages" in r["issues"]]
    print("still reported unreadable with OCR on: %d (held-out %d); OCR kept a reading on %d" % (
        len(still), sum(r["held_out"] for r in still), sum(r["ocr"] == "kept" for r in ok)))
    by = collections.defaultdict(list)
    for r in still:
        by[r["f4"]].append(r)
    for kind, rs in sorted(by.items(), key=lambda kv: -len(kv[1])):
        ocr = collections.Counter(r["ocr"] for r in rs)
        print("\n%-30s pages %4d (held-out %3d) docs %3d | ocr %s" % (
            kind, len(rs), sum(r["held_out"] for r in rs), len({r["doc"] for r in rs}), dict(ocr)))
        print("   no curves %d | curves 1-50 %d | curves >50 %d | OCR saw words the layer lacks (>=20 alnum) %d, (1-19) %d" % (
            sum(r["curves"] == 0 for r in rs), sum(0 < r["curves"] <= 50 for r in rs), sum(r["curves"] > 50 for r in rs),
            sum(r["ocr_unseen_alnum"] >= 20 for r in rs), sum(0 < r["ocr_unseen_alnum"] < 20 for r in rs)))
        print("   body written: nothing %d, some %d" % (sum(r["body_alnum"] == 0 for r in rs),
                                                         sum(r["body_alnum"] > 0 for r in rs)))


if __name__ == "__main__":
    if sys.argv[1] == "convert":
        args = [a for a in sys.argv[2:] if not a.startswith("--")]
        convert(args[0], args[1], args[2], int(args[3]) if len(args) > 3 else 4, "--suspect-or-no-picture" in sys.argv)
    else:
        report(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
