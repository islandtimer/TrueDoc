"""Three page shapes, sized before any rule is written (23 September 2026).

1. A side note in a drawn box (F1): a filled or outlined box, narrower than the page, holding lines of text, with lines
   of the body beside it at the same height. Fault: TrueDoc threads the box's lines into the paragraph beside it - one
   block holding lines from inside the box and from outside it.
2. A table of wrapped lists with no rules between its rows (F5): lists of bullet-led lines set side by side. Fault: a
   table built one row per printed line - an item's second line, with no bullet, in a row of its own under it.
3. A page counted unreadable for the wrong reason (F4): the text-layer check (`textlayer._assess_quality`) rejects
   a page with (almost) nothing on it, a ruled page for notes, and a page whose text is in several scripts; each is
   reported `unreadable-pages` and its document ends `incomplete`. Sorted here by what the page holds.

`screen` reads every page without the layout model (text layer, marks, drawn objects, the text-layer verdict);
`convert` converts the pages flagged for 1 and 2, up to N a document for each, with the product's options; `report`
counts pages, documents and insurers, and the faults as TrueDoc writes them. Populations as in
`side_label_icon_census.py`; held-out pages counted, never named, no text of theirs kept.

usage (repo root, the project's venv):
    box_list_blank_census.py screen bench|insurance|library <out.jsonl> [workers]
    box_list_blank_census.py convert <screen.jsonl> <out.jsonl> [workers] --pop bench|insurance|library [--per-doc N]
    box_list_blank_census.py report <screen.jsonl> [<convert.jsonl>]
"""
import collections
import concurrent.futures
import json
import os
import sys
import unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "bench", "probes"))
sys.path.insert(0, os.path.join(REPO, "bench", "tools"))
from side_label_icon_census import jobs as _jobs  # noqa: E402


def jobs(which):
    """The populations of side_label_icon_census.py, and `bench-all`: every benchmark page, scanned ones too (a page
    counted unreadable is as often a scan)."""
    if which != "bench-all":
        yield from _jobs(which)
        return
    from order_screen import jobs as every
    for label, path, number, secret in every("bench"):
        yield (label, path, [number], secret, label.split("/")[0], label)

BULLETS = set("•●▪‣◦■□–-·○✓✗")
DASHES = set("–-")


MARKS = set("✓✗○")


def is_bullet(text: str) -> bool:
    """A line or a cell that opens with a bullet: a dash only when a space follows it, since "-0.05" is a number, and
    never a tick, a cross or a circle - a table's marks, not a list's."""
    t = text.strip()
    return bool(t) and t[0] in BULLETS and t[0] not in MARKS and (t[0] not in DASHES or t[1:2] == " ")


def opening(text: str) -> str:
    """How a cell's text opens, in a word that holds none of its words (what a held-out page may keep)."""
    t = text.strip()
    if not t:
        return "empty"
    if is_bullet(t):
        return "bullet"
    if t[0] in MARKS:
        return "mark"
    return "lower" if t[0].islower() else "upper" if t[0].isupper() else "digit" if t[0].isdigit() else "other"


def _script(ch: str) -> str | None:
    if not ch.isalpha():
        return None
    try:
        name = unicodedata.name(ch)
    except ValueError:
        return None
    head = name.split()[0]
    return "CJK" if head in ("CJK", "HIRAGANA", "KATAKANA", "HANGUL") else head


def _boxes(path, number, page, lines):
    """Drawn boxes holding two lines or more, with lines of text beside them at the same height."""
    from truedoc.extract import pdfium_objects

    objs = pdfium_objects.page_objects(path, number) or []
    W, H = page.width, page.height
    found = []
    for o in objs:
        if o.kind != "path" or (o.fill is None and o.stroke is None):
            continue
        x0, y0, x1, y1 = o.bbox
        w, h = x1 - x0, y1 - y0
        if not (60 <= w <= 0.7 * W and 18 <= h <= 0.6 * H):
            continue
        if o.fill is not None and min(o.fill) > 0.985 and o.stroke is None:
            continue                                  # white on white
        inside = [l for l in lines if l.bbox.x0 >= x0 - 1 and l.bbox.x1 <= x1 + 1 and l.bbox.y0 >= y0 - 1 and l.bbox.y1 <= y1 + 1]
        if len(inside) < 2:
            continue
        beside = [l for l in lines if l not in inside and l.bbox.y1 > y0 and l.bbox.y0 < y1
                  and (l.bbox.x1 <= x0 + 1 or l.bbox.x0 >= x1 - 1)
                  and min(abs(l.bbox.x1 - x0), abs(l.bbox.x0 - x1)) <= 0.3 * W and len(l.words) >= 4]
        if not beside:
            continue
        box = [round(v, 1) for v in (x0, y0, x1, y1)]
        if any(abs(a - b) <= 2 for f in found for a, b in zip(f["box"], box)):
            continue
        found.append({"box": box, "inside": len(inside), "beside": len(beside), "filled": o.fill is not None})
    return found


