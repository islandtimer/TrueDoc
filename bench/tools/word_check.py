"""The word check (D040): is every word printed on a page either in TrueDoc's output or accounted for?

A page's printed words are read a second, independent way - PyMuPDF's text layer, not the PDFium reader TrueDoc uses -
and set against what TrueDoc wrote for that page *plus everything it says it deliberately left out of the body*: the
edge lines it records as its own decisions (running heads and feet, page numbers, imprint), and the hidden text it
lists (D011). What is left over is **unaccounted**: a word printed on the page that the conversion neither published
nor owned up to leaving out. The reverse is reported too - words TrueDoc wrote that the page does not print - because
a changed word ("artificial" written "4artificial") shows up as one lost and one added.

It does not check order, nor which cell a word landed in: a table with the right words in the wrong columns passes.
That is the second reader's job (D040). A page with no text layer has nothing to check against and is reported as such.

Normalisation, both sides alike, so that what differs is the conversion and not the spelling of the same thing:
Unicode NFKC; the ligature PyMuPDF reports with a space after it ("ﬁ xed") closed up; a word broken at a line end
joined; hyphens and soft hyphens dropped inside words; HTML entities, tags, markdown and LaTeX commands stripped from
TrueDoc's side; private-use glyphs dropped; lower case; a word is a run of letters and digits.

Held out, counted only: a document is held out if the meaning test holds it out (odd sha1 of its file name, D039) or
the Key Facts oracle does (`kfs_grade.held_out`). For those only counts are written - never a word. The sealed 19
(D030) are never touched.

usage (repo root, the project's venv):
    word_check.py <out.jsonl> --pdf <file.pdf> [--pages 1,2,3] [--workers 8]      # a document, as it arrives
    word_check.py <out.jsonl> --sample <N documents> [--seed 40] [--workers 10]     # the library, one page of each
"""
import collections
import concurrent.futures
import hashlib
import html
import json
import os
import random
import re
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

_TOKEN = re.compile(r"[^\W_]+", re.UNICODE)
_LIGATURE_GAP = re.compile("([ﬀ-ﬆ]) ")
_TAG = re.compile(r"<[^>]{1,200}>")
_LATEX = re.compile(r"\\[A-Za-z]+")
_FIGURE = re.compile(r"!\[[^\]]*\]\([^)]*\)")


