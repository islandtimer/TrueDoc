"""The OCR acceptance gate: noise is rejected, words are accepted."""

from truedoc.model import BBox, Char, Line, Word
from truedoc.ocr.rapid import _looks_like_text


def _line(text):
    words = [Word(text=t, bbox=BBox(0, 0, 10, 10), chars=[Char(text=c, bbox=BBox(0, 0, 1, 10), font="OCR", size=8) for c in t]) for t in text.split()]
    return Line(words=words, bbox=BBox(0, 0, 100, 10))


def test_real_sentence_is_wordlike():
    lines = [_line("Dear Sir, thank you for your letter of May 3, 1914."), _line("We will send the documents shortly.")]
    assert _looks_like_text(lines) >= 0.8


def test_handwriting_noise_is_rejected():
    lines = [_line("tHee pltcae Silaln Rhealeel nedl esiny"), _line("Ighlanm tuhethimia mlhan")]
    assert _looks_like_text(lines) < 0.6