def _lists(page, lines, objs_lines):
    """Bullet-led lines set in two columns side by side, and whether a drawn rule crosses both between their items."""
    W = page.width
    heads = [l for l in lines if l.words and is_bullet(l.text)]
    groups = collections.defaultdict(list)
    for l in heads:
        groups[round(l.bbox.x0 / 4)].append(l)
    cols = [g for g in groups.values() if len(g) >= 2]
    pairs = []
    for i, a in enumerate(cols):
        for b in cols[i + 1:]:
            ax, bx = a[0].bbox.x0, b[0].bbox.x0
            if abs(ax - bx) < 0.15 * W:
                continue
            a0, a1 = min(l.bbox.y0 for l in a), max(l.bbox.y1 for l in a)
            b0, b1 = min(l.bbox.y0 for l in b), max(l.bbox.y1 for l in b)
            overlap = min(a1, b1) - max(a0, b0)
            if overlap < 0.3 * min(a1 - a0, b1 - b0):
                continue
            left, right = min(ax, bx), max(ax, bx)
            rules = sum(1 for (x0, y0, x1, y1) in objs_lines if abs(y1 - y0) < 1.5 and x0 <= left + 5 and x1 >= right + 20
                        and max(a0, b0) < y0 < min(a1, b1))
            pairs.append({"x": [round(ax, 1), round(bx, 1)], "y": [round(max(a0, b0), 1), round(min(a1, b1), 1)],
                          "items": [len(a), len(b)], "rules_between": rules})
    return pairs


def screen_one(job):
    key, path, pages, secret, insurer, _k = job
    sys.path.insert(0, REPO)
    from truedoc.extract import pdfium_objects
    from truedoc.pipeline import ConvertOptions, load_document
    try:
        doc = load_document(path, ConvertOptions(frontmatter=False, pages=pages, layout=False, tables=False, math=False,
                                                 ocr=False, marks=True))
    except Exception as exc:
        return [{"doc": key, "insurer": insurer, "held_out": secret, "error": repr(exc)[:120]}]
    rows = []
    for page in doc.pages:
        lines = [l for l in page.lines if not l.rotated and l.text.strip()]
        objs = pdfium_objects.page_objects(path, page.number) or []
        rule_lines = [seg for o in objs if o.kind == "path" for seg in (o.lines or [])]
        q = page.quality
        scripts = collections.Counter(s for c in page.chars for s in [_script(c.text)] if s)
        kinds = collections.Counter(o.kind for o in objs)
        horizontal = sum(1 for (x0, y0, x1, y1) in rule_lines if abs(y1 - y0) < 1.5 and (x1 - x0) > 0.3 * page.width)
        rows.append({
            "doc": key, "insurer": insurer, "held_out": secret, "page": page.number, "w": round(page.width, 1),
            "h": round(page.height, 1),
            "quality": {"kind": q.kind, "usable": q.usable, "alnum": q.n_alnum, "garbage": round(q.garbage_fraction, 3),
                        "images": round(q.image_coverage, 3)},
            "objects": {"path": kinds.get("path", 0), "image": kinds.get("image", 0), "text": kinds.get("text", 0),
                        "horizontal_rules": horizontal},
            "scripts": {s: n for s, n in scripts.items() if n >= 20},
            "boxes": _boxes(path, page.number, page, lines),
            "lists": _lists(page, lines, rule_lines),
        })
    return rows


def f4_kind(r) -> str | None:
    """What a page the text-layer check rejects holds."""
    q, o = r["quality"], r["objects"]
    if q["usable"]:
        return None
    if len(r["scripts"]) >= 2 and q["kind"] == "suspect":
        return "several scripts"
    if q["alnum"] == 0 and o["image"] == 0 and o["path"] == 0:
        return "blank"
    if q["alnum"] < 20 and o["image"] == 0 and o["horizontal_rules"] >= 5:
        return "ruled (a page for notes)"
    if q["alnum"] < 20 and o["image"] == 0:
        return "nearly empty, drawings only"
    if o["image"] and q["alnum"] < 20:
        return "a picture or a scan"
    return "other text-layer fault"


# ------------------------------------------------------------------------------------------------ conversion

