"""Two independent readers of the same Key Facts Sheets: TrueDoc, and a model that only saw the page.

Built 17 September 2026, when Infinity-Parser2-Pro read pages 1 and 2 of all 190 sheets on a rented
GPU (`bench/gpu/build_own_sets.py` cut the pages, `bench/gpu/run_bakeoff.sh` read them, the readings
are `bench/gpu/out5/pro/own/inference.jsonl` with `manifest.json` beside them naming each page).

Two questions, and the second is the one that finds defects:

  shape   `kfs_grade.grade` on the model's two pages, exactly as it grades TrueDoc's: header whole,
          events in rows, answers attached. Same grader, same pages, same held-out fifth.
  words   for every prescribed event both readers found, is the Yes / No / Optional the same, and is
          the third column the same words? TrueDoc's words are the PDF's own text; the model's come
          from looking at the page. Where they differ one of them is wrong, and a shape grader that
          passes both cannot say which - so the differences are listed for reading against the page.

The differences are evidence to read, not a score: on 17 September every one of the fifteen that was
read against TrueDoc's own markdown was TrueDoc's (a wrapped cell line opening with a capital made a
row of its own; a stray word from a neighbouring cell).

usage (repo root, the project's venv):
    kfs_two_readers.py                      grade, compare, list the differences
    kfs_two_readers.py <readings folder>    another model's readings in the same form
"""
import collections
import difflib
import html
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "gpu"))
import kfs_grade  # noqa: E402
from place_bakeoff import layout_text  # noqa: E402

FOLDER = sys.argv[1] if len(sys.argv) > 1 else os.path.join("bench", "gpu", "out5", "pro", "own")


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def load():
    """sheet pdf -> {page: the model's reading}, from the manifest and the readings beside it."""
    manifest = json.loads(read(os.path.join(FOLDER, "manifest.json")))
    readings, counts = {}, collections.Counter()
    for line in read(os.path.join(FOLDER, "inference.jsonl")).splitlines():
        if line.strip():
            rec = json.loads(line)
            name = os.path.splitext(os.path.basename(rec["pdf"].replace("\\", "/")))[0]
            readings[name] = layout_text(rec.get("markdown") or "", counts, "model")
    sheets = collections.OrderedDict()
    for m in manifest:
        if m["set"] == "kfs":
            sheets.setdefault(m["pdf"], {})[m["page"]] = readings.get(m["name"], "")
    return sheets


def norm(s):
    s = re.sub(r"<br\s*/?>", " ", s)
    s = html.unescape(re.sub(r"<[^>]+>", " ", s))
    s = s.replace("\\$", "$").replace("\\|", "|").replace("**", "").replace("*", "")
    for a, b in (("’", "'"), ("‘", "'"), ("“", '"'), ("”", '"'), ("–", "-"), ("—", "-")):
        s = s.replace(a, b)
    s = re.sub(r"^[\s•✓✗✔✘-]+", "", s)
    return re.sub(r"\s+", " ", s).strip().lower()


def rows_of(md):
    """event -> (answer, third column), from the table holding the most prescribed events."""
    best, hits = None, 0
    for block in kfs_grade.blocks(md):
        text = " ".join(block).lower()
        h = sum(1 for e in kfs_grade.EVENTS if e in text)
        if h > hits:
            best, hits = block, h
    out = {}
    for line in (best or [])[1:]:
        cs = kfs_grade.cells_of(line)
        if len(cs) < 2:
            continue
        label = kfs_grade._LEAD.sub("", cs[0]).lower()
        for e in kfs_grade.EVENTS:
            if label.startswith(e) and e not in out:
                out[e] = (norm(cs[1]), norm(" ".join(cs[2:])))
                break
    return out


def summarise(rows, title):
    found = [g for g in rows if g.get("found")]
    events = sum(g["events"] for g in found)
    whole = sum(1 for g in found if g["header_whole"])
    print("  %-22s sheets %3d | table found %3d | header whole %3d (%.0f%%) | events in rows %4d/%d | answers attached %4d/%d" % (
        title, len(rows), len(found), whole, 100.0 * whole / max(len(rows), 1),
        sum(g["events_in_rows"] for g in found), events, sum(g["answers_attached"] for g in found), events))


def main():
    sheets = load()
    pairs = []
    for pdf, pages in sheets.items():
        cache = kfs_grade.cache_path(pdf)
        if os.path.exists(cache):
            pairs.append((pdf, read(cache), "\n\n".join(pages[p] for p in sorted(pages))))
    print("%d sheets read by both (of %d the model read)\n\nSHAPE" % (len(pairs), len(sheets)))
    for label, want in (("tuned on", False), ("held out, never tuned on", True)):
        print(" " + label)
        summarise([kfs_grade.grade(td) for pdf, td, _ in pairs if kfs_grade.held_out(pdf) == want], "TrueDoc")
        summarise([kfs_grade.grade(mo) for pdf, _, mo in pairs if kfs_grade.held_out(pdf) == want], "the model")

    both = same = 0
    ratios, answers, texts = [], [], []
    for pdf, td_md, mo_md in pairs:
        td, mo = rows_of(td_md), rows_of(mo_md)
        for e in td:
            if e not in mo:
                continue
            both += 1
            if td[e][0] == mo[e][0]:
                same += 1
            else:
                answers.append((os.path.basename(pdf), e, td[e][0], mo[e][0]))
            r = difflib.SequenceMatcher(None, td[e][1], mo[e][1]).ratio() if (td[e][1] or mo[e][1]) else 1.0
            ratios.append(r)
            if r < 0.98:
                texts.append((r, os.path.basename(pdf), e, td[e][1], mo[e][1]))
    print("\nWORDS\n  event rows found by both: %d" % both)
    print("  answer identical: %d (%.2f%%), different: %d" % (same, 100.0 * same / max(both, 1), both - same))
    print("  third column identical: %d | at least 0.98 alike: %d | under 0.98: %d" % (
        sum(1 for r in ratios if r == 1.0), sum(1 for r in ratios if r >= 0.98), len(texts)))
    for sheet, e, a, b in answers:
        print("  answer   %-46s %-22s TrueDoc %r | model %r" % (sheet[:46], e, a[:30], b[:30]))
    for r, sheet, e, a, b in sorted(texts):
        ops = [o for o in difflib.SequenceMatcher(None, a, b).get_opcodes() if o[0] != "equal"][:1]
        for tag, i1, i2, j1, j2 in ops:
            print("  %.2f     %-46s %-22s TrueDoc [%s] | model [%s]" % (
                r, sheet[:46], e, a[max(0, i1 - 20):i2 + 20][:70], b[max(0, j1 - 20):j2 + 20][:70]))


if __name__ == "__main__":
    main()
