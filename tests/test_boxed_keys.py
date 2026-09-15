"""A key that draws a sample before each of its lines holds separate entries, not one run of text.

A plot legend is a stroked box of short lines of text, and the boxed-cells rule read the legend in each of arxiv
2503.04674's convergence plots as a card: "Gauss (s=1)" over "Radau IIA (s=2)" over "Gauss (s=2)" folded into one cell,
and each method lost the marker drawn beside it. What a card's wrapped name never has is a drawn sample leading each line.
"""
from truedoc.tables import boxed_cells as bc

# The legend's lines and samples as the rule reads them on that page: the words start at 118.9pt, and a stroke 11.2pt long
# ends 1.2pt before them at the middle of each line.
LEGEND = [bc._Held(y0=351.6, y1=356.8, size=5.4, text="Gauss (s=1)", x0=118.9, x1=148.3),
          bc._Held(y0=358.4, y1=363.5, size=5.4, text="Radau IIA (s=2)", x0=118.9, x1=156.6),
          bc._Held(y0=365.1, y1=370.2, size=5.4, text="Gauss (s=2)", x0=118.9, x1=148.3)]
SAMPLES = [{"orientation": "h", "x0": 106.5, "x1": 117.7, "top": y, "bottom": y} for y in (353.8, 360.5, 367.2)]

# Budget Direct's card: the name on two lines, and strokes of the armchair drawn to the right of it.
NAME = [bc._Held(y0=219.3, y1=230.7, size=10.0, text="Unspecified", x0=58.8, x1=115.1),
        bc._Held(y0=231.3, y1=242.7, size=10.0, text="Personal Effects", x0=58.8, x1=134.0)]
ICON = [{"orientation": "h", "x0": 176.7, "x1": 179.8, "top": 228.7, "bottom": 228.7},
        {"orientation": "h", "x0": 174.5, "x1": 181.9, "top": 238.6, "bottom": 238.6}]


def test_a_key_with_a_sample_before_each_line_is_not_one_run():
    assert bc._one_run(LEGEND, [])
    assert not bc._one_run(LEGEND, SAMPLES)


def test_an_icon_drawn_beside_a_name_leads_no_line():
    assert bc._one_run(NAME, ICON)
