"""The head strip of a page belongs to running heads, except a table's own heading row.

The aligned finder leaves the top and bottom 9% of the page to running heads and feet. Rows of
several cells alone in that strip are not a table: a document-control stamp ("issued: |
2019-04-17", "supersedes: | Revision 1", "reviewed: | --", "dated: | 2016-09-06") is furniture,
and reading it as a table cost five checks in run 50. The one exception is the heading row of a
table that starts in the strip, sitting within a line of the table's first body row.
"""
from truedoc.model import BBox, Char, Line, Page, Word
from truedoc.tables.aligned import find_aligned_tables

SIZE = 9.0


def _seg(text, x0, x1, y0):
    cw = (x1 - x0) / max(1, len(text))
    chars = [Char(text=c, bbox=BBox(x0 + i * cw, y0, x0 + (i + 1) * cw, y0 + SIZE), font="F", size=SIZE, origin_y=y0 + 0.8 * SIZE) for i, c in enumerate(text)]
    words = [Word(text=text, bbox=BBox(x0, y0, x1, y0 + SIZE), chars=chars)]
    return Line(words=words, bbox=BBox(x0, y0, x1, y0 + SIZE))


def _page(lines):
    page = Page(number=1, width=612, height=792)
    page.lines = lines
    page.body_font_size = SIZE
    return page


def test_a_document_control_stamp_in_the_head_strip_is_not_a_table():
    rows = [
        [("Revision 2", 400, 450), ("issued:", 470, 500), ("2019-04-17", 510, 560)],
        [("supersedes:", 470, 520), ("Revision 1", 530, 580)],
        [("reviewed:", 470, 515), ("--", 530, 540)],
        [("dated:", 470, 500), ("2016-09-06", 510, 560)],
    ]
    lines = []
    for i, row in enumerate(rows):
        y = 20 + 10 * i          # all four rows sit inside the top 9% of a 792 pt page
        lines.extend(_seg(t, x0, x1, y) for t, x0, x1 in row)
    body = [_seg("The committee met to review the annual report and its findings on the matters raised", 40, 560, 140 + 12 * i) for i in range(4)]
    lines.extend(body)
    tables, remaining = find_aligned_tables(_page(lines), lines, SIZE)
    assert tables == []
    assert len(remaining) == len(lines)


def test_a_banner_above_a_table_is_not_its_heading():
    # A report's banner (wide centred titles in two rows) right above a table:
    # its cells do not start on the table's columns (a campus report lost a
    # check to this in run 50).
    banner = [_seg("District Name: NORTH EAST ISD", 60, 230, 50), _seg("Texas 2016-17 Campus", 300, 420, 50), _seg("Performance Report", 480, 590, 50),
              _seg("Campus Name: STONE OAK EL", 60, 220, 61), _seg("Academic Profile", 300, 400, 61), _seg("Total Students: 849", 480, 580, 61)]
    body = [
        [("Indicator", 40, 90), ("Campus", 250, 290), ("District", 380, 430), ("State", 520, 550)],
        [("Attendance Rate", 40, 120), ("96.4%", 250, 280), ("95.9%", 380, 410), ("95.7%", 520, 550)],
        [("Dropout Rate", 40, 105), ("1.9%", 250, 275), ("2.1%", 380, 405), ("2.4%", 520, 545)],
        [("Graduation Rate", 40, 125), ("94.0%", 250, 280), ("91.2%", 380, 410), ("89.1%", 520, 550)],
    ]
    lines = list(banner)
    for i, row in enumerate(body):
        lines.extend(_seg(t, x0, x1, 76 + 12 * i) for t, x0, x1 in row)
    tables, remaining = find_aligned_tables(_page(lines), lines, SIZE)
    assert len(tables) == 1
    t = tables[0].table
    assert t.n_rows == 4
    assert [c.text for c in t.cells if c.row == 0] == ["Indicator", "Campus", "District", "State"]
    assert all(l in remaining for l in banner)


