"""A page whose text layer the check turns down is called unreadable only when something on it may be lost (D042).

The check (`textlayer._assess_quality`) turns down a page with under twenty letters and figures, and a page where a
quarter of the longer words look like no language. Every such page used to be reported `unreadable-pages`, ending its
document `incomplete`: a blank page, a ruled page for notes, a divider holding its page number, and a page of notices
in eleven languages whose text was written all the same. Now each is judged by what it holds:
- a page with no picture, whose drawings hold no words its layer lacks - OCR saw none there, or, where OCR did not
  look, nothing is drawn with a curve, as every letter drawn as a shape is - is blank, a note and not a loss;
- a page whose words look like no language only while a vowel sign is taken for a symbol, or a Chinese sentence for
  one word, is read from its layer - which pages a model reads, when one is configured, is not changed;
- anything else stays unreadable.
"""
import pymupdf

from truedoc.extract.textlayer import _assess_quality, _garbled_in_its_script, _looks_garbled
from truedoc.model import BBox, Char, ImageRef, Line, Page, TextQuality, Word
from truedoc.pipeline import ConvertOptions, _lost_on, convert_with_status

FAST = dict(layout=False, math=False, ocr=False)


# --- a word judged in its own script -------------------------------------------------------------

def test_a_sentence_in_a_script_without_spaces_keeps_its_commas_inside():
    sentence = "此乃关於保险的重要文件，它解释了根据保单条款什麽是受保、什麽是不受保项目，"
    assert _looks_garbled(sentence)                  # to the Latin measure, symbols strewn through a word
    assert not _garbled_in_its_script(sentence)
    assert not _garbled_in_its_script("第3章保险条款")    # a figure between ideographs is no digit inside a word
    assert _looks_garbled("保险（Policy）条款") and not _garbled_in_its_script("保险（Policy）条款")   # nor are brackets


def test_a_vowel_sign_is_part_of_its_letter():
    for word in ("महत्वपूर्ण", "पॉलिसी", "ਮਹਤਵਪੂਰਨ"):
        assert _looks_garbled(word)
        assert not _garbled_in_its_script(word)


def test_a_broken_latin_layer_is_still_broken():
    for token in ("0Ql.5)')81", "tAatcHnGg", "PIOI*Jnlboctenum", "~hlngomonas", "xqzvbkt", "文件0Ql.5)')81"):
        assert _garbled_in_its_script(token), token


def _layer(tokens, script_words):
    """A page whose words are `tokens`, and enough readable Latin words besides to count."""
    words = [Word(text=t, bbox=BBox(0, 0, 10, 10)) for t in tokens + script_words]
    chars = [Char(text=c, bbox=BBox(0, 0, 1, 1), font="Helvetica", size=10.0) for w in words for c in w.text]
    page = Page(number=1, width=595.0, height=842.0, words=words, chars=chars)
    visibility = type("V", (), {"drawn_invisible": 0, "drawn_total": len(chars)})()
    return _assess_quality(page, visibility)


def test_a_page_in_several_scripts_is_suspect_to_the_check_and_digital_in_its_scripts():
    english = ["important", "document", "about", "insurance", "explains", "what", "covered", "under", "policy"] * 3
    hindi = ["महत्वपूर्ण", "पॉलिसी", "सहायता", "व्यक्ति"] * 3
    q = _layer(english, hindi)
    assert q.kind == "suspect" and q.garbage_fraction > 0.2
    assert q.script_kind == "digital"
    garbled = _layer(english, ["0Ql.5)')81", "tAatcHnGg", "PIOI*Jnlboctenum"] * 4)
    assert garbled.kind == "suspect" and garbled.script_kind == "suspect"


# --- what a turned-down page lost ----------------------------------------------------------------

