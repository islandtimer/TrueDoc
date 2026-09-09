"""Render PDF pages to images (for layout models, OCR, marks and the vision endpoints).

Every part of TrueDoc that looks at pixels rather than text comes through here, so the choice of
drawing library is made once. PyMuPDF draws by default; PDFium draws when `TRUEDOC_RENDERER=pdfium`
is set, which is the licence path of D007 and M18.

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
import os

import pymupdf
from PIL import Image

try:  # silence PyMuPDF's one-off advert for its AGPL layout package
    pymupdf.no_recommend_layout()
except Exception:
    pass

_DOCS: dict[str, tuple] = {}     # path -> (stamp, PdfDocument); a handful kept open
_DOCS_MAX = 2


def enabled() -> bool:
    return os.environ.get("TRUEDOC_RENDERER", "").strip().lower() == "pdfium"


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


def _document(path: str):
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


def _crop(clip, width: float, height: float) -> tuple:
    """A clip rectangle as the four edge insets PDFium wants, clamped inside the page."""
    x0 = max(0.0, min(float(clip[0]), width))
    y0 = max(0.0, min(float(clip[1]), height))
    x1 = max(x0, min(float(clip[2]), width))
    y1 = max(y0, min(float(clip[3]), height))
    return (x0, height - y1, width - x1, y0)


def _render_pdfium(pdf_page, scale: float, clip, grey: bool) -> Image.Image | None:
    try:
        path = pdf_page.parent.name
        if not path:
            return None
        page = _document(path)[pdf_page.number]
        # `vision/regions.py` turns a page that lies on its side by setting its rotation, and that
        # change lives only in MuPDF's copy of the document. Anything PDFium would draw differently
        # from what the caller is holding goes back to MuPDF rather than quietly drawing the page
        # the wrong way up.
        if int(page.get_rotation()) != int(pdf_page.rotation):
            return None
        width, height = float(pdf_page.rect.width), float(pdf_page.rect.height)
        crop = _crop(clip, width, height) if clip is not None else (0, 0, 0, 0)
        bitmap = page.render(scale=scale, crop=crop, grayscale=grey)
        return bitmap.to_pil().convert("L" if grey else "RGB")
    except Exception:
        return None


def _render_mupdf(pdf_page, scale: float, clip, grey: bool) -> Image.Image:
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
