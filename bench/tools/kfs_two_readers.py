"""Two independent readers of the same Key Facts Sheets: TrueDoc, and a model that only saw the page.

Built 17 September 2026, when Infinity-Parser2-Pro read pages 1 and 2 of all 190 sheets on a rented
GPU (`bench/gpu/build_own_sets.py` cut the pages, `bench/gpu/run_bakeoff.sh` read them, the readings
are `bench/gpu/out5/pro/own/inference.jsonl` with `manifest.json` beside them naming each page).

Two questions, and the second is the one that finds defects:

  shape   `kfs_grade.grade` on the model's two pages, exactly as it grades TrueDoc's: header whole,
          events in rows, answers attached. Same grader, same pages, same held-out fifth.
  words   for every prescribed event, did both readers find a row for it; is the Yes / No / Optional
          the same; is the mark in front of it the same; do the third columns say the same thing?
          TrueDoc's words are the PDF's own text; the model's come from looking at the page. Where
          they differ one of them is wrong - or the page is ambiguous - and a shape grader that passes
          both cannot say which, so the differences are listed for reading against the page.

**What this is and is not.** It is a way to find cells worth reading against the page image. It is
not a measure of meaning: two readers can agree and both be wrong, and a difference says nothing
about which reader erred until someone has looked at the page. Every listed difference carries an
empty `verdict` for that reading (`truedoc` / `model` / `both` / `source ambiguous`).

**The held-out fifth stays held out.** A fifth of the sheets (`kfs_grade.held_out`) is never tuned
on, and a tool that prints which cell of which held-out sheet is wrong tunes on it all the same. So
held-out sheets are counted and never listed: their differences appear as totals, by kind, and
nowhere by name. The first version of this tool (17 September) listed every sheet; the review of
18 September caught it (its F10), before any held-out cell had been read.

**Repaired with it (the same review's probes):** a leading tick or cross was stripped before the
comparison, so "covered" and "not covered" by mark compared equal; only third columns under 0.98
alike were listed, and a dropped "not" in a long condition is 0.998 alike; a row one reader missed
fell out of the count altogether. Marks are now compared as marks, negations, amounts and limiting
words are compared as a bag of their own whatever the ratio, and rows only one reader found are
counted and listed.

usage (repo root, the project's venv):
    kfs_two_readers.py                      grade, compare, list the tuned-on differences
    kfs_two_readers.py <readings folder>    another model's readings in the same form
    kfs_two_readers.py --json <file>        also write the tuned-on differences for adjudication
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

ALIKE = 0.98                       # a third column less alike than this is listed as a wording difference
TICKS, CROSSES = "✓✔☑", "✗✘☒✕✖"
# Words that turn a sentence round or bound it, and every figure: a difference in these is a
# difference in meaning however alike the sentences are otherwise.
CRITICAL = re.compile(
    r"\b(?:not|no|never|none|nor|neither|without|unless|except|excepting|excluded|excludes|excluding|exclusion|"
    r"only|other than|up to|at least|at most|more than|less than|under|over|maximum|minimum|limit|limited)\b"
    r"|n't\b|[$£€]\s?\d[\d,]*(?:\.\d+)?|\b\d[\d,]*(?:\.\d+)?\s?%|\b\d[\d,]*(?:\.\d+)?\b", re.I)


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def load(folder):
    """sheet pdf -> {page: the model's reading}, and how many readings were salvaged from a reply
    that was cut off (`place_bakeoff.layout_text`)."""
    manifest = json.loads(read(os.path.join(folder, "manifest.json")))
    readings, counts, cut_off = {}, collections.Counter(), set()
    for line in read(os.path.join(folder, "inference.jsonl")).splitlines():
        if line.strip():
            rec = json.loads(line)
            name = os.path.splitext(os.path.basename(rec["pdf"].replace("\\", "/")))[0]
            readings[name], was_cut = layout_text(rec.get("markdown") or "", counts, "model")
            if was_cut:
                cut_off.add(name)
    sheets = collections.OrderedDict()
    for m in manifest:
        if m["set"] == "kfs":
            sheets.setdefault(m["pdf"], {})[m["page"]] = readings.get(m["name"], "")
    return sheets, cut_off


def plain(s):
    """A cell as words: markup, escapes and typographic variants out, case folded. The mark in
    front of it is kept - `mark_of` reads it - and only list furniture is dropped."""
    s = re.sub(r"<br\s*/?>", " ", s)
    s = html.unescape(re.sub(r"<[^>]+>", " ", s))
    s = s.replace("\\$", "$").replace("\\|", "|").replace("**", "").replace("*", "")
    for a, b in (("’", "'"), ("‘", "'"), ("“", '"'), ("”", '"'), ("–", "-"), ("—", "-")):
        s = s.replace(a, b)
    s = re.sub(r"^[\s•·-]+", "", s)
    return re.sub(r"\s+", " ", s).strip().lower()


def mark_of(s):
    """'tick', 'cross' or '' for the mark a cell opens with: a tick and a cross are an answer."""
    lead = plain(s)[:1]
    return "tick" if lead and lead in TICKS else "cross" if lead and lead in CROSSES else ""


def norm(s):
    """The words alone, the opening mark aside (it is compared by `mark_of`, not thrown away)."""
    return re.sub(r"^[\s%s%s]+" % (TICKS, CROSSES), "", plain(s)).strip()


def critical(s):
    """The negations, limiting words and figures of a cell, as a bag."""
    return collections.Counter(re.sub(r"[\s,]", "", m.group(0).lower()) for m in CRITICAL.finditer(norm(s)))


_SPANNING = re.compile(r"<t[dh][^>]*\browspan\s*=\s*[\"']?(\d+)", re.I)


def gather_spans(md):
    """The markdown with every HTML row whose FIRST cell spans rows made one row with the rows it
    covers: their cells follow its own, in order.

    An entry is what stands beside its label. A reader that writes a table nested in a row as
    further rows under a row-spanning label (CGU's "High value items and collections", with Policy
    / Item Limit / Overall Limit over three rows) and a reader that writes it all into the entry's
    third cell hold the same words, and comparing the second's whole cell with the first's first
    row reported four "critical words" differences on 19 September that neither reader had."""
    def table(html):
        rows = kfs_grade.html_parts(html, "tr", inside=True)
        out, k = [], 0
        while k < len(rows):
            cells = kfs_grade.html_parts(rows[k], ("td", "th"), inside=True)
            span = _SPANNING.match(cells[0]) if cells else None
            n = int(span.group(1)) if span else 1
            for later in rows[k + 1:k + n]:
                cells += kfs_grade.html_parts(later, ("td", "th"), inside=True)
            out.append("<tr>" + "".join(cells) + "</tr>")
            k += max(1, n)
        return "<table>" + "".join(out) + "</table>"

    # Outermost tables only, nesting respected (`kfs_grade.html_parts`): a table inside a cell (D038) stays inside
    # its cell, and its words are that cell's words - the other way of writing the same entry.
    for whole in kfs_grade.html_parts(md, "table"):
        md = md.replace(whole, table(whole), 1)
    return md


def rows_of(md):
    """event -> (answer cell, third column) as written, from every table in the markdown, the first
    row of each included; and the events whose label opens more than one row, of which this keeps
    the first and a reader of the differences should know. A row-spanning label's rows are one
    entry (`gather_spans`).

    Every table, because a sheet's table does not always arrive as one: a full-width band inside it
    ("Cover for valuables, collections and items away...") ends one markdown table, and the rows
    under it come as another whose first row - a data row - stands where markdown wants a header.
    The first version read only the table holding the most events, and on 18 September reported
    eight rows of two RACQ sheets as missing from a reading that held every word of them."""
    out = {}
    seen = collections.Counter()
    for block in kfs_grade.blocks(gather_spans(md)):
        for line in block:
            cs = kfs_grade.cells_of(line)
            if len(cs) < 2:
                continue
            label = kfs_grade._LEAD.sub("", cs[0]).lower()
            for e in kfs_grade.EVENTS:
                if label.startswith(e):
                    seen[e] += 1
                    out.setdefault(e, (cs[1], " ".join(cs[2:])))
                    break
    return out, sorted(e for e, n in seen.items() if n > 1)


def compare(td_md, mo_md):
    """Every difference between two readings of one sheet, as dicts of `kind` and what each reader
    wrote; and the counts the totals are made of. Pure: nothing is printed, nothing is read."""
    (td, td_dup), (mo, mo_dup) = rows_of(td_md), rows_of(mo_md)
    found = []
    counts = collections.Counter(rows_truedoc=len(td), rows_model=len(mo))
    for e in sorted(set(td) | set(mo)):
        if e not in td or e not in mo:
            counts["row_one_reader_only"] += 1
            found.append({"kind": "row only one reader found", "event": e,
                          "truedoc": " | ".join(td[e]) if e in td else None, "model": " | ".join(mo[e]) if e in mo else None})
            continue
        counts["rows_both"] += 1
        (ta, tt), (ma, mt) = td[e], mo[e]
        if norm(ta) != norm(ma):
            counts["answer"] += 1
            found.append({"kind": "answer", "event": e, "truedoc": ta, "model": ma})
        if (mark_of(ta), mark_of(tt)) != (mark_of(ma), mark_of(mt)):
            counts["mark"] += 1
            found.append({"kind": "mark", "event": e, "truedoc": (ta + " | " + tt)[:120], "model": (ma + " | " + mt)[:120]})
        a, b = norm(tt), norm(mt)
        ratio = difflib.SequenceMatcher(None, a, b).ratio() if (a or b) else 1.0
        counts["third_identical"] += ratio == 1.0
        if critical(tt) != critical(mt):
            counts["critical"] += 1
            diff = (critical(tt) - critical(mt)) + (critical(mt) - critical(tt))
            found.append({"kind": "critical words", "event": e, "alike": round(ratio, 4), "differ": sorted(diff),
                          "truedoc": a, "model": b})
        elif ratio < ALIKE:
            counts["wording"] += 1
            found.append({"kind": "wording", "event": e, "alike": round(ratio, 4), "truedoc": a, "model": b})
    for e in sorted(set(td_dup) | set(mo_dup)):
        counts["label_repeated"] += 1
        found.append({"kind": "label opens more than one row", "event": e,
                      "truedoc": e in td_dup, "model": e in mo_dup})
    return found, counts


def summarise(rows, title):
    found = [g for g in rows if g.get("found")]
    events = sum(g["events"] for g in found)
    whole = sum(1 for g in found if g["header_whole"])
    print("  %-22s sheets %3d | table found %3d | header whole %3d (%.0f%%) | events in rows %4d/%d | answers attached %4d/%d" % (
        title, len(rows), len(found), whole, 100.0 * whole / max(len(rows), 1),
        sum(g["events_in_rows"] for g in found), events, sum(g["answers_attached"] for g in found), events))


KINDS = ("row_one_reader_only", "answer", "mark", "critical", "wording", "label_repeated")


def totals_line(c):
    return ("rows found by both %d (TrueDoc %d, model %d) | only one reader %d | answer differs %d | mark differs %d | "
            "critical words differ %d | wording under %.2f alike %d | third column identical %d | repeated labels %d" % (
                c["rows_both"], c["rows_truedoc"], c["rows_model"], c["row_one_reader_only"], c["answer"], c["mark"],
                c["critical"], ALIKE, c["wording"], c["third_identical"], c["label_repeated"]))


def _window(a, b):
    ops = [o for o in difflib.SequenceMatcher(None, a, b).get_opcodes() if o[0] != "equal"][:1]
    for _tag, i1, i2, j1, j2 in ops:
        return a[max(0, i1 - 25):i2 + 25][:80], b[max(0, j1 - 25):j2 + 25][:80]
    return a[:80], b[:80]


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    json_out = argv[argv.index("--json") + 1] if "--json" in argv else None
    if json_out in args:
        args.remove(json_out)
    folder = args[0] if args else os.path.join("bench", "gpu", "out5", "pro", "own")

    import doc_library
    sheets, cut_off = load(folder)
    pairs = []
    for rel, pages in sheets.items():
        pdf = doc_library.absolute(rel)
        cache = kfs_grade.cache_path(pdf)
        if os.path.exists(cache):
            pairs.append((pdf, read(cache), "\n\n".join(pages[p] for p in sorted(pages))))
    print("%d sheets read by both (of %d the model read; %d of the model's pages were salvaged from a cut-off reply)\n\nSHAPE" % (
        len(pairs), len(sheets), len(cut_off)))
    for label, want in (("tuned on", False), ("held out, never tuned on", True)):
        print(" " + label)
        summarise([kfs_grade.grade(td) for pdf, td, _ in pairs if kfs_grade.held_out(pdf) == want], "TrueDoc")
        summarise([kfs_grade.grade(mo) for pdf, _, mo in pairs if kfs_grade.held_out(pdf) == want], "the model")

    listed, held = [], collections.Counter()
    tuned = collections.Counter()
    for pdf, td_md, mo_md in pairs:
        found, counts = compare(td_md, mo_md)
        if kfs_grade.held_out(pdf):
            held.update(counts)                             # totals only: no sheet, no event, no words
        else:
            tuned.update(counts)
            # the sheet's place in the library, not its bare name: one file kept under two product
            # lines is two sheets here, and should look like two and not like one counted twice
            listed.extend(dict(d, sheet=doc_library.relative(pdf), verdict=None) for d in found)
    print("\nWORDS\n tuned on\n  " + totals_line(tuned))
    print(" held out, never tuned on (totals only - these sheets are never listed)\n  " + totals_line(held))
    print("\nDIFFERENCES ON TUNED-ON SHEETS, to be read against the page image (neither reader is the answer)")
    for kind in ("row only one reader found", "answer", "mark", "critical words", "wording", "label opens more than one row"):
        for d in [d for d in listed if d["kind"] == kind]:
            if kind in ("critical words", "wording"):
                a, b = _window(d["truedoc"], d["model"])
                extra = " differ %s" % d["differ"] if kind == "critical words" else ""
                print("  %-14s %.4f %-44s %-20s%s\n      TrueDoc [%s]\n      model   [%s]" % (
                    kind, d["alike"], d["sheet"][-60:], d["event"], extra, a, b))
            else:
                print("  %-30s %-44s %-20s TrueDoc %r | model %r" % (
                    kind, d["sheet"][-60:], d["event"], str(d["truedoc"])[:40], str(d["model"])[:40]))
    if json_out:
        with open(json_out, "w", encoding="utf-8") as f:
            json.dump(listed, f, indent=1, ensure_ascii=False)
        print("\n%d differences written to %s, each with an empty verdict" % (len(listed), json_out))


if __name__ == "__main__":
    main(sys.argv[1:])
