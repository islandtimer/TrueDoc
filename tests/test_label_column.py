"""A column of labels is not a heading wrapping onto the rows below it.

QBE's financial services guide sets "Phone:", "Email:", "Online:", "Post:" down a column with their values beside
them. The first value - seven words, closing on no full stop - stood over an email address that starts in lower case,
which is what `_heading_wraps_on` looks for, so the heading fold folded three labels into one cell; the table was then
refused altogether and the page published the labels and the values as two paragraphs with nothing to pair them. A
colon closes what it follows, so where the row below fills a column whose cell above ends in one, it is a row of its
own. The same reading of a colon is already in `_label_carries_on` and in the merger's label branch.

The Key Facts Sheets' own interleaved heading - "... that apply to" over "Yes/No" over "Event/Cover | Optional |
events/covers ..." - must still fold, and one sheet (WFI's classic home building) lost its whole header to a wider
version of this guard before it was narrowed to the colon.
"""
import pymupdf

from truedoc.pipeline import ConvertOptions, convert
from truedoc.tables import aligned

OFF = ConvertOptions(layout=False, ocr=False, math=False, marks=False, tables=True, frontmatter=False)

HEADING = ["Some examples of specific conditions, exclusions or limits that apply to",
           "events/covers (see PDS and other policy documentation for details of others)*"]


def test_a_column_of_labels_is_not_a_heading_wrapping():
    grid = [["Phone:", "1300 650 503 (Monday to Friday, 9am-5pm AEST/AEDT)"],
            ["Email:", "complaints@qbe.com"]]
    assert aligned._heading_wraps_on(grid, 0) is False


def test_a_heading_still_wraps_where_the_rows_below_leave_its_other_columns_alone():
    grid = [["", "Yes/No", HEADING[0]],
            ["Event/Cover", "Optional", HEADING[1]]]
    assert aligned._heading_wraps_on(grid, 0) is True


def test_a_label_ending_in_a_colon_does_not_stop_its_own_column_wrapping():
    """The guard is about the *other* columns: a cell may still carry on in the column that wraps."""
    grid = [["Cover:", "a long heading that carries on past the end of this line and does not stop"],
            ["", "here, but goes on"]]
    assert aligned._heading_wraps_on(grid, 0) is True


def _pdf(tmp_path):
    doc = pymupdf.open()
    page = doc.new_page(width=420, height=300)
    page.insert_text((57, 60), "How to contact us", fontsize=11)
    rows = [("Phone:", "1300 650 503 (Monday to Friday, 9am-5pm AEST/AEDT)"),
            ("Email:", "complaints@example.com"),
            ("Online:", "example.com/complaints"),
            ("Post:", "Customer Relations")]
    for i, (label, value) in enumerate(rows):
        y = 100 + 18 * i
        page.insert_text((62, y), label, fontsize=9)
        page.insert_text((119, y), value, fontsize=9)
    path = tmp_path / "contact.pdf"
    doc.save(str(path))
    doc.close()
    return str(path)


def test_each_label_keeps_its_own_value(tmp_path):
    md = convert(_pdf(tmp_path), OFF)
    assert "| Phone: | 1300 650 503 (Monday to Friday, 9am-5pm AEST/AEDT) |" in md, md
    assert "| Email: | complaints@example.com |" in md, md
    assert "| Online: | example.com/complaints |" in md, md
    assert "Phone: Email: Online:" not in md
