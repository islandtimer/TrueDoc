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
from truedoc.tables.cell_lists import BULLETS
from truedoc.tables.list_columns import _label_blocks, side_by_side

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


def test_a_heading_split_over_a_column_of_marks_is_the_heading_of_the_list(tmp_path):
    cut = [list(row) for row in CUT]
    cut[0] = ["What we cover", "What we", "do not cover"]
    cells = [TableCell(text=text, row=r, col=c, is_header=(r == 0), bbox=BBox(BANDS[c][0], ROWS[r][0], BANDS[c][1], ROWS[r][1]))
             for r, row in enumerate(cut) for c, text in enumerate(row) if text is not None]
    page = _page(tmp_path)
    table = side_by_side(page, Table(n_rows=6, n_cols=3, cells=cells, bbox=BBox(38, 50, 400, 146),
                                     provenance="textlayer-aligned"), [])
    grid = {(c.row, c.col): c for c in table.cells}
    assert [grid[(0, 0)].text, grid[(0, 1)].text] == ["What we cover", "What we do not cover"]
    # and a heading across the whole table heads both lists, once
    cells = [c for c in cells if c.row != 0] + [TableCell(text="Your home", row=0, col=0, colspan=3, is_header=True,
                                                           bbox=BBox(38, 50, 400, 64))]
    table = side_by_side(page, Table(n_rows=6, n_cols=3, cells=cells, bbox=BBox(38, 50, 400, 146),
                                     provenance="textlayer-aligned"), [])
    assert [(c.text, c.colspan) for c in table.cells if c.row == 0] == [("Your home", 2)]


def test_a_table_holding_words_the_page_does_not_is_left_as_it_is(tmp_path):
    cut = [list(row) for row in CUT]
    cut[4][2] = "Pontoons and jetties"
    assert side_by_side(_page(tmp_path), _table(cut), []) is None


# --- The same cut, more widely (D042) --------------------------------------------------------------------------------
# A covered list beside a not-covered list, a label set beside them, a heading row whose marks a drawn rule sets apart,
# a column opening with words before its entries and one closing with a note; each wrapped entry cut into rows of its
# own, and the other list's entries opening beside the cut.

WIDE = [
    (130, 80, "Covered"), (300, 80, "Not covered"),
    (40, 130, "Buildings"), (130, 130, "Your:"), (300, 130, "• buildings located outside"),
    (306.3, 144, "Australia"),
    (130, 150, "• main building"),
    (300, 164, "• caravans, trailers or their"),
    (130, 170, "• outbuildings, including sheds"),
    (306.3, 178, "accessories"),
    (136.3, 184, "and granny flats"),
    (300, 198, "• houseboats"),
    (130, 204, "• fixtures"),
    (130, 224, "at the property address"),
    (300, 240, "Continued next page..."),
]
WIDE_BANDS = ((36, 124), (124, 290), (290, 520))
WIDE_ROWS = [(72, 84)] + [(y - 10, y + 2) for y in (130, 144, 150, 164, 170, 178, 184, 198, 204, 224, 240)]
WIDE_CUT = [
    [None, "✓ Covered", "✗ Not covered"],
    ["Buildings", "Your:", "• buildings located outside"],
    [None, "", "Australia"],
    [None, "• main building", ""],
    [None, "", "• caravans, trailers or their"],
    [None, "• outbuildings, including sheds", ""],
    [None, "", "accessories"],
    [None, "and granny flats", ""],
    [None, "", "• houseboats"],
    [None, "• fixtures", ""],
    [None, "at the property address", ""],
    [None, "", "Continued next page..."],
]


def _wide_page(tmp_path, text, rules=(), short=()):
    doc = pymupdf.open()
    pdf_page = doc.new_page(width=560, height=300)
    for x, y, words in text:
        pdf_page.insert_text((x, y), words, fontsize=10)
    for y in rules:                      # drawn a column at a time, as the page draws them
        for x0, x1 in WIDE_BANDS:
            pdf_page.draw_line((x0, y), (x1, y), width=0.5)
    for y, band in short:                # a rule under one column only
        pdf_page.draw_line((WIDE_BANDS[band][0], y), (WIDE_BANDS[band][1], y), width=0.5)
    path = tmp_path / f"wide{len(list(tmp_path.glob('wide*.pdf')))}.pdf"       # the reader keeps the last file open
    doc.save(str(path))
    doc.close()
    handle = open_pdf(str(path))
    try:
        return extract_page(handle[0], 1)
    finally:
        handle.close()


