"""Every block a conversion takes out as a running head or foot, and whether the pages beside it print it there.

Honey's household PDS sets each peril's name at the top of its page ("Animal damage", "Explosion", "Flood") and the
layout model labelled each a page header, so no peril's page said which peril it describes; AAMI's definitions pages
lost their terms ("Incident", "Illegal drugs") to the margin clean-up the same way. A running head runs: the same words
at the same height, page after page. For every HEADER, FOOTER and PAGE_NUMBER block a page's conversion takes out, this
records the rule that took it (its provenance), where it sits, and whether a page within two either side prints most
of its words (60%) in the same band - measured down from the head of each page for a block in the upper half of its
page, up from the foot for one in the lower half, as `layout/fuse.py`'s `_repeated_beside` asks it: true, false, or
null when no page beside it has a text layer. Pages are loaded as a conversion loads them (`load_document`: the layout
model and the margin clean-up), without OCR, maths, marks or tables.

Run on the code before a change, the heads not repeated beside them are what asking the question gives back; run on
the code after it, the only ones left should be those no rule asks about (text in a picture's banner, rotated tabs).

usage (repo root):
    PYTHONPATH=<tree> running_head_census.py scan <insurance | kfs | sample:N | list:<file> | <pdf>@<page>>
        --out <file.jsonl> [--workers 3]
    running_head_census.py read <file.jsonl> [<file.jsonl> ...] [--kind HEADER] [--provenance <rule>] [--limit 40]
"""
import collections
import concurrent.futures
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
_WORD = re.compile("[a-z]{2,}")


def tasks_for(name: str) -> list:
    """The census names of `unplaced_marks_census.py`, and a list of "<pdf>@<page>" lines - a census stopped part-way
    goes on from the pages it has not read, shuffled or not."""
    if name.startswith("list:"):
        with open(name[len("list:"):], encoding="utf-8") as fh:
            specs = [line.strip() for line in fh if line.strip()]
        return [(spec.rsplit("@", 1)[0], int(spec.rsplit("@", 1)[1])) for spec in specs]
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from unplaced_marks_census import tasks_for as census_tasks

    return census_tasks(name)


def repeated(path: str, index: int, text: str, y0: float, y1: float, height: float, size: float, head: bool):
    """Most of the block's words in the same band on a page within two either side; None when no such page has text."""
    import pypdfium2 as pdfium

    words = set(_WORD.findall(text.lower()))
    if not words:
        return None
    doc = pdfium.PdfDocument(path)
    asked = False
    try:
        for i in (index - 2, index - 1, index + 1, index + 2):
            if not 0 <= i < len(doc):
                continue
            other = doc[i]
            textpage = other.get_textpage()
            try:
                if textpage.count_chars() == 0:
                    continue
                asked = True
                _, bottom, _, top = other.get_cropbox()
                if head:
                    band = textpage.get_text_bounded(bottom=top - y1 - size, top=top - max(0.0, y0 - size))
                else:
                    band = textpage.get_text_bounded(bottom=bottom + max(0.0, height - y1 - size),
                                                     top=bottom + height - y0 + size)
            finally:
                textpage.close()
                other.close()
            if len(words & set(_WORD.findall(band.lower()))) >= 0.6 * len(words):
                return True
    finally:
        doc.close()
    return False if asked else None


def scan(task):
    path, number = task
    try:
        from truedoc.model import BlockKind
        from truedoc.pipeline import ConvertOptions, load_document

        opts = ConvertOptions(frontmatter=False, pages=[number], ocr=False, math=False, marks=False, tables=False)
        doc = load_document(path, opts)
        for page in doc.pages:
            body = page.body_font_size or 10.0
            rows = []
            for b in getattr(page, "blocks", None) or []:
                if b.kind not in (BlockKind.HEADER, BlockKind.FOOTER, BlockKind.PAGE_NUMBER):
                    continue
                text = " ".join(b.text.split())
                size = b.size or body
                rows.append({
                    "kind": b.kind.name, "provenance": str(b.provenance), "text": text[:160],
                    "y0": round(b.bbox.y0 / page.height, 3), "y1": round(b.bbox.y1 / page.height, 3),
                    "x0": round(b.bbox.x0), "x1": round(b.bbox.x1), "size": round(size, 1), "lines": len(b.lines),
                    "rotated": bool(b.lines) and all(getattr(l, "rotated", False) for l in b.lines),
                    "repeated": repeated(path, number - 1, text, b.bbox.y0, b.bbox.y1, page.height, size,
                                         b.bbox.cy < 0.5 * page.height),
                })
            return {"pdf": path, "page": number, "height": round(page.height), "body": body, "blocks": rows}
        return {"pdf": path, "page": number, "error": "no page"}
    except Exception as exc:
        return {"pdf": path, "page": number, "error": repr(exc)[:200]}


def read(files: list, kind: str, only: str | None, limit: int) -> None:
    rows = [json.loads(line) for file in files for line in open(file, encoding="utf-8")]
    pages = [r for r in rows if not r.get("error")]
    by_rule = collections.defaultdict(list)
    for r in pages:
        for b in r["blocks"]:
            if b["kind"] == kind and not b["rotated"]:
                by_rule[(b["provenance"], b["repeated"])].append((r, b))
    documents = len({r["pdf"] for r in pages})
    print(f"{len(pages)} pages of {documents} documents read, {len(rows) - len(pages)} errors; "
          f"{kind} blocks (not rotated) by rule and repetition:")
    for (rule, rep), items in sorted(by_rule.items(), key=lambda kv: (kv[0][0], str(kv[0][1]))):
        on = len({(r["pdf"], r["page"]) for r, _ in items})
        print(f"  {rule:28s} repeated={str(rep):5s} {len(items):4d} blocks on {on:4d} pages")
    shown = 0
    for (rule, rep), items in sorted(by_rule.items(), key=lambda kv: (kv[0][0], str(kv[0][1]))):
        if rep is not False or (only and rule != only):
            continue
        print(f"=== {rule}, not repeated beside")
        for r, b in items[:max(0, limit - shown)]:
            print(f"  {os.path.basename(r['pdf'])[:58]:60s} p{r['page']:<4d} y {b['y0']:.3f}-{b['y1']:.3f} "
                  f"size {b['size']:>4} body {r['body']:>4} | {b['text'][:90]}")
            shown += 1


def main() -> None:
    args = sys.argv[1:]
    if args[0] == "read":
        files = [a for i, a in enumerate(args[1:], 1) if not a.startswith("--") and not args[i - 1].startswith("--")]
        kind = args[args.index("--kind") + 1] if "--kind" in args else "HEADER"
        only = args[args.index("--provenance") + 1] if "--provenance" in args else None
        limit = int(args[args.index("--limit") + 1]) if "--limit" in args else 40
        read(files, kind, only, limit)
        return
    out = args[args.index("--out") + 1]
    workers = int(args[args.index("--workers") + 1]) if "--workers" in args else 3
    tasks = tasks_for(args[1])
    print(f"{len(tasks)} pages", flush=True)
    with open(out, "w", encoding="utf-8") as fh, concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
        for done, row in enumerate(pool.map(scan, tasks, chunksize=1), 1):
            fh.write(json.dumps(row) + "\n")
            fh.flush()
            if done % 25 == 0:
                print(f"  {done}/{len(tasks)}", flush=True)
    print("done", flush=True)


if __name__ == "__main__":
    main()
