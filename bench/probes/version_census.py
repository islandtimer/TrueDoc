"""How much of a document carries over from its nearest other issue: the library, matched page by page (D040).

For each document, the other documents of its folder (insurer / product line) are ranked by the word pairs they share
with it; the two nearest are matched page by page (`truedoc.versions`) and the one sharing the most pages is its nearest
issue. Counted over the documents that have one - half their pages or more matched: pages `same` (reprinted word for
word), `restamped` (only the date, form code or page number changed - what a person confirmed carries over), `changed`
(checked afresh; how many with a figure changed), and `new`. A document's nearest issue may be an earlier or later issue,
or the same wording sold under another brand; either way its pages are what a confirmation could be carried to.

Held-out documents (the meaning test's odd hash, the Key Facts oracle's fifth) are counted, never named; the sealed 19
are never opened.

usage (repo root, the project's venv):
    version_census.py <out.json> [workers]
"""
import collections
import concurrent.futures
import hashlib
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "bench", "tools"))
NEAREST = 2           # candidates matched in full per document
CARRIES = 0.5         # share of a document's pages matched for it to have an issue in the library


def folder_rows(job):
    folder, docs = job                                   # docs: [(path, secret)]
    from truedoc.versions import match, page_prints
    prints, errors = {}, 0
    for path, secret in docs:
        try:
            prints[path] = page_prints(path)
        except Exception:
            errors += 1
    pairs = {p: set().union(*(pp.bigrams() for pp in pr)) if pr else set() for p, pr in prints.items()}
    rows = []
    for path, secret in docs:
        if path not in prints or not prints[path]:
            continue
        mine = pairs[path]
        ranked = sorted((len(mine & pairs[o]) / max(1, len(mine | pairs[o])), o) for o in prints if o != path and pairs[o])
        best = None
        for score, other in ranked[::-1][:NEAREST]:
            result = match(prints[other], prints[path])
            kinds = collections.Counter(m.kind for m in result if m.new is not None)
            matched = kinds["same"] + kinds["restamped"] + kinds["changed"]
            figures = sum(1 for m in result if m.kind == "changed" and m.figures)
            if best is None or matched > best[0]:
                best = (matched, other, kinds, figures)
        row = {"doc": path, "secret": secret, "pages": len(prints[path])}
        if best:
            matched, other, kinds, figures = best
            row.update(other=other, other_secret=dict(docs).get(other, False), matched=matched,
                       kinds=dict(kinds), changed_with_figures=figures)
        rows.append(row)
    return folder, rows, errors


if __name__ == "__main__":
    import doc_library
    from word_check import held_out
    out = sys.argv[1]
    workers = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    root = doc_library.root()
    sealed = {l.strip().replace("\\", "/") for l in open(os.path.join(REPO, "bench", "insurance_holdout.txt"), encoding="utf-8")
              if l.strip() and not l.startswith("#")}
    names = {os.path.basename(s) for s in sealed}
    folders = collections.defaultdict(list)
    for d, _, fs in os.walk(root):
        for f in fs:
            p = os.path.join(d, f).replace("\\", "/")
            if f.lower().endswith(".pdf") and doc_library.relative(p) not in sealed and f not in names:
                folders[os.path.dirname(p)].append((p, bool(held_out(p))))
    jobs = sorted(folders.items(), key=lambda kv: -len(kv[1]))
    print(len(jobs), "folders,", sum(len(v) for v in folders.values()), "documents", flush=True)
    rows, errors = [], 0
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
        for folder, r, e in pool.map(folder_rows, jobs):
            rows.extend(r)
            errors += e
    hide = lambda p: "held-out:" + hashlib.sha1(p.encode()).hexdigest()[:10]
    for r in rows:
        r["doc"] = hide(r["doc"]) if r["secret"] else doc_library.relative(r["doc"])
        if "other" in r:
            r["other"] = hide(r["other"]) if r["other_secret"] else doc_library.relative(r["other"])
    json.dump({"errors": errors, "rows": rows}, open(out, "w", encoding="utf-8"), indent=1)
    print("documents unreadable:", errors)
    for half, name in ((False, "tuned-on"), (True, "held out")):
        mine = [r for r in rows if r["secret"] == half]
        issued = [r for r in mine if r.get("matched", 0) >= CARRIES * r["pages"]]
        kinds = collections.Counter()
        for r in issued:
            kinds.update(r["kinds"])
        pages = sum(r["pages"] for r in issued)
        print("%-9s documents %4d | with an issue in the library %4d (%d pages): same %d, restamped %d, changed %d "
              "(%d with a figure changed), new %d" % (name, len(mine), len(issued), pages, kinds["same"], kinds["restamped"],
              kinds["changed"], sum(r["changed_with_figures"] for r in issued), kinds["new"]))
    shown = sorted((r for r in rows if not r["secret"] and r.get("matched", 0) >= CARRIES * r["pages"] and not r["other_secret"]),
                   key=lambda r: -r["pages"])[:12]
    for r in shown:
        print("   %-62s %3d pages <- %-50s %s" % (r["doc"][-62:], r["pages"], r["other"][-50:], r["kinds"]))
