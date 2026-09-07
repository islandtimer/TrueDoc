"""A dichotomous key is a two-column table: long leads on the left, short names on the right.

A flora's key sets each lead ("A. Glands of the involucre ovate, elliptic or nearly round in
cross-section", "aa. Glands kidney-shaped or crescent-shaped, concave side outside") beside the
species or the next lead it points to ("Euphorbia helioscopia", "B"). The prose rejection reads
the long leads as body text and drops the table (tables/b74ef859, 4 checks in run 48). Every
lead starts with an enumerator and every right cell is a short label: that is a key, not prose.
A column of prose beside margin line numbers, the mirror image, stays prose.
"""
from truedoc.model import BBox, Char, Line, Page, Word
from truedoc.tables.aligned import find_aligned_tables

SIZE = 11.0


def _seg(text, x0, x1, y0):
    cw = (x1 - x0) / max(1, len(text))
    chars = [Char(text=c, bbox=BBox(x0 + i * cw, y0, x0 + (i + 1) * cw, y0 + SIZE), font="F", size=SIZE, origin_y=y0 + 0.8 * SIZE) for i, c in enumerate(text)]
    words = []
    x = x0
    for tok in text.split(" "):
        w = cw * len(tok)
        words.append(Word(text=tok, bbox=BBox(x, y0, x + w, y0 + SIZE), chars=[c for c in chars if x <= c.bbox.x0 < x + w + 0.01]))
        x += w + cw
    return Line(words=words, bbox=BBox(x0, y0, x1, y0 + SIZE))


def _page(lines):
    page = Page(number=1, width=612, height=792)
    page.lines = lines
    page.body_font_size = SIZE
    return page


LEADS = [
    ("A. Glands of the involucre ovate, elliptic or nearly round in cross-section", "Euphorbia helioscopia"),
    ("aa. Glands kidney-shaped or crescent-shaped, concave side outside", "B"),
    ("B. Rays of the cyathium umbel three or more, leaves alternate below", "C"),
    ("bb. Rays of the cyathium umbel two, leaves opposite throughout", "E. peplus"),
    ("C. Seeds pitted or wrinkled, capsule warty on the keels", "E. exigua"),
]


def test_key_of_leads_and_names_is_a_table():
    lines = []
    for i, (lead, name) in enumerate(LEADS):
        y = 641 + 14 * i
        lines.append(_seg(lead, 60, 60 + 4.9 * len(lead), y))
        lines.append(_seg(name, 470, 470 + 5.2 * len(name), y))
    tables, _ = find_aligned_tables(_page(lines), lines, SIZE)
    assert len(tables) == 1
    t = tables[0].table
    assert (t.n_rows, t.n_cols) == (5, 2)
    texts = {(c.row, c.col): c.text for c in t.cells}
    assert texts[(0, 1)] == "Euphorbia helioscopia" and texts[(3, 1)] == "E. peplus"
    assert texts[(1, 0)].startswith("aa. Glands")


def test_prose_beside_line_numbers_is_still_prose():
    lines = []
    for i in range(6):
        y = 200 + 14 * i
        lines.append(_seg(str(400 + i), 20, 38, y))
        lines.append(_seg("Body text of a manuscript page runs on beside the line numbers in the margin", 60, 480, y))
    tables, _ = find_aligned_tables(_page(lines), lines, SIZE)
    assert tables == []
