"""Render PDF pages to images (for layout models, OCR, marks and the vision endpoints).

Every part of TrueDoc that looks at pixels rather than text comes through here, so the choice of
drawing library is made once. PDFium draws by default since run 71 (D023, the licence path of D007
and M18); PyMuPDF draws when `TRUEDOC_RENDERER=mupdf` is set, for measurement.

**Clip rectangles are in the rendered page's own space** - the space a reader sees, and the space
the layout model's boxes live in. Both libraries clip there, but they say it differently: PyMuPDF
takes the rectangle, PDFium takes four insets from the edges of the bitmap, applied after rotation.
The conversion is `(x0, H - y1, W - x1, y0)`, measured against PyMuPDF over 32 pages including 8
rotated ones: a mean of 5.7 shades per pixel apart, against 35.7 for the other plausible reading
and 4.3 for the same pages rendered whole. See `bench/tools/render_compare.py`.

Two details that cost an afternoon when they were assumed rather than measured:

* PDFium refuses a negative inset, so a clip reaching past the edge of the page has to be clamped
  first. PyMuPDF simply intersects.
* pypdfium2 rounds each inset up (`math.ceil(inset * scale)`), so a clip on fractional points can
  land a pixel away from PyMuPDF's. Over text that shows up as a large mean difference and looks
  exactly like a wrong convention.
"""

from __future__ import annotations

import io
import math
import os

from PIL import Image

from truedoc.extract.handle import pymupdf_module

_DOCS: dict[str, tuple] = {}     # path -> (stamp, PdfDocument); a handful kept open
_DOCS_MAX = 2


def enabled() -> bool:
    """On by default since run 71 (D023); `TRUEDOC_RENDERER=mupdf` draws with MuPDF instead."""
    return os.environ.get("TRUEDOC_RENDERER", "pdfium").strip().lower() not in ("mupdf", "off", "0", "")


def available() -> bool:
    try:
        import pypdfium2  # noqa: F401
    except Exception:
        return False
    return True


def _stamp(path: str) -> tuple:
    try:
        st = os.stat(path)
        return (st.st_mtime_ns, st.st_size)
    except OSError:
        return (0, 0)


def document(path: str):
    """An open PDFium document, reused across calls.

    `marks.py` renders once per candidate shape - hundreds on a busy page - so reopening the file
    each time would cost more than the drawing does.
    """
    import pypdfium2 as pdfium

    stamp = _stamp(path)
    hit = _DOCS.get(path)
    if hit is not None and hit[0] == stamp:
        return hit[1]
    if hit is not None:
        try:
            hit[1].close()
        except Exception:
            pass
        _DOCS.pop(path, None)
    doc = pdfium.PdfDocument(path)
    while len(_DOCS) >= _DOCS_MAX:
        _, old = _DOCS.pop(next(iter(_DOCS)))
        try:
            old.close()
        except Exception:
            pass
    _DOCS[path] = (stamp, doc)
    return doc


def _pixel_box(clip, scale: float, width: float, height: float) -> tuple:
    """The clip as whole pixels of the page's own grid, cut to the page: the pixels MuPDF would draw
    (`fz_round_rect`, with its own thousandth of a pixel of slack)."""
    sw, sh = math.ceil(width * scale), math.ceil(height * scale)
    x0 = min(max(math.floor(float(clip[0]) * scale + 0.001), 0), sw)
    y0 = min(max(math.floor(float(clip[1]) * scale + 0.001), 0), sh)
    x1 = min(max(math.ceil(float(clip[2]) * scale - 0.001), x0), sw)
    y1 = min(max(math.ceil(float(clip[3]) * scale - 0.001), y0), sh)
    return (x0, y0, x1, y1)