def option(name, default):
    return type(default)(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default


def normalise(text: str, markup: bool = False) -> collections.Counter:
    return collections.Counter(token_list(text, markup))


def token_list(text: str, markup: bool = False) -> list[str]:
    if markup:
        text = _FIGURE.sub(" ", text)
        text = _TAG.sub(" ", text)
        text = html.unescape(text)
        text = _LATEX.sub(" ", text)
    text = _LIGATURE_GAP.sub(r"\1", text)
    text = unicodedata.normalize("NFKC", text).replace("­", "")
    text = re.sub(r"(?<=\w)-\s*\n\s*(?=\w)", "", text)          # a word broken at the end of a line
    text = re.sub(r"(?<=\w)-(?=\w)", "", text)                   # a hyphen inside a word, either side's spelling
    text = "".join(" " if 0xE000 <= ord(c) <= 0xF8FF or unicodedata.category(c) == "Cc" and c not in "\n\t" else c for c in text)
    return [t.lower() for t in _TOKEN.findall(text)]


def classify_boundaries(lines: list[list[str]], lost: collections.Counter, added: collections.Counter,
                        blob: str) -> tuple[collections.Counter, collections.Counter]:
    """Two readers can agree on every letter and break the words differently. Sort that out of `lost` and `added`.

    Glued (a fault of the conversion): an added word that is several consecutive printed words of one line run
    together - "Step 1 Understanding" written "Step1Understanding" on Key Facts Sheets whose step number stands in a
    box of its own - or a printed word with a symbol written as a character run into it ("4artificial": a Webdings
    bullet). Respaced (a fault of the reference, not of the conversion): a printed line of at least two missing words
    whose letters, run together, stand in what TrueDoc wrote or recorded - a title set with wide letter spacing is read
    in fragments by one reader ("bu", "ildin", "g") and whole by the other. Fifteen letters at least, so that a short
    line ("Cover") is never excused by turning up somewhere else on the page."""
    glued = collections.Counter()
    for a in sorted(added, key=len, reverse=True):
        for toks in lines:
            i = 0
            while added[a] > 0 and i < len(toks):
                joined, j = "", i
                while j < len(toks) and len(joined) < len(a):
                    joined += toks[j]
                    j += 1
                window = toks[i:j]
                if joined == a and len(window) > 1 and all(lost[t] >= window.count(t) for t in set(window)):
                    for t in window:
                        lost[t] -= 1
                    added[a] -= 1
                    glued[a] += 1
                    i = j
                else:
                    i += 1
    for a in list(added):
        for l in list(lost):
            if added[a] <= 0 or lost[l] <= 0 or len(a) <= len(l):
                continue
            extra = a[:len(a) - len(l)] if a.endswith(l) else (a[len(l):] if a.startswith(l) else "")
            if extra and len(extra) <= 3 and not extra.isalpha():
                n = min(added[a], lost[l])
                added[a] -= n
                lost[l] -= n
                glued[a] += n
    # Only a line most of whose words failed to match is taken for a respaced one: a letter-spaced title fails almost
    # word by word. A line TrueDoc wrote whole has at most a word or two that another line lost ("to", "insurance"), and
    # the first version of this rule handed those back, excusing three words of a torn table heading on CBA's PEDG.
    respaced = collections.Counter()
    for toks in lines:
        here = [t for t in toks if lost[t] > 0]
        line_letters = "".join(toks)
        if len(here) >= 2 and len(here) >= 0.6 * len(toks) and len(line_letters) >= 15 and line_letters in blob:
            for t in here:
                if lost[t] > 0:
                    lost[t] -= 1
                    respaced[t] += 1
    return +glued, +respaced


_SYMBOL_FONTS = ("wingding", "webding", "dingbat", "marlett", "monotypesorts")


def printed_text(page) -> str:
    """What the page prints, glyph by glyph, from PyMuPDF's raw characters.

    Not `get_text()`: that substitutes a PDF's accessibility text (/ActualText) for the glyphs it covers. CBA's home
    PEDG draws each answer of a cover table as a tick or a cross in ZapfDingbats and labels them "Applies" and "does
    not apply"; a star is labelled "asterisk". A reader sees the tick. Read that way, the first run of this check
    counted 130 "lost" words on the page where TrueDoc had written every tick and cross (21 September 2026).
    Characters set in a symbol font are marks, not words, and are left out here: TrueDoc turns them into marks.

    That accessibility text reaches even PyMuPDF's raw characters, as a span in a stand-in font ("does not apply" in
    "Times-Roman", 30 times on that page) that nothing on the page draws - its text trace, which is what is drawn,
    holds no such words - so the characters are read with `TEXT_IGNORE_ACTUALTEXT` (PyMuPDF 1.24 on), which drops it
    all and keeps the page's own spelling, broken ligatures included. What is drawn invisibly (render mode 3, or no
    opacity) is not printed either; the text trace carries the render mode, and its characters are matched to the raw
    ones by where they stand.
    """
    import pymupdf
    invisible = set()
    for t in page.get_texttrace():
        if t.get("type") == 3 or t.get("opacity", 1.0) == 0:
            for ch in t.get("chars", ()):
                x0, y0 = ch[3][0], ch[3][1]
                invisible.add((round(x0), round(y0)))
    parts = []
    turned = []
    flags = pymupdf.TEXTFLAGS_RAWDICT | getattr(pymupdf, "TEXT_IGNORE_ACTUALTEXT", 0)
    for block in page.get_text("rawdict", flags=flags).get("blocks", []):
        for line in block.get("lines", []):
            pieces = []
            for span in line.get("spans", []):
                symbol = any(k in span.get("font", "").lower().replace(" ", "").replace("-", "") for k in _SYMBOL_FONTS)
                pieces.append("".join(" " if symbol or (round(c["bbox"][0]), round(c["bbox"][1])) in invisible else c["c"]
                                      for c in span.get("chars", [])))
            # Text set on its side is broken into words differently by the two readers ("bu", "ildin", "g" against
            # "BUILDING"), so it is kept apart and judged as a run of letters (see `check_page`).
            (parts if abs(line.get("dir", (1.0, 0.0))[0]) >= 0.99 else turned).append("".join(pieces))
        parts.append("")
    return "\n".join(parts), "\n".join(turned)


_LIGATURE_LETTERS = set("fitl")


def reconcile_repairs(lost: collections.Counter, added: collections.Counter) -> collections.Counter:
    """Pair a lost word with an added one that is the same word with a ligature's letters put back.

    A text layer that maps a ligature to fewer letters than it draws spells "after" as "afer" and "certificate" as
    "certifcate"; TrueDoc reads the glyph's name and writes the word the page shows (`extract/glyph_names`). The pair is
    a repair, not a loss and an invention. Only letters a ligature holds (f, i, l, t) and at most two of them: "4" in
    front of "artificial" is not a repair, and stays reported."""
    repaired = collections.Counter()
    for a in list(added):
        for l in list(lost):
            if added[a] <= 0 or lost[l] <= 0 or not 0 < len(a) - len(l) <= 2:
                continue
            it = iter(a)
            if not all(ch in it for ch in l):                     # l is a subsequence of a
                continue
            extra = list((collections.Counter(a) - collections.Counter(l)).elements())
            if extra and set(extra) <= _LIGATURE_LETTERS:
                n = min(added[a], lost[l])
                added[a] -= n
                lost[l] -= n
                repaired[l + "->" + a] += n
    return repaired


def held_out(path: str) -> bool:
    name = os.path.basename(path)
    if int(hashlib.sha1(name.encode("utf-8")).hexdigest()[:8], 16) % 2 == 1:
        return True
    try:
        import kfs_grade
        return bool(kfs_grade.held_out(path))
    except Exception:
        return False


def check_page(job):
    path, number = job
    sys.path.insert(0, REPO)
    import pymupdf
    from truedoc.pipeline import ConvertOptions, load_document
    from truedoc.render.okf import RenderOptions, render_document
    secret = held_out(path)
    out = {"page": number, "held_out": secret}
    try:
        reference, turned_text = printed_text(pymupdf.open(path)[number - 1])
    except Exception as exc:
        return dict(out, error="reference: " + repr(exc)[:100])
    ref = normalise(reference)
    turned = normalise(turned_text)
    if sum(ref.values()) + sum(turned.values()) < 5:
        return dict(out, no_text_layer=True)
    try:
        doc = load_document(path, ConvertOptions(frontmatter=False, pages=[number]))
        body = render_document(doc, RenderOptions(frontmatter=False))
    except Exception as exc:
        return dict(out, error="conversion: " + repr(exc)[:100])
    page = doc.pages[0]
    owned = []                                              # what TrueDoc says it left out of the body, and why
    for d in page.meta.get("decisions") or []:
        owned.append((d["because"], d["text"]))
    for h in page.hidden_text:
        owned.append(("hidden: " + h["reason"], h["text"]))
    td = normalise(body, markup=True)
    accounted = collections.Counter()
    for _why, text in owned:
        accounted += normalise(text)
    lost = ref - (td + accounted)
    added = td - (ref + turned)
    repaired = reconcile_repairs(lost, added)
    lost, added = +lost, +added
    blob = re.sub(r"\W", "", unicodedata.normalize("NFKC", body + " " + " ".join(text for _why, text in owned)).lower())
    glued, respaced = classify_boundaries([token_list(l) for l in reference.splitlines()], lost, added, blob)
    lost, added = +lost, +added
    # Text on its side is judged as a run of letters: a turned stamp at the page's edge is read in pieces by one reader
    # and whole by the other, so a piece is accounted for when it stands inside what TrueDoc wrote or owned up to leaving
    # out. Only turned text is judged so loosely: in level text "a" or "2" stands inside anything.
    fragments = collections.Counter({w: n for w, n in turned.items() if w in blob})
    respaced += fragments
    lost += turned - fragments
    out.update(ref_words=sum(ref.values()) + sum(turned.values()), body_words=sum(td.values()), accounted_words=sum(accounted.values()),
               missing=sum(lost.values()), glued=sum(glued.values()), added=sum(added.values()),
               respaced=sum(respaced.values()), repaired=sum(repaired.values()),
               decisions=len(page.meta.get("decisions") or []),
               # kept though it could not be shown to run; a turned stamp is left uncounted here (it is kept nowhere)
               unchecked=sum(1 for d in page.meta.get("decisions") or [] if not d["checked"] and d.get("kept_in")),
               turned_stamps=sum(1 for d in page.meta.get("decisions") or [] if d["because"].startswith("a turned stamp")))
    if not secret:
        out.update(missing_words=sorted(lost.elements())[:60], glued_words=sorted(glued.elements())[:30],
                   added_words=sorted(added.elements())[:60], repairs=sorted(repaired)[:20],
                   owned=[(why, text[:120]) for why, text in owned][:12])
    return out


def library_sample(n, seed):
    import doc_library
    root = doc_library.root()
    sealed = {l.strip().replace("\\", "/") for l in open(os.path.join(REPO, "bench", "insurance_holdout.txt"), encoding="utf-8")
              if l.strip() and not l.startswith("#")}
    sealed_names = {os.path.basename(s) for s in sealed}
    pdfs = sorted(os.path.join(d, f).replace("\\", "/") for d, _, fs in os.walk(root) for f in fs if f.lower().endswith(".pdf"))
    pdfs = [p for p in pdfs if doc_library.relative(p) not in sealed and os.path.basename(p) not in sealed_names]
    rng = random.Random(seed)
    rng.shuffle(pdfs)
    import pypdfium2 as pdfium
    jobs = []
    for p in pdfs:
        if len(jobs) >= n:
            break
        try:
            doc = pdfium.PdfDocument(p)
            pages = len(doc)
            doc.close()
        except Exception:
            continue
        jobs.append((p, rng.randint(1, pages)))
    return jobs


if __name__ == "__main__":
    out = sys.argv[1]
    workers = option("--workers", 8)
    if "--pdf" in sys.argv:
        path = sys.argv[sys.argv.index("--pdf") + 1]
        import pypdfium2 as pdfium
        doc = pdfium.PdfDocument(path)
        count = len(doc)
        doc.close()
        wanted = [int(x) for x in option("--pages", "").split(",") if x.strip()] or list(range(1, count + 1))
        jobs = [(path, n) for n in wanted]
    else:
        jobs = library_sample(option("--sample", 100), option("--seed", 40))
    print(len(jobs), "pages to check", flush=True)
    import doc_library
    with open(out, "w", encoding="utf-8") as f, concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
        for job, r in zip(jobs, pool.map(check_page, jobs, chunksize=1)):
            r["document"] = "(held out)" if r.get("held_out") else doc_library.relative(job[0])
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    rows = [json.loads(l) for l in open(out, encoding="utf-8")]
    checked = [r for r in rows if "missing" in r]
    for half, name in ((False, "tuned-on"), (True, "held out")):
        mine = [r for r in checked if r["held_out"] == half]
        if not mine:
            continue
        print("%-9s pages %3d | printed words %6d | MISSING %4d on %3d pages | GLUED %3d on %3d pages | added %4d | "
              "respaced (the reference's) %4d | repaired %3d | unchecked edge calls %d"
              % (name, len(mine), sum(r["ref_words"] for r in mine),
                 sum(r["missing"] for r in mine), sum(1 for r in mine if r["missing"]),
                 sum(r["glued"] for r in mine), sum(1 for r in mine if r["glued"]),
                 sum(r["added"] for r in mine), sum(r["respaced"] for r in mine), sum(r["repaired"] for r in mine),
                 sum(r["unchecked"] for r in mine)))
    print("no text layer: %d | errors: %d" % (sum(1 for r in rows if r.get("no_text_layer")), sum(1 for r in rows if "error" in r)))
    for r in sorted((r for r in checked if not r["held_out"] and (r["missing"] or r["glued"])), key=lambda r: -(r["missing"] + r["glued"]))[:20]:
        print("   %-58s p%-3d missing %3d glued %2d | %s | glued: %s" % (r["document"][-58:], r["page"], r["missing"], r["glued"],
                                                                      " ".join(r["missing_words"][:10]), " ".join(r["glued_words"][:4])))
