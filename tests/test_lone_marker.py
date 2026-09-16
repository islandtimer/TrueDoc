"""A bullet the text layer sets on a line of its own marks the words beside it.

Some PDFs draw a list's bullets in a text run apart from their items, an em or more before the words they mark. The
line splitter cuts there, so each bullet becomes a line holding one glyph: the items lose their markers and run
together into one paragraph, and the orphan bullets are published as empty list items ("- " with nothing after). Over
sixty documents of the owner's library, with the layout model running, sixteen pages of 386 and nine documents of
sixty did this - 54 empty items. A mark read from its own drawing already joins the words beside it
(`_read_private_glyphs`, RACQ's supplementary PDS); a bullet the text layer names does the same, on the same measures.
"""
import pymupdf

from truedoc.pipeline import ConvertOptions, convert

OFF = ConvertOptions(layout=False, ocr=False, math=False, marks=False, tables=False, frontmatter=False)


def _pdf(tmp_path, rows, mark="•", gap=22.0, name="list.pdf"):
    """Each row is (text, y): the mark at x=60 and the words at x=60+gap, as separate text runs."""
    doc = pymupdf.open()
    page = doc.new_page(width=400, height=560)
    page.insert_text((40, 60), "You are not covered for:", fontsize=10)
    for text, y in rows:
        page.insert_text((60, y), mark, fontsize=10)
        page.insert_text((60 + gap, y), text, fontsize=10)
    path = tmp_path / name
    doc.save(str(path))
    doc.close()
    return str(path)


def test_the_bullet_and_its_words_are_one_item(tmp_path):
    md = convert(_pdf(tmp_path, [("diving equipment", 100)]), OFF)
    assert "- diving equipment" in md
    assert not [l for l in md.splitlines() if l.strip() in ("-", "- ")]


def test_every_item_keeps_its_own_marker(tmp_path):
    rows = [("diving equipment", 100), ("parachutes", 120), ("wear and tear or scratches.", 140)]
    md = convert(_pdf(tmp_path, rows), OFF)
    assert [l.strip() for l in md.splitlines() if l.strip().startswith("- ")] == [
        "- diving equipment", "- parachutes", "- wear and tear or scratches."]


def test_without_the_rule_the_items_would_have_no_markers(tmp_path):
    """What the page holds is the point: three items, three markers, nothing run together."""
    rows = [("diving equipment", 100), ("parachutes", 120)]
    md = convert(_pdf(tmp_path, rows), OFF)
    assert "diving equipment parachutes" not in " ".join(md.split())


def test_a_bullet_further_off_than_three_ems_marks_nothing(tmp_path):
    """The reach is the one the drawn marks already use; a bullet a column away is a cell's own content."""
    md = convert(_pdf(tmp_path, [("the next column", 100)], gap=90.0), OFF)
    assert "- the next column" not in md


def test_a_tick_alone_is_left_where_it_stands(tmp_path):
    """A column of ticks is a table's answers, not a list's markers (D028), so ticks are not joined here."""
    md = convert(_pdf(tmp_path, [("Carpets and loose floor coverings", 100)], mark="✓"), OFF)
    assert "- ✓ Carpets" not in md


def test_a_bullet_with_no_words_beside_it_stays(tmp_path):
    doc = pymupdf.open()
    page = doc.new_page(width=400, height=560)
    page.insert_text((60, 100), "•", fontsize=10)
    page.insert_text((60, 140), "a paragraph well below the bullet", fontsize=10)
    path = tmp_path / "alone.pdf"
    doc.save(str(path))
    doc.close()
    md = convert(str(path), OFF)
    assert "a paragraph well below the bullet" in md
    assert "•" in md or "-" in md
