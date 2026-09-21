"""Two issues of one document, matched page by page (D040): what carries over, what must be checked afresh.

An insurer reissues a PDS with most pages reprinted word for word under a new date and form code, a few reworded, a few
added or dropped. A page reprinted with only its stamp changed keeps what a person confirmed about it; any other change
sends it back to be checked, and a changed figure is named. The pages below are built the way those documents are: a
body, and a foot line with the issue's date and the page number.
"""
import pymupdf

from truedoc.versions import match, page_prints

A4 = (595, 842)


def _pdf(tmp_path, name, pages):
    """Each page: (body lines, foot line or None, head line or None)."""
    doc = pymupdf.open()
    for body, foot, head in pages:
        page = doc.new_page(width=A4[0], height=A4[1])
        if head:
            page.insert_text((50, 40), head, fontsize=9)
        y = 150
        for line in body:
            page.insert_text((50, y), line, fontsize=11)
            y += 18
        if foot:
            page.insert_text((50, 815), foot, fontsize=8)
    path = tmp_path / name
    doc.save(str(path))
    doc.close()
    return str(path)


COVER = ["Your home insurance policy covers your home against", "loss or damage caused by fire, storm and theft."]
EXCESS = ["The excess you must pay for each claim is $500.", "A higher excess applies to earthquake claims."]
EXCLUDE = ["We do not cover loss or damage caused by wear", "and tear, rust, mould or gradual deterioration."]


def _issue(date, total, pages):
    return [(body, "PDS prepared %s  QM1234  Page %d of %d" % (date, i + 1, total), None) for i, body in enumerate(pages)]


def _kinds(result):
    return [(m.old, m.new, m.kind) for m in result]


def test_the_same_document_matches_itself_page_for_page(tmp_path):
    path = _pdf(tmp_path, "a.pdf", _issue("29/07/14", 3, [COVER, EXCESS, EXCLUDE]))
    assert _kinds(match(page_prints(path), page_prints(path))) == [(1, 1, "same"), (2, 2, "same"), (3, 3, "same")]


def test_a_reissue_with_only_a_new_date_is_restamped(tmp_path):
    old = _pdf(tmp_path, "old.pdf", _issue("29/07/14", 3, [COVER, EXCESS, EXCLUDE]))
    new = _pdf(tmp_path, "new.pdf", _issue("01/03/18", 3, [COVER, EXCESS, EXCLUDE]))
    assert _kinds(match(page_prints(old), page_prints(new))) == [(1, 1, "restamped"), (2, 2, "restamped"), (3, 3, "restamped")]


def test_a_changed_figure_makes_the_page_changed_and_is_named(tmp_path):
    old = _pdf(tmp_path, "old.pdf", _issue("29/07/14", 3, [COVER, EXCESS, EXCLUDE]))
    raised = ["The excess you must pay for each claim is $750.", EXCESS[1]]
    new = _pdf(tmp_path, "new.pdf", _issue("01/03/18", 3, [COVER, raised, EXCLUDE]))
    result = match(page_prints(old), page_prints(new))
    assert _kinds(result) == [(1, 1, "restamped"), (2, 2, "changed"), (3, 3, "restamped")]
    assert ("$500.", "$750.") in result[1].figures


def test_a_page_added_between_issues_is_new_and_the_rest_still_pair(tmp_path):
    old = _pdf(tmp_path, "old.pdf", _issue("29/07/14", 3, [COVER, EXCESS, EXCLUDE]))
    added = ["Changes in this edition: we now cover accidental", "breakage of glass in your home's windows."]
    new = _pdf(tmp_path, "new.pdf", _issue("01/03/18", 4, [COVER, added, EXCESS, EXCLUDE]))
    assert _kinds(match(page_prints(old), page_prints(new))) == [
        (1, 1, "restamped"), (None, 2, "new"), (2, 3, "restamped"), (3, 4, "restamped")]


def test_a_page_dropped_between_issues_is_reported(tmp_path):
    old = _pdf(tmp_path, "old.pdf", _issue("29/07/14", 3, [COVER, EXCESS, EXCLUDE]))
    new = _pdf(tmp_path, "new.pdf", _issue("01/03/18", 2, [COVER, EXCLUDE]))
    assert _kinds(match(page_prints(old), page_prints(new))) == [(1, 1, "restamped"), (2, None, "dropped"), (3, 2, "restamped")]


def test_a_reworded_line_that_repeats_at_each_head_is_a_change_not_a_stamp(tmp_path):
    """A table's heading repeated at the top of every page is taken for a running line - and a change to its words must
    still be seen: only numbers and month names may differ for a page to count as restamped."""
    old_pages = [(COVER, None, "Item | Covered | Limit"), (EXCESS, None, "Item | Covered | Limit")]
    new_pages = [(COVER, None, "Item | Covered | Limit applies"), (EXCESS, None, "Item | Covered | Limit applies")]
    result = match(page_prints(_pdf(tmp_path, "old.pdf", old_pages)), page_prints(_pdf(tmp_path, "new.pdf", new_pages)))
    assert [m.kind for m in result] == ["changed", "changed"]
    assert any("applies" in new for old, new in result[0].wording)


def test_the_foot_of_a_one_page_document_is_its_own_content(tmp_path):
    """No page beside it to show the foot line runs: the date is part of the page, and a new date is a change."""
    old = _pdf(tmp_path, "old.pdf", _issue("29/07/14", 1, [COVER]))
    new = _pdf(tmp_path, "new.pdf", _issue("01/03/18", 1, [COVER]))
    result = match(page_prints(old), page_prints(new))
    assert [m.kind for m in result] == ["changed"] and result[0].figures
