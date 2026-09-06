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
    texts = ["we have $v_{p}(\Theta_{0})\notin$", "$\{-1,0\}$ is small"]
    assert join_lines(lines, texts) == "we have $v_{p}(\Theta_{0})\notin \{-1,0\}$ is small"
