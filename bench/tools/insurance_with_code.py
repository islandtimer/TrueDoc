"""Convert every page of the insurance set with the `truedoc` found at <code root>, into <out folder>.

For measuring a change code against code: run it once with a git worktree of the commit before the change and once
with the repository root, into two folders, and compare the folders file by file. The cached
`bench/out/insurance_set/converted` is not a before state - a copy there can predate an earlier commit (19 September
2026: one page "changed" under a rule that could not touch it).

Each worker puts <code root> first on its path and reports which `truedoc` it imported; this file sits in
`bench/tools`, which holds no `truedoc` folder, so nothing shadows it.

usage (repo root, the project's venv): insurance_with_code.py <code root> <out folder> [workers]
"""
import concurrent.futures
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT, OUT = (sys.argv + ["", ""])[1:3]


def one(entry):
    sys.path.insert(0, ROOT)
    import truedoc
    from truedoc.pipeline import ConvertOptions, convert
    md = convert(entry["pdf"], ConvertOptions(frontmatter=False, pages=[entry["page"]]))
    with open(os.path.join(OUT, entry["name"] + ".md"), "w", encoding="utf-8") as fh:
        fh.write(md)
    return os.path.dirname(truedoc.__file__)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    pages = json.load(open(os.path.join(REPO, "bench", "out", "insurance_set", "manifest.json"), encoding="utf-8"))["pages"]
    with concurrent.futures.ProcessPoolExecutor(max_workers=int(sys.argv[3]) if len(sys.argv) > 3 else 6) as pool:
        where = set(pool.map(one, pages))
    print(len(pages), "pages converted with", where)
