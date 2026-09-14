"""Where the width cap would cut a glyph short, is the next character beside the glyph, or set over or under it?

The reader's width cap (`pdftext_rawdict._geometry`) stops a level glyph's box at the next character's origin when the
width lookup's advance runs more than a quarter of the size past it. Its second version stopped at any such character
the file holds, and on the benchmark 23 pages lost by it: TeX's letters were stopped at the hats, tildes and dots set
over them and a sum's limit at the sum, whose fonts map them to "b", "e", "9" and "X", and an umlaut Jönsson's font maps
to "«" put a space into the name. For every character that version cuts - reproduced from PDFium directly, without the
reader's exceptions for ligatures and unmapped codes, so on some pages it lists many more - this takes the character,
the next, whether the two share a font object, how much of the smaller glyph's height their ink boxes share, and how far
the next glyph's ink reaches past this one's, in sizes (at or below 0 it ends inside). On each of those 23 pages the
version cut a glyph at a character sharing none of its height, where all 40 of RAA's cuts share nine tenths or more. The
reach and the font do not separate them: a wide hat reaches past a narrow letter, and the letter set beside a TeX
bracket comes from another font. A folder means every PDF in it at page 1; --brief prints one line a page with cuts,
then the run's cuts by font, role, shared height and reach.

usage (repo root): stack_probe.py [--brief] <pdf>@<page> | <folder> [...]
"""
import collections
import ctypes
import glob
import os
import sys
import unicodedata

import pypdfium2 as pdfium
import pypdfium2.raw as raw

sys.stdout.reconfigure(encoding="utf-8")

BINS = ((0.01, "0"), (0.25, "<.25"), (0.5, "<.5"), (0.9, "<.9"), (9.0, ">=.9"))


def box(tp, i: int):
    left, right, bottom, top = ctypes.c_double(), ctypes.c_double(), ctypes.c_double(), ctypes.c_double()
    if not raw.FPDFText_GetCharBox(tp.raw, i, left, right, bottom, top):
        return None
    return left.value, right.value, bottom.value, top.value


def shared_height(one, two):
    if not one or not two:
        return None
    smaller = min(one[3] - one[2], two[3] - two[2])
    if smaller <= 0:
        return None
    return max(0.0, min(one[3], two[3]) - max(one[2], two[2])) / smaller


def bin_of(shared) -> str:
    if shared is None:
        return "no box"
    return next(label for edge, label in BINS if shared < edge)


def reach_of(reach) -> str:
    if reach is None:
        return "no box"
    return "past" if reach > 0 else "inside"


def font_of(tp, i: int):
    obj = raw.FPDFText_GetTextObject(tp.raw, i)
    font = raw.FPDFTextObj_GetFont(obj) if obj else None
    return font, (ctypes.cast(font, ctypes.c_void_p).value if font else None)


