"""The numbers a page prints, where each applies, kept only when they run on from the pages beside.

Read from every line at a page's edge that TrueDoc leaves out of the body, a running line too ("Page 30 | Household
Insurance Policy" carries its page's number). A spread prints two numbers, one on each half, and each applies to its
half. A section tab set at the head of page after page runs on from nothing and is not a page number. The location
map carries them.
"""
import pymupdf

from truedoc.pipeline import ConvertOptions, convert_with_status

OPTS = ConvertOptions(frontmatter=False, layout=False, ocr=False, math=False, marks=False, location_map=True)
BODY = ["The cover this part of the policy gives, set out in full so that it can be read on its own page.",
        "What we pay for, and the limits that apply to each thing we pay for under this part.",
        "The conditions you must meet, and what happens when they are not met by you or by us.",
        "How to make a claim, what we need from you, and how long each step of it will take.",
        "What we do not cover, whichever part of the policy the loss or damage would fall under."]


def _document(tmp_path, feet, heads=None, width=400, name="doc.pdf"):
    doc = pymupdf.open()
    for i, foot in enumerate(feet):
        page = doc.new_page(width=width, height=500)
        if heads:
            page.insert_text((width - 30, 30), heads[i], fontsize=9)
        for k, line in enumerate(BODY):
            page.insert_text((40, 80 + 16 * k), line[: int(width / 5.2)], fontsize=9)
        for x, text in foot:
            page.insert_text((x, 480), text, fontsize=8)
    path = tmp_path / name
    doc.save(str(path))
    doc.close()
    return str(path)


def _printed(path):
    return {p["page"]: [(n["number"], n["applies"]) for n in p["printed"]] for p in convert_with_status(path, OPTS).location_map["pages"]}


def test_a_running_line_carries_its_page_number(tmp_path):
    feet = [[(40, "Page %d | Household Insurance Policy" % (n + 10))] for n in range(5)]
    printed = _printed(_document(tmp_path, feet))
    assert printed == {n + 1: [(str(n + 10), "page")] for n in range(5)}


def test_a_spread_prints_a_number_on_each_half(tmp_path):
    feet = [[(40, str(2 * n + 30)), (760, str(2 * n + 31))] for n in range(5)]
    printed = _printed(_document(tmp_path, feet, width=800))
    assert printed[3] == [("34", "left half"), ("35", "right half")]
    assert all(len(v) == 2 for v in printed.values())


def test_a_section_tab_is_not_a_page_number(tmp_path):
    feet = [[(190, str(n + 5))] for n in range(5)]
    printed = _printed(_document(tmp_path, feet, heads=["2"] * 5))
    assert printed == {n + 1: [(str(n + 5), "page")] for n in range(5)}
