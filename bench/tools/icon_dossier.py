"""Build the review spec for the corpus's unexplained icons: one card per distinct shape.

The census says 15,085 occurrences of load-bearing icons have no explanation anywhere in their own
document, and that they are only 171 distinct shapes. Looking at a contact sheet of those 171 showed
the structural filter is over-promoting: a large share are letters drawn as vector outlines (logos,
drop caps) rather than symbols. That is a judgement call a person makes in a second and a heuristic
argues about for a week, so this puts each shape in front of the owner with its evidence.

Each card carries the rendered crop, how much of the corpus it touches, where to look at a real
example, what TrueDoc's own mark reader makes of it, and a machine suggestion with the reason it
might be wrong. The owner's calls become the ground truth for whether the structural tests work.

    python bench/tools/icon_dossier.py --out bench/out/dossier

Writes <out>/spec.json and <out>/img/*.png. Reads only; converts and scores nothing.
"""
from __future__ import annotations

import argparse
import collections
import glob
import hashlib
import json
import os
import sys

import pymupdf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import icon_census as ic  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from truedoc import marks  # noqa: E402
from truedoc.model import BBox  # noqa: E402

import doc_library  # noqa: E402

LIB = doc_library.root()


def _neighbours(page, box, long_side):
    """How many other icon candidates sit on this one's baseline, right beside it.

    A drawn letter is never alone: letters form words, so another glyph sits within a fraction of
    its own width on the same baseline. A symbol in a table cell or beside a paragraph stands by
    itself. This is the cheap test for the letter noise the contact sheet exposed.
    """
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    mid = (y0 + y1) / 2.0
    n = 0
    for _ident, b, _k in ic._page_icons(page, long_side):
        if abs(b[0] - x0) < 0.5 and abs(b[1] - y0) < 0.5:
            continue                     # itself
        bmid = (b[1] + b[3]) / 2.0
        if abs(bmid - mid) > 0.35 * h:
            continue                     # not on the same baseline
        gap = b[0] - x1 if b[0] >= x1 else x0 - b[2]
        if -0.2 * w <= gap <= 0.6 * w:
            n += 1
    return n


def _evidence_image(page, r, path, width=760):
    """The icon enlarged, and above it the band of page it actually sits in.

    An icon in isolation cannot tell you whether it is doing any work: a tick in a table cell and a
    letter in a logo look the same on their own. The band shows the row it lives in - the cell, the
    sentence beside it, its neighbours - with the icon outlined so it can be found at a glance.
    """
    if r.width < 1 or r.height < 1:
        raise ValueError("degenerate icon box")
    # The context band: wide enough to show the row, tall enough to show the lines above and below.
    ctx = pymupdf.Rect(r.x0 - 7.0 * r.width, r.y0 - 1.8 * r.height,
                       r.x1 + 7.0 * r.width, r.y1 + 1.8 * r.height) & page.rect
    if ctx.width < 2 or ctx.height < 2:
        ctx = page.rect
    # Outline the icon on the page itself (in memory only; the file is never saved).
    page.draw_rect(r, color=(0.86, 0.15, 0.15), width=max(0.6, 0.05 * r.width))
    band = page.get_pixmap(matrix=pymupdf.Matrix(width / ctx.width, width / ctx.width),
                           clip=ctx, alpha=False, colorspace=pymupdf.csRGB)
    close = pymupdf.Rect(r.x0 - 0.18 * r.width, r.y0 - 0.18 * r.height,
                         r.x1 + 0.18 * r.width, r.y1 + 0.18 * r.height) & page.rect
    zoom = max(1.0, 190.0 / max(close.width, close.height, 1.0))
    icon = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), clip=close,
                           alpha=False, colorspace=pymupdf.csRGB)
    gap, pad = 10, 8
    h = pad + icon.height + gap + band.height + pad
    sheet = pymupdf.open()
    pg = sheet.new_page(width=width + 2 * pad, height=h)
    pg.draw_rect(pg.rect, color=(1, 1, 1), fill=(1, 1, 1))
    pg.insert_image(pymupdf.Rect(pad, pad, pad + icon.width, pad + icon.height), pixmap=icon)
    y = pad + icon.height + gap
    pg.draw_line((pad, y - gap / 2), (width + pad, y - gap / 2), color=(0.85, 0.87, 0.9), width=0.8)
    pg.insert_image(pymupdf.Rect(pad, y, pad + band.width, y + band.height), pixmap=band)
    pg.get_pixmap(matrix=pymupdf.Matrix(1.4, 1.4), alpha=False).save(path)
    sheet.close()


