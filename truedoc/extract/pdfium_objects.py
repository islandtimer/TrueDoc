"""What is drawn on a page, in the order it is drawn, read through PDFium (D007, M18).

Four things in TrueDoc ask MuPDF what a page has on it, and all four want the same answer in
slightly different clothes: `_extract_drawings` and `_extract_images` in `extract/textlayer.py`
build the rulings and picture regions, `marks._candidates` hunts for small shapes that might be a
tick, and `_Visibility` works out what is painted over what so hidden text can be found (D011).

MuPDF offers three separate views of this - `get_drawings`, `get_image_info` and `get_bboxlog` -
and the last of those looked, from the outside, like the hard part of leaving PyMuPDF: it is a log
of every drawing operation with its box, and PDFium has nothing called that. Reading what TrueDoc
actually takes from it dissolved most of the problem. It uses the log for two things only: the
bounding boxes of images and shadings, and the order they were painted in. PDFium's page objects
come back in painting order with a type and a bounding box, which is the same information.

**Coordinates are MuPDF's unrotated page space** - the space `get_drawings` and `get_image_info`
report in, which `textlayer._rect` then turns once. PDFium measures from the bottom left, so each
box is flipped about the crop box here, exactly as `pdftext_rawdict` does for characters.

**Form XObjects are flattened.** MuPDF reports the shapes inside a form as if they were drawn on
the page; PDFium reports the form as one object with its own children, so this walks into them and
keeps the page-order numbering flat.
"""
from __future__ import annotations

import ctypes
import os
from dataclasses import dataclass, field

_MAX_OBJECTS = 40000     # a runaway generated page should not hang a conversion


@dataclass
class PageObject:
    """One thing drawn on the page, in MuPDF's unrotated coordinates."""
    order: int                              # painting order, 0 first
    kind: str                               # "path" | "image" | "text" | "shading" | "form"
    bbox: tuple                             # (x0, y0, x1, y1), y down from the top
    fill: tuple | None = None               # (r, g, b), each 0..1, or None when nothing is filled
    fill_alpha: float = 1.0
    stroke: tuple | None = None
    stroke_width: float = 0.0
    rects: list = field(default_factory=list)   # axis-aligned rectangles this path fills
    lines: list = field(default_factory=list)   # straight segments this path strokes, (x0, y0, x1, y1)
    invisible_text: bool = False            # text drawn in render mode 3


def enabled() -> bool:
    """On by default since run 71 (D023); `TRUEDOC_OBJECTS=mupdf` reads drawings with MuPDF instead."""
    return os.environ.get("TRUEDOC_OBJECTS", "pdfium").strip().lower() not in ("mupdf", "off", "0", "")


def available() -> bool:
    try:
        import pypdfium2  # noqa: F401
    except Exception:
        return False
    return True


def _colour(getter, obj) -> tuple[tuple | None, float]:
    r, g, b, a = (ctypes.c_uint() for _ in range(4))
    if not getter(obj, r, g, b, a):
        return None, 1.0
    if a.value == 0:
        return None, 0.0
    return (r.value / 255.0, g.value / 255.0, b.value / 255.0), a.value / 255.0


_IDENTITY = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def _compose(outer: tuple, inner: tuple) -> tuple:
    """The matrix that applies `inner` and then `outer`."""
    ai, bi, ci, di, ei, fi = inner
    ao, bo, co, do, eo, fo = outer
    return (ao * ai + co * bi, bo * ai + do * bi,
            ao * ci + co * di, bo * ci + do * di,
            ao * ei + co * fi + eo, bo * ei + do * fi + fo)


def _apply(matrix: tuple, x: float, y: float) -> tuple:
    a, b, c, d, e, f = matrix
    return (a * x + c * y + e, b * x + d * y + f)


def _box_through(matrix: tuple, x0: float, y0: float, x1: float, y1: float) -> tuple:
    """A rectangle through a matrix, as the envelope of its corners."""
    if matrix == _IDENTITY:
        return (x0, y0, x1, y1)
    pts = [_apply(matrix, x, y) for x, y in ((x0, y0), (x1, y0), (x0, y1), (x1, y1))]
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return (min(xs), min(ys), max(xs), max(ys))


