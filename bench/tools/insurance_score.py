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

usage (repo root): insurance_score.py [--keep <file of page names to score>]
"""
import collections
import glob
import json
import os
import re
import sys

from olmocr.bench.tests import load_single_test

OUT = os.path.join("bench", "out", "insurance_set")
ESCAPE = re.compile(r"\\([\\`*_{}\[\]()#+\-.!$|&%~<>])")


def unescape(md: str) -> str:
    """Markdown escapes are syntax, not content."""
    return ESCAPE.sub(r"\1", md)


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
                test = load_single_test(raw)
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
                quoted = raw.get("text") or raw.get("cell") or raw.get("before") or ""
                failures.append((name, raw["type"], " ".join(str(quoted).split())[:90]))
        per_page.append((name, ok, n))

    total = sum(n for _, _, n in per_page)
    good = sum(k for _, k, _ in per_page)
    print(f"{len(per_page)} pages, {total} checks, {good} passed ({100.0 * good / max(1, total):.1f}%)")
    print()
    print(f"{'kind':10s} {'passed':>7s} {'of':>5s}")
    for kind in ("present", "order", "absent", "table"):
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