def _crop(box, scale: float, width: float, height: float) -> tuple:
    """That pixel box as the four edge insets PDFium wants - left, bottom, right, top.

    PDFium draws the whole page at `scale` and cuts whole pixels off each edge, rounding each inset up, so
    each inset is given half a pixel inside its edge and PDFium's rounding lands on the row MuPDF drew. A
    crop one pixel short turns a chevron in a disc into a dot (`tests/test_marks_arrows.py`).
    """
    sw, sh = math.ceil(width * scale), math.ceil(height * scale)
    x0, y0, x1, y1 = box
    return (max(0.0, x0 - 0.5) / scale, max(0.0, sh - y1 - 0.5) / scale,
            max(0.0, sw - x1 - 0.5) / scale, max(0.0, y0 - 0.5) / scale)


def _render_pdfium(pdf_page, scale: float, clip, grey: bool) -> Image.Image | None:
    try:
        path = pdf_page.parent.name
        if not path:
            return None
        page = document(path)[pdf_page.number]
        # A page that lay on its side is turned by setting its rotation (`pipeline._turn_page`,
        # `vision/regions.py`), and the turn lives only in the page handle, not in the file PDFium
        # reads: PDFium is asked to add it (clockwise, as /Rotate is; the crop applies after it).
        turn = (int(pdf_page.rotation) - int(page.get_rotation())) % 360
        width, height = float(pdf_page.rect.width), float(pdf_page.rect.height)
        crop = (0, 0, 0, 0)
        if clip is not None:
            box = _pixel_box(clip, scale, width, height)
            if box[2] <= box[0] or box[3] <= box[1]:
                # Nothing of the page lies inside the clip. PDFium refuses such a crop ("Crop exceeds page
                # dimensions") and MuPDF hands back an empty picture, so hand back the same empty picture
                # rather than falling back to MuPDF for it: those were the last renderings reaching PyMuPDF.
                return Image.new("L" if grey else "RGB", (box[2] - box[0], box[3] - box[1]), "white")
            crop = _crop(box, scale, width, height)
        bitmap = page.render(scale=scale, rotation=turn, crop=crop, grayscale=grey)
        return bitmap.to_pil().convert("L" if grey else "RGB")
    except Exception:
        return None


def _render_mupdf(pdf_page, scale: float, clip, grey: bool) -> Image.Image:
    pymupdf = pymupdf_module()
    kwargs = {"matrix": pymupdf.Matrix(scale, scale), "alpha": False,
              "colorspace": pymupdf.csGRAY if grey else pymupdf.csRGB}
    if clip is not None:
        kwargs["clip"] = pymupdf.Rect(*clip)
    pix = pdf_page.get_pixmap(**kwargs)
    return Image.frombytes("L" if grey else "RGB", (pix.width, pix.height), pix.samples)


def render_image(pdf_page, scale: float = 1.0, clip=None, grey: bool = False) -> Image.Image:
    """The page, or the part of it inside `clip`, drawn at `scale` times its natural size.

    `clip` is a rectangle in the rendered page's own space (see the module docstring). PDFium is
    used when it is switched on and can do the job, and PyMuPDF otherwise, so a page PDFium cannot
    draw still converts.
    """
    if enabled():
        img = _render_pdfium(pdf_page, scale, clip, grey)
        if img is not None:
            return img
    return _render_mupdf(pdf_page, scale, clip, grey)


def render_page(pdf_page: "pymupdf.Page", dpi: int = 144, clip=None) -> tuple[Image.Image, float]:
    """Render a page (or a clip rectangle, in points) and return (image, pixels-per-point)."""
    scale = dpi / 72.0
    return render_image(pdf_page, scale, clip, False), scale


def render_png(pdf_page, scale: float = 1.0, clip=None) -> bytes:
    """The same rendering, as PNG bytes, for the vision endpoints."""
    buf = io.BytesIO()
    render_image(pdf_page, scale, clip, False).save(buf, format="PNG")
    return buf.getvalue()


def close_documents() -> None:
    """Let go of any PDFium documents held open. Called when a conversion finishes."""
    for _, doc in _DOCS.values():
        try:
            doc.close()
        except Exception:
            pass
    _DOCS.clear()
