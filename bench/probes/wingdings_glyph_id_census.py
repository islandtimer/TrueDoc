"""Wingdings arrows whose CODE is gone but whose GLYPH ID is not: how many, where?

A producer that re-encodes an embedded Wingdings subset (codes 1, 2, 3 ... in order of first use) leaves no Unicode
and no Wingdings code: benchmark tables/9921f236..._pg349 sets "⇨ Post-deal" with the arrow at code 2. But that
subset kept the font's glyph ids - 226 glyph slots, three of them filled - and glyph 214 of Microsoft's Wingdings is
code F0, the open right arrow the page draws. This census counts, on a population, every character of a Wingdings
(proper) font whose code is NOT a Wingdings arrow's but whose glyph id IS, with the embedded font's glyph count beside
it (226 = the font's own glyph order was kept), and what the line says.

Reads the PDFs with PyMuPDF only; needs the system's wingding.ttf to turn a glyph id into a code.

usage (repo root): wingdings_glyph_id_census.py <out.jsonl> kfs|insurance|bench [workers]
"""
import concurrent.futures
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "bench", "probes"))

PROPER = re.compile(r"wingdings(?![\s_-]*[23])", re.I)
_BACK = None


def glyph_codes():
    global _BACK
    if _BACK is None:
        from fontTools.ttLib import TTFont
        font = TTFont(r"C:/Windows/Fonts/wingding.ttf")
        order = font.getGlyphOrder()
        table = next(t for t in font["cmap"].tables if (t.platformID, t.platEncID) == (3, 0))
        _BACK = ({order.index(name): code & 0xFF for code, name in table.cmap.items()}, len(order))
    return _BACK


def census(job):
    label, path, number, secret = job
    import pymupdf
    from fontTools.ttLib import TTFont
    back, full = glyph_codes()
    out = []
    try:
        doc = pymupdf.open(path)
        page = doc[number - 1]
        fonts = [f for f in page.get_fonts() if PROPER.search(f[3])]
        if not fonts:
            return out
        counts = {}
        for f in fonts:
            try:
                data = doc.extract_font(f[0])[3]
                counts[f[3].split("+")[-1]] = len(TTFont(io.BytesIO(data)).getGlyphOrder()) if data else None
            except Exception:
                counts[f[3].split("+")[-1]] = None
        lines = [("".join(c["c"] for s in l["spans"] for c in s["chars"]), l["bbox"])
                 for b in page.get_text("rawdict")["blocks"] for l in b.get("lines", [])]
        for span in page.get_texttrace():
            if not PROPER.search(span["font"]):
                continue
            for uni, gid, origin, box in span["chars"]:
                code = back.get(gid)
                if code is None or not (0xDF <= code <= 0xF8) or uni - 0xF000 == code or uni == code:
                    continue
                near = [t for t, b in lines if b[1] - 2 <= origin[1] <= b[3] + 2 or b[0] - 2 <= origin[0] <= b[2] + 2]
                out.append({"page": label, "held_out": secret, "unicode": hex(uni), "glyph": gid, "code": hex(code),
                            "slots": counts.get(span["font"].split("+")[-1]), "full": full,
                            "near": "(held out)" if secret else " | ".join(t.strip()[:24] for t in near[:3])})
    except Exception as exc:
        return [{"page": label, "error": repr(exc)[:100]}]
    return out


if __name__ == "__main__":
    from orphan_row_census import jobs
    out, which = sys.argv[1], sys.argv[2]
    todo = list(jobs(which))
    print(len(todo), "pages", flush=True)
    with open(out, "w", encoding="utf-8") as f, concurrent.futures.ProcessPoolExecutor(max_workers=int(sys.argv[3]) if len(sys.argv) > 3 else 6) as pool:
        for rows in pool.map(census, todo, chunksize=4):
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    rows = [json.loads(l) for l in open(out, encoding="utf-8")]
    errors = [r for r in rows if "error" in r]
    rows = [r for r in rows if "glyph" in r]
    print("arrows known by glyph id only: %d on %d pages (held-out pages, counted only: %d); errors: %d"
          % (len(rows), len({r["page"] for r in rows}), len({r["page"] for r in rows if r["held_out"]}), len(errors)))
    for page in sorted({r["page"] for r in rows if not r["held_out"]}):
        mine = [r for r in rows if r["page"] == page]
        print("   %-46s %d: codes %s unicode %s slots %s of %s | %s" % (
            page[-46:], len(mine), sorted({r["code"] for r in mine}), sorted({r["unicode"] for r in mine}),
            sorted({str(r["slots"]) for r in mine}), mine[0]["full"], mine[0]["near"][:90]))
