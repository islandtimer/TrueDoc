"""Text set on a slant - neither level nor upright: how much, where, what does it say?

`extract/textlayer.py` calls a line rotated when its direction's x part is under 0.5, that is, turned more than 60
degrees. A watermark set at 45 degrees ("ARTICLE IN PRESS", benchmark tables/c8cdd4c4..._pg3) is therefore LEVEL
text to us: its letters are sorted into the page's lines by their height on the page, and "P" joined "Palm kernel
oil*". That page's watermark is invisible and should never have been read at all (see veiled_form_census.py), but a
watermark a reader does see - DRAFT, SAMPLE, SPECIMEN - would go the same way. This census counts the characters
PDFium says are turned between 10 and 80 degrees from level (in any quadrant), a page at a time.

usage (repo root): diagonal_text_census.py <out.jsonl> kfs|insurance|bench [workers]
"""
import concurrent.futures
import json
import math
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "bench", "probes"))


def census(job):
    label, path, number, secret = job
    import pypdfium2 as pdfium
    import pypdfium2.raw as raw
    try:
        doc = pdfium.PdfDocument(path)
        page = doc[number - 1]
        tp = page.get_textpage()
        n = raw.FPDFText_CountChars(tp.raw)
        slanted, angles, total = [], [], 0
        for i in range(n):
            code = raw.FPDFText_GetUnicode(tp.raw, i)
            if code <= 32 or raw.FPDFText_IsGenerated(tp.raw, i) == 1:
                continue
            total += 1
            a = math.degrees(raw.FPDFText_GetCharAngle(tp.raw, i)) % 90.0
            if 10.0 <= a <= 80.0:
                slanted.append(chr(code))
                angles.append(round(math.degrees(raw.FPDFText_GetCharAngle(tp.raw, i))))
                size = raw.FPDFText_GetFontSize(tp.raw, i)
        if not slanted:
            return []
        return [{"page": label, "held_out": secret, "slanted": len(slanted), "of": total, "size": round(size, 1),
                 "angles": sorted(set(angles))[:6], "text": "(held out)" if secret else "".join(slanted)[:70]}]
    except Exception as exc:
        return [{"page": label, "error": repr(exc)[:100]}]


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
    rows = [r for r in rows if "slanted" in r]
    print("pages with slanted characters: %d (held-out pages, counted only: %d); characters %d; errors %d"
          % (len(rows), sum(1 for r in rows if r["held_out"]), sum(r["slanted"] for r in rows), len(errors)))
    for r in sorted((r for r in rows if not r["held_out"]), key=lambda r: -r["slanted"]):
        print("   %-46s %4d of %5d, last size %5.1f, angles %s: %s" % (r["page"][-46:], r["slanted"], r["of"], r["size"], r["angles"], r["text"]))