def _wide_table(rows, row_boxes, label_rows=None):
    cells = []
    for r, row in enumerate(rows):
        for c, text in enumerate(row):
            if text is None:
                continue
            span = label_rows if (c == 0 and r == 1 and label_rows) else 1
            cells.append(TableCell(text=text, row=r, col=c, rowspan=span, is_header=(r == 0),
                                   bbox=BBox(WIDE_BANDS[c][0], row_boxes[r][0], WIDE_BANDS[c][1],
                                             row_boxes[r + span - 1][1])))
    return Table(n_rows=len(rows), n_cols=3, cells=cells, bbox=BBox(36, 70, 520, 245), provenance="textlayer-aligned")


def test_lists_under_a_label_beside_them_are_rebuilt_whole(tmp_path):
    page = _wide_page(tmp_path, WIDE, rules=(90,))
    table = side_by_side(page, _wide_table(WIDE_CUT, WIDE_ROWS, label_rows=11), [])
    assert (table.n_rows, table.n_cols) == (2, 3)
    grid = {(c.row, c.col): c for c in table.cells}
    assert [grid[(0, 1)].text, grid[(0, 2)].text] == ["✓ Covered", "✗ Not covered"] and grid[(0, 1)].is_header
    assert grid[(1, 0)].text == "Buildings"
    covered, not_covered = grid[(1, 1)].listing, grid[(1, 2)].listing
    assert covered.lead == "Your:" and covered.note == "at the property address"
    assert [i.text for i in covered.items] == ["main building", "outbuildings, including sheds and granny flats", "fixtures"]
    assert [i.text for i in not_covered.items] == [
        "buildings located outside Australia", "caravans, trailers or their accessories", "houseboats"]
    assert not_covered.note == "Continued next page..."
    # a label's span is the first column's; a cell spanning rows anywhere else is no list set side by side
    spanning = [list(row) for row in WIDE_CUT]
    spanning[1][2], spanning[2][2] = "• buildings located outside Australia", None
    table = _wide_table(spanning, WIDE_ROWS, label_rows=11)
    for c in table.cells:
        if (c.row, c.col) == (1, 2):
            c.rowspan = 2
    assert side_by_side(page, table, []) is None


# Two features divided by a rule drawn across the table: each is a row of its own.
FEATURES = [
    (130, 80, "We will"), (300, 80, "But not"),
    (40, 130, "Loss of rent"), (130, 130, "pay up to $25,000 towards:"), (300, 130, "fees charged for:"),
    (130, 144, "• the rent you lose; or"), (300, 150, "• cleaning or"),
    (130, 158, "• the rent you are expected"), (306.3, 164, "advertising"),
    (136.3, 172, "to lose"), (300, 178, "• managing the property"),
    (40, 220, "Removal of debris"), (130, 220, "the cost to remove debris"), (300, 220, "• trees not on the"),
    (306.3, 234, "property"),
]
FEATURE_ROWS = [(72, 84)] + [(y - 10, y + 2) for y in (130, 144, 150, 158, 164, 172, 178, 220, 234)]
FEATURE_CUT = [
    [None, "We will", "But not"],
    ["Loss of rent", "pay up to $25,000 towards:", "fees charged for:"],
    ["", "• the rent you lose; or", ""],
    ["", "", "• cleaning or"],
    ["", "• the rent you are expected", ""],
    ["", "", "advertising"],
    ["", "to lose", ""],
    ["", "", "• managing the property"],
    ["Removal of debris", "the cost to remove debris", "• trees not on the"],
    ["", "", "property"],
]


