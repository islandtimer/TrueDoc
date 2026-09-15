"""An arrow with a shaft is read as an arrow, cut out of a square or drawn in ink.

Budget Direct's home PDS puts a green square with a white arrow cut out of it beside every page link ("page 47"), and the
mark reader read each square as a dot, so every link came out as a bullet. The chevron test wants an arrow's arms to
reach the corners of its ink; a shaft running the length of the ink leaves the corners at its tail empty.
"""
import pymupdf

from truedoc.extract.handle import open_pdf
from truedoc import marks
from truedoc.marks import classify_mark
from truedoc.model import BBox

GREEN = (0.0, 0.6, 0.3)
WHITE = (1.0, 1.0, 1.0)
ARROWS = ("arrow-right", "arrow-left", "arrow-up", "arrow-down")


def _read(tmp_path, name, draw, square=True):
    doc = pymupdf.open()
    page = doc.new_page(width=200, height=200)
    if square:
        page.draw_rect(pymupdf.Rect(50, 50, 70, 70), color=None, fill=GREEN)
    draw(page, WHITE if square else GREEN)
    path = tmp_path / f"{name}.pdf"
    doc.save(str(path))
    doc.close()
    handle = open_pdf(str(path))
    try:
        mark = classify_mark(handle[0], BBox(50, 50, 70, 70))
    finally:
        handle.close()
    return mark.kind if mark else None


def _right(page, colour):
    page.draw_line((53, 60), (66, 60), color=colour, width=1.4)
    page.draw_polyline([(61, 55), (66.5, 60), (61, 65)], color=colour, width=1.4)


def _left(page, colour):
    page.draw_line((54, 60), (67, 60), color=colour, width=1.4)
    page.draw_polyline([(59, 55), (53.5, 60), (59, 65)], color=colour, width=1.4)


def _down(page, colour):
    page.draw_line((60, 53), (60, 66), color=colour, width=1.4)
    page.draw_polyline([(55, 61), (60, 66.5), (65, 61)], color=colour, width=1.4)


def _plus(page, colour):
    page.draw_line((53, 60), (67, 60), color=colour, width=1.4)
    page.draw_line((60, 53), (60, 67), color=colour, width=1.4)


def test_an_arrow_cut_out_of_a_square_is_read_whichever_way_it_points(tmp_path):
    assert _read(tmp_path, "right", _right) == "arrow-right"
    assert _read(tmp_path, "left", _left) == "arrow-left"
    assert _read(tmp_path, "down", _down) == "arrow-down"


def test_an_arrow_drawn_in_ink_is_read_too(tmp_path):
    assert _read(tmp_path, "inked", _right, square=False) == "arrow-right"


def test_a_plus_cut_out_of_a_square_is_no_arrow(tmp_path):
    assert _read(tmp_path, "plus", _plus) not in ARROWS


def _solid_with_hole(cells):
    """A solid square on the reader's 32-cell grid, the given cells cut out of it."""
    mask = [[1 if 1 <= x <= 30 and 1 <= y <= 30 else 0 for x in range(32)] for y in range(32)]
    for x, y in cells:
        mask[y][x] = 0
    return mask


def _line(x0, y0, x1, y1):
    steps = max(abs(x1 - x0), abs(y1 - y0))
    return {(round(x0 + (x1 - x0) * i / steps), round(y0 + (y1 - y0) * i / steps)) for i in range(steps + 1)}


def _classified(monkeypatch, mask):
    monkeypatch.setattr(marks, "_ink", lambda pdf_page, box, M=None: (mask, "green"))
    return marks.classify_mark(None, BBox(0, 0, 10, 10)).kind