def convert_one(job):
    key, path, pages, secret, insurer = job
    sys.path.insert(0, REPO)
    from truedoc.model import BlockKind
    from truedoc.pipeline import ConvertOptions, load_document
    rows = []
    for number in pages:
        try:
            doc = load_document(path, ConvertOptions(frontmatter=False, pages=[number]))
        except Exception as exc:
            rows.append({"doc": key, "page": number, "held_out": secret, "insurer": insurer, "error": repr(exc)[:120]})
            continue
        page = doc.pages[0]
        blocks = []
        for b in sorted(page.blocks, key=lambda b: b.order):
            rec = {"k": b.kind.value, "o": b.order, "b": [round(v, 1) for v in (b.bbox.x0, b.bbox.y0, b.bbox.x1, b.bbox.y1)],
                   "ls": [[round(v, 1) for v in (l.bbox.x0, l.bbox.y0, l.bbox.x1, l.bbox.y1)] for l in b.lines]}
            if b.kind == BlockKind.TABLE and b.table is not None:
                cells = []
                for c in b.table.cells:
                    t = (c.text or "").strip()
                    cells.append({"r": c.row, "c": c.col, "rs": c.rowspan, "cs": c.colspan, "bullet": is_bullet(t),
                                  "lower": t[:1].islower(), "empty": not t, "lines": t.count("\n") + 1 if t else 0,
                                  "stops": t[-1:] in ".;:!?)", "opens": opening(t),
                                  **({} if secret else {"t": t[:60]})})
                rec["cells"] = cells
                rec["rows"] = b.table.n_rows
            blocks.append(rec)
        rows.append({"doc": key, "page": number, "held_out": secret, "insurer": insurer, "w": round(page.width, 1),
                     "blocks": blocks})
    return rows


def threaded(box, blocks) -> bool:
    """A block holding lines from inside the box and from outside it - where the box holds prose: two lines or more
    across half its width at least. A figure's frame round its axis labels is a box of text too, and not a note."""
    x0, y0, x1, y1 = box
    inside = [l for b in blocks if b["k"] not in ("table", "figure") for l in b["ls"]
              if l[0] >= x0 - 1 and l[2] <= x1 + 1 and l[1] >= y0 - 1 and l[3] <= y1 + 1]
    if sum(1 for l in inside if l[2] - l[0] >= 0.5 * (x1 - x0)) < 2:
        return False
    for b in blocks:
        if b["k"] in ("table", "figure") or len(b["ls"]) < 2:
            continue
        ins = [l for l in b["ls"] if l[0] >= x0 - 1 and l[2] <= x1 + 1 and l[1] >= y0 - 1 and l[3] <= y1 + 1]
        if ins and len(ins) < len(b["ls"]):
            return True
    return False


def cut_lists(blocks) -> bool:
    """A table whose items are cut one row per printed line: in a column holding bullet-led cells, a bullet-led cell
    that does not end its sentence, and the next filled cell below it carrying its words on without a bullet - the
    item's second line in a row of its own."""
    for b in blocks:
        cells = b.get("cells")
        if not cells:
            continue
        columns = collections.defaultdict(list)
        for c in cells:
            if not c["empty"]:
                if "opens" in c:
                    c = dict(c, bullet=c["opens"] == "bullet")
                elif "t" in c:
                    c = dict(c, bullet=is_bullet(c["t"]))      # the stored words say it again, by today's test
                columns[c["c"]].append(c)
        for col in columns.values():
            if sum(c["bullet"] for c in col) < 2:
                continue
            col.sort(key=lambda c: c["r"])
            for a, below in zip(col, col[1:]):
                if a["bullet"] and not a["stops"] and not below["bullet"] and a["lines"] == 1:
                    return True
    return False


