"""A line in the margin reading "page N" is the page's own number only if it counts pages.

The zone rule takes any block reading just "page N", "N" or "N of M" in the top or bottom strip for the page's number,
and the renderer leaves page numbers out. Budget Direct's home PDS ends a card on PDF page 8 with the pointer
"page 52", 41pt above the foot, and it was published nowhere. A page number counts pages: the pages beside it print
theirs at the same distance from their place in the file. Where the pages beside it agree on that distance and the
line is not at it, the line is text - unless a page beside it prints the same line at the same place, as RACQ prints
its section tab "1" two pages on, which makes it a running head all the same. Where nothing beside it can say - a file
of one page - the zone rule stands.
"""
import pymupdf

from truedoc.classify.page_numbers import counts_pages
from truedoc.extract.handle import open_pdf
from truedoc.pipeline import ConvertOptions, convert

BODY = [
    "Landlord Options cover what a tenant leaves behind.",
    "Tenant default and theft and malicious damage are both included.",
    "Read the policy wording for the limits that apply to each option.",
]


def _pdf(tmp_path, pages):
    """A file of 400 x 570pt pages, each drawn from (x, baseline, text) pieces at 9pt."""
    doc = pymupdf.open()
    for pieces in pages:
        page = doc.new_page(width=400, height=570)
        for x, y, text in pieces:
            page.insert_text((x, y), text, fontsize=9)
    path = tmp_path / "doc.pdf"
    doc.save(str(path))
    doc.close()
    return str(path)


def _body(y=200):
    return [(60, y + 14 * i, line) for i, line in enumerate(BODY)]


def _convert(path, number):
    return convert(path, ConvertOptions(frontmatter=False, pages=[number], layout=False))


def test_a_pointer_in_the_foot_that_does_not_count_pages_is_kept(tmp_path):
    # PDF pages 1 to 3 print 5, 6 and 7 at the top; page 2 ends with a pointer to page 52.
    path = _pdf(tmp_path, [
        [(30, 40, "5")] + _body(),
        [(30, 40, "6")] + _body() + [(60, 528, "page 52")],
        [(30, 40, "7")] + _body(),
    ])
    md = _convert(path, 2)
    assert "page 52" in md
    assert "6" not in md.split()


def test_a_page_number_that_counts_pages_is_still_left_out(tmp_path):
    path = _pdf(tmp_path, [_body() + [(170, 528, f"Page {n} of 3")] for n in (1, 2, 3)])
    md = _convert(path, 2)
    assert "Landlord Options" in md
    assert "Page 2 of 3" not in md


def test_a_number_that_runs_like_a_head_stays_out(tmp_path):
    # Five pages number themselves "Page 5" to "Page 9" at the foot, and pages 1, 3 and 5 carry a section tab "1" in
    # the top corner. The tab counts no pages, but page 3's is printed again at the same place two pages each way.
    pages = []
    for n in range(1, 6):
        pieces = _body() + [(170, 548, f"Page {n + 4}")]
        if n % 2:
            pieces.append((370, 40, "1"))
        pages.append(pieces)
    md = _convert(_pdf(tmp_path, pages), 3)
    assert "Landlord Options" in md
    assert "1" not in md.split()
    assert "Page 7" not in md


def test_a_file_of_one_page_keeps_the_zone_rule(tmp_path):
    # Nothing beside the page can say whether "page 52" counts pages, so it goes as a page number, as before.
    path = _pdf(tmp_path, [_body() + [(60, 528, "page 52")]])
    md = _convert(path, 1)
    assert "Landlord Options" in md
    assert "page 52" not in md


def test_pages_beside_it_that_disagree_say_nothing(tmp_path):
    path = _pdf(tmp_path, [[(30, 40, n)] + _body() for n in ("5", "6", "9")])
    doc = open_pdf(path)
    try:
        assert counts_pages("6", doc[1]) is None
        assert counts_pages("page 52", doc[1]) is None
    finally:
        doc.close()
