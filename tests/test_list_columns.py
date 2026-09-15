"""Two lists set side by side are written as two lists, not as rows cut from their lines (D028).

POL1418DIR's page 13 sets a covered list beside a not-covered list with no boxes, and the text-built table cut each item
where it wraps and gave the second list's marks a column of their own. Read again column by column - a marks column
joined to its words, a lone label opening a section - each column is one list whose entries hold all their lines, and
the rebuilt table keeps exactly the words the cut one held.
"""
import pymupdf

from truedoc.extract.handle import open_pdf
from truedoc.extract.textlayer import extract_page
from truedoc.model import BBox, Table, TableCell
from truedoc.tables.list_columns import side_by_side

# (x, baseline, text): two bulleted lists side by side, the second with its bullets set apart from their words.
TEXT = [
    (40, 60, "What we cover"), (226, 60, "What we do not cover"),
    (40, 80, "Structures"),
    (40, 100, "• Your home buildings"), (226, 100, "•"), (240, 100, "Any hotel, motel or hostel"),
    (40, 114, "• Building infrastructure, including pipes,"), (240, 114, "or boarding house"),
    (46.3, 128, "cables and wires"), (226, 128, "•"), (240, 128, "Pontoons"),
    (40, 142, "• Garages and sheds"),
]
BANDS = ((38, 224), (224, 236), (236, 400))
ROWS = ((50, 64), (70, 84), (90, 104), (104, 118), (118, 132), (132, 146))
CUT = [  # as the aligned finder cuts them: a row to a line, the second list's bullets in a column of their own
    ["What we cover", "What we do not cover", None],
    ["Structures", "", ""],
    ["• Your home buildings", "•", "Any hotel, motel or hostel"],
    ["• Building infrastructure, including pipes,", "", "or boarding house"],
    ["cables and wires", "•", "Pontoons"],
    ["• Garages and sheds", "", ""],
]


def _page(tmp_path):
    doc = pymupdf.open()
    pdf_page = doc.new_page(width=420, height=200)
    for x, y, text in TEXT:
        pdf_page.insert_text((x, y), text, fontsize=10)
    path = tmp_path / "side.pdf"
    doc.save(str(path))
    doc.close()
    handle = open_pdf(str(path))
    try:
        return extract_page(handle[0], 1)
    finally:
        handle.close()


def _table(rows):
    cells = []
    for r, row in enumerate(rows):
        for c, text in enumerate(row):
            if text is None:
                continue
            span = 2 if r == 0 and c == 1 else 1
            cells.append(TableCell(text=text, row=r, col=c, colspan=span, is_header=(r == 0),
                                   bbox=BBox(BANDS[c][0], ROWS[r][0], BANDS[c + span - 1][1], ROWS[r][1])))
    return Table(n_rows=len(rows), n_cols=3, cells=cells, bbox=BBox(38, 50, 400, 146), provenance="textlayer-aligned")


def test_lists_set_side_by_side_are_rebuilt_as_lists(tmp_path):
    table = side_by_side(_page(tmp_path), _table(CUT), [])
    assert (table.n_rows, table.n_cols) == (3, 2)
    grid = {(c.row, c.col): c for c in table.cells}
    assert [grid[(0, 0)].text, grid[(0, 1)].text] == ["What we cover", "What we do not cover"]
    assert grid[(1, 0)].text == "Structures" and grid[(1, 0)].colspan == 2
    assert [i.text for i in grid[(2, 0)].listing.items] == [
        "Your home buildings", "Building infrastructure, including pipes, cables and wires", "Garages and sheds"]
    assert [i.text for i in grid[(2, 1)].listing.items] == ["Any hotel, motel or hostel or boarding house", "Pontoons"]
    assert table.has_merged


def test_a_table_holding_words_the_page_does_not_is_left_as_it_is(tmp_path):
    cut = [list(row) for row in CUT]
    cut[4][2] = "Pontoons and jetties"
    assert side_by_side(_page(tmp_path), _table(cut), []) is None
