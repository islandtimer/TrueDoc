"""Check a model's reading of a page against what we can read of it ourselves (D008, M6).

D008 says nothing is invented. On every page without a digital text layer a model does the
reading (D019), and until now nothing verified that - the promise was a policy we stated rather
than one we measured. The page's own reading is the natural second witness: a hidden OCR layer,
or our own engine's rejected lines, kept for exactly this in `page.meta["witness_lines"]`.

**This reports; it never acts.** Measured over the 281 model-read benchmark pages, every page
where support was low turned out to have a broken witness rather than an inventing model - one
Persian page whose text layer is mojibake (`ƶŝ Ĩŝ ƾĭŵźƀƟř`) against the model's correct Persian,
and a garbled formula our own reconstruction mangled. Dropping the model's text on low support
would have destroyed both correct readings. So the verdict goes in the front matter and the
reader decides; the conversion is unchanged either way.

The witness is often unusable, and saying so is the honest answer rather than a pass or a fail:

  unchecked     no witness at all - a bare scan our OCR could not read
  unverified    a witness exists but cannot be compared: it is in a different script from the
                model's text, which means the layer's encoding is broken, or too few words
  corroborated  the witness backs most of the model's words
  low support   a comparable witness backs few of them - worth a person's eye, nothing more

Known limit, found in the hand audit: the script test compares the *dominant* script, so a
bilingual page defeats it. A Korean paper with an English title has Latin on both sides, so its
mojibake Korean layer reads as comparable and lands in "low support" rather than "unverified" -
still flagged and still never acted on, but the reason given is wrong. Comparing script per run
of text rather than per page would fix it.
"""
from __future__ import annotations

import collections
import re
import unicodedata

_WORD = re.compile(r"[^\W_]{3,}", re.UNICODE)

MIN_WITNESS_WORDS = 40      # below this the witness cannot say anything either way
CORROBORATED = 0.55         # share of the model's words the witness must back


def _words(text: str) -> list[str]:
    return [w.lower() for w in _WORD.findall(text or "")]


def _script(words: list[str]) -> str:
    """The dominant writing system, by letter. A witness in a different script from the model's
    text is not a weak witness, it is a broken one: that is what a mojibake text layer looks
    like, Latin gibberish standing where Persian should be."""
    counts: collections.Counter = collections.Counter()
    for w in words:
        for ch in w:
            try:
                name = unicodedata.name(ch)
            except ValueError:
                continue
            counts[name.split()[0]] += 1
    if not counts:
        return ""
    return counts.most_common(1)[0][0]


def check(model_text: str, witness_text: str) -> dict:
    """What the page's own reading can say about the model's. Never changes either."""
    model = _words(model_text)
    witness = _words(witness_text)
    out = {"model_words": len(model), "witness_words": len(witness)}
    if not model:
        return dict(out, state="unchecked", reason="the model returned no words")
    if len(witness) < MIN_WITNESS_WORDS:
        return dict(out, state="unchecked",
                    reason="no usable witness: the page's own reading has %d words" % len(witness))
    ms, ws = _script(model), _script(witness)
    if ms and ws and ms != ws:
        return dict(out, state="unverified", script=(ms.title(), ws.title()),
                    reason="the page's own reading is %s where the model reads %s, so its encoding "
                           "is broken and it cannot witness anything" % (ws.title(), ms.title()))
    bag = collections.Counter(witness)
    backed = sum(1 for w in model if bag[w])
    share = backed / len(model)
    out["support"] = round(share, 3)
    if share >= CORROBORATED:
        return dict(out, state="corroborated",
                    reason="the page's own reading backs %d%% of the model's words" % round(100 * share))
    return dict(out, state="low support",
                reason="the page's own reading backs only %d%% of the model's words; worth an eye, "
                       "but a garbled witness looks the same as an inventing model" % round(100 * share))
