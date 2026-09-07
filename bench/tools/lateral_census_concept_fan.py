"""Census used by the concept-fan round (7 Sept 2026). Read-only; runs no conversion.

Usage (from the repo root, project venv):
    .venv/Scripts/python bench/out/swarm/concept_fan_census.py long_tiny_text
    .venv/Scripts/python bench/out/swarm/concept_fan_census.py multi_column
    .venv/Scripts/python bench/out/swarm/concept_fan_census.py old_scans

For every failing present/order check of the section it aligns the reference
snippet against our run-48 output with the checker's own normalisation, prints
the near misses as REF/OUT pairs (the input for the two-witnesses test, idea 3)
and classifies the differing tokens (space lost after punctuation, stray quote,
non-word for word, glued or split words), which sizes idea 4.
"""
import collections
import difflib
import json
import os
import re
import sys

from rapidfuzz.fuzz import partial_ratio_alignment

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)
from olmocr.bench.tests import normalize_text  # noqa: E402

RUN = os.path.join(ROOT, "bench", "runs", "truedoc47-20260907-090140", "failed_tests.jsonl")
OUT = os.path.join(ROOT, "bench", "data", "olmocr-bench", "bench_data", "truedoc47")
WORDS_FILE = os.path.join(ROOT, "truedoc", "data", "en_common_words.txt")


def section_of(r):
    return r["pdf"].replace(chr(92), "/").split("/")[0]


def stem_of(r):
    return r["pdf"].replace(chr(92), "/").split("/")[-1][:-4]


def output_body(r):
    f = os.path.join(OUT, section_of(r), stem_of(r) + "_pg1_repeat1.md")
    if not os.path.exists(f):
        return None
    t = open(f, encoding="utf-8").read()
    return t.split("---", 2)[-1] if t.startswith("---") else t


def classify(rtoks, gtoks, words):
    strip = lambda t: t.strip(".,;:!?()[]\"'-")
    if len(gtoks) == 1 and len(rtoks) == 2 and re.search(r"[,;:.]\S", gtoks[0]):
        return "space-lost-after-punct"
    if len(gtoks) == 1 and len(rtoks) >= 2 and gtoks[0].replace("-", "") == "".join(rtoks).replace("-", ""):
        return "glued-words"
    if len(gtoks) >= 2 and len(rtoks) == 1 and "".join(gtoks) == rtoks[0]:
        return "split-word"
    if len(gtoks) == 1 and len(rtoks) == 1:
        g, rr = strip(gtoks[0]).lower(), strip(rtoks[0]).lower()
        if g == rr:
            return "punct/quote-only"
        if g.isalpha() and g not in words and rr in words:
            return "nonword-for-word"
        if g.isalpha() and g in words:
            return "word-for-word"
        return "other-single"
    return "multi"


def main(section):
    rows = [json.loads(l) for l in open(RUN, encoding="utf-8")]
    words = {w.strip().lower() for w in open(WORDS_FILE, encoding="utf-8") if w.strip()}
    hist = collections.Counter()
    kinds = collections.Counter()
    for r in rows:
        if section_of(r) != section or r["type"] not in ("present", "order"):
            continue
        body = output_body(r)
        if body is None or not body.strip():
            hist["empty-or-missing-output"] += 1
            continue
        content = normalize_text(body)
        snippets = [r["text"]] if r["type"] == "present" else [r["before"], r["after"]]
        for sn in snippets:
            ref = normalize_text(sn)
            a = partial_ratio_alignment(ref, content)
            score = a.score if a else 0.0
            band = "exact" if score >= 99.9 else "near(<=3 edits)" if score >= 95 else "partial(80-95)" if score >= 80 else "missing"
            hist[band] += 1
            if 90 <= score < 99.9:
                got = content[a.dest_start:a.dest_end]
                print(f"--- {stem_of(r)} score={score:.1f}")
                print("   REF:", ref[:120])
                print("   OUT:", got[:120])
                sm = difflib.SequenceMatcher(a=ref.split(), b=got.split())
                for tag, i1, i2, j1, j2 in sm.get_opcodes():
                    if tag != "equal":
                        kinds[classify(ref.split()[i1:i2], got.split()[j1:j2], words)] += 1
    print("\nsnippet bands:", dict(hist))
    print("token error classes (near misses only):", dict(kinds))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "long_tiny_text")
