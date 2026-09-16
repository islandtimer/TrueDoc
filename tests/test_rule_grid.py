"""A table whose columns hold only drawn marks is read from its own rules when the layout model boxes it.

QBE's home PDS page 16 sets which cover each change concerns as a column of situations beside two columns that hold only
a drawn tick or cross, with a rule under the header and under every row, each rule stroked in pieces that meet at the
column edges, and no vertical rules. The layout model boxed it as a table, but the text inside the box built none - the
mark columns hold no text - so the rows came out as headings and paragraphs and the marks were lost. Each test draws
such a page with PyMuPDF; the first gives the pipeline the model's table box (the model itself is not run) and converts
it, the second asks the grid for its cells directly.

RAC's premium, excess and discount guide sets the same kind of table another way: each rule stroked in three pieces
that stop 1.5pt short of one another at the column edges, and the header in a filled band with no rule under it, so
the first rule lies under the first row. The rest of the tests draw that page.
"""
import pymupdf

from truedoc import pipeline
from truedoc.layout.base import Region, RegionKind
from truedoc.model import BBox, Line
from truedoc.pipeline import ConvertOptions, convert, process_page
from truedoc.tables.rule_grid import table_from_rules

HEADER_Y = 70
RULES = [80, 104, 140, 164]
EDGES = [40, 230, 300, 370]
REGION = BBox(38, 58, 372, 166)


def _tick(page, x, y, s=8, color=(0.2, 0.6, 0.9)):
    # A check mark: short stroke down-right, long stroke up-right.
    page.draw_polyline([(x, y + 0.5 * s), (x + 0.35 * s, y + 0.9 * s), (x + s, y)], color=color, width=1.6)


def _cross(page, x, y, s=8, color=(0.2, 0.6, 0.9)):
    page.draw_line((x, y), (x + s, y + s), color=color, width=1.6)
    page.draw_line((x, y + s), (x + s, y), color=color, width=1.6)


def _pdf(tmp_path):
    doc = pymupdf.open()
    page = doc.new_page(width=400, height=300)
    page.insert_text((44, HEADER_Y), "When to update", fontsize=10)
    page.insert_text((234, HEADER_Y), "Buildings", fontsize=10)
    page.insert_text((304, HEADER_Y), "Contents", fontsize=10)
    for y in RULES:
        # each rule in three strokes overlapping a little at the column edges, as QBE's page draws them
        page.draw_line((EDGES[0], y), (EDGES[1] + 0.5, y), color=(0.1, 0.3, 0.6), width=0.5)
        page.draw_line((EDGES[1], y), (EDGES[2] + 0.5, y), color=(0.1, 0.3, 0.6), width=0.5)
        page.draw_line((EDGES[2], y), (EDGES[3], y), color=(0.1, 0.3, 0.6), width=0.5)
    page.insert_text((44, 96), "Alterations or renovations", fontsize=10)
    _tick(page, 261, 88)
    _tick(page, 331, 88)
    page.insert_text((44, 118), "If you find you are underinsured", fontsize=10)
    page.insert_text((44, 131), "after a valuation", fontsize=10)
    _tick(page, 261, 118)
    _tick(page, 331, 118)
    page.insert_text((44, 156), "You buy jewellery or art", fontsize=10)
    _cross(page, 261, 148)
    _tick(page, 331, 148)
    path = tmp_path / "rule_grid.pdf"
    doc.save(str(path))
    doc.close()
    return str(path)


def _rows(md):
    return [[c.strip() for c in l.strip().strip("|").split("|")]
            for l in md.splitlines() if l.startswith("|") and "---" not in l]


def test_a_table_of_marks_is_read_from_its_own_rules(tmp_path, monkeypatch):
    path = _pdf(tmp_path)
    region = Region(kind=RegionKind.TABLE, bbox=REGION, score=0.95, source="test")
    monkeypatch.setattr(pipeline, "_detect_layout", lambda pdf_page, opts, page=None: [region])
    md = convert(path, ConvertOptions(frontmatter=False, layout=True, ocr=False))
    rows = _rows(md)
    assert ["Alterations or renovations", "✓", "✓"] in rows, md
    assert ["If you find you are underinsured after a valuation", "✓", "✓"] in rows, md
    assert ["You buy jewellery or art", "✗", "✓"] in rows, md


