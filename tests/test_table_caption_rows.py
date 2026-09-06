"""A caption swallowed by a layout model's table box is not the table's header row."""

import pymupdf

from truedoc.layout.base import Region, RegionKind
from truedoc.layout.fuse import apply_layout, caption_like
from truedoc.model import BBox, BlockKind
from truedoc.pipeline import ConvertOptions, process_page


def _page(tmp_path):
    doc = pymupdf.open()
    page = doc.new_page(width=500, height=400)
    page.insert_text((40, 60), "Table 2. Differentiating features between neuroretinitis and other closely resembling entities", fontsize=9)
    rows = [("Feature", "Neuroretinitis", "Papillitis"), ("Vision", "6/60-6/12", "6/36-6/6"), ("Pain", "Rare", "Common"), ("Onset", "Days", "Hours")]
    for i, cells in enumerate(rows):
        for x, text in zip((40, 200, 360), cells):
            page.insert_text((x, 90 + 20 * i), text, fontsize=10)
    page.insert_text((40, 200), "The two conditions are told apart mainly by the pattern of visual loss.", fontsize=10)
    path = tmp_path / "caption_table.pdf"
    doc.save(str(path))
    doc.close()
    return str(path)


def test_caption_above_the_table_box_is_not_adopted_as_its_header(tmp_path):
    pdf_page = pymupdf.open(_page(tmp_path))[0]
    page = process_page(pdf_page, 1, ConvertOptions(layout=False, ocr=False, math=False, marks=False, tables=False))
    # The model's box starts under the caption; the caption is the nearest line above it.
    region = Region(kind=RegionKind.TABLE, bbox=BBox(30, 70, 470, 160), score=0.9)
    blocks = apply_layout(page, list(page.blocks), [region], pdf_page=pdf_page, ocr=False)
    tables = [b for b in blocks if b.kind == BlockKind.TABLE and b.table is not None]
    assert tables, "no table built inside the region"
    grid = [[(c.text if c else "") for c in row] for row in tables[0].table.grid()]
    assert grid[0][:2] == ["Feature", "Neuroretinitis"], grid[0]
    assert not any("Table 2" in cell for row in grid for cell in row)
    texts = " ".join(b.text for b in blocks if b.kind != BlockKind.TABLE)
    assert "Table 2. Differentiating features" in texts


def test_caption_like_rules():
    from truedoc.model import Char, Line, Word

    def line(text, width):
        chars = [Char(text=ch, bbox=BBox(i, 0, i + 1, 10), font="F", size=10, origin_y=9) for i, ch in enumerate(text)]
        words = [Word(text=text, bbox=BBox(0, 0, width, 10), chars=chars)]
        return Line(words=words, bbox=BBox(0, 0, width, 10))

    assert caption_like(line("Table 3 Prematurity", 60), 400)
    assert caption_like(line("Observed mean home range size and mean proportion of exclusive area in founder females", 380), 400)
    assert not caption_like(line("Case Onset Duration Birthweight Gestation Comment", 380), 400)
    assert not caption_like(line("Antepartum haemorrhage. Irritable, lethargic baby, feeding poorly", 120), 400)
