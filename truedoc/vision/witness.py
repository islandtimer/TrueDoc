"""The page's own lines as a witness for a model's reading (D019).

A vision model transcribes what it sees, running heads and feet included: an issue number, a
journal title, "Fonte: Bacen". TrueDoc's header rules work on geometry, which a model's markdown
does not have, but the page's own lines do: the hidden OCR layer where there is one, our own
engine's lines otherwise (kept even when the acceptance gate rejected them). A line of the
model's text at the head or foot of the page that matches a witness line in the same strip is
furniture and is dropped; the dropped lines are recorded so nothing goes silently.
"""

from __future__ import annotations

import difflib
import re

STRIP = 0.12            # the head and foot strips, as a fraction of the page height
_MAX_WORDS = 8          # a running head is short
_MIN_CHARS = 4
_RATIO = 0.8

_NON_ALNUM = re.compile(r"[^0-9a-zÀ-ɏͰ-ϿЀ-ӿ֐-ۿঀ-৿]+")
_PAGE_NUMBER = re.compile(r"^[\s\-–—.·|]*(?:\d{1,4}|[ivxlcIVXLC]{1,7})[\s\-–—.·|]*$")


def _norm(text: str) -> str:
    return _NON_ALNUM.sub(" ", text.casefold()).strip()


def looks_like_furniture(line: str) -> bool:
    """A running head or foot is short and set apart: all capitals, a page number, or a
    few words with a digit in a script that has no case. A sentence of body text that
    happens to sit at the page's edge (the first entry of a dictionary page, a magazine's
    price line) is not dropped on position alone; measured on the 281 model pages of
    7 September, the looser rule cost as many checks as it won."""
    text = line.strip()
    words = text.split()
    if not text or len(words) > _MAX_WORDS:
        return False
    if _PAGE_NUMBER.match(text):
        return True
    letters = [c for c in text if c.isalpha()]
    cased = [c for c in letters if c.upper() != c.lower()]
    if cased:
        return len(cased) >= 3 and all(c.isupper() for c in cased)
    return len(words) <= 4 and any(c.isdigit() for c in text)


def strip_lines(lines, height: float) -> tuple[list[str], list[str]]:
    """Split a page's lines into the texts of its head strip and foot strip."""
    top: list[str] = []
    bottom: list[str] = []
    for line in lines:
        if isinstance(line, (tuple, list)):
            text, y0, y1 = line[0], float(line[1]), float(line[2])
        else:
            text = getattr(line, "text", None)
            if text is None:
                text = " ".join(w.text for w in line.words)
            y0, y1 = line.bbox.y0, line.bbox.y1
        text = (text or "").strip()
        if not text:
            continue
        if y1 <= STRIP * height:
            top.append(text)
        elif y0 >= (1.0 - STRIP) * height:
            bottom.append(text)
    return top, bottom


def _matches(line: str, witnesses: list[str]) -> bool:
    a = _norm(line)
    if not a or len(line.split()) > _MAX_WORDS:
        return False
    for w in witnesses:
        b = _norm(w)
        if not b:
            continue
        if a == b:
            return True
        if len(a) < _MIN_CHARS or len(b) < _MIN_CHARS:
            continue    # a page number matches only exactly
        if (len(a) >= 8 and a in b) or (len(b) >= 8 and b in a):
            return True
        if difflib.SequenceMatcher(None, a, b).ratio() >= _RATIO:
            return True
    return False


def strip_running_heads(text: str, top: list[str], bottom: list[str]) -> tuple[str, list[str]]:
    """Drop the model's edge lines that the page's own head or foot strip vouches for as furniture.

    Returns the text and the dropped lines. Only the first and the last non-empty line are
    looked at, the line must look like furniture (`looks_like_furniture`), and a witness must
    sit in the same strip: a title repeated in the body is never touched.
    """
    if not text or not (top or bottom):
        return text, []
    lines = text.split("\n")
    idx = [i for i, l in enumerate(lines) if l.strip()]
    if not idx:
        return text, []
    drop: set[int] = set()
    first, last = idx[0], idx[-1]
    cand_first = lines[first].strip("# >*_ ").strip()
    if top and looks_like_furniture(cand_first) and _matches(cand_first, top):
        drop.add(first)
    cand_last = lines[last].strip("# >*_ ").strip()
    if bottom and last != first and looks_like_furniture(cand_last) and _matches(cand_last, bottom):
        drop.add(last)
    if not drop:
        return text, []
    dropped = [lines[i] for i in sorted(drop)]
    kept = [l for i, l in enumerate(lines) if i not in drop]
    out = "\n".join(kept).strip("\n")
    return out, dropped


def strip_lines_from_ocr(pdf_page, width: float, height: float, need_top: bool, need_bottom: bool) -> tuple[list[str], list[str]]:
    """Read an empty head or foot strip with our own engine, for a page whose layer leaves it
    empty (a publisher's download stamp at the foot of an otherwise bare scan). The engine
    misses text at a crop's edge, so a crop twice the strip's height is read and only the lines
    inside the strip are kept."""
    from truedoc.model import BBox
    from truedoc.ocr.rapid import ocr_region

    top: list[str] = []
    bottom: list[str] = []
    if need_top:
        lines, _, _ = ocr_region(pdf_page, BBox(0.0, 0.0, width, 2 * STRIP * height))
        top = [l.text.strip() for l in lines if l.bbox.y1 <= STRIP * height and l.text.strip()]
    if need_bottom:
        lines, _, _ = ocr_region(pdf_page, BBox(0.0, (1.0 - 2 * STRIP) * height, width, height))
        bottom = [l.text.strip() for l in lines if l.bbox.y0 >= (1.0 - STRIP) * height and l.text.strip()]
    return top, bottom
