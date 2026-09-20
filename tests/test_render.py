from truedoc.model import BBox, Char, Line, Table, TableCell, Word
from truedoc.render.okf import join_lines, render_table


def _line(text: str, y: float = 0.0) -> Line:
    words = []
    x = 0.0
    for tok in text.split():
        chars = [Char(text=c, bbox=BBox(x + i * 5, y, x + (i + 1) * 5, y + 10), font="F", size=10, origin_y=y + 8) for i, c in enumerate(tok)]
        words.append(Word(text=tok, bbox=BBox(x, y, x + 5 * len(tok), y + 10), chars=chars))
        x += 5 * len(tok) + 5
    return Line(words=words, bbox=BBox(0, y, x, y + 10))


def test_join_lines_dehyphenates_ordinary_word():
    assert join_lines([_line("the conver-"), _line("sion works")]) == "the conversion works"


def test_join_lines_keeps_hyphen_before_capital():
    assert join_lines([_line("the COVID-"), _line("19 era")]) == "the COVID-19 era"


def test_join_lines_keeps_hyphen_in_compound():
    assert join_lines([_line("a state-of-"), _line("the-art tool")]) == "a state-of-the-art tool"


def test_join_lines_keeps_a_suspended_hyphen_and_its_space():
    assert join_lines([_line("both pre-"), _line("and post-natal care")]) == "both pre- and post-natal care"
    assert join_lines([_line("from two-"), _line("to three-fold")]) == "from two- to three-fold"


def test_join_lines_halves_that_make_a_word_are_the_word_even_before_a_function_word():
    # "spir-" / "it" was written "spir- it": the function word was asked about before the word list.
    assert join_lines([_line("in the spir-"), _line("it of the agreement")]) == "in the spirit of the agreement"
    assert join_lines([_line("cancel with-"), _line("in 14 days")]) == "cancel within 14 days"


def test_render_table_simple():
    cells = [
        TableCell("Name", 0, 0, is_header=True),
        TableCell("Value", 0, 1, is_header=True),
        TableCell("a", 1, 0),
        TableCell("1", 1, 1),
    ]
    t = Table(n_rows=2, n_cols=2, cells=cells, bbox=BBox(0, 0, 10, 10))
    md = render_table(t)
    assert md.splitlines()[0] == "| Name | Value |"
    assert md.splitlines()[2] == "| a | 1 |"


def test_render_table_merged_uses_html():
    cells = [
        TableCell("Head", 0, 0, colspan=2, is_header=True),
        TableCell("a", 1, 0),
        TableCell("1", 1, 1),
    ]
    t = Table(n_rows=2, n_cols=2, cells=cells, bbox=BBox(0, 0, 10, 10), has_merged=True)
    html = render_table(t)
    assert 'colspan="2"' in html and html.startswith("<table>")


def test_empty_document_renders_empty_file():
    from truedoc.model import Document, Page
    from truedoc.render.okf import RenderOptions, render_document

    doc = Document(path="x.pdf", pages=[Page(number=1, width=100, height=100)])
    assert render_document(doc, RenderOptions(frontmatter=False)) == ""


def test_inline_formula_broken_across_lines_is_rejoined():
    from truedoc.render.okf import join_lines

    lines = [_line("we have v"), _line("x is small")]
    texts = ["we have \\(v_{p}(\Theta_{0})\notin\\)", "\\(\{-1,0\}\\) is small"]
    assert join_lines(lines, texts) == "we have \\(v_{p}(\Theta_{0})\notin \{-1,0\}\\) is small"


def test_join_lines_a_grade_and_its_minus_are_not_half_a_word():
    # "C-" / "or ECON 402H": the word list holds "cor". One letter is not half of a broken word.
    assert join_lines([_line("with a minimum grade of C-"), _line("or ECON 402H")]) == "with a minimum grade of C- or ECON 402H"


def test_join_lines_one_letter_and_a_hyphen_is_the_head_of_a_compound():
    # No word is broken after its first letter: "Deep Q-" / "network" was written "Deep Qnetwork".
    assert join_lines([_line("policy algorithm, Deep Q-"), _line("network (DQN)")]) == "policy algorithm, Deep Q-network (DQN)"
    assert join_lines([_line("benefits of L-"), _line("carnitine in athletes")]) == "benefits of L-carnitine in athletes"
    assert join_lines([_line("comprising a s-"), _line("ingle object")]) == "comprising a single object"     # unless the halves are a word


def test_a_table_inside_a_cell_is_written_as_a_table_inside_the_cell():
    # D038 (the owner, 20 September 2026): CGU's "High value items and collections | Yes | [Policy / Item Limit / ...]".
    inner = Table(n_rows=2, n_cols=3, bbox=BBox(0, 0, 10, 10), cells=[
        TableCell("Policy", 0, 0, is_header=True), TableCell("Item Limit", 0, 1, is_header=True), TableCell("Overall Limit", 0, 2, is_header=True),
        TableCell("Fundamentals Home", 1, 0), TableCell("$1,000/item", 1, 1), TableCell("$2,000", 1, 2)])
    outer = Table(n_rows=2, n_cols=3, bbox=BBox(0, 0, 10, 10), cells=[
        TableCell("Event/Cover", 0, 0, is_header=True), TableCell("Yes/No Optional", 0, 1, is_header=True), TableCell("Some examples", 0, 2, is_header=True),
        TableCell("High value items and collections", 1, 0), TableCell("Yes", 1, 1),
        TableCell("Policy Item Limit Overall Limit Fundamentals Home $1,000/item $2,000", 1, 2, inner=inner)])
    md = render_table(outer)
    assert md.startswith("<table>") and md.count("<table>") == 2
    assert ("<td><table><tr><th>Policy</th><th>Item Limit</th><th>Overall Limit</th></tr>"
            "<tr><td>Fundamentals Home</td><td>$1,000/item</td><td>$2,000</td></tr></table></td>") in md
    assert "<th>Event/Cover</th>" in md and "<td>Yes</td>" in md
