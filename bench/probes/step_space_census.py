"""Does the file itself mark the space beside a Key Facts Sheet's big step number? Tuned-on sheets only.

Written to answer whether the 16 September 2026 note - "spaces lost in the text layer" - was right. For every digit set
at 30 points or more on the sheets' pages, as PDFium's text layer holds it, on each side: is there a space the file
holds, one PDFium generated for the gap, or none - and if none, a clear gap (over 13% of the smaller size, or 0.9
point) or boxes that touch? On 21 September: beside about three step numbers in five the space is there to be read,
beside the rest the boxes touch though the page shows a clear space.

usage (repo root, the project's venv):
    step_space_census.py
"""
import collections
import ctypes
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "bench", "probes"))
sys.path.insert(0, os.path.join(REPO, "bench", "tools"))
import pypdfium2 as pdfium
import pypdfium2.raw as raw
from orphan_row_census import jobs


def box(tp, i):
    l, b, r, t = (ctypes.c_double() for _ in range(4))
    raw.FPDFText_GetCharBox(tp, i, l, r, b, t)
    return l.value, r.value


def side(tp, n, i, step):
    """What stands between char i and the next glyph in direction `step`: 'space' (held by the file), 'generated'
    (PDFium's own), or 'none' - with the gap in points to that glyph's box, and its size."""
    j, held, generated = i + step, False, False
    while 0 <= j < n:
        ch = raw.FPDFText_GetUnicode(tp, j)
        if ch in (0x20, 0xA0):
            if raw.FPDFText_IsGenerated(tp, j) == 1:
                generated = True
            else:
                held = True
            j += step
            continue
        if ch in (0x0D, 0x0A, 0x02):
            return "line end", None, None
        break
    if not 0 <= j < n:
        return "edge", None, None
    (l0, r0), (l1, r1) = box(tp, i), box(tp, j)
    gap = (l1 - r0) if step > 0 else (l0 - r1)
    return ("space" if held else "generated" if generated else "none"), gap, raw.FPDFText_GetFontSize(tp, j)


if __name__ == "__main__":
    tally = collections.Counter()
    sheets = set()
    for label, path, number, secret in jobs("kfs"):
        if secret:                       # the oracle's held-out fifth is not opened
            continue
        sheets.add(path)
        doc = pdfium.PdfDocument(path)
        page = doc[number - 1]
        textpage = page.get_textpage()
        tp = textpage.raw
        n = raw.FPDFText_CountChars(tp)
        for i in range(n):
            big = raw.FPDFText_GetFontSize(tp, i)
            if not 0x30 <= raw.FPDFText_GetUnicode(tp, i) <= 0x39 or big < 30:
                continue
            for name, step in (("before", -1), ("after", 1)):
                kind, gap, size = side(tp, n, i, step)
                if kind in ("line end", "edge"):
                    tally[(name, kind)] += 1
                elif kind != "none":
                    tally[(name, "the file holds a space" if kind == "space" else "PDFium generated a space")] += 1
                elif gap > max(0.13 * min(size, big), 0.9):
                    tally[(name, "no space, a clear gap")] += 1
                else:
                    tally[(name, "no space, boxes touch or nearly")] += 1
        textpage.close()
        page.close()
        doc.close()
    print("tuned-on sheets:", len(sheets))
    for name in ("before", "after"):
        print("  %s the step number:" % name)
        for (k, what), v in sorted(tally.items(), key=lambda kv: -kv[1]):
            if k == name:
                print("     %4d  %s" % (v, what))
