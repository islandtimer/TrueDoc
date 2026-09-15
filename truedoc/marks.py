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

from truedoc.extract import pdfium_objects, render
from truedoc.geometry import Rect
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
    rect = Rect(r)
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
    objs = pdfium_objects.page_objects(pdf_page.parent.name, pdf_page.number + 1) if pdfium_objects.enabled() else None
    if objs is not None:
        for o in objs:
            if o.kind == "path" and o.fill is None and o.stroke is None:
                continue    # a path that paints nothing is not a mark
            if o.kind not in ("path", "image"):
                continue
            b = _rect(o.bbox, M)
            if _small(b, scale):
                boxes.append(b)
    else:
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

def classify_mark(pdf_page: "pymupdf.Page", box: BBox, M=None, glyph: bool = False) -> Mark | None:
    """Render the box and say what is drawn in it.

    `glyph` says the box is a font glyph's, and its mark must stand on its own there. Ink reaching the edge of the crop
    belongs to something else drawn there - Suncorp's flow arrow, a solid triangle set in ZapfDingbats with a rule under
    it, read as a cross with the rule - and a dot, a square or a box is as wide at each height as at its mirror height,
    where Apia's flow arrows, a Wingdings 3 shaft standing on a head, read as dots.
    """
    mask, colour = _ink(pdf_page, box, M)
    if mask is None:
        return None
    if glyph and (any(mask[0]) or any(mask[-1]) or any(row[0] or row[-1] for row in mask)):
        return None
    mark = _read_ink(mask, box, colour, glyph)
    if glyph and mark is not None and mark.kind in ("dot", "square", "box") and not _same_upside_down(mask):
        return None
    return mark


def _same_upside_down(mask) -> bool:
    """Whether the ink, cut to its own box, is about as wide at each height as at the height mirroring it, as a disc, a
    square and a frame are: the differences come to less than a third of all the width. Bullets set as private-use
    glyphs differ by 0.03 to 0.24 of it, Apia's block arrows by 0.41."""
    m = _tight(_drop_specks(mask))
    rows = [y for y, row in enumerate(m) if any(row)]
    if not rows:
        return True
    widths = [sum(m[y]) for y in range(rows[0], rows[-1] + 1)]
    return 3 * sum(abs(a - b) for a, b in zip(widths, reversed(widths))) < sum(widths)


def _read_ink(mask, box: BBox, colour: str, glyph: bool = False) -> Mark | None:
    """What the ink in a mark's grid is."""
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
    # a shape solid enough to be a background - a true ring is too thin to qualify. The reading is the
    # page's rather than the renderer's because the crop is drawn large and shrunk here (`_SUPER`):
    # the same grey disc reads 0.511 drawn by MuPDF and 0.505 by PDFium.
    if filled >= 0.45 * n * n:
        hole = _knockout(mask)
        cut = sum(sum(row) for row in hole)
        if cut >= 0.03 * n * n:
            kind, score = _best_template(hole)
            if kind in ("tick", "cross") or (kind or "").startswith("arrow-"):
                return Mark(bbox=box, kind=kind, score=score, colour=colour)
        elif cut >= 0.025 * n * n:
            # A thin arrow cut out of a square holds fewer cells than a tick cut out of a disc: Budget Direct's page
            # links cut 30 to 39 of the grid's 1,024, and one fell under the 3% gate. Below it only an arrow with a
            # shaft is taken - with the gate lowered for every shape, a question mark cut out of an NRMA disc read as
            # a chevron pointing down.
            arrow = _shafted_arrow(_tight(_drop_specks(hole)))
            if arrow is not None:
                return Mark(bbox=box, kind=arrow[0], score=arrow[1], colour=colour)
    ring = _has_ring(mask)
    if ring:
        core = _erase_ring(mask)
        core_filled = sum(sum(row) for row in core)
        if core_filled < 0.03 * n * n:
            return Mark(bbox=box, kind="circle", score=0.9, colour=colour)
        mask = core
    # A shafted arrow is read from the whole ink or from a shape cut out of a solid one, never from what erasing a ring
    # leaves: a bold letter touches the ring's band all round, and the middle of an "m" - a stroke with two arches
    # bending onto it - is a shaft with two arms closing on its end (CBA's "Commonwealth", Woolworths' "Home").
    kind, score = _best_template(mask, shafts=not ring, glyph=glyph)
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


