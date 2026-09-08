"""Ruled tables whose label column has no row rules, and sub-heading rows spanning the values.

A statistical yearbook (904a1b4e in run 58, four checks) rules its value cells row by row but
leaves the label column as one tall cell: PyMuPDF's extractor puts every label on the first row
and None on the rows the cell spans. Each label belongs to the row its position falls in. The
same table sets "% da população" in one cell across the value columns: a group heading of the
rows beneath, which a reader takes as their heading; it becomes a spanning heading row.
"""
import pymupdf

from truedoc.tables.ruled import find_ruled_tables


def _draw_table(path):
    doc = pymupdf.open()
    page = doc.new_page(width=612, height=792)
    # Outer frame and column rules; the label column (100-260) has no row rules.
    page.draw_rect(pymupdf.Rect(100, 100, 500, 220), width=0.8)
    page.draw_line((260, 100), (260, 220), width=0.8)      # the label column's edge, full height
    for x in (340, 420):
        page.draw_line((x, 100), (x, 120), width=0.8)      # column rules stop at the sub-heading row ...
        page.draw_line((x, 140), (x, 220), width=0.8)      # ... and resume under it: one cell across the values
    page.draw_line((100, 120), (500, 120), width=0.8)      # under the year heading
    page.draw_line((100, 140), (500, 140), width=0.8)      # under the spanning sub-heading
    for y in (160, 180, 200):
        page.draw_line((260, y), (500, y), width=0.8)      # value rows only
    page.insert_text((280, 114), "1998", fontsize=9)
    page.insert_text((360, 114), "1999", fontsize=9)
    page.insert_text((440, 114), "2000", fontsize=9)
    page.insert_text((330, 134), "% da populacao", fontsize=9)
    labels = ["Taxa de actividade", "Taxa de emprego total", "Taxa de emprego, homens", "Taxa de emprego, mulheres"]
    values = [("62,8", "60,2", "62,2"), ("55,3", "53,2", "51,3"), ("61,7", "60,2", "57,4"), ("49,4", "47,7", "45,5")]
    for i, (lab, vals) in enumerate(zip(labels, values)):
        y = 154 + 20 * i
        page.insert_text((104, y), lab, fontsize=8)
        for x, v in zip((280, 360, 440), vals):
            page.insert_text((x, y), v, fontsize=9)
    doc.save(str(path))
    doc.close()


def test_labels_in_a_tall_unruled_cell_are_dealt_to_their_rows(tmp_path):
    path = tmp_path / "yearbook.pdf"
    _draw_table(path)
    doc = pymupdf.open(str(path))
    blocks = find_ruled_tables(doc[0])
    assert len(blocks) == 1
    t = blocks[0].table
    texts = {(c.row, c.col): c.text for c in t.cells}
    label_rows = [r for r in range(t.n_rows) if texts.get((r, 0), "").startswith("Taxa")]
    assert len(label_rows) == 4, texts
    r0 = label_rows[0]
    assert texts[(r0, 0)] == "Taxa de actividade" and texts[(r0, 1)] == "62,8"
    assert texts[(r0 + 2, 0)] == "Taxa de emprego, homens" and texts[(r0 + 2, 3)] == "57,4"


def test_sub_heading_spanning_the_value_columns_is_a_heading_row(tmp_path):
    path = tmp_path / "yearbook.pdf"
    _draw_table(path)
    doc = pymupdf.open(str(path))
    t = find_ruled_tables(doc[0])[0].table
    sub = [c for c in t.cells if c.text == "% da populacao"]
    assert len(sub) == 1
    assert sub[0].col == 1 and sub[0].colspan == 3 and sub[0].is_header
    assert t.has_merged