def collect():
    shapes = collections.Counter()
    docs = collections.defaultdict(set)
    example = {}
    for pdf in sorted(glob.glob(os.path.join(LIB, "**", "*.pdf"), recursive=True)):
        try:
            doc = pymupdf.open(pdf)
        except Exception:
            continue
        ids = collections.Counter()
        alone = collections.Counter()
        named = collections.defaultdict(collections.Counter)
        sizes = collections.defaultdict(set)
        on_pages = collections.defaultdict(set)
        on_legend = set()
        loc = {}
        for pno, page in enumerate(doc):
            long_side = max(page.rect.width, page.rect.height) or 792.0
            icons = ic._page_icons(page, long_side)
            if not icons:
                continue
            try:
                words = [(w[0], w[1], w[2], w[3], w[4]) for w in page.get_text("words")]
            except Exception:
                words = []
            gap = 0.06 * long_side
            labels = []
            for ident, box, _k in icons:
                ids[ident] += 1
                on_pages[ident].add(pno)
                sizes[(round(box[2] - box[0]), round(box[3] - box[1]))].add(ident)
                lab = ic._labelled(box, words, gap)
                labels.append(lab)
                if lab and len(lab) <= 24 and len(lab.split()) <= 3:
                    named[ident][lab] += 1
                else:
                    alone[ident] += 1
                if box[2] - box[0] > 1 and box[3] - box[1] > 1:
                    loc.setdefault(ident, (pno, list(box)))
            try:
                if ic._looks_like_a_legend(page.get_text(), icons, labels):
                    for ident, _b, _k in icons:
                        on_legend.add(ident)
            except Exception:
                pass
        scheme = {i for i in ids
                  if len(on_pages[i]) >= ic._MIN_PAGES
                  and (i.startswith("img:") or len(i.split(":")[1]) >= ic._MIN_COMMANDS)}
        contrasting = {i for g in sizes.values() if len(g & scheme) > 1 for i in (g & scheme)}
        for i in scheme:
            if alone[i] <= 0 or i not in contrasting or i not in loc:
                continue
            best = named[i].most_common(1)
            if i in on_legend or (best and best[0][1] >= 2):
                continue
            shapes[i] += ids[i]
            docs[i].add(os.path.basename(pdf))
            example.setdefault(i, (pdf, loc[i][0], loc[i][1]))
        doc.close()
    return shapes, docs, example


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="bench/out/dossier")
    args = ap.parse_args()
    img_dir = os.path.join(args.out, "img")
    os.makedirs(img_dir, exist_ok=True)

    shapes, docs, example = collect()
    print("distinct shapes: %d, occurrences: %d" % (len(shapes), sum(shapes.values())))

    items = []
    for sig, uses in shapes.most_common():
        pdf, pno, box = example[sig]
        ident = hashlib.sha1(sig.encode("utf-8")).hexdigest()[:10]
        try:
            d = pymupdf.open(pdf)
            page = d[pno]
            long_side = max(page.rect.width, page.rect.height) or 792.0
            r = pymupdf.Rect(*box)
            nb = _neighbours(page, box, long_side)
            mark = marks.classify_mark(page, BBox(*box), None)
            _evidence_image(page, r, os.path.join(args.out, "img", ident + ".png"))
            d.close()
        except Exception as e:
            print("  skipped %s: %s" % (ident, e))
            continue

        reader = mark.kind if mark else "nothing readable"
        colour = (mark.colour if mark else "") or "-"
        # The machine's proposal, and the way each one can be wrong.
        if nb >= 1:
            kind, sev = "letter-like", "low"
            verdict, rec = "not_real", "ignore"
            ev = ("Another drawn shape sits on the same baseline right beside this one (%d of them). "
                  "Letters form words; a symbol usually stands alone." % nb)
            warn = ("A symbol legitimately paired with another - a tick beside a cross in one cell, or a "
                    "row of rating dots - looks exactly like this. Check the crop before ignoring it.")
        elif reader in ("tick", "cross"):
            kind, sev = "pictogram", "high"
            verdict, rec = "real", "meaning"
            ev = "TrueDoc's mark reader identifies this as a %s (%s). Convention settles what it means." % (reader, colour)
            warn = ("The reader matches shapes, not intent. A tick used purely as a decorative bullet on "
                    "every row carries no distinction and should be ignored.")
        elif reader in ("dot", "circle", "square", "box"):
            kind, sev = "shape", "med"
            verdict, rec = "uncertain", ""
            ev = ("The mark reader calls this a %s, which names the shape but not the meaning: a filled "
                  "dot may mean 'included' or may just be a bullet." % reader)
            warn = "Shape and meaning are different questions, and only the document can settle the second."
        else:
            kind, sev = "pictogram", "high" if uses >= 200 else "med"
            verdict, rec = "real", "meaning"
            ev = "No shape the mark reader knows, and nothing in its own document explains it."
            warn = ("The structural filter over-promotes: this may be a logo fragment or decoration that "
                    "merely recurs. The crop is the evidence - trust it over this suggestion.")
        if uses >= 400:
            sev = "high"

        n_docs = len(docs[sig])
        items.append({
            "id": ident,
            "type": kind,
            "severity": sev,
            "title": "%d uses across %d document%s" % (uses, n_docs, "" if n_docs == 1 else "s"),
            "image": os.path.join("img", ident + ".png").replace("\\", "/"),
            "chips": ["neighbours: %d" % nb, "reader: %s" % reader] + ([colour] if colour != "-" else []),
            "fields": [
                {"label": "Example to look at",
                 "value": "%s, page %d" % (os.path.basename(pdf), pno + 1), "tone": "info"},
                {"label": "Reach",
                 "value": "%d occurrences in %d of the 1,176 documents" % (uses, n_docs),
                 "tone": "warn" if uses >= 200 else ""},
                {"label": "Why it is here",
                 "value": ("It recurs across pages, stands alone somewhere (no short label beside it), and "
                           "contrasts with another symbol of its size - so on the structural tests it looks "
                           "like it carries meaning. Nothing in its own document explains it."),
                 "tone": "state"},
            ],
            "guidance": ("'Carries meaning' means a reader would lose something if this were dropped, so it "
                         "needs naming - by convention or by a model. 'Safe to ignore' means the words "
                         "already carry it, or it is decoration, a logo or drawn text."),
            "verification": {
                "verdict": verdict, "confidence": "low" if verdict == "uncertain" else "med",
                "recommendation": rec, "evidence": ev, "warning": warn,
            },
        })

    spec = {
        "title": "Which of these icons carry meaning?",
        "subtitle": ("%d distinct shapes, %s occurrences, from 1,176 insurance PDS documents. Every one "
                     "recurs, stands alone somewhere, and has no explanation in its own document."
                     % (len(items), format(sum(shapes.values()), ","))),
        "eyebrow": "Machine proposes · you confirm · nothing is applied from this page",
        "storage_key": "truedoc_icons_v1",
        "export_filename": "icon_decisions.json",
        "export_note": ("A record of the owner's calls on each icon shape. Not a clearance: the conversion "
                        "path is changed by a separate step that reads this file."),
        "decisions": ["meaning", "ignore", "unsure"],
        "types": [{"key": "pictogram", "label": "Pictogram"},
                  {"key": "letter-like", "label": "Looks like a letter"},
                  {"key": "shape", "label": "Plain shape"}],
        "items": items,
    }
    with open(os.path.join(args.out, "spec.json"), "w", encoding="utf-8") as f:
        json.dump(spec, f, indent=1)
    print("wrote %d cards to %s" % (len(items), os.path.join(args.out, "spec.json")))


if __name__ == "__main__":
    main()
