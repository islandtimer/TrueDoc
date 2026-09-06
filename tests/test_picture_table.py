"""A table drawn as a picture on an otherwise digital page is read by OCR of the region."""

import pymupdf

from truedoc.layout.base import Region, RegionKind
from truedoc.layout.fuse import apply_layout
from truedoc.model import BBox
from truedoc.pipeline import ConvertOptions, process_page


def _page_with_picture_table(tmp_path):
    # Draw the table into an image page, then place that image on a text page.
    src = pymupdf.open()
    p = src.new_page(width=300, height=120)
    rows = [("Product", "Units", "Price"), ("Apples", "120", "3.50"), ("Pears", "80", "4.25"), ("Plums", "45", "6.10")]
    for i, cells in enumerate(rows):
        for x, text in zip((20, 130, 220), cells):
            p.insert_text((x, 25 + 24 * i), text, fontsize=14)
    pix = p.get_pixmap(dpi=200)
    src.close()
    doc = pymupdf.open()
    page = doc.new_page(width=500, height=500)
    page.insert_text((40, 50), "Sales for the quarter are summarised in the table below.", fontsize=11)
    page.insert_image(pymupdf.Rect(40, 80, 460, 248), pixmap=pix)
    page.insert_text((40, 300), "All figures are in thousands and exclude returns.", fontsize=11)
    path = tmp_path / "picture_table.pdf"
    doc.save(str(path))
    doc.close()
    return str(path)


def test_picture_table_is_read_by_region_ocr(tmp_path):
    path = _page_with_picture_table(tmp_path)
    pdf_page = pymupdf.open(path)[0]
    page = process_page(pdf_page, 1, ConvertOptions(layout=False, ocr=True))
    # Stand in for the layout model with the picture's box as a confident table region.
    region = Region(kind=RegionKind.TABLE, bbox=BBox(40, 80, 460, 248), score=0.95)
    blocks = apply_layout(page, list(page.blocks), [region], pdf_page=pdf_page, ocr=True)
    tables = [b for b in blocks if b.kind.name == "TABLE" and b.table is not None]
    assert tables, "no table built from the picture"
    grid = [[(c.text if c else "") for c in row] for row in tables[0].table.grid()]
    flat = " ".join(" ".join(r) for r in grid)
    assert "Apples" in flat and "Plums" in flat and "4.25" in flat
    assert tables[0].provenance == "layout-table-ocr"
