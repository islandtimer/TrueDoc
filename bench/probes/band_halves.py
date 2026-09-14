"""Which half of the partial-band change freed a sheet's band: the white space around it, or the grid's crossing?

The change has two parts: `_band_segments` takes a single run of text set apart above and below for a band, and
`_spanned_columns` lets a known band cross into a column once it reaches 0.4 of the body size into it. Each named
tuned-on sheet is converted with the working tree three ways - as it stands, with the white-space test cut, and with
the band's crossing cut - by exec'ing aligned.py's own functions, with one part cut, into the module's namespace, so
every caller in aligned.py resolves the cut version. No file is touched; a held-out sheet is refused.

usage (repo root): band_halves.py <fragment> [<fragment> ...]
"""
import inspect
import os
import sys

sys.path.insert(0, os.path.join("bench", "tools"))
from kfs_grade import cache_path, grade, held_out, sheets  # noqa: E402
import truedoc.tables.aligned as aligned  # noqa: E402
from truedoc.pipeline import ConvertOptions, convert  # noqa: E402

CUTS = {
    "no white space": ("_band_segments", "        if apart and any(", "        if False and any("),
    "no crossing": ("_spanned_columns", "(min(0.3 * (hi - lo), 0.4 * size) if band else 0.3 * (hi - lo))", "(0.3 * (hi - lo))"),
}
ORIGINAL = {name: getattr(aligned, name) for name, _, _ in CUTS.values()}
SOURCE = {name: inspect.getsource(fn) for name, fn in ORIGINAL.items()}


def use(which: str) -> None:
    for name, fn in ORIGINAL.items():
        setattr(aligned, name, fn)
    if which in CUTS:
        name, old, new = CUTS[which]
        if SOURCE[name].count(old) != 1:
            sys.exit(f"{which}: the passage is not in the running {name}")
        exec(SOURCE[name].replace(old, new), vars(aligned))


def main() -> None:
    by_cache = {os.path.basename(cache_path(p)): p for _, p in sheets()}
    names = sorted({n for f in sys.argv[1:] for n in by_cache if f in n})
    for name in names:
        path = by_cache[name]
        if held_out(path):
            print(f"{name[:44]:44s} held out - not looked at", flush=True)
            continue
        cells = []
        for which in ("as it stands", "no white space", "no crossing"):
            use(which)
            g = grade(convert(path, ConvertOptions(frontmatter=False, pages=[1, 2])))
            cells.append(f"{which}: swallowed {str(bool(g.get('band_swallowed'))):5s} answers {g.get('answers_attached', 0):2d}")
        use("as it stands")
        print(f"{name[:44]:44s} " + "  |  ".join(cells), flush=True)


if __name__ == "__main__":
    main()