def test_a_rule_across_the_table_divides_its_rows(tmp_path):
    page = _wide_page(tmp_path, FEATURES, rules=(90, 200), short=((133, 2),))     # and one under a column only
    table = side_by_side(page, _wide_table(FEATURE_CUT, FEATURE_ROWS), [])
    # with no rule under the headings, a rule lower down still divides the rows and heads nothing; with no rule between
    # the features, their labels divide them
    for rules in ((200,), (90,)):
        assert _shape(side_by_side(_wide_page(tmp_path, FEATURES, rules=rules), _wide_table(FEATURE_CUT, FEATURE_ROWS),
                                   [])) == _shape(table)
    # and a first column that is no column of labels - it holds entries - is divided by the rule alone
    marked = FEATURES + [(40, 144, "• Buildings"), (40, 234, "• Contents")]
    cut = [list(row) for row in FEATURE_CUT]
    cut[2][0], cut[9][0] = "• Buildings", "• Contents"
    ruled = side_by_side(_wide_page(tmp_path, marked, rules=(90, 200)), _wide_table(cut, FEATURE_ROWS), [])
    grid = {(c.row, c.col): c for c in ruled.cells}
    words = lambda cell: " ".join(w for w in cell.text.split() if w not in BULLETS)
    assert ruled.n_rows == 3 and words(grid[(1, 0)]) == "Loss of rent Buildings" and words(grid[(2, 0)]) == "Removal of debris Contents"
    grid = {(c.row, c.col): c for c in table.cells}
    assert table.n_rows == 3
    assert [grid[(1, 0)].text, grid[(2, 0)].text] == ["Loss of rent", "Removal of debris"]
    assert grid[(1, 1)].listing.lead == "pay up to $25,000 towards:"
    assert [i.text for i in grid[(1, 1)].listing.items] == ["the rent you lose; or", "the rent you are expected to lose"]
    assert [i.text for i in grid[(1, 2)].listing.items] == ["cleaning or advertising", "managing the property"]
    assert grid[(2, 1)].text == "the cost to remove debris"
    one = grid[(2, 2)].text.split(" ", 1)                   # a single entry is no list: it keeps its bullet
    assert one[0] in BULLETS and one[1] == "trees not on the property" and grid[(2, 2)].listing is None


# A table of records: each row starts its cells level, and no entry carries on beside another's start.
RECORDS = [
    (40, 130, "Theft by a person who broke into"), (300, 130, "• up to $5,000 for each item"),
    (40, 144, "your home"),
    (40, 164, "Fire that started in the kitchen or"), (300, 164, "• up to the sum insured"),
    (40, 178, "anywhere else"),
    (40, 198, "Flood from a river over its banks"), (300, 198, "• only with flood cover"),
]
RECORD_BANDS = ((36, 290), (290, 520))
RECORD_CUT = [
    ["What happened", "What we pay"],
    ["Theft by a person who broke into", "• up to $5,000 for each item"],
    ["your home", ""],
    ["Fire that started in the kitchen or", "• up to the sum insured"],
    ["anywhere else", ""],
    ["Flood from a river over its banks", "• only with flood cover"],
]


def test_a_table_of_records_keeps_its_rows(tmp_path):
    page = _wide_page(tmp_path, [(40, 80, "What happened"), (300, 80, "What we pay")] + RECORDS)
    rows = [(72, 84)] + [(y - 10, y + 2) for y in (130, 144, 164, 178, 198)]
    cells = [TableCell(text=text, row=r, col=c, is_header=(r == 0),
                       bbox=BBox(RECORD_BANDS[c][0], rows[r][0], RECORD_BANDS[c][1], rows[r][1]))
             for r, row in enumerate(RECORD_CUT) for c, text in enumerate(row)]
    table = Table(n_rows=len(RECORD_CUT), n_cols=2, cells=cells, bbox=BBox(36, 70, 520, 205), provenance="textlayer-aligned")
    assert side_by_side(page, table, []) is None


def _shape(table):
    return [(c.row, c.col, c.text, c.is_header) for c in table.cells]


def test_labels_are_short_blocks_with_no_mark(tmp_path):
    labels = _label_blocks(_wide_page(tmp_path, FEATURES), BBox(36, 120, 124, 240), [])
    assert [words for _top, words in labels] == ["Loss of rent", "Removal of debris"]
    bullets = [(40, 130, "Loss of rent"), (40, 150, "• Buildings"), (40, 164, "• Contents")]
    assert _label_blocks(_wide_page(tmp_path, bullets), BBox(36, 120, 124, 240), []) is None
    prose = [(40, 130, "We will pay if"), (40, 144, "the loss occurs"), (40, 158, "to your home and"),
             (40, 172, "it cannot be lived in"), (40, 200, "Removal of debris")]
    assert _label_blocks(_wide_page(tmp_path, prose), BBox(36, 120, 124, 240), []) is None


