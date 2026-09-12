"""TrueDoc converts with PyMuPDF unavailable (M18, D007): the product path is PDFium's alone.

PyMuPDF is AGPL or a paid licence, and D007 keeps AGPL out of the product. It stays reachable for
measurement and for the old reader (TRUEDOC_READER=mupdf), imported only when one of those asks. This
converts pages in a fresh interpreter where importing PyMuPDF fails, so a call that still reaches it on
the default path fails here instead of quietly working - the way the renderer quietly fell back to
MuPDF on every page from 10 to 12 Sept.
"""
import os
import subprocess
import sys
import tempfile

import pytest

from truedoc.extract import render

pytestmark = pytest.mark.skipif(not render.available(), reason="pypdfium2 not installed")

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCRIPT = (
    "import os, sys\n"
    "sys.modules['pymupdf'] = None\n"
    "sys.modules['fitz'] = None\n"
    "for k in ('TRUEDOC_READER', 'TRUEDOC_RENDERER', 'TRUEDOC_OBJECTS'):\n"
    "    os.environ.pop(k, None)\n"
    "from truedoc.pipeline import ConvertOptions, convert\n"
    "sys.stdout.write(convert(sys.argv[1], ConvertOptions(frontmatter=False)))\n"
)

# Page 1: prose with a ruled box. Page 2: filed a quarter turn round (/Rotate 90). Page 3: a line a
# reader cannot see (render mode 3) under a line they can.
_PAGES = (
    (b"/Rotate 0",
     b"BT /F1 14 Tf 72 720 Td (Policy wording for home cover) Tj ET\n"
     b"BT /F1 11 Tf 72 690 Td (We pay for loss or damage to your home.) Tj ET\n"
     b"0.5 w 72 600 200 40 re S\n"),
    # filed a quarter turn round, with its glyphs turned to match, so it reads upright to a person
    (b"/Rotate 90",
     b"BT /F1 12 Tf 0 1 -1 0 72 72 Tm (This page is filed on its side.) Tj ET\n"),
    (b"/Rotate 0",
     b"BT /F1 12 Tf 72 720 Td (Visible statement of cover.) Tj ET\n"
     b"BT /F1 12 Tf 3 Tr 72 700 Td (Unseen layer words) Tj ET\n"),
)


def _pdf() -> str:
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [" + b" ".join(str(3 + 2 * i).encode() + b" 0 R" for i in range(len(_PAGES)))
            + b"] /Count " + str(len(_PAGES)).encode() + b" >>"]
    font = 3 + 2 * len(_PAGES)
    for rotate, content in _PAGES:
        own = len(objs) + 1
        objs.append(b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] " + rotate
                    + b" /Resources << /Font << /F1 " + str(font).encode() + b" 0 R >> >> /Contents "
                    + str(own + 1).encode() + b" 0 R >>")
        objs.append(b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream")
    objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objs, start=1):
        offsets.append(len(out))
        out += str(i).encode() + b" 0 obj\n" + body + b"\nendobj\n"
    start = len(out)
    out += b"xref\n0 " + str(len(objs) + 1).encode() + b"\n0000000000 65535 f \n"
    for off in offsets:
        out += ("%010d 00000 n \n" % off).encode()
    out += (b"trailer\n<< /Size " + str(len(objs) + 1).encode() + b" /Root 1 0 R >>\n"
            b"startxref\n" + str(start).encode() + b"\n%%EOF\n")
    fd, path = tempfile.mkstemp(suffix=".pdf")
    with os.fdopen(fd, "wb") as fh:
        fh.write(bytes(out))
    return path


def test_a_document_converts_with_pymupdf_unavailable():
    path = _pdf()
    try:
        done = subprocess.run([sys.executable, "-c", _SCRIPT, path], cwd=_ROOT, capture_output=True,
                              text=True, encoding="utf-8", timeout=600)
    finally:
        os.unlink(path)
    assert done.returncode == 0, done.stderr[-3000:]
    md = done.stdout
    for words in ("Policy wording for home cover", "We pay for loss or damage to your home.",
                  "This page is filed on its side.", "Visible statement of cover."):
        assert words in md, (words, md)
    assert "Unseen layer words" not in md, md
