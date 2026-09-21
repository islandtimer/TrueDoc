"""What TrueDoc writes for each frequent symbol-font code of the library: one tuned-on example page per code.

Reads `dingbat_census.py`'s output. For each code set at least N times with a tuned-on example, the example page is read
twice: PyMuPDF's raw characters give the positions of that font's characters at that code; TrueDoc's text layer (no
layout model, tables or maths: the glyph reader works in the text layer) gives what it made of the characters at those
positions. Prints, per code: what TrueDoc wrote there and two of its lines, and saves a crop of the page around the
first one to look at. Held-out documents are never examples (the census names none).

usage (repo root, the project's venv):
    dingbat_readings.py <census.json> <crops dir> [min chars, default 100]
"""
import collections
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "bench", "tools"))
sys.path.insert(0, os.path.join(REPO, "bench", "probes"))
import pymupdf
import doc_library
from dingbat_census import family
from truedoc.pipeline import ConvertOptions, load_document

census, crops = sys.argv[1], sys.argv[2]
least = int(sys.argv[3]) if len(sys.argv) > 3 else 100
os.makedirs(crops, exist_ok=True)
rows = [r for r in json.load(open(census, encoding="utf-8"))["rows"] if r["example"] and r["chars"] >= least]
cache = {}
for r in rows:
    rel, number = r["example"]
    path = doc_library.absolute(rel)
    pdf = pymupdf.open(path)
    page = pdf[number - 1]
    spots = []
    for block in page.get_text("rawdict")["blocks"]:
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                if family(span.get("font", "")) != r["family"]:
                    continue
                for ch in span.get("chars", []):
                    cp = ord(ch["c"][0]) if ch["c"] else -1
                    if (cp - 0xF000 if 0xF000 <= cp <= 0xF0FF else cp) == r["code"]:
                        spots.append(pymupdf.Rect(ch["bbox"]))
    if not spots:
        continue
    key = (path, number)
    if key not in cache:
        cache[key] = load_document(path, ConvertOptions(frontmatter=False, pages=[number], layout=False, tables=False, math=False))
    doc = cache[key]
    wrote, lines = collections.Counter(), []
    for line in doc.pages[0].lines:
        for w in line.words:
            for c in w.chars:
                if family(c.font) != r["family"]:
                    continue
                cb = pymupdf.Rect(c.bbox.x0, c.bbox.y0, c.bbox.x1, c.bbox.y1)
                if any(abs(cb.x0 - s.x0) < 1.0 and abs((cb.y0 + cb.y1) / 2 - (s.y0 + s.y1) / 2) < 3.0 for s in spots):
                    wrote[c.text] += 1
                    if len(lines) < 2 and line.text not in lines:
                        lines.append(line.text)
    s = spots[0]
    clip = pymupdf.Rect(s.x0 - 12, s.y0 - 14, min(page.rect.x1, s.x0 + 200), s.y1 + 14)
    name = "%s_%04X.png" % (r["family"], r["code"])
    page.get_pixmap(dpi=200, clip=clip).save(os.path.join(crops, name))
    print("%-11s 0x%04X %6d chars, %3d docs: TrueDoc wrote %s" % (r["family"], r["code"], r["chars"], r["tuned_docs"] + r["held_docs"],
          dict(wrote.most_common(4)) or "(nothing at those positions)"))
    for l in lines:
        print("              %r" % l[:100])
    print("              crop %s  (%s p%d)" % (name, rel[-60:], number))
