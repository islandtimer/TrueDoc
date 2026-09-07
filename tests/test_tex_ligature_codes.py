"""Raw glyph codes of TeX Type 3 text fonts are read as the ligatures they stand for.

A dvips Type 3 font names its glyphs by code, so MuPDF hands back the raw code: 0x0C in
"classi\x0ccation" is "fi" in TeX's OT1 layout. A symbol font using the same code for
another glyph is told apart by its use (single letters, never words).
"""
from truedoc.extract.textlayer import _recover_tex_codes
from truedoc.model import BBox, Char


def _line(font: str, text: str, x: float = 0.0) -> list[Char]:
    chars = []
    for ch in text:
        chars.append(Char(text=ch, bbox=BBox(x, 0, x + 5, 10), font=font, size=10))
        x += 5
    return chars


def _text(chars) -> str:
    return "".join(c.text for c in chars)


def test_ot1_ligature_codes_become_letters_in_a_text_font():
    lines = [
        (_line("T15", "semantic classi\x0ccation of the question"), (1.0, 0.0)),
        (_line("T15", "provided by an o\x0b-line question"), (1.0, 0.0)),
        (_line("T15", "an e\x0ecient and \x0dexible reader"), (1.0, 0.0)),
    ]
    assert _recover_tex_codes(lines)
    assert _text(lines[0][0]) == "semantic classification of the question"
    assert _text(lines[1][0]) == "provided by an off-line question"
    assert _text(lines[2][0]) == "an efficient and flexible reader"
    # One character per letter, sharing the glyph's box.
    fi = [c for c in lines[0][0] if c.bbox.width == 2.5]
    assert [c.text for c in fi] == ["f", "i"] and fi[0].bbox.x1 == fi[1].bbox.x0


def test_symbol_font_codes_are_left_alone():
    # A maths italic font (cmmi) uses 0x1C for tau and sets single letters only;
    # the text font on the same page is OT1.
    lines = [
        (_line("T15", "the queue size of session at time"), (1.0, 0.0)),
        (_line("T15", "the \x0crst server"), (1.0, 0.0)),
        (_line("T13", "B") + _line("T15", "(") + _line("T13", "\x1c") + _line("T15", ")"), (1.0, 0.0)),
    ]
    assert _recover_tex_codes(lines)
    assert _text(lines[1][0]) == "the first server"
    assert _text(lines[2][0]) == "B(\x1c)"


def test_no_text_font_signature_means_no_change():
    # A text font whose raw codes are not in the ligature slots (a broken encoding).
    lines = [(_line("Frutiger", "ordinary words here and there \x01 more \x13 text"), (1.0, 0.0))]
    assert not _recover_tex_codes(lines)
    assert "\x01" in _text(lines[0][0])
    # A page that is mostly symbols, even with a code in the ligature slot.
    lines = [(_line("Sym", "a \x0c b + c = d"), (1.0, 0.0))]
    assert not _recover_tex_codes(lines)


def test_t1_ligature_slots_when_they_are_the_only_codes():
    lines = [
        (_line("SFRM", "the \x1crst and \x1bth di\x1eculty of the a\x1dair"), (1.0, 0.0)),
        (_line("SFRM", "another line of ordinary words"), (1.0, 0.0)),
    ]
    assert _recover_tex_codes(lines)
    assert _text(lines[0][0]) == "the first and ffth difficulty of the aflair"


def test_code_without_a_neighbouring_letter_stays():
    lines = [
        (_line("T15", "the classi\x0ccation of the question and more words"), (1.0, 0.0)),
        (_line("T15", "equation ") + _line("T15", "\x06", x=200.0), (1.0, 0.0)),
    ]
    assert _recover_tex_codes(lines)
    assert _text(lines[0][0]) == "the classification of the question and more words"
    assert _text(lines[1][0]).endswith("\x06")
