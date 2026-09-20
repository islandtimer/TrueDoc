"""Every word `extract/textlayer._read_drawn_underscores` makes, on every page of a population.

The reader is the only thing that changed and it changes a page only by joining two words round a drawn
underscore, so the words it makes name exactly the pages that can differ. Text layer only: fast.

usage (repo root): drawn_underscore_screen.py <out.jsonl> kfs|insurance|bench [workers]
"""
import concurrent.futures
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "bench", "probes"))
FOUND = []


def _install():
    from truedoc.extract import textlayer
    if getattr(textlayer, "_underscore_screen", False):
        return
    textlayer._underscore_screen = True
    read0 = textlayer._read_drawn_underscores

    def read(pdf_page, page, M=None):
        before = {id(w) for l in page.lines for w in l.words}
        read0(pdf_page, page, M)
        FOUND.extend(w.text for l in page.lines for w in l.words if id(w) not in before)

    textlayer._read_drawn_underscores = read


def screen(job):
    label, path, number, secret = job
    _install()
    del FOUND[:]
    from truedoc.pipeline import ConvertOptions, load_document
    try:
        load_document(path, ConvertOptions(frontmatter=False, pages=[number], layout=False, tables=False, math=False))
    except Exception as exc:
        return [{"page": label, "error": repr(exc)[:100]}]
    return [{"page": label, "held_out": secret, "word": "(held out)" if secret else w} for w in FOUND]


if __name__ == "__main__":
    from orphan_row_census import jobs
    out, which = sys.argv[1], sys.argv[2]
    todo = list(jobs(which))
    print(len(todo), "pages", flush=True)
    with open(out, "w", encoding="utf-8") as f, concurrent.futures.ProcessPoolExecutor(max_workers=int(sys.argv[3]) if len(sys.argv) > 3 else 6) as pool:
        for rows in pool.map(screen, todo, chunksize=4):
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    rows = [json.loads(l) for l in open(out, encoding="utf-8")]
    errors = [r for r in rows if "error" in r]
    rows = [r for r in rows if "word" in r]
    print("words joined round a drawn underscore: %d on %d pages (held-out pages, counted only: %d); conversion errors: %d"
          % (len(rows), len({r["page"] for r in rows}), len({r["page"] for r in rows if r["held_out"]}), len(errors)))
    for page in sorted({r["page"] for r in rows if not r["held_out"]}):
        print("   %-46s %s" % (page[-46:], ", ".join(r["word"] for r in rows if r["page"] == page)[:150]))
