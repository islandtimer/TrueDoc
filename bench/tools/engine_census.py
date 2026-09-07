"""PyMuPDF against PDFium on every benchmark page: the first step of the licence decision (8 September 2026).

For each page, both engines read the text layer and the census records, per engine: real characters
(PDFium's own line-break characters left out), the text as a string, the set of font names, odd
characters (control, private-use, replacement), image and path counts, and the time taken. Then
per page: the agreement of the two texts (difflib ratio on the normalised strings), whether the
font sets agree, and the Type 3 fonts PyMuPDF sees (the dvips case the formula stage leans on).

    python bench/tools/engine_census.py <out.tsv>

The summary at the end of the file says how many pages disagree and where, so the decision rests
on numbers: if PDFium yields the same characters, fonts and boxes on the pages the formula stage
depends on, a PDFium extractor is viable; if not, the licence is the cheaper path.
"""
from __future__ import annotations

import ctypes
import difflib
import glob
import os
import re
import sys
import time
import unicodedata

import pymupdf
import pypdfium2 as pdfium
import pypdfium2.raw as raw

B = "bench/data/olmocr-bench/bench_data/pdfs"
_WS = re.compile(r"\s+")


def _norm(s: str) -> str:
    return _WS.sub(" ", unicodedata.normalize("NFC", s)).strip()


def _odd(ch: str) -> bool:
    o = ord(ch)
    return (o < 32 and ch not in "\t\n\r") or o == 0xFFFD or 0xE000 <= o <= 0xF8FF


def read_mupdf(path: str):
    t0 = time.time()
    doc = pymupdf.open(path)
    page = doc[0]
    raw_dict = page.get_text("rawdict")
    chars: list[str] = []
    fonts: set[str] = set()
    for b in raw_dict["blocks"]:
        if b["type"] != 0:
            continue
        for l in b["lines"]:
            for s in l["spans"]:
                fonts.add(s["font"])
                for c in s["chars"]:
                    chars.append(c["c"])
            chars.append("\n")
    type3 = sorted({f[3] for f in page.get_fonts(full=True) if f[2] == "Type3"})
    n_img = len(page.get_images(full=True))
    n_path = len(page.get_drawings())
    doc.close()
    text = "".join(chars)
    return {"n": sum(1 for c in chars if c != "\n"), "text": text, "fonts": fonts, "odd": sum(1 for c in chars if _odd(c)),
            "type3": type3, "img": n_img, "path": n_path, "t": time.time() - t0}


def read_pdfium(path: str):
    t0 = time.time()
    doc = pdfium.PdfDocument(path)
    page = doc[0]
    tp = page.get_textpage()
    n = tp.count_chars()
    buf = ctypes.create_string_buffer(256)
    flags = ctypes.c_int()
    chars: list[str] = []
    fonts: set[str] = set()
    generated = 0
    for i in range(n):
        u = raw.FPDFText_GetUnicode(tp, i)
        if raw.FPDFText_IsGenerated(tp, i):
            generated += 1
            chars.append("\n" if u in (10, 13) else " ")
            continue
        ln = raw.FPDFText_GetFontInfo(tp, i, buf, 256, flags)
        if ln > 1:
            fonts.add(buf.raw[: ln - 1].decode("utf-8", "replace"))
        chars.append(chr(u) if u else "�")
    n_img = n_path = 0
    for obj in page.get_objects(max_depth=2):
        if obj.type == raw.FPDF_PAGEOBJ_IMAGE:
            n_img += 1
        elif obj.type == raw.FPDF_PAGEOBJ_PATH:
            n_path += 1
    doc.close()
    text = "".join(chars)
    return {"n": n - generated, "text": text, "fonts": fonts, "odd": sum(1 for c in chars if _odd(c)), "img": n_img, "path": n_path, "t": time.time() - t0}


