"""A comma, semicolon or colon glued to the next word by an OCR engine is a word break.

Scanned pages read "plant,and" or "Smith;Jones" as one token when the printed space
after the mark is narrow. Measured on run 48's outputs (7 Sept 2026): 12 checks won,
none lost. Numbers, times, web and e-mail addresses are left alone.
"""
from truedoc.extract.textlayer import _split_glued_words
from truedoc.model import BBox, Char, Line, Word
from truedoc.ocr import rapid


def test_our_ocr_splits_glued_punctuation():
    text = "plant,and Smith;Jones time:10 e.g.,the http://a.b/c:d x@y.com:z 1,000 www.a.b:c A,B f(x,y)"
    words = rapid._split_words(text, BBox(0, 0, 500, 10), 0.9)
    assert [w.text for w in words] == [
        "plant,", "and", "Smith;", "Jones", "time:10", "e.g.,", "the",
        "http://a.b/c:d", "x@y.com:z", "1,000", "www.a.b:c", "A,B", "f(x,y)",
    ]
    # The two halves of a split token abut: the second starts where the first ends,
    # and no character slot is lost or invented.
    assert abs(words[1].bbox.x0 - words[0].bbox.x1) < 1e-6
    assert sum(len(w.chars) for w in words) == sum(len(t) for t in text.split())


def test_our_ocr_keeps_plain_tokens_as_before():
    words = rapid._split_words("Total 1,234.5 (n=12); see", BBox(0, 0, 200, 10), 0.9)
    assert [w.text for w in words] == ["Total", "1,234.5", "(n=12);", "see"]


def _ocr_layer_line(*tokens: str) -> Line:
    x = 0.0
    words = []
    for tok in tokens:
        chars = []
        for ch in tok:
            chars.append(Char(text=ch, bbox=BBox(x, 0, x + 5, 10), font="Layer", size=10))
            x += 5
        words.append(Word(text=tok, bbox=BBox.union_all(c.bbox for c in chars), chars=chars))
        x += 5
    return Line(words=words, bbox=BBox.union_all(w.bbox for w in words))


def test_hidden_layer_splits_at_comma_before_letter():
    line = _split_glued_words(_ocr_layer_line("plant,and", "1991).The", "1,000", "a;b", "A,B"))
    assert [w.text for w in line.words] == ["plant,", "and", "1991).", "The", "1,000", "a;", "b", "A,B"]
    # Each new word keeps the characters it was cut from.
    assert all("".join(c.text for c in w.chars) == w.text for w in line.words)
