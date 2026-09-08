"""A mark is small relative to its page, not in absolute points.

An insurance product disclosure statement in the owner's library (Huddle Black Home, page 9)
is laid out at 1920 x 1080 points instead of the usual 612 x 792, and its benefit table marks
coverage with 40-point tick and cross icons. The mark reader's size gate was an absolute 3 to
30 points, so every one of those icons was rejected as "too big" and the table converted with
its meaning removed: "Emergency storage of your contents" came out with two empty cells where
the page says covered for the home and not for the contents. Relative to its own page a
40-point icon there is smaller than a 30-point tick on a letter page (2.1% of the width
against 4.9%), so the gate has to scale with the page.
"""

import pymupdf

from truedoc.pipeline import ConvertOptions, convert


def _tick(page, x, y, s, color=(0.2, 0.7, 0.2)):
    page.draw_polyline([(x, y + 0.5 * s), (x + 0.35 * s, y + 0.9 * s), (x + s, y)], color=color, width=0.2 * s)


def _cross(page, x, y, s, color=(0.85, 0.2, 0.2)):
    page.draw_line((x, y), (x + s, y + s), color=color, width=0.2 * s)
    page.draw_line((x, y + s), (x + s, y), color=color, width=0.2 * s)


def _benefit_page(tmp_path):
    """The library page's geometry: a 1920x1080 slide, 40-point marks, 77-point rows."""
    doc = pymupdf.open()
    page = doc.new_page(width=1920, height=1080)
    xs = [700, 1450, 1660, 1870]
    ys = [140, 217, 294, 371]
    for x in xs:
        page.draw_line((x, ys[0]), (x, ys[-1]), color=(0, 0, 0), width=1.5)
    for y in ys:
        page.draw_line((xs[0], y), (xs[-1], y), color=(0, 0, 0), width=1.5)
    page.insert_text((720, 190), "What you are covered for", fontsize=26)
    page.insert_text((1470, 190), "Home", fontsize=26)
    page.insert_text((1680, 190), "Contents", fontsize=26)
    page.insert_text((720, 267), "Removal of debris", fontsize=26)
    _tick(page, 1512, 230, 40)
    _tick(page, 1722, 230, 40)
    page.insert_text((720, 344), "Emergency accommodation", fontsize=26)
    _tick(page, 1512, 307, 40)
    _cross(page, 1722, 307, 40)
    path = tmp_path / "benefits_slide.pdf"
    doc.save(str(path))
    doc.close()
    return str(path)


def test_marks_on_a_presentation_sized_page_reach_the_table(tmp_path):
    md = convert(_benefit_page(tmp_path), ConvertOptions(frontmatter=False, layout=False, ocr=False))
    rows = [l for l in md.splitlines() if l.startswith("|") and "---" not in l]
    assert rows, "no table was found at all:\n" + md

    debris = next((r for r in rows if "Removal of debris" in r), None)
    assert debris is not None, md
    assert debris.count("✓") == 2, "both cells are covered: " + debris

    emergency = next((r for r in rows if "Emergency accommodation" in r), None)
    assert emergency is not None, md
    cells = [c.strip() for c in emergency.strip("|").split("|")]
    assert "✓" in cells and "✗" in cells, "covered for home, not for contents: " + emergency


def _disc_tick(page, x, y, s, colour):
    """A white tick knocked out of a solid coloured disc, as the library page draws it."""
    r = s / 2.0
    page.draw_circle((x + r, y + r), r, color=colour, fill=colour)
    page.draw_polyline([(x + 0.24 * s, y + 0.52 * s), (x + 0.42 * s, y + 0.70 * s), (x + 0.76 * s, y + 0.30 * s)],
                       color=(1, 1, 1), width=0.1 * s)


def _disc_cross(page, x, y, s, colour):
    r = s / 2.0
    page.draw_circle((x + r, y + r), r, color=colour, fill=colour)
    page.draw_line((x + 0.3 * s, y + 0.3 * s), (x + 0.7 * s, y + 0.7 * s), color=(1, 1, 1), width=0.1 * s)
    page.draw_line((x + 0.3 * s, y + 0.7 * s), (x + 0.7 * s, y + 0.3 * s), color=(1, 1, 1), width=0.1 * s)


def test_a_mark_knocked_out_of_a_solid_disc_keeps_its_meaning(tmp_path):
    """The meaning is the hole, not the ink.

    The Huddle benefit table draws cover as a white tick inside a solid green disc and no cover
    as a white cross inside a solid red one. Read as ink, both are just discs, so both columns
    said the same thing - which tells a reader everything is covered.
    """
    doc = pymupdf.open()
    page = doc.new_page(width=1920, height=1080)
    xs = [700, 1450, 1660, 1870]
    ys = [140, 217, 294]
    for x in xs:
        page.draw_line((x, ys[0]), (x, ys[-1]), color=(0, 0, 0), width=1.5)
    for y in ys:
        page.draw_line((xs[0], y), (xs[-1], y), color=(0, 0, 0), width=1.5)
    page.insert_text((720, 190), "Benefit", fontsize=26)
    page.insert_text((1470, 190), "Home", fontsize=26)
    page.insert_text((1680, 190), "Contents", fontsize=26)
    page.insert_text((720, 267), "Emergency accommodation", fontsize=26)
    _disc_tick(page, 1512, 230, 40, (0.13, 0.72, 0.45))
    _disc_cross(page, 1722, 230, 40, (0.90, 0.22, 0.21))
    path = tmp_path / "knockout.pdf"
    doc.save(str(path))
    doc.close()

    md = convert(str(path), ConvertOptions(frontmatter=False, layout=False, ocr=False))
    row = next((l for l in md.splitlines() if "Emergency accommodation" in l and l.startswith("|")), None)
    assert row is not None, md
    cells = [c.strip() for c in row.strip("|").split("|")]
    assert "✓" in cells, "the green disc holds a tick: " + row
    assert "✗" in cells, "the red disc holds a cross: " + row
