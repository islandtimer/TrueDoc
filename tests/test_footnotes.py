"""Footnote markers become [^n] and their notes become [^n]: definitions."""

import pymupdf

from truedoc.pipeline import ConvertOptions, convert


def _pdf(tmp_path):
    doc = pymupdf.open()
    page = doc.new_page(width=400, height=400)
    y = 60
    for line in ["The committee reviewed the plan for the harbour", "and approved the budget without amendment."]:
        page.insert_text((40, y), line, fontsize=11)
        y += 15
    # A raised small "1" right after "harbour" on the first line, and a "2" after "amendment."
    page.insert_text((40 + pymupdf.get_text_length("The committee reviewed the plan for the harbour", fontsize=11), 55), "1", fontsize=7)
    page.insert_text((40 + pymupdf.get_text_length("and approved the budget without amendment.", fontsize=11), 70), "2", fontsize=7)
    y = 110
    for line in ["Later paragraphs discuss the timetable and the costs of the works in some detail,",
                 "and the reader is referred to the appendix for the full tables."]:
        page.insert_text((40, y), line, fontsize=11)
        y += 15
    # The notes at the foot of the page, in smaller type.
    page.insert_text((40, 360), "1 Minutes of the meeting of 4 March.", fontsize=8)
    page.insert_text((40, 372), "2 See the treasurer's report, page 3.", fontsize=8)
    path = tmp_path / "notes.pdf"
    doc.save(str(path))
    doc.close()
    return str(path)


def test_markers_and_notes_are_linked(tmp_path):
    md = convert(_pdf(tmp_path), ConvertOptions(frontmatter=False, layout=False, ocr=False))
    assert "harbour[^1]" in md, md
    assert "amendment.[^2]" in md, md
    assert "[^1]: Minutes of the meeting of 4 March." in md, md
    assert "[^2]: See the treasurer's report, page 3." in md, md
    # The raw digits do not survive as loose numbers.
    assert "harbour1" not in md and "\n1 Minutes" not in md


def test_numbers_in_ordinary_text_are_not_markers(tmp_path):
    doc = pymupdf.open()
    page = doc.new_page(width=400, height=300)
    page.insert_text((40, 60), "In 2019 the fleet had 12 vessels and 3 tugs.", fontsize=11)
    page.insert_text((40, 260), "3 vessels were sold the following year.", fontsize=11)
    path = tmp_path / "plain.pdf"
    doc.save(str(path))
    doc.close()
    md = convert(str(path), ConvertOptions(frontmatter=False, layout=False, ocr=False))
    assert "[^" not in md, md


def _marked_page(doc, text: str, marker: str, note: str | None = None):
    page = doc.new_page(width=400, height=400)
    page.insert_text((40, 60), text, fontsize=11)
    page.insert_text((40 + pymupdf.get_text_length(text, fontsize=11), 55), marker, fontsize=7)
    y = 90
    for line in ["Later paragraphs discuss the timetable and the costs of the works in some detail,",
                 "and the reader is referred to the appendix for the full tables."]:
        page.insert_text((40, y), line, fontsize=11)
        y += 15
    if note:
        page.insert_text((40, 360), note, fontsize=8)
    return page


def test_endnotes_on_a_later_page_are_linked(tmp_path):
    doc = pymupdf.open()
    _marked_page(doc, "The committee reviewed the plan for the harbour", "1")
    _marked_page(doc, "The council approved the budget for the works", "2")
    notes = doc.new_page(width=400, height=400)
    notes.insert_text((40, 60), "Notes", fontsize=14)
    notes.insert_text((40, 90), "1 Minutes of the meeting of 4 March.", fontsize=11)
    notes.insert_text((40, 105), "2 See the treasurer's report, page 3.", fontsize=11)
    path = tmp_path / "endnotes.pdf"
    doc.save(str(path))
    doc.close()
    md = convert(str(path), ConvertOptions(frontmatter=False, layout=False, ocr=False))
    assert "harbour[^1]" in md and "works[^2]" in md, md
    assert "[^1]: Minutes of the meeting of 4 March." in md, md
    assert "[^2]: See the treasurer's report, page 3." in md, md


def test_note_keys_stay_unique_across_pages(tmp_path):
    doc = pymupdf.open()
    _marked_page(doc, "The committee reviewed the plan for the harbour", "1", "1 Minutes of the meeting of 4 March.")
    _marked_page(doc, "The council approved the budget for the works", "1", "1 See the treasurer's report, page 3.")
    path = tmp_path / "twice.pdf"
    doc.save(str(path))
    doc.close()
    md = convert(str(path), ConvertOptions(frontmatter=False, layout=False, ocr=False))
    assert "harbour[^1]" in md and "[^1]: Minutes of the meeting of 4 March." in md, md
    assert "works[^1-p2]" in md and "[^1-p2]: See the treasurer's report, page 3." in md, md
    assert md.count("[^1]:") == 1


def test_a_marker_without_any_note_keeps_its_digits(tmp_path):
    # Citation numbers point at a bibliography that is not on the page: "tumors.2-4"
    # stays as printed rather than becoming links to nothing.
    doc = pymupdf.open()
    page = doc.new_page(width=400, height=300)
    text = "Risk factors include achalasia and head and neck tumors."
    page.insert_text((40, 60), text, fontsize=11)
    x = 40 + pymupdf.get_text_length(text, fontsize=11)
    page.insert_text((x, 55), "2-4", fontsize=7)
    page.insert_text((40, 90), "The esophagus lacks a serosal layer, which allows early spread.", fontsize=11)
    path = tmp_path / "citations.pdf"
    doc.save(str(path))
    doc.close()
    md = convert(str(path), ConvertOptions(frontmatter=False, layout=False, ocr=False))
    assert "[^" not in md, md
    assert "tumors.2-4" in md, md


def test_a_numbered_heading_is_not_an_endnote(tmp_path):
    doc = pymupdf.open()
    _marked_page(doc, "The committee reviewed the plan for the harbour", "1")
    page = doc.new_page(width=400, height=400)
    page.insert_text((40, 60), "1 Introduction", fontsize=14)
    page.insert_text((40, 90), "The plan covers the harbour and the roads leading to it.", fontsize=11)
    path = tmp_path / "heading.pdf"
    doc.save(str(path))
    doc.close()
    md = convert(str(path), ConvertOptions(frontmatter=False, layout=False, ocr=False))
    assert "[^1]:" not in md, md
    assert "Introduction" in md
