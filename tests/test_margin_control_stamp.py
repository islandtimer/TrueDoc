"""A document-control stamp at the head of a page is furniture, even as a small table.

A specification sheet opens with "CM-FECL3 -E | issued: 2019-04-17", "Revision 2 | reviewed: --",
"supersedes: Revision 1 | dated: 2016-09-06" above its title. The aligned finder reads the three
rows as a table, and a table is never a running head, so the stamp stayed in the body and cost
five checks in run 50. A table of a few short key: value cells in the head of the page, above
the page's first heading, is the stamp; a real table further down keeps its place.
"""
from truedoc.model import BBox, Block, BlockKind, Char, Line, Page, Table, TableCell, Word
from truedoc.pipeline import _margin_cleanup

SIZE = 8.0


def _line(text, x0, y0):
    chars = [Char(text=c, bbox=BBox(x0 + i * 4.0, y0, x0 + (i + 1) * 4.0, y0 + SIZE), font="F", size=SIZE, origin_y=y0 + 0.8 * SIZE) for i, c in enumerate(text)]
    return Line(words=[Word(text=text, bbox=BBox(x0, y0, x0 + 4.0 * len(text), y0 + SIZE), chars=chars)], bbox=BBox(x0, y0, x0 + 4.0 * len(text), y0 + SIZE))


def _table(rows, bbox):
    cells = [TableCell(text=t, row=r, col=c, is_header=(r == 0)) for r, row in enumerate(rows) for c, t in enumerate(row)]
    table = Table(n_rows=len(rows), n_cols=len(rows[0]), cells=cells, bbox=bbox, provenance="textlayer-aligned")
    return Block(kind=BlockKind.TABLE, bbox=bbox, table=table, provenance="textlayer-aligned", confidence=0.7)


def test_control_stamp_table_at_the_head_is_furniture_and_a_body_table_is_not():
    page = Page(number=1, width=595, height=842)
    page.body_font_size = SIZE
    stamp = _table([["CM-FECL3 -E", "issued: 2019-04-17"], ["Revision 2", "reviewed: --"], ["supersedes: Revision 1", "dated: 2016-09-06"]], BBox(43, 81, 315, 115))
    title = Block(kind=BlockKind.HEADING, bbox=BBox(43, 142, 186, 156), lines=[_line("Product Specification", 43, 142)])
    para = Block(kind=BlockKind.TEXT, bbox=BBox(43, 170, 500, 190), lines=[_line("Ferric chloride anhydrous is supplied as a dark solid in drums of 25 kg net weight.", 43, 170),
                                                                            _line("It is hygroscopic and must be kept sealed until use in the treatment plant.", 43, 181)])
    body_table = _table([["Parameter", "Unit", "Specification"], ["FeCl3", "g/100g", "min. 96"], ["Fe2+", "g/100g", "max. 0.5"], ["Insolubles", "g/100g", "max. 1.0"]], BBox(43, 389, 500, 558))
    blocks = [stamp, title, para, body_table]
    page.lines = [l for b in blocks for l in b.lines]
    _margin_cleanup(page, blocks)
    assert stamp.kind == BlockKind.HEADER
    assert body_table.kind == BlockKind.TABLE
    assert title.kind == BlockKind.HEADING and para.kind == BlockKind.TEXT
