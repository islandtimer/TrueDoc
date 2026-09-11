"""The PDF document and page handles TrueDoc reads through (M18, D007): PDFium's, in place of PyMuPDF's.

A handle carries only what the product asks of a page: its file (`parent.name`), its index
(`number`, from 0), its size as drawn (`rect`, from the origin), its rotation, the matrix that turns
unrotated page space into drawn space (`rotation_matrix`), and `set_rotation`, which turns a page
lying on its side for everything downstream - in memory only, the file is not changed. The readers
open the file by path themselves (`pdftext_rawdict`, `pdfium_objects`, `render`), so a handle holds
no text or drawings of its own.

Each value is PyMuPDF's exactly, down to the 32-bit arithmetic, including one quirk: PyMuPDF builds
the rotation matrix from the /CropBox as written, where the page is drawn from the crop box cut to
the media box, so on a page whose crop box reaches past its media box the two sizes differ. The
proof is `handle_identity.py`. Anything else a page is asked for belongs to the old reader
(TRUEDOC_READER=mupdf and the fallbacks) and goes to PyMuPDF's copy of the page, opened only then.
"""
from __future__ import annotations

import os
import struct

from truedoc.geometry import Matrix, Rect

_F32 = struct.Struct("f")


def open_pdf(path: str) -> "PdfDocument":
    return PdfDocument(path)


class PdfDocument:
    """An open PDF: `len`, indexing, `name`, `metadata` and `close`, as PyMuPDF's document offers them."""

    def __init__(self, path: str) -> None:
        import pypdfium2 as pdfium

        self.name = path
        self._pdf = pdfium.PdfDocument(path)
        self._mu = None

    def __len__(self) -> int:
        return len(self._pdf)

    def __getitem__(self, index: int) -> "PdfPage":
        if index < 0:
            index += len(self)
        if not 0 <= index < len(self):
            raise IndexError(f"page {index} not in document")
        return PdfPage(self, index)

    @property
    def metadata(self) -> dict:
        """The document information, under PyMuPDF's lower-case keys (only `title` is read)."""
        try:
            info = self._pdf.get_metadata_dict(skip_empty=False)
        except Exception:
            return {}
        return {k.lower(): v for k, v in info.items()}

    def mupdf(self):
        """The same file opened by PyMuPDF, for the old reader's paths only; opened on first use."""
        if self._mu is None:
            import pymupdf

            self._mu = pymupdf.open(self.name)
        return self._mu

    def close(self) -> None:
        if self._mu is not None:
            self._mu.close()
            self._mu = None
        self._pdf.close()


class PdfPage:
    def __init__(self, parent: PdfDocument, number: int) -> None:
        self.parent = parent
        self.number = number
        self._mu = None
        page = parent._pdf[number]
        try:
            width, height = page.get_size()
            self._rotation = int(page.get_rotation()) % 360
            # the page's own boxes; None when absent or inherited from the page tree
            crop = page.get_cropbox(fallback_ok=False)
            media = page.get_mediabox(fallback_ok=False)
        finally:
            page.close()
        # get_size is the page as drawn; keep the unrotated size, as the rotation can change
        if self._rotation in (90, 270):
            width, height = height, width
        self._width, self._height = float(width), float(height)
        self._crop_w, self._crop_h = _crop_size(crop, media, self._width, self._height)

    @property
    def rotation(self) -> int:
        return self._rotation

    def set_rotation(self, rotation: int) -> None:
        """Turn the page for everything downstream. The file is not changed."""
        rotation = int(rotation)
        if rotation % 90:
            raise ValueError("bad rotation")
        self._rotation = rotation % 360
        if self._mu is not None:
            self._mu.set_rotation(self._rotation)

    @property
    def rect(self) -> Rect:
        if self._rotation in (90, 270):
            return Rect(0, 0, self._height, self._width)
        return Rect(0, 0, self._width, self._height)

    @property
    def rotation_matrix(self) -> Matrix:
        w, h = self._crop_w, self._crop_h
        if self._rotation == 90:
            return Matrix(0, 1, -1, 0, h, 0)
        if self._rotation == 180:
            return Matrix(-1, 0, 0, -1, w, h)
        if self._rotation == 270:
            return Matrix(0, -1, 1, 0, 0, w)
        return Matrix(1, 0, 0, 1, 0, 0)

    def __getattr__(self, name: str):
        # The old reader's calls (`get_text`, `get_pixmap`, `get_drawings` ...) go to PyMuPDF's copy of
        # the page, turned the same way.
        if name.startswith("_"):
            raise AttributeError(name)
        _note(self, name)
        if self._mu is None:
            self._mu = self.parent.mupdf()[self.number]
            if int(self._mu.rotation) != self._rotation:
                self._mu.set_rotation(self._rotation)
        return getattr(self._mu, name)


def _note(page: PdfPage, name: str) -> None:
    """With TRUEDOC_MUPDF_TRACE naming a folder, note each call that still reaches PyMuPDF, one file per
    process: what is left to move before the package can leave the product (M18, D007)."""
    folder = os.environ.get("TRUEDOC_MUPDF_TRACE")
    if not folder:
        return
    try:
        with open(os.path.join(folder, f"{os.getpid()}.tsv"), "a", encoding="utf-8") as fh:
            fh.write(f"{name}\t{page.parent.name}\t{page.number + 1}\t{page.rotation}\n")
    except OSError:
        pass


def _ordered(box) -> tuple[float, float, float, float] | None:
    """A PDF box with its corners in order, or None when absent or empty (MuPDF's `pdf_to_rect`)."""
    if box is None:
        return None
    x0, x1 = min(box[0], box[2]), max(box[0], box[2])
    y0, y1 = min(box[1], box[3]), max(box[1], box[3])
    if x0 >= x1 or y0 >= y1:
        return None
    return (x0, y0, x1, y1)


def _crop_size(crop, media, width: float, height: float) -> tuple[float, float]:
    """The crop box's width and height as MuPDF takes them for the rotation matrix: the /CropBox as
    written, or the media box when it is empty (an empty media box reads as US Letter, one under a
    point as a unit square). A box PDFium cannot read off the page itself, being inherited from the
    page tree, is taken as the page's own size - which it is unless it reaches past the media box.
    MuPDF keeps the width and height as 32-bit floats, and so does this."""
    box = _ordered(crop)
    if box is None:
        if crop is None or media is None:
            return width, height
        box = _ordered(media)
        if box is None:
            return 612.0, 792.0
        if box[2] - box[0] < 1 or box[3] - box[1] < 1:
            return 1.0, 1.0
    return _f32(box[2] - box[0]), _f32(box[3] - box[1])


def _f32(x: float) -> float:
    return _F32.unpack(_F32.pack(x))[0]