def page_cuts(path: str, number: int) -> list[dict]:
    buf, flags = ctypes.create_string_buffer(256), ctypes.c_int()
    cuts = []
    doc = pdfium.PdfDocument(path)
    try:
        page = doc[number - 1]
        tp = page.get_textpage()
        try:
            n = tp.count_chars()
            ox, oy = ctypes.c_double(), ctypes.c_double()
            matrix = raw.FS_MATRIX()
            adv = ctypes.c_float()
            origins, codes, generated = [], [], []
            for i in range(n):
                raw.FPDFText_GetCharOrigin(tp.raw, i, ox, oy)
                origins.append((ox.value, oy.value))
                codes.append(raw.FPDFText_GetUnicode(tp.raw, i))
                generated.append(raw.FPDFText_IsGenerated(tp.raw, i))
            for i in range(n - 1):
                if generated[i] or generated[i + 1] or not raw.FPDFText_GetMatrix(tp.raw, i, matrix):
                    continue
                if abs(matrix.b) > 1e-6 or abs(matrix.c) > 1e-6:
                    continue
                font, handle = font_of(tp, i)
                size = abs(raw.FPDFText_GetFontSize(tp.raw, i))
                if not font or not codes[i] or not raw.FPDFFont_GetGlyphWidth(font, codes[i], size, adv):
                    continue
                advance = adv.value * (abs(matrix.a) or 1.0)
                drawn = size * abs(matrix.a)
                x, y = origins[i]
                nx, ny = origins[i + 1]
                if not (abs(ny - y) < 0.5 * max(drawn, 1.0)
                        and x + 0.15 * max(drawn, 1.0) <= nx < x + advance - 0.25 * max(drawn, 1.0)):
                    continue
                try:
                    kind = unicodedata.category(chr(codes[i + 1]))
                    here = chr(codes[i])
                except ValueError:
                    continue
                if codes[i + 1] == codes[i] or kind[0] == "M" or kind in ("Sk", "Lm"):
                    continue
                if unicodedata.category(here)[0] == "M":
                    role = "mark"
                elif unicodedata.bidirectional(here) in ("R", "AL"):
                    role = "rtl"
                else:
                    role = "plain"
                _, next_handle = font_of(tp, i + 1)
                raw.FPDFText_GetFontInfo(tp.raw, i, buf, 256, flags)
                mine, theirs = box(tp, i), box(tp, i + 1)
                reach = (theirs[1] - mine[1]) / max(drawn, 1.0) if mine and theirs else None
                cuts.append({"role": role, "same": "same font" if handle == next_handle else "other font",
                             "shared": shared_height(mine, theirs), "reach": reach, "here": here,
                             "next": chr(codes[i + 1]), "font": buf.value.decode("latin-1", "replace")})
        finally:
            tp.close()
            page.close()
    finally:
        doc.close()
    return cuts


def targets(args):
    for a in args:
        if os.path.isdir(a):
            for p in sorted(glob.glob(os.path.join(a, "*.pdf"))):
                yield p, 1
        else:
            path, number = a.rsplit("@", 1)
            yield path, int(number)


def main() -> None:
    brief = "--brief" in sys.argv
    corpus = collections.Counter()
    pages = with_cuts = 0
    for path, number in targets([a for a in sys.argv[1:] if a != "--brief"]):
        pages += 1
        name = os.path.basename(path)[:50]
        try:
            cuts = page_cuts(path, number)
        except Exception as exc:
            print(f"== {name} p{number}: unreadable ({exc!r})"[:160])
            continue
        if not cuts:
            if not brief:
                print(f"== {name} p{number}: no cuts")
            continue
        with_cuts += 1
        for c in cuts:
            corpus[(c["same"], c["role"], bin_of(c["shared"]), reach_of(c["reach"]))] += 1
        by = collections.Counter((bin_of(c["shared"]), reach_of(c["reach"])) for c in cuts)
        print(f"== {name} p{number}: {len(cuts)} cuts;  "
              + ", ".join(f"{b} {r}: {k}" for (b, r), k in sorted(by.items())))
        if brief:
            continue
        examples = collections.OrderedDict()
        for c in cuts:
            key = (c["role"], c["same"], bin_of(c["shared"]), reach_of(c["reach"]), c["here"], c["next"], c["font"])
            entry = examples.setdefault(key, [0, [], []])
            entry[0] += 1
            if c["shared"] is not None and len(entry[1]) < 3:
                entry[1].append(round(c["shared"], 2))
                entry[2].append(round(c["reach"], 2))
        listed = list(examples.items())
        odd = [e for e in listed[8:] if e[0][2] not in ("<.9", ">=.9") or e[0][3] != "past"]
        for (role, same, where, reach, here, nxt, font), (k, shares, reaches) in listed[:8] + odd[:10]:
            print(f"   {k:3d} x {here!r} then {nxt!r} ({unicodedata.category(nxt)}) in {font[:20]}: {role}, {same[:5]},"
                  f" shared {where} {shares}, {reach} {reaches}")
    print(f"\n{pages} page(s), {with_cuts} with cuts; cuts by font, role, shared height and reach:")
    for (same, role, b, r), k in sorted(corpus.items()):
        print(f"   {k:6d}  {same:10s} {role:5s} {b:6s} {r}")


if __name__ == "__main__":
    main()
