"""Show the characters behind a glued word: sizes, boxes and gaps.

python gap_probe.py <pdf> <substring>
"""
import sys

import pymupdf

from truedoc.extract.textlayer import extract_page

pdf, needle = sys.argv[1], sys.argv[2]
doc = pymupdf.open(pdf)
page = extract_page(doc[0], 1)
print("quality:", page.quality.kind, page.quality.usable, "body size", page.body_font_size, "page", page.width, page.height)
found = 0
for line in page.lines:
    if needle in line.text.replace(" ", ""):
        found += 1
        print("LINE:", line.text[:100], "| size", round(line.size, 2))
        for w in line.words:
            if needle[:4] in w.text:
                chars = w.chars
                print("  WORD:", w.text, "font", chars[0].font, "size", round(chars[0].size, 2))
                prev = None
                for c in chars:
                    gap = round(c.bbox.x0 - prev.bbox.x1, 2) if prev else 0
                    print(f"    {c.text!r:6} x0={c.bbox.x0:7.2f} x1={c.bbox.x1:7.2f} w={c.bbox.width:5.2f} h={c.bbox.height:5.2f} size={c.size:5.2f} gap={gap}")
                    prev = c
        if found >= 2:
            break
if not found:
    print("not found; first lines:")
    for line in page.lines[:8]:
        print("  ", line.text[:100])
