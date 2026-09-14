"""Pages whose own text layer has lost letters to ligatures: words that are no word until an "f" is expanded.

RAA's landlord PDS page 22 maps its ff and fi ligatures to a single "f", so the file itself reads "ofer", "fnd" and
"Certifcate". A word the common-words list does not know, which becomes a word it knows when one of its f's is read as
ff, fi, fl, ffi or ffl, is the signature. This counts such words per page over the insurance set's pages and the Key
Facts Sheets' pages 1 and 2, reading PDFium's text for each, and lists the pages that have any, with examples. On 15
September: 405 pages and 231,362 words, and only RAA's page 22 had any (4) - a clean page-level signal, with nothing on
the other 404 pages that a detector built on it would have flagged.

usage (repo root): lossy_ligatures.py [--min N]
"""
import collections
import json
import os
import re
import sys

import pypdfium2 as pdfium

sys.stdout.reconfigure(encoding="utf-8")
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "bench", "tools"))
with open(os.path.join(REPO, "truedoc", "data", "en_common_words.txt"), encoding="utf-8") as fh:
    VOCAB = {w.strip().lower() for w in fh if w.strip()}
WORD = re.compile("[A-Za-z]+")
EXPANSIONS = ("ff", "fi", "fl", "ffi", "ffl")


def repair(token: str) -> str | None:
    low = token.lower()
    if low in VOCAB or "f" not in low or len(low) < 3:
        return None
    for i, ch in enumerate(low):
        if ch != "f":
            continue
        for e in EXPANSIONS:
            candidate = low[:i] + e + low[i + 1:]
            if candidate in VOCAB:
                return candidate
    return None


def page_text(path: str, number: int) -> str:
    doc = pdfium.PdfDocument(path)
    try:
        if number > len(doc):
            return ""
        page = doc[number - 1]
        tp = page.get_textpage()
        try:
            return tp.get_text_range()
        finally:
            tp.close()
            page.close()
    finally:
        doc.close()


def pages():
    with open(os.path.join(REPO, "bench", "out", "insurance_set", "manifest.json"), encoding="utf-8") as fh:
        manifest = json.load(fh)
    items = manifest if isinstance(manifest, list) else next(v for v in manifest.values() if isinstance(v, list))
    for e in items:
        yield "insurance", e["pdf"], e["page"]
    from kfs_grade import sheets
    for _insurer, path in sheets():
        for n in (1, 2):
            yield "kfs", path, n


def main() -> None:
    minimum = int(sys.argv[sys.argv.index("--min") + 1]) if "--min" in sys.argv else 1
    flagged, scanned, words_total = [], 0, 0
    for kind, path, n in pages():
        text = page_text(path, n)
        if not text:
            continue
        scanned += 1
        tokens = WORD.findall(text)
        words_total += len(tokens)
        hits = collections.Counter()
        for t in tokens:
            fixed = repair(t)
            if fixed:
                hits[(t, fixed)] += 1
        if sum(hits.values()) >= minimum:
            flagged.append((sum(hits.values()), kind, os.path.basename(path), n, len(tokens), hits))
    flagged.sort(key=lambda x: -x[0])
    print(f"{scanned} pages read, {words_total} words; {len(flagged)} page(s) with at least {minimum} such word(s)")
    for count, kind, name, n, ntok, hits in flagged[:40]:
        examples = ", ".join(f"{t}->{r}" + (f" x{k}" if k > 1 else "") for (t, r), k in hits.most_common(6))
        print(f"  {count:3d} of {ntok:4d} words  {kind:9s} {name[:48]} p{n}: {examples}")


if __name__ == "__main__":
    main()
