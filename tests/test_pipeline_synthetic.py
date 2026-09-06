"""End-to-end test on a PDF we generate ourselves, so the expected text is known exactly."""

import pymupdf

from truedoc.pipeline import ConvertOptions, convert

LEFT = [
    "The quick brown fox jumps over the lazy dog near the river bank.",
    "It was a sunny afternoon and the fox had nothing better to do.",
    "Second paragraph of the left column starts here and continues.",
]
RIGHT = [
    "Right column begins with a different story about a cat.",
    "The cat, unlike the fox, preferred to sleep all afternoon long.",
]


def _make_pdf(path):
    doc = pymupdf.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((72, 40), "Running header text", fontsize=8)
    page.insert_text((72, 90), "A Two Column Test Document", fontsize=20)
    page.insert_text((72, 130), "1 Introduction", fontsize=13)
    y = 160
    for line in LEFT:
        page.insert_textbox(pymupdf.Rect(72, y, 300, y + 60), line, fontsize=10)
        y += 50
    y = 160
    for line in RIGHT:
        page.insert_textbox(pymupdf.Rect(320, y, 540, y + 60), line, fontsize=10)
        y += 50
    page.insert_text((300, 770), "7", fontsize=9)
    doc.save(str(path))
    doc.close()


def test_two_column_synthetic(tmp_path):
    pdf = tmp_path / "two_col.pdf"
    _make_pdf(pdf)
    md = convert(str(pdf), ConvertOptions(frontmatter=False))
    # Title and heading recognised.
    assert "# A Two Column Test Document" in md
    assert "1 Introduction" in md
    # Running header and page number removed.
    assert "Running header text" not in md
    assert "\n7\n" not in md
    # Reading order: whole left column before the right column.
    pos = [md.index(t.split(",")[0].split(" near")[0]) for t in LEFT + RIGHT]
    assert pos == sorted(pos)


def test_frontmatter_present(tmp_path):
    pdf = tmp_path / "fm.pdf"
    _make_pdf(pdf)
    md = convert(str(pdf), ConvertOptions(frontmatter=True))
    assert md.startswith("---\ntype: Document")
    fm = md.split("---\n", 2)[1]
    for key in ("title:", "resource:", "generated:", "status: draft", "sources:", "truedoc:"):
        assert key in fm
    assert "sha256:" in md


def _make_table_pdf(path):
    doc = pymupdf.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((72, 80), "Table 1. Yields by plot", fontsize=11)
    rows = [("Plot", "Yield", "Notes"), ("North", "12.5", "wet"), ("South", "9.1", "dry"), ("East", "14.0", "mixed"), ("West", "7.7", "rocky")]
    y = 110
    for r in rows:
        page.insert_text((72, y), r[0], fontsize=10)
        page.insert_text((200, y), r[1], fontsize=10)
        page.insert_text((300, y), r[2], fontsize=10)
        y += 16
    page.insert_textbox(pymupdf.Rect(72, 220, 540, 300), "A paragraph of ordinary prose follows the table and should not become a table row.", fontsize=10)
    doc.save(str(path))
    doc.close()


def test_unruled_table_extracted(tmp_path):
    pdf = tmp_path / "table.pdf"
    _make_table_pdf(pdf)
    md = convert(str(pdf), ConvertOptions(frontmatter=False, layout=False))
    assert "| Plot | Yield | Notes |" in md
    assert "| South | 9.1 | dry |" in md
    assert "ordinary prose" in md and "| A paragraph" not in md


def test_rotated_page_is_read_in_rendered_space(tmp_path):
    """A landscape table typeset sideways on a portrait page with /Rotate 90 (a common scan layout)."""
    doc = pymupdf.open()
    page = doc.new_page(width=612, height=792)
    rows = [("Plot", "Yield", "Notes"), ("North", "12.5", "wet"), ("South", "9.1", "dry"), ("East", "14.0", "mixed"), ("West", "7.7", "rocky")]
    x = 100
    for r in rows:
        # rotate=90 draws the text running upward; the page rotation below turns it upright.
        page.insert_text((x, 700), r[0], fontsize=10, rotate=90)
        page.insert_text((x, 560), r[1], fontsize=10, rotate=90)
        page.insert_text((x, 460), r[2], fontsize=10, rotate=90)
        x += 16
    page.set_rotation(90)
    rotated = tmp_path / "rot90.pdf"
    doc.save(str(rotated))
    doc.close()
    from truedoc.extract.textlayer import extract_page

    page = extract_page(pymupdf.open(str(rotated))[0], 1)
    assert page.width > page.height
    assert all(not l.rotated for l in page.lines)
    assert all(0 <= l.bbox.x0 <= page.width and 0 <= l.bbox.y0 <= page.height for l in page.lines)
    md = convert(str(rotated), ConvertOptions(frontmatter=False, layout=False))
    assert "| South | 9.1 | dry |" in md
