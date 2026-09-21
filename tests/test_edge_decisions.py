"""TrueDoc writes down what it leaves out at a page's edge, and why, and whether it could check (D040).

A line at a page's head or foot is left out of the body when it is a running head or foot, a page number, or the
document's imprint. Each of those is a judgement, and until 21 September 2026 none was recorded: a line that runs was
dropped without trace (a Key Facts Sheet's prescribed "The content of this Key Facts Sheet is prescribed by the
Australian Government ..." stands on both its pages), and a line that could not be checked was dropped outright (a
one-page SPDS's issuer and preparation date). These tests pin the record, the front matter it feeds, the note that
says a call could not be checked, and - most of all - that the body does not move.
"""

import pymupdf
import yaml

from truedoc.pipeline import ConvertOptions, convert, convert_with_status, load_document

BODY = ["Home Building Insurance",
        "Product Disclosure Statement and Policy Booklet",
        "Please read this booklet and keep it with your policy papers."]
OFF = ConvertOptions(layout=False, ocr=False, math=False, marks=False, tables=False)
ISSUER = "AAI Limited ABN 48 005 297 807 AFSL 230859 trading as AAMI"
PRESCRIBED = "The content of this Key Facts Sheet is prescribed by the Australian Government"


def _document(tmp_path, feet, name="pds.pdf"):
    doc = pymupdf.open()
    for foot in feet:
        page = doc.new_page(width=405, height=573)
        for j, text in enumerate(BODY):
            page.insert_text((14, 120 + 14 * j), text, fontsize=10)
        page.insert_text((14, 545), foot, fontsize=9)
    path = tmp_path / name
    doc.save(str(path))
    doc.close()
    return str(path)


def _front(md):
    return yaml.safe_load(md.split("---\n", 2)[1])["truedoc"]


def test_a_running_line_is_kept_once_with_its_pages(tmp_path):
    doc = load_document(_document(tmp_path, [PRESCRIBED] * 3), OFF)
    running = doc.metadata.get("running") or []
    assert [e["text"] for e in running] == [PRESCRIBED]
    assert running[0]["pages"] == [1, 2, 3]


def test_every_edge_call_is_recorded_with_its_reason(tmp_path):
    result = convert_with_status(_document(tmp_path, [PRESCRIBED, PRESCRIBED, "Page 3 of 3"]), OFF)
    by_page = {d["page"]: d for d in result.decisions}
    assert by_page[1]["kept_in"] == "running" and by_page[1]["checked"] is True
    assert by_page[3]["because"] == "a page number" and by_page[3]["kept_in"] is None
    assert all(d["decided"] == "left out of the body" for d in result.decisions)


def test_a_call_that_could_not_be_checked_is_said_out_loud(tmp_path):
    result = convert_with_status(_document(tmp_path, [ISSUER], name="one.pdf"), OFF)
    assert [d["checked"] for d in result.decisions] == [False]
    assert "edge-unchecked" in [i.code for i in result.issues]
    # a note, not a fault: the conversion is still complete
    assert result.completion == "complete"
    fm = _front(result.markdown)
    assert fm["imprint"][0]["text"] == ISSUER and fm["imprint"][0]["checked"] is False


def test_a_line_of_figures_is_compared_by_its_figures(tmp_path):
    # AAMI prints its phone number, "13 22 44", at the head of every page. Asked in words it has none, so it could
    # never be shown to run and would be kept as an unchecked imprint on every page; its figures show that it runs.
    doc = pymupdf.open()
    for _ in range(3):
        page = doc.new_page(width=405, height=573)
        for j, text in enumerate(BODY):
            page.insert_text((14, 120 + 14 * j), text, fontsize=10)
        page.insert_text((300, 30), "13 22 44", fontsize=9)
    path = tmp_path / "phone.pdf"
    doc.save(str(path))
    doc.close()
    result = convert_with_status(str(path), OFF)
    calls = [d for d in result.decisions if d["text"] == "13 22 44"]
    assert calls and all(d["kept_in"] == "running" and d["checked"] for d in calls)
    assert "figures" in calls[0]["because"]
    assert "edge-unchecked" not in [i.code for i in result.issues]


def test_the_body_does_not_move(tmp_path):
    # What the records change is the front matter; every measure reads the body without it, so none can move.
    bodyless = ConvertOptions(layout=False, ocr=False, math=False, marks=False, tables=False, frontmatter=False)
    for feet, name in (([PRESCRIBED] * 2, "run.pdf"), ([ISSUER], "one.pdf"), (["Page 1 of 1"], "folio.pdf")):
        body = convert(_document(tmp_path, feet, name=name), bodyless)
        assert feet[0] not in body, body[:300]
        assert all(line in body for line in BODY)
