"""A list item set further in than the item above it opens a sub-list, and is written as one.

The owner's D028 says this already for a list inside a table cell: "a mark set further in than the entry's own opens
an item of a sub-list". The body had no such rule, so CGU's landlord PDS - "there is any change to:" over four items
an em further in - published both levels as siblings, and nothing said which items belonged to the entry above them.
Over 217 pages of forty library documents, 20 pages and 11 documents set a list at two levels or more.

The level is read from the page: within a run of list items, the markers' left edges are gathered into places half an
em apart. A list that carries on in the next column starts again there, because a marker further in than a list ever
goes is another column, not a deeper level.
"""
import pymupdf

from truedoc.pipeline import ConvertOptions, convert

OFF = ConvertOptions(layout=False, ocr=False, math=False, marks=False, tables=False, frontmatter=False)


def _pdf(tmp_path, items, width=420, name="list.pdf"):
    """Each item is (x, text); y steps down the page."""
    doc = pymupdf.open()
    page = doc.new_page(width=width, height=400)
    page.insert_text((57, 60), "You must tell Us if:", fontsize=11)
    for i, (x, text) in enumerate(items):
        page.insert_text((x, 100 + 20 * i), "• " + text, fontsize=9)
    path = tmp_path / name
    doc.save(str(path))
    doc.close()
    return str(path)


def test_a_sub_list_is_written_under_the_entry_it_belongs_to(tmp_path):
    md = convert(_pdf(tmp_path, [
        (60, "Your Rental Property will be unoccupied for sixty days"),
        (60, "there is any change to:"),
        (76, "the address or Site where Your Rental Property is insured"),
        (76, "Your Rental Property due to renovations or demolition"),
        (76, "the people insured under this Policy"),
    ]), OFF)
    lines = [l for l in md.splitlines() if l.strip().startswith("-")]
    assert lines[0].startswith("- Your Rental Property"), lines
    assert lines[1].startswith("- there is any change to:"), lines
    assert all(l.startswith("  - ") for l in lines[2:]), lines


def test_a_flat_list_stays_flat(tmp_path):
    md = convert(_pdf(tmp_path, [
        (60, "the policy; or"),
        (60, "the IC Act,"),
        (60, "any other agreement between us"),
    ]), OFF)
    lines = [l for l in md.splitlines() if l.strip().startswith("-")]
    assert len(lines) == 3, lines
    assert all(not l.startswith(" ") for l in lines), lines


def test_a_list_carrying_on_in_the_next_column_is_not_a_deeper_level(tmp_path):
    """Eight ems in is another column of the page; each column's levels are read on their own."""
    md = convert(_pdf(tmp_path, [
        (60, "first column, first item"),
        (60, "first column, second item"),
        (60, "first column, third item"),
        (260, "second column, first item"),
        (260, "second column, second item"),
        (260, "second column, third item"),
    ], width=520), OFF)
    lines = [l for l in md.splitlines() if l.strip().startswith("-")]
    assert len(lines) == 6, lines
    assert all(not l.startswith(" ") for l in lines), lines


def test_nothing_goes_deeper_than_four_levels(tmp_path):
    md = convert(_pdf(tmp_path, [(60 + 12 * i, "level {}".format(i + 1)) for i in range(6)]), OFF)
    lines = [l for l in md.splitlines() if l.strip().startswith("-")]
    assert max(len(l) - len(l.lstrip()) for l in lines) <= 6, lines
