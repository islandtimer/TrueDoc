"""Reading one region of a page through a vision model: an icon or a figure.

Decision D015, items 1 and 4: an icon that carries meaning (a "covered" tick
drawn as a pictogram, a phone symbol) and a figure (a chart, a diagram) are
handed to a model as a small image with a question, and the answer goes into
the text with the `[^inferred]` tag. The prompts, the cropping and the
cleaning of the answer live here so every provider does the same thing.
"""

from __future__ import annotations

import base64
import re

import pymupdf

ICON_PROMPT = (
    "This image is a small icon or symbol cut out of a document, shown with a little of its surroundings. "
    "Say what it means to a reader of that document, in at most five words and in the document's own language "
    "(for example: Covered, Not covered, Optional extra, Warning, Telephone). Answer with those words only. "
    "If it is decoration with no meaning (a logo, a photograph, a plain bullet), answer exactly: decorative"
)

FIGURE_PROMPT = (
    "This image is a figure taken from a document: a chart, a diagram, a map or a picture. "
    "Describe what it shows in one or two plain sentences for a reader who cannot see it: the kind of figure, "
    "what is compared or depicted, and any values, labels or trends that can be read from it. "
    "Answer with the description only, without preamble. "
    "If it carries no information (a logo, a decorative picture), answer exactly: decorative"
)

# Longest side of the crop sent to the model, in pixels.
LONGEST_DIM = {"icon": 384, "figure": 1024}
# Padding around the region, as a fraction of its longer side: an icon needs
# some context (the cell it sits in), a figure only its own edges.
PADDING = {"icon": 0.6, "figure": 0.04}
MAX_TOKENS = {"icon": 40, "figure": 400}


def region_prompt(kind: str) -> str:
    return ICON_PROMPT if kind == "icon" else FIGURE_PROMPT


def render_region_png_base64(pdf_path: str, page_number: int, bbox: tuple[float, float, float, float], kind: str) -> str:
    """The region as a PNG (padded, longest side per `LONGEST_DIM`), base64-encoded.

    `bbox` is in the page's own coordinates as TrueDoc reports them (rotation
    already applied, the space of `page.rect`), which is also the space PyMuPDF's
    `clip` expects.
    """
    doc = pymupdf.open(pdf_path)
    try:
        page = doc[page_number - 1]
        x0, y0, x1, y1 = bbox
        pad = PADDING.get(kind, 0.1) * max(x1 - x0, y1 - y0, 1.0)
        clip = pymupdf.Rect(x0 - pad, y0 - pad, x1 + pad, y1 + pad) & page.rect
        if clip.is_empty or clip.width < 1 or clip.height < 1:
            clip = page.rect
        zoom = LONGEST_DIM.get(kind, 512) / max(clip.width, clip.height, 1.0)
        pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), clip=clip, alpha=False)
        return base64.b64encode(pix.tobytes("png")).decode("ascii")
    finally:
        doc.close()


def clean_answer(text: str | None, kind: str) -> str | None:
    """The model's answer as text fit for the document, or None when there is
    nothing to write (decoration, an empty or evasive answer)."""
    if not text:
        return None
    t = text.strip()
    if t.startswith("---"):  # an olmOCR-style front matter before the answer
        parts = t.split("---", 2)
        if len(parts) == 3:
            t = parts[2].strip()
    t = re.sub(r"^```[a-z]*\s*|\s*```$", "", t).strip()
    t = t.strip("\"'` \n")
    if not t:
        return None
    first = t.split("\n\n", 1)[0].strip()
    if re.match(r"^(decorative|decoration|none|n/a)\b", first, re.I):
        return None
    if kind == "icon":
        line = first.splitlines()[0].strip().rstrip(".:;,")
        line = re.sub(r"^(this|the)\s+(icon|symbol|image)\s+(means|shows|indicates|represents)\s*:?\s*", "", line, flags=re.I)
        words = line.split()
        if not words or len(words) > 8:
            return None
        return " ".join(words)
    desc = re.sub(r"\s+", " ", first).strip()
    if len(desc) > 400:
        cut = desc[:400]
        end = max(cut.rfind(". "), cut.rfind("; "))
        desc = (cut[: end + 1] if end > 120 else cut.rstrip() + "...").strip()
    return desc or None
