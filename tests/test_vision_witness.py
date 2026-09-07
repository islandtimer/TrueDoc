"""The page's own lines witness the running heads a vision model transcribes (D019).

A French journal page's hidden layer holds "LES JUIFS, LES GRECS-CATHOLIQUES SOUS 'ALI BEY
AL-KABIR" in its head strip and "265" in its foot strip; the model's reading starts with the
same title and ends with the same number. Both are furniture and go. The body is never touched,
a long line is never a running head, and without a witness nothing is dropped.
"""
from truedoc.model import BBox
from truedoc.vision.witness import strip_lines, strip_running_heads

TEXT = (
    "LES JUIFS, LES GRECS-CATHOLIQUES SOUS 'ALÎ BEY AL-KABÎR\n\n"
    "D'autres grecs-catholiques se répartirent le contrôle des autres fermes et monopoles.\n\n"
    "Le consul français du Caire annonça les changements intervenus.\n\n"
    "265"
)


def test_head_and_foot_lines_with_a_witness_are_dropped():
    out, dropped = strip_running_heads(TEXT, top=["LES JUIFS, LES GRECS-CATHOLIQUES SOUS 'ALI BEY AL-KABIR"], bottom=["265"])
    assert dropped == ["LES JUIFS, LES GRECS-CATHOLIQUES SOUS 'ALÎ BEY AL-KABÎR", "265"]
    assert out.startswith("D'autres grecs-catholiques") and out.endswith("intervenus.")


def test_witness_in_the_wrong_strip_does_not_count():
    out, dropped = strip_running_heads(TEXT, top=["265"], bottom=["LES JUIFS, LES GRECS-CATHOLIQUES SOUS 'ALI BEY AL-KABIR"])
    assert dropped == [] and out == TEXT


def test_body_lines_at_the_edge_stay_even_when_witnessed():
    # A dictionary page's first entry sits inside the head strip of a dense scan, and the
    # layer has it there too; it is body text, not furniture (measured 7 September: the
    # position-only rule dropped 147 such lines and cost what it won).
    entry = "TRUNK-WEAM. A fiddle."
    text = entry + "\n\nTRUNLIN. A large coal. North.\n\nSee page 265 for the rest."
    out, dropped = strip_running_heads(text, top=[entry], bottom=["See page 265 for the rest."])
    assert out == text and dropped == []
    long_caps = "THIS OPENING LINE RUNS TO MORE THAN EIGHT WORDS AND IS BODY TEXT NOT A RUNNING HEAD"
    assert strip_running_heads(long_caps + "\n\nBody.", top=[long_caps], bottom=[]) == (long_caps + "\n\nBody.", [])
    assert strip_running_heads(TEXT, top=[], bottom=[]) == (TEXT, [])


def test_furniture_shapes():
    from truedoc.vision.witness import looks_like_furniture

    assert looks_like_furniture("MØRE OG ROMSDAL")
    assert looks_like_furniture("- 24 -") and looks_like_furniture("265") and looks_like_furniture("xiv")
    assert looks_like_furniture("العدد ٢١")           # no case in the script: a few words with a digit
    assert not looks_like_furniture("Fonte: Bacen")
    assert not looks_like_furniture("PERSPECTIVE. A reflecting-glass.")
    assert not looks_like_furniture("খুলনা প্রকৌশল ও প্রযুক্তি বিশ্ববিদ্যালয়")


def test_strip_lines_takes_objects_or_tuples():
    class L:
        def __init__(self, text, y0, y1):
            self.text, self.bbox = text, BBox(0, y0, 100, y1)

    lines = [L("Running head", 10, 20), L("Body", 300, 312), ("footer", 700, 712)]
    top, bottom = strip_lines(lines, 792.0)
    assert top == ["Running head"] and bottom == ["footer"]
