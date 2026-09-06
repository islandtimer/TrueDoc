"""Figure placeholders: rendered where a figure is, without breaking the text around them."""

import pymupdf

from truedoc.pipeline import ConvertOptions, convert


def test_figure_renders_as_a_placeholder(tmp_path):
    doc = pymupdf.open()
    page = doc.new_page(width=400, height=500)
    page.insert_text((40, 60), "The chart below shows the trend.", fontsize=11)
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 60, 40), 0)
    pix.clear_with(120)
    page.insert_image(pymupdf.Rect(60, 120, 340, 320), pixmap=pix)
    page.insert_text((40, 380), "Source: the annual report.", fontsize=9)
    path = tmp_path / "fig.pdf"
    doc.save(str(path))
    doc.close()
    md = convert(str(path), ConvertOptions(frontmatter=False, layout=False, ocr=False))
    assert md.index("trend.") < md.index("![](figure)") < md.index("Source:"), md


def test_paragraph_continues_across_a_figure_at_the_foot_of_a_column(tmp_path):
    """Two columns; the left one ends with a figure under a paragraph that carries
    on at the top of the right column. The paragraph is one paragraph, the
    placeholder follows it."""
    doc = pymupdf.open()
    page = doc.new_page(width=600, height=400)
    left = ["The committee met in the spring to review the", "harbour works and the budget for the coming", "year, and after a long debate it resolved that the"]
    y = 60
    for line in left:
        page.insert_text((40, y), line, fontsize=10)
        y += 14
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 60, 40), 0)
    pix.clear_with(120)
    page.insert_image(pymupdf.Rect(50, 130, 270, 280), pixmap=pix)
    right = ["works should proceed without further delay, and", "that the treasurer report back in the autumn."]
    y = 60
    for line in right:
        page.insert_text((320, y), line, fontsize=10)
        y += 14
    path = tmp_path / "columns.pdf"
    doc.save(str(path))
    doc.close()
    md = convert(str(path), ConvertOptions(frontmatter=False, layout=False, ocr=False))
    assert "resolved that the works should proceed" in md, md
    assert md.count("![](figure)") == 1 and md.index("![](figure)") > md.index("autumn."), md
