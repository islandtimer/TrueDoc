"""Hidden text (D011) must be found the same way whichever library reads the page (M18, D022).

`_Visibility` decides, per character, whether a reader can see it: drawn in render mode 3, covered
by an opaque shape painted afterwards, or the same colour as what lies beneath. It is the last
stage still reading through MuPDF's own devices (`get_texttrace`, `get_bboxlog`), and it has the
same silent failure mode as everything else in the swap: get it wrong and nothing crashes - text a
reader cannot see lands in the body, or text they can see is quietly dropped.

The quantity the two readers must agree on is the set of hidden characters and the reason for each.
This builds a page carrying one word of every kind and checks both that the reasons are the ones a
person would give, and that the PDFium path gives the same answers as MuPDF's.

Until the PDFium branch of `_Visibility` exists, the second half of this passes trivially - both
paths run the same MuPDF code. Once it exists, break the branch and this must fail.
"""

import os
import tempfile

import pymupdf
import pytest

from truedoc.extract import render
from truedoc.extract.textlayer import extract_page

_SWITCHES = ("TRUEDOC_READER", "TRUEDOC_RENDERER", "TRUEDOC_OBJECTS")

# One word of each kind. "Buried" is drawn first and a black box painted over it afterwards;
# "Snow" is white on the white page; "Ghost" is drawn in render mode 3.
_CONTENT = (
    b"BT /F1 12 Tf 0 Tr 0 0 0 rg 50 700 Td (Visible) Tj ET\n"
    b"BT /F1 12 Tf 3 Tr 0 0 0 rg 50 650 Td (Ghost) Tj ET\n"
    b"BT /F1 12 Tf 0 Tr 0 0 0 rg 50 600 Td (Buried) Tj ET\n"
    b"0 0 0 rg 40 590 120 30 re f\n"
    b"BT /F1 12 Tf 0 Tr 1 1 1 rg 50 550 Td (Snow) Tj ET\n"
)


def _pdf() -> bytes:
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 800] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(_CONTENT)).encode() + b" >>\nstream\n" + _CONTENT + b"\nendstream",
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


def _reasons(pdfium: bool) -> tuple[dict, list]:
    """{hidden run text: reason} and the visible words, read one way or the other."""
    was = {k: os.environ.pop(k, None) for k in _SWITCHES}
    if pdfium:
        os.environ.update({"TRUEDOC_READER": "pdftext", "TRUEDOC_RENDERER": "pdfium",
                           "TRUEDOC_OBJECTS": "pdfium"})
    fd, path = tempfile.mkstemp(suffix=".pdf")
    with os.fdopen(fd, "wb") as fh:
        fh.write(_pdf())
    doc = pymupdf.open(path)
    try:
        page = extract_page(doc[0], 1)
        hidden = {h["text"].strip(): h["reason"] for h in page.hidden_text}
        visible = sorted(w.text for w in page.words)
        return hidden, visible
    finally:
        render.close_documents()
        doc.close()
        os.unlink(path)
        for k, v in was.items():
            os.environ.pop(k, None)
            if v is not None:
                os.environ[k] = v


def test_each_kind_of_hidden_text_gets_the_reason_a_person_would_give():
    hidden, visible = _reasons(pdfium=False)
    assert visible == ["Visible"], (visible, hidden)
    assert hidden.get("Ghost") == "invisible", hidden
    assert hidden.get("Buried") == "covered", hidden
    assert hidden.get("Snow") == "same-colour", hidden


@pytest.mark.skipif(not render.available(), reason="pypdfium2 not installed")
def test_pdfium_finds_the_same_hidden_text_for_the_same_reasons():
    """The D022 quantity: which characters are hidden, and why, must not depend on the reader."""
    mu_hidden, mu_visible = _reasons(pdfium=False)
    pf_hidden, pf_visible = _reasons(pdfium=True)
    assert pf_visible == mu_visible, (pf_visible, mu_visible)
    assert pf_hidden == mu_hidden, (pf_hidden, mu_hidden)
