"""Text drawn inside a form that is itself drawn transparent: how much, where, and what does it say?

Benchmark tables/c8cdd4c4..._pg3 carries "ARTICLE IN PRESS" across the page at 45 degrees in 72-point type, and the
page shows none of it: the form holding it is drawn under an ExtGState of `/CA 0 /ca 0`. Inside the form the text
sets its own opacity back to 1, so the character's own alpha - all the hidden-text reader looks at - says visible,
and we published the letters: "# S", "# S", "# E", "PPalm kernel oil*", "R6.8", and a table's heading line broken.
PDFium does report the form's alpha (`FPDFPageObj_GetFillColor` on the form object: 0), so the veil can be known.

This census walks every page's objects, carries each form's alpha down to the text inside it, and lists the text
objects whose enclosing alpha is under 1 - with the alpha, so that a half-transparent watermark a reader DOES see is
told apart from one drawn at nothing.

usage (repo root): veiled_form_census.py <out.jsonl> kfs|insurance|bench [workers]
"""
import concurrent.futures
import ctypes
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "bench", "probes"))


def census(job):
    label, path, number, secret = job
    import pypdfium2 as pdfium
    import pypdfium2.raw as raw
    out = []
    try:
        doc = pdfium.PdfDocument(path)
        page = doc[number - 1]
        textpage = page.get_textpage()

        def alpha_of(obj):
            r, g, b, a = (ctypes.c_uint() for _ in range(4))
            fill = raw.FPDFPageObj_GetFillColor(obj, r, g, b, a)
            fa = a.value / 255.0 if fill else 1.0
            stroke = raw.FPDFPageObj_GetStrokeColor(obj, r, g, b, a)
            sa = a.value / 255.0 if stroke else 1.0
            return min(fa, sa) if (fill and stroke) else (fa if fill else sa)

        def text_of(obj):
            n = raw.FPDFTextObj_GetText(obj, textpage.raw, None, 0)
            if n <= 2:
                return ""
            buf = (ctypes.c_ushort * (n // 2 + 1))()
            raw.FPDFTextObj_GetText(obj, textpage.raw, buf, n)
            return bytes(buf)[:n - 2].decode("utf-16-le", "replace")

        def walk(obj, veil, depth):
            kind = raw.FPDFPageObj_GetType(obj)
            if kind == raw.FPDF_PAGEOBJ_FORM and depth < 8:
                inner = veil * alpha_of(obj)
                for i in range(raw.FPDFFormObj_CountObjects(obj)):
                    child = raw.FPDFFormObj_GetObject(obj, i)
                    if child:
                        walk(child, inner, depth + 1)
            elif kind == raw.FPDF_PAGEOBJ_TEXT and veil < 0.999:
                text = text_of(obj).strip()
                if text:
                    out.append({"page": label, "held_out": secret, "veil": round(veil, 3), "own": round(alpha_of(obj), 3),
                                "chars": len(text), "text": "(held out)" if secret else text[:60]})
            elif veil < 0.999:
                # What else stands under a veil: a fill drawn at nothing covers nothing, and the hidden-text reader
                # takes a later opaque fill for a cover.
                out.append({"page": label, "held_out": secret, "veil": round(veil, 3), "own": round(alpha_of(obj), 3),
                            "chars": 0, "text": {raw.FPDF_PAGEOBJ_PATH: "<path>", raw.FPDF_PAGEOBJ_IMAGE: "<image>"}.get(kind, "<other>")})

        for i in range(raw.FPDFPage_CountObjects(page.raw)):
            walk(raw.FPDFPage_GetObject(page.raw, i), 1.0, 0)
    except Exception as exc:
        return [{"page": label, "error": repr(exc)[:100]}]
    return out


if __name__ == "__main__":
    from orphan_row_census import jobs
    out, which = sys.argv[1], sys.argv[2]
    todo = list(jobs(which))
    print(len(todo), "pages", flush=True)
    with open(out, "w", encoding="utf-8") as f, concurrent.futures.ProcessPoolExecutor(max_workers=int(sys.argv[3]) if len(sys.argv) > 3 else 6) as pool:
        for rows in pool.map(census, todo, chunksize=4):
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    rows = [json.loads(l) for l in open(out, encoding="utf-8")]
    errors = [r for r in rows if "error" in r]
    rows = [r for r in rows if "veil" in r]
    for name, keep in (("drawn at nothing (veil 0)", lambda r: r["veil"] == 0), ("drawn faint (0 < veil < 1)", lambda r: r["veil"] > 0)):
        mine = [r for r in rows if keep(r)]
        print("%s: %d text objects, %d characters, %d pages (held-out pages, counted only: %d)"
              % (name, len(mine), sum(r["chars"] for r in mine), len({r["page"] for r in mine}), len({r["page"] for r in mine if r["held_out"]})))
        for page in sorted({r["page"] for r in mine if not r["held_out"]}):
            here = [r for r in mine if r["page"] == page]
            print("   %-46s %3d objects, veil %s, own %s: %s" % (page[-46:], len(here), sorted({r["veil"] for r in here}), sorted({r["own"] for r in here}),
                                                                 " | ".join(sorted({r["text"] for r in here}))[:120]))
    print("errors:", len(errors), [e["page"][-30:] for e in errors[:3]])
