"""When the render check overturns a "covered" verdict, was it looking at the covered text's ink?

D011 keeps text a reader cannot see out of the body. `_Visibility.reason` judges a character
"covered" when an opaque fill is painted over it later, and `_Visibility.verify` then renders the
run's box: a flat patch confirms the verdict, contrast overturns it (paint order can mislead).

18 September 2026, a GIO Key Facts Sheet: the word "entered" is in the PDF under the row's fill,
and the visible sentence "the insured address with your consent." is printed over the same spot.
The patch shows contrast - the *other* text's - so the correct verdict was overturned and
"entered" went into the body. This census sizes that: for every run judged covered (or the same
colour as its background) and then un-hidden by the render, what share of its characters sit
under another, visible character?

Text layer only (no layout model, no tables), so it is quick; a worker pool; one JSON line a
run. Key Facts Sheets that are held out are counted and their words are not written.

usage (repo root): covered_overprint_census.py <out.jsonl> bench|kfs|insurance [workers]
"""
import concurrent.futures
import glob
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "bench", "tools"))


def _install():
    from truedoc.extract import textlayer
    vis = textlayer._Visibility
    if getattr(vis, "_census", False):
        return textlayer
    vis._census = True
    reason0, verify0 = vis.reason, vis.verify

    def reason(self, ch, origin):
        self.__dict__.setdefault("_all_chars", []).append(ch)
        verdict = reason0(self, ch, origin)
        if not verdict and not ch.text.isspace() and ch.size >= 1.0:
            # Door B: a later opaque fill covers the character's INK though not 0.9 of its font box,
            # which is taller than the ink in it. Ink is taken as the em from 0.22 below the
            # baseline to 0.75 above it, inside the character's own box.
            info = self._span_at.get((round(origin[0] * 2), round(origin[1] * 2)))
            seq = info["seqno"] if info is not None else -1
            if seq >= 0:
                from truedoc.model import BBox
                top, bottom = max(ch.bbox.y0, origin[1] - 0.75 * ch.size), min(ch.bbox.y1, origin[1] + 0.22 * ch.size)
                if bottom - top > 1.0:
                    ink = BBox(ch.bbox.x0, top, ch.bbox.x1, bottom)
                    if any(s > seq and ink.overlap_fraction(rect) >= 0.9 for s, rect, _kind, _colour in self.cover):
                        self.__dict__.setdefault("_ink_covered", []).append(ch)
        return verdict

    def verify(self, pdf_page, M):
        runs = [(r["text"], r["reason"], r["_chars"]) for r in self._runs() if r["reason"] in ("covered", "same-colour")]
        verify0(self, pdf_page, M)
        found = []
        for text, why, chars in runs:
            unhidden = all(not c.hidden for c in chars)
            mine = {id(c) for c in chars}
            others = [c for c in self.__dict__.get("_all_chars", []) if id(c) not in mine and not c.hidden and not c.text.isspace()]
            inked = [c for c in chars if not c.text.isspace()]
            under = sum(1 for c in inked if any(c.bbox.overlap_fraction(o.bbox) >= 0.5 for o in others))
            found.append({"text": text[:80], "reason": why, "unhidden": unhidden, "chars": len(inked),
                          "overprinted": round(under / max(len(inked), 1), 2)})
        # Door B's characters, gathered into runs along a line, and what the render says of each.
        from truedoc.model import BBox
        runs_b, last = [], None
        for c in self.__dict__.get("_ink_covered", []):
            if last is not None and abs(c.bbox.y0 - last.bbox.y0) < 2.0 and -1.0 < c.bbox.x0 - last.bbox.x1 < 3.0 * max(c.size, 1.0):
                runs_b[-1].append(c)
            else:
                runs_b.append([c])
            last = c
        visible = [c for c in self.__dict__.get("_all_chars", []) if not c.hidden and not c.text.isspace()]
        for chars in runs_b:
            mine = {id(c) for c in chars}
            others = [c for c in visible if id(c) not in mine]
            under = sum(1 for c in chars if any(c.bbox.overlap_fraction(o.bbox) >= 0.5 for o in others))
            box = BBox.union_all(c.bbox for c in chars)
            uniform = textlayer._renders_uniform(pdf_page, box, M) if M is None else None
            found.append({"text": "".join(c.text for c in chars)[:80], "reason": "ink-covered", "unhidden": True, "chars": len(chars),
                          "overprinted": round(under / len(chars), 2), "renders_flat": uniform})
        textlayer._CENSUS_RUNS = found

    vis.reason, vis.verify = reason, verify
    return textlayer


