"""Grade every Key Facts Sheet in the owner's library against the structure the law prescribes.

A Key Facts Sheet is prescribed by the Australian Government under the Insurance Contracts Act 1984:
the same three columns, the same header wording, the same list of insured events, at every insurer.
The typesetting is *not* prescribed - the sheets only have to look the same to a reader - so the
converter meets 34 different layouts of one known document. That is the rarest thing a converter can
have: **a few hundred pages where the right answer is known without anyone writing a check**.

What it is for, and what it is not for. It is an oracle for deriving rules and a regression guard for
keeping them. It is not a licence to special-case: a rule that reads "if this document is a Key Facts
Sheet" fixes 202 documents and no others, and the whole point is that the faults here - a header that
wraps onto three lines, a full-width band inside a table, a label split from its answer - are faults
everywhere. So a rule earns its place by being written in geometry and typography, verified here
because here the answer is known, and then measured on the olmOCR benchmark to show it does no harm
elsewhere.

Graded per document, all of it structural (nothing here knows what a correct *answer* is, only what a
correct *shape* is):

    header whole      the three prescribed header parts are in the header row, not leaked into the body
    events in rows    each prescribed event opens a row of its own
    answers attached  that row carries a Yes / No / Optional in the answer column
    band its own row  a full-width band inside the table ("Cover for valuables...") is not swallowed
    no orphans        no row whose only content is a lowercase continuation of the row above

A fifth of the sheets are held out by a hash of their filename and never reported alongside the rest,
so a rule cannot be tuned until every sheet passes. Same idea as `bench/holdout.txt` (D016).

usage (repo root):
    kfs_grade.py                     grade every sheet, four workers, reusing cached conversions
    kfs_grade.py --workers 6         more workers
    kfs_grade.py --fresh             re-convert, ignoring the cache
    kfs_grade.py --limit 20          a quick pass over the first 20 insurers
    kfs_grade.py --failures header   list the documents failing one property
"""
import collections
import concurrent.futures
import glob
import hashlib
import os
import re
import sys

LIB = os.path.join("C:/", "Users", "griff", "OneDrive", "Documents", "10 Have a crack",
                   "25 InsurancePlatform", "uploads", "PDS Docs")
OUT = os.path.join("bench", "out", "kfs")
HOLDOUT_IN = 5          # one sheet in five is never reported with the tuned-on set

ROW = re.compile(r"^\|.*\|\s*$")
SEP = re.compile(r"^\|[\s:|-]+\|\s*$")
_LEAD = re.compile(r"^[^0-9A-Za-z]+")
ANSWER = re.compile(r"^\s*(yes|no|optional|yes\s*/\s*no|not covered|covered)\b", re.I)
BAND = re.compile(r"^\|\s*([^|]{12,96}?)\s*\|(?:\s*\|)+\s*$")
# The header's three parts, however an insurer breaks its lines across them.
HEADER_PARTS = ("event", "yes", "some examples")
# The events the regulation lists. A buildings sheet and a contents sheet differ in the tail, so a
# sheet is graded on the ones it actually contains, never on a fixed count.
EVENTS = ("fire and explosion", "flood", "storm", "earthquake", "lightning", "theft",
          "actions of the sea", "malicious damage", "impact", "escape of liquid",
          "accidental breakage", "accidental damage", "high value items", "items away")


def sheets() -> list[tuple[str, str]]:
    """(insurer, path) for every Key Facts Sheet in the library, insurer by insurer."""
    found = []
    for path in sorted(glob.glob(os.path.join(LIB, "*", "*", "*.pdf"))):
        base = os.path.basename(path).lower()
        if "kfs" not in base and "key-fact" not in base and "key_fact" not in base:
            continue
        insurer = path.replace("\\", "/").split("/")[-3]
        if insurer.startswith("zz_"):
            continue
        found.append((insurer, path))
    return found


