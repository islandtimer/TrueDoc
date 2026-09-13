"""Pick the pages for the insurance test set, and render them for a blind reader.

Half the pages are drawn at random, so the eventual number is an honest estimate of the library rather
than of the parts we find interesting. The other half are chosen because the page itself draws many
horizontal rules, which is what a benefits table looks like in a product disclosure statement - that is
where meaning is densest and where the library's one known defect lived. The rule count comes from the
PDF's own drawing objects, not from anything our converter decided, so the choice does not depend on
whether we got the page right.

Renders each page large, because whoever writes the checks has to read it.

usage (repo root): insurance_pick_pages.py [how many pages] [pixels on the longest side]
"""
import glob
import json
import os
import random
import sys

import pypdfium2 as pdfium

LIBRARY = r"C:/Users/griff/OneDrive/Documents/10 Have a crack/25 InsurancePlatform/uploads/PDS Docs"
CONVERTED = os.path.join("bench", "out", "library")
OUT = os.path.join("bench", "out", "insurance_set")
HOW_MANY = int(sys.argv[1]) if len(sys.argv) > 1 else 25
LONGEST = int(sys.argv[2]) if len(sys.argv) > 2 else 2200
SEED = 20260913


def rules_for(path: str, upto: int) -> dict:
    """Horizontal rules per page, read by the converter's own drawing reader.

    A first version counted path objects straight from pypdfium2 and asked each for a bounding box it
    does not have; the exception was swallowed and every page came back with nothing. Using the reader
    that already works is both correct and honest: it is the same code that finds ruled tables.
    """
    from truedoc.math.extract import page_rules
    from truedoc.pipeline import ConvertOptions, load_document

    doc = load_document(path, ConvertOptions(layout=False, ocr=False, math=False, tables=False,
                                             marks=False, pages=list(range(1, upto + 1))))
    return {page.number: len(page_rules(page)) for page in doc.pages}


def main() -> None:
    os.makedirs(os.path.join(OUT, "pages"), exist_ok=True)
    # the documents already converted, so the same pages can be scored afterwards
    done = {os.path.splitext(os.path.basename(p))[0] for p in glob.glob(os.path.join(CONVERTED, "*", "*.md"))}
    pdfs = [p for p in glob.glob(os.path.join(LIBRARY, "**", "*.pdf"), recursive=True)
            if os.path.splitext(os.path.basename(p))[0] in done]
    print(f"{len(pdfs)} documents converted and available to sample from")

    catalogue = []
    for path in pdfs:
        try:
            doc = pdfium.PdfDocument(path)
            upto = min(len(doc), 40)
            doc.close()
            rules = rules_for(path, upto)
        except Exception as exc:
            print(f"   skipped {os.path.basename(path)[:40]}: {repr(exc)[:70]}")
            continue
        for n in range(1, upto + 1):
            catalogue.append((path, n, rules.get(n, 0)))

    print(f"{len(catalogue)} pages to choose from")

    random.seed(SEED)
    half = HOW_MANY // 2
    table_like = sorted([c for c in catalogue if c[2] >= 6], key=lambda c: -c[2])
    chosen_tables = random.sample(table_like, min(HOW_MANY - half, len(table_like))) if table_like else []
    rest = [c for c in catalogue if c not in chosen_tables]
    chosen_random = random.sample(rest, min(half, len(rest)))
    chosen = chosen_tables + chosen_random

    manifest = []
    for path, page_no, rules in chosen:
        stem = os.path.splitext(os.path.basename(path))[0]
        name = f"{stem}__p{page_no}"
        out = os.path.join(OUT, "pages", name + ".png")
        if not os.path.exists(out):
            doc = pdfium.PdfDocument(path)
            try:
                page = doc[page_no - 1]
                scale = LONGEST / max(page.get_width(), page.get_height())
                page.render(scale=scale).to_pil().save(out)
            finally:
                doc.close()
        manifest.append({"name": name, "pdf": path, "page": page_no, "rules": rules,
                         "why": "drawn at random" if (path, page_no, rules) in chosen_random
                                else "the page draws many rules, so it is probably a table"})
    with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump({"seed": SEED, "longest_side_px": LONGEST, "pages": manifest}, fh, indent=2)
    print(f"{len(manifest)} pages rendered into {os.path.join(OUT, 'pages')}")
    print(f"   {len(chosen_tables)} chosen for their rules, {len(chosen_random)} drawn at random")


if __name__ == "__main__":
    main()
