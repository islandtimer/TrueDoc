r"""Score TrueDoc against the insurance test set.

The checks are run by the benchmark's own machinery - the same code that has judged ninety-one runs -
so nothing new is being invented here. One thing is added, and it matters:

**markdown escapes are undone before comparing.** D024 has us write a literal dollar sign as `\$`, and a
pipe inside a table cell as `\|`. Those backslashes are markdown syntax, not content: a reader sees
"$500" either way. Left in, a check quoting "the excess is $500 for each claim" fails against our
"the excess is \$500 for each claim" - the same words, one character of syntax apart - and across an
insurance library, where prices are on every page, that would make a correct converter look broken. The
benchmark's own normaliser already strips `**bold**` and `*italics*` for exactly this reason; escapes
are the same kind of thing.

**One kind of check is our own: `list_item`.** Under D028 a list set inside a table cell is written as a
list, so a check can no longer ask for one of its entries as a cell of its own ("Solar panels" out of
Kogan's boxed list of covers). It asks instead for the entry, with its tick or cross, among the list
elements of a table cell under its column heading - `{"type": "list_item", "item": ..., "top_heading":
...}`. An entry's own words are compared, not its sub-list's, after the benchmark's own normalising.

usage (repo root): insurance_score.py [--keep <file of page names to score>]
"""
import collections
import glob
import json
import os
import re
import sys

from olmocr.bench.tests import load_single_test, normalize_text

OUT = os.path.join("bench", "out", "insurance_set")
ESCAPE = re.compile(r"\\([\\`*_{}\[\]()#+\-.!$|&%~<>])")
KINDS = ("present", "order", "absent", "table", "list_item")


def unescape(md: str) -> str:
    """Markdown escapes are syntax, not content."""
    return ESCAPE.sub(r"\1", md)


class ListItemTest:
    """An entry of a list set inside a table cell (D028), under its column's heading."""

    def __init__(self, raw: dict):
        self.item = raw["item"]
        self.top_heading = raw.get("top_heading") or ""

    def run(self, md: str) -> tuple[bool, str]:
        from bs4 import BeautifulSoup

        want = normalize_text(self.item)
        heading = normalize_text(self.top_heading) if self.top_heading else None
        elsewhere = False
        for table in BeautifulSoup(md, "html.parser").find_all("table"):
            taken: set[tuple[int, int]] = set()
            headings: dict[int, list[str]] = {}
            for r, tr in enumerate(table.find_all("tr")):
                c = 0
                for cell in tr.find_all(["th", "td"], recursive=False):
                    while (r, c) in taken:
                        c += 1
                    span, down = int(cell.get("colspan", 1)), int(cell.get("rowspan", 1))
                    taken |= {(r + i, c + j) for i in range(down) for j in range(span)}
                    if cell.name == "th":
                        for j in range(span):
                            headings.setdefault(c + j, []).append(normalize_text(cell.get_text(" ")))
                    for li in cell.find_all("li"):
                        own = " ".join(li.find_all(string=True, recursive=False))
                        if normalize_text(own) != want:
                            continue
                        if heading is None or any(heading in headings.get(c + j, []) for j in range(span)):
                            return True, ""
                        elsewhere = True
                    c += span
        return False, ("the entry is in a list, but not under that heading" if elsewhere
                       else "no list in a table cell holds that entry")


def main() -> None:
    keep = None
    if "--keep" in sys.argv:
        path = sys.argv[sys.argv.index("--keep") + 1]
        keep = {l.strip() for l in open(path, encoding="utf-8") if l.strip()}

    names = sorted(os.path.splitext(os.path.basename(p))[0]
                   for p in glob.glob(os.path.join(OUT, "checks_a", "*.jsonl")))
    if keep is not None:
        names = [n for n in names if n in keep]

    by_kind = collections.Counter()
    passed_kind = collections.Counter()
    per_page = []
    failures = []
    for name in names:
        md_path = os.path.join(OUT, "converted", name + ".md")
        if not os.path.exists(md_path):
            continue
        md = unescape(open(md_path, encoding="utf-8").read())
        n = ok = 0
        for line in open(os.path.join(OUT, "checks_a", name + ".jsonl"), encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            raw.setdefault("id", f"{name}_{n}")
            raw.setdefault("pdf", name + ".pdf")
            raw.setdefault("page", 1)
            try:
                test = ListItemTest(raw) if raw.get("type") == "list_item" else load_single_test(raw)
            except Exception as exc:
                failures.append((name, raw.get("type"), "the check itself is malformed: " + repr(exc)[:70]))
                continue
            n += 1
            by_kind[raw["type"]] += 1
            try:
                good, why = test.run(md)
            except Exception as exc:
                good, why = False, "the check could not run: " + repr(exc)[:70]
            ok += good
            passed_kind[raw["type"]] += good
            if not good:
                quoted = raw.get("text") or raw.get("cell") or raw.get("item") or raw.get("before") or ""
                failures.append((name, raw["type"], " ".join(str(quoted).split())[:90]))
        per_page.append((name, ok, n))

    total = sum(n for _, _, n in per_page)
    good = sum(k for _, k, _ in per_page)
    print(f"{len(per_page)} pages, {total} checks, {good} passed ({100.0 * good / max(1, total):.1f}%)")
    print()
    print(f"{'kind':10s} {'passed':>7s} {'of':>5s}")
    for kind in KINDS:
        if by_kind[kind]:
            print(f"{kind:10s} {passed_kind[kind]:7d} {by_kind[kind]:5d}   "
                  f"{100.0 * passed_kind[kind] / by_kind[kind]:5.1f}%")
    print()
    print("pages, worst first:")
    for name, ok, n in sorted(per_page, key=lambda r: (r[1] / max(1, r[2]))):
        print(f"   {ok:2d}/{n:<2d}  {name[:66]}")
    print()
    print(f"the {min(20, len(failures))} failures to look at first:")
    for name, kind, quoted in failures[:20]:
        print(f"   {name[:40]:42s} {kind:8s} {quoted}")


if __name__ == "__main__":
    main()
