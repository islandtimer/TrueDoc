"""How many icons in a document carry meaning, and what could tell us what they mean?

An icon earns a place in the output only when deleting it would lose a distinction the document
is making. Beside text that already names it ("$ Limit:", "house Home") it is illustration: the
words carry the meaning. Alone in a table cell, where its neighbours show a different symbol, it
*is* the content - which is how the Huddle policy's benefit table came out with empty cells.

This counts three things per document, to size the work before any of it is built:

  1. How many DISTINCT icons the document uses. The PDF says so itself: the same icon is almost
     always the same image object reused, so its xref is an exact identity key and nothing has to
     be rendered. Vector marks get a signature of their size, colour and path count instead.
  2. How many of those are LOAD-BEARING: they stand alone (no text beside them) and the document
     uses a contrasting set (more than one icon of that size), so the choice between them carries
     information.
  3. Which rung of the EVIDENCE LADDER is available for naming them: a legend block that pairs
     symbols with sentences, or a self-describing occurrence where the icon sits beside its own
     label somewhere in the document, which is what lets an unlabelled use elsewhere be resolved.

    python bench/tools/icon_census.py <folder of pdfs> [--limit N] [--out file.tsv]

Writes one row per document plus a summary. Reads only; nothing is converted or scored.
"""
from __future__ import annotations

import argparse
import collections
import glob
import os
import sys
import time

import pymupdf

# An icon is small and roughly square. The bounds are generous because a page laid out at
# 1920x1080 draws everything larger; the size is compared with the page later.
_MIN_SIDE = 4.0
_MAX_SIDE = 0.09          # of the page's long side
_ASPECT = (0.55, 1.8)
_MIN_PAGES = 3            # a scheme symbol recurs; decoration lives on one page
_MIN_COMMANDS = 3         # a single line, rectangle or quad is not an icon

# Words that announce a legend. A candidate still has to look like one to count.
_LEGEND_CUES = (
    "symbol", "symbols", "legend", "key to", "these icons", "icons used",
    "what the icons", "we use the following", "have special meanings",
)
_MEANS = ("means", "shows", "indicates", "represents", "tells you", "this is", "you are")


def _page_icons(page, long_side):
    """Icon candidates on one page: (identity, bbox, kind)."""
    out = []
    limit = _MAX_SIDE * long_side
    try:
        for im in page.get_image_info(xrefs=True):
            b = im["bbox"]
            w, h = b[2] - b[0], b[3] - b[1]
            if not (_MIN_SIDE <= w <= limit and _MIN_SIDE <= h <= limit):
                continue
            if not (_ASPECT[0] <= w / max(h, 0.1) <= _ASPECT[1]):
                continue
            out.append(("img:%s" % im.get("xref", 0), b, "image"))
    except Exception:
        pass
    try:
        for d in page.get_drawings():
            r = d.get("rect")
            if r is None:
                continue
            w, h = r.width, r.height
            if not (_MIN_SIDE <= w <= limit and _MIN_SIDE <= h <= limit):
                continue
            if not (_ASPECT[0] <= w / max(h, 0.1) <= _ASPECT[1]):
                continue
            if d.get("fill") is None and d.get("color") is None:
                continue
            # Identity has to be the SHAPE, not the size: the same tick drawn at 21 and at 24
            # points is one icon, and keying on exact size split one document's six symbols into
            # three hundred. The drawing commands ("l" line, "c" curve, "re" rectangle, "qu"
            # quad) are size-invariant, so their sequence plus a coarse colour is the key.
            items = d.get("items") or ()
            kinds = "".join(str(it[0]) for it in items)[:40]
            fill = tuple(round(float(v), 1) for v in (d.get("fill") or ())) or None
            line = tuple(round(float(v), 1) for v in (d.get("color") or ())) or None
            aspect = round((w / max(h, 0.1)) * 4) / 4.0
            sig = "vec:%s:%s:%s:%s" % (kinds, fill, line, aspect)
            out.append((sig, (r.x0, r.y0, r.x1, r.y1), "vector"))
    except Exception:
        pass
    return out


