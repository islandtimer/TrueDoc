"""A ruled box of body rows with its column headings printed unruled just above it."""

import pymupdf

from truedoc.pipeline import ConvertOptions, convert


def _boxed_row_pdf(tmp_path, with_header: bool):
    doc = pymupdf.open()
    page = doc.new_page(width=612, height=300)
    page.insert_text((36, 60), "Minutes of the meeting. The action items agreed are listed below.", fontsize=10)
    xs = [36, 342, 468, 567]
    y0, y1 = 120, 138
    if with_header:
        for x, h in zip(xs, ["Action Item", "Who Will Do", "Due Date"]):
            page.insert_text((x + 2, 112), h, fontsize=10)
    # the boxed single row: outer frame plus two column dividers
    page.draw_rect(pymupdf.Rect(xs[0], y0, xs[-1], y1), width=0.8)
    for x in xs[1:-1]:
        page.draw_line((x, y0), (x, y1), width=0.8)
    for x, cell in zip(xs, ["Revise Course Review List document", "Dr. Tresolini", "August 14, 2003"]):
        page.insert_text((x + 4, 132), cell, fontsize=10)
    page.insert_text((36, 180), "The next meeting is on August 14, 2003, in room 238.", fontsize=10)
    path = tmp_path / ("boxed_header.pdf" if with_header else "boxed.pdf")
    doc.save(str(path))
    doc.close()
    return str(path)


def test_headings_above_a_boxed_row_become_the_header(tmp_path):
    md = convert(_boxed_row_pdf(tmp_path, True), ConvertOptions(frontmatter=False, layout=False, ocr=False))
    assert "| Action Item | Who Will Do | Due Date |" in md, md
    assert "| Revise Course Review List document | Dr. Tresolini | August 14, 2003 |" in md, md
    assert "# Action Item" not in md


def test_a_boxed_header_row_over_unruled_body_rows_is_left_to_the_whitespace_finder(tmp_path):
    """A ruled box around the column names, with the body rows unruled below it,
    is the header of a bigger table; the line above the box (a group heading) is
    not adopted, and the box is not turned into a two-row table of its own."""
    doc = pymupdf.open()
    page = doc.new_page(width=400, height=400)
    xs = [40, 140, 240, 340]
    page.insert_text((60, 66), "most common classes", fontsize=10)
    page.insert_text((250, 66), "most common objects", fontsize=10)
    page.draw_rect(pymupdf.Rect(xs[0], 72, xs[-1], 90), width=0.8)
    for x in xs[1:-1]:
        page.draw_line((x, 72), (x, 90), width=0.8)
    for x, h in zip(xs, ["class", "count", "object"]):
        page.insert_text((x + 4, 85), h, fontsize=10)
    y = 104
    for row in (("seashore", "3554", "person"), ("alp", "2568", "car"), ("lakeside", "2446", "cup"), ("fountain", "2265", "bird")):
        for x, cell in zip(xs, row):
            page.insert_text((x + 4, y), cell, fontsize=10)
        y += 14
    path = tmp_path / "boxed_header.pdf"
    doc.save(str(path))
    doc.close()
    md = convert(str(path), ConvertOptions(frontmatter=False, layout=False, ocr=False))
    assert "| most common classes |" not in md, md
    assert "seashore" in md and "fountain" in md


def test_a_boxed_row_without_headings_is_not_a_table(tmp_path):
    md = convert(_boxed_row_pdf(tmp_path, False), ConvertOptions(frontmatter=False, layout=False, ocr=False))
    assert "| ---" not in md and "<table" not in md, md
    assert "Revise Course Review List document" in md and "Dr. Tresolini" in md
