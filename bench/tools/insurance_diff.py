"""Every insurance-set check whose outcome differs between two folders of converted pages, named one by one.

`insurance_score.py` scores the folder `converted/` and prints totals and the first twenty failures; a total that moves
by one can be a check won and two lost. This runs every check, through the benchmark's own `load_single_test` and the
scorer's own unescaping, on two folders side by side, and names each check that passes in one and fails in the other.

usage (repo root): insurance_diff.py <folder A> <folder B>   e.g. insurance_diff.py converted_13sept converted_e32e431
       (folders under bench/out/insurance_set/)
"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.join("bench", "tools"))
from insurance_score import OUT, ListItemTest, unescape  # noqa: E402
from olmocr.bench.tests import load_single_test  # noqa: E402


def outcomes(folder: str, name: str) -> list[tuple[str, str, bool]]:
    md_path = os.path.join(OUT, folder, name + ".md")
    if not os.path.exists(md_path):
        return []
    md = unescape(open(md_path, encoding="utf-8").read())
    found = []
    for n, line in enumerate(l.strip() for l in open(os.path.join(OUT, "checks_a", name + ".jsonl"), encoding="utf-8")):
        if not line:
            continue
        raw = json.loads(line)
        raw.setdefault("id", f"{name}_{n}")
        raw.setdefault("pdf", name + ".pdf")
        raw.setdefault("page", 1)
        quoted = " ".join(str(raw.get("text") or raw.get("cell") or raw.get("item") or raw.get("before") or "").split())
        try:
            # The set's own kind (D028), run as insurance_score.py runs it: without it the five list-item checks fail
            # in every folder, and a total read off this tool is five short of the score (found 23 September 2026).
            test = ListItemTest(raw) if raw.get("type") == "list_item" else load_single_test(raw)
            good = bool(test.run(md)[0])
        except Exception:
            good = False
        found.append((raw.get("type", "?"), quoted, good))
    return found


def main() -> None:
    a, b = sys.argv[1], sys.argv[2]
    names = sorted(os.path.splitext(os.path.basename(p))[0] for p in glob.glob(os.path.join(OUT, "checks_a", "*.jsonl")))
    totals = {a: 0, b: 0}
    changed = 0
    for name in names:
        left, right = outcomes(a, name), outcomes(b, name)
        if not left or not right:
            continue
        totals[a] += sum(g for _, _, g in left)
        totals[b] += sum(g for _, _, g in right)
        for (kind, quoted, ga), (_, _, gb) in zip(left, right):
            if ga != gb:
                changed += 1
                print(f"  {'WON ' if gb else 'LOST'}  {name[:40]:40s} {kind:8s} {quoted[:90]}")
    print(f"{a}: {totals[a]} passed; {b}: {totals[b]} passed; {changed} checks changed")


if __name__ == "__main__":
    main()
