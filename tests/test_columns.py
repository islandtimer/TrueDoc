"""Column gutters and word breaks in the text-layer extractor."""

from truedoc.extract.textlayer import _chars_to_words, _column_gutters, _reassemble_lines, _split_at_gutters
from truedoc.model import BBox, Char, Line, Word


def word(text, x, oy, size=10.0, char_w=5.0):
    chars = []
    cx = x
    for ch in text:
        chars.append(Char(text=ch, bbox=BBox(cx, oy - 0.7 * size, cx + char_w, oy + 0.2 * size), font="Times", size=size, origin_y=oy))
        cx += char_w
    return Word(text=text, bbox=BBox.union_all(c.bbox for c in chars), chars=chars)


def line(*words):
    return Line(words=list(words), bbox=BBox.union_all(w.bbox for w in words))


def two_column_page(rows=20, gutter=(250, 262)):
    """Two justified columns; word positions vary from row to row as in real text."""
    lefts = ["lorem ipsum dolor sit amet", "consectetur adipiscing elit sed", "do eiusmod tempor incididunt", "ut labore et dolore magna", "aliqua enim ad minim veniam"]
    rights = ["quis nostrud exercitation ullamco", "laboris nisi ut aliquip ex", "ea commodo consequat duis aute", "irure dolor in reprehenderit", "voluptate velit esse cillum"]
    lines = []
    for i in range(rows):
        oy = 100 + 12 * i
        for text, x0, x1 in ((lefts[i % 5], 50, gutter[0]), (rights[i % 5], gutter[1], 460)):
            ws = text.split()
            n_chars = sum(len(w) for w in ws)
            char_w = 4.0
            space = (x1 - x0 - n_chars * char_w) / max(1, len(ws) - 1)   # justified
            x = x0
            words = []
            for w in ws:
                words.append(word(w, x, oy, char_w=char_w))
                x += len(w) * char_w + space
            lines.append(line(*words))
    return lines


def test_gutter_is_found_and_never_crossed():
    lines = two_column_page()
    gutters = _column_gutters(lines)
    assert len(gutters) == 1 and 249 <= gutters[0][0] <= 251 and 261 <= gutters[0][1] <= 263
    out = _reassemble_lines(lines, gutters)
    assert len(out) == 40  # 20 rows, two segments each; nothing joined across the gutter
    assert all(l.bbox.x1 <= 251 or l.bbox.x0 >= 261 for l in out)


def test_patent_line_numbers_in_the_gutter_do_not_bridge_columns():
    lines = two_column_page()
    # every fourth row carries a line number in the gutter, emitted with the left segment
    for i in range(0, len(lines), 8):
        l = lines[i]
        oy = l.words[0].chars[0].origin_y
        l.words.append(word("15", 254, oy, char_w=2.5))
        l.bbox = BBox.union_all(w.bbox for w in l.words)
    gutters = _column_gutters(lines)
    assert len(gutters) == 1
    out = _reassemble_lines(_split_at_gutters(lines, gutters), gutters)
    texts = [l.text for l in out]
    assert not any("tet right" in t or "15 right" in t for t in texts)
    assert all("15" not in t or t == "15" for t in texts)


def test_narrow_justified_word_gaps_break_words():
    # 7 pt text with 0.96 pt word gaps (about 0.14 em) and touching letters
    size = 7.0
    chars = []
    x = 10.0
    for w in ("encourage", "businesses", "to", "reduce"):
        for ch in w:
            chars.append(Char(text=ch, bbox=BBox(x, 93, x + 3.5, 101), font="Clan", size=size, origin_y=100))
            x += 3.5
        x += 0.96
    words = _chars_to_words(chars)
    assert [w.text for w in words] == ["encourage", "businesses", "to", "reduce"]


def test_letter_spaced_word_is_not_broken():
    chars = []
    x = 10.0
    for ch in "ANNUAL":
        chars.append(Char(text=ch, bbox=BBox(x, 90, x + 6, 102), font="Times", size=12.0, origin_y=100))
        x += 6 + 1.6   # uniform 1.6 pt tracking (0.13 em), no larger gap anywhere
    words = _chars_to_words(chars)
    assert len(words) == 1 and words[0].text == "ANNUAL"


def test_garbled_tokens_are_recognised():
    from truedoc.extract.textlayer import _looks_garbled

    for token in ("Staphylococcus", "kloosii/carnosus", "McDonald", "DQ453581", "COVID-19", "Départementale", "U.S.A.", "Ph.D.", "www.example.com", "rhythm"):
        assert not _looks_garbled(token), token
    for token in ("0Ql.5)')81", "PIOI*Jnlboctenum", "Shi9cllo", "~hlngomonas", "H[oE", "EUE{3", "aBcDeFg"):
        assert _looks_garbled(token), token


def test_a_row_of_single_digits_an_em_apart_is_not_letter_spacing():
    """A rating scale's "1 2 3 ... 10" at 12pt, 16pt apart, read as one number 12345678910
    through the PDFium reader, which hands the row over as one line; MuPDF cut it into ten
    lines first, so the merge never saw it. Letter spacing is a fraction of the em."""
    chars = []
    x = 10.0
    for ch in "123456789":
        chars.append(Char(text=ch, bbox=BBox(x, 90, x + 6.7, 102), font="Arial", size=12.0, origin_y=100))
        chars.append(Char(text=" ", bbox=BBox(x + 6.7, 90, x + 6.7, 102), font="Arial", size=12.0, origin_y=100))
        x += 6.7 + 16.2
    for ch in "10":
        chars.append(Char(text=ch, bbox=BBox(x, 90, x + 6.7, 102), font="Arial", size=12.0, origin_y=100))
        x += 6.7
    words = _chars_to_words(chars)
    assert [w.text for w in words] == ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"], [w.text for w in words]
