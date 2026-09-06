"""Explicit space characters in the text layer are word breaks, however tight the geometry.

Two things used to glue words: the fuser for word pieces emitted separately
(Type 3 fonts) joined "platform." to "These" across a 0.1 em sentence space,
and on hidden OCR layers, whose glyph boxes overlap at word boundaries, the
"spurious space" rule threw the engine's own spaces away ("Fracturesextend").
"""

from truedoc.extract.textlayer import _chars_to_words, _fuse_touching_words
from truedoc.model import BBox, Char, Line


def _chars(spec, size=11.0):
    """spec: list of (char, x0, x1); y is fixed."""
    return [Char(text=ch, bbox=BBox(x0, 100.0, x1, 100.0 + size), font="ACaslon-Regular", size=size, origin_y=100.0 + size) for ch, x0, x1 in spec]


def _run(text, x=0.0, width=5.0):
    """Letters set touching, each `width` wide, from x."""
    out = []
    for i, ch in enumerate(text):
        out.append((ch, x + i * width, x + (i + 1) * width))
    return out


def test_tight_sentence_space_survives_the_fuser():
    # "platform." then a space glyph whose box overlaps the full stop, then "These" 1.1 pt on.
    spec = _run("platform.", 36.0) + [(" ", 80.6, 83.4)] + _run("These", 82.1)
    words = _chars_to_words(_chars(spec))
    assert [w.text for w in words] == ["platform.", "These"]
    assert words[1].after_space
    fused = _fuse_touching_words(Line(words=words, bbox=BBox.union_all(w.bbox for w in words)))
    assert [w.text for w in fused.words] == ["platform.", "These"]


def test_ocr_layer_space_kept_when_boxes_overlap():
    # OCR layer: "Fractures" ends at 52.9, the space box sits at 53.1-55.6, "extend" starts at 52.6.
    spec = _run("Fractures", 8.0) + [(" ", 53.1, 55.6)] + _run("extend", 52.6)
    words = _chars_to_words(_chars(spec, size=9.0), ocr_layer=True)
    assert [w.text for w in words] == ["Fractures", "extend"]


def test_tight_space_after_a_comma_is_kept():
    # "However," then a space glyph, then "state" 0.8 pt on at 11 pt (0.07 em).
    spec = _run("However,", 400.0) + [(" ", 439.5, 442.3)] + _run("state", 440.8)
    words = _chars_to_words(_chars(spec))
    assert [w.text for w in words] == ["However,", "state"]


def test_spurious_kerning_space_still_dropped_on_digital_text():
    # A MuPDF-inserted "space" at a 0.3 pt kerning gap inside "AVATAR" is not a word break.
    spec = _run("AV", 10.0) + [(" ", 20.0, 20.3)] + _run("ATAR", 20.3)
    words = _chars_to_words(_chars(spec))
    assert [w.text for w in words] == ["AVATAR"]


def test_word_pieces_without_a_space_are_still_fused():
    # Type 3 producers emit "Ann" and "ual" as separate objects with no space glyph between them.
    spec = _run("Ann", 10.0) + _run("ual", 25.2)
    words = _chars_to_words(_chars(spec))
    fused = _fuse_touching_words(Line(words=words, bbox=BBox.union_all(w.bbox for w in words)))
    assert [w.text for w in fused.words] == ["Annual"]
