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
    invisible_text: bool = False            # text drawn in render mode 3


def enabled() -> bool:
    return os.environ.get("TRUEDOC_OBJECTS", "").strip().lower() == "pdfium"


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


def _walk(raw, obj, order: list, out: list, flip, matrix: tuple = _IDENTITY, depth: int = 0,
          handles: dict | None = None) -> None:
    if len(out) >= _MAX_OBJECTS:
        return
    kind_id = raw.FPDFPageObj_GetType(obj)
    if kind_id == raw.FPDF_PAGEOBJ_FORM and depth < 8:
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
                _walk(raw, child, order, out, flip, combined, depth + 1, handles)
        return

    left, bottom, right, top = (ctypes.c_float() for _ in range(4))
    if not raw.FPDFPageObj_GetBounds(obj, left, bottom, right, top):
        return
    box = flip(*_box_through(matrix, left.value, bottom.value, right.value, top.value))

    kind = {raw.FPDF_PAGEOBJ_PATH: "path", raw.FPDF_PAGEOBJ_IMAGE: "image",
            raw.FPDF_PAGEOBJ_TEXT: "text", raw.FPDF_PAGEOBJ_SHADING: "shading"}.get(kind_id, "other")

    fill, fill_alpha = (None, 1.0)
    stroke, width, rects, invisible = None, 0.0, [], False
    if kind == "path":
        fillmode, stroking = ctypes.c_int(), ctypes.c_int()
        filled = bool(raw.FPDFPath_GetDrawMode(obj, fillmode, stroking)) and fillmode.value != raw.FPDF_FILLMODE_NONE
        if filled:
            fill, fill_alpha = _colour(raw.FPDFPageObj_GetFillColor, obj)
            # `FPDFPageObj_GetBounds` reports a box that already went through the object's own
            # matrix, but `FPDFPathSegment_GetPoint` hands back the raw points from before it, so
            # the segments need that matrix as well as any form's. Missing it put one page's
            # rectangles at y = -32,000 while its bounding boxes were perfectly correct.
            own = _IDENTITY
            om = raw.FS_MATRIX()
            if raw.FPDFPageObj_GetMatrix(obj, om):
                own = (om.a, om.b, om.c, om.d, om.e, om.f)
            rects = _rects_of_path(raw, obj, flip, _compose(matrix, own))
        if stroking.value:
            stroke, _ = _colour(raw.FPDFPageObj_GetStrokeColor, obj)
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
                          stroke=stroke, stroke_width=width, rects=rects, invisible_text=invisible))
    if handles is not None:
        # The object's pointer, valid only for this page load: pypdfium2 calls FPDF_LoadPage on
        # every `doc[i]`, so a caller that wants to join characters to objects must walk on the
        # same handle it reads the text from. The order numbers are what carry across loads.
        handles[ctypes.cast(obj, ctypes.c_void_p).value] = order[0]
    order[0] += 1


def walk_page(raw, page, handles: dict | None = None) -> list[PageObject]:
    """Everything drawn on an already-loaded pypdfium2 page, in painting order.

    `handles`, when given, is filled with object pointer -> order for this load, so the caller
    can join the text page's characters (`FPDFText_GetTextObject`) to what was drawn.
    """
    crop = page.get_cropbox()
    x_off, y_top = float(crop[0]), float(crop[3])

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
            _walk(raw, obj, order, out, flip, handles=handles)
    return out


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
