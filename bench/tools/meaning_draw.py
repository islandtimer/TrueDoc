"""Draw the pages of a meaning test (D039) from the owner's library, and lay out what each reader of the test may see.

D039: how well TrueDoc converts the owner's documents is measured by whether a reader gets the right answer to a
question about their cover. Questions are written from the PICTURE of a page by someone who never sees TrueDoc's
output; they are then answered from the picture, from TrueDoc's text of the page, and from a plain text dump of it.

This tool does the part that needs no model.

  * Pages are drawn, not chosen: a seeded shuffle of the eligible documents, one page of each at random. Never a
    document of the sealed slice (D030, `bench/insurance_holdout.txt`), a Key Facts Sheet (D027's oracle) or a document
    of the insurance set. At most `--per-insurer` documents of one insurer in each half.
  * Half are held out, by a hash of the file name: of those, whoever writes TrueDoc's rules sees scores and nothing
    else. This tool prints counts only, for both halves.
  * Only pages with a digital text layer: a scanned page goes to a model reader in the product (D019, D033), which
    is not running here, and converting it without one would measure something nobody ships. Dropped pages are counted.
  * Each candidate is converted, and its kind read off the conversion (marks / table / list / prose) only so that the
    draw can be spread over kinds; candidates are then taken kind by kind in the order of the shuffle.
  * For each page three things are laid out under names that say nothing and share nothing, so that a reader handed
    one cannot find the others: the picture (whole page, and its top and bottom halves larger), TrueDoc's text, and a
    plain text dump of the PDF page.

Writes <out>/manifest_private.json (what is where - the only file that joins them) and <out>/workflow_args.json
(page ids, halves and file paths; no words of any page).

usage (repo root, the project's venv): meaning_draw.py <out folder> [--seed 39] [--candidates 40] [--take 24] [--per-insurer 2] [--workers 10]
"""
import concurrent.futures
import hashlib
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
KINDS = ("table", "list", "marks", "prose")


