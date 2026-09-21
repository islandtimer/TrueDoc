"""Versions of a document, matched page by page (D040).

An insurer revises a document by issuing it again: most pages are reprinted word for word under a new date or form
code, some are reworded, some added, some dropped. For what a person confirmed about one version to carry over to the
next, each page of the new version is matched with the page of the old version that it reprints, and classed:

    same        the page prints the same words, its running lines included
    restamped   the same words in its body; its running lines differ only in numbers and month names - a date, a form
                code's digits, a page number
    changed     a page of the old version reworded: the passages that differ are listed, those holding a figure first
    new         no page of the old version is like it

and a page of the old version that nothing matches is dropped. Only a page found `same` or `restamped` keeps what was
confirmed about it; a `changed` page is checked afresh, and its figures always (D040: lessons settle structure, figures
are checked every time).

What is compared is what the page prints, as PDFium reads it - not TrueDoc's conversion, which changes whenever TrueDoc
does - so a match stands however TrueDoc comes to read the page.

A running line is a line in the page's head or foot band that a page beside it prints too, numbers aside - the
definition D029 uses for running heads: "Page 3 of 64", "PDS prepared 29/07/14", a form code. A line in the band that
no page beside prints is the page's own content, part of its body. A line taken for running wrongly - a table's
heading repeated at the top of each page, say - cannot hide a change of wording: `restamped` allows the running lines
to differ in numbers and month names only; any other difference makes the page `changed`.
"""
from __future__ import annotations

import difflib
import re
import unicodedata
from dataclasses import dataclass, field

_EDGE = 0.12          # the head and foot bands, as a share of the page's height
_MATCH = 0.5          # the least likeness for two pages to be taken as versions of one page
_NUMBER = re.compile(r"\d+")
_MONTH = re.compile(r"\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|"
                    r"sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\b", re.I)


def _fold(text: str) -> str:
    """A running line with its numbers and month names taken out: what stays the same from one issue to the next."""
    return _MONTH.sub("<m>", _NUMBER.sub("#", text))


@dataclass
class PagePrint:
    """What one page prints, for matching: its body's words in reading order, and its running lines."""
    number: int                                   # 1-based
    body: list[str]
    running: list[str]

    def bigrams(self) -> set[tuple[str, str]]:
        words = self.body
        return set(zip(words, words[1:])) if len(words) > 1 else {(w, "") for w in words}


@dataclass
class PageMatch:
    new: int | None                               # the page's number in the new version; None for a dropped page
    old: int | None                               # the page it reprints in the old version; None for a new page
    kind: str                                     # same | restamped | changed | new | dropped
    likeness: float = 0.0                         # share of word pairs the two pages hold in common (Jaccard)
    figures: list[tuple[str, str]] = field(default_factory=list)   # changed passages holding a figure: (old, new)
    wording: list[tuple[str, str]] = field(default_factory=list)   # the other changed passages: (old, new)


def _lines(textpage, height: float) -> list[tuple[float, float, str]]:
    """The page's text as lines (top, left, text): PDFium's text rectangles, joined where they share a baseline."""
    rects = []
    for i in range(textpage.count_rects()):
        left, bottom, right, top = textpage.get_rect(i)
        text = textpage.get_text_bounded(left, bottom, right, top).strip()
        if text:
            rects.append((height - top, height - bottom, left, text))
    rects.sort(key=lambda r: (round(r[0], 1), r[2]))
    lines: list[list] = []
    for y0, y1, x0, text in rects:
        mid = (y0 + y1) / 2
        for line in lines:
            if line[0] <= mid <= line[1]:
                line[3].append((x0, text))
                break
        else:
            lines.append([y0, y1, x0, [(x0, text)]])
    out = []
    for y0, y1, x0, pieces in lines:
        out.append((y0, min(x for x, _ in pieces), " ".join(t for _, t in sorted(pieces))))
    return sorted(out)


def _words(text: str) -> list[str]:
    return unicodedata.normalize("NFKC", text).split()


def page_prints(path: str, pages: list[int] | None = None) -> list[PagePrint]:
    """Every page of the PDF at `path` (or those numbered in `pages`), read for matching."""
    import pypdfium2 as pdfium

    doc = pdfium.PdfDocument(path)
    try:
        numbers = pages or list(range(1, len(doc) + 1))
        read = []                                  # (number, height, lines)
        for n in numbers:
            page = doc[n - 1]
            height = page.get_height()
            textpage = page.get_textpage()
            read.append((n, height, _lines(textpage, height)))
            textpage.close()
            page.close()
    finally:
        doc.close()
    bands = []
    for n, height, lines in read:
        bands.append({_fold(text) for top, left, text in lines if top < _EDGE * height or top > (1 - _EDGE) * height})
    prints = []
    for i, (n, height, lines) in enumerate(read):
        beside = set().union(*(bands[j] for j in (i - 1, i + 1) if 0 <= j < len(bands) and read[j][0] - n in (-1, 1)))
        body, running = [], []
        for top, left, text in lines:
            edge = top < _EDGE * height or top > (1 - _EDGE) * height
            if edge and _fold(text) in beside:
                running.append(text)
            else:
                body.extend(_words(text))
        prints.append(PagePrint(number=n, body=body, running=running))
    return prints


def likeness(a: PagePrint, b: PagePrint) -> float:
    x, y = a.bigrams(), b.bigrams()
    if not x and not y:
        return 1.0
    return len(x & y) / len(x | y)


def _changes(old: list[str], new: list[str]) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    figures, wording = [], []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=old, b=new, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        pair = (" ".join(old[i1:i2]), " ".join(new[j1:j2]))
        (figures if any(ch.isdigit() for ch in pair[0] + pair[1]) else wording).append(pair)
    return figures, wording


def match(old: list[PagePrint], new: list[PagePrint]) -> list[PageMatch]:
    """Each page of `new` with the page of `old` it reprints, in order: pages are added, dropped or reworded between
    issues, not shuffled, so the pairing is the one that keeps both orders and holds the most in common. A page moved
    elsewhere comes out as dropped where it was and new where it is - checked afresh, never assumed."""
    n, m = len(old), len(new)
    like = [[likeness(o, w) for w in new] for o in old]
    best = [[0.0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            pair = like[i][j] + best[i + 1][j + 1] if like[i][j] >= _MATCH else float("-inf")
            best[i][j] = max(best[i + 1][j], best[i][j + 1], pair)
    out: list[PageMatch] = []
    i = j = 0
    while i < n or j < m:
        if i < n and j < m and like[i][j] >= _MATCH and best[i][j] == like[i][j] + best[i + 1][j + 1]:
            o, w = old[i], new[j]
            if o.body == w.body and o.running == w.running:
                kind = "same"
            elif o.body == w.body and [_fold(t) for t in o.running] == [_fold(t) for t in w.running]:
                kind = "restamped"
            else:
                kind = "changed"
            figures, wording = _changes(o.body + o.running, w.body + w.running) if kind == "changed" else ([], [])
            out.append(PageMatch(new=w.number, old=o.number, kind=kind, likeness=like[i][j], figures=figures, wording=wording))
            i, j = i + 1, j + 1
        elif j < m and (i == n or best[i][j] == best[i][j + 1]):
            out.append(PageMatch(new=new[j].number, old=None, kind="new"))
            j += 1
        else:
            out.append(PageMatch(new=None, old=old[i].number, kind="dropped"))
            i += 1
    return out
