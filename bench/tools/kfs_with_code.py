"""Convert the Key Facts Sheets with the `truedoc` found at <code root>, into <out folder>; then compare two folders.

The Key Facts twin of `insurance_with_code.py`, for measuring a change code against code: run it once with a git
worktree of the commit before the change and once with the repository root, into two folders, and compare them.
`bench/out/kfs` is the grader's cache and not a before state. The files carry the grader's own names
(`kfs_grade.cache_path`), so `kfs_changed.py`'s rule holds here too: a tuned-on sheet that differs is named, a
held-out sheet is counted and never named.

Each worker puts <code root> first on its path and reports which `truedoc` it imported; this file sits in
`bench/tools`, which holds no `truedoc` folder, so nothing shadows it.

usage (repo root, the project's venv):
    kfs_with_code.py <code root> <out folder> [workers] [--only <file of sheet paths relative to the library, "@page" allowed>]
    kfs_with_code.py --compare <folder before> <folder after>
"""
import concurrent.futures
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ARGS = sys.argv[1:]
ROOT, OUT = (ARGS + ["", ""])[:2]


def one(path):
    sys.path.insert(0, ROOT)
    import truedoc
    from truedoc.pipeline import ConvertOptions, convert, first_pages
    import kfs_grade
    target = os.path.join(OUT, os.path.basename(kfs_grade.cache_path(path)))
    try:
        md = convert(path, ConvertOptions(frontmatter=False, pages=first_pages(path, 2)))
    except Exception as exc:
        return truedoc.__file__, "FAILED: " + repr(exc)[:90]
    with open(target, "w", encoding="utf-8") as fh:
        fh.write(md)
    return truedoc.__file__, "ok"


def compare(before, after):
    import kfs_grade
    named, hidden, same, missing = [], 0, 0, 0
    for _insurer, pdf in kfs_grade.sheets():
        name = os.path.basename(kfs_grade.cache_path(pdf))
        a, b = os.path.join(before, name), os.path.join(after, name)
        if not (os.path.exists(a) and os.path.exists(b)):
            missing += 1
        elif open(a, encoding="utf-8").read() == open(b, encoding="utf-8").read():
            same += 1
        elif kfs_grade.held_out(pdf):
            hidden += 1
        else:
            named.append(name)
    print("sheets the same: %d | differ: %d tuned-on, %d held out (counted, never named) | not in both folders: %d" % (same, len(named), hidden, missing))
    for n in named:
        print("   ", n)


if __name__ == "__main__":
    if ROOT == "--compare":
        compare(ARGS[1], ARGS[2])
        sys.exit(0)
    import doc_library
    import kfs_grade
    todo = [p for _ins, p in kfs_grade.sheets()]
    if "--only" in ARGS:
        wanted = {l.strip().split("@")[0] for l in open(ARGS[ARGS.index("--only") + 1], encoding="utf-8") if l.strip()}
        todo = [p for p in todo if doc_library.relative(p) in wanted]
    workers = next((int(a) for a in ARGS[2:3] if a.isdigit()), 6)
    os.makedirs(OUT, exist_ok=True)
    print(len(todo), "sheets, code at", os.path.abspath(ROOT), flush=True)
    seen, failed = set(), 0
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
        for where, note in pool.map(one, todo, chunksize=2):
            seen.add(where)
            failed += note != "ok"
    print("imported truedoc from:", sorted(seen), "| failures:", failed)
