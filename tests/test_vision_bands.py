"""A hard page read in two overlapping bands, welded back into one page.

A model sent a whole page sees it at whatever the service's image limit allows - on the benchmark's old
scans about 0.66 of the page's own pixels. Sent the halves it sees each at about 0.90, a median 1.3
times more ink per letter, and looks at every line twice. The welding is the part that can go wrong: the
bands share a strip, so the same lines arrive twice and must be joined rather than stacked.
"""
import pytest

from truedoc.vision.bands import band_boxes, splice, splice_all


def test_two_bands_cover_the_page_and_share_a_strip():
    boxes = band_boxes(1000.0, 2000.0, count=2, overlap=0.2)
    assert len(boxes) == 2
    (_, top0, _, top1), (_, bot0, _, bot1) = boxes
    assert top0 == 0.0 and bot1 == 2000.0            # the whole page is covered
    assert bot0 < top1                                # and the two share a strip
    shared = top1 - bot0
    assert shared == pytest.approx(0.2 * (top1 - top0), rel=0.02)


def test_one_band_is_the_whole_page():
    assert band_boxes(800.0, 600.0, count=1) == [(0.0, 0.0, 800.0, 600.0)]


def test_the_shared_lines_are_written_once():
    first = "Dear Sir\nI write about the matter\nof the Liverpool cargo"
    second = "of the Liverpool cargo\nwhich sailed on Tuesday\nYours faithfully"
    assert splice(first, second).splitlines() == [
        "Dear Sir",
        "I write about the matter",
        "of the Liverpool cargo",
        "which sailed on Tuesday",
        "Yours faithfully",
    ]


def test_a_longer_shared_run_is_found_whole():
    shared = ["and have not compromised themselves", "in acts against the United States", "I have known Mr Law for many years"]
    first = "\n".join(["Besides, they are confirmed"] + shared)
    second = "\n".join(shared + ["and valued his word as I should his bond"])
    assert splice(first, second).splitlines() == [
        "Besides, they are confirmed",
        *shared,
        "and valued his word as I should his bond",
    ]


def test_two_readings_of_a_line_that_differ_a_little_still_weld():
    # the same line, one reading a word short at the band's edge
    first = "the distribution of nodes is\nN_x times N_v equals forty nine"
    second = "distribution of nodes is\nN_x times N_v equals forty nine\nby ninety seven"
    joined = splice(first, second).splitlines()
    assert joined.count("N_x times N_v equals forty nine") == 1
    assert joined[-1] == "by ninety seven"


def test_nothing_in_common_keeps_both_halves():
    # a page whose halves share nothing readable: losing a line is worse than seeing one twice
    first = "the upper half of the page"
    second = "the lower half of the page"
    joined = splice(first, second)
    assert "upper half" in joined and "lower half" in joined


def test_a_repeated_short_line_is_not_mistaken_for_the_overlap():
    # "1862" ending one band and beginning the next is not evidence of a shared strip
    first = "a letter of some length about the cargo\n1862"
    second = "1862\nand a second page about the insurance"
    joined = splice(first, second)
    assert "about the cargo" in joined and "about the insurance" in joined


def test_an_empty_band_leaves_the_other_alone():
    assert splice("", "only this") == "only this"
    assert splice("only this", "") == "only this"


def test_three_bands_weld_in_order():
    # real lines, because a two-word line is deliberately not enough to anchor an overlap
    one = "Bangor Pennsylvania the twenty second of May"
    two = "Colonel Roosevelt comrade and friend I am glad"
    three = "that you arrived home in the best of health"
    four = "it has been a long time since I wanted to write"
    five = "and tell you what a great admiration I have"
    six = "but there is one instant that I cannot express"
    a = "\n".join([one, two, three])
    b = "\n".join([two, three, four, five])
    c = "\n".join([four, five, six])
    assert splice_all([a, b, c]).splitlines() == [one, two, three, four, five, six]


def test_the_endpoint_name_can_ask_for_bands(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    from truedoc.vision import make_provider

    assert make_provider("anthropic").bands == 1
    assert make_provider("anthropic/bands=2").bands == 2
    assert make_provider("anthropic:claude-sonnet-5/bands=3").bands == 3
    assert make_provider("anthropic:claude-sonnet-5/bands=3").model == "claude-sonnet-5"
    # nonsense is not a crash, it is one band
    assert make_provider("anthropic/bands=many").bands == 1


def test_a_band_is_told_it_is_a_slice():
    from truedoc.vision.anthropic_api import _band_prompt

    top, bottom = _band_prompt(1, 2), _band_prompt(2, 2)
    assert "the top" in top and "the bottom" in bottom
    for prompt in (top, bottom):
        assert "slice" in prompt and "overlap" in prompt
        assert "Do not write a heading" in prompt
        # and it still carries the two rules a whole page carries
        assert "running heads" in prompt and "keep the writer's spelling" in prompt


def test_a_bad_match_far_down_the_second_band_cannot_eat_the_middle():
    """The failure that cost old_scans/1 the middle of its letter (12 September).

    The top band ended "...During your Trip to". The weld matched that against a line far down the
    bottom band and dropped everything before it, so the page read from the salutation straight to the
    signature and forty per cent of the words were gone. A weld may only reach as far into the second
    band as the shared strip can plausibly extend; past that it keeps both halves.
    """
    top = "\n".join([
        "I am one of D E Sickles old Regt and Brigade",
        "I Served Through all of the civil War",
        "this country During your Trip to",
    ])
    bottom = "\n".join([
        "South America which I read of in the papers",
        "and the fever you took there was a great loss",
        "I am now past seventy years of age and poor",
        "the pension I draw is but twelve dollars",
        "which is little enough for a man who served",
        "I would Like to See you Address 25 market St",
        "your very Resp Caleb Aber",
    ])
    joined = splice(top, bottom)
    # every line of the second band survives: nothing in it was ever duplicated in the first
    for line in bottom.splitlines():
        assert line in joined, line
    assert "this country During your Trip to" in joined


def test_a_short_line_does_not_match_a_long_one_that_merely_contains_it():
    a = "the cargo sailed on Tuesday"
    b = "the cargo sailed on Tuesday last from the port of Liverpool bound for New York"
    from truedoc.vision.bands import _same

    assert not _same(a, b)
    # but a line one word short at the band's edge still matches
    assert _same("and have not compromised themselves in acts against",
                 "and have not compromised themselves in acts against the")