def _page(words=(), kind="none", images=(), **meta):
    ws = [Word(text=w, bbox=BBox(100, 100, 140, 112)) for w in words]
    alnum = sum(ch.isalnum() for w in words for ch in w)
    page = Page(number=1, width=595.0, height=842.0, words=ws, lines=[Line(words=ws, bbox=BBox(100, 100, 140, 112))] if ws else [],
                images=[ImageRef(bbox=BBox(*b)) for b in images], quality=TextQuality(n_alnum=alnum, kind=kind))
    page.meta.update(meta)
    return page


def test_a_page_where_ocr_found_nothing_and_there_is_no_picture_is_blank():
    assert _lost_on(_page(ocr_empty=True)) == "blank"


def test_a_page_for_notes_is_blank_when_ocr_saw_only_its_own_words():
    page = _page(["Notes", "50"], ocr_rejected=True, witness_lines=[("Notes", 60.0, 80.0), ("50", 800.0, 810.0)])
    assert _lost_on(page) == "blank"


def test_words_ocr_saw_that_the_layer_lacks_are_a_loss():
    seen = [("Section three: what we cover", 300.0, 340.0)]
    assert _lost_on(_page(["3"], ocr_rejected=True, witness_lines=seen)) == "lost"
    # under a readable page's worth they are a logo's word or two, and nothing is lost
    assert _lost_on(_page(["F1024"], ocr_rejected=True, witness_lines=[("company logo", 300.0, 340.0)])) == "blank"


def test_a_picture_may_hold_words_no_one_read():
    assert _lost_on(_page(ocr_empty=True, images=[(0, 0, 595, 842)])) == "lost"


def test_a_page_of_any_other_kind_the_check_turned_down_is_a_loss():
    assert _lost_on(_page(kind="ocr", ocr_empty=True)) == "lost"


def test_where_ocr_did_not_look_a_curve_may_be_a_letter():
    assert _lost_on(_page(curves=0)) == "blank"
    assert _lost_on(_page(curves=12)) == "lost"
    assert _lost_on(_page(curves=None)) == "lost"
    assert _lost_on(_page()) == "lost"


def test_a_page_in_several_scripts_is_read_from_its_layer():
    page = _page(["important"] * 30, kind="suspect")
    page.quality.script_kind = "digital"
    assert _lost_on(page) == "read"
    page.quality.script_kind = "suspect"
    assert _lost_on(page) == "lost"
    written = _page([], kind="suspect")
    written.quality.script_kind = "digital"
    assert _lost_on(written) == "lost"                # nothing of it in the body: its layer was never written


# --- the conversion's status ---------------------------------------------------------------------

def _pdf(path, draw):
    pdf = pymupdf.open()
    page = pdf.new_page()
    draw(page)
    pdf.save(str(path))
    pdf.close()
    return str(path)


def test_a_blank_page_is_a_note_and_the_document_is_complete(tmp_path):
    result = convert_with_status(_pdf(tmp_path / "blank.pdf", lambda page: None), ConvertOptions(frontmatter=False, **FAST))
    assert result.completion == "complete"
    assert [(i.code, i.severity, i.pages) for i in result.issues] == [("blank-pages", "note", [1])]


def test_a_ruled_page_for_notes_is_blank_and_its_heading_is_written(tmp_path):
    def notes(page):
        page.insert_text((72, 200), "Notes", fontsize=18)
        for i in range(16):
            page.draw_line((72, 240 + 30 * i), (523, 240 + 30 * i), width=0.5)

    result = convert_with_status(_pdf(tmp_path / "notes.pdf", notes), ConvertOptions(frontmatter=False, **FAST))
    assert result.completion == "complete" and "Notes" in result.markdown
    assert [i.code for i in result.issues] == ["blank-pages"]


def test_a_shape_drawn_with_curves_where_ocr_did_not_look_leaves_the_page_unreadable(tmp_path):
    result = convert_with_status(_pdf(tmp_path / "circle.pdf", lambda page: page.draw_circle((300, 400), 80)),
                                 ConvertOptions(frontmatter=False, **FAST))
    assert result.completion == "incomplete"
    assert [i.code for i in result.issues] == ["unreadable-pages"]
