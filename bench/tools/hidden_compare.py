"""Do the two readers hide the same text, for the same reasons? (M18, D011, D022)

`_Visibility` decides which characters a reader cannot see - drawn invisibly, painted over, or the
same colour as what lies beneath - and keeps them out of the body (D011). It was the last stage
reading through MuPDF's own devices, and its PDFium branch has the swap's usual failure mode: get
it wrong and nothing crashes, the body just gains text no reader can see, or loses text they can.

D022 asks for a quantity the two must agree on before the score is consulted. Here it is the set
of hidden runs on a page - each run's text and the reason given - so this converts a sample of
benchmark pages both ways (the text stage only, no layout model) and compares them.

    python bench/tools/hidden_compare.py [--pages 120] [--seed 11]

What to read off it: the share of pages where the two agree exactly, and the pages where they do
not, with what each side hid. A disagreement is not automatically a fault in the new branch - the
old one has its own quirks - but every one is worth a look, because neither the benchmark nor the
quick gate will show it.
"""
from __future__ import annotations

import argparse
import glob
import os
import random
import sys

import pymupdf

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BENCH = os.path.join(REPO, "bench", "data", "olmocr-bench", "bench_data")
SWITCHES = {"TRUEDOC_READER": "pdftext", "TRUEDOC_RENDERER": "pdfium", "TRUEDOC_OBJECTS": "pdfium"}


def _hidden(path: str, pdfium: bool) -> tuple[set, bool] | None:
    from truedoc.extract import render
    from truedoc.extract.textlayer import extract_page

    for k in SWITCHES:
        os.environ.pop(k, None)
    if pdfium:
        os.environ.update(SWITCHES)
    try:
        doc = pymupdf.open(path)
        try:
            page = extract_page(doc[0], 1)
            runs = {(h["text"].strip(), h["reason"]) for h in page.hidden_text if h["text"].strip()}
            return runs, bool(getattr(page.quality, "kind", "") == "ocr")
        finally:
            doc.close()
            render.close_documents()
    except Exception as exc:
        print(f"  FAILED {os.path.basename(path)}: {exc}", file=sys.stderr)
        return None
    finally:
        for k in SWITCHES:
            os.environ.pop(k, None)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=120)
    ap.add_argument("--seed", type=int, default=11)
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(BENCH, "pdfs", "*", "*.pdf")))
    random.Random(args.seed).shuffle(files)
    files = files[:args.pages]

    same = differ = 0
    runs_mu = runs_pf = runs_both = 0
    pages_with_hidden = 0
    worst: list[tuple[int, str, set, set]] = []
    for path in files:
        a = _hidden(path, False)
        b = _hidden(path, True)
        if a is None or b is None:
            continue
        ra, rb = a[0], b[0]
        if ra or rb:
            pages_with_hidden += 1
        runs_mu += len(ra)
        runs_pf += len(rb)
        runs_both += len(ra & rb)
        if ra == rb:
            same += 1
        else:
            differ += 1
            worst.append((len(ra ^ rb), os.path.basename(path), ra - rb, rb - ra))

    total = same + differ
    print(f"{total} pages, {pages_with_hidden} carrying hidden text on at least one side\n")
    print(f"  pages where both readers hide exactly the same runs: {same}/{total}")
    print(f"  hidden runs: MuPDF {runs_mu}, PDFium {runs_pf}, in both {runs_both}")
    if worst:
        print("\n  pages that differ (runs only MuPDF hid | runs only PDFium hid):")
        for n, name, only_mu, only_pf in sorted(worst, reverse=True)[:12]:
            mu_s = "; ".join(f"{t[:28]!r} ({r})" for t, r in sorted(only_mu))[:110]
            pf_s = "; ".join(f"{t[:28]!r} ({r})" for t, r in sorted(only_pf))[:110]
            print(f"    {n:3d}  {name[:44]}\n         MuPDF only : {mu_s or '-'}\n         PDFium only: {pf_s or '-'}")


if __name__ == "__main__":
    main()
