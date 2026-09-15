"""Page-number candidates that do not count pages: "page N" lines the page-number rule drops though N does not fit the
page numbers printed on the pages beside it.

classify/blocks.py marks a block reading just "page N", "N", "N of M" or a roman numeral as the page's own number when
it sits in the top or bottom strip, and the renderer leaves it out. Budget Direct's home PDS (PDF page 8) ends its
Landlord Options card with the pointer "page 52", 41pt above the bottom edge: dropped, while "page 53" 28pt higher
survives. A page number counts pages, so the pages beside it print theirs at the same offset from the page's index
(Budget Direct prints 4, 5, 7, 8 at the top of PDF pages 6, 7, 9, 10: offset -2; and 6 on page 8). This lists every
candidate whose nearest numbered page before and nearest numbered page after (within two pages) agree on an offset the
candidate does not fit, and counts the candidates that do fit one.

usage: folio_pointer_census.py library | insurance [--workers 2]     (truedoc from PYTHONPATH)
"""
import concurrent.futures
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding="utf-8")

REACH = 2
FIRST_INT = re.compile(r"\d{1,4}")


def strip_lines(textpage, height: float) -> list[tuple[float, float, float, str]]:
    """Lines of text in the top and bottom strips, as (y0, y1, x0, text) measured from the top of the page."""
    zone = 0.09 * height
    pieces = []
    for i in range(textpage.count_rects()):
        left, bottom, right, top = textpage.get_rect(i)
        y0, y1 = height - top, height - bottom
        if y1 <= zone * 1.3 + 12 or y0 >= (height - zone) * 0.97 - 12:
            words = " ".join(textpage.get_text_bounded(left, bottom, right, top).split())
            if words:
                pieces.append([y0, y1, left, right, words])
    pieces.sort(key=lambda p: ((p[0] + p[1]) / 2, p[2]))
    lines = []
    for p in pieces:
        h = max(1.0, p[1] - p[0])
        cy = (p[0] + p[1]) / 2
        for line in lines:
            lh = max(1.0, line[1] - line[0])
            if abs((line[0] + line[1]) / 2 - cy) <= 0.5 * min(h, lh) and -2.0 <= p[2] - line[3] <= 1.5 * max(h, lh):
                line[0], line[1] = min(line[0], p[0]), max(line[1], p[1])
                line[3] = max(line[3], p[3])
                line[4] = line[4] + " " + p[4]
                break
        else:
            lines.append(p)
    return [(l[0], l[1], l[2], l[4]) for l in lines
            if l[1] <= zone * 1.3 or l[0] >= (height - zone) * 0.97]


def scan_file(path: str):
    import pypdfium2 as pdfium
    from truedoc.classify.blocks import _PAGE_NUMBER
    try:
        doc = pdfium.PdfDocument(path)
    except Exception:
        return path, 0, [], 0, 1
    n = len(doc)
    cands: dict[int, list] = {}
    errors = 0
    for index in range(n):
        try:
            page = doc[index]
            _, height = page.get_size()
            found = []
            for y0, y1, x0, text in strip_lines(page.get_textpage(), height):
                if _PAGE_NUMBER.match(text):
                    m = FIRST_INT.search(text)
                    found.append((int(m.group()) if m else None, text, round(y0, 1), round(x0, 1)))
            if found:
                cands[index + 1] = found
        except Exception:
            errors += 1
    flagged, fitting = [], 0
    for p, found in cands.items():
        before = next((q for q in range(p - 1, p - 1 - REACH, -1) if any(v is not None for v, *_ in cands.get(q, []))), None)
        after = next((q for q in range(p + 1, p + 1 + REACH) if any(v is not None for v, *_ in cands.get(q, []))), None)
        if before is None or after is None:
            continue
        offsets_before = {v - before for v, *_ in cands[before] if v is not None}
        offsets_after = {v - after for v, *_ in cands[after] if v is not None}
        shared = offsets_before & offsets_after
        if not shared:
            continue
        for v, text, y0, x0 in found:
            if v is None:
                continue
            if v - p in shared:
                fitting += 1
            else:
                own = [t for w, t, *_ in found if w is not None and w - p in shared]
                flagged.append((p, text, y0, x0, sorted(shared), [t for _, t, *_ in cands[before]],
                                [t for _, t, *_ in cands[after]], own))
    return path, n, flagged, fitting, errors


def main() -> None:
    import joined_rules_census as jr
    args = sys.argv[1:]
    workers = int(args[args.index("--workers") + 1]) if "--workers" in args else 2
    names = [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or args[i - 1] != "--workers")]
    for name in names:
        paths = sorted({path for path, _ in jr.tasks_for(name)})
        pages = errors = fitting = 0
        flagged = []
        with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
            for path, n, hits, fit, err in pool.map(scan_file, paths, chunksize=4):
                pages += n
                errors += err
                fitting += fit
                flagged.extend((path, *h) for h in hits)
        with_own = sum(1 for f in flagged if f[-1])
        print(f"== {name}: {len(paths)} files, {pages} pages ({errors} unread); {fitting} candidate(s) fit the numbers "
              f"beside them; {len(flagged)} do not, on {len({(f[0], f[1]) for f in flagged})} page(s) in "
              f"{len({f[0] for f in flagged})} file(s); {with_own} of those on a page whose own number was found",
              flush=True)
        for path, p, text, y0, x0, shared, before, after, own in flagged[:60]:
            shown = path[len(jr.LIB) + 1:] if path.startswith(jr.LIB) else os.path.basename(path)
            print(f"   {shown[:70]} p{p}: {text!r} at y{y0} x{x0}; offset {shared}; before {before[:3]} after {after[:3]}; "
                  f"own {own[:2]}", flush=True)


if __name__ == "__main__":
    main()
