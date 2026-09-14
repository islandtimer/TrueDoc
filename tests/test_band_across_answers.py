"""A band laid across a table belongs to no column: it neither refuses a boundary nor is divided by one.

On a Key Facts Sheet a band opens a section - "Cover for valuables, collections and items away from the
insured address" - and runs as one line of text over the gap between the answers and the exclusions. The
cut-finder refused any cut that a segment crosses without a gap of its own, which is right for a title or a
group heading over the columns, and on seven contents sheets it kept "Optional" at the head of the
exclusions ("Flood |  | Optional Excludes damage..."). A band is told from a title by where it sits: rows of
the table above and below it, each with two or more segments under its extent. A label run together with its
answer is one segment too, but it has a real gap in it, and it stays a row to be divided.
"""
from truedoc.model import BBox, Line, Word
from truedoc.tables.aligned import table_from_lines

BAND = [("Cover", 40, 66), ("for", 69, 82), ("valuables,", 85, 130), ("collections", 133, 180), ("and", 183, 200),
        ("items", 203, 228), ("away", 231, 255), ("from", 258, 280), ("the", 283, 298), ("insured", 301, 336),
        ("address", 339, 376)]


def _segment(y, *words):
    ws = [Word(text=t, bbox=BBox(x0, y, x1, y + 10)) for t, x0, x1 in words]
    return Line(words=ws, bbox=BBox.union_all(w.bbox for w in ws))


def _cells(table):
    assert table is not None
    return [c.text for row in table.grid() for c in row if c and c.text]


def _event(y, label, answer, exclusion):
    """A label, and its answer run together with the first line of its exclusions, then two wrapped lines."""
    return [_segment(y, *label), _segment(y, answer, *exclusion),
            _segment(y + 12, ("damage", 185, 219), ("by", 222, 232), ("rising", 235, 262), ("water.", 265, 292)),
            _segment(y + 24, ("or", 185, 195), ("storm", 198, 224), ("surge.", 227, 254))]


def _sheet(*extra):
    return (_event(100, [("Flood", 40, 66)], ("Optional", 140, 178), [("Excludes", 185, 225), ("flood.", 228, 255)])
            + _event(140, [("Storm", 40, 68)], ("Yes", 140, 156), [("Excludes", 185, 225), ("rain.", 228, 250)])
            + [_segment(180, *BAND)]
            + _event(200, [("Theft", 40, 64)], ("Yes", 140, 156), [("Excludes", 185, 225), ("theft.", 228, 256)])
            + _event(240, [("Earthquake", 40, 92)], ("Yes", 140, 156), [("Excludes", 185, 225), ("tremors.", 228, 266)])
            + list(extra))


def test_a_band_does_not_keep_an_answer_inside_the_exclusions():
    cells = _cells(table_from_lines(_sheet(), 10.0, trusted=True))
    assert "Optional" in cells, cells
    assert any(c.startswith("Excludes flood.") for c in cells), cells
    assert "Cover for valuables, collections and items away from the insured address" in cells, cells


def test_a_label_run_together_with_its_answer_is_not_a_band():
    # One segment alone on its row inside the table, like a band - but with a real gap before its "No".
    glued = [_segment(280, ("Actions", 40, 76), ("of", 79, 88), ("the", 91, 106), ("sea", 109, 125), ("No", 140, 152))]
    after = _event(300, [("Fire", 40, 58)], ("Yes", 140, 156), [("Excludes", 185, 225), ("arson.", 228, 256)])
    cells = _cells(table_from_lines(_sheet(*glued, *after), 10.0, trusted=True))
    assert "Actions of the sea" in cells and "No" in cells, cells


def test_a_band_over_only_the_answers_and_exclusions_is_still_a_band():
    # ALDI's contents sheets start the band over the answers, so the rows around it hold one segment under its extent;
    # it stands 5pt clear of both neighbours, where a wrapped line runs on from the line above.
    lines = [_segment(100, ("Theft", 21, 45)), _segment(100, ("Yes", 101, 118)), _segment(100, ("Excludes", 145, 185), ("jewellery.", 188, 232)),
             _segment(111, ("unless", 145, 175), ("specified.", 178, 222)),
             _segment(130, ("Escape", 21, 52), ("of", 55, 64), ("liquid", 67, 94)), _segment(130, ("Yes", 101, 118)),
             _segment(130, ("Excludes", 145, 185), ("leaks.", 188, 214)),
             _segment(141, ("device", 145, 175), ("which", 178, 204), ("leaked.", 207, 240)),
             _segment(156, *[(t, x0 + 96, x1 + 96) for t, x0, x1 in BAND]),
             _segment(171, ("High", 21, 42), ("value", 45, 68)),
             _segment(171, ("Optional", 101, 138), ("We", 145, 158), ("refer", 161, 181), ("to", 184, 192), ("items.", 195, 220)),
             _segment(182, ("items", 21, 44), ("and", 47, 64)), _segment(182, ("for", 145, 158), ("loss.", 161, 181)),
             _segment(200, ("Flood", 21, 45)), _segment(200, ("Optional", 101, 138), ("Excludes", 145, 185), ("walls.", 188, 214)),
             _segment(211, ("and", 145, 162), ("paths.", 165, 192))]
    cells = _cells(table_from_lines(lines, 10.0, trusted=True))
    assert "Optional" in cells, cells
    assert any(c.startswith("We refer to items.") for c in cells), cells
    assert "Cover for valuables, collections and items away from the insured address" in cells, cells