def _rects_of_path(raw, obj, flip, matrix=_IDENTITY) -> list:
    """The axis-aligned rectangles a path draws.

    `_Visibility` needs these rather than the path's bounding box: a box border drawn as a filled
    path spans the whole box while painting only its edges, so its bounds would hide text that is
    plainly visible inside it. MuPDF hands back the source's own `re` operators; PDFium has already
    turned them into line segments, so a closed run of straight lines forming four right angles is
    read back as a rectangle.
    """
    try:
        n = raw.FPDFPath_CountSegments(obj)
    except Exception:
        return []
    if n <= 0:
        return []
    x, y = ctypes.c_float(), ctypes.c_float()
    subpaths: list[list] = []
    current: list = []
    for i in range(min(n, 2000)):
        seg = raw.FPDFPath_GetPathSegment(obj, i)
        if not seg:
            continue
        kind = raw.FPDFPathSegment_GetType(seg)
        if kind == raw.FPDF_SEGMENT_BEZIERTO:
            current = []            # a curve is not a rectangle; abandon this subpath
            continue
        if not raw.FPDFPathSegment_GetPoint(seg, x, y):
            continue
        point = _apply(matrix, x.value, y.value) if matrix != _IDENTITY else (x.value, y.value)
        if kind == raw.FPDF_SEGMENT_MOVETO:
            if len(current) >= 4:
                subpaths.append(current)
            current = [point]
        else:
            current.append(point)
    if len(current) >= 4:
        subpaths.append(current)

    out = []
    for pts in subpaths:
        if len(pts) == 5 and abs(pts[0][0] - pts[4][0]) < 0.01 and abs(pts[0][1] - pts[4][1]) < 0.01:
            pts = pts[:4]
        if len(pts) != 4:
            continue
        xs = sorted(p[0] for p in pts)
        ys = sorted(p[1] for p in pts)
        # axis-aligned means the four corners pair up: two distinct x values, two distinct y
        if abs(xs[0] - xs[1]) > 0.01 or abs(xs[2] - xs[3]) > 0.01:
            continue
        if abs(ys[0] - ys[1]) > 0.01 or abs(ys[2] - ys[3]) > 0.01:
            continue
        out.append(flip(xs[0], ys[0], xs[3], ys[3]))
    return out


def _segments_of_path(raw, obj, flip, matrix=_IDENTITY) -> list:
    """The straight segments a path draws, each as (x0, y0, x1, y1) in the page's space.

    The table finder needs these for a stroked path rather than its bounds: PDFium's bounds
    inflate a stroked path by its line width on every side, so a 3pt rule comes back as a 6pt
    box (f1774abd lost the rule under its header that way, and its table a row), where
    PyMuPDF's finder reads each drawn segment at its own length (D022). A curve gives nothing;
    the point it ends on begins whatever is drawn next.
    """
    try:
        n = raw.FPDFPath_CountSegments(obj)
    except Exception:
        return []
    if n <= 0:
        return []
    x, y = ctypes.c_float(), ctypes.c_float()
    out: list = []
    start = prev = None
    for i in range(min(n, 2000)):
        seg = raw.FPDFPath_GetPathSegment(obj, i)
        if not seg or not raw.FPDFPathSegment_GetPoint(seg, x, y):
            continue
        kind = raw.FPDFPathSegment_GetType(seg)
        point = _apply(matrix, x.value, y.value) if matrix != _IDENTITY else (x.value, y.value)
        if kind == raw.FPDF_SEGMENT_MOVETO:
            start = prev = point
        elif kind == raw.FPDF_SEGMENT_LINETO:
            if prev is not None:
                out.append(flip(prev[0], prev[1], point[0], point[1]))
            prev = point
        else:
            prev = point
        if raw.FPDFPathSegment_GetClose(seg) and start is not None and prev is not None and prev != start:
            out.append(flip(prev[0], prev[1], start[0], start[1]))
            prev = start
    return out


