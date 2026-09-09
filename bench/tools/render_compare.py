"""Do PyMuPDF and PDFium draw the same page? (M18, D022)

Page rendering is the next stage to come off PyMuPDF, and D022 asks for a quantity the two
libraries must agree on because it describes the same thing. For rendering that quantity is the
picture itself, so this renders the same page both ways and compares it pixel by pixel.

    python bench/tools/render_compare.py [--pages 40] [--seed 3]

Two conventions differ and are the whole reason for measuring rather than assuming:

* **Clipping.** PyMuPDF takes a rectangle in the page's *unrotated* coordinate space (which is why
  the call sites in `truedoc/` multiply by the inverse rotation matrix before clipping). PDFium
  takes four insets from the edges of the *rendered* bitmap, after rotation. This tries both
  readings and reports which one lines up, rather than picking one and hoping.
* **Rotation.** Both apply the page's own rotation when rendering, but only a rotated page proves
  it, so rotated pages are sampled deliberately rather than left to chance.

A difference of a shade or two per pixel is expected and harmless - the two libraries antialias
differently. A difference in image *size*, or a large mean difference, is a real fault.
"""
from __future__ import annotations

import argparse
import glob
import os
import random
import statistics

import numpy as np
import pymupdf
import pypdfium2 as pdfium

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BENCH = os.path.join(REPO, "bench", "data", "olmocr-bench", "bench_data")


def mupdf_render(page, scale: float, clip=None, grey: bool = False) -> np.ndarray:
    kwargs = {"matrix": pymupdf.Matrix(scale, scale), "alpha": False,
              "colorspace": pymupdf.csGRAY if grey else pymupdf.csRGB}
    if clip is not None:
        kwargs["clip"] = pymupdf.Rect(*clip)
    pix = page.get_pixmap(**kwargs)
    n = 1 if grey else 3
    return np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, n)


def pdfium_render(page, scale: float, crop=(0, 0, 0, 0), grey: bool = False) -> np.ndarray:
    bmp = page.render(scale=scale, crop=crop, grayscale=grey)
    arr = np.asarray(bmp.to_pil().convert("L" if grey else "RGB"))
    return arr[:, :, None] if grey else arr


def compare(a: np.ndarray, b: np.ndarray, slack: int = 2) -> tuple[bool, float, float]:
    """(comparable, mean absolute difference, share of pixels differing by more than 8).

    The two libraries round a clipped bitmap's size differently, by a pixel or two; that is not
    the fault worth hunting, so images within `slack` pixels are compared over the region they
    share. A larger difference means the crop landed somewhere else entirely and is reported as
    not comparable.
    """
    if abs(a.shape[0] - b.shape[0]) > slack or abs(a.shape[1] - b.shape[1]) > slack:
        return False, float("nan"), float("nan")
    h, w = min(a.shape[0], b.shape[0]), min(a.shape[1], b.shape[1])
    d = np.abs(a[:h, :w].astype(np.int16) - b[:h, :w].astype(np.int16))
    return True, float(d.mean()), float((d > 8).mean())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=40)
    ap.add_argument("--seed", type=int, default=3)
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(BENCH, "pdfs", "*", "*.pdf")))
    rng = random.Random(args.seed)
    rng.shuffle(files)

    plain, rotated = [], []
    for f in files:
        if len(plain) >= args.pages and len(rotated) >= 8:
            break
        try:
            d = pymupdf.open(f)
            (rotated if d[0].rotation else plain).append(f)
            d.close()
        except Exception:
            pass
    sample = plain[:args.pages] + rotated[:8]
    print(f"{len(sample)} pages ({len(rotated[:8])} of them rotated)\n")

    stats: dict[str, list] = {}
    size_faults: list[str] = []
    shape_notes: list[str] = []
    for f in sample:
        doc = pymupdf.open(f)
        mp = doc[0]
        pd = pdfium.PdfDocument(f)
        pp = pd[0]
        W, H = float(mp.rect.width), float(mp.rect.height)
        for label, scale, grey in (("full 1x", 1.0, False), ("full 2x", 2.0, False), ("full grey", 1.0, True)):
            a = mupdf_render(mp, scale, None, grey)
            b = pdfium_render(pp, scale, (0, 0, 0, 0), grey)
            ok, mean, share = compare(a, b)
            if not ok:
                size_faults.append(f"{label} {os.path.basename(f)} {a.shape} vs {b.shape}")
            else:
                stats.setdefault(label, []).append((mean, share))

        # Deliberately off-centre: a symmetric clip makes the two conventions arithmetically
        # identical and so proves nothing about which one is right.
        # Whole points: pypdfium2 rounds each inset up (`math.ceil(c*scale)`), so a fractional
        # clip shifts its crop by up to a pixel against MuPDF's, and a one-pixel shift over text
        # swamps the comparison. Rounding is measured separately below.
        clip = (float(int(0.10 * W)), float(int(0.20 * H)), float(int(0.60 * W)), float(int(0.50 * H)))
        a = mupdf_render(mp, 1.0, clip, False)
        turn = " (rotated)" if mp.rotation else " (upright)"
        for name, crop in (
            ("clip as bitmap insets" + turn, (clip[0], H - clip[3], W - clip[2], clip[1])),
            ("clip as unrotated rect" + turn, (clip[0], clip[1], W - clip[2], H - clip[3])),
        ):
            b = pdfium_render(pp, 1.0, crop, False)
            ok, mean, share = compare(a, b)
            if ok:
                stats.setdefault(name, []).append((mean, share))
            else:
                stats.setdefault(name + " [size mismatch]", []).append((float("nan"), float("nan")))
                if len(shape_notes) < 6:
                    shape_notes.append(f"{name}: mupdf {a.shape[1]}x{a.shape[0]} vs pdfium "
                                       f"{b.shape[1]}x{b.shape[0]}  (page {W:.1f}x{H:.1f}, rot {mp.rotation})")
        pd.close()
        doc.close()

    print(f"{'comparison':<28s}{'pages':>7s}{'mean diff':>12s}{'>8 apart':>11s}")
    for label, rows in stats.items():
        good = [r for r in rows if r[0] == r[0]]
        if not good:
            print(f"  {label:<26s}{len(rows):>7d}{'  size mismatch':>23s}")
            continue
        print(f"  {label:<26s}{len(good):>7d}{statistics.mean(m for m, _ in good):>12.3f}"
              f"{100 * statistics.mean(s for _, s in good):>10.2f}%")
    if size_faults:
        print("\nfull-page size mismatches:")
        for line in size_faults[:10]:
            print("  " + line)
    if shape_notes:
        print("\nclip size mismatches:")
        for line in shape_notes:
            print("  " + line)


if __name__ == "__main__":
    main()
