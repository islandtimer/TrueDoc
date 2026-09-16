"""A filled disc or square is a bullet: it belongs to the list element, not to the entry's words (D028).

The dingbat rule reads a Wingdings bullet by what it draws, and the mark reader writes a dot as "●" and a square as
"■". `cell_lists` knew the small bullets and not those, so every entry of Woolworths' target market determination came
out as "<li>● Fire and explosion;</li>" - the glyph said twice what the element already says. A tick or a cross stays
with its words, because it says whether the entry is covered; a hollow box or circle stays too, because an empty box
is how a form draws an answer not given.
"""
from truedoc.tables.cell_lists import build_listing, is_list

from tests.test_cell_lists import _line


def _listing(mark):
    lines = [_line(20, 0, "{} Fire and explosion;".format(mark), indent=32),
             _line(20, 12, "{} Malicious damage;".format(mark), indent=32),
             _line(20, 24, "{} Escape of liquid.".format(mark), indent=32)]
    listing = build_listing(lines)
    assert listing is not None and is_list(listing)
    return [item.text for item in listing.items]


def test_a_disc_belongs_to_the_element():
    assert _listing("●") == ["Fire and explosion;", "Malicious damage;", "Escape of liquid."]


def test_a_filled_square_belongs_to_the_element():
    assert _listing("■") == ["Fire and explosion;", "Malicious damage;", "Escape of liquid."]


def test_a_small_bullet_still_belongs_to_the_element():
    assert _listing("•") == ["Fire and explosion;", "Malicious damage;", "Escape of liquid."]


def test_a_tick_stays_with_its_words():
    assert _listing("✓") == ["✓ Fire and explosion;", "✓ Malicious damage;", "✓ Escape of liquid."]


def test_an_empty_box_stays_with_its_words():
    """An unticked box is an answer not given; dropping it would drop the answer."""
    assert _listing("□") == ["□ Fire and explosion;", "□ Malicious damage;", "□ Escape of liquid."]
