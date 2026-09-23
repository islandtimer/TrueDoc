"""The location map: every block's page, box and range in the text, in a file beside it; the text unchanged.

For every block in the map, the text between its character positions is that block's text, and every box lies inside
its page; a paragraph that runs over a page break is one paragraph with two boxes; a bold term keeps its boundary as a
range; the markdown is the same with the map asked for or not, and the map carries the checksum of the text it
describes.
"""
import hashlib

import pymupdf

from truedoc.pipeline import ConvertOptions, convert_with_status

OPTS = dict(layout=False, ocr=False, math=False, marks=False)


def _pdf(tmp_path):
    doc = pymupdf.open()
    first = doc.new_page(width=400, height=500)
    first.insert_text((40, 60), "Cover for your home", fontsize=18)
    first.insert_text((40, 100), "A storm is when strong winds blow over the area where the home", fontsize=10)
    first.insert_text((40, 114), "stands and the damage it does to the roof is covered.", fontsize=10)
    first.insert_text((40, 150), "Excess", fontsize=10, fontname="helv")
    first.insert_text((40, 164), "The amount you pay towards each claim, which the schedule shows, and which", fontsize=10)
    first.insert_text((40, 178), "is taken off what we pay you for the claim when we settle it with you and", fontsize=10)
    first.insert_text((40, 460), "the insured owner of the home under the terms of", fontsize=10)
    second = doc.new_page(width=400, height=500)
    second.insert_text((40, 60), "the policy, as it is set out in the schedule we send each year.", fontsize=10)
    second.insert_text((40, 100), "Flood", fontsize=10, fontname="hebo")
    second.insert_text((80, 100), "means the covering of normally dry land by water.", fontsize=10)
    path = tmp_path / "policy.pdf"
    doc.save(str(path))
    doc.close()
    return str(path)


def test_the_text_is_the_same_and_the_map_names_it(tmp_path):
    path = _pdf(tmp_path)
    plain = convert_with_status(path, ConvertOptions(frontmatter=False, **OPTS))
    mapped = convert_with_status(path, ConvertOptions(frontmatter=False, location_map=True, **OPTS))
    assert mapped.markdown == plain.markdown
    assert plain.location_map is None
    m = mapped.location_map
    assert m["markdown"]["sha256"] == hashlib.sha256(mapped.markdown.encode("utf-8")).hexdigest()
    assert m["markdown"]["characters"] == len(mapped.markdown)


def test_every_block_is_its_text_and_every_box_is_on_its_page(tmp_path):
    result = convert_with_status(_pdf(tmp_path), ConvertOptions(frontmatter=True, location_map=True, **OPTS))
    md, m = result.markdown, result.location_map
    sizes = {p["page"]: p["size"] for p in m["pages"]}
    last = m["markdown"]["body_start"]
    assert m["markdown"]["all_found_in_place"]
    for block in m["blocks"]:
        s, e = block["range"]
        assert last <= s < e <= len(md)
        assert md[s:e].strip() and md[s:e] in md[m["markdown"]["body_start"]:]
        last = e
        for box in block["boxes"]:
            w, h = sizes[box["page"]]
            x0, y0, x1, y1 = box["box"]
            assert 0 <= x0 <= x1 <= w and 0 <= y0 <= y1 <= h
    texts = [md[b["range"][0]:b["range"][1]] for b in m["blocks"]]
    assert any(t.startswith("#") and "Cover for your home" in t for t in texts)
    assert all(p["state"] == "read" and p["read"] == "text layer" for p in m["pages"])


def test_a_paragraph_over_a_page_break_has_both_boxes(tmp_path):
    result = convert_with_status(_pdf(tmp_path), ConvertOptions(frontmatter=False, location_map=True, **OPTS))
    md, m = result.markdown, result.location_map
    joined = [b for b in m["blocks"] if len({x["page"] for x in b["boxes"]}) == 2]
    assert len(joined) == 1
    block = joined[0]
    s, e = block["range"]
    assert "under the terms of the policy" in md[s:e]
    first, second = block["pieces"]
    assert (first["page"], second["page"]) == (1, 2)
    assert md[first["range"][0]:first["range"][1]].endswith("under the terms of")
    assert md[second["range"][0]:second["range"][1]].startswith("the policy")
    assert first["range"][0] == s and second["range"][1] == e


def test_bold_is_written_as_ranges(tmp_path):
    result = convert_with_status(_pdf(tmp_path), ConvertOptions(frontmatter=False, location_map=True, **OPTS))
    md, m = result.markdown, result.location_map
    assert set(m["emphasis"]) == {"bold", "italic"} and m["emphasis"]["italic"] == []
    assert [md[s:e] for s, e in m["emphasis"]["bold"]] == ["Flood"]