def test_a_word_the_reader_reports_twice_at_one_place_is_read_once(tmp_path):
    # QBE's page 11: the reader gives "contents cover" inside a longer header line and again as a line of its own.
    doc = pymupdf.open(_pdf(tmp_path))
    try:
        pdf_page = doc[0]
        page = process_page(pdf_page, 1, ConvertOptions(layout=False, ocr=False, marks=False, math=False))
        heading = next(l for l in page.lines if l.text == "Contents")
        page.lines.append(Line(words=list(heading.words), bbox=heading.bbox))
        result = table_from_rules(page, pdf_page, REGION, page.body_font_size)
    finally:
        doc.close()
    assert result is not None
    table, _ = result
    assert next(c.text for c in table.cells if c.row == 0 and c.col == 2) == "Contents"


BAND = (58, 80)                 # the header's filled band
ROW_RULES = [102, 122, 142]     # a rule under each row, none under the header
BANDED_REGION = BBox(38, 56, 372, 146)
PRICING = [("Location of your building", 94), ("The sum you are insured for", 114), ("Your age", 134)]


def _banded_pdf(tmp_path, gap):
    doc = pymupdf.open()
    page = doc.new_page(width=400, height=300)
    page.draw_rect(pymupdf.Rect(EDGES[0], BAND[0], EDGES[3], BAND[1]), color=None, fill=(0.47, 0.55, 0.6))
    page.draw_rect(pymupdf.Rect(EDGES[0], BAND[1], EDGES[3], ROW_RULES[-1]), color=None, fill=(0.91, 0.91, 0.91))
    page.insert_text((44, HEADER_Y), "Pricing factors", fontsize=10)
    page.insert_text((234, HEADER_Y), "Buildings", fontsize=10)
    page.insert_text((304, HEADER_Y), "Contents", fontsize=10)
    for y in ROW_RULES:
        # each rule in three strokes that stop `gap` short of one another at the column edges
        page.draw_line((EDGES[0], y), (EDGES[1] - gap / 2, y), color=(0.4, 0.4, 0.4), width=0.5)
        page.draw_line((EDGES[1] + gap / 2, y), (EDGES[2] - gap / 2, y), color=(0.4, 0.4, 0.4), width=0.5)
        page.draw_line((EDGES[2] + gap / 2, y), (EDGES[3], y), color=(0.4, 0.4, 0.4), width=0.5)
    for label, baseline in PRICING:
        page.insert_text((44, baseline), label, fontsize=10)
        _tick(page, 261, baseline - 8)
        _tick(page, 331, baseline - 8)
    path = tmp_path / f"banded_grid_{gap}.pdf"
    doc.save(str(path))
    doc.close()
    return str(path)


def _banded_grid(tmp_path, gap):
    doc = pymupdf.open(_banded_pdf(tmp_path, gap))
    try:
        pdf_page = doc[0]
        page = process_page(pdf_page, 1, ConvertOptions(layout=False, ocr=False, marks=False, math=False))
        result = table_from_rules(page, pdf_page, BANDED_REGION, page.body_font_size)
    finally:
        doc.close()
    if result is None:
        return None
    table, _ = result
    return [[c.text for c in sorted((c for c in table.cells if c.row == r), key=lambda c: c.col)]
            for r in range(table.n_rows)]


def test_rule_pieces_a_little_apart_still_meet_at_a_column_edge(tmp_path):
    grid = _banded_grid(tmp_path, gap=1.5)
    assert grid is not None
    assert grid[0] == ["Pricing factors", "Buildings", "Contents"]


def test_rule_pieces_standing_well_apart_do_not_meet(tmp_path):
    # 6pt apart at 10pt text is more than a word space: the pieces are separate rules, not one stroked in pieces.
    assert _banded_grid(tmp_path, gap=6.0) is None


def test_a_header_set_in_a_filled_band_ends_where_the_band_does(tmp_path):
    # The pieces touch, so only the band can keep the first row out of the header.
    grid = _banded_grid(tmp_path, gap=0.0)
    assert grid == [["Pricing factors", "Buildings", "Contents"]] + [[label, "", ""] for label, _ in PRICING]


def test_a_banded_table_of_marks_is_read_from_its_rules(tmp_path, monkeypatch):
    path = _banded_pdf(tmp_path, gap=1.5)
    region = Region(kind=RegionKind.TABLE, bbox=BANDED_REGION, score=0.85, source="test")
    monkeypatch.setattr(pipeline, "_detect_layout", lambda pdf_page, opts, page=None: [region])
    md = convert(path, ConvertOptions(frontmatter=False, layout=True, ocr=False))
    rows = _rows(md)
    assert rows == [["Pricing factors", "Buildings", "Contents"]] + [[label, "✓", "✓"] for label, _ in PRICING], md