_SUPER = 4          # the crop is drawn this many times larger than the grid it is read on


def _ink(pdf_page, box: BBox, M=None):
    """A square boolean grid of "ink" pixels inside the box, and the ink colour.

    `box` is in the rendered page's own space and is used as it stands. `get_pixmap` clips in that
    same space, so turning the box back into the unrotated one - which is right for text, and was
    being done here - photographed the wrong patch of a rotated page and read its marks from it.
    `M` is accepted and ignored, so callers need not care.
    """
    rect = Rect(box.x0, box.y0, box.x1, box.y1)
    rect.normalize()
    pad = 0.08 * max(rect.width, rect.height)
    rect = Rect(rect.x0 - pad, rect.y0 - pad, rect.x1 + pad, rect.y1 + pad)
    # Drawn at the grid's own size, the shape is the renderer's opinion as much as the page's: PDFium
    # keeps a stroke at least a pixel wide where MuPDF thins it, and a tick on a presentation-sized
    # page came out 0.146 of the crop under one and 0.177 under the other, which read as a tick and an
    # arrow. Drawn four times larger and shrunk to the grid here, the two agree to a thousandth
    # (0.171 and 0.172) and both read the tick.
    zoom = _SUPER * _GRID / max(rect.width, rect.height, 1.0)
    try:
        img = render.render_image(pdf_page, zoom, tuple(rect))
    except Exception:
        return None, ""
    w, h, s = img.width, img.height, img.tobytes()
    if w < 4 or h < 4:
        return None, ""
    px = [[(s[(y * w + x) * 3], s[(y * w + x) * 3 + 1], s[(y * w + x) * 3 + 2]) for x in range(w)] for y in range(h)]
    border = [px[0][x] for x in range(w)] + [px[h - 1][x] for x in range(w)] + [px[y][0] for y in range(h)] + [px[y][w - 1] for y in range(h)]
    bg = tuple(sorted(c[i] for c in border)[len(border) // 2] for i in range(3))
    ink_px = []
    n = _GRID
    # A grid cell covers several pixels now that the crop is drawn larger, and counts as ink when a
    # quarter of them are. Any pixel at all fattens the ink until a tick knocked out of a green disc
    # closes up and the disc reads as a plain dot; half of them thins it until a chevron in a disc
    # disappears. A quarter reads every mark right and reads the same whichever library drew the page.
    hits = [[0] * n for _ in range(n)]
    seen = [[0] * n for _ in range(n)]
    for y in range(h):
        gy = min(n - 1, int(y * n / h))
        for x in range(w):
            gx = min(n - 1, int(x * n / w))
            seen[gy][gx] += 1
            r, g, b = px[y][x]
            if abs(r - bg[0]) + abs(g - bg[1]) + abs(b - bg[2]) > 120:
                hits[gy][gx] += 1
                ink_px.append((r, g, b))
    mask = [[1 if hits[y][x] >= max(1, 0.25 * seen[y][x]) else 0 for x in range(n)] for y in range(n)]
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


def _points_right(m) -> float | None:
    """How firmly the ink is an arrow with a shaft pointing right, or None.

    A bar through the middle running most of the ink's length; a head of two arms at the right end, one above the bar
    and one below, each closing on the bar's end - nearer the bar, further right; and nothing but the bar at the left
    end. A plus sign has its upright in the middle and no arms closing, a T-bar has its cross-bar straight, a solid
    triangle has ink at its base, and a star turned to take its top spike for the bar ends in two legs either side of the
    bar's line, where an arrowhead's arms meet on it; none of them passes."""
    n = len(m)
    rows = [y for y in range(n) if any(m[y])]
    cols = [x for x in range(n) if any(m[y][x] for y in range(n))]
    if len(rows) < 6 or len(cols) < 6:
        return None
    y0, y1, x0, x1 = rows[0], rows[-1], cols[0], cols[-1]
    h, w = y1 - y0 + 1, x1 - x0 + 1
    mid = (y0 + y1) / 2.0
    band = max(1, round(h / 8))
    shaft = [y for y in range(y0, y1 + 1) if abs(y - mid) <= band + 1 and sum(m[y][x0:x1 + 1]) >= 0.7 * w]
    if not shaft:
        return None
    above = [y for y in range(y0, min(shaft)) if any(m[y])]
    below = [y for y in range(max(shaft) + 1, y1 + 1) if any(m[y])]
    if not above or not below:
        return None
    if any(m[y][x] for y in above + below for x in range(x0, int(x0 + 0.25 * w))):
        return None
    # The head's arms meet on the shaft's line, so the ink's far end lies on the shaft (the Doody's star rating on
    # headers_footers 7881b598 ends in two legs with nothing between them).
    if not any(m[y][x] for y in shaft for x in range(max(x0, x1 + 1 - max(2, round(0.1 * w))), x1 + 1)):
        return None

    def centre(y):
        xs = [x for x in range(x0, x1 + 1) if m[y][x]]
        return sum(xs) / len(xs)

    closing = min(centre(above[-1]) - centre(above[0]), centre(below[0]) - centre(below[-1])) / w
    return round(closing, 2) if closing > 0.15 else None


def _shafted_arrow(mask):
    """An arrow with a shaft, whichever way it points, or None.

    Budget Direct's page links cut one out of a green square beside "page 47". The chevron test wants an arrow's arms
    to reach the corners of its ink; a shaft running the length of the ink leaves the corners at its tail empty, so the
    squares were read as dots and every "go to page" came out as a bullet."""
    n = len(mask)
    views = {
        "arrow-right": mask,
        "arrow-left": [list(reversed(row)) for row in mask],
        "arrow-down": [[mask[x][y] for x in range(n)] for y in range(n)],
        "arrow-up": [list(reversed([mask[x][y] for x in range(n)])) for y in range(n)],
    }
    for kind, view in views.items():
        score = _points_right(view)
        if score is not None:
            return kind, score
    return None


def _best_template(mask, shafts: bool = True, glyph: bool = False):
    """Say what shape the ink is.

    Ticks and crosses are told by where their ink lies (a tick leaves the
    upper-left quarter empty and runs from lower-left to upper-right; a cross
    fills all four quarters along the diagonals), which holds for any stroke
    weight or font. Discs, squares and boxes are matched against templates
    with checks that a glyph in a ring ("$") cannot pass. `shafts` false leaves
    the shafted arrow out, for what is left once a ring is erased. `glyph` reads
    the ink of an icon font's glyph, whose tick may be heavy enough to carry into
    the upper-left quarter where its strokes meet.
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
    # A heavy tick's strokes carry a little into that quarter where they meet: FontAwesome's check, set in every cell of
    # RAC's 2021 pricing tables, puts 12 to 13 per cent of its ink there. Only a glyph's tick has that room: given to
    # drawn marks too, two pieces of an Allianz illustration, a hand and a pen, read as ticks.
    if thin and ul < (0.15 if glyph else 0.12) and ur >= 0.25 and ll >= 0.12 and lr <= 0.35 and ll + ur >= 0.6:
        return "tick", round(1.0 - ul - max(0.0, lr - 0.1), 2)
    # An arrow head, before the cross test because the two are easily confused: both are two
    # strokes crossing the middle. The difference is at the corners - an X reaches all four, a
    # chevron reaches only the two it opens away from, and its point sits on the opposite edge.
    arrow = (_shafted_arrow(mask) if shafts else None) or _chevron(mask)
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