def _labelled(icon_box, words, gap):
    """Is there text right beside this icon that could be naming it?

    Text on the icon's own line, starting within `gap` to its right (or ending within `gap` to
    its left). That is the shape of "house Home" and of a legend row, and it is what makes an
    occurrence redundant as content and useful as evidence.
    """
    x0, y0, x1, y1 = icon_box
    mid = (y0 + y1) / 2.0
    best = None
    for wx0, wy0, wx1, wy1, text in words:
        if not text.strip():
            continue
        if not (wy0 - 2 <= mid <= wy1 + 2):
            continue
        if x1 <= wx0 <= x1 + gap:
            if best is None or wx0 < best[0]:
                best = (wx0, text)
        elif x0 - gap <= wx1 <= x0:
            if best is None:
                best = (wx1, text)
    return best[1] if best else None


def _looks_like_a_legend(text, icons, labels):
    """A block that pairs symbols with explanations, and says so."""
    low = text.lower()
    if not any(c in low for c in _LEGEND_CUES):
        return False
    if len(icons) < 2:
        return False
    # at least two icons explained by something sentence-shaped
    explained = sum(1 for lab in labels if lab and (len(lab) > 3 or any(m in low for m in _MEANS)))
    return explained >= 2


def survey(pdf_path):
    try:
        doc = pymupdf.open(pdf_path)
    except Exception:
        return None
    ids = collections.Counter()          # identity -> times seen
    alone = collections.Counter()        # identity -> times seen with no text beside it
    named = collections.defaultdict(collections.Counter)  # identity -> short labels seen beside it
    sizes = collections.defaultdict(set)  # rounded size -> identities of that size
    on_pages = collections.defaultdict(set)  # identity -> which pages it appears on
    on_legend = set()                    # identities explained on a legend page
    legend_pages = []
    pages = 0
    try:
        for pno, page in enumerate(doc):
            pages += 1
            r = page.rect
            long_side = max(r.width, r.height) or 792.0
            icons = _page_icons(page, long_side)
            if not icons:
                continue
            try:
                words = [(w[0], w[1], w[2], w[3], w[4]) for w in page.get_text("words")]
            except Exception:
                words = []
            gap = 0.06 * long_side
            labels = []
            for ident, box, _kind in icons:
                ids[ident] += 1
                on_pages[ident].add(pno)
                sizes[(round(box[2] - box[0]), round(box[3] - box[1]))].add(ident)
                lab = _labelled(box, words, gap)
                labels.append(lab)
                # Text beside an icon plays one of two opposite roles, and they look identical
                # on the page. "house Home" NAMES the icon; "tick Loss or damage caused by an
                # animal" is the statement the icon MARKS. The tell is repetition: a name is
                # short and recurs with that icon, a marked statement is different every time.
                if lab and len(lab) <= 24 and len(lab.split()) <= 3:
                    named[ident][lab] += 1
                else:
                    alone[ident] += 1
            if len(legend_pages) < 3:
                try:
                    text = page.get_text()
                except Exception:
                    text = ""
                if _looks_like_a_legend(text, icons, labels):
                    legend_pages.append(pno + 1)
                    # Rung 1 evidence: these symbols are explained by the document itself. The
                    # explanation is a sentence, not a short name, so it never looks like a
                    # label - it has to be collected here or the legend counts for nothing.
                    for ident, _b, _k in icons:
                        on_legend.add(ident)
    except Exception:
        pass
    doc.close()
    if not ids:
        return dict(pages=pages, distinct=0, load_bearing=0, named=0, legend=0, occurrences=0)
    # A symbol scheme recurs through the document; decoration lives on one page. Counting every
    # small shape made one policy look like it used 169 symbols, when 67 of them appeared exactly
    # once and the rest were rules and filled quads. A scheme symbol has to have some structure
    # (a single line or quad is not an icon) and has to turn up on several different pages.
    scheme = {i for i in ids
              if len(on_pages[i]) >= _MIN_PAGES
              and (i.startswith("img:") or len(i.split(":")[1]) >= _MIN_COMMANDS)}
    # Load-bearing: stands alone somewhere, and belongs to a contrasting set - another scheme
    # icon of the same size is used in the document, so the choice between them carries meaning.
    contrasting = {i for group in sizes.values() if len(group & scheme) > 1 for i in (group & scheme)}
    load = [i for i in scheme if alone[i] > 0 and i in contrasting]
    # Rung 1 or 2 of the ladder: the icon is explained on a legend page, or somewhere in the
    # document it sits beside a short label that recurs - which is what lets an unlabelled use
    # elsewhere be resolved without a model.
    by_legend = {i for i in load if i in on_legend}
    by_label = set()
    for i in load:
        best = named[i].most_common(1)
        if best and best[0][1] >= 2:
            by_label.add(i)
    ids = {i: n for i, n in ids.items() if i in scheme}
    return dict(
        pages=pages,
        distinct=len(ids),
        load_bearing=len(load),
        named=len(by_legend | by_label),
        by_legend=len(by_legend),
        by_label=len(by_label),
        legend=len(legend_pages),
        occurrences=sum(ids.values()),
        distinct_raw=len(on_pages),
        legend_pages=legend_pages,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    pdfs = sorted(glob.glob(os.path.join(args.folder, "**", "*.pdf"), recursive=True))
    if args.limit:
        pdfs = pdfs[: args.limit]
    out = open(args.out, "w", encoding="utf-8", newline="\n") if args.out else sys.stdout
    print("document\tpages\ticon_uses\tdistinct\tload_bearing\tload_named\tlegend_pages", file=out)
    started = time.time()
    docs = with_icons = with_load = with_legend = 0
    dist_sum = load_sum = named_sum = leg_sum = lab_sum = 0
    for i, pdf in enumerate(pdfs):
        s = survey(pdf)
        if s is None:
            continue
        docs += 1
        print("%s\t%d\t%d\t%d\t%d\t%d\t%s" % (os.path.basename(pdf)[:70], s["pages"], s["occurrences"],
                                              s["distinct"], s["load_bearing"], s["named"],
                                              ",".join(str(p) for p in s.get("legend_pages", [])) or "-"), file=out)
        if s["distinct"]:
            with_icons += 1
            dist_sum += s["distinct"]
        if s["load_bearing"]:
            with_load += 1
            load_sum += s["load_bearing"]
            named_sum += s["named"]
            leg_sum += s.get("by_legend", 0)
            lab_sum += s.get("by_label", 0)
        if s["legend"]:
            with_legend += 1
        if out is not sys.stdout and (i + 1) % 50 == 0:
            out.flush()
            print("  %d/%d documents, %.0f s" % (i + 1, len(pdfs), time.time() - started), file=sys.stderr, flush=True)
    print("", file=out)
    print("documents read: %d in %.0f s" % (docs, time.time() - started), file=out)
    print("documents using icons at all: %d (%.0f%%)" % (with_icons, 100.0 * with_icons / max(docs, 1)), file=out)
    print("  mean distinct icons in those: %.1f" % (dist_sum / max(with_icons, 1)), file=out)
    print("documents with LOAD-BEARING icons: %d (%.0f%%)" % (with_load, 100.0 * with_load / max(docs, 1)), file=out)
    print("  mean load-bearing icons in those: %.1f" % (load_sum / max(with_load, 1)), file=out)
    print("  of those load-bearing icons, EXPLAINED somewhere in their own document: %d of %d (%.0f%%)"
          % (named_sum, load_sum, 100.0 * named_sum / max(load_sum, 1)), file=out)
    print("     rung 1, on a legend block: %d      rung 2, by a short label beside them: %d" % (leg_sum, lab_sum), file=out)
    print("     rungs 1-2 unavailable (would need convention or a model): %d" % (load_sum - named_sum), file=out)
    print("documents with a legend block: %d (%.0f%%)" % (with_legend, 100.0 * with_legend / max(docs, 1)), file=out)
    if out is not sys.stdout:
        out.close()


if __name__ == "__main__":
    main()