def _clip_box(raw, obj) -> tuple | None:
    """The box of an object's clip path in the page's space, or None when it has none.

    Several clip paths on one object apply together, so their boxes are intersected. The
    points come back in the page's space for an object drawn straight on the page; for one
    inside a form the space is not settled here, so callers ask only at the top level.
    """
    try:
        clip = raw.FPDFPageObj_GetClipPath(obj)
        if not clip:
            return None
        count = raw.FPDFClipPath_CountPaths(clip)
    except Exception:
        return None
    if count <= 0:
        return None
    boxes = []
    x, y = ctypes.c_float(), ctypes.c_float()
    for p in range(count):
        xs, ys = [], []
        for s in range(raw.FPDFClipPath_CountPathSegments(clip, p)):
            seg = raw.FPDFClipPath_GetPathSegment(clip, p, s)
            if seg and raw.FPDFPathSegment_GetPoint(seg, x, y):
                xs.append(x.value)
                ys.append(y.value)
        if xs and ys:
            boxes.append((min(xs), min(ys), max(xs), max(ys)))
    if not boxes:
        return None
    x0, y0 = max(b[0] for b in boxes), max(b[1] for b in boxes)
    x1, y1 = min(b[2] for b in boxes), min(b[3] for b in boxes)
    return (x0, y0, x1, y1) if x1 > x0 and y1 > y0 else (x0, y0, x0, y0)


