"""Small pictorial marks that carry meaning.

A benefits table says which cover a line applies to with a tick under "Your
home" and a cross under "Your contents"; a checklist puts a filled circle in
front of each done item. Those marks are drawn as vector paths or tiny images,
not as text, so a text-only reading loses them. This module finds such marks,
works out what each one is by rendering it and comparing the ink with a few
templates (and its colour), and hands back a character a reader understands:
✓, ✗, ●, ○, ■, □. Marks it cannot read are still reported, as "unknown", so
the caller can keep a placeholder rather than drop them silently.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import pymupdf

from truedoc.model import BBox, Page

MARK_TEXT = {"tick": "✓", "cross": "✗", "dot": "●", "circle": "○", "square": "■", "box": "□",
             "arrow-down": "↓", "arrow-up": "↑", "arrow-right": "→", "arrow-left": "←",
             "unknown": "[icon]"}

_GRID = 32          # template resolution (cells per side)
_MIN_PT = 3.0       # smallest mark side, in points
_MAX_PT = 30.0      # largest mark side, in points on a letter-sized page
_LETTER_PT = 792.0  # the long side of a letter page: the size the limits above assume


@dataclass
class Mark:
    bbox: BBox
    kind: str          # tick, cross, dot, circle, square, box, unknown
    score: float
    colour: str = ""   # green, red, other

    @property
    def text(self) -> str:
        return MARK_TEXT.get(self.kind, MARK_TEXT["unknown"])


def find_marks(pdf_page: "pymupdf.Page", page: Page, M=None) -> list[Mark]:
    """Marks on the page, in no particular order."""
    marks: list[Mark] = []
    for box in _candidates(pdf_page, page, M):
        mark = classify_mark(pdf_page, box, M)
        if mark is not None:
            marks.append(mark)
    return marks


# ---------------------------------------------------------------- candidates

def _rect(r, M) -> BBox:
    rect = pymupdf.Rect(r)
    if M is not None:
        rect = rect * M
    rect.normalize()
    return BBox(float(rect.x0), float(rect.y0), float(rect.x1), float(rect.y1))


def _page_scale(page: Page) -> float:
    """How much larger than a letter page this one is.

    A mark is small relative to its page, not in absolute points. Slide-shaped and poster-sized
    pages draw everything larger: the owner's Huddle Black policy is laid out at 1920 x 1080 and
    marks its benefit table with 40-point ticks, which an absolute 30-point ceiling rejected, so
    the table came out with every coverage cell empty. Only pages bigger than a letter page
    scale; smaller ones keep the absolute floor, because a mark still has to be drawable.
    """
    side = max(page.width or 0.0, page.height or 0.0)
    return max(1.0, side / _LETTER_PT)


def _small(b: BBox, scale: float = 1.0) -> bool:
    if b.width < _MIN_PT * scale or b.height < _MIN_PT * scale:
        return False
    if b.width > _MAX_PT * scale or b.height > _MAX_PT * scale:
        return False
    aspect = b.width / max(b.height, 0.1)
    return 0.4 <= aspect <= 2.5


def _candidates(pdf_page: "pymupdf.Page", page: Page, M) -> list[BBox]:
    scale = _page_scale(page)
    boxes: list[BBox] = []
    try:
        for p in pdf_page.get_drawings():
            rect = p.get("rect")
            if rect is None:
                continue
            b = _rect(rect, M)
            # A stroke or fill so faint it is white on white is not a mark.
            if p.get("fill") is None and p.get("color") is None:
                continue
            if _small(b, scale):
                boxes.append(b)
    except Exception:
        pass
    try:
        for info in pdf_page.get_image_info():
            b = _rect(info["bbox"], M)
            if _small(b, scale):
                boxes.append(b)
    except Exception:
        pass
    if not boxes:
        return []
    # A ring drawn around a tick is a second path with a nested box: merge
    # overlapping or nested candidates into one.
    boxes.sort(key=lambda b: (b.y0, b.x0))
    merged: list[BBox] = []
    for b in boxes:
        for i, m in enumerate(merged):
            if b.x0 < m.x1 + 1 and b.x1 > m.x0 - 1 and b.y0 < m.y1 + 1 and b.y1 > m.y0 - 1:
                merged[i] = m.union(b)
                break
        else:
            merged.append(b)
    # Marks stand apart from text: a glyph box overlapping the candidate rules it out
    # (an underline or a box around a word is a drawing, not a mark).
    out: list[BBox] = []
    for b in merged:
        if not _small(b, scale):
            continue
        if any(c.bbox.overlap_fraction(b) > 0.3 for c in page.chars if not c.text.isspace() and c.bbox.y1 > b.y0 and c.bbox.y0 < b.y1):
            continue
        out.append(b)
    return out


# ------------------------------------------------------------- classification

def classify_mark(pdf_page: "pymupdf.Page", box: BBox, M=None) -> Mark | None:
    """Render the box and say what is drawn in it."""
    mask, colour = _ink(pdf_page, box, M)
    if mask is None:
        return None
    n = len(mask)
    filled = sum(sum(row) for row in mask)
    if filled < 0.02 * n * n:
        return None
    # A solid shape with something cut out of it: the meaning is the hole, not the ink. The
    # owner's Huddle Black policy marks cover with a white tick knocked out of a solid green
    # disc and no cover with a white cross in a red one; read as ink both are discs, so both
    # columns said the same thing, which tells a reader everything is covered. This runs before
    # the ring test on purpose: a solid disc has ink all the way round, so it reads as a ring,
    # and erasing that ring throws away the very shape that carries the meaning. Only a hole
    # that reads as a tick or a cross is taken (that is what is drawn this way), and only from
    # a shape solid enough to be a background - a true ring is too thin to qualify.
    if filled >= 0.45 * n * n:
        hole = _knockout(mask)
        if sum(sum(row) for row in hole) >= 0.03 * n * n:
            kind, score = _best_template(hole)
            if kind in ("tick", "cross") or (kind or "").startswith("arrow-"):
                return Mark(bbox=box, kind=kind, score=score, colour=colour)
    ring = _has_ring(mask)
    if ring:
        core = _erase_ring(mask)
        core_filled = sum(sum(row) for row in core)
        if core_filled < 0.03 * n * n:
            return Mark(bbox=box, kind="circle", score=0.9, colour=colour)
        mask = core
    kind, score = _best_template(mask)
    if kind is None:
        return Mark(bbox=box, kind="unknown", score=0.0, colour=colour)
    return Mark(bbox=box, kind=kind, score=score, colour=colour)


def _knockout(mask):
    """The shape cut out of a solid blob: pixels with ink on both sides of them, and above
    and below. A crescent of background at the edge of a disc has ink on one side only, so it
    does not count; a tick painted in white through the middle of the disc does."""
    n = len(mask)
    out = [[0] * n for _ in range(n)]
    for y in range(n):
        row = mask[y]
        xs = [x for x in range(n) if row[x]]
        if len(xs) < 2:
            continue
        for x in range(xs[0] + 1, xs[-1]):
            if not row[x]:
                out[y][x] = 1
    for x in range(n):
        ys = [y for y in range(n) if mask[y][x]]
        lo, hi = (ys[0], ys[-1]) if len(ys) >= 2 else (n, -1)
        for y in range(n):
            if y <= lo or y >= hi:
                out[y][x] = 0
    return out


def _ink(pdf_page, box: BBox, M=None):
    """A square boolean grid of "ink" pixels inside the box, and the ink colour.

    `box` is in the rendered page's own space and is used as it stands. `get_pixmap` clips in that
    same space, so turning the box back into the unrotated one - which is right for text, and was
    being done here - photographed the wrong patch of a rotated page and read its marks from it.
    `M` is accepted and ignored, so callers need not care.
    """
    rect = pymupdf.Rect(box.x0, box.y0, box.x1, box.y1)
    rect.normalize()
    pad = 0.08 * max(rect.width, rect.height)
    rect = pymupdf.Rect(rect.x0 - pad, rect.y0 - pad, rect.x1 + pad, rect.y1 + pad)
    zoom = _GRID / max(rect.width, rect.height, 1.0)
    try:
        pix = pdf_page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), clip=rect, alpha=False, colorspace=pymupdf.csRGB)
    except Exception:
        return None, ""
    w, h, s = pix.width, pix.height, pix.samples
    if w < 4 or h < 4:
        return None, ""
    px = [[(s[(y * w + x) * 3], s[(y * w + x) * 3 + 1], s[(y * w + x) * 3 + 2]) for x in range(w)] for y in range(h)]
    border = [px[0][x] for x in range(w)] + [px[h - 1][x] for x in range(w)] + [px[y][0] for y in range(h)] + [px[y][w - 1] for y in range(h)]
    bg = tuple(sorted(c[i] for c in border)[len(border) // 2] for i in range(3))
    ink_px = []
    n = _GRID
    mask = [[0] * n for _ in range(n)]
    for y in range(h):
        for x in range(w):
            r, g, b = px[y][x]
            if abs(r - bg[0]) + abs(g - bg[1]) + abs(b - bg[2]) > 120:
                gy = min(n - 1, int(y * n / h))
                gx = min(n - 1, int(x * n / w))
                mask[gy][gx] = 1
                ink_px.append((r, g, b))
    if not ink_px:
        return mask, ""
    r = sum(p[0] for p in ink_px) / len(ink_px)
    g = sum(p[1] for p in ink_px) / len(ink_px)
    b = sum(p[2] for p in ink_px) / len(ink_px)
    if g > r + 40 and g > b + 20:
        colour = "green"
    elif r > g + 50 and r > b + 50:
        colour = "red"
    else:
        colour = "other"
    return mask, colour


def _has_ring(mask) -> bool:
    n = len(mask)
    cx = cy = (n - 1) / 2.0
    R = n / 2.0
    bins = [0] * 24
    for y in range(n):
        for x in range(n):
            if not mask[y][x]:
                continue
            d = math.hypot(x - cx, y - cy)
            if 0.76 * R <= d <= 1.02 * R:
                a = math.atan2(y - cy, x - cx)
                bins[int((a + math.pi) / (2 * math.pi) * 24) % 24] = 1
    return sum(bins) >= 18


def _erase_ring(mask):
    n = len(mask)
    cx = cy = (n - 1) / 2.0
    R = n / 2.0
    out = [[0] * n for _ in range(n)]
    for y in range(n):
        for x in range(n):
            if mask[y][x] and math.hypot(x - cx, y - cy) < 0.64 * R:
                out[y][x] = 1
    return out


def _tight(mask):
    """Re-sample the ink to fill the grid, so templates compare shapes, not sizes."""
    n = len(mask)
    ys = [y for y in range(n) if any(mask[y])]
    xs = [x for x in range(n) if any(mask[y][x] for y in range(n))]
    if not ys or not xs:
        return mask
    y0, y1, x0, x1 = ys[0], ys[-1], xs[0], xs[-1]
    h, w = y1 - y0 + 1, x1 - x0 + 1
    side = max(h, w)
    # Keep the aspect ratio: centre the ink in a square before scaling.
    oy = (side - h) // 2
    ox = (side - w) // 2
    out = [[0] * n for _ in range(n)]
    for y in range(n):
        for x in range(n):
            sy = y0 + int(y * side / n) - oy
            sx = x0 + int(x * side / n) - ox
            if y0 <= sy <= y1 and x0 <= sx <= x1 and mask[sy][sx]:
                out[y][x] = 1
    return out


def _template(kind: str):
    n = _GRID
    t = [[0] * n for _ in range(n)]

    def seg(ax, ay, bx, by, thick):
        for y in range(n):
            for x in range(n):
                px, py = (x + 0.5) / n, (y + 0.5) / n
                vx, vy = bx - ax, by - ay
                L2 = vx * vx + vy * vy or 1e-9
                u = max(0.0, min(1.0, ((px - ax) * vx + (py - ay) * vy) / L2))
                d = math.hypot(px - (ax + u * vx), py - (ay + u * vy))
                if d <= thick:
                    t[y][x] = 1

    if kind == "tick":
        seg(0.05, 0.55, 0.38, 0.92, 0.10)
        seg(0.38, 0.92, 0.97, 0.08, 0.10)
    elif kind == "cross":
        seg(0.08, 0.08, 0.92, 0.92, 0.10)
        seg(0.08, 0.92, 0.92, 0.08, 0.10)
    elif kind == "dot":
        for y in range(n):
            for x in range(n):
                if math.hypot((x + 0.5) / n - 0.5, (y + 0.5) / n - 0.5) <= 0.48:
                    t[y][x] = 1
    elif kind == "square":
        for y in range(n):
            for x in range(n):
                if 0.06 <= (x + 0.5) / n <= 0.94 and 0.06 <= (y + 0.5) / n <= 0.94:
                    t[y][x] = 1
    elif kind == "box":
        for y in range(n):
            for x in range(n):
                px, py = (x + 0.5) / n, (y + 0.5) / n
                inside = 0.06 <= px <= 0.94 and 0.06 <= py <= 0.94
                inner = 0.22 <= px <= 0.78 and 0.22 <= py <= 0.78
                if inside and not inner:
                    t[y][x] = 1
    return t


_TEMPLATES = {k: _template(k) for k in ("tick", "cross", "dot", "square", "box")}


def _features(mask) -> dict:
    """Where the ink lies: quarter shares, the share within a band along the
    two diagonals, the share near the axes, and the fill."""
    n = len(mask)
    total = sum(sum(r) for r in mask) or 1
    cx = cy = (n - 1) / 2.0
    w = n / 6.0
    q = {"ul": 0, "ur": 0, "ll": 0, "lr": 0}
    diag = axis = 0
    for y in range(n):
        for x in range(n):
            if not mask[y][x]:
                continue
            q[("u" if y < n // 2 else "l") + ("l" if x < n // 2 else "r")] += 1
            if abs(x - y) <= w or abs(x + y - (n - 1)) <= w:
                diag += 1
            a = abs(math.degrees(math.atan2(y - cy, x - cx))) % 90.0
            if a < 22.5 or a > 67.5:
                axis += 1
    return {
        "total": total,
        "fill": total / float(n * n),
        "ul": q["ul"] / total, "ur": q["ur"] / total, "ll": q["ll"] / total, "lr": q["lr"] / total,
        "diag": diag / total,
        "axis": axis / total,
    }


def _drop_specks(mask, min_share: float = 0.06):
    """Remove small islands of ink (what is left of a ring after erasing it)."""
    n = len(mask)
    seen = [[False] * n for _ in range(n)]
    total = sum(sum(r) for r in mask) or 1
    out = [[0] * n for _ in range(n)]
    for y0 in range(n):
        for x0 in range(n):
            if not mask[y0][x0] or seen[y0][x0]:
                continue
            stack, blob = [(y0, x0)], []
            seen[y0][x0] = True
            while stack:
                y, x = stack.pop()
                blob.append((y, x))
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < n and 0 <= xx < n and mask[yy][xx] and not seen[yy][xx]:
                        seen[yy][xx] = True
                        stack.append((yy, xx))
            if len(blob) >= min_share * total:
                for y, x in blob:
                    out[y][x] = 1
    return out


def _chevron(mask):
    """An arrow head, or None.

    Two arms meeting at a point. Told apart from a cross by the corners: an X puts ink in all
    four, a chevron only in the two its arms open towards, and its point lands on the middle of
    the opposite edge. Insurance documents chain statements down a page with these, where the
    arrow is carrying the word "then".
    """
    n = len(mask)
    ys = [y for y in range(n) if any(mask[y])]
    xs = [x for x in range(n) if any(mask[y][x] for y in range(n))]
    if not ys or not xs:
        return None
    y0, y1, x0, x1 = ys[0], ys[-1], xs[0], xs[-1]
    h, w = y1 - y0 + 1, x1 - x0 + 1
    if h < 4 or w < 4:
        return None
    # Patches are taken from the ink's own box, not the grid: the grid keeps the aspect ratio, so
    # a chevron wider than it is tall sits letterboxed and every grid corner reads empty.
    qh, qw = max(2, h // 4), max(2, w // 4)

    def patch(px, py):
        """Fraction of ink in a quarter-sized patch at (px, py) of the ink box, each 0..1."""
        sx = x0 + int(px * (w - qw))
        sy = y0 + int(py * (h - qh))
        cells = [mask[y][x] for y in range(sy, min(n, sy + qh)) for x in range(sx, min(n, sx + qw))]
        return sum(cells) / max(len(cells), 1)

    tl, tr, bl, br = patch(0, 0), patch(1, 0), patch(0, 1), patch(1, 1)
    top, bottom = patch(0.5, 0), patch(0.5, 1)
    left, right = patch(0, 0.5), patch(1, 0.5)
    # kind -> (the two corners the arms reach, the two they must not, the point)
    shapes = {
        "arrow-down": (tl, tr, bl, br, bottom),
        "arrow-up": (bl, br, tl, tr, top),
        "arrow-right": (tl, bl, tr, br, right),
        "arrow-left": (tr, br, tl, bl, left),
    }
    for kind, (a, b, empty1, empty2, point) in shapes.items():
        if a >= 0.25 and b >= 0.25 and empty1 <= 0.06 and empty2 <= 0.06 and point >= 0.25:
            return kind, round(min(a, b, point), 2)
    return None


def _best_template(mask):
    """Say what shape the ink is.

    Ticks and crosses are told by where their ink lies (a tick leaves the
    upper-left quarter empty and runs from lower-left to upper-right; a cross
    fills all four quarters along the diagonals), which holds for any stroke
    weight or font. Discs, squares and boxes are matched against templates
    with checks that a glyph in a ring ("$") cannot pass.
    """
    mask = _tight(_drop_specks(mask))
    n = len(mask)
    f = _features(mask)
    total = f["total"]
    fill = f["fill"]
    ul, ur, ll, lr = f["ul"], f["ur"], f["ll"], f["lr"]
    thin = fill < 0.5
    # A tick: (almost) nothing upper-left, the long arm upper-right, the short
    # arm lower-left. What is left of a ring adds a little ink everywhere.
    if thin and ul < 0.12 and ur >= 0.25 and ll >= 0.12 and lr <= 0.35 and ll + ur >= 0.6:
        return "tick", round(1.0 - ul - max(0.0, lr - 0.1), 2)
    # An arrow head, before the cross test because the two are easily confused: both are two
    # strokes crossing the middle. The difference is at the corners - an X reaches all four, a
    # chevron reaches only the two it opens away from, and its point sits on the opposite edge.
    arrow = _chevron(mask)
    if arrow is not None:
        return arrow
    # A cross: ink in all four quarters, lying along the two diagonals (a disc
    # has about half its ink there, a fat cross nearly all of it).
    if min(ul, ur, ll, lr) >= 0.12 and f["diag"] >= 0.75 and fill < 0.8:
        return "cross", round(f["diag"], 2)
    scores = {}
    for kind, t in _TEMPLATES.items():
        if kind in ("tick", "cross"):
            continue
        inter = union = 0
        for y in range(n):
            for x in range(n):
                a, b = mask[y][x], t[y][x]
                inter += a & b
                union += a | b
        scores[kind] = inter / union if union else 0.0
    band = sum(mask[y][x] for y in range(n) for x in range(n) if min(x, y, n - 1 - x, n - 1 - y) < n // 4)
    for kind, score in sorted(scores.items(), key=lambda kv: -kv[1]):
        if score < 0.30:
            break
        if kind == "dot" and (fill < 0.55 or f["diag"] > 0.72):
            continue                            # a glyph in a ring ("$"), or a fat cross
        if kind == "square" and fill < 0.65:
            continue
        if kind == "box" and band < 0.85 * total:
            continue                            # ink inside the frame: a pictogram
        return kind, score
    return None, max(scores.values(), default=0.0)