# Lists side by side, each opening with words before its entries, and every entry on one line: nothing shows the rows
# are printed lines rather than records, and the table is left as the finder built it.
LEVEL = [(40, 80, "Covered"), (300, 80, "Not covered"),
         (40, 130, "Your:"), (300, 130, "Items:"), (40, 144, "• main building"), (300, 144, "• caravans"),
         (40, 158, "• sheds"), (300, 158, "• houseboats")]
LEVEL_CUT = [["Covered", "Not covered"], ["Your:", "Items:"], ["• main building", "• caravans"], ["• sheds", "• houseboats"]]


def test_lists_whose_entries_start_level_are_left_as_they_are(tmp_path):
    rows = [(72, 84)] + [(y - 10, y + 2) for y in (130, 144, 158)]
    cells = [TableCell(text=text, row=r, col=c, is_header=(r == 0),
                       bbox=BBox(RECORD_BANDS[c][0], rows[r][0], RECORD_BANDS[c][1], rows[r][1]))
             for r, row in enumerate(LEVEL_CUT) for c, text in enumerate(row)]
    table = Table(n_rows=4, n_cols=2, cells=cells, bbox=BBox(36, 70, 520, 165), provenance="textlayer-aligned")
    assert side_by_side(_wide_page(tmp_path, LEVEL), table, []) is None


def _two_columns(rows_text, baselines):
    rows = [(72, 84)] + [(y - 10, y + 2) for y in baselines]
    cells = [TableCell(text=text, row=r, col=c, is_header=(r == 0),
                       bbox=BBox(RECORD_BANDS[c][0], rows[r][0], RECORD_BANDS[c][1], rows[r][1]))
             for r, row in enumerate(rows_text) for c, text in enumerate(row)]
    return Table(n_rows=len(rows_text), n_cols=2, cells=cells, bbox=BBox(36, 70, 520, rows[-1][1] + 3),
                 provenance="textlayer-aligned")


def test_a_record_whose_entry_wraps_starts_level_with_the_next_cell_and_is_left_as_it_is(tmp_path):
    text = [(40, 80, "Covered"), (300, 80, "Not covered"), (40, 130, "Your:"), (300, 130, "Items:"),
            (40, 144, "• the main building and"), (300, 144, "• caravans"), (46.3, 158, "its garage"),
            (40, 172, "• sheds"), (300, 172, "• houseboats")]
    cut = [["Covered", "Not covered"], ["Your:", "Items:"], ["• the main building and", "• caravans"],
           ["its garage", ""], ["• sheds", "• houseboats"]]
    assert side_by_side(_wide_page(tmp_path, text), _two_columns(cut, (130, 144, 158, 172)), []) is None


def test_labels_beside_lists_whose_entries_start_level_are_left_as_they_are(tmp_path):
    text = [(40, 80, "Cover"), (130, 80, "Covered"), (300, 80, "Not covered"),
            (40, 130, "Theft"), (130, 130, "• jewellery"), (300, 130, "• cash"), (130, 144, "• tools"),
            (40, 170, "Fire"), (130, 170, "• smoke damage"), (300, 170, "• bushfire in the first"),
            (130, 184, "• scorching")]
    cut = [["Cover", "Covered", "Not covered"], ["Theft", "• jewellery", "• cash"], ["", "• tools", ""],
           ["Fire", "• smoke damage", "• bushfire in the first"], ["", "• scorching", ""]]
    rows = [(72, 84)] + [(y - 10, y + 2) for y in (130, 144, 170, 184)]
    cells = [TableCell(text=t, row=r, col=c, is_header=(r == 0),
                       bbox=BBox(WIDE_BANDS[c][0], rows[r][0], WIDE_BANDS[c][1], rows[r][1]))
             for r, row in enumerate(cut) for c, t in enumerate(row)]
    table = Table(n_rows=5, n_cols=3, cells=cells, bbox=BBox(36, 70, 520, 190), provenance="textlayer-aligned")
    assert side_by_side(_wide_page(tmp_path, text), table, []) is None


