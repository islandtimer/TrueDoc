"""Text kept as a picture on a digital page is read with OCR and stands in for the picture."""

import pymupdf
import yaml

from truedoc.pipeline import ConvertOptions, convert

SIDEBAR = [
    "The guidelines set a series of mandatory and recommended",
    "actions designed to reduce the use of harmful cleaning",
    "products in schools and to protect the health of the",
    "children and the staff who work in the buildings every day.",
    "Schools should keep records of the products they use and",
    "train the people who clean with them at least once a year.",
]


def _text_pixmap():
    doc = pymupdf.open()
    page = doc.new_page(width=320, height=140)
    y = 22
    for line in SIDEBAR:
        page.insert_text((10, y), line, fontsize=10)
        y += 18
    pix = page.get_pixmap(matrix=pymupdf.Matrix(3, 3), alpha=False)
    doc.close()
    return pix


def _pdf(tmp_path):
    doc = pymupdf.open()
    page = doc.new_page(width=600, height=500)
    page.insert_text((40, 60), "State policies vary considerably, as the box below explains.", fontsize=11)
    page.insert_image(pymupdf.Rect(60, 100, 380, 240), pixmap=_text_pixmap())
    page.insert_text((40, 300), "Most states leave the choice of products to the districts.", fontsize=11)
    path = tmp_path / "sidebar.pdf"
    doc.save(str(path))
    doc.close()
    return str(path)


def test_text_inside_a_picture_is_read(tmp_path):
    md = convert(_pdf(tmp_path), ConvertOptions(layout=False, ocr=True, ocr_pictures=True))
    _, fm, body = md.split("---\n", 2)
    meta = yaml.safe_load(fm)
    assert "mandatory and recommended" in body, body
    assert "harmful cleaning" in body and "once a year" in body, body
    assert "![](figure)" not in body
    assert body.index("vary considerably") < body.index("mandatory") < body.index("Most states")
    regions = meta["truedoc"]["ocr_regions"]
    assert len(regions) == 1 and regions[0]["page"] == 1 and regions[0]["words"] >= 40


def test_a_picture_without_text_stays_a_figure(tmp_path):
    doc = pymupdf.open()
    page = doc.new_page(width=600, height=500)
    page.insert_text((40, 60), "The photograph below shows the harbour at dawn.", fontsize=11)
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 120, 80), 0)
    pix.clear_with(90)
    page.insert_image(pymupdf.Rect(60, 100, 380, 300), pixmap=pix)
    path = tmp_path / "photo.pdf"
    doc.save(str(path))
    doc.close()
    md = convert(str(path), ConvertOptions(layout=False, ocr=True, ocr_pictures=True))
    assert "![](figure)" in md
    assert "ocr_regions" not in md
