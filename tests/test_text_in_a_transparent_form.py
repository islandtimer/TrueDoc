"""Text inside a form that is drawn transparent is on no reader's page (D011).

A journal's "ARTICLE IN PRESS", 72-point type across the page, sat in a form drawn under `/CA 0 /ca 0`; inside the
form the text set its own opacity back to 1, so the character itself said "visible", the page showed nothing, and its
letters came out as headings and broke a table's heading row (benchmark tables/c8cdd4c4..._pg3, 20 September 2026).
"""
import pymupdf
import yaml

from truedoc.pipeline import ConvertOptions, convert


def _page_with_a_form(tmp_path, veil, own=0.99):
    """A page with a visible sentence, and a second sentence inside a form drawn with opacity `veil`; the sentence in
    the form sets its own opacity to `own`, as the journal's watermark sets its own to 1."""
    src = pymupdf.open()
    sp = src.new_page(width=400, height=300)
    sp.insert_text((40, 160), "WATERMARK WORDS NOBODY SEES", fontsize=14, fill_opacity=own, stroke_opacity=own)
    doc = pymupdf.open()
    page = doc.new_page(width=400, height=300)
    page.insert_text((40, 60), "Visible sentence about apples and oranges.", fontsize=12)
    page.show_pdf_page(page.rect, src, 0)
    if veil is not None:
        page.clean_contents()     # first: it drops a graphics state nothing names yet
        gs = doc.get_new_xref()
        doc.update_object(gs, "<</Type/ExtGState/ca %g/CA %g>>" % (veil, veil))
        kind, value = doc.xref_get_key(page.xref, "Resources")
        holder, key = (int(value.split()[0]), "ExtGState") if kind == "xref" else (page.xref, "Resources/ExtGState")
        assert doc.xref_get_key(holder, key)[0] == "null"      # the visible sentence needs no graphics state
        doc.xref_set_key(holder, key, "<</GSveil %d 0 R>>" % gs)
        xref = page.get_contents()[0]
        stream = doc.xref_stream(xref)
        name = [x[1] for x in page.get_xobjects()][0].encode()
        assert b"/" + name + b" Do" in stream
        doc.update_stream(xref, stream.replace(b"/" + name + b" Do", b"/GSveil gs /" + name + b" Do"))
    path = tmp_path / "t.pdf"
    doc.save(str(path))
    return str(path)


def _convert(path):
    md = convert(path, ConvertOptions(frontmatter=True, layout=False, ocr=False))
    _, fm, body = md.split("---\n", 2)
    return yaml.safe_load(fm), body


def test_text_in_a_form_drawn_at_nothing_is_hidden(tmp_path):
    fm, body = _convert(_page_with_a_form(tmp_path, 0))
    assert "apples and oranges" in body
    assert "WATERMARK" not in body
    assert any("WATERMARK" in h["text"] for h in fm.get("truedoc", {}).get("hidden_text") or [])


def test_text_in_a_faint_form_is_read(tmp_path):
    # a watermark a reader does see, however pale
    _, body = _convert(_page_with_a_form(tmp_path, 0.2))
    assert "WATERMARK WORDS NOBODY SEES" in body


def test_text_in_an_ordinary_form_is_read(tmp_path):
    _, body = _convert(_page_with_a_form(tmp_path, None))
    assert "WATERMARK WORDS NOBODY SEES" in body
