"""Contact sheet of glyphs from given font families across the arxiv_math pages.

usage: python bench/tools/glyph_sheet.py <out.png> <font substring> [<font substring> ...] [--all]
Each cell shows one distinct (family, char): the glyph clipped from the first page that uses it,
with a little context to the left and right, labelled with the family, the char and its code.
Without --all only chars missing from truedoc's mathabx table are shown. This is how the
mathabx, mathb and mathx symbol tables in truedoc/math/symbols.py were filled by eye.
"""
import glob
import os
import sys

import pymupdf
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, REPO)
from truedoc.math.symbols import _MATHABX_RAW  # noqa: E402

B = os.path.join(REPO, "bench", "data", "olmocr-bench", "bench_data")


def main():
    out = sys.argv[1]
    fams = [a.lower() for a in sys.argv[2:] if not a.startswith("--")]
    show_all = "--all" in sys.argv
    seen = {}
    for pdf in sorted(glob.glob(os.path.join(B, "pdfs", "arxiv_math", "*.pdf"))):
        try:
            doc = pymupdf.open(pdf)
            page = doc[0]
            names = {f[3].split("+")[-1].lower() for f in page.get_fonts(full=True)}
        except Exception:
            continue
        if not any(any(fam in n for fam in fams) for n in names):
            continue
        d = page.get_text("rawdict")
        for b in d["blocks"]:
            for l in b.get("lines", []):
                for s in l["spans"]:
                    f = s["font"].lower()
                    fam = next((fam for fam in fams if fam in f), None)
                    if fam is None:
                        continue
                    for c in s["chars"]:
                        ch = c["c"]
                        if ch.isspace():
                            continue
                        if not show_all and ch in _MATHABX_RAW:
                            continue
                        key = (fam, ch)
                        if key in seen:
                            continue
                        seen[key] = (pdf, c["bbox"], s["size"])
    keys = sorted(seen, key=lambda k: (k[0], ord(k[1])))
    cell_w, cell_h = 260, 120
    cols = 4
    rows = (len(keys) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell_w, max(1, rows) * cell_h), "white")
    draw = ImageDraw.Draw(sheet)
    for i, key in enumerate(keys):
        pdf, bb, size = seen[key]
        doc = pymupdf.open(pdf)
        page = doc[0]
        x0, y0, x1, y1 = bb
        pad = 2.0 * size
        clip = pymupdf.Rect(x0 - pad, y0 - 0.5 * size, x1 + pad, y1 + 0.5 * size)
        pix = page.get_pixmap(clip=clip, dpi=150)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        scale = min((cell_w - 10) / img.width, (cell_h - 30) / img.height, 1.5)
        img = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))))
        cx = (i % cols) * cell_w
        cy = (i // cols) * cell_h
        sheet.paste(img, (cx + 5, cy + 22))
        # mark the glyph's own box (red) within the clip
        sx = img.width / pix.width
        gx0 = cx + 5 + int((x0 - clip.x0) / clip.width * pix.width * sx)
        gx1 = cx + 5 + int((x1 - clip.x0) / clip.width * pix.width * sx)
        draw.rectangle([gx0, cy + 20, gx1, cy + 22 + img.height], outline="red")
        label = "%s %r U+%04X %s" % (key[0], key[1], ord(key[1]), os.path.basename(pdf)[:14])
        draw.text((cx + 4, cy + 4), label, fill="black")
        draw.rectangle([cx, cy, cx + cell_w - 1, cy + cell_h - 1], outline="#999")
    sheet.save(out)
    print(out, len(keys), "glyphs")


if __name__ == "__main__":
    main()
