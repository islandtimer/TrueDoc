"""A wrapped entry whose value is set against its last line is one row.

BOM's home PDS contents page writes "What you're covered for" over "under each of the insured events" with the page
number 16 beside the second line only, and the table came out with two rows, the first holding no page number. The upper
row fills its label alone, the lower row's label carries it on and holds the value, and the row after starts an entry of
its own: the two are one entry. A heading over a group reads the same way until the row after it - "Demographics" over
"age (years)" is followed by "sex (male %)", which carries on too - and a label closed by a colon or a bracket, or one
opened by a tick, is whole.

Joining must not change whether the text is a table at all. A conference flyer's accommodation list (0722235b on the
benchmark) sets room types over two lines with the price beside the second; counted whole, the joined labels took its
short cells under the two-column table's bar, and the whole price list came out as run-on text.
"""
import html
import re

import pymupdf

from truedoc.pipeline import ConvertOptions, convert
from truedoc.tables.aligned import _Row, _merge_wrapped_rows


def _merged(grid):
    rows = [_Row(segments=[], y0=12.0 * i, y1=12.0 * i + 10.0) for i in range(len(grid))]
    out, geometry = _merge_wrapped_rows([list(r) for r in grid], rows, 10.0)
    return out, geometry


def test_a_wrapped_entry_with_its_value_on_the_last_line_is_one_row():
    out, geometry = _merged([
        ["Understanding your policy", "9"],
        ["What you’re covered for", ""],
        ["under each of the insured events", "16"],
        ["Buildings", "24"],
    ])
    assert out == [
        ["Understanding your policy", "9"],
        ["What you’re covered for under each of the insured events", "16"],
        ["Buildings", "24"],
    ]
    assert (geometry[1].y0, geometry[1].y1) == (12.0, 34.0)


def test_a_heading_over_a_group_of_entries_is_not_joined():
    grid = [["Demographics", ""], ["age (years)", "60.5"], ["sex (male %)", "48"], ["Outcome", "12"]]
    assert _merged(grid)[0] == grid


def test_a_label_closed_by_a_bracket_or_a_colon_is_whole():
    bracket = [["Patient outcomes (n %)", ""], ["death", "86 (10)"], ["ESRD", "12 (4)"]]
    colon = [["Teachers by highest degree:", ""], ["no degree", "0.0"], ["Bachelors", "2.0"]]
    assert _merged(bracket)[0] == bracket
    assert _merged(colon)[0] == colon


def test_a_tick_starts_an_entry_of_its_own():
    grid = [["✓ Outdoor structures, including decks,", ""], ["pergolas, gazebos and fences", "✗"], ["✓ Your home", ""]]
    assert _merged(grid)[0] == grid


# Room types with a price beside the line it belongs to, three of them set over two lines, under a first entry that
# opens the table. Counted as the page sets them nearly every cell is four words or fewer; counted after joining, the
# three six-word labels take the short cells under the two-column bar.
PRICES = [
    ("Airport transfer", "US $25.00"),
    ("Standard rooms", None), ("(standard or double occupancy)", "US $85.00"),
    ("Executive rooms", None), ("(standard or double occupancy)", "US $130.00"),
    ("Junior suites", None), ("(standard or double occupancy)", "US $175.00"),
    ("Studio units", "US $55.00"), ("Single Superior Room", "US $61.25"), ("1 Bedroom Suite", "US $88.76"),
    ("Senior Common Room, UWI Mona", None), ("(Very limited accommodation, prices subject to change)", None),
    ("Single occupancy", "US $35.00"),
]


def _price_list(tmp_path):
    """The flyer's accommodation list: labels on the left, a price on the right beside the line it belongs to."""
    doc = pymupdf.open()
    page = doc.new_page(width=420, height=420)
    for i, (label, price) in enumerate(PRICES):
        y = 70 + 14 * i
        page.insert_text((40, y), label, fontsize=10)
        if price:
            page.insert_text((270, y), price, fontsize=10)
    path = tmp_path / "prices.pdf"
    doc.save(str(path))
    doc.close()
    return str(path)


def _table_rows(md):
    """Every table row in the markdown, pipe or HTML, as its cells' text."""
    rows = []
    for line in md.splitlines():
        if line.startswith("|"):
            cells = [c.strip().replace("\\$", "$") for c in line.strip().strip("|").split("|")]
            if not all(set(c) <= set("-: ") for c in cells):
                rows.append(cells)
    for tr in re.findall(r"<tr>(.*?)</tr>", md, re.S):
        rows.append([html.unescape(re.sub(r"<[^>]+>", "", c)).strip().replace("\\$", "$")
                     for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", tr, re.S)])
    return rows


def test_joined_entries_leave_a_price_list_a_table(tmp_path):
    md = convert(_price_list(tmp_path), ConvertOptions(frontmatter=False, layout=False, ocr=False))
    rows = _table_rows(md)
    assert ["Standard rooms (standard or double occupancy)", "US $85.00"] in rows, md
    assert ["Single Superior Room", "US $61.25"] in rows, md
