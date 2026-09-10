"""A document opened from memory converts with the PDFium switches on (M18).

Every PDFium adapter opens the file by its path, because PDFium reads files and MuPDF's page
object is all a caller hands over. A document opened from bytes has no path - `parent.name` is
empty - and the first version reached `os.stat(None)`, a TypeError that the `except OSError`
around it did not catch. The launcher found it, because it runs the suite with whatever switches
the launching shell carries and `test_sideways_pages` builds its page in memory; I had only ever
run the suite in the default configuration. The adapters now hand such a document back to MuPDF.
"""

import os

import pymupdf
import pytest

from truedoc.extract import render
from truedoc.extract.textlayer import extract_page

_SWITCHES = {"TRUEDOC_READER": "pdftext", "TRUEDOC_RENDERER": "pdfium", "TRUEDOC_OBJECTS": "pdfium"}


def _pdf() -> bytes:
    content = b"BT /F1 12 Tf 30 150 Td (In memory) Tj ET\n"
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
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
    return bytes(out)


@pytest.mark.skipif(not render.available(), reason="pypdfium2 not installed")
def test_a_document_with_no_file_behind_it_still_converts_with_the_switches_on():
    was = {k: os.environ.get(k) for k in _SWITCHES}
    os.environ.update(_SWITCHES)
    try:
        doc = pymupdf.open(stream=_pdf(), filetype="pdf")
        try:
            assert not doc.name, "the point of the test is a document without a path"
            page = extract_page(doc[0], 1)
            assert [w.text for w in page.words] == ["In", "memory"]
        finally:
            doc.close()
    finally:
        render.close_documents()
        for k, v in was.items():
            os.environ.pop(k, None)
            if v is not None:
                os.environ[k] = v