def report(screen_path, convert_path=None):
    S = [json.loads(l) for l in open(screen_path, encoding="utf-8")]
    S = [r for r in S if "error" not in r]
    print("SCREEN: %d pages of %d documents; held-out pages %d" % (len(S), len({r["doc"] for r in S}), sum(r["held_out"] for r in S)))
    for title, pred in (("F1 a drawn box of 2+ lines with body text beside it", lambda r: r["boxes"]),
                        ("F5 bullet lists side by side", lambda r: r["lists"]),
                        ("F5 ... with no drawn rule between their items", lambda r: any(p["rules_between"] == 0 for p in r["lists"]))):
        pages = [r for r in S if pred(r)]
        print("%-52s pages %5d (held-out %d) | documents %4d (held-out %d) | insurers %3d" % (
            title, len(pages), sum(r["held_out"] for r in pages), len({r["doc"] for r in pages}),
            len({r["doc"] for r in pages if r["held_out"]}), len({r["insurer"] for r in pages})))
    kinds = collections.Counter()
    docs = collections.defaultdict(set)
    docs_held = collections.defaultdict(set)
    for r in S:
        k = f4_kind(r)
        if k:
            kinds[k] += 1
            docs[k].add(r["doc"])
            if r["held_out"]:
                docs_held[k].add(r["doc"])
    print("F4 pages the text-layer check rejects, by what they hold:")
    for k, n in kinds.most_common():
        print("     %-32s pages %5d | documents %4d (held-out %d)" % (k, n, len(docs[k]), len(docs_held[k])))
    wrong = {"blank", "ruled (a page for notes)", "several scripts"}
    every = collections.defaultdict(set)
    for r in S:
        k = f4_kind(r)
        if k:
            every[r["doc"]].add(k)
    only_wrong = [d for d, ks in every.items() if ks <= wrong]
    print("   documents whose every rejected page is blank, ruled or in several scripts: %d (so today's `incomplete` is wrong)" % len(only_wrong))
    if not convert_path:
        return
    C = [json.loads(l) for l in open(convert_path, encoding="utf-8")]
    C = [r for r in C if "blocks" in r]
    boxes = {(r["doc"], r["page"]): r["boxes"] for r in S}
    lists = {(r["doc"], r["page"]): r["lists"] for r in S}
    f1 = [r for r in C if boxes.get((r["doc"], r["page"]))]
    f1_bad = [r for r in f1 if any(threaded(b["box"], r["blocks"]) for b in boxes[(r["doc"], r["page"])])]
    f5 = [r for r in C if lists.get((r["doc"], r["page"]))]
    f5_bad = [r for r in f5 if cut_lists(r["blocks"])]
    print("\nCONVERTED %d pages of %d documents" % (len(C), len({r["doc"] for r in C})))
    for title, all_, bad in (("F1 box beside text", f1, f1_bad), ("F5 lists side by side", f5, f5_bad)):
        print("%-24s pages converted %4d | fault on %4d (held-out %d) | documents %d (held-out %d) | insurers %d" % (
            title, len(all_), len(bad), sum(r["held_out"] for r in bad), len({r["doc"] for r in bad}),
            len({r["doc"] for r in bad if r["held_out"]}), len({r["insurer"] for r in bad})))
        print("   by insurer (tuned-on): %s" % dict(collections.Counter(r["insurer"] for r in bad if not r["held_out"]).most_common()))


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "report":
        report(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
        sys.exit(0)
    if mode == "screen":
        which, out = sys.argv[2], sys.argv[3]
        workers = int(sys.argv[4]) if len(sys.argv) > 4 else 10
        todo = list(jobs(which))
        print(len(todo), "documents", flush=True)
        with open(out, "w", encoding="utf-8") as f, concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
            for n, rows in enumerate(pool.map(screen_one, todo, chunksize=1), 1):
                for r in rows:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
                if n % 50 == 0:
                    print(" ", n, flush=True)
        print("done", flush=True)
    elif mode == "convert":
        src, out = sys.argv[2], sys.argv[3]
        workers = int(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[4].isdigit() else 6
        which = sys.argv[sys.argv.index("--pop") + 1]
        cap = int(sys.argv[sys.argv.index("--per-doc") + 1]) if "--per-doc" in sys.argv else None
        paths = {j[0]: (j[1], j[3], j[4]) for j in jobs(which)}      # the screen names a page's document by j[0]
        by_doc = collections.defaultdict(list)
        for line in open(src, encoding="utf-8"):
            r = json.loads(line)
            if "error" not in r:
                by_doc[r["doc"]].append(r)
        only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
        held_only = "--held-only" in sys.argv
        whole = sys.argv[sys.argv.index("--whole") + 1] if "--whole" in sys.argv else None

        def f1_score(r):
            # a page with a box or two of real text beside the body, not a page of table cells
            good = [b for b in r["boxes"] if b["inside"] >= 3 and b["beside"] >= 3]
            return (len(good) > 0, -len(r["boxes"]), max((min(b["inside"], b["beside"]) for b in good), default=0))

        todo = []
        for doc, rs in by_doc.items():
            if held_only and not rs[0]["held_out"]:
                continue
            take = set()
            for key, fault in (("boxes", "f1"), ("lists", "f5")):
                if only and fault != only:
                    continue
                if whole and whole in doc:
                    take.update(r["page"] for r in rs if r[key])
                    continue
                rank = f1_score if fault == "f1" else (lambda r: len(r["lists"]))
                ranked = sorted((r for r in rs if r[key]), key=rank, reverse=True)
                take.update(r["page"] for r in (ranked[:cap] if cap else ranked))
            if take:
                todo.append((doc, paths[doc][0], sorted(take), paths[doc][1], paths[doc][2]))
        todo.sort(key=lambda j: -len(j[2]))
        print(len(todo), "documents,", sum(len(j[2]) for j in todo), "pages", flush=True)
        done = 0
        with open(out, "w", encoding="utf-8") as f, concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
            for rows in pool.map(convert_one, todo, chunksize=1):
                for r in rows:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
                done += len(rows)
                print("  pages", done, flush=True)
        print("done", flush=True)
