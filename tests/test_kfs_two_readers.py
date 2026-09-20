"""The two-readers comparison must not hide a difference in meaning (the review's F10, 18 September).

Its first version stripped a leading tick or cross before comparing, listed only third columns
under 0.98 alike (a dropped "not" in a long condition is 0.998 alike), and let a row only one
reader found fall out of the count. These are the review's synthetic probes P2-03, P2-04 and
P2-05 as tests, with the placer's two (P2-01, P2-02). Synthetic sheets only: no library needed.
"""

import collections
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "bench", "tools"))
sys.path.insert(0, os.path.join(ROOT, "bench", "gpu"))

import kfs_two_readers as two  # noqa: E402
from place_bakeoff import CUT_OFF_BLOCK, layout_text  # noqa: E402

HEADER = "| Event/Cover | Yes/No/Optional | Some examples of specific conditions, exclusions or limits |\n| --- | --- | --- |\n"
LONG = ("We cover loss or damage caused by flood, including the cost of removing debris from the site, of temporary "
        "accommodation while your home cannot be lived in, and of storing your contents, but we do not cover damage "
        "to retaining walls, gates, fences, swimming pool covers or liners, or loss caused by actions of the sea.")


def _sheet(*rows):
    return HEADER + "".join("| %s | %s | %s |\n" % r for r in rows)


def _kinds(found):
    return collections.Counter(d["kind"] for d in found)


def test_a_tick_and_a_cross_are_not_the_same_answer():
    found, counts = two.compare(_sheet(("Flood", "✓ Covered", "Up to the sum insured.")),
                                _sheet(("Flood", "✗ Covered", "Up to the sum insured.")))
    assert two.mark_of("✓ Covered") == "tick" and two.mark_of("✗ Covered") == "cross" and two.mark_of("Covered") == ""
    assert two.norm("✓ Covered") == two.norm("✗ Covered") == "covered"      # the words agree; the marks do not
    assert counts["mark"] == 1 and _kinds(found) == {"mark": 1}


def test_a_dropped_not_is_listed_however_alike_the_sentences_are():
    changed = LONG.replace("we do not cover damage", "we do cover damage")
    import difflib
    assert difflib.SequenceMatcher(None, two.norm(LONG), two.norm(changed)).ratio() > two.ALIKE   # the old test saw nothing
    found, counts = two.compare(_sheet(("Flood", "Yes", LONG)), _sheet(("Flood", "Yes", changed)))
    assert counts["critical"] == 1 and counts["wording"] == 0
    assert found[0]["kind"] == "critical words" and found[0]["differ"] == ["not"]


def test_a_changed_amount_is_listed_too():
    found, counts = two.compare(_sheet(("Theft", "Yes", "Jewellery is limited to $5,000 in total.")),
                                _sheet(("Theft", "Yes", "Jewellery is limited to $50,000 in total.")))
    assert counts["critical"] == 1 and sorted(found[0]["differ"]) == ["$5000", "$50000"]


def test_a_row_only_one_reader_found_is_counted_and_named():
    td = _sheet(("Flood", "Yes", "Covered."), ("Storm", "Yes", "Covered."))
    mo = _sheet(("Flood", "Yes", "Covered."))
    found, counts = two.compare(td, mo)
    assert counts["rows_both"] == 1 and counts["row_one_reader_only"] == 1
    assert [(d["kind"], d["event"], d["model"]) for d in found] == [("row only one reader found", "storm", None)]


def test_a_label_that_opens_two_rows_is_reported():
    td = _sheet(("Flood", "Yes", "Covered."), ("Flood", "No", "Not covered for contents."))
    found, counts = two.compare(td, td)
    assert counts["label_repeated"] == 1 and _kinds(found) == {"label opens more than one row": 1}


def test_readers_that_agree_list_nothing():
    sheet = _sheet(("Flood", "Yes", LONG), ("Storm", "✓ Yes", "Up to $1,000."))
    found, counts = two.compare(sheet, sheet)
    assert found == [] and counts["rows_both"] == 2 and counts["third_identical"] == 2


def test_punctuation_and_markup_alone_are_not_a_difference():
    found, _ = two.compare(_sheet(("Flood", "**Yes**", "We don’t cover “wear and tear” – ever.")),
                           _sheet(("Flood", "Yes", "We don't cover \"wear and tear\" - ever.")))
    assert found == []


# --- the placer: P2-01 and P2-02 -------------------------------------------------------------------

def test_a_reading_salvaged_from_a_cut_off_reply_is_marked_in_its_own_file():
    cut = '[{"category": "text", "text": "We cover storm damage."}, {"category": "text", "text": "We do not cover dam'
    counts = collections.Counter()
    text, was_cut = layout_text(cut, counts, "x")
    assert text == "We cover storm damage." and was_cut is True           # the cover survives, its exception does not
    assert CUT_OFF_BLOCK.startswith("---\ncut_off: true\n---")             # and the file will say so (test_status_contract)
    whole, was_cut = layout_text('[{"category": "text", "text": "All of it."}]', counts, "x")
    assert whole == "All of it." and was_cut is False


