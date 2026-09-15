"""A list set inside a table cell is written as a list (D028).

Kogan's home PDS page 29 draws one box holding a whole ticked list - covers, one with a bulleted sub-list - and the cell
ran them together on one line. The list is read as the page sets it: a mark opens an entry at its hanging indent, lines
at that indent carry it on, a mark further in opens a sub-item, a line back at the indent after a sub-list carries the
entry on after it, and a line out at the box's edge is a note. One entry is not a list, and nothing the cell says
changes, only its shape.
"""
import re

import pymupdf

from truedoc.model import BBox, CellItem, CellList, Table, TableCell
from truedoc.pipeline import ConvertOptions, convert
from truedoc.render.okf import render_table
from truedoc.tables.cell_lists import build_listing, is_list


def _line(x, top, text, indent=None, height=8.0):
    """A line of words starting at x; given an indent, its first word is a mark and the words after it start there."""
    out, pos = [], x
    for i, word in enumerate(text.split()):
        if i == 1 and indent is not None:
            pos = indent
        out.append((word, pos, pos + 5.0 * len(word), top, top + height))
        pos += 5.0 * len(word) + 2.5
    return out


def test_a_ticked_list_with_a_sub_list_reads_as_a_list():
    listing = build_listing([
        _line(54.0, 126, "✔ Fixed ceiling, wall and floor", indent=65.3),
        _line(65.3, 140, "coverings (except carpet or rugs)"),
        _line(54.0, 173, "✔ Fixed domestic appliances that", indent=65.3),
        _line(65.3, 186, "are permanently connected, like:"),
        _line(62.5, 200, "• air conditioners & heating", indent=73.8),
        _line(73.8, 211, "systems"),
        _line(62.5, 224, "• ovens", indent=73.8),
        _line(54.0, 238, "✔ Trees and plants", indent=65.3),
        _line(65.3, 252, "– $5,000 limit applies."),
        _line(54.0, 266, "✔ Solar panels", indent=65.3),
    ])
    assert [item.text for item in listing.items] == [
        "✔ Fixed ceiling, wall and floor coverings (except carpet or rugs)",
        "✔ Fixed domestic appliances that are permanently connected, like:",
        "✔ Trees and plants – $5,000 limit applies.",
        "✔ Solar panels",
    ]
    assert listing.items[1].children == ["air conditioners & heating systems", "ovens"]
    assert listing.lead == "" and listing.note == ""


def test_words_after_a_sub_list_carry_the_entry_on_and_a_line_at_the_box_edge_is_a_note():
    listing = build_listing([
        _line(51.5, 226, "✔ Loss or damage caused by an earthquake", indent=62.9, height=9.1),
        _line(62.9, 239, "or tsunami.", height=9.1),
        _line(51.5, 251, "✔ Loss or damage caused by or arising", indent=62.9, height=9.1),
        _line(62.9, 264, "from:", height=9.1),
        _line(60.0, 278, "• soil movement, including erosion,", indent=71.4, height=9.1),
        _line(60.0, 292, "• landslide", indent=71.4, height=9.1),
        _line(62.9, 333, "if it is caused directly by an earthquake.", height=9.1),
        _line(48.7, 369, "An additional excess of $250 applies", height=9.1),
        _line(48.7, 380, "to each earthquake.", height=9.1),
    ])
    assert [item.text for item in listing.items] == [
        "✔ Loss or damage caused by an earthquake or tsunami.", "✔ Loss or damage caused by or arising from:"]
    assert listing.items[1].children == ["soil movement, including erosion,", "landslide"]
    assert listing.items[1].tail == "if it is caused directly by an earthquake."
    assert listing.note == "An additional excess of $250 applies to each earthquake."


def test_one_entry_with_a_sub_list_is_a_list():
    listing = build_listing([
        _line(31.2, 395, "✓ Loss or damage caused by impact from:", indent=43.3),
        _line(41.1, 409, "• any motor vehicle, train or watercraft,", indent=49.9),
        _line(41.1, 422, "• any aircraft or drone,", indent=49.9),
    ], least=1)
    assert is_list(listing)
    assert listing.items[0].children == ["any motor vehicle, train or watercraft,", "any aircraft or drone,"]


