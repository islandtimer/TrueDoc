"""Render PDF pages to images (for layout models and OCR)."""

from __future__ import annotations

import pymupdf
from PIL import Image


def render_page(pdf_page: "pymupdf.Page", dpi: int = 144, clip=None) -> tuple[Image.Image, float]:
    """Render a page (or a clip rectangle, in points) and return (image, pixels-per-point)."""
    scale = dpi / 72.0
    mat = pymupdf.Matrix(scale, scale)
    kwargs = {"matrix": mat, "alpha": False, "colorspace": pymupdf.csRGB}
    if clip is not None:
        kwargs["clip"] = pymupdf.Rect(*clip)
    pix = pdf_page.get_pixmap(**kwargs)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    return img, scale