def main() -> None:
    out_path = sys.argv[1]
    out = open(out_path, "w", encoding="utf-8")
    print("page\tmu_chars\tpdfium_chars\tagree\tfonts_agree\tmu_odd\tpdfium_odd\ttype3\tmu_img\tpdfium_img\tmu_path\tpdfium_path\tmu_s\tpdfium_s\tbag\tonly_mu\tonly_pdfium", file=out)
    rows = []
    t0 = time.time()
    for pdf in sorted(glob.glob(os.path.join(B, "*", "*.pdf"))):
        page_id = os.path.basename(os.path.dirname(pdf)) + "/" + os.path.basename(pdf)[:-4]
        try:
            m = read_mupdf(pdf)
            f = read_pdfium(pdf)
        except Exception as exc:  # noqa: BLE001
            print(page_id + "\tERROR\t" + repr(exc)[:120], file=out, flush=True)
            continue
        a, b = _norm(m["text"]), _norm(f["text"])
        agree = difflib.SequenceMatcher(None, a, b, autojunk=False).ratio() if (a or b) else 1.0
        # The same characters in a different order are not a disagreement about characters:
        # compare the bags of non-space characters as well.
        from collections import Counter

        ca, cb = Counter(c for c in a if not c.isspace()), Counter(c for c in b if not c.isspace())
        only_mu = sum((ca - cb).values())
        only_pf = sum((cb - ca).values())
        bag = 1.0 - (only_mu + only_pf) / max(1, sum(ca.values()) + sum(cb.values()))
        mu_fonts = {x.split("+")[-1] for x in m["fonts"]}
        pf_fonts = {x.split("+")[-1] for x in f["fonts"]}
        fonts_agree = mu_fonts == pf_fonts
        row = (page_id, m["n"], f["n"], round(agree, 4), int(fonts_agree), m["odd"], f["odd"], ";".join(m["type3"])[:60], m["img"], f["img"], m["path"], f["path"], round(m["t"], 3), round(f["t"], 3), round(bag, 4), only_mu, only_pf)
        rows.append(row)
        print("\t".join(str(x) for x in row), file=out, flush=True)
    print("", file=out)
    n = len(rows)
    print("pages: %d in %.0fs; PyMuPDF %.1fs, PDFium %.1fs" % (n, time.time() - t0, sum(r[12] for r in rows), sum(r[13] for r in rows)), file=out)
    for thr in (0.999, 0.99, 0.95, 0.9):
        print("text agreement (in order) below %.3f: %d pages; bag of characters below %.3f: %d pages" % (thr, sum(1 for r in rows if r[3] < thr), thr, sum(1 for r in rows if r[14] < thr)), file=out)
    print("characters only PyMuPDF sees: %d on %d pages; only PDFium sees: %d on %d pages" % (sum(r[15] for r in rows), sum(1 for r in rows if r[15]), sum(r[16] for r in rows), sum(1 for r in rows if r[16])), file=out)
    print("font sets differ: %d pages" % sum(1 for r in rows if not r[4]), file=out)
    print("odd chars: PyMuPDF has some on %d pages, PDFium on %d; PDFium more than PyMuPDF on %d" % (sum(1 for r in rows if r[5]), sum(1 for r in rows if r[6]), sum(1 for r in rows if r[6] > r[5])), file=out)
    t3 = [r for r in rows if r[7]]
    print("pages with Type 3 fonts: %d; of them text agreement below 0.99: %d, PDFium with more odd chars: %d" % (len(t3), sum(1 for r in t3 if r[3] < 0.99), sum(1 for r in t3 if r[6] > r[5])), file=out)
    print("image counts differ: %d pages; path counts differ: %d pages" % (sum(1 for r in rows if r[8] != r[9]), sum(1 for r in rows if r[10] != r[11])), file=out)
    worst = sorted(rows, key=lambda r: r[14])[:25]
    print("lowest bag-of-characters agreement:", file=out)
    for r in worst:
        print("  %-60s bag %.3f order %.3f  chars %d/%d  only mu/pdfium %d/%d  odd %d/%d  type3 %s" % (r[0][:60], r[14], r[3], r[1], r[2], r[15], r[16], r[5], r[6], r[7][:30]), file=out)
    out.close()
    print("wrote", out_path)


if __name__ == "__main__":
    main()