def census(job):
    path, page_number, label, secret = job
    textlayer = _install()
    from truedoc.extract.handle import open_pdf
    textlayer._CENSUS_RUNS = []
    try:
        pdf = open_pdf(path)
        try:
            textlayer.extract_page(pdf[page_number - 1], page_number)
        finally:
            pdf.close()
    except Exception as exc:
        return [{"page": label, "error": repr(exc)[:120]}]
    rows = []
    for r in textlayer._CENSUS_RUNS:
        if secret:
            r = dict(r, text="(held out)")
        rows.append(dict(r, page=label, held_out=secret))
    return rows or [{"page": label, "runs": 0}]


def jobs(which):
    if which == "bench":
        b = os.path.join(REPO, "bench", "data", "olmocr-bench", "bench_data", "pdfs")
        scans = {l.split("\t")[0].strip() for l in open(os.path.join(REPO, "bench", "gpu", "pages.txt"), encoding="utf-8") if l.strip()}
        for p in sorted(glob.glob(os.path.join(b, "*", "*.pdf"))):
            label = os.path.basename(os.path.dirname(p)) + "/" + os.path.basename(p)[:-4]
            if label not in scans:
                yield (p, 1, label, False)
    elif which == "kfs":
        import kfs_grade
        from truedoc.pipeline import first_pages
        for _insurer, p in kfs_grade.sheets():
            import doc_library
            for n in first_pages(p, 2):
                yield (p, n, "%s@%d" % (doc_library.relative(p), n), kfs_grade.held_out(p))
    elif which == "insurance":
        m = json.load(open(os.path.join(REPO, "bench", "out", "insurance_set", "manifest.json"), encoding="utf-8"))
        for e in (m if isinstance(m, list) else next(v for v in m.values() if isinstance(v, list))):
            yield (e["pdf"], e["page"], e["name"], False)


if __name__ == "__main__":
    out, which = sys.argv[1], sys.argv[2]
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 6
    todo = list(jobs(which))
    print(len(todo), "pages")
    with open(out, "w", encoding="utf-8") as f, concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
        for n, rows in enumerate(pool.map(census, todo, chunksize=4), 1):
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
            if n % 200 == 0:
                print(" ", n, flush=True)
    rows = [json.loads(l) for l in open(out, encoding="utf-8")]
    door_b = [r for r in rows if r.get("reason") == "ink-covered"]
    rows = [r for r in rows if r.get("reason") != "ink-covered"]
    flat = [r for r in door_b if r["renders_flat"]]
    inked_over = [r for r in door_b if not r["renders_flat"] and r["overprinted"] >= 0.5]
    print("DOOR B - ink under a later fill, font box not: %d runs on %d pages | render flat (hidden, and in the body today) %d | "
          "render shows ink and at least half overprinted by visible text %d | render shows ink, not overprinted (visible: leave) %d" % (
              len(door_b), len({r["page"] for r in door_b}), len(flat), len(inked_over), len(door_b) - len(flat) - len(inked_over)))
    for r in sorted(flat + inked_over, key=lambda r: -r["chars"])[:20]:
        print("   %-60s flat=%-5s %3d chars over %.2f  %r" % (r["page"][-60:], r["renders_flat"], r["chars"], r["overprinted"], r["text"][:44]))
    print("DOOR A")
    runs = [r for r in rows if "reason" in r]
    un = [r for r in runs if r["unhidden"]]
    over = [r for r in un if r["overprinted"] >= 0.5]
    print("pages %d | errors %d | runs judged covered or same-colour %d | kept hidden by the render %d | un-hidden %d | "
          "un-hidden while at least half overprinted by visible text %d (on %d pages)" % (
              len(todo), sum(1 for r in rows if "error" in r), len(runs), len(runs) - len(un), len(un), len(over), len({r["page"] for r in over})))
    for r in sorted(over, key=lambda r: -r["chars"])[:25]:
        print("   %-64s %-11s %3d chars %.2f  %r" % (r["page"][-64:], r["reason"], r["chars"], r["overprinted"], r["text"][:50]))
