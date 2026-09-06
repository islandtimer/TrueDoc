"""Tables whose cells wrap onto several lines (built as a small PDF, no layout model)."""

import pymupdf

from truedoc.pipeline import ConvertOptions, convert
from truedoc.tables.aligned import _continues


def test_continuation_rule():
    assert _continues("US Citizens and", "Permanent Residents")
    assert _continues("Please visit the", "program website")
    assert _continues("F (student) or J", "(exchange visitor)")
    assert not _continues("Permanent Residents", "International Applicants")
    assert not _continues("", "anything")


def test_wrapped_cells_stay_whole(tmp_path):
    doc = pymupdf.open()
    page = doc.new_page(width=500, height=400)
    page.insert_text((40, 40), "Deadlines for the coming year are listed below for each kind of applicant.", fontsize=9)
    rows = [
        (70, ["Type of Applicant", "Fall Deadline", "Spring Deadline"]),
        (86, ["Domestic Applicants", "", ""]),
        (100, ["US Citizens and", "Please visit the", "See the notes"]),
        (111, ["Permanent Residents", "program website", "below for details"]),
        (127, ["International Applicants", "Contact us", "Not offered"]),
        (141, ["Exchange Visitors", "March 1", "October 1"]),
        (155, ["Returning Students", "June 15", "January 15"]),
    ]
    for y, cells in rows:
        for x, text in zip((40, 210, 360), cells):
            if text:
                page.insert_text((x, y), text, fontsize=9)
    page.insert_text((40, 200), "Applicants who miss a deadline may apply for the following term instead.", fontsize=9)
    path = tmp_path / "wrapped.pdf"
    doc.save(str(path))
    doc.close()
    # The text-layer finder alone rejects wordy tables (they look like prose); a
    # layout region would vouch for this one, which is the trusted path.
    from truedoc.extract.textlayer import extract_page
    from truedoc.tables.aligned import table_from_lines

    page = extract_page(pymupdf.open(str(path))[0], 1)
    lines = [l for l in page.lines if 55 <= l.bbox.cy <= 165]
    table = table_from_lines(lines, page.body_font_size, trusted=True)
    assert table is not None
    grid = [[(c.text if c else "") for c in row] for row in table.grid()]
    assert grid[0] == ["Type of Applicant", "Fall Deadline", "Spring Deadline"]
    assert ["US Citizens and Permanent Residents", "Please visit the program website", "See the notes below for details"] in grid
    assert ["International Applicants", "Contact us", "Not offered"] in grid
    assert all(c.bbox is not None for c in table.cells)
