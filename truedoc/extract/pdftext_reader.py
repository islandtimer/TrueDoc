"""Read a page's characters and lines through pdftext (Apache-2.0) over PDFium (D007, M18).

PyMuPDF is AGPL or a paid Artifex licence, and D007 keeps AGPL out of the product path. PDFium is
BSD and reads the same characters in the same places - measured 9 September over 216 benchmark
pages: reading order agrees at 0.998 median, horizontal boxes to 0.000 pt, vertical to 0.527 pt.
What PDFium does not give is the grouping: PyMuPDF's rawdict hands back characters already sorted
into blocks, lines and spans, and that is a service TrueDoc has been receiving free.

Rather than rebuild that, this uses pdftext, which does it over PDFium already and is Apache-2.0.
`keep_chars=True` returns every character's own box, which the formula rebuild needs - our arXiv
score is built on per-glyph positions, so a reader that returns only spans would trade the best
category for a licence fix.

**Worth knowing before trusting any comparison with PyMuPDF's lines.** Three independent
implementations were measured against them - a hand-written grouper (0.49 of lines exact),
pdftext (0.48) and pdfminer.six (0.75). Three serious tools disagree with PyMuPDF and with each
other, and pdftext is what Marker uses to score 76.0 on this same benchmark. So PyMuPDF's
segmentation is one valid answer among several, not a gold standard, and agreement with it does
not measure quality. Only a scored run does.

Nothing here is wired into the converter: `extract_page` still reads through PyMuPDF. This exists
so the two can be run against each other on the benchmark.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ReadChar:
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    font: str
    size: float
    weight: int
    flags: int = 0


@dataclass
class ReadLine:
    """One line, with its characters kept: TrueDoc rebuilds words itself from character boxes."""
    chars: list[ReadChar] = field(default_factory=list)
    x0: float = 0.0
    y0: float = 0.0
    x1: float = 0.0
    y1: float = 0.0

    @property
    def text(self) -> str:
        return "".join(c.text for c in self.chars)


def available() -> bool:
    try:
        import pdftext.extraction  # noqa: F401
    except Exception:
        return False
    return True


def read_page(path: str, page_index: int) -> list[ReadLine]:
    """Lines for one page, each carrying its own characters.

    pdftext reports boxes already in top-left coordinates against the page box, which is what the
    rest of TrueDoc assumes, so nothing is flipped here (unlike the raw PDFium reader, where PDF
    space has to be turned upside down).
    """
    from pdftext.extraction import dictionary_output

    pages = dictionary_output(path, page_range=[page_index], keep_chars=True)
    out: list[ReadLine] = []
    for page in pages:
        for block in page.get("blocks", []) or []:
            for line in block.get("lines", []) or []:
                chars: list[ReadChar] = []
                for span in line.get("spans", []) or []:
                    font = span.get("font", {}) or {}
                    name = str(font.get("name") or "")
                    weight = int(font.get("weight") or 0)
                    flags = int(font.get("flags") or 0)
                    size = float(span.get("font", {}).get("size") or 0.0) if isinstance(span.get("font"), dict) else 0.0
                    for ch in span.get("chars", []) or []:
                        b = ch.get("bbox") or [0.0, 0.0, 0.0, 0.0]
                        chars.append(ReadChar(
                            text=str(ch.get("char", "")),
                            x0=float(b[0]), y0=float(b[1]), x1=float(b[2]), y1=float(b[3]),
                            font=name, size=size or _height(b), weight=weight, flags=flags,
                        ))
                if not chars:
                    continue
                lb = line.get("bbox") or [
                    min(c.x0 for c in chars), min(c.y0 for c in chars),
                    max(c.x1 for c in chars), max(c.y1 for c in chars)]
                out.append(ReadLine(chars=chars, x0=float(lb[0]), y0=float(lb[1]),
                                    x1=float(lb[2]), y1=float(lb[3])))
    return out


def _height(bbox) -> float:
    try:
        return float(bbox[3]) - float(bbox[1])
    except Exception:
        return 0.0
