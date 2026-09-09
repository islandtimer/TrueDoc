"""D008 on model-read pages: check what a model wrote against what we can read ourselves.

Measured over the 281 model-read benchmark pages before this was built: 181 corroborated, 91 with
no witness at all, 7 low support, 2 unverified. Every low-support page turned out to have a broken
witness rather than an inventing model, which is why the check reports and never acts.
"""

from truedoc.vision.corroborate import CORROBORATED, MIN_WITNESS_WORDS, check


def _many(word: str, n: int) -> str:
    return " ".join(["%s%d" % (word, i) for i in range(n)])


def test_a_witness_that_backs_the_model_corroborates_it():
    shared = _many("alpha", 60)
    r = check(shared, shared + " extra words here")
    assert r["state"] == "corroborated", r
    assert r["support"] >= CORROBORATED


def test_no_witness_is_unchecked_not_a_pass():
    """A bare scan our OCR could not read says nothing either way, and must not imply a pass."""
    r = check(_many("alpha", 60), "two words")
    assert r["state"] == "unchecked", r
    assert "no usable witness" in r["reason"]


def test_a_witness_in_another_script_is_broken_not_weak():
    """The real case: a Persian page whose text layer is mojibake ('ƶŝ Ĩŝ ƾĭŵźƀƟř') against the
    model's correct Persian. Zero overlap, but the model is right and the layer is unusable."""
    model = " ".join(["بهداشتی", "درمانی", "کاشان"] * 30)
    witness = " ".join(["ƶŝĨŝ", "ƾĭŵźƀƟř", "ƱƺƯŻō"] * 30)
    r = check(model, witness)
    assert r["state"] == "unverified", r
    assert "encoding is broken" in r["reason"]


def test_a_comparable_witness_that_backs_little_is_flagged_only():
    r = check(_many("alpha", 60), _many("beta", 60))
    assert r["state"] == "low support", r
    assert r["support"] < CORROBORATED
    # It says what it cannot distinguish, rather than asserting invention.
    assert "garbled witness looks the same" in r["reason"]


def test_the_witness_floor_is_honest_about_itself():
    assert MIN_WITNESS_WORDS >= 20, "too few words cannot witness anything"
