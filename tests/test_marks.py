"""Marks drawn as shapes (ticks, crosses, bullets) carry meaning and must reach the text.

Each test draws a small PDF with PyMuPDF and converts it.
"""

import pymupdf

from truedoc.pipeline import ConvertOptions, convert


def _pdf(tmp_path, draw, name="marks.pdf"):
    doc = pymupdf.open()
    page = doc.new_page(width=400, height=300)
    draw(page)
    path = tmp_path / name
    doc.save(str(path))
    doc.close()
    return str(path)


def _tick(page, x, y, s=8, color=(0.2, 0.7, 0.2)):
    # A check mark: short stroke down-right, long stroke up-right.
    page.draw_polyline([(x, y + 0.5 * s), (x + 0.35 * s, y + 0.9 * s), (x + s, y)], color=color, width=1.6)


def _cross(page, x, y, s=8, color=(0.85, 0.2, 0.2)):
    page.draw_line((x, y), (x + s, y + s), color=color, width=1.6)
    page.draw_line((x, y + s), (x + s, y), color=color, width=1.6)


def _convert(path):
    return convert(path, ConvertOptions(frontmatter=False, layout=False, ocr=False))


def test_tick_and_cross_in_ruled_table_cells(tmp_path):
    def draw(page):
        # A ruled table: three columns, header plus two rows.
        xs = [40, 200, 280, 360]
        ys = [60, 84, 108, 132]
        for x in xs:
            page.draw_line((x, ys[0]), (x, ys[-1]), color=(0, 0, 0), width=0.8)
        for y in ys:
            page.draw_line((xs[0], y), (xs[-1], y), color=(0, 0, 0), width=0.8)
        page.insert_text((44, 78), "Excess", fontsize=10)
        page.insert_text((204, 78), "Your home", fontsize=10)
        page.insert_text((284, 78), "Your contents", fontsize=10)
        page.insert_text((44, 102), "Pet cover excess", fontsize=10)
        _cross(page, 236, 90)
        _tick(page, 316, 90)
        page.insert_text((44, 126), "Basic excess", fontsize=10)
        _tick(page, 236, 114)
        _tick(page, 316, 114)

    md = _convert(_pdf(tmp_path, draw))
    rows = [l for l in md.splitlines() if l.startswith("|") and "---" not in l]
    assert any("Pet cover excess" in r and "✗" in r and "✓" in r for r in rows), md
    pet = next(r for r in rows if "Pet cover excess" in r)
    cells = [c.strip() for c in pet.strip("|").split("|")]
    assert cells[1] == "✗" and cells[2] == "✓", cells
    basic = next(r for r in rows if "Basic excess" in r)
    assert basic.count("✓") == 2, basic


def test_ringed_marks_are_read(tmp_path):
    def draw(page):
        xs = [40, 200, 280]
        ys = [60, 84, 108, 132]
        for x in xs:
            page.draw_line((x, ys[0]), (x, ys[-1]), color=(0, 0, 0), width=0.8)
        for y in ys:
            page.draw_line((xs[0], y), (xs[-1], y), color=(0, 0, 0), width=0.8)
        page.insert_text((44, 78), "Item", fontsize=10)
        page.insert_text((204, 78), "Covered", fontsize=10)
        page.insert_text((44, 102), "Mobile phones", fontsize=10)
        page.insert_text((44, 126), "Bicycles", fontsize=10)
        # A circle drawn around each mark, as many benefit tables do.
        page.draw_circle((240, 96), 7, color=(0.85, 0.2, 0.2), width=0.8)
        _cross(page, 236.5, 92.5, s=7)
        page.draw_circle((240, 120), 7, color=(0.2, 0.7, 0.2), width=0.8)
        _tick(page, 236.5, 116.5, s=7)

    md = _convert(_pdf(tmp_path, draw))
    row = next(l for l in md.splitlines() if "Mobile phones" in l)
    assert "✗" in row, md
    row = next(l for l in md.splitlines() if "Bicycles" in l)
    assert "✓" in row, md


def test_tick_before_a_line_starts_the_line(tmp_path):
    def draw(page):
        page.insert_text((60, 80), "Bring your policy number", fontsize=11)
        _tick(page, 44, 71, s=9)
        page.insert_text((60, 100), "Bring photo identification", fontsize=11)
        _cross(page, 44, 91, s=9)

    md = _convert(_pdf(tmp_path, draw))
    assert "✓ Bring your policy number" in md, md
    assert "✗ Bring photo identification" in md, md


def test_ringed_glyph_is_not_a_mark(tmp_path):
    # A dollar sign in a circle (a "limit" icon) is neither a tick nor a bullet.
    def draw(page):
        page.insert_text((60, 80), "Up to the sum insured for your home", fontsize=11)
        page.draw_circle((44, 76), 8, color=(0.1, 0.3, 0.7), width=0.9)
        page.insert_text((40.5, 80), "$", fontsize=11, color=(0.1, 0.3, 0.7))

    md = _convert(_pdf(tmp_path, draw))
    line = next(l for l in md.splitlines() if "sum insured" in l)
    assert not any(ch in line for ch in "✓✗●○■□"), line
    assert "[icon]" not in line


def test_no_marks_on_plain_text(tmp_path):
    def draw(page):
        page.insert_text((40, 80), "Only ordinary text lives on this page.", fontsize=11)
        page.draw_line((40, 84), (250, 84), color=(0, 0, 0), width=0.6)  # an underline is not a mark

    md = _convert(_pdf(tmp_path, draw))
    assert "✓" not in md and "✗" not in md and "[icon]" not in md