def test_a_thin_shape_under_the_old_gate_is_taken_only_as_a_shafted_arrow(monkeypatch):
    chevron = _line(8, 8, 16, 20) | _line(24, 8, 16, 20) | {(9, 8), (23, 8), (16, 21)}
    arrow = _line(9, 16, 23, 16) | _line(17, 10, 23, 16) | _line(17, 22, 23, 16)
    for cells in (chevron, arrow):
        assert 0.025 * 1024 <= len(cells) < 0.03 * 1024, len(cells)
    assert _classified(monkeypatch, _solid_with_hole(chevron)) not in ARROWS
    assert _classified(monkeypatch, _solid_with_hole(arrow)) == "arrow-right"


def test_an_arrow_whose_head_reaches_back_a_third_of_its_length_is_an_arrow(monkeypatch):
    head = _line(10, 4, 24, 15) | _line(10, 26, 24, 16) | _line(11, 4, 25, 15) | _line(11, 26, 25, 16)
    shaft = {(x, y) for x in range(2, 30) for y in (15, 16)}
    assert _classified(monkeypatch, _solid_with_hole(head | shaft)) == "arrow-right"


# The "m" of "Commonwealth" on CBA's home PDS, drawn as an outline, as the reader's own grid holds it (page 1 of
# cba-home-pds-20220410). Bold, it touches the ring test's band all round; erasing that ring leaves the middle stroke
# with the two arches bending onto it, which the shafted-arrow test read as an arrow pointing up.
M_OF_COMMONWEALTH = [
    "................................",
    "................................",
    "................................",
    "..####...######.....######......",
    "..#####.########...#########....",
    "..###############.###########...",
    "..###############.###########...",
    "..###########################...",
    "..#######...#########...######..",
    "..######.....#######.....#####..",
    "..#####......######......#####..",
    "..#####.......#####......#####..",
    "..#####.......#####......#####..",
    "..#####.......####.......#####..",
    "..#####.......####.......#####..",
    "..#####.......####.......#####..",
    "..#####.......####.......#####..",
    "..#####.......####.......#####..",
    "..#####.......####.......#####..",
    "..#####.......####.......#####..",
    "..#####.......####.......#####..",
    "..#####.......####.......#####..",
    "..#####.......####.......#####..",
    "..#####.......####.......#####..",
    "..#####.......####.......#####..",
    "..#####.......####.......#####..",
    "..#####.......####.......#####..",
    "..#####.......####.......#####..",
    "..#####.......####.......#####..",
    "................................",
    "................................",
    "................................",
]


def test_what_erasing_a_ring_leaves_of_a_bold_letter_is_no_arrow(monkeypatch):
    mask = [[1 if cell == "#" else 0 for cell in row] for row in M_OF_COMMONWEALTH]
    assert marks._has_ring(mask)
    assert _classified(monkeypatch, mask) not in ARROWS


# One of the five filled stars of the "Doody's Star Rating" on a book record (olmOCR-bench headers_footers 7881b598,
# page 1), as the reader's own grid holds it. Turned so its top spike is the tail, it passed every test for a shafted
# arrow pointing down; its two legs end either side of the line where an arrowhead's arms would meet.
STAR = [
    "................................",
    "................................",
    "................................",
    "...............##...............",
    "...............##...............",
    ".............######.............",
    ".............######.............",
    ".............######.............",
    ".............######.............",
    ".............######.............",
    ".............######.............",
    "..############################..",
    "..############################..",
    "..############################..",
    "..############################..",
    ".....#######################....",
    "......######################....",
    ".......##################.......",
    ".......#################........",
    ".........##############.........",
    ".........##############.........",
    ".........##############.........",
    ".........###############........",
    ".........################.......",
    ".......##################.......",
    ".......########.#########.......",
    ".......#####........#####.......",
    ".......#####........#####.......",
    ".....#####............####......",
    "......####............####......",
    "................................",
    "................................",
]


def test_a_star_is_no_shafted_arrow():
    mask = [[1 if cell == "#" else 0 for cell in row] for row in STAR]
    assert marks._shafted_arrow(marks._tight(marks._drop_specks(mask))) is None
