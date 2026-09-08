"""A column gutter is found under a full-width head, and lines joined across it are split.

A Physical Review Letters page sets its title, authors and abstract across both columns and
then two justified columns 16 points apart; MuPDF joins ten body lines across that gutter
("...the refractive index is modu-" + "vector k to photons..."), and the head's lines cross it
too, so the strict channel scan (no more than three lines in a hundred may cross) found no
gutter and the two columns read as one (0145cc39b0 and 52 more pages in run 60). The columns'
edges show it: a quarter of the lines start at the right column's edge and end at the left one's.
A line's word gap splits at such a gutter only when it covers most of it: the head's ordinary
word spaces do not.
"""
from tests.test_columns import line, two_column_page, word
from truedoc.extract.textlayer import _column_gutters, _split_at_gutters


def _full_width(text, oy, x0=60.0, space=6.0):
    """A line set across both columns with ordinary word spaces (0.6 em)."""
    x = x0
    words = []
    for w in text.split():
        words.append(word(w, x, oy, char_w=4.0))
        x += len(w) * 4.0 + space
    return line(*words)


def _page_with_head_and_merged_lines():
    lines = two_column_page(rows=24)
    head = [_full_width("Mode Softening, Ferroelectric Transition, and Tunable Photonic Band Structure", 40),
            _full_width("in a Point-Dipole Crystal of Coupled Emitters and Cavities", 52),
            _full_width("J. A. Klugkist, M. Mostovoy, and J. Knoester, Zernike Institute", 64),
            _full_width("We study the photonic band structure of cubic crystals of point dipoles", 76),
            _full_width("and show that the mode softening and ferroelectric transition tune it.", 88)]
    # MuPDF joined six rows' two segments into one line each.
    merged = []
    for i in range(0, 12, 2):
        left, right = lines[2 * i], lines[2 * i + 1]
        merged.append(line(*(left.words + right.words)))
    kept = [l for j, l in enumerate(lines) if j // 2 not in {0, 2, 4, 6, 8, 10}]
    return head + merged + kept, merged


def test_gutter_found_under_a_full_width_head():
    lines, merged = _page_with_head_and_merged_lines()
    gutters = _column_gutters(lines)
    assert len(gutters) == 1 and 246 <= gutters[0][0] <= 252 and 260 <= gutters[0][1] <= 266, gutters


def test_joined_lines_split_at_the_gutter_and_the_head_does_not():
    lines, merged = _page_with_head_and_merged_lines()
    gutters = _column_gutters(lines)
    out = _split_at_gutters(lines, gutters)
    texts = [l.text for l in out]
    assert not any("amet quis" in t or "sed laboris" in t or "incididunt ea" in t for t in texts), "columns joined"
    assert sum(1 for l in out if l.bbox.x1 <= 252) >= 24 and sum(1 for l in out if l.bbox.x0 >= 260) >= 24
    assert "Mode Softening, Ferroelectric Transition, and Tunable Photonic Band Structure" in texts
    assert "in a Point-Dipole Crystal of Coupled Emitters and Cavities" in texts


def test_a_single_column_page_has_no_gutter():
    # Justified lines of one column: their word gaps fall at different places from line to line.
    texts = ["lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor",
             "incididunt ut labore et dolore magna aliqua enim ad minim veniam quis nostrud",
             "exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat duis aute",
             "irure dolor in reprehenderit voluptate velit esse cillum dolore eu fugiat nulla",
             "pariatur excepteur sint occaecat cupidatat non proident sunt in culpa qui officia"]
    lines = []
    for i in range(30):
        ws = texts[i % 5].split()
        space = (410 - sum(len(w) for w in ws) * 4.0) / (len(ws) - 1)
        x = 50.0
        words = []
        for w in ws:
            words.append(word(w, x, 100 + 12 * i, char_w=4.0))
            x += len(w) * 4.0 + space
        lines.append(line(*words))
    assert _column_gutters(lines) == []
