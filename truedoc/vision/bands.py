"""Reading a hard page in overlapping bands, and joining the readings back into one page.

Why. A model sent a whole page sees it at whatever the service's image limit allows: on the benchmark's
old scans, about 0.66 of the page's own pixels. Sent the top and bottom halves separately it sees each
at about 0.90 - a median 1.3 times more ink per letter, measured over those pages on 12 September - and
it gets a second, undistracted look at every line. Three bands buy nothing over two, because past that
the page's *width* is what the limit binds on.

The cost is one extra call a page, so this is meant for the hard tail (a page with no text layer whose
own OCR comes back with nothing word-like), not for every scan.

**Measured and not shipped (12 September).** Over the benchmark's 98 old-scan pages, two bands scored 252
of 526 checks against 280 for the same model reading each page whole - twenty-eight checks worse, not
better. Two reasons were observed rather than guessed, by printing what each band actually returned:

* The bands disagree about lines. On old_scans/1 the top band answered in the manuscript's own short
  lines and the bottom band reflowed its half into one 99-word paragraph. Nothing can weld those, so the
  welder does the safe thing and keeps both, and the shared strip is written twice.
* A band reads worse than a page, for all its extra pixels. On that same page the whole-page reading has
  "when He Lost His Legg" - Sickles lost a leg at Gettysburg - where the band, seeing only the bottom
  half, offers "when He lost his Job". Context beat resolution.

So this stays behind its switch, off, until someone has a reason to think the second problem is solvable.
The first probably is, by telling both bands to keep the document's own line breaks.

The join. Consecutive bands overlap, so the same lines are read twice and must be welded, not stacked.
`splice` looks for the longest run of lines that ends the first reading and begins the second, and drops
the duplicate; failing that it anchors on a single substantial line; failing that it keeps both, because
a reader would rather see a line twice than not at all.
"""

from __future__ import annotations

import re

# How much of its own height each band shares with its neighbour. Enough that a line cut by one band's
# edge is whole inside the next, and that the welder has several lines to match on.
OVERLAP = 0.18
BANDS = 2

# A run longer than this is not an overlap, it is the same page read twice.
_MAX_RUN = 24
_WORD = re.compile(r"[^\W_]+", re.UNICODE)


def band_boxes(width: float, height: float, count: int = BANDS, overlap: float = OVERLAP) -> list[tuple[float, float, float, float]]:
    """`count` clip boxes down the page, each sharing `overlap` of its height with the next."""
    if count < 2 or height <= 0:
        return [(0.0, 0.0, width, height)]
    # count bands of height h, each overlapping the next by overlap*h, must cover the page:
    # count*h - (count-1)*overlap*h = height
    band = height / (count - (count - 1) * overlap)
    boxes = []
    for i in range(count):
        y0 = i * band * (1.0 - overlap)
        y1 = min(height, y0 + band)
        boxes.append((0.0, max(0.0, y0), width, y1))
    boxes[-1] = (0.0, max(0.0, height - band), width, height)
    return boxes


def _key(line: str) -> str:
    """A line reduced to what two readings of it would agree on."""
    return " ".join(w.lower() for w in _WORD.findall(line))


def _same(a: str, b: str) -> bool:
    ka, kb = _key(a), _key(b)
    if not ka or not kb:
        return ka == kb
    if ka == kb:
        return True
    # One reading may have dropped or gained a word at a band's edge, so a line contained in the other
    # counts - but only if it is most of it. Without that second condition a short line matches almost
    # any long one, and on old_scans/1 a single bad match threw away the middle of the letter: the weld
    # kept the top band and then jumped to the signature (12 September).
    shorter, longer = (ka, kb) if len(ka) <= len(kb) else (kb, ka)
    return len(shorter) >= 12 and shorter in longer and len(shorter) >= 0.6 * len(longer)


def _substantial(line: str) -> bool:
    return len(_key(line).split()) >= 4


def splice(first: str, second: str) -> str:
    """Weld two band readings that share an overlap into one page reading."""
    a = [l for l in (first or "").splitlines()]
    b = [l for l in (second or "").splitlines()]
    if not a:
        return second or ""
    if not b:
        return first or ""
    # the longest run of lines that ends `a` and begins `b`
    for run in range(min(len(a), len(b), _MAX_RUN), 0, -1):
        tail = [l for l in a[-run:]]
        head = [l for l in b[:run]]
        if any(_substantial(l) for l in tail) and all(_same(x, y) for x, y in zip(tail, head)):
            return "\n".join(a + b[run:])
    # No run matched. Anchor on one of the last few lines of `a` if it appears where the shared strip
    # can plausibly reach into `b` - never further. The bands share `OVERLAP` of a band's height, so
    # the strip is about that share of `b`'s lines; welding past it means dropping text that was never
    # duplicated, which is how the middle of a letter disappears.
    reach = max(3, int(len(b) * (OVERLAP + 0.12)) + 1)
    for i in range(len(a) - 1, max(-1, len(a) - 4) - 1, -1):
        if not _substantial(a[i]):
            continue
        for j in range(min(len(b), reach)):
            if _same(a[i], b[j]):
                return "\n".join(a[: i + 1] + b[j + 1:])
        break
    # nothing matched: keep both, a line seen twice beats a line lost
    return "\n".join(a + [""] + b)


def splice_all(readings: list[str]) -> str:
    """Weld a page's bands, top to bottom."""
    out = ""
    for text in readings:
        out = text if not out else splice(out, text)
    return out
