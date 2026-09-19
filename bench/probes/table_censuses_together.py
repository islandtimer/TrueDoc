"""Run the table censuses that hook different functions in one pass over a population.

A pass over the benchmark's digital pages costs about 35 minutes and one over the Key Facts Sheets
about 12, whatever is counted on the way; `header_long_cell_census` hooks `_header_row_count` and
`split_row_census` hooks `_merge_wrapped_rows`, so both can ride the same conversions.

usage (repo root): table_censuses_together.py <out folder> kfs|insurance|bench [workers]
writes <out folder>/header_<which>.jsonl and <out folder>/split_<which>.jsonl; read each with its
own probe's summary (the probes print one when given the file they wrote).
"""
import concurrent.futures
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "bench", "probes"))


def census(job):
    import header_long_cell_census as header
    import split_row_census as split
    label, path, number, secret = job
    header._install()
    split._install()
    del header.FOUND[:]
    del split.FOUND[:]
    from truedoc.pipeline import ConvertOptions, load_document
    try:
        load_document(path, ConvertOptions(frontmatter=False, pages=[number]))
    except Exception as exc:
        return [{"page": label, "error": repr(exc)[:100]}], []
    hide_h = {"rows": "(held out)"} if secret else {}
    hide_s = {"cut": "(held out)", "others": "(held out)"} if secret else {}
    return ([dict(r, page=label, held_out=secret, **hide_h) for r in header.FOUND],
            [dict(r, page=label, held_out=secret, **hide_s) for r in split.FOUND])


if __name__ == "__main__":
    from orphan_row_census import jobs
    folder, which = sys.argv[1], sys.argv[2]
    os.makedirs(folder, exist_ok=True)
    todo = list(jobs(which))
    print(len(todo), "pages", flush=True)
    with open(os.path.join(folder, "header_%s.jsonl" % which), "w", encoding="utf-8") as fh, \
            open(os.path.join(folder, "split_%s.jsonl" % which), "w", encoding="utf-8") as fs, \
            concurrent.futures.ProcessPoolExecutor(max_workers=int(sys.argv[3]) if len(sys.argv) > 3 else 6) as pool:
        for n, (hs, ss) in enumerate(pool.map(census, todo, chunksize=2), 1):
            for r in hs:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            for r in ss:
                fs.write(json.dumps(r, ensure_ascii=False) + "\n")
            if n % 200 == 0:
                print(" ", n, flush=True)
    print("done", flush=True)
