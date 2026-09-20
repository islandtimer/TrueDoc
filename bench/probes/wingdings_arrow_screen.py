"""Every Wingdings arrow `extract/textlayer._symbol_font_mark` now names, on every page of a population.

The table only gained codes, so the characters it turns into arrows name exactly the pages that can differ. Text
layer only: fast. Each record carries the word the arrow stands in, to be read.

usage (repo root): wingdings_arrow_screen.py <out.jsonl> kfs|insurance|bench [workers]
"""
import concurrent.futures
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "bench", "probes"))


def screen(job):
    label, path, number, secret = job
    from truedoc.extract import textlayer
    from truedoc.pipeline import ConvertOptions, load_document
    arrows = set(textlayer._WINGDINGS_ARROWS.values())
    try:
        doc = load_document(path, ConvertOptions(frontmatter=False, pages=[number], layout=False, tables=False, math=False))
    except Exception as exc:
        return [{"page": label, "error": repr(exc)[:100]}]
    out = []
    for page in doc.pages:
        for line in page.lines:
            for w in line.words:
                for c in w.chars:
                    if c.text in arrows and textlayer._WINGDINGS_PROPER.search(c.font.lower()):
                        out.append({"page": label, "held_out": secret, "arrow": c.text, "font": c.font,
                                    "word": "(held out)" if secret else w.text[:40], "line": "(held out)" if secret else line.text[:70]})
    return out


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
    rows = [r for r in rows if "arrow" in r]
    print("Wingdings arrows named: %d on %d pages (held-out pages, counted only: %d); conversion errors: %d"
          % (len(rows), len({r["page"] for r in rows}), len({r["page"] for r in rows if r["held_out"]}), len(errors)))
    for page in sorted({r["page"] for r in rows if not r["held_out"]}):
        mine = [r for r in rows if r["page"] == page]
        print("   %-46s %d: %s" % (page[-46:], len(mine), " | ".join(sorted({r["line"] for r in mine}))[:150]))
