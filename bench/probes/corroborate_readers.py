"""Does one reader invent more than another? D021's check, run over several readers' saved pages.

D033 made Infinity-Parser2-Flash the standard reader subject to this. Every page without a digital
text layer is read by a model, and `truedoc.vision.corroborate` compares the model's words with
what the page can say for itself - a hidden OCR layer, or our own engine's rejected lines. The
witness is the page's and does not change with the reader, so two readers' support on the same
page is a like-for-like comparison: the reader whose words the page backs less is the one
putting words there that the page does not hold.

A third of these pages have no usable witness (bare handwriting our OCR cannot read), which is
exactly where invention would hide. For those a second measure needs no witness at all: the share
of a reader's words that neither other reader produced anywhere on the page. It cannot tell an
invention from a word only one reader got right, so it is read as a population, not page by page.

usage (repo root, the project's venv - the layout model and the OCR engine must load):
    corroborate_readers.py scan <out.jsonl> <name>=<candidate folder> ...     convert and record
    corroborate_readers.py read <out.jsonl>                                    the comparison
"""
import collections
import concurrent.futures
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BENCH = os.path.join(REPO, "bench", "data", "olmocr-bench", "bench_data")
_WORD = re.compile(r"[^\W_]{3,}", re.UNICODE)


def one(job):
    page, name, folder = job
    from truedoc.pipeline import ConvertOptions, load_document
    pdf = os.path.join(BENCH, "pdfs", page.replace("/", os.sep) + ".pdf")
    try:
        doc = load_document(pdf, ConvertOptions(frontmatter=False, pages=[1], vision_endpoint="file:" + folder, vision_regions=False))
        verdicts = doc.metadata.get("corroboration") or []
        v = dict(verdicts[0]) if verdicts else {"state": "not read by the model"}
        v["warnings"] = [w for w in doc.warnings if "could not run" in w]
    except Exception as exc:  # a page that will not convert is a fact about the page, not the reader
        v = {"state": "FAILED", "reason": repr(exc)[:160]}
    return dict(v, page=page, reader=name)


def scan(out_path, readers):
    pages = [l.split("\t")[0].strip() for l in open(os.path.join(REPO, "bench", "gpu", "pages.txt"), encoding="utf-8") if l.strip()]
    jobs = [(p, name, folder) for p in pages for name, folder in readers]
    done = 0
    with open(out_path, "w", encoding="utf-8") as out, concurrent.futures.ProcessPoolExecutor(max_workers=10) as pool:
        for rec in pool.map(one, jobs, chunksize=2):
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")
            out.flush()
            done += 1
            if done % 100 == 0:
                print("%d of %d" % (done, len(jobs)), flush=True)
    print("done: %d records -> %s" % (done, out_path))


def words_of(folder, page):
    cat, stem = page.split("/", 1)
    path = os.path.join(folder, cat, stem + "_pg1_repeat1.md")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [w.lower() for w in _WORD.findall(re.sub(r"<[^>]+>", " ", f.read()))]


def read(out_path, folders):
    by_page = collections.defaultdict(dict)
    with open(out_path, encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            by_page[rec["page"]][rec["reader"]] = rec
    readers = sorted({r for v in by_page.values() for r in v})
    print("pages: %d | readers: %s\n" % (len(by_page), ", ".join(readers)))
    print("VERDICTS (D021)")
    for r in readers:
        c = collections.Counter(v[r]["state"] for v in by_page.values() if r in v)
        print("  %-10s %s" % (r, dict(c)))
    comparable = [p for p, v in by_page.items() if all(r in v and "support" in v[r] for r in readers)]
    print("\nSUPPORT, on the %d pages where every reader has a comparable witness" % len(comparable))
    for r in readers:
        s = sorted(by_page[p][r]["support"] for p in comparable)
        print("  %-10s mean %.3f | median %.3f | lowest tenth %.3f | under 0.55: %d" % (
            r, sum(s) / len(s), s[len(s) // 2], s[len(s) // 10], sum(1 for x in s if x < 0.55)))
    base = readers[0] if "olmocr2" not in readers else "olmocr2"
    for r in readers:
        if r == base:
            continue
        worse = sorted((by_page[p][r]["support"] - by_page[p][base]["support"], p) for p in comparable)
        print("\n  %s against %s, page by page: lower by 0.10 or more on %d, higher by 0.10 or more on %d" % (
            r, base, sum(1 for d, _ in worse if d <= -0.10), sum(1 for d, _ in worse if d >= 0.10)))
        for d, p in worse[:8]:
            if d <= -0.10:
                print("     %+.2f  %s   (%s %.2f, %s %.2f; %d words)" % (d, p, r, by_page[p][r]["support"], base,
                      by_page[p][base]["support"], by_page[p][r].get("model_words", 0)))
    if folders:
        print("\nWORDS NO OTHER READER HAS, all %d pages (needs no witness)" % len(by_page))
        for r in readers:
            alone = total = 0
            heavy = []
            for p in by_page:
                mine = words_of(folders[r], p)
                others = set()
                for o in readers:
                    if o != r:
                        others.update(words_of(folders[o], p))
                n = sum(1 for w in mine if w not in others)
                alone += n
                total += len(mine)
                if len(mine) >= 40:
                    heavy.append((n / len(mine), p))
            heavy.sort(reverse=True)
            print("  %-10s %6d of %7d words (%.1f%%) | pages over a third alone: %d" % (
                r, alone, total, 100.0 * alone / max(total, 1), sum(1 for s, _ in heavy if s > 1 / 3)))


if __name__ == "__main__":
    mode, out_path = sys.argv[1], sys.argv[2]
    pairs = [a.split("=", 1) for a in sys.argv[3:]]
    folders = {n: (f if os.path.isabs(f) else os.path.join(BENCH, f)) for n, f in pairs}
    if mode == "scan":
        scan(out_path, sorted(folders.items()))
    else:
        read(out_path, folders)
