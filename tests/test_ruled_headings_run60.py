"""Ruled tables after run 60: tall cells that stay whole, and heading rows beyond the first.

Run 60 dealt every tall cell's lines to the rows it spans and lost four checks to cells that are
one cell: a heading over two heading rows ("Minimum Central Pressure (mb)" beside "Landfall
Location" over "Longitude | Latitude"), a realtors' note beside two value rows, a label centred
in a cell over empty rows. Such a cell now spans its rows. It also marked only the first row of
an HTML table as headings and lost four checks to a title row over the column headings: every
row above the first row of values is a heading row.
"""
import pymupdf

from truedoc.render.okf import render_table
from truedoc.tables.ruled import find_ruled_tables


def _cells(table):
    return {(c.row, c.col): c for c in table.cells}


def _two_tier_heading(path):
    doc = pymupdf.open()
    page = doc.new_page(width=612, height=792)
    page.draw_rect(pymupdf.Rect(100, 100, 500, 190), width=0.8)
    for x in (200, 300):
        page.draw_line((x, 100), (x, 190), width=0.8)          # Storm | Pressure | Landfall
    page.draw_line((400, 130), (400, 190), width=0.8)          # Longitude | Latitude, under Landfall Location
    page.draw_line((300, 130), (500, 130), width=0.8)          # under Landfall Location only
    for y in (150, 170):
        page.draw_line((100, y), (500, y), width=0.8)
    page.insert_text((110, 116), "Storm", fontsize=9)
    page.insert_text((110, 136), "Number", fontsize=9)
    page.insert_text((210, 116), "Minimum Central", fontsize=9)
    page.insert_text((210, 136), "Pressure (mb)", fontsize=9)
    page.insert_text((340, 118), "Landfall Location", fontsize=9)
    page.insert_text((310, 143), "Longitude", fontsize=9)
    page.insert_text((410, 143), "Latitude", fontsize=9)
    for i, vals in enumerate((("1", "960", "-91.2", "29.5"), ("2", "930", "-90.4", "29.5"))):
        y = 164 + 20 * i
        for x, v in zip((110, 210, 310, 410), vals):
            page.insert_text((x, y), v, fontsize=9)
    doc.save(str(path))
    doc.close()


def test_heading_over_two_heading_rows_spans_them(tmp_path):
    path = tmp_path / "storms.pdf"
    _two_tier_heading(path)
    t = find_ruled_tables(pymupdf.open(str(path))[0])[0].table
    cells = _cells(t)
    assert cells[(0, 1)].text == "Minimum Central Pressure (mb)" and cells[(0, 1)].rowspan == 2 and cells[(0, 1)].is_header
    assert (1, 1) not in cells and (1, 0) not in cells
    assert cells[(0, 2)].text == "Landfall Location" and cells[(0, 2)].colspan == 2
    assert cells[(1, 2)].text == "Longitude" and cells[(1, 2)].is_header
    assert cells[(1, 3)].text == "Latitude" and cells[(1, 3)].is_header
    assert not cells[(2, 0)].is_header
    html = render_table(t)
    assert '<th rowspan="2">Minimum Central Pressure (mb)</th>' in html
    assert "<th>Longitude</th>" in html and "<td>960</td>" in html


def _note_beside_rows(path):
    doc = pymupdf.open()
    page = doc.new_page(width=612, height=792)
    page.draw_rect(pymupdf.Rect(100, 100, 500, 160), width=0.8)
    for x in (200, 300):
        page.draw_line((x, 100), (x, 160), width=0.8)
    page.draw_line((100, 120), (500, 120), width=0.8)
    page.draw_line((100, 140), (300, 140), width=0.8)          # the note's cell has no row rule
    for x, h in zip((110, 210, 310), ("Period", "Florida", "Note")):
        page.insert_text((x, 114), h, fontsize=9)
    page.insert_text((110, 134), "2022 - Mar", fontsize=9)
    page.insert_text((210, 134), "3.9%", fontsize=9)
    page.insert_text((110, 154), "Prior 12 months", fontsize=9)
    page.insert_text((210, 154), "1.4%", fontsize=9)
    for i, line in enumerate(("Realtors expect higher price growth.", "Their expectations are also higher", "than a year ago.")):
        page.insert_text((306, 131 + 11 * i), line, fontsize=8)
    doc.save(str(path))
    doc.close()


