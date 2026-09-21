"""The text layer's lines of every page of a population, under the `truedoc` at <code root>: the stage signature.

For a change to how the text layer is read (words, spaces, lines), run this once with a worktree of the commit before
and once with the working tree, then `--compare` the two: the pages whose lines differ are the only pages the change
can reach, and for each the lines that changed. Text layer only - no layout model, tables or maths - so it is fast.
Held-out pages (the benchmark's `holdout.txt`, the Key Facts oracle's fifth) are recorded as a hash of their lines and
counted, never shown.

usage (repo root, the project's venv):
    line_signature.py <code root> <out.jsonl> kfs|insurance|bench [workers]
    line_signature.py --compare <before.jsonl> <after.jsonl> [--show 40]
"""
import concurrent.futures
import hashlib
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "bench", "probes"))
sys.path.insert(0, os.path.join(REPO, "bench", "tools"))
ROOT = sys.argv[1]


def lines_of(job):
    label, path, number, secret = job
    sys.path.insert(0, ROOT)
    import truedoc
    from truedoc.pipeline import ConvertOptions, load_document
    try:
        doc = load_document(path, ConvertOptions(frontmatter=False, pages=[number], layout=False, tables=False, math=False))
        lines = [l.text for p in doc.pages for l in p.lines]
    except Exception as exc:
        return {"page": label, "error": repr(exc)[:100], "held_out": secret}
    if secret:
        return {"page": label, "held_out": True, "hash": hashlib.sha1("\n".join(lines).encode("utf-8")).hexdigest(),
                "n": len(lines), "code": os.path.dirname(truedoc.__file__)}
    return {"page": label, "held_out": False, "lines": lines, "code": os.path.dirname(truedoc.__file__)}


def compare(before, after, show):
    a = {r["page"]: r for r in (json.loads(l) for l in open(before, encoding="utf-8"))}
    b = {r["page"]: r for r in (json.loads(l) for l in open(after, encoding="utf-8"))}
    print("code: before %s | after %s" % ({r.get("code") for r in a.values()} - {None}, {r.get("code") for r in b.values()} - {None}))
    changed, hidden, failed = [], 0, 0
    for page in sorted(set(a) & set(b)):
        x, y = a[page], b[page]
        if "error" in x or "error" in y:
            failed += 1                  # a run that failed on every page must not read as "nothing changed"
            continue
        if x["held_out"]:
            hidden += x["hash"] != y["hash"]
        elif x["lines"] != y["lines"]:
            changed.append(page)
    print("pages compared %d (%d failed to read in either state, not compared) | lines differ on %d tuned-on pages, %d held-out "
          "(counted, never shown)" % (len(set(a) & set(b)) - failed, failed, len(changed), hidden))
    shown = 0
    for page in changed:
        old, new = a[page]["lines"], b[page]["lines"]
        gone = [l for l in old if l not in new]
        came = [l for l in new if l not in old]
        for g, c in zip(gone, came):
            if shown < show:
                print("  %-44s  - %r\n  %-44s  + %r" % (page[-44:], g[:90], "", c[:90]))
                shown += 1
        if len(gone) != len(came) and shown < show:
            print("  %-44s  (%d lines before, %d after)" % (page[-44:], len(old), len(new)))


if __name__ == "__main__":
    if sys.argv[1] == "--compare":
        compare(sys.argv[2], sys.argv[3], int(sys.argv[sys.argv.index("--show") + 1]) if "--show" in sys.argv else 40)
        sys.exit(0)
    from orphan_row_census import jobs
    out, which = sys.argv[2], sys.argv[3]
    # Each population's own hold-out: the benchmark's holdout.txt, the Key Facts oracle's fifth; the insurance set has
    # none. (The meaning test's odd-hash half is of the wider library, which neither of the others draws from.)
    todo = list(jobs(which))
    print(len(todo), "pages", flush=True)
    with open(out, "w", encoding="utf-8") as f, concurrent.futures.ProcessPoolExecutor(max_workers=int(sys.argv[4]) if len(sys.argv) > 4 else 8) as pool:
        for r in pool.map(lines_of, todo, chunksize=4):
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("done", flush=True)
