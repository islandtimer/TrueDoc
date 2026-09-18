"""A Key Facts Sheet's answer lines, span by span: can typography tell a label from the answer run on after it?

Honey's landlord building sheet sets "Accidental Breakage" 4.7pt before its "Yes", and the text layer runs the two
into one line. For every text line on the sheet that holds a Yes / No / Optional word this prints each span's text,
font, size, fill colour, flags and x-extent, and the gaps between the line's words, so the label's typography can be
set beside the answer's on the tight row and on the rows that already divide. On that sheet both sides share one face,
size, colour and set of flags, and the "Yes" starts at x 117.1, where the other answers start: the signal is geometry.
Reads the owner's PDS library through PyMuPDF (the `bench` extra).

usage (repo root): label_spans.py [file name fragment]      default: landlord-building-KFSLLBLD
"""
import glob
import os
import re
import sys

import pymupdf

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import doc_library  # noqa: E402
LIB = doc_library.root()
FRAGMENT = sys.argv[1] if len(sys.argv) > 1 else "landlord-building-KFSLLBLD"
ANSWER = re.compile("^(Yes|No|Optional)$")


def main() -> None:
    paths = [p for p in glob.glob(os.path.join(LIB, "**", "*.pdf"), recursive=True) if FRAGMENT in os.path.basename(p)]
    print(len(paths), "file(s):", [os.path.basename(p) for p in paths])
    for path in paths[:1]:
        doc = pymupdf.open(path)
        for pno, page in enumerate(doc):
            words = page.get_text("words")
            for block in page.get_text("dict")["blocks"]:
                for line in block.get("lines", []):
                    spans = line["spans"]
                    text = "".join(s["text"] for s in spans)
                    if not any(ANSWER.match(w) for w in text.split()):
                        continue
                    x0, y0, x1, y1 = line["bbox"]
                    print(f"p{pno + 1} line y={y0:.1f}-{y1:.1f} x={x0:.1f}-{x1:.1f}: {text!r}")
                    for s in spans:
                        sx0, _, sx1, _ = s["bbox"]
                        print(f"    span x={sx0:.1f}-{sx1:.1f} font={s['font']} size={s['size']:.2f} "
                              f"colour={s['color']:06x} flags={s['flags']}: {s['text']!r}")
                    on_line = sorted((w for w in words if abs((w[1] + w[3]) / 2 - (y0 + y1) / 2) < 2
                                      and w[0] >= x0 - 1 and w[2] <= x1 + 1), key=lambda w: w[0])
                    gaps = [f"{b[0] - a[2]:.1f}" for a, b in zip(on_line, on_line[1:])]
                    print("    words:", [w[4] for w in on_line], "gaps:", gaps)


if __name__ == "__main__":
    main()
