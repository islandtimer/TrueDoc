"""Two page shapes, sized before any rule is written: a label in a narrow left column beside a group of lines, and a
small drawing repeated at the head of text lines.

1. The side label. A short piece of text (three words at most) stands at the left, apart from the lines beside it by a
   gutter, its top level with the first line of a group that runs down beside it: "Yes" beside the lines that are
   covered, "Limits" beside the limits. A reader takes the label first and the group under it. The label's column is
   narrow, so the reading-order cut declines to treat it as a column (its guard against a line-number gutter), and the
   label is then weighed against the wide line beside it by their centres - a tie a label can lose by a fraction of a
   point, which writes it after the first line it governs.
2. The item icon. A small drawing or picture (a mark's size, `marks._small`) at the head of a text line, the same
   drawing repeated through the document: a tick, a cross, a dollar in a circle opening each item. The mark reader
   reads some of them; the layout model calls each a picture, and a picture is written as a placeholder.

Three stages. `screen` reads the text layer and the small drawings of every page, without the layout model, and
records every side label and every small drawing at a line's head. `convert` converts the pages the screen flags,
with the layout model (the product's own options, no vision reader), and records the blocks as TrueDoc builds them.
`report` counts: pages, documents, insurers, and the faults as TrueDoc writes them today.

Populations: the benchmark's digital pages (a scanned page is read by a model, D019), the insurance set's 25 pages,
and the library - every document but the sealed 19 (D030), every page. Held-out pages (the benchmark's holdout.txt;
the library's odd-hash half, D039/D040, and the Key Facts oracle's fifth, D027) are counted, never named, and no text
of theirs is recorded.

Written 23 September 2026 to size both shapes before a rule was written; `side_label_icon_designs.py` groups the
documents that show each into designs, so that one design sold under several brands counts once.

usage (repo root, the project's venv):
    side_label_icon_census.py screen bench|insurance|library <out.jsonl> [workers]
    side_label_icon_census.py convert <screen.jsonl> <out.jsonl> [workers] --pop bench|insurance|library [--all | --per-doc N]
    side_label_icon_census.py report <screen.jsonl> [<convert.jsonl>]
"""
import collections
import concurrent.futures
import glob
import hashlib
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "bench", "tools"))
sys.path.insert(0, os.path.join(REPO, "bench", "probes"))

LABEL_WORDS = 3          # a side label is three words at most ...
LABEL_CHARS = 30
LABEL_WIDTH = 0.15       # ... no wider than this share of the page
ALIGN = 0.4              # tops level within this share of the shorter line's height
GUTTER = 0.8             # the label stands apart from its line by at least this many body sizes ...
GUTTER_MAX = 0.4         # ... and no further than this share of the page
HEAD_GAP = 3.0           # a drawing leads a line starting within this many body sizes to its right


def _secret_library(path):
    name = os.path.basename(path)
    if int(hashlib.sha1(name.encode("utf-8")).hexdigest()[:8], 16) % 2 == 1:
        return True
    import kfs_grade
    return bool(kfs_grade.held_out(path))


def _insurer(rel):
    parts = rel.replace("\\", "/").split("/")
    return parts[1] if parts[0].startswith("zz_") and len(parts) > 2 else parts[0]