def option(name, default):
    return type(default)(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default


def held_out(path: str) -> bool:
    return int(hashlib.sha1(os.path.basename(path).encode("utf-8")).hexdigest()[:8], 16) % 2 == 1


def text_layer_chars(path: str, number: int) -> int:
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(path)
    try:
        return len((doc[number - 1].get_textpage().get_text_range() or "").split())
    finally:
        doc.close()


def convert_one(job):
    path, number = job
    sys.path.insert(0, REPO)
    from truedoc.pipeline import ConvertOptions, convert
    try:
        return convert(path, ConvertOptions(frontmatter=False, pages=[number]))
    except Exception as exc:
        return "FAILED: " + repr(exc)[:120]


def kind_of(md: str) -> str:
    lines = md.splitlines()
    if any(ch in md for ch in "✓✔✗✘☑☒"):
        return "marks"
    if "<table" in md or any(l.startswith("| ---") for l in lines):
        return "table"
    if sum(1 for l in lines if l.lstrip().startswith(("- ", "* ")) or (l[:3].strip(". ").isdigit() and ". " in l[:5])) >= 3:
        return "list"
    return "prose"


def name_for(seed, rel, number, role) -> str:
    return hashlib.sha1(("%s|%s|%s|%s" % (seed, rel, number, role)).encode("utf-8")).hexdigest()[:14]


if __name__ == "__main__":
    import doc_library
    import kfs_grade
    import pypdfium2 as pdfium

    out = sys.argv[1]
    seed, want, take = option("--seed", 39), option("--candidates", 40), option("--take", 24)
    per_insurer, workers = option("--per-insurer", 2), option("--workers", 10)
    root = doc_library.root()
    library = sorted(os.path.join(d, f).replace("\\", "/") for d, _, fs in os.walk(root) for f in fs if f.lower().endswith(".pdf"))
    sealed = {l.strip().replace("\\", "/") for l in open(os.path.join(REPO, "bench", "insurance_holdout.txt"), encoding="utf-8")
              if l.strip() and not l.startswith("#")}
    sealed_names = {os.path.basename(s) for s in sealed}
    sheets = {p.replace("\\", "/") for _ins, p in kfs_grade.sheets()}
    manifest = json.load(open(os.path.join(REPO, "bench", "out", "insurance_set", "manifest.json"), encoding="utf-8"))
    in_set = {doc_library.absolute(p["pdf"]).replace("\\", "/") for p in manifest["pages"]} | {p["pdf"].replace("\\", "/") for p in manifest["pages"]}
    eligible = [p for p in library if doc_library.relative(p) not in sealed and os.path.basename(p) not in sealed_names
                and p not in sheets and p not in in_set]
    print("library %d PDFs | sealed %d, Key Facts Sheets %d, insurance-set documents %d left out | eligible %d"
          % (len(library), len(library) - len([p for p in library if doc_library.relative(p) not in sealed and os.path.basename(p) not in sealed_names]),
             len([p for p in library if p in sheets]), len([p for p in library if p in in_set]), len(eligible)), flush=True)

    rng = random.Random(seed)
    order = list(eligible)
    rng.shuffle(order)
    picked = {False: [], True: []}
    per = {False: {}, True: {}}
    dropped = {"no text layer": 0, "unreadable": 0, "insurer already has its share": 0}
    for path in order:
        half = held_out(path)
        if len(picked[half]) >= want:
            if all(len(v) >= want for v in picked.values()):
                break
            continue
        insurer = doc_library.relative(path).split("/")[0]
        if per[half].get(insurer, 0) >= per_insurer:
            dropped["insurer already has its share"] += 1
            continue
        try:
            doc = pdfium.PdfDocument(path)
            pages = len(doc)
            doc.close()
            number = rng.randint(1, pages)
            if text_layer_chars(path, number) < 40:
                dropped["no text layer"] += 1
                continue
        except Exception:
            dropped["unreadable"] += 1
            continue
        per[half][insurer] = per[half].get(insurer, 0) + 1
        picked[half].append((path, number, insurer))
    print("candidates: tuned-on %d, held out %d | dropped on the way: %s" % (len(picked[False]), len(picked[True]), dropped), flush=True)

    jobs = [(p, n) for half in (False, True) for p, n, _ in picked[half]]
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
        converted = dict(zip(jobs, pool.map(convert_one, jobs, chunksize=1)))
    failed = sum(1 for md in converted.values() if md.startswith("FAILED"))

    for sub in ("pic", "td", "plain"):
        os.makedirs(os.path.join(out, sub), exist_ok=True)
    import pymupdf
    entries, counts = [], {}
    for half in (False, True):
        by_kind = {k: [] for k in KINDS}
        for path, number, insurer in picked[half]:
            md = converted[(path, number)]
            if not md.startswith("FAILED"):
                by_kind[kind_of(md)].append((path, number, insurer))
        chosen = []
        while len(chosen) < take and any(by_kind.values()):
            for k in KINDS:                       # kind by kind, each in the order of the shuffle
                if by_kind[k] and len(chosen) < take:
                    chosen.append((k,) + by_kind[k].pop(0))
        counts[half] = {k: sum(1 for c in chosen if c[0] == k) for k in KINDS}
        for kind, path, number, insurer in chosen:
            rel = doc_library.relative(path)
            pid = "%s%02d" % ("h" if half else "t", sum(1 for e in entries if e["held_out"] == half) + 1)
            names = {role: name_for(seed, rel, number, role) for role in ("pic", "td", "plain")}
            page = pdfium.PdfDocument(path)[number - 1]
            whole = page.render(scale=130 / 72).to_pil().convert("RGB")
            large = page.render(scale=220 / 72).to_pil().convert("RGB")
            w, h = large.size
            files = {"pic_full": os.path.join(out, "pic", names["pic"] + "_whole.png"),
                     "pic_top": os.path.join(out, "pic", names["pic"] + "_top.png"),
                     "pic_bottom": os.path.join(out, "pic", names["pic"] + "_bottom.png"),
                     "td": os.path.join(out, "td", names["td"] + ".md"),
                     "plain": os.path.join(out, "plain", names["plain"] + ".txt")}
            whole.save(files["pic_full"])
            large.crop((0, 0, w, int(0.56 * h))).save(files["pic_top"])
            large.crop((0, int(0.44 * h), w, h)).save(files["pic_bottom"])
            with open(files["td"], "w", encoding="utf-8") as f:
                f.write(converted[(path, number)])
            with open(files["plain"], "w", encoding="utf-8") as f:
                f.write(pymupdf.open(path)[number - 1].get_text())
            entries.append(dict({"pid": pid, "held_out": half, "kind": kind, "insurer": insurer, "document": rel, "page": number},
                                **{k: os.path.abspath(v).replace("\\", "/") for k, v in files.items()}))
    with open(os.path.join(out, "manifest_private.json"), "w", encoding="utf-8") as f:
        json.dump({"seed": seed, "pages": entries}, f, indent=1, ensure_ascii=False)
    with open(os.path.join(out, "workflow_args.json"), "w", encoding="utf-8") as f:
        json.dump([{k: e[k] for k in ("pid", "held_out", "kind", "pic_full", "pic_top", "pic_bottom", "td", "plain")} for e in entries], f, indent=1)
    print("conversions that failed: %d | laid out: tuned-on %s, held out %s" % (failed, counts[False], counts[True]))
    print("insurers: tuned-on %d, held out %d" % (len({e["insurer"] for e in entries if not e["held_out"]}), len({e["insurer"] for e in entries if e["held_out"]})))
