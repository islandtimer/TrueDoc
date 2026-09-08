"""Three running-head and running-foot shapes the classifier missed in run 61.

A form repeats its running head as a bold label at the foot of its box, above the page's
bottom strip ("Schedule A (Form 990) 2022", 8e953483): a short line that repeats a running
head's text is furniture wherever it sits. A footnote in small type just above the bottom
strip ("9 Ibid", 138eff9f) matched the numbered-heading shape. A bare web address at the foot
("health.ucsd.edu/jacobs", 0f727ae2) carried no "www." or "http" for the contact rule.
"""
from tests.test_classify import _block
from truedoc.classify.blocks import classify_blocks
from truedoc.model import BlockKind, Page
from truedoc.pipeline import _margin_cleanup


def _page():
    page = Page(number=1, width=612, height=792)
    page.body_font_size = 8.0
    return page


def test_a_line_repeating_the_running_head_is_furniture_wherever_it_sits():
    page = _page()
    head = _block("Schedule A (Form 990) 2022", 36, 40, size=7.9)
    body = _block("Part I Reason for Public Charity Status (All organizations must complete this part.)", 36, 120, size=8.0)
    repeat = _block("Schedule A (Form 990) 2022", 467, 652, size=7.9)
    blocks = [head, body, repeat]
    classify_blocks(page, blocks)
    repeat.kind = BlockKind.HEADING          # the layout model's verdict on a short bold line
    _margin_cleanup(page, blocks)             # runs after the layout model, as in the pipeline
    assert head.kind == BlockKind.HEADER and body.kind == BlockKind.TEXT
    assert repeat.kind in (BlockKind.HEADER, BlockKind.FOOTER)
    # The page's title in display type repeats the running head: it stays the title.
    page = _page()
    head = _block("Physics Minor (Non-Teaching)", 421, 34, size=8.0)
    title = _block("Physics Minor (Non-Teaching)", 54, 66, size=22.0)
    blocks = [head, title, _block("Students must complete the core courses listed in the table below.", 54, 130, size=8.0)]
    classify_blocks(page, blocks)
    _margin_cleanup(page, blocks)
    assert head.kind == BlockKind.HEADER and title.kind == BlockKind.HEADING


def test_a_display_size_line_in_the_bottom_strip_is_a_running_foot():
    # "Surfside Gazette • AUGUST 2013" in 18 pt at the foot of a newspaper page (eac8e314).
    page = Page(number=1, width=612, height=792)
    page.body_font_size = 11.0
    body = _block("The street sign was unveiled on Harding Avenue before a crowd of residents.", 40, 600, size=11.0)
    foot = _block("Surfside Gazette • AUGUST 2013", 228, 757, size=18.0)
    blocks = [body, foot]
    classify_blocks(page, blocks)
    foot.kind = BlockKind.HEADING
    _margin_cleanup(page, blocks)
    assert foot.kind == BlockKind.FOOTER
    # A title in display type at the top stays a title.
    page = Page(number=1, width=612, height=792)
    page.body_font_size = 11.0
    title = _block("ON HARDING AVE", 83, 44, size=30.0)
    blocks = [title, _block("The street sign was unveiled on Harding Avenue before a crowd of residents.", 40, 120, size=11.0)]
    classify_blocks(page, blocks)
    title.kind = BlockKind.HEADING
    _margin_cleanup(page, blocks)
    assert title.kind == BlockKind.HEADING


def test_a_small_numbered_line_near_the_foot_is_not_a_heading():
    page = Page(number=1, width=595, height=842)
    page.body_font_size = 11.5
    body = _block("The Minister replied to the question in the House on Thursday.", 88, 300, size=11.5)
    note = _block("9 Ibid", 88, 745, size=9.7)
    note.meta["heading_like"] = True      # the segmenter's verdict on a short numbered line
    classify_blocks(page, [body, note])
    assert note.kind != BlockKind.HEADING
    heading = _block("9 Conclusions", 88, 300, size=12.5)
    classify_blocks(page, [heading, _block("The findings are summarised below in three parts.", 88, 320, size=11.5)])
    assert heading.kind == BlockKind.HEADING


def test_a_bare_web_address_at_the_foot_is_a_footer():
    page = Page(number=1, width=612, height=792)
    page.body_font_size = 11.0
    body = _block("Our clinics offer the full range of services to patients and physicians.", 72, 300, size=11.0)
    foot = _block("health.ucsd.edu/jacobs", 263, 725, size=12.0)
    classify_blocks(page, [body, foot])
    assert foot.kind == BlockKind.FOOTER
    assert body.kind == BlockKind.TEXT