def jobs(which):
    """(label, path, pages or None for every page, held_out, insurer, document key)."""
    if which == "insurance":
        m = json.load(open(os.path.join(REPO, "bench", "out", "insurance_set", "manifest.json"), encoding="utf-8"))
        import doc_library
        for e in (m if isinstance(m, list) else next(v for v in m.values() if isinstance(v, list))):
            rel = doc_library.relative(e["pdf"])
            yield (e["name"], e["pdf"], [e["page"]], False, _insurer(rel), rel)
    elif which == "bench":
        b = os.path.join(REPO, "bench", "data", "olmocr-bench", "bench_data", "pdfs")
        scans = {l.split("\t")[0].strip() for l in open(os.path.join(REPO, "bench", "gpu", "pages.txt"), encoding="utf-8") if l.strip()}
        held = {l.strip()[:-4] for l in open(os.path.join(REPO, "bench", "holdout.txt"), encoding="utf-8")
                if l.strip() and not l.startswith("#")}
        for p in sorted(glob.glob(os.path.join(b, "*", "*.pdf"))):
            label = os.path.basename(os.path.dirname(p)) + "/" + os.path.basename(p)[:-4]
            if label not in scans:
                yield (label, p, [1], label in held, os.path.basename(os.path.dirname(p)), label)
    else:
        import doc_library
        root = doc_library.root()
        sealed = {l.strip().replace("\\", "/") for l in open(os.path.join(REPO, "bench", "insurance_holdout.txt"), encoding="utf-8")
                  if l.strip() and not l.startswith("#")}
        sealed_names = {os.path.basename(s) for s in sealed}
        pdfs = sorted(os.path.join(d, f).replace("\\", "/") for d, _, fs in os.walk(root) for f in fs if f.lower().endswith(".pdf"))
        for p in pdfs:
            rel = doc_library.relative(p)
            if rel in sealed or os.path.basename(p) in sealed_names:
                continue
            secret = _secret_library(p)
            key = ("held:" + hashlib.sha1(rel.encode("utf-8")).hexdigest()[:10]) if secret else rel
            yield (key, p, None, secret, _insurer(rel), key)


# ------------------------------------------------------------------------------------------------ the screen

def _words(text):
    return len(text.split())


def _label_kind(text):
    t = text.strip()
    letters = sum(c.isalpha() for c in t)
    return "word" if letters >= 2 else "marker"


def side_labels(page):
    """Side labels on a page from its text-layer lines (no layout model)."""
    body = page.body_font_size or 10.0
    lines = [l for l in page.lines if not l.rotated and l.text.strip()]
    out = []
    for L in lines:
        t = L.text.strip()
        if _words(t) > LABEL_WORDS or len(t) > LABEL_CHARS or L.bbox.width > LABEL_WIDTH * page.width:
            continue
        best = None
        for R in lines:
            if R is L or R.bbox.x0 <= L.bbox.x1:
                continue
            gap = R.bbox.x0 - L.bbox.x1
            if gap < GUTTER * body or gap > GUTTER_MAX * page.width:
                continue
            if abs(R.bbox.y0 - L.bbox.y0) > ALIGN * min(L.bbox.height, R.bbox.height):
                continue
            if best is None or gap < best[0]:
                best = (gap, R)
        if best is None:
            continue
        gap, R = best
        # Nothing between the label and its line.
        if any(o is not L and o is not R and o.bbox.x0 >= L.bbox.x1 - 0.5 and o.bbox.x1 <= R.bbox.x0 + 0.5
               and o.bbox.y1 > L.bbox.y0 and o.bbox.y0 < L.bbox.y1 for o in lines):
            continue
        # The group: lines below R that start at R's edge or indented from it, down to a line that starts left of it.
        group = [R]
        below = sorted((o for o in lines if o.bbox.y0 > R.bbox.y0 + 0.5 * R.bbox.height), key=lambda o: o.bbox.y0)
        for o in below:
            if o.bbox.x1 < R.bbox.x0 - 1.0:
                # Something in the label's column: the next label, or text across both columns.
                if o.bbox.y0 - group[-1].bbox.y1 < 2.5 * R.bbox.height:
                    break
                break
            if o.bbox.x0 < R.bbox.x0 - 1.5:
                break
            if o.bbox.x0 > R.bbox.x0 + 6.0 * body:
                continue            # something further right (a second column) is not the group
            if o.bbox.y0 - group[-1].bbox.y1 > 1.6 * max(R.bbox.height, body):
                break
            group.append(o)
        out.append({
            "kind": _label_kind(t),
            "text": t,
            "L": [round(v, 1) for v in (L.bbox.x0, L.bbox.y0, L.bbox.x1, L.bbox.y1)],
            "R": [round(v, 1) for v in (R.bbox.x0, R.bbox.y0, R.bbox.x1, R.bbox.y1)],
            "group_lines": len(group),
            "dcy": round(L.bbox.cy - R.bbox.cy, 2),     # > 0: the label's centre is below its line's
            "gap": round(gap, 1),
        })
    return out