def test_note_beside_two_value_rows_is_one_cell(tmp_path):
    path = tmp_path / "note.pdf"
    _note_beside_rows(path)
    t = find_ruled_tables(pymupdf.open(str(path))[0])[0].table
    cells = _cells(t)
    note = cells[(1, 2)]
    assert note.text.startswith("Realtors expect higher price growth.") and note.text.endswith("than a year ago.")
    assert note.rowspan == 2 and (2, 2) not in cells
    assert cells[(2, 0)].text == "Prior 12 months" and cells[(2, 1)].text == "1.4%"
    md = render_table(t)
    assert md.count("Realtors expect") == 1 and "| Prior 12 months | 1.4% |  |" in md


def _centred_labels(path):
    doc = pymupdf.open()
    page = doc.new_page(width=612, height=792)
    page.draw_rect(pymupdf.Rect(100, 100, 500, 240), width=0.8)
    page.draw_line((200, 100), (200, 240), width=0.8)
    page.draw_line((100, 120), (500, 120), width=0.8)
    page.draw_line((100, 180), (500, 180), width=0.8)          # between the two label cells
    for y in (140, 160, 200, 220):
        page.draw_line((200, y), (500, y), width=0.8)          # the value column's rows only
    page.insert_text((110, 114), "Dimension", fontsize=9)
    page.insert_text((210, 114), "Strengths", fontsize=9)
    page.insert_text((104, 153), "a. Community-based", fontsize=8)    # centred in its tall cell
    page.insert_text((104, 213), "b. Mobile outreach", fontsize=8)
    doc.save(str(path))
    doc.close()


def test_label_centred_in_a_tall_cell_keeps_its_first_row(tmp_path):
    path = tmp_path / "labels.pdf"
    _centred_labels(path)
    t = find_ruled_tables(pymupdf.open(str(path))[0])[0].table
    cells = _cells(t)
    assert cells[(1, 0)].text == "a. Community-based" and cells[(1, 0)].rowspan == 3
    assert cells[(4, 0)].text == "b. Mobile outreach" and cells[(4, 0)].rowspan == 3
    assert (2, 0) not in cells and (3, 0) not in cells


def _titled_table(path):
    doc = pymupdf.open()
    page = doc.new_page(width=612, height=792)
    page.draw_rect(pymupdf.Rect(100, 100, 500, 200), width=0.8)
    for y in (120, 140, 160, 180):
        page.draw_line((100, y), (500, y), width=0.8)
    for x in (250, 350):
        page.draw_line((x, 120), (x, 140), width=0.8)          # column rules: the heading row ...
        page.draw_line((x, 160), (x, 200), width=0.8)          # ... and the value rows, not the title or the group label
    page.insert_text((110, 114), "Effet de Groupe pour DQ3", fontsize=9)
    for x, h in zip((110, 260, 360), ("Langue", "DF", "F Value")):
        page.insert_text((x, 134), h, fontsize=9)
    page.insert_text((110, 154), "PRE (6/4/18) / POST II (6/23/18)", fontsize=9)
    for i, vals in enumerate((("Anglais", "2", "2.51"), ("Francais", "2", "2.05"))):
        for x, v in zip((110, 260, 360), vals):
            page.insert_text((x, 174 + 20 * i), v, fontsize=9)
    doc.save(str(path))
    doc.close()


def test_rows_above_the_values_are_heading_rows(tmp_path):
    path = tmp_path / "titled.pdf"
    _titled_table(path)
    t = find_ruled_tables(pymupdf.open(str(path))[0])[0].table
    cells = _cells(t)
    assert cells[(0, 0)].text == "Effet de Groupe pour DQ3" and cells[(0, 0)].colspan == 3 and cells[(0, 0)].is_header
    assert all(cells[(1, c)].is_header for c in range(3)) and cells[(1, 2)].text == "F Value"
    assert cells[(2, 0)].text.startswith("PRE") and cells[(2, 0)].colspan == 3 and not cells[(2, 0)].is_header
    assert not cells[(3, 0)].is_header
    html = render_table(t)
    assert "<th>F Value</th>" in html and "<td>2.51</td>" in html
