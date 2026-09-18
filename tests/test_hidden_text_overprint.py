"""An earlier wording left under a row's shading, with the present sentence printed over it (D011).

Found 18 September 2026 by reading our conversions of Key Facts Sheets against a model's and then
against the page: "entered" (GIO), "item." (Apia) and "s at:" (Seniors, Real) stood in the body of
sheets that do not print them. Each is in the PDF, painted first, then the table row's opaque
shading over it, then the visible sentence over the same spot. Three things let them through, and
each has a case here, read by both libraries:

  * the shading is as tall as the line, which covers every stroke of a character and 87% of its
    font box - and the test asked for 90% of the box;
  * the render check overturned a correct "covered" verdict because the patch showed ink: the ink
    of the sentence printed over it;
  * a hidden full stop and a letter of the visible sentence shared an origin to half a point, and
    characters were matched to their paint order by position alone, so the full stop was judged
    by the visible letter's.
"""

import pytest

from test_hidden_text_readers import _pdf, _read  # noqa: F401  (the same page builder and both readers)

# A row of a table: an old word, the row's light-blue shading over it (12 points tall, the height
# of the line: Helvetica at 12 points has a font box of about 13.7), then the sentence that is
# actually printed, starting at the same spot.
_BAND = b"0.72 0.82 0.93 rg 45 597.5 240 12 re f\n"
_OVERPRINTED = (
    b"BT /F1 12 Tf 0 Tr 0 0 0 rg 50 700 Td (Heading) Tj ET\n"
    b"BT /F1 12 Tf 0 Tr 0 0 0 rg 50 600 Td (entered) Tj ET\n" + _BAND +
    b"BT /F1 12 Tf 0 Tr 0 0 0 rg 50 600 Td (the insured address) Tj ET\n"
)
_BURIED_ALONE = (
    b"BT /F1 12 Tf 0 Tr 0 0 0 rg 50 700 Td (Heading) Tj ET\n"
    b"BT /F1 12 Tf 0 Tr 0 0 0 rg 50 600 Td (entered) Tj ET\n" + _BAND +
    b"BT /F1 12 Tf 0 Tr 0 0 0 rg 150 600 Td (elsewhere) Tj ET\n"
)
# "item." is 22.668 + 3.336 points wide in Helvetica 12; its full stop starts at x = 72.668, and so
# does the "t" of the visible text, set there on purpose.
_SHARED_ORIGIN = (
    b"BT /F1 12 Tf 0 Tr 0 0 0 rg 50 700 Td (Heading) Tj ET\n"
    b"BT /F1 12 Tf 0 Tr 0 0 0 rg 50 600 Td (item.) Tj ET\n" + _BAND +
    b"BT /F1 12 Tf 0 Tr 0 0 0 rg 50 600 Td (Ear) Tj ET\n"
    b"BT /F1 12 Tf 0 Tr 0 0 0 rg 72.668 600 Td (thquake) Tj ET\n"
)


def _hidden_and_visible(pdfium: bool, content: bytes):
    page = _read(pdfium, content)
    hidden = {h["text"].strip(): h["reason"] for h in page.hidden_text}
    return hidden, " ".join(w.text for w in page.words)


@pytest.mark.parametrize("pdfium", [True, False], ids=["pdfium", "mupdf"])
def test_a_word_under_the_shading_with_the_sentence_printed_over_it_stays_hidden(pdfium):
    hidden, visible = _hidden_and_visible(pdfium, _OVERPRINTED)
    assert hidden == {"entered": "covered"}
    assert "entered" not in visible and "insured" in visible and "Heading" in visible


@pytest.mark.parametrize("pdfium", [True, False], ids=["pdfium", "mupdf"])
def test_shading_as_tall_as_the_line_covers_the_word_under_it(pdfium):
    hidden, visible = _hidden_and_visible(pdfium, _BURIED_ALONE)
    assert hidden == {"entered": "covered"}             # its ink is covered, though 87% of its font box is
    assert "entered" not in visible and "elsewhere" in visible


@pytest.mark.parametrize("pdfium", [True, False], ids=["pdfium", "mupdf"])
def test_a_hidden_full_stop_is_not_judged_by_the_visible_letter_at_the_same_spot(pdfium):
    hidden, visible = _hidden_and_visible(pdfium, _SHARED_ORIGIN)
    assert hidden == {"item.": "covered"}               # the full stop went with its word
    assert "item" not in visible and "." not in visible.replace("...", "")


def test_text_printed_on_the_shading_is_still_read():
    # The ordinary case must not move: shading first, then the words on it.
    content = (b"0.72 0.82 0.93 rg 45 597.5 240 12 re f\n"
               b"BT /F1 12 Tf 0 Tr 0 0 0 rg 50 600 Td (Flood is covered) Tj ET\n")
    for pdfium in (True, False):
        hidden, visible = _hidden_and_visible(pdfium, content)
        assert hidden == {} and "Flood" in visible and "covered" in visible
