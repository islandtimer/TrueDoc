"""Where do the missing Yes/No answers go? Sort every unanswered prescribed event by shape.

On a Key Facts Sheet the answer beside each insured event is the reason the document exists, and 7%
of them are missing. Before any rule is written the losses are sorted, because the last three
explanations offered for a moving number today were all wrong. Shapes:

  glued        the answer is fused onto the label: "Fire and Explosion Yes" in one cell
  neighbour    the event's row has no answer, but the row just above or below carries a lone one -
               the answer was split off into a row of its own
  no row       the event's name is in the table but never opens a row (buried in another cell)
  bare         the event opens a row and no answer is anywhere near it

Grades with `kfs_grade`'s own table-finding and cell splitting, never a copy of them: a copied
matcher went on reporting 55 lost answers after the grader it was copied from had been fixed.

usage (repo root): answer_census.py [how many examples of each]
"""
import collections
import glob
import os
import re
import sys

sys.path.insert(0, os.path.join("bench", "tools"))
from kfs_grade import ANSWER, EVENTS, _LEAD, blocks, cache_path, carries_answer, cells_of, held_events, held_out, sheets  # noqa: E402

SHOW = int(sys.argv[1]) if len(sys.argv) > 1 else 3
GLUED = re.compile(r"\b(yes|no|optional)\s*$", re.I)


def prescribed_table(md: str):
    best, hits = None, 0
    for block in blocks(md):
        n = sum(1 for e in EVENTS if e in " ".join(block).lower())
        if n > hits:
            best, hits = block, n
    return best if best is not None and hits >= 3 else None


def classify(table: list[str]) -> list[tuple]:
    body = [cells_of(line) for line in table[1:]]
    found = []
    for event in held_events(table[1:]):
        at = next((n for n, r in enumerate(body)
                   if r and _LEAD.sub("", r[0]).lower().startswith(event)), None)
        if at is None:
            found.append((event, "no row", ""))
            continue
        row = body[at]
        if carries_answer(row):
            found.append((event, "answered", ""))
            continue
        shown = " | ".join(c[:34] for c in row)
        if GLUED.search(row[0]):
            found.append((event, "glued", shown))
            continue
        near = [body[k] for k in (at - 1, at + 1) if 0 <= k < len(body)]
        if any(sum(1 for c in r if c) == 1 and any(ANSWER.match(c) for c in r) for r in near):
            found.append((event, "neighbour", shown))
            continue
        found.append((event, "bare", shown))
    return found


def main() -> None:
    tally = {"tuned": collections.Counter(), "held": collections.Counter()}
    sheets_with = collections.defaultdict(set)
    examples = collections.defaultdict(list)
    # The cache names a file by the first 60 characters of the PDF's name plus a hash, so the PDF's
    # own name - which is what decides the held-out split - cannot be rebuilt from the cache name
    # when it is longer than that. Map back through the grader's own naming instead.
    source = {os.path.normcase(os.path.abspath(cache_path(p))): p for _, p in sheets()}
    for path in sorted(glob.glob(os.path.join("bench", "out", "kfs", "*.md"))):
        pdf = source.get(os.path.normcase(os.path.abspath(path)))
        if pdf is None:
            continue
        md = open(path, encoding="utf-8").read()
        table = prescribed_table(md)
        if table is None:
            continue
        side = "held" if held_out(pdf) else "tuned"
        for event, shape, shown in classify(table):
            tally[side][shape] += 1
            if shape != "answered":
                sheets_with[shape].add(os.path.basename(path))
                if len(examples[shape]) < SHOW:
                    examples[shape].append((os.path.basename(path)[:40], event, shown))
    for side in ("tuned", "held"):
        total = sum(tally[side].values())
        print(f"\n{side}: {total} prescribed events")
        for shape, n in tally[side].most_common():
            print(f"   {n:5d}  {shape:10s} ({100.0 * n / max(1, total):4.1f}%)")
    for shape in ("glued", "neighbour", "no row", "bare"):
        if not examples[shape]:
            continue
        print(f"\n{shape} - on {len(sheets_with[shape])} sheets:")
        for name, event, shown in examples[shape]:
            print(f"   {name:42s} [{event}]  {shown}")


if __name__ == "__main__":
    main()