def head_drawings(page):
    """Every small drawing the mark reader found, whether it leads a line, and a signature for counting repeats."""
    body = page.body_font_size or 10.0
    lines = [l for l in page.lines if not l.rotated and l.text.strip()]
    out = []
    for m in page.meta.get("marks") or []:
        x0, y0, x1, y1 = m["bbox"]
        cy, h = (y0 + y1) / 2, y1 - y0
        head = bool(m.get("placed"))       # a mark the reader placed opens its line (tables are off in the screen)
        if not head:
            for l in lines:
                if l.bbox.y1 < y0 or l.bbox.y0 > y1:
                    continue
                if abs(l.bbox.cy - cy) > 0.7 * max(l.bbox.height, h):
                    continue
                if -1.0 <= l.bbox.x0 - x1 <= HEAD_GAP * body:
                    head = True
                    break
        out.append({"kind": m["kind"], "colour": m.get("colour", ""), "bbox": m["bbox"], "placed": bool(m.get("placed")),
                    "head": head, "sig": "%s|%s|%d|%d" % (m["kind"], m.get("colour", ""), round(x1 - x0), round(y1 - y0))})
    return out


def screen_one(job):
    label, path, pages, secret, insurer, key = job
    sys.path.insert(0, REPO)
    from truedoc.pipeline import ConvertOptions, load_document
    try:
        doc = load_document(path, ConvertOptions(frontmatter=False, pages=pages, layout=False, tables=False, math=False,
                                                 ocr=False, marks=True))
    except Exception as exc:
        return [{"doc": key, "insurer": insurer, "held_out": secret, "error": repr(exc)[:120]}]
    rows = []
    for page in doc.pages:
        labels = side_labels(page)
        draws = head_drawings(page)
        if secret:
            for x in labels:
                x.pop("text")
        rows.append({"doc": key, "insurer": insurer, "held_out": secret, "page": page.number,
                     "w": round(page.width, 1), "h": round(page.height, 1), "body": page.body_font_size,
                     "n_lines": len(page.lines), "labels": labels, "draws": draws})
    return rows


# ---------------------------------------------------------------------------------------------- the conversion

