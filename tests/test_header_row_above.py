"""A sentence above a table's box is not its header row, however well its words land on the columns.

The layout model's box often starts under a table's header row, so a line just above the box whose
words sit on the table's columns is taken as that header (`_header_lines_above`). Where a table's
columns tile the whole width - a Key Facts Sheet's label, answer and exclusions - every word of the
sentence above lands on some column, and "Any amounts you claim include GST less any input tax
credit..." became the first row of the table on three contents sheets. What separates the two is how
the line crosses a column boundary: a header row crosses on the gap between its cells, a sentence on
an ordinary word space.

Both directions are tested, because nothing else in the suite covers the header row the box missed.
The columns here sit close enough that, without the word-space test, the sentence is adopted.
"""
import pymupdf

from truedoc.layout.base import Region, RegionKind
from truedoc.layout.fuse import apply_layout
from truedoc.model import BBox, BlockKind
from truedoc.pipeline import ConvertOptions, process_page

COLUMNS = (40, 140, 190)
ROWS = [("Fire and Explosion", "Yes", "Excludes loss or damage caused by scorching"),
        ("Flood", "Optional", "Excludes damage by flood if you have chosen"),
        ("Storm", "Yes", "Excludes loss or damage caused by rain and hail"),
        ("Earthquake", "Yes", "Excludes damage more than 72 hours after the event")]


def _pdf(tmp_path, above):
    doc = pymupdf.open()
    page = doc.new_page(width=500, height=400)
    if isinstance(above, str):
        page.insert_text((40, 78), above, fontsize=10)
    else:
        for x, text in zip(COLUMNS, above):
            page.insert_text((x, 78), text, fontsize=10)
    for i, cells in enumerate(ROWS):
        for x, text in zip(COLUMNS, cells):
            page.insert_text((x, 100 + 20 * i), text, fontsize=10)
    path = tmp_path / "above.pdf"
    doc.save(str(path))
    doc.close()
    return str(path)


def _grid(path):
    pdf_page = pymupdf.open(path)[0]
    page = process_page(pdf_page, 1, ConvertOptions(layout=False, ocr=False, math=False, marks=False, tables=False))
    # The model's box starts under whatever sits on the line above the first row.
    region = Region(kind=RegionKind.TABLE, bbox=BBox(30, 86, 470, 180), score=0.9)
    blocks = apply_layout(page, list(page.blocks), [region], pdf_page=pdf_page, ocr=False)
    tables = [b for b in blocks if b.kind == BlockKind.TABLE and b.table is not None]
    assert tables, "no table built inside the region"
    return [[(c.text if c else "") for c in row] for row in tables[0].table.grid()]


def test_a_sentence_running_across_the_columns_is_not_adopted(tmp_path):
    grid = _grid(_pdf(tmp_path, "Any amounts you claim include GST less any input tax credit to which you are entitled"))
    assert not any("Any amounts" in cell for row in grid for cell in row), grid[0]
    assert grid[0][0] == "Fire and Explosion", grid[0]


def test_a_header_row_the_box_missed_is_still_adopted(tmp_path):
    grid = _grid(_pdf(tmp_path, ("Event/Cover", "Yes/No", "Some examples")))
    assert grid[0][:2] == ["Event/Cover", "Yes/No"], grid[0]
