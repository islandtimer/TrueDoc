"""A table the text built across the cells its page draws is read again from the drawing.

GIO's home PDS page 26 draws its limits table as filled cells, and the table built from its text lines ran the header's
second band into the first line of every Jewellery limit and cut "Paintings ... art objects" into two items. The drawing
is the table's own grid: where words of one text cell lie on both sides of a drawn cell edge, the cells the page draws
replace the table, header marked and spans kept (written as HTML, since a pipe table would repeat a spanning cell's text
in every column); a text table that agrees with its drawing is left as it is.
"""
import pymupdf

from truedoc.extract.handle import open_pdf
from truedoc.extract.textlayer import extract_page
from truedoc.model import BBox, Block, BlockKind, Table, TableCell
from truedoc.render.okf import render_table
from truedoc.tables import fill_grid

BLUE, GREY = (0.0, 0.29, 0.6), (0.92, 0.92, 0.93)


def _page(tmp_path, band=False):
    """Item | Limit on a blue header band - under a blue band spanning both columns, when asked - and two body rows,
    their Limit cells grey, a rule under each row."""
    doc = pymupdf.open()
    page = doc.new_page(width=400, height=300)
    if band:
        page.draw_rect(pymupdf.Rect(40, 20, 360, 40), color=None, fill=BLUE)
        page.insert_text((120, 35), "Limits for any one incident", fontsize=9)
    for x0, x1 in ((40, 200), (200, 360)):
        page.draw_rect(pymupdf.Rect(x0, 40, x1, 60), color=None, fill=BLUE)
    page.draw_rect(pymupdf.Rect(200, 60, 360, 100), color=None, fill=GREY)
    page.draw_rect(pymupdf.Rect(200, 100, 360, 130), color=None, fill=GREY)
    for y in (100, 130):
        page.draw_line((40, y), (360, y), color=(0.6, 0.6, 0.6), width=0.5)
    for x, y, text in ((45, 55, "Item"), (205, 55, "Limit"),
                       (45, 75, "Paintings, pictures,"), (45, 90, "antiques and art"),
                       (205, 75, "$10,000 per item"), (205, 90, "or $50,000 in total"),
                       (45, 118, "Jewellery"), (205, 118, "$2,000")):
        page.insert_text((x, y), text, fontsize=9)
    path = tmp_path / "drawn.pdf"
    doc.save(str(path))
    doc.close()
    return str(path)


def _text_table(rows, n_cols=2):
    """A table as a text finder might build it: rows of (text, box) cells."""
    cells = [TableCell(text=t, row=r, col=c, bbox=BBox(*box))
             for r, row in enumerate(rows) for c, (t, box) in enumerate(row)]
    bbox = BBox.union_all(cell.bbox for cell in cells)
    table = Table(n_rows=len(rows), n_cols=n_cols, cells=cells, bbox=bbox, provenance="layout-table")
    return Block(kind=BlockKind.TABLE, bbox=bbox, table=table, provenance="layout-table")


def _rows(block):
    t = block.table
    grid = [[""] * t.n_cols for _ in range(t.n_rows)]
    for c in t.cells:
        grid[c.row][c.col] = c.text
    return grid


def _redraw(path, blocks):
    doc = open_pdf(path)
    try:
        page = extract_page(doc[0], 1)
        return fill_grid.redraw_tables(page, doc[0], blocks)
    finally:
        doc.close()


CROSSED = [
    [("Item Paintings, pictures,", (40, 45, 200, 80)), ("Limit $10,000 per item", (200, 45, 360, 80))],
    [("antiques and art", (40, 84, 200, 95)), ("or $50,000 in total", (200, 84, 360, 95))],
    [("Jewellery", (40, 110, 200, 120)), ("$2,000", (200, 110, 360, 120))],
]


def test_a_table_built_across_its_drawn_cells_is_read_from_them(tmp_path):
    out = _redraw(_page(tmp_path), [_text_table(CROSSED)])
    assert len(out) == 1 and out[0].provenance == "drawn-cells"
    assert _rows(out[0]) == [["Item", "Limit"],
                             ["Paintings, pictures, antiques and art", "$10,000 per item or $50,000 in total"],
                             ["Jewellery", "$2,000"]]
    assert [c.is_header for c in out[0].table.cells if c.row == 0] == [True, True]


def test_a_drawn_cell_spanning_columns_keeps_its_span(tmp_path):
    band = [[("Limits for any one incident", (40, 22, 360, 38))]] + CROSSED
    out = _redraw(_page(tmp_path, band=True), [_text_table(band)])
    assert len(out) == 1 and out[0].provenance == "drawn-cells"
    table = out[0].table
    top = [c for c in table.cells if c.row == 0]
    assert [(c.text, c.colspan) for c in top] == [("Limits for any one incident", 2)]
    assert table.has_merged
    html = render_table(table)
    assert 'colspan="2"' in html and html.count("Limits for any one incident") == 1


def test_a_table_that_agrees_with_its_drawing_is_left_alone(tmp_path):
    agreeing = _text_table([
        [("Item", (40, 45, 200, 58)), ("Limit", (200, 45, 360, 58))],
        [("Paintings, pictures, antiques and art", (40, 65, 200, 95)),
         ("$10,000 per item or $50,000 in total", (200, 65, 360, 95))],
        [("Jewellery", (40, 110, 200, 120)), ("$2,000", (200, 110, 360, 120))],
    ])
    blocks = [agreeing]
    assert _redraw(_page(tmp_path), blocks) is blocks