def test_heading_row_with_a_column_the_body_leaves_empty_still_joins():
    # "# | Attribute | Description" over rows whose first column is empty: two
    # of the three heading cells start on the body's columns, and that is
    # enough (a capability list lost its heading in run 51).
    lines = [_seg("#", 45, 50, 62), _seg("Attribute", 90, 140, 62), _seg("Description", 250, 310, 62)]
    body = [
        [("1", 45, 50), ("driverTypeAddress", 90, 180), ("Address of the Driver Type", 250, 400)],
        [("serial", 90, 120), ("Serial number of the driver", 250, 400)],
        [("2", 45, 50), ("projectID", 90, 140), ("Name of the Project / Tender", 250, 410)],
        [("firmwareVersion", 90, 170), ("Version of the driver hardware firmware", 250, 460)],
    ]
    for i, row in enumerate(body):
        lines.extend(_seg(t, x0, x1, 76 + 16 * i) for t, x0, x1 in row)   # ruled rows, padded: no wrapped-row folds
    tables, _ = find_aligned_tables(_page(lines), lines, SIZE)
    assert len(tables) == 1
    t = tables[0].table
    heading = [c.text for c in t.cells if c.row == 0]
    assert "Attribute" in heading and "Description" in heading
    assert t.n_rows == 5


def test_heading_and_first_data_row_both_in_the_strip_join_the_table():
    # The capability list of run 51: running head at the page's edge, then the
    # heading row, then the first data row, all inside the strip, the rest of
    # the table below it. The data row joins the body; the heading joins through it.
    head = [_seg("15/2/23, 9:34", 26, 69, 16), _seg("Schreder Hyperion CapabilityList", 147, 400, 16)]
    heading = [_seg("#", 64, 70, 33), _seg("Attribute", 83, 128, 33), _seg("Description", 209, 269, 33)]
    rows = [
        (55, [("1", 64, 70), ("driverTypeAddress", 83, 173), ("Address of the Driver Type", 209, 338)]),
        (79, [("2", 64, 70), ("serial", 83, 108), ("Serial number of the driver", 209, 338)]),
        (102, [("3", 64, 70), ("projectID", 83, 127), ("Name of the Project / Tender", 209, 349)]),
        (124, [("4", 64, 70), ("firmwareVersion", 83, 161), ("Version of the driver hardware firmware", 209, 420)]),
        (147, [("5", 64, 70), ("manufactureYear", 83, 170), ("Year of manufacture of the driver", 209, 400)]),
    ]
    lines = head + heading
    for y, row in rows:
        lines.extend(_seg(t, x0, x1, y) for t, x0, x1 in row)
    page = _page(lines)
    page.height = 841
    tables, remaining = find_aligned_tables(page, lines, 11.0)
    assert len(tables) == 1
    t = tables[0].table
    top = [c.text for c in t.cells if c.row == 0]
    assert "Attribute" in top and "Description" in top
    assert t.n_rows == 6
    assert all(l in remaining for l in head)


def test_heading_row_in_the_strip_above_a_table_belongs_to_it():
    # A continued table whose heading row sits inside the top strip, its body
    # just below it ("Category | Region | Phenotype" over "LTP | hippocampus |
    # ..."): the heading is a row of the table, not a running head (a
    # neuroscience table lost its heading in run 49).
    lines = [_seg("Category", 40, 90, 62), _seg("Region", 150, 190, 62), _seg("Phenotype", 250, 300, 62), _seg("Age", 400, 420, 62)]
    body = [
        [("mGluR LTD", 40, 95), ("hippocampus", 150, 210), ("enhanced", 250, 295), ("4-12 wk", 400, 440)],
        [("LTP", 40, 60), ("hippocampus", 150, 210), ("NONE", 250, 280), ("20-26 wk", 400, 445)],
        [("L-LTP", 40, 70), ("hippocampus", 150, 210), ("NONE", 250, 280), ("5-7 wk", 400, 435)],
        [("LTP", 40, 60), ("cerebellum", 150, 205), ("deficient", 250, 295), ("2 wk", 400, 425)],
    ]
    for i, row in enumerate(body):
        y = 76 + 12 * i     # the first body row starts just under the 9% strip of a 792 pt page
        lines.extend(_seg(t, x0, x1, y) for t, x0, x1 in row)
    tables, _ = find_aligned_tables(_page(lines), lines, SIZE)
    assert len(tables) == 1
    t = tables[0].table
    assert t.n_rows == 5
    assert [c.text for c in t.cells if c.row == 0] == ["Category", "Region", "Phenotype", "Age"]
    assert all(c.is_header for c in t.cells if c.row == 0)
