"""Half the Key Facts Sheets still lose their header. Sort them by *why*, so the next rule is aimed.

The heading fold took header-whole from a third to a half. The rest fail for reasons the fold cannot
reach, and guessing from two examples is how an afternoon gets spent on the wrong rule. This reads the
cached conversions and sorts every failing sheet into a cause:

  prose above     a sentence from the paragraph above the table became the header row, pushing the
                  real header into the body ("rebuild your home (Total replacement)." at AAMI)
  column lost     the grid has fewer columns than the header needs, so a part has nowhere to go
  still split     the header is spread over rows the fold did not join
  no table        no table holding the prescribed events at all
  other           none of the above - look by hand

usage (repo root): kfs_why.py [how many examples of each]
"""
import collections
import glob
import os
import re
import sys

SHOW = int(sys.argv[1]) if len(sys.argv) > 1 else 3
OUT = os.path.join("bench", "out", "kfs")
ROW = re.compile(r"^\|.*\|\s*$")
SEP = re.compile(r"^\|[\s:|-]+\|\s*$")
PARTS = ("event", "yes", "some examples")
EVENTS = ("fire and explosion", "flood", "storm", "earthquake", "lightning", "theft",
          "actions of the sea", "malicious damage", "impact", "escape of liquid")


def blocks(md: str) -> list[list[str]]:
    found, lines, i = [], md.splitlines(), 0
    while i < len(lines):
        if ROW.match(lines[i]) and i + 1 < len(lines) and SEP.match(lines[i + 1]):
            block, j = [lines[i]], i + 2
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


def cause(md: str) -> tuple:
    best, hits = None, 0
    for block in blocks(md):
        n = sum(1 for e in EVENTS if e in " ".join(block).lower())
        if n > hits:
            best, hits = block, n
    if best is None or hits < 3:
        return "no table", ""
    head = cells_of(best[0])
    head_text = " ".join(head).lower()
    body = best[1:]
    body_text = " ".join(body).lower()
    if all(p in head_text for p in PARTS):
        return "passes now", " | ".join(head)[:90]
    missing = [p for p in PARTS if p not in head_text]
    # the row in the body that holds the header labels, if any
    label_row = next((r for r in body if any(p in r.lower() for p in PARTS)), "")
    if label_row and len(head) >= 2 and head_text.rstrip().endswith((".", ")")):
        return "prose above", " | ".join(head)[:90]
    if len(head) < 3:
        return "column lost", " | ".join(head)[:90]
    if label_row:
        return "still split", " | ".join(head)[:90]
    return "other", " | ".join(head)[:90] + "   >> " + (body[0][:60] if body else "")


def main() -> None:
    tally = collections.Counter()
    examples = collections.defaultdict(list)
    for path in sorted(glob.glob(os.path.join(OUT, "*.md"))):
        md = open(path, encoding="utf-8").read()
        kind, sample = cause(md)
        tally[kind] += 1
        if len(examples[kind]) < SHOW:
            examples[kind].append((os.path.basename(path)[:44], sample))
    total = sum(tally.values())
    print(f"{total} Key Facts Sheets:")
    for kind, n in tally.most_common():
        print(f"   {n:4d}  {kind}")
    for kind, _ in tally.most_common():
        if kind == "passes now":
            continue
        print(f"\n{kind}:")
        for name, sample in examples[kind]:
            print(f"   {name:46s} {sample}")


if __name__ == "__main__":
    main()