def _walk(raw, obj, order: list, out: list, flip, matrix: tuple = _IDENTITY, depth: int = 0,
          handles: dict | None = None, clips: dict | None = None,
          veil: float = 1.0, veils: dict | None = None) -> None:
    if len(out) >= _MAX_OBJECTS:
        return
    kind_id = raw.FPDFPageObj_GetType(obj)
    if kind_id == raw.FPDF_PAGEOBJ_FORM and depth < 8:
        # The opacity a form is drawn with comes down with its children too. A journal's "ARTICLE IN PRESS", 72-point
        # type across the page, sits in a form drawn under `/CA 0 /ca 0`; inside it the text sets its own opacity
        # back to 1, so the character says "visible" and the page shows nothing (benchmark tables/c8cdd4c4..._pg3).
        # PDFium reports the form's alpha as it reports a path's. The larger of the two alphas: text may be filled,
        # stroked or both, and only a form that shows neither is sure to show none of it.
        # The smallest on the way down, not the product: a form inside a form inherits the outer one's opacity and
        # reports it again, so multiplying would count it twice. At nothing - the only value read - the two agree.
        _, fill_alpha = _colour(raw.FPDFPageObj_GetFillColor, obj)
        _, stroke_alpha = _colour(raw.FPDFPageObj_GetStrokeColor, obj)
        veil = min(veil, max(fill_alpha, stroke_alpha))
        # A form's children are measured in the form's own space, not the page's, so its matrix
        # has to come down with them. Missed at first, and it cost 38 checks of the tables
        # category: one page's rules all landed 178.5pt from where they belonged, because that is
        # what the form's matrix translates by.
        inner = _IDENTITY
        fm = raw.FS_MATRIX()
        if raw.FPDFPageObj_GetMatrix(obj, fm):
            inner = (fm.a, fm.b, fm.c, fm.d, fm.e, fm.f)
        combined = _compose(matrix, inner)
        try:
            count = raw.FPDFFormObj_CountObjects(obj)
        except Exception:
            count = 0
        for i in range(count):
            child = raw.FPDFFormObj_GetObject(obj, i)
            if child:
                _walk(raw, child, order, out, flip, combined, depth + 1, handles, clips, veil, veils)
        return

    left, bottom, right, top = (ctypes.c_float() for _ in range(4))
    if not raw.FPDFPageObj_GetBounds(obj, left, bottom, right, top):
        return
    box = flip(*_box_through(matrix, left.value, bottom.value, right.value, top.value))

    kind = {raw.FPDF_PAGEOBJ_PATH: "path", raw.FPDF_PAGEOBJ_IMAGE: "image",
            raw.FPDF_PAGEOBJ_TEXT: "text", raw.FPDF_PAGEOBJ_SHADING: "shading"}.get(kind_id, "other")

    fill, fill_alpha = (None, 1.0)
    stroke, width, rects, lines, invisible = None, 0.0, [], [], False
    if kind == "path":
        fillmode, stroking = ctypes.c_int(), ctypes.c_int()
        filled = bool(raw.FPDFPath_GetDrawMode(obj, fillmode, stroking)) and fillmode.value != raw.FPDF_FILLMODE_NONE
        # `FPDFPageObj_GetBounds` reports a box that already went through the object's own
        # matrix, but `FPDFPathSegment_GetPoint` hands back the raw points from before it, so
        # the segments need that matrix as well as any form's. Missing it put one page's
        # rectangles at y = -32,000 while its bounding boxes were perfectly correct.
        own = _IDENTITY
        om = raw.FS_MATRIX()
        if raw.FPDFPageObj_GetMatrix(obj, om):
            own = (om.a, om.b, om.c, om.d, om.e, om.f)
        if filled:
            fill, fill_alpha = _colour(raw.FPDFPageObj_GetFillColor, obj)
            rects = _rects_of_path(raw, obj, flip, _compose(matrix, own))
        if stroking.value:
            stroke, _ = _colour(raw.FPDFPageObj_GetStrokeColor, obj)
            lines = _segments_of_path(raw, obj, flip, _compose(matrix, own))
        w = ctypes.c_float()
        if raw.FPDFPageObj_GetStrokeWidth(obj, w):
            # a stroke inside a scaled form is drawn at the scaled width
            width = float(w.value) * ((abs(matrix[0]) + abs(matrix[3])) / 2.0 if matrix != _IDENTITY else 1.0)
    elif kind == "text":
        try:
            invisible = raw.FPDFTextObj_GetTextRenderMode(obj) == raw.FPDF_TEXTRENDERMODE_INVISIBLE
        except Exception:
            invisible = False

    out.append(PageObject(order=order[0], kind=kind, bbox=box, fill=fill, fill_alpha=fill_alpha,
                          stroke=stroke, stroke_width=width, rects=rects, lines=lines,
                          invisible_text=invisible))
    if handles is not None:
        # The object's pointer, valid only for this page load: pypdfium2 calls FPDF_LoadPage on
        # every `doc[i]`, so a caller that wants to join characters to objects must walk on the
        # same handle it reads the text from. The order numbers are what carry across loads.
        handles[ctypes.cast(obj, ctypes.c_void_p).value] = order[0]
    if veils is not None and kind == "text" and veil < 1.0:
        veils[ctypes.cast(obj, ctypes.c_void_p).value] = veil
    if clips is not None and kind == "text" and depth == 0:
        # Where the page clips this text (a Word-made PDF boxes every paragraph): the text
        # page ignores clipping, and the reader drops what was never shown. Top level only -
        # the space a form's clip paths are reported in is not settled.
        clip = _clip_box(raw, obj)
        if clip is not None:
            clips[ctypes.cast(obj, ctypes.c_void_p).value] = flip(*clip)
    order[0] += 1


def page_box(page) -> tuple[float, float, float, float]:
    """The box a page's coordinates are measured from: the crop box within the media box.

    MuPDF's page rect is the intersection of the two, with its top-left as the origin of
    everything it reports. pypdfium2's `get_cropbox` hands back the /CropBox as written, and a
    journal page (b2ca8e00, headers) writes an A4 crop box around a 430 by 660 media box:
    measured from the raw crop box every character sat 82.5pt right and 92pt down of where
    MuPDF has it, the running head fell out of the page-edge band and stayed in the text.
    `get_size` already reports the intersection's width and height; this is its origin too.
    """
    c, m = page.get_cropbox(), page.get_mediabox()
    box = (max(c[0], m[0]), max(c[1], m[1]), min(c[2], m[2]), min(c[3], m[3]))
    if box[2] <= box[0] or box[3] <= box[1]:
        box = tuple(float(v) for v in c)
    return tuple(float(v) for v in box)