def held_out(path: str) -> bool:
    """A stable fifth, chosen by the filename so the split never moves."""
    digest = hashlib.sha1(os.path.basename(path).encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % HOLDOUT_IN == 0


def cache_path(path: str) -> str:
    stem = hashlib.sha1(path.encode("utf-8")).hexdigest()[:12]
    return os.path.join(OUT, os.path.splitext(os.path.basename(path))[0][:60] + "_" + stem + ".md")


def convert_one(job: tuple) -> tuple:
    """Page 1 and 2: some insurers start the table on page 1 and finish it on page 2."""
    path, fresh = job
    target = cache_path(path)
    if not fresh and os.path.exists(target) and os.path.getsize(target) > 0:
        return path, open(target, encoding="utf-8").read(), "cached"
    from truedoc.pipeline import ConvertOptions, convert
    try:
        md = convert(path, ConvertOptions(frontmatter=False, pages=[1, 2]))
    except Exception as exc:
        return path, "", "FAILED: " + repr(exc)[:90]
    os.makedirs(OUT, exist_ok=True)
    with open(target, "w", encoding="utf-8") as fh:
        fh.write(md)
    return path, md, f"{len(md.split())} words"


def blocks(md: str) -> list[list[str]]:
    """Every table in the markdown, HTML ones flattened to the same pipe shape."""
    found = []
    lines = md.splitlines()
    i = 0
    while i < len(lines):
        if ROW.match(lines[i]) and i + 1 < len(lines) and SEP.match(lines[i + 1]):
            block = [lines[i]]
            j = i + 2
            while j < len(lines) and ROW.match(lines[j]):
                block.append(lines[j])
                j += 1
            found.append(block)
            i = j
            continue
        i += 1
    for m in re.finditer(r"<table.*?</table>", md, re.S):
        rows = []
        for r in re.findall(r"<tr.*?</tr>", m.group(0), re.S):
            cells = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", c)).strip()
                     for c in re.findall(r"<t[dh][^>]*>.*?</t[dh]>", r, re.S)]
            rows.append("| " + " | ".join(cells) + " |")
        if rows:
            found.append(rows)
    return found