def _icon_signature(pdf, number, box):
    """A coarse picture of a small drawing, for telling the same icon again: 12 x 12 cells of ink, and its colour."""
    page = pdf[number - 1]
    x0, y0, x1, y1 = box
    H = page.get_height()
    scale = 4.0
    try:
        img = page.render(scale=scale, crop=(x0, H - y1, page.get_width() - x1, y0)).to_pil().convert("RGB")
    except Exception:
        return None
    # The layout model's box sits differently around each copy of an icon: cut the picture down to its ink, measured
    # against the crop's own background (its commonest colour), before it is compared.
    full = list(img.getdata())
    bg = collections.Counter(full).most_common(1)[0][0]
    W0, H0 = img.size
    far = lambda p: abs(p[0] - bg[0]) + abs(p[1] - bg[1]) + abs(p[2] - bg[2]) > 90
    xs = [i % W0 for i, p in enumerate(full) if far(p)]
    ys = [i // W0 for i, p in enumerate(full) if far(p)]
    if not xs:
        return "blank"
    img = img.crop((min(xs), min(ys), max(xs) + 1, max(ys) + 1)).resize((12, 12))
    px = list(img.getdata())
    bits = "".join("1" if far(p) else "0" for p in px)
    ink = [(r, g, b) for (r, g, b), bit in zip(px, bits) if bit == "1"]
    if ink:
        r, g, b = (sum(c[i] for c in ink) / len(ink) for i in range(3))
        colour = "green" if g > r + 30 and g > b else "red" if r > g + 40 and r > b + 40 else "blue" if b > r + 30 else "dark"
    else:
        colour = "none"
    return bits + "|" + colour


def same_icon(a, b, tolerance=12):
    """Two signatures of one icon: the same colour, and pictures differing in few of their 144 cells."""
    if a == b:
        return True
    if not a or not b or "|" not in a or "|" not in b:
        return False
    (ba, ca), (bb, cb) = a.split("|"), b.split("|")
    if ca != cb or len(ba) != len(bb):
        return False
    return sum(x != y for x, y in zip(ba, bb)) <= tolerance


def convert_one(job):
    key, path, pages, secret, insurer = job
    sys.path.insert(0, REPO)
    from truedoc.model import BlockKind
    from truedoc.pipeline import ConvertOptions, load_document
    from truedoc.render.okf import RenderOptions, render_document
    import pypdfium2 as pdfium
    rows = []
    pdf = pdfium.PdfDocument(path)
    for number in pages:
        try:
            doc = load_document(path, ConvertOptions(frontmatter=False, pages=[number]))
        except Exception as exc:
            rows.append({"doc": key, "page": number, "held_out": secret, "insurer": insurer, "error": repr(exc)[:120]})
            continue
        page = doc.pages[0]
        blocks = []
        for b in sorted(page.blocks, key=lambda b: b.order):
            rec = {"k": b.kind.value, "p": b.provenance, "o": b.order,
                   "b": [round(v, 1) for v in (b.bbox.x0, b.bbox.y0, b.bbox.x1, b.bbox.y1)],
                   "nl": len(b.lines), "nw": len(b.text.split()) if b.text else 0,
                   "na": sum(ch.isalpha() for ch in (b.text or ""))}
            if b.lines:
                rec["ls"] = [[round(v, 1) for v in (l.bbox.x0, l.bbox.y0, l.bbox.x1, l.bbox.y1)] for l in b.lines]
            if b.kind == BlockKind.FIGURE:
                rec["mo"] = b.meta.get("mark_only") or ""
                rec["placeholder"] = not b.lines and b.text_override is None and not b.meta.get("mark_only")
                side = max(b.bbox.width, b.bbox.height)
                if rec["placeholder"] and side <= 30.0 * max(1.0, max(page.width, page.height) / 792.0):
                    rec["sig"] = _icon_signature(pdf, number, rec["b"])
            if not secret:
                rec["t"] = (b.text or "")[:100]
            blocks.append(rec)
        row = {"doc": key, "page": number, "held_out": secret, "insurer": insurer,
               "w": round(page.width, 1), "h": round(page.height, 1), "body": page.body_font_size,
               "blocks": blocks, "marks": page.meta.get("marks") or []}
        if not secret:
            try:
                row["md"] = render_document(doc, RenderOptions(frontmatter=False))
            except Exception as exc:
                row["md_error"] = repr(exc)[:100]
        rows.append(row)
    pdf.close()
    return rows


def flagged(r):
    """A page the conversion must see: a side label of words, a small drawing at a line's head, or one small drawing
    three times or more on the page (a table's column of ticks has no line to lead)."""
    if any(x["kind"] == "word" for x in r.get("labels", [])):
        return True
    draws = r.get("draws", [])
    if any(d["head"] for d in draws):
        return True
    return any(n >= 3 for n in collections.Counter(d["sig"] for d in draws).values())


# -------------------------------------------------------------------------------------------------- the report

def _rows(path):
    return [json.loads(l) for l in open(path, encoding="utf-8")]


def _body_like(x, w):
    """A side label's line is a line of the body, not the next cell of a row of short labels."""
    R, L = x["R"], x["L"]
    return (R[2] - R[0]) >= 0.15 * w and (R[2] - R[0]) >= 2.0 * (L[2] - L[0])


def label_outcomes(r):
    """Each side label as TrueDoc wrote it: before its first line, after it, or beside a block's inner line."""
    body = r.get("body") or 10.0
    blocks = r["blocks"]
    tables = [b["b"] for b in blocks if b["k"] == "table"]
    texty = [b for b in blocks if b["k"] in ("text", "heading", "list_item", "title", "caption", "footnote") and b.get("ls")]
    out = []
    for L in texty:
        if L["nw"] == 0 or L["nw"] > LABEL_WORDS or len(L["ls"]) > LABEL_WORDS:
            continue            # "We / don't / cover" is set a word to a line
        x0, y0, x1, y1 = L["b"]
        if x1 - x0 > LABEL_WIDTH * r["w"]:
            continue
        if L.get("na", sum(c.isalpha() for c in L.get("t", "xx"))) < 2:
            continue
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        if any(t[0] <= cx <= t[2] and t[1] <= cy <= t[3] for t in tables):
            continue
        lh = L["ls"][0][3] - L["ls"][0][1]
        best = None
        for R in texty:
            if R is L:
                continue
            for i, ln in enumerate(R["ls"]):
                gap = ln[0] - x1
                if gap < GUTTER * body or gap > GUTTER_MAX * r["w"]:
                    continue
                if abs(ln[1] - L["ls"][0][1]) > ALIGN * min(lh, ln[3] - ln[1]):
                    continue
                # A line of the body, not the next of a row of short labels ("Home   Contents").
                if R["nw"] < 4 or (ln[2] - ln[0]) < 2.0 * (x1 - x0):
                    continue
                if best is None or gap < best[0]:
                    best = (gap, R, i)
        if best is None:
            continue
        gap, R, i = best
        edge = R["ls"][i][0]
        # The label's column holds labels only. A paper's section heading in its left column, level by chance with a
        # line of the right column, stands in a column of long body lines.
        column = [ln for b in texty for ln in b["ls"] if ln[2] < edge - 1.0 and ln[0] <= x1 and ln[2] >= x0]
        narrow = sum(1 for ln in column if ln[2] - ln[0] <= LABEL_WIDTH * r["w"])
        purity = narrow / max(1, len(column))
        # The group: lines at the line's edge or indented from it, from the line down to the next thing in the label's
        # column, while they run on without a wide gap.
        top = R["ls"][i][1]
        nxt = min([ln[1] for ln in column if ln[1] > y1 - 1.0] + [r["h"]])
        run = sorted((ln for b in texty if b is not L for ln in b["ls"]
                      if ln[0] >= edge - 1.5 and ln[1] >= top - 1.0 and ln[1] < nxt - 1.0), key=lambda ln: ln[1])
        group, last = 0, None
        for ln in run:
            if last is not None and ln[1] - last > 2.2 * max(lh, body):
                break
            group += 1
            last = ln[3]
        if i > 0:
            outcome = "inner"
        elif R["o"] < L["o"]:
            outcome = "after"
        elif any(L["o"] < b["o"] < R["o"] for b in texty):
            outcome = "separated"       # before its line, but other text read between them (a label column read whole)
        else:
            outcome = "right"
        out.append({"outcome": outcome, "L": L["b"], "label": L.get("t", ""), "line": (R.get("t") or "")[:60],
                    "R_lines": len(R["ls"]), "purity": round(purity, 2), "column": len(column), "group": group})
    return out


PURITY = 0.75           # a label column: at least this share of what stands in it is label-narrow


def icon_placeholders(r):
    """Every picture placeholder the size of a mark, and where it stands."""
    body = r.get("body") or 10.0
    blocks = r["blocks"]
    tables = [b["b"] for b in blocks if b["k"] == "table"]
    lines = [(b, ln) for b in blocks if b["k"] not in ("figure", "table") and b.get("ls") for ln in b["ls"]]
    out = []
    for f in blocks:
        if f["k"] != "figure" or not f.get("placeholder") or "sig" not in f:
            continue
        x0, y0, x1, y1 = f["b"]
        cx, cy, h = (x0 + x1) / 2, (y0 + y1) / 2, y1 - y0
        where = "other"
        led = None
        for b, ln in lines:
            if ln[3] < y0 or ln[1] > y1:
                continue
            if abs((ln[1] + ln[3]) / 2 - cy) > 0.7 * max(ln[3] - ln[1], h):
                continue
            if -1.0 <= ln[0] - x1 <= HEAD_GAP * body:
                where, led = "line-head", b
                break
        if where == "other" and any(t[0] <= cx <= t[2] and t[1] <= cy <= t[3] for t in tables):
            where = "table"
        read = any(m["bbox"][0] <= cx <= m["bbox"][2] and m["bbox"][1] <= cy <= m["bbox"][3] and m.get("placed")
                   and m["kind"] != "unknown" for m in r.get("marks", []))
        # Written after the very line it leads: the item is cut in two.
        after_own = led is not None and led["o"] < f["o"]
        out.append({"where": where, "read_as_mark": read, "after_own_line": after_own, "sig": f["sig"], "b": f["b"]})
    return out


def report(screen_path, convert_path=None):
    rows = _rows(screen_path)
    S = [r for r in rows if "error" not in r]
    print("SCREEN: %d pages of %d documents (%d documents failed to read); held-out pages %d" % (
        len(S), len({r["doc"] for r in S}), sum(1 for r in rows if "error" in r), sum(r["held_out"] for r in S)))
    word = lambda x, r: x["kind"] == "word" and _body_like(x, r["w"])
    multi = lambda x, r: word(x, r) and x["group_lines"] >= 2
    for title, pred in (("side label of words beside a body line", word), ("... whose group runs two lines or more", multi)):
        pages = [r for r in S if any(pred(x, r) for x in r["labels"])]
        print("F2 %-44s pages %5d (held-out %d) | documents %4d (held-out %d) | insurers %3d" % (
            title, len(pages), sum(r["held_out"] for r in pages), len({r["doc"] for r in pages}),
            len({r["doc"] for r in pages if r["held_out"]}), len({r["insurer"] for r in pages})))
    words = collections.Counter()
    for r in S:
        if not r["held_out"]:
            for x in r["labels"]:
                if multi(x, r):
                    words[x["text"].lower()] += 1
    print("   distinct label wordings (tuned-on, group of two lines or more): %d; commonest: %s" % (
        len(words), ", ".join("%s %d" % kv for kv in words.most_common(30))))

    per_doc = collections.defaultdict(collections.Counter)
    for r in S:
        for d in r["draws"]:
            if d["head"]:
                per_doc[r["doc"]][d["sig"]] += 1
    rep = {doc: {s: n for s, n in c.items() if n >= 3} for doc, c in per_doc.items()}
    rep = {d: c for d, c in rep.items() if c}
    held_docs = {r["doc"] for r in S if r["held_out"]}
    kinds = collections.Counter(s.split("|")[0] for c in rep.values() for s in c)
    pages = [r for r in S if r["doc"] in rep and any(d["head"] and d["sig"] in rep[r["doc"]] for d in r["draws"])]
    print("F3 small drawing leading a line, 3+ times in its document: documents %d (held-out %d) | insurers %d | pages %d" % (
        len(rep), len(set(rep) & held_docs), len({r["insurer"] for r in S if r["doc"] in rep}), len(pages)))
    print("   shapes by what the mark reader calls them (document x shape): %s" % dict(kinds.most_common()))
    unread = {d for d, c in rep.items() if any(s.split("|")[0] == "unknown" for s in c)}
    print("   documents with an UNREAD repeated line-head drawing: %d (held-out %d), insurers %d" % (
        len(unread), len(unread & held_docs), len({r["insurer"] for r in S if r["doc"] in unread})))
    print("   pages the conversion stage would take: %d" % sum(1 for r in S if flagged(r)))

    if not convert_path:
        return
    crow = _rows(convert_path)
    C = [r for r in crow if "error" not in r and "blocks" in r]
    print("\nCONVERTED: %d pages of %d documents (errors %d)" % (
        len(C), len({r["doc"] for r in C}), sum(1 for r in crow if "error" in r)))
    outcomes = collections.Counter()
    pattern_pages, fault_pages = [], []
    impure = collections.Counter()
    for r in C:
        o = label_outcomes(r)
        impure.update(x["outcome"] for x in o if x["purity"] < PURITY)
        o = [x for x in o if x["purity"] >= PURITY]
        if not o:
            continue
        pattern_pages.append(r)
        c = collections.Counter(x["outcome"] for x in o)
        outcomes.update(c)
        if c["after"]:
            fault_pages.append(r)
    print("F2 side labels as written: %s   (set aside, in a column of long lines: %s)" % (dict(outcomes), dict(impure)))
    print("   pages with a side label %d; with a label written AFTER its first line %d (held-out %d) | documents %d | insurers %d" % (
        len(pattern_pages), len(fault_pages), sum(r["held_out"] for r in fault_pages), len({r["doc"] for r in fault_pages}),
        len({r["insurer"] for r in fault_pages})))
    print("   fault pages by insurer (tuned-on): %s" % dict(collections.Counter(r["insurer"] for r in fault_pages if not r["held_out"]).most_common()))

    # One icon, however the layout model boxed each copy: grouped per document, each copy joining the first group
    # whose first member it matches.
    groups = collections.defaultdict(list)          # doc -> [[representative sig, count]]
    all_ph = []
    for r in C:
        ph = icon_placeholders(r)
        for x in ph:
            for g in groups[r["doc"]]:
                if same_icon(g[0], x["sig"]):
                    g[1] += 1
                    x["group"] = g
                    break
            else:
                g = [x["sig"], 1]
                groups[r["doc"]].append(g)
                x["group"] = g
        all_ph.append((r, ph))
    where = collections.Counter()
    n_total = n_rep = 0
    rep_pages, rep_docs, rep_ins = set(), set(), set()
    for r, ph in all_ph:
        for x in ph:
            n_total += 1
            repeated = x["group"][1] >= 3
            where[(x["where"], "read as a mark too" if x["read_as_mark"] else "not read", "repeated" if repeated else "single",
                   "after its own line" if x["after_own_line"] else "")] += 1
            if repeated and x["where"] in ("line-head", "table"):
                n_rep += 1
                rep_pages.add((r["doc"], r["page"]))
                rep_docs.add(r["doc"])
                rep_ins.add(r["insurer"])
    print("F3 mark-sized picture placeholders written: %d; repeated 3+ in the document, at a line's head or in a table: %d" % (n_total, n_rep))
    print("   on pages %d | documents %d | insurers %d" % (len(rep_pages), len(rep_docs), len(rep_ins)))
    for k, n in sorted(where.items(), key=lambda kv: -kv[1]):
        print("     %-70s %d" % (" / ".join(p for p in k if p), n))


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
        everything = "--all" in sys.argv
        # Paths come back from the population, never from the screen's file (which names held-out documents by hash).
        which = sys.argv[sys.argv.index("--pop") + 1]
        paths = {j[5]: (j[1], j[3], j[4]) for j in jobs(which)}
        per_doc = collections.defaultdict(list)
        screened = [r for r in (json.loads(line) for line in open(src, encoding="utf-8")) if "error" not in r]
        cap = int(sys.argv[sys.argv.index("--per-doc") + 1]) if "--per-doc" in sys.argv else None
        if cap:
            # The pages likeliest to show each shape, up to `cap` a document for each: a document's answer, not every page.
            head_sigs = collections.defaultdict(collections.Counter)
            for r in screened:
                for d in r["draws"]:
                    if d["head"]:
                        head_sigs[r["doc"]][d["sig"]] += 1

            def f2score(r):
                xs = [x for x in r["labels"] if x["kind"] == "word" and _body_like(x, r["w"])]
                edges = collections.Counter(round(x["L"][0]) for x in xs)
                return sum((2 if x["group_lines"] >= 2 else 1) for x in xs if edges[round(x["L"][0])] >= 2) + 0.1 * len(xs)

            def f3score(r):
                n = sum(1 for d in r["draws"] if d["head"] and head_sigs[r["doc"]][d["sig"]] >= 3)
                on_page = collections.Counter(d["sig"] for d in r["draws"])
                return n + sum(k for k in on_page.values() if k >= 3)

            by_doc = collections.defaultdict(list)
            for r in screened:
                by_doc[r["doc"]].append(r)
            for doc, rs in by_doc.items():
                take = set()
                for score in (f2score, f3score):
                    ranked = sorted((r for r in rs if score(r) > 0), key=lambda r: -score(r))
                    take.update(r["page"] for r in ranked[:cap])
                if take:
                    per_doc[doc] = sorted(take)
        for r in screened:
            if cap:
                break
            if everything or flagged(r):
                per_doc[r["doc"]].append(r["page"])
        todo = [(k, paths[k][0], sorted(v), paths[k][1], paths[k][2]) for k, v in per_doc.items()]
        # big documents first, so the pool does not end on one long tail
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