def test_layout_json_is_recognised_however_the_model_spaced_it():
    pretty = '[\n  {\n    "category": "text",\n    "text": "Spaced out."\n  },\n  {"category": "figure", "text": ""}\n]'
    text, was_cut = layout_text(pretty, collections.Counter(), "x")
    assert text == "Spaced out." and was_cut is False                     # it used to pass through as raw JSON
    assert layout_text("[1] A footnote, not JSON.", collections.Counter(), "x") == ("[1] A footnote, not JSON.", False)


def test_rows_under_a_band_are_found_though_they_arrive_as_a_second_table():
    # RACQ, 18 September: a band across the table ends one markdown table, and the rows under it
    # come as another whose first row is a data row standing where markdown wants a header.
    split = (_sheet(("Flood", "Yes", "Covered.")) + "\nCover for valuables, collections and items away\n\n"
             "| High value items and collections | Optional | Specified items only. |\n| --- | --- | --- |\n"
             "| Items away from the insured address | Optional | Australia and New Zealand only. |\n")
    whole = _sheet(("Flood", "Yes", "Covered."), ("High value items and collections", "Optional", "Specified items only."),
                   ("Items away from the insured address", "Optional", "Australia and New Zealand only."))
    found, counts = two.compare(split, whole)
    assert found == [] and counts["rows_both"] == 3 and counts["row_one_reader_only"] == 0


def test_rows_under_a_row_spanning_label_are_one_entry():
    # CGU's sheet, 19 September 2026: one reader writes the table nested in "High value items" as further
    # rows under a row-spanning label, the other writes it all into the entry's third cell. Same words.
    spanning = ("<table><tr><th>Event/Cover</th><th>Yes/No</th><th colspan=\"3\">Some examples</th></tr>"
                "<tr><td rowspan=\"3\">High value items and collections</td><td rowspan=\"3\">Yes</td>"
                "<td>Policy</td><td>Item Limit</td><td>Overall Limit</td></tr>"
                "<tr><td>Accidental Damage Home</td><td>$2,500/item</td><td>20% of Contents SI or $7,500</td></tr>"
                "<tr><td>Fundamentals Home</td><td>$1,000/item</td><td>$2,000</td></tr>"
                "<tr><td>Flood</td><td>Yes</td><td colspan=\"3\">Up to the sum insured.</td></tr></table>")
    flat = _sheet(("High value items and collections", "Yes", "Policy Item Limit Overall Limit Accidental Damage Home "
                   "$2,500/item 20% of Contents SI or $7,500 Fundamentals Home $1,000/item $2,000"),
                  ("Flood", "Yes", "Up to the sum insured."))
    found, counts = two.compare(flat, spanning)
    assert found == [] and counts["rows_both"] == 2 and counts["third_identical"] == 2
    entries, _repeated = two.rows_of(spanning)
    assert entries["flood"] == ("Yes", "Up to the sum insured.")            # the row after the span is its own


def test_a_table_inside_a_cell_is_that_cell_s_words_whichever_way_the_other_reader_wrote_it():
    # D038 (20 September 2026): TrueDoc writes the nested table inside the cell; the other reader spliced its rows
    # into the outer table under a row-spanning label. Same entry, same words.
    import kfs_grade

    nested = ("<table><tr><th>Event/Cover</th><th>Yes/No</th><th>Some examples</th></tr>"
              "<tr><td>High value items and collections</td><td>Yes</td><td><table>"
              "<tr><th>Policy</th><th>Item Limit</th><th>Overall Limit</th></tr>"
              "<tr><td>Fundamentals Home</td><td>$1,000/item</td><td>$2,000</td></tr></table></td></tr>"
              "<tr><td>Flood</td><td>Yes</td><td>Up to the sum insured.</td></tr></table>")
    spliced = ("<table><tr><th>Event/Cover</th><th>Yes/No</th><th colspan=\"3\">Some examples</th></tr>"
               "<tr><td rowspan=\"2\">High value items and collections</td><td rowspan=\"2\">Yes</td>"
               "<td>Policy</td><td>Item Limit</td><td>Overall Limit</td></tr>"
               "<tr><td>Fundamentals Home</td><td>$1,000/item</td><td>$2,000</td></tr>"
               "<tr><td>Flood</td><td>Yes</td><td colspan=\"3\">Up to the sum insured.</td></tr></table>")
    rows = kfs_grade.blocks(nested)
    assert len(rows) == 1 and len(rows[0]) == 3                     # one table of three rows: the row after the nested one is not lost
    assert kfs_grade.cells_of(rows[0][1])[2] == "Policy Item Limit Overall Limit Fundamentals Home $1,000/item $2,000"
    found, counts = two.compare(nested, spliced)
    assert found == [] and counts["rows_both"] == 2
