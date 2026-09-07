"""A picture's answer is split into transcription and description (session 3, 8 September 2026).

Of the 50 crop readings olmOCR 2 returned for pictures on digital pages, 22 were a single image
reference whose alt text describes the picture ("![Scatter plot showing ...](...)"): that is a
description and belongs in the figure's alt text (D015), not in the body. A transcription may
also carry such a line for a chart beside the text; it is taken out and the text kept.
"""
from truedoc.vision.regions import split_picture_answer


def test_image_only_answer_is_a_description():
    text, desc = split_picture_answer("![Scatter plot showing the proportion exclusive area versus density of resident females.](page_1.png)")
    assert text is None
    assert desc == "Scatter plot showing the proportion exclusive area versus density of resident females."


def test_table_answer_is_a_transcription():
    table = "<table>\n<tr><th>YEAR-TO-DATE</th><th>PAID TIME OFF</th></tr>\n<tr><td>Start Balance</td><td>0.0</td></tr>\n</table>"
    text, desc = split_picture_answer(table)
    assert text == table and desc is None


def test_image_line_inside_a_transcription_is_taken_out():
    text, desc = split_picture_answer("Table 3. Results by site\n\n![Bar chart of yields](chart.png)\n\n| Site | Yield |\n|---|---|\n| A | 12 |")
    assert "![" not in text and text.startswith("Table 3. Results by site") and text.endswith("| A | 12 |")
    assert desc == "Bar chart of yields"


def test_nothing_readable():
    assert split_picture_answer("") == (None, None)
    assert split_picture_answer("![](x.png)") == (None, None)
    assert split_picture_answer("A B") == (None, None)    # fewer than three words