def cells_of(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def carries_answer(cells: list[str]) -> bool:
    """Does this row hold its Yes / No / Optional in the answer column - the second cell?

    The column is headed "Yes / No / Optional", so the answer belongs in that column and nowhere
    else. An earlier test accepted an answer word opening *any* later cell, so a row reading
    "Flood |  | Optional Excludes damage to the liner..." - the answer fused onto the front of the
    exclusions and filed in the third column, the answer column left blank - passed as answered.
    A reader of that row sees a blank where the answer should be, so it is not answered.

    Shared by everything that asks the question, so no copy of it can drift from this one.
    """
    return len(cells) > 1 and bool(ANSWER.match(cells[1]))


def held_events(body: list[str]) -> list[str]:
    """The prescribed events a table holds: those named in its label column, read down the table.

    An event is held if its name is in the *label column* - the first cell of each row, read down
    the table - not if it appears anywhere in the table. Matching the whole table counted names
    *mentioned* inside other cells as events with no row of their own: "Accidental Damage" inside
    the exclusions of the Accidental Breakage row (91 sheets, 76 of them with the real event
    answered), "items away" inside the band that opens the valuables section (12), "malicious
    damage" inside the fire exclusion (8). That inflated both the missing count and the total.

    Read down the column rather than row by row, so a label genuinely split across two rows
    ("Accidental" over "breakage") still counts as held and still fails - that is real damage and
    worth seeing. A row that is one cell spanning the table is a band, not a label, and is left out.

    Shared with every diagnostic that sorts the events, so none of them can count a different set.
    """
    labels = " ".join(cs[0] for cs in (cells_of(line) for line in body) if len(cs) >= 2).lower()
    return [e for e in EVENTS if e in labels]


def grade(md: str) -> dict:
    """The prescribed table, found by the events it holds, then graded on shape alone."""
    best, best_hits = None, 0
    for block in blocks(md):
        text = " ".join(block).lower()
        hits = sum(1 for e in EVENTS if e in text)
        if hits > best_hits:
            best, best_hits = block, hits
    if best is None or best_hits < 3:
        return {"found": False}

    head = cells_of(best[0])
    head_text = " ".join(head).lower()
    body = best[1:]
    body_text = " ".join(body).lower()

    # Every event the sheet holds, and whether it opens a row with an answer beside it.
    want = held_events(body)
    opens = answered = 0
    for event in want:
        for line in body:
            cs = cells_of(line)
            # The label must *open* the cell, not merely appear in it. A band spanning the table -
            # "Cover for valuables, collections and items away from the insured address" - contains
            # the name of a prescribed event, and once bands were written into the first column this
            # matched as that event's row, a row which by its nature carries no answer. That read as
            # 47 events losing their Yes/No when nothing in the converter had changed for them.
            if cs and _LEAD.sub("", cs[0]).lower().startswith(event):
                opens += 1
                if carries_answer(cs):
                    answered += 1
                break

    bands = [m.group(1) for m in (BAND.match(l) for l in body) if m]
    swallowed = re.search(r"[.!?]\s+(cover for [a-z][^|]{10,90})\s*\|", body_text)
    orphans = 0
    for line in body:
        cs = cells_of(line)
        filled = [c for c in cs if c]
        if len(cs) >= 2 and len(filled) == 1 and filled[0][:1].islower():
            orphans += 1

    return {
        "found": True,
        "events": len(want),
        "header_whole": all(p in head_text for p in HEADER_PARTS),
        "header_leaks": any(p in body_text for p in HEADER_PARTS if p not in head_text),
        "events_in_rows": opens,
        "answers_attached": answered,
        "band_own_row": bool(bands),
        "band_swallowed": bool(swallowed),
        "orphans": orphans,
    }


def report(rows: list[tuple], title: str) -> None:
    if not rows:
        return
    n = len(rows)
    tally = collections.Counter()
    events = opens = answers = 0
    for _, _, g in rows:
        if not g.get("found"):
            tally["no prescribed table found"] += 1
            continue
        tally["header whole"] += bool(g["header_whole"] and not g["header_leaks"])
        tally["band swallowed"] += bool(g["band_swallowed"])
        tally["rows orphaned"] += bool(g["orphans"])
        events += g["events"]
        opens += g["events_in_rows"]
        answers += g["answers_attached"]
    print(f"\n{title}: {n} sheets")
    print(f"   {tally['no prescribed table found']:4d}  no prescribed table found")
    print(f"   {tally['header whole']:4d}  header whole ({100.0 * tally['header whole'] / n:.0f}%)")
    print(f"   {opens:4d}  of {events} prescribed events open a row of their own"
          f" ({100.0 * opens / max(1, events):.0f}%)")
    print(f"   {answers:4d}  of {events} carry their Yes / No / Optional"
          f" ({100.0 * answers / max(1, events):.0f}%)")
    print(f"   {tally['band swallowed']:4d}  a full-width band swallowed by the cell above")
    print(f"   {tally['rows orphaned']:4d}  hold a row that is only a continuation")


def main() -> None:
    args = sys.argv[1:]
    fresh = "--fresh" in args
    workers = int(args[args.index("--workers") + 1]) if "--workers" in args else 4
    limit = int(args[args.index("--limit") + 1]) if "--limit" in args else None
    failing = args[args.index("--failures") + 1] if "--failures" in args else None

    todo = sheets()
    if limit:
        seen, trimmed = set(), []
        for insurer, path in todo:
            if insurer in seen:
                continue
            seen.add(insurer)
            trimmed.append((insurer, path))
            if len(trimmed) >= limit:
                break
        todo = trimmed
    print(f"{len(todo)} Key Facts Sheets, {len({i for i, _ in todo})} insurers", flush=True)

    by_path = {path: insurer for insurer, path in todo}
    results = []
    done = 0
    # Processes, not threads: the converter keeps global state and fails silently in a thread.
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
        for path, md, note in pool.map(convert_one, [(p, fresh) for _, p in todo]):
            done += 1
            if done % 25 == 0 or note.startswith("FAILED"):
                print(f"  {done:3d}/{len(todo)}  {os.path.basename(path)[:48]:50s} {note}", flush=True)
            results.append((by_path[path], path, grade(md) if md else {"found": False}))

    tuned = [r for r in results if not held_out(r[1])]
    holdout = [r for r in results if held_out(r[1])]
    report(tuned, "Tuned on")
    report(holdout, "Held out (never tuned on)")

    if failing:
        print(f"\nsheets failing '{failing}':")
        for insurer, path, g in sorted(results):
            bad = (not g.get("found") or not g["header_whole"] or g["header_leaks"]) \
                if failing == "header" else \
                (g.get("band_swallowed") if failing == "band" else g.get("orphans"))
            if bad:
                print(f"   {'held out' if held_out(path) else '        '}  {insurer[:22]:24s} "
                      f"{os.path.basename(path)[:56]}")


if __name__ == "__main__":
    main()
