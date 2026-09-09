"""Hand `extract_page` the same shape PyMuPDF's rawdict has, built through PDFium (D007, M18).

PyMuPDF is AGPL or a paid Artifex licence and D007 keeps AGPL out of the product path. Everything
`extract_page` needs from PyMuPDF arrives as one `rawdict` structure - blocks, lines, spans, and a
box and origin per character - so the least invasive way to read through PDFium instead is to
rebuild that structure rather than rewrite the stage that consumes it. pdftext (Apache-2.0) does
the line and span grouping over PDFium, which is the one part PDFium itself does not provide.

Measured before this was written, on one arXiv page: identical non-space character count (1,896),
the same font names and sizes, boxes agreeing with PyMuPDF to under a point, and top-left
coordinates already, so nothing is flipped.

**Two approximations, both deliberate and both visible in the output.**

* **Origin.** PyMuPDF reports each glyph's origin - the point on the baseline where it is drawn.
  pdftext does not, so the baseline is estimated from the metric box as `y1 - 0.21 * size`, the
  usual descender share of a font's box. It is a constant offset within a span, so anything
  comparing characters to each other (line grouping, script detection) is unaffected; anything
  reading an absolute baseline is off by a fraction of a point.
* **Colour.** pdftext does not report a fill colour per span, so colour comes back 0 (black).
  TrueDoc uses it for the hidden-text rules (D011), which therefore cannot fire on this path.

Switched on with the environment variable `TRUEDOC_READER=pdftext`, and off by default. That is
deliberately a blunt switch for an experiment rather than a settled option: the question it exists
to answer is what the benchmark score does, and only a scored run can answer it.
"""
from __future__ import annotations

import os

_DESCENDER = 0.21       # share of a font's metric box that sits below the baseline


def enabled() -> bool:
    return os.environ.get("TRUEDOC_READER", "").strip().lower() == "pdftext"


def available() -> bool:
    try:
        import pdftext.extraction  # noqa: F401
    except Exception:
        return False
    return True


def build(path: str, page_number: int) -> dict | None:
    """A rawdict-shaped reading of one page (1-based), or None if pdftext cannot read it."""
    try:
        from pdftext.extraction import dictionary_output
    except Exception:
        return None
    try:
        pages = dictionary_output(path, page_range=[page_number - 1], keep_chars=True)
    except Exception:
        return None
    if not pages:
        return None
    blocks = []
    for block in pages[0].get("blocks", []) or []:
        lines = []
        for line in block.get("lines", []) or []:
            spans = []
            for span in line.get("spans", []) or []:
                font = span.get("font") or {}
                size = float(font.get("size") or 0.0)
                chars = []
                for ch in span.get("chars", []) or []:
                    b = ch.get("bbox") or [0.0, 0.0, 0.0, 0.0]
                    text = str(ch.get("char", ""))
                    if not text:
                        continue
                    y1 = float(b[3])
                    chars.append({
                        "c": text,
                        "bbox": (float(b[0]), float(b[1]), float(b[2]), y1),
                        # The baseline PyMuPDF would have reported, estimated from the metric box.
                        "origin": (float(b[0]), y1 - _DESCENDER * (size or (y1 - float(b[1])))),
                    })
                if not chars:
                    continue
                spans.append({
                    "font": str(font.get("name") or ""),
                    "size": size,
                    "flags": int(font.get("flags") or 0),
                    "color": 0,
                    "chars": chars,
                })
            if not spans:
                continue
            lines.append({"dir": (1.0, 0.0), "spans": spans})
        if lines:
            blocks.append({"type": 0, "lines": lines})
    return {"blocks": blocks}
