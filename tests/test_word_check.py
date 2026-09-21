"""The word check's sorting of differences (D040), on the shapes found in the owner's library on 21 September 2026.

The check sets the words a page prints against what TrueDoc wrote and what it owns up to leaving out. What differs is
sorted: *repaired* (a ligature the text layer spells short, which TrueDoc puts right), *glued* (words TrueDoc ran
together - a fault), *respaced* (words the reference reader broke apart - not TrueDoc's fault) and *missing* (a real
loss). Each test is one of the pages that made the rule.
"""
import collections
import importlib.util
import os

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("word_check", os.path.join(HERE, "..", "bench", "tools", "word_check.py"))
wc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wc)

C = collections.Counter


def test_a_short_spelled_ligature_is_a_repair_not_a_loss():
    # CBA's PEDG: the text layer spells "after" as "afer"; TrueDoc reads the glyph's name and writes "after".
    lost, added = C({"afer": 1, "certifcate": 1}), C({"after": 1, "certificate": 1})
    repaired = wc.reconcile_repairs(lost, added)
    assert +lost == C() and +added == C()
    assert sorted(repaired) == ["afer->after", "certifcate->certificate"]


def test_a_digit_in_front_of_a_word_is_not_a_repair():
    lost, added = C({"artificial": 1}), C({"4artificial": 1})
    assert wc.reconcile_repairs(lost, added) == C()
    assert lost["artificial"] == 1


def test_words_run_together_are_glued():
    # Key Facts Sheets set "Step 1" in a box of its own, and "Step 1 Understanding the Facts Sheet" came out
    # "Step1Understanding the Facts Sheet".
    lines = [["step", "1", "understanding", "the", "facts", "sheet"]]
    lost, added = C({"step": 1, "1": 1, "understanding": 1}), C({"step1understanding": 1})
    glued, respaced = wc.classify_boundaries(lines, lost, added, blob="")
    assert glued == C({"step1understanding": 1}) and +lost == C() and +added == C()


def test_a_symbol_run_into_its_word_is_glued():
    # A Webdings bullet written as the character "4" and run into "artificial grass or turf".
    lines = [["artificial", "grass", "or", "turf"]]
    lost, added = C({"artificial": 1}), C({"4artificial": 1})
    glued, _ = wc.classify_boundaries(lines, lost, added, blob="")
    assert glued == C({"4artificial": 1}) and +lost == C()


def test_a_letter_spaced_title_the_reference_broke_is_respaced():
    # AAMI's SPDS sets its title with wide letter spacing; one reader reads fragments, TrueDoc the words.
    lines = [["aami", "bu", "ildin", "g", "insu", "r", "ance"]]
    lost = C({"bu": 1, "ildin": 1, "g": 1, "insu": 1, "r": 1, "ance": 1})
    glued, respaced = wc.classify_boundaries(lines, lost, C(), blob="xxaamibuildinginsurancexx")
    assert glued == C() and sum(respaced.values()) == 6 and +lost == C()


def test_a_line_written_whole_does_not_excuse_a_word_lost_elsewhere():
    # CBA's torn table heading lost "to your"; the same page wrote "we agree to pay a claim" whole. The first version
    # handed the heading's "to" back because it also stood on the whole line.
    lines = [["you", "must", "contribute", "when", "we", "agree", "to", "pay", "your", "claim"],
             ["to", "your", "building"]]
    lost = C({"to": 1, "your": 1})
    blob = "youmustcontributewhenweagreetopayyourclaim"
    _, respaced = wc.classify_boundaries(lines, lost, C(), blob=blob)
    assert respaced == C() and lost == C({"to": 1, "your": 1})


def test_a_short_line_is_never_excused():
    # "Cover", a torn heading cell of its own, also appears elsewhere on the page; five letters prove nothing.
    lines = [["cover"]]
    lost = C({"cover": 1})
    _, respaced = wc.classify_boundaries(lines, lost, C(), blob="buildingcoverexcess")
    assert respaced == C() and lost["cover"] == 1
