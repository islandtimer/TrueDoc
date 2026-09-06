"""Hidden text (D011): text a reader cannot see stays out of the body and is listed in the front matter.

Each test builds a small PDF with PyMuPDF and converts it.
"""

import pymupdf
import yaml

from truedoc.pipeline import ConvertOptions, convert


def _pdf(tmp_path, draw):
    doc = pymupdf.open()
    page = doc.new_page(width=400, height=300)
    draw(page)
    path = tmp_path / "t.pdf"
    doc.save(str(path))
    doc.close()
    return str(path)


def _convert(path):
    return convert(path, ConvertOptions(frontmatter=True, layout=False, ocr=False))


def _split(md):
    assert md.startswith("---\n")
    _, fm, body = md.split("---\n", 2)
    return yaml.safe_load(fm), body


def test_white_text_is_hidden(tmp_path):
    def draw(page):
        page.insert_text((40, 60), "Visible sentence about apples and oranges.", fontsize=12)
        page.insert_text((40, 120), "keyword stuffing hidden in white", fontsize=12, color=(1, 1, 1))

    fm, body = _split(_convert(_pdf(tmp_path, draw)))
    assert "apples and oranges" in body
    assert "keyword stuffing" not in body
    hidden = fm.get("truedoc", {}).get("hidden_text") or []
    assert any("keyword stuffing" in h["text"] for h in hidden)
    assert hidden[0]["page"] == 1 and hidden[0]["reason"]


def test_tiny_text_is_hidden(tmp_path):
    def draw(page):
        page.insert_text((40, 60), "Visible sentence about apples and oranges.", fontsize=12)
        page.insert_text((40, 120), "microscopic tracking text", fontsize=0.4)

    fm, body = _split(_convert(_pdf(tmp_path, draw)))
    assert "microscopic" not in body
    assert any("microscopic" in h["text"] for h in fm.get("truedoc", {}).get("hidden_text") or [])


def test_text_under_an_opaque_shape_is_hidden(tmp_path):
    def draw(page):
        page.insert_text((40, 60), "Visible sentence about apples and oranges.", fontsize=12)
        page.insert_text((40, 160), "covered by a black box", fontsize=12)
        page.draw_rect(pymupdf.Rect(30, 140, 300, 175), color=(0, 0, 0), fill=(0, 0, 0))

    fm, body = _split(_convert(_pdf(tmp_path, draw)))
    assert "covered by a black box" not in body
    assert any("covered by" in h["text"] for h in fm.get("truedoc", {}).get("hidden_text") or [])


def test_invisible_render_mode_on_a_normal_page_is_hidden(tmp_path):
    def draw(page):
        page.insert_text((40, 60), "Visible sentence about apples and oranges.", fontsize=12)
        page.insert_text((40, 120), "invisible render mode text", fontsize=12, render_mode=3)

    fm, body = _split(_convert(_pdf(tmp_path, draw)))
    assert "invisible render mode" not in body
    assert any("invisible render mode" in h["text"] for h in fm.get("truedoc", {}).get("hidden_text") or [])


def test_scanned_page_keeps_its_invisible_ocr_layer(tmp_path):
    # A scan: a full-page image with an invisible text layer on top (D010 exception).
    def draw(page):
        pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 40, 30), 0)
        pix.clear_with(255)
        page.insert_image(page.rect, pixmap=pix)
        y = 40
        for _ in range(8):
            page.insert_text((30, y), "This is a line of a scanned book page with an invisible text layer on it.", fontsize=9, render_mode=3)
            y += 14

    fm, body = _split(_convert(_pdf(tmp_path, draw)))
    assert "scanned book page" in body
    assert not fm.get("truedoc", {}).get("hidden_text")


def test_visible_text_is_not_reported(tmp_path):
    def draw(page):
        page.insert_text((40, 60), "Only ordinary visible text lives on this page.", fontsize=12)

    fm, body = _split(_convert(_pdf(tmp_path, draw)))
    assert "ordinary visible text" in body
    assert not fm.get("truedoc", {}).get("hidden_text")
