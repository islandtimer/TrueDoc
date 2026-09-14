"""RAA's landlord PDS page 22: for each code its fonts map to "f", the glyph name the encoding gives it and its width.

The text layer's Unicode map sends several codes to "f" - the letter and the ff, fi, fl and ffi ligatures - while the
encoding's /Differences still names each code's glyph. TrueDoc gets a character's Unicode from PDFium but not its
code; this prints, per font, each code mapped to "f" with its glyph name and its /Widths entry (thousandths of an em).
On 15 September, National2-Regular: 0x1b f_f_i 863, 0x1c fl 604, 0x1d f_f 619, 0x1f fi 568, 0x66 f 324. The names say
which ligature each is; the widths tell a ligature from the letter (every f before a space advances 299 to 319), but
not fl from f_f once kerning moves an advance by 15 to 25 ("ofer" advances 604 on an f_f glyph).

usage (repo root): ligature_codes.py
"""
import os
import re
import sys

import pypdf

sys.stdout.reconfigure(encoding="utf-8")
PDF = os.path.join("C:/", "Users", "griff", "OneDrive", "Documents", "10 Have a crack", "25 InsurancePlatform",
                   "uploads", "PDS Docs", "RAA", "landlord-insurance",
                   "raa-landlord-and-short-stay-insurance-pds-product-disclosure-statement-30-9-2021_0f6ceea4.pdf")
BFCHAR = re.compile("<([0-9A-Fa-f]+)>[ ]*<([0-9A-Fa-f]+)>")


def obj(x):
    return x.get_object() if hasattr(x, "get_object") else x


def main() -> None:
    page = pypdf.PdfReader(PDF).pages[21]
    fonts = obj(obj(page.get("/Resources")).get("/Font"))
    for key, ref in fonts.items():
        f = obj(ref)
        enc = obj(f.get("/Encoding"))
        names = {}
        if isinstance(enc, dict) and enc.get("/Differences"):
            code = 0
            for item in enc.get("/Differences"):
                if isinstance(item, (int, float)):
                    code = int(item)
                else:
                    names[code] = str(item).lstrip("/")
                    code += 1
        widths = [float(w) for w in (f.get("/Widths") or [])]
        first = int(f.get("/FirstChar", 0) or 0)
        cmap = obj(f.get("/ToUnicode")).get_data().decode("latin-1", "replace") if "/ToUnicode" in f else ""
        to_unicode = {int(a, 16): b.upper() for a, b in BFCHAR.findall(cmap)}
        f_codes = sorted(c for c, u in to_unicode.items() if u == "0066")
        print(f"{key} {f.get('/BaseFont')}: codes mapped to f: {[hex(c) for c in f_codes]}")
        for c in f_codes:
            w = widths[c - first] if 0 <= c - first < len(widths) else None
            print(f"   code {c:#04x}  name {names.get(c, '(base encoding)')!s:10s}  width {w}")


if __name__ == "__main__":
    main()
