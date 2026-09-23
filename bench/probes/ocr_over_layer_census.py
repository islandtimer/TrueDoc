"""When TrueDoc's OCR replaces a text layer the check rejected, does it drop words the layer held? (24 September 2026)

A page whose text layer the check turns down (`textlayer._assess_quality`: kind `none` or `suspect`) goes to OCR, and a
reading OCR keeps replaces the layer whole (`ocr.rapid.apply_ocr`). Where the layer held words - a cover's title over a
full-page picture, a page number, a line in another script - a word the layer wrote and OCR did not see would be lost.
This counts, for every rejected page of a screen made by `box_list_blank_census.py screen` whose layer holds at least
one letter or figure:

- what OCR made of it, run as the pipeline runs it (`pipeline.process_page`, the turn included): nothing, a reading it
  rejected, a reading it kept, or a failure;
- where OCR kept its reading, the layer's words it does not hold - a word counts as held if OCR wrote it, or wrote it
  run together with its neighbours (its letters inside OCR's letters) - and the reverse, OCR's words the layer lacks.

Held-out pages (the benchmark's held-back fifth, the library's odd-hash half, the Key Facts oracle's fifth) are counted,
never named, and none of their text is kept. The sealed documents are not in any screen.

usage (repo root, the project's venv):
    ocr_over_layer_census.py run library|bench-all <screen.jsonl> <out.jsonl> [workers]
    ocr_over_layer_census.py report <out.jsonl> [<out.jsonl> ...]
"""
import collections
import concurrent.futures
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "bench", "probes"))
sys.path.insert(0, os.path.join(REPO, "bench", "tools"))

_WORD = re.compile(r"[^\W_]+")


def _tokens(words) -> list[str]:
    return [t.lower() for w in words for t in _WORD.findall(w)]


def read_one(job):
    key, path, number, secret, insurer = job
    sys.path.insert(0, REPO)
    import pymupdf

    from truedoc.extract.textlayer import extract_page
    from truedoc.ocr.rapid import apply_ocr
    from truedoc.pipeline import _turn_page

    row = {"doc": key, "page": number, "held_out": secret, "insurer": insurer}
    try:
        with pymupdf.open(path) as pdf:
            pdf_page = pdf[number - 1]
            page = extract_page(pdf_page, number)
            layer = _tokens(w.text for w in page.words)
            row.update(kind=page.quality.kind, image_share=round(page.quality.image_coverage, 2),
                       layer_alnum=sum(len(t) for t in layer))
            try:
                kept = apply_ocr(page, pdf_page)
                turn = page.meta.pop("ocr_turn", 0)
                if turn:
                    page = _turn_page(pdf_page, number, turn)
                    kept = apply_ocr(page, pdf_page, allow_turn=False)
            except Exception as exc:
                row.update(ocr="failed", error=repr(exc)[:160])
                return row
    except Exception as exc:
        row.update(ocr="error", error=repr(exc)[:160])
        return row
    if not kept:
        row["ocr"] = "empty" if page.meta.get("ocr_empty") else "rejected"
        return row
    ocr = _tokens(w.text for w in page.words)
    joined = "".join(ocr)
    seen = set(ocr)
    missing = [t for t in layer if t not in seen and t not in joined]
    layer_set = set(layer)
    added = [t for t in ocr if t not in layer_set]
    row.update(ocr="kept", ocr_alnum=sum(len(t) for t in ocr), missing_alnum=sum(len(t) for t in missing),
               missing_words=len(missing), added_alnum=sum(len(t) for t in added))
    if not secret:
        row["missing"] = missing[:30]
        row["layer_text"] = " ".join(layer)[:200]
        row["ocr_text"] = " ".join(ocr)[:200]
    return row


def jobs(which: str, screen: str):
    from box_list_blank_census import jobs as census_jobs

    wanted = {}
    for line in open(screen, encoding="utf-8"):
        r = json.loads(line)
        q = r.get("quality") or {}
        if q and not q["usable"] and q["alnum"] > 0:
            wanted.setdefault(r["doc"], set()).add(r["page"])
    for key, path, pages, secret, insurer, _k in census_jobs(which):
        for n in sorted(wanted.get(key, ())):
            if pages is None or n in pages:
                yield (key, path, n, secret, insurer)


def run(which: str, screen: str, out: str, workers: int) -> None:
    todo = list(jobs(which, screen))
    print("pages to read:", len(todo), "held out:", sum(1 for j in todo if j[3]), flush=True)
    with open(out, "w", encoding="utf-8") as f, concurrent.futures.ProcessPoolExecutor(workers) as pool:
        for i, row in enumerate(pool.map(read_one, todo, chunksize=1), 1):
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            f.flush()
            if i % 20 == 0:
                print(i, "of", len(todo), flush=True)


def report(paths: list[str]) -> None:
    for path in paths:
        rows = [json.loads(l) for l in open(path, encoding="utf-8")]
        print("==", os.path.basename(path), "- pages", len(rows), "(held out %d)" % sum(r["held_out"] for r in rows))
        by = collections.Counter((r["ocr"], r.get("kind")) for r in rows)
        for (ocr, kind), n in sorted(by.items(), key=str):
            print("   OCR %-8s over a layer judged %-8s pages %4d" % (ocr, kind, n))
        kept = [r for r in rows if r["ocr"] == "kept"]
        for floor, label in ((1, "any word"), (20, "20+ letters and figures")):
            hit = [r for r in kept if r["missing_alnum"] >= floor]
            docs = {r["doc"] for r in hit}
            print("   kept, and the layer held words OCR did not (%s): pages %d (held out %d) | documents %d "
                  "(held out %d) | insurers %d" % (label, len(hit), sum(r["held_out"] for r in hit), len(docs),
                                                   len({r["doc"] for r in hit if r["held_out"]}),
                                                   len({r["insurer"] for r in hit})))
        print("   letters and figures: layer %d, lost %d; OCR added %d" % (
            sum(r["layer_alnum"] for r in kept), sum(r["missing_alnum"] for r in kept), sum(r["added_alnum"] for r in kept)))
        for r in rows:
            if r["ocr"] in ("failed", "error"):
                print("   %s: %s" % (r["ocr"], r["error"] if not r["held_out"] else "(held out)"))
        for r in sorted(kept, key=lambda r: -r["missing_alnum"]):
            if r["missing_alnum"] and not r["held_out"]:
                print("   - %s p%d lost %d: %s" % (r["doc"], r["page"], r["missing_alnum"], " ".join(r["missing"])[:140]))


if __name__ == "__main__":
    if sys.argv[1] == "run":
        run(sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5]) if len(sys.argv) > 5 else 6)
    else:
        report(sys.argv[2:])
