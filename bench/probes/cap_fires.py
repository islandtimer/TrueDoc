"""Where the width cap fires: every character whose advance is cut back to the next character's origin.

The text reader stops a level character's box at the next character's origin when the width lookup's advance runs more
than a quarter of the size past it (`pdftext_rawdict._geometry`, 15 September) - for a font that maps its ligatures to
letters, whose "f" PDFium answers with a ligature's width (RAA's landlord PDS). This patches a logging copy into the
reader in memory and, for each page, counts the characters the cap shortened: the character and the one after it, the
font, the advance the lookup gave and the one the cap left. On reader code from before the cap it inserts the cap
itself. That is how its first version was found cutting ticks, crosses, bullets and word-final letters to half a
point on an Allianz PDS page (a line break PDFium makes up stands just after the letter before it), and how the
refined version was shown to fire on RAA's page alone of the insurance set's 25.

usage (repo root): cap_fires.py <insurance page name | pdf@page | --all> [...]
"""
import collections
import inspect
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
from truedoc.extract import pdftext_rawdict as prd  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MANIFEST = os.path.join(REPO, "bench", "out", "insurance_set", "manifest.json")
ANCHOR = "                            advance = adv_w.value * (abs(matrix.a) or 1.0)\n"
ASSIGN = "                                    advance = ox2.value - x_off - origin[0]\n"
LOGGED = ("                                    raw_api.FPDFText_GetFontInfo(tp, i, font_buf, 256, font_flags)\n"
          "                                    CAP_LOG.append((code, nxt, font_buf.value.decode('latin-1', 'replace'), advance,\n"
          "                                                    ox2.value - x_off - origin[0], drawn))\n"
          + ASSIGN)
CAP = (ANCHOR
       + "                            if (advance > 0 and i + 1 < count\n"
       + "                                    and not raw_api.FPDFText_IsGenerated(tp, i + 1)\n"
       + "                                    and raw_api.FPDFText_GetCharOrigin(tp, i + 1, ox2, oy2)\n"
       + "                                    and abs(oy2.value - oy.value) < 0.5 * max(drawn, 1.0)\n"
       + "                                    and origin[0] + 0.15 * max(drawn, 1.0) <= ox2.value - x_off\n"
       + "                                    < origin[0] + advance - 0.25 * max(drawn, 1.0)):\n"
       + "                                nxt = raw_api.FPDFText_GetUnicode(tp, i + 1)\n"
       + "                                kind = unicodedata.category(chr(nxt))\n"
       + "                                if nxt != code and kind[0] != 'M' and kind not in ('Sk', 'Lm'):\n"
       + LOGGED)


def patched_source() -> str:
    source = inspect.getsource(prd._geometry)
    if "not raw_api.FPDFText_IsGenerated(tp, i + 1)" in source:
        # the reader already has the cap: log where its own cut is made
        if source.count(ASSIGN) != 1:
            sys.exit(f"the cap's cut found {source.count(ASSIGN)} times")
        return source.replace(ASSIGN, LOGGED)
    if source.count(ANCHOR) != 1:
        sys.exit(f"the advance line found {source.count(ANCHOR)} times")
    return source.replace(ANCHOR, CAP)


def pages(args):
    manifest = json.load(open(MANIFEST, encoding="utf-8"))
    items = manifest if isinstance(manifest, list) else next(v for v in manifest.values() if isinstance(v, list))
    by_name = {e["name"]: (e["pdf"], e["page"]) for e in items}
    for a in args:
        if a == "--all":
            yield from by_name.values()
        elif "@" in a:
            path, number = a.rsplit("@", 1)
            yield path, int(number)
        else:
            yield by_name[a[:-3] if a.endswith(".md") else a]


def main() -> None:
    capped = "not raw_api.FPDFText_IsGenerated(tp, i + 1)" in inspect.getsource(prd._geometry)
    print(f"reader: {prd.__file__} ({'logging the cap it already has' if capped else 'inserting the cap'})")
    prd.__dict__["CAP_LOG"] = []
    exec(compile(patched_source(), prd.__file__, "exec"), prd.__dict__)
    fired_pages = 0
    for pdf, number in pages(sys.argv[1:]):
        prd.CAP_LOG.clear()
        prd._CACHE.clear()
        prd.build(pdf, number)
        log = list(prd.CAP_LOG)
        fired_pages += bool(log)
        print(f"== {os.path.basename(pdf)[:60]} p{number}: {len(log)} character(s) cut back")
        counts = collections.Counter((e[0], e[1], e[2]) for e in log)
        for (c, n, font), k in counts.most_common(12):
            e = next(x for x in log if (x[0], x[1], x[2]) == (c, n, font))
            print(f"   {k:3d} x {chr(c)!r} U+{c:04X} before {chr(n)!r} U+{n:04X} in {font[:32]}:"
                  f" advance {e[3]:.2f} -> {e[4]:.2f} at {e[5]:.1f}pt")
    print(f"the cap fired on {fired_pages} page(s)")


if __name__ == "__main__":
    main()