def test_a_wrapped_line_alone_in_its_row_carries_its_entry_on_and_heads_nothing(tmp_path):
    text = [(40, 80, "Covered"), (300, 80, "Not covered"),
            (40, 144, "• buildings located outside"), (300, 150, "• caravans, trailers"), (46.3, 158, "Australia"),
            (306.3, 164, "and boats"), (300, 178, "• houseboats"), (40, 186, "• sheds")]
    cut = [["Covered", "Not covered"], ["• buildings located outside", ""], ["", "• caravans, trailers"], ["Australia", ""],
           ["", "and boats"], ["", "• houseboats"], ["• sheds", ""]]
    table = side_by_side(_wide_page(tmp_path, text), _two_columns(cut, (144, 150, 158, 164, 178, 186)), [])
    assert table.n_rows == 2
    grid = {(c.row, c.col): c for c in table.cells}
    assert [i.text for i in grid[(1, 0)].listing.items] == ["buildings located outside Australia", "sheds"]
    assert [i.text for i in grid[(1, 1)].listing.items] == ["caravans, trailers and boats", "houseboats"]


def test_a_cell_of_several_marks_run_together_is_marks(tmp_path):
    cut = [list(row) for row in CUT]
    cut[2][1], cut[4][1] = "• •", ""                         # the finder ran the second list's two bullets together
    table = side_by_side(_page(tmp_path), _table(cut), [])
    assert (table.n_rows, table.n_cols) == (3, 2)


def test_a_line_opening_in_lower_case_heads_no_section(tmp_path):
    page = _wide_page(tmp_path, [(40, 80, "Covered"), (300, 80, "Not covered"),
                                 (40, 130, "• the main building and"), (300, 136, "• caravans, trailers"),
                                 (46.3, 144, "its garage"), (306.3, 150, "and boats"), (300, 164, "• houseboats"),
                                 (40, 178, "such as:"), (40, 192, "• sheds")])
    cut = [["Covered", "Not covered"], ["• the main building and", ""], ["", "• caravans, trailers"], ["its garage", ""],
           ["", "and boats"], ["", "• houseboats"], ["such as:", ""], ["• sheds", ""]]
    table = side_by_side(page, _two_columns(cut, (130, 136, 144, 150, 164, 178, 192)), [])
    assert table.n_rows == 2 and not any(c.colspan == 2 for c in table.cells)


def test_a_label_carried_on_below_is_one_label(tmp_path):
    page = _wide_page(tmp_path, [(40, 130, "Contents"), (40, 146, "(continued...)"), (40, 200, "Fixtures")])
    assert [words for _top, words in _label_blocks(page, BBox(36, 120, 124, 240), [])] == [
        "Contents (continued...)", "Fixtures"]


def test_an_entry_opening_inside_a_cell_and_carried_on_beside_another_start_is_a_cut(tmp_path):
    page = _wide_page(tmp_path, [(40, 80, "Covered"), (300, 80, "Not covered"),
                                 (40, 130, "Items used for homes and:"), (300, 130, "• trees"),
                                 (40, 144, "• if you are an owner, which"), (46.3, 158, "the body corporate insures"),
                                 (300, 158, "• soil")])
    cut = [["Covered", "Not covered"], ["Items used for homes and: • if you are an owner, which", "• trees"],
           ["the body corporate insures", "• soil"]]
    rows = [(72, 84), (120, 147), (148, 161)]                  # the finder's first row holds two printed lines
    cells = [TableCell(text=text, row=r, col=c, is_header=(r == 0),
                       bbox=BBox(RECORD_BANDS[c][0], rows[r][0], RECORD_BANDS[c][1], rows[r][1]))
             for r, row in enumerate(cut) for c, text in enumerate(row)]
    table = side_by_side(page, Table(n_rows=3, n_cols=2, cells=cells, bbox=BBox(36, 70, 520, 164),
                                     provenance="textlayer-aligned"), [])
    grid = {(c.row, c.col): c for c in table.cells}
    assert table.n_rows == 2 and [i.text for i in grid[(1, 1)].listing.items] == ["trees", "soil"]