def walk_page(raw, page, handles: dict | None = None, clips: dict | None = None,
              veils: dict | None = None) -> list[PageObject]:
    """Everything drawn on an already-loaded pypdfium2 page, in painting order.

    `handles`, when given, is filled with object pointer -> order for this load, so the caller
    can join the text page's characters (`FPDFText_GetTextObject`) to what was drawn; `clips`,
    when given, with object pointer -> the clip box of each top-level text object that has one,
    in MuPDF's page space; `veils`, when given, with object pointer -> the opacity of the forms
    a text object is drawn inside, where that is under 1.
    """
    x_off, _y0, _x1, y_top = page_box(page)

    def flip(x0, y0, x1, y1):
        ax0, ax1 = x0 - x_off, x1 - x_off
        ay0, ay1 = y_top - y0, y_top - y1
        return (min(ax0, ax1), min(ay0, ay1), max(ax0, ax1), max(ay0, ay1))

    handle = page.raw
    count = raw.FPDFPage_CountObjects(handle)
    out: list[PageObject] = []
    order = [0]
    for i in range(count):
        obj = raw.FPDFPage_GetObject(handle, i)
        if obj:
            _walk(raw, obj, order, out, flip, handles=handles, clips=clips, veils=veils)
    return out


def curve_segments(path: str, page_number: int) -> int | None:
    """How many curves the paths on one page (1-based) draw, forms opened, or None if PDFium cannot read it.

    A letter drawn as an outline is made of curves; a rule, a box or a band of colour is not. A page whose text layer
    holds next to nothing, and whose drawings have no curve, is not holding words drawn as shapes (`pipeline._lost_on`).
    """
    if not path:
        return None
    try:
        import pypdfium2.raw as raw

        from truedoc.extract import render

        page = render.document(path)[page_number - 1]      # held while its handle is walked
        handle = page.raw
    except Exception:
        return None
    count = 0

    def walk(obj, depth: int) -> None:
        nonlocal count
        kind = raw.FPDFPageObj_GetType(obj)
        if kind == raw.FPDF_PAGEOBJ_FORM and depth < 8:
            for i in range(raw.FPDFFormObj_CountObjects(obj)):
                child = raw.FPDFFormObj_GetObject(obj, i)
                if child:
                    walk(child, depth + 1)
        elif kind == raw.FPDF_PAGEOBJ_PATH:
            for i in range(min(raw.FPDFPath_CountSegments(obj), 2000)):
                seg = raw.FPDFPath_GetPathSegment(obj, i)
                if seg and raw.FPDFPathSegment_GetType(seg) == raw.FPDF_SEGMENT_BEZIERTO:
                    count += 1

    try:
        for i in range(min(raw.FPDFPage_CountObjects(handle), _MAX_OBJECTS)):
            obj = raw.FPDFPage_GetObject(handle, i)
            if obj:
                walk(obj, 0)
    except Exception:
        return None
    return count


# Five stages ask for the same page's objects (drawings, images, mark candidates, ruled tables,
# hidden text), so the last few pages' lists are kept. Plain dataclasses; no handle is held.
_CACHE: dict[tuple, list] = {}
_CACHE_MAX = 4


def page_objects(path: str, page_number: int) -> list[PageObject] | None:
    """Everything drawn on one page (1-based), in painting order, or None if PDFium cannot read it."""
    if not path:
        # A document opened from memory has no file for PDFium to open; MuPDF reads it instead.
        # Found by the launcher, which runs the suite with the switches on: a test that builds
        # its page in memory reached os.stat(None), a TypeError no OSError guard catches.
        return None
    try:
        import pypdfium2.raw as raw

        from truedoc.extract import render
    except Exception:
        return None
    try:
        st = os.stat(path)
        key = (os.path.abspath(path), page_number, st.st_mtime_ns, st.st_size)
    except (OSError, TypeError):
        key = None
    if key is not None and key in _CACHE:
        return _CACHE[key]
    try:
        out = walk_page(raw, render.document(path)[page_number - 1])
    except Exception:
        return None
    if key is not None:
        if len(_CACHE) >= _CACHE_MAX:
            _CACHE.pop(next(iter(_CACHE)))
        _CACHE[key] = out
    return out