def test_one_entry_is_not_a_list():
    assert build_listing([
        _line(217.9, 125, "✘ Carpets, rugs and internal blinds.", indent=232.0),
        _line(232.0, 140, "Go to Contents cover on pages 34 to 37."),
    ]) is None


def test_a_cell_holding_a_list_is_written_as_one():
    listing = CellList(items=[CellItem("✔ Solar panels"),
                              CellItem("✔ Fixed domestic appliances, like:", children=["ovens", "dishwashers"])],
                       note="An excess applies.")
    cells = [TableCell("What’s covered?", 0, 0, is_header=True), TableCell("What’s not covered?", 0, 1, is_header=True),
             TableCell("✔ Solar panels ✔ Fixed domestic appliances, like: • ovens • dishwashers An excess applies.", 1, 0,
                       listing=listing),
             TableCell("✘ Pontoons", 1, 1)]
    html = render_table(Table(n_rows=2, n_cols=2, cells=cells, bbox=BBox(0, 0, 100, 100)))
    assert html.startswith("<table>")
    assert "<li>✔ Solar panels</li>" in html
    assert re.search(r"<li>✔ Fixed domestic appliances, like:\s*<ul>\s*<li>ovens</li>\s*<li>dishwashers</li>\s*</ul>\s*</li>",
                     html), html
    assert "<p>An excess applies.</p>" in html
    assert "<td>✘ Pontoons</td>" in html


def test_a_list_drawn_in_one_box_comes_out_as_a_list(tmp_path):
    doc = pymupdf.open()
    page = doc.new_page(width=420, height=300)
    for x in (40, 210, 380):
        page.draw_line((x, 40), (x, 200), color=(0, 0, 0), width=0.8)
    for y in (40, 60, 200):
        page.draw_line((40, y), (380, y), color=(0, 0, 0), width=0.8)
    page.insert_text((46, 54), "What we cover", fontsize=10)
    page.insert_text((216, 54), "What we do not cover", fontsize=10)
    for i, (x, text) in enumerate([(50, "• Solar panels"), (50, "• Satellite dishes and"), (56.3, "antennas"),
                                   (50, "• Hot water systems")]):
        page.insert_text((x, 78 + 14 * i), text, fontsize=10)
    page.insert_text((46, 150), "Limits apply to each item.", fontsize=10)
    page.insert_text((216, 78), "Pontoons", fontsize=10)
    path = tmp_path / "boxed.pdf"
    doc.save(str(path))
    doc.close()
    md = convert(str(path), ConvertOptions(frontmatter=False, layout=False, ocr=False))
    assert re.search(r"<li>Solar panels</li>\s*<li>Satellite dishes and antennas</li>\s*<li>Hot water systems</li>", md), md
    assert "<p>Limits apply to each item.</p>" in md, md


def test_a_paragraph_under_an_entry_is_a_note_and_a_line_wrapped_under_its_bullet_is_not():
    noted = build_listing([
        _line(31.2, 290, "✓ Loss or damage caused by actual or attempted", indent=42.5),
        _line(42.5, 302, "theft or burglary."),
        _line(31.2, 316, "You must report the incident to police"),
    ], least=1)
    assert [item.text for item in noted.items] == ["✓ Loss or damage caused by actual or attempted theft or burglary."]
    assert noted.note == "You must report the incident to police"
    wrapped = build_listing([
        _line(31.2, 290, "• Loss or damage caused by fire or", indent=37.0),
        _line(31.2, 300.5, "smoke"),
        _line(31.2, 311, "• Storm", indent=37.0),
    ])
    assert [item.text for item in wrapped.items] == ["Loss or damage caused by fire or smoke", "Storm"]
    assert wrapped.note == ""
