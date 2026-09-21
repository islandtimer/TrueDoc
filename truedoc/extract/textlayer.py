"""Text-layer extraction with PyMuPDF.

Produces the raw evidence for a page: characters with fonts and boxes, words,
line segments, vector drawings (for table rulings) and image regions, plus an
assessment of how trustworthy the text layer is.
"""

from __future__ import annotations

import dataclasses
import math
import os
import unicodedata

from truedoc.math.symbols import is_extension_font, is_piece_glyph, latex_for_char, unfold_truncated_surrogate
from truedoc.extract import pdfium_objects, pdftext_rawdict, render
from truedoc.extract.handle import pymupdf_module
from truedoc.geometry import Rect, transform_point
from truedoc.model import BBox, Char, Drawing, ImageRef, Line, Page, TextQuality, Word

# Characters that indicate a broken or untrustworthy text layer.
_BAD_CATEGORIES = {"Co", "Cn", "Cs"}  # private use, unassigned, surrogates


def _is_bad_char(ch: str) -> bool:
    if ch == "�":
        return True
    cat = unicodedata.category(ch)
    if cat in _BAD_CATEGORIES:
        return True
    if cat == "Cc" and ch not in ("\t", "\n", "\r"):
        return True
    return False


def _rect(b, M=None) -> BBox:
    """A BBox from a 4-tuple; with a rotation matrix M, mapped into the rendered page space.

    MuPDF reports text, drawing and image coordinates in the unrotated page
    space; the rendered image (and the layout model's boxes) live in the
    rotated space, so everything is transformed once here.
    """
    if M is not None:
        r = Rect(b) * M
        return BBox(float(r.x0), float(r.y0), float(r.x1), float(r.y1))
    return BBox(float(b[0]), float(b[1]), float(b[2]), float(b[3]))


def _point(pt, M=None) -> tuple[float, float]:
    if M is not None:
        return transform_point(pt, M)
    return float(pt[0]), float(pt[1])


def _direction(d, M=None) -> tuple[float, float]:
    if M is not None:
        return (d[0] * M.a + d[1] * M.c, d[0] * M.b + d[1] * M.d)
    return (float(d[0]), float(d[1]))


_INK_FONT_HINTS = ("CMEX", "MTEX", "TXEX", "PXEX", "ESINT", "STMARY", "MATHEX", "LMMATHEXT", "CMBSY", "MATHX")


def _needs_ink(font: str) -> bool:
    """Maths-extension fonts: big brackets, big operators, wide accents, radicals."""
    f = font.upper()
    return is_extension_font(font) or any(h in f for h in _INK_FONT_HINTS)


def _page_has_extension_font(pdf_page: "pymupdf.Page", raw: dict | None = None) -> bool:
    if raw is not None and raw.get("source") == "pdftext":
        return any(_needs_ink(sp.get("font", ""))
                   for b in raw.get("blocks", []) if b.get("type") == 0
                   for ln in b.get("lines", []) for sp in ln.get("spans", []))
    try:
        return any(_needs_ink(f[3]) for f in pdf_page.get_fonts())
    except Exception:
        return False


def _extension_glyph_origins(pdf_page: "pymupdf.Page", M, raw: dict | None = None) -> list[tuple[float, float]]:
    """Origins of the real glyphs of maths-extension fonts.

    MuPDF's text extraction inserts a space character wherever it sees a gap,
    and that space carries the font of the span it lands in. A space inside an
    extension-font span is therefore either a synthetic blank or a real bracket
    glyph on a whitespace code; only the text trace, which lists drawn glyphs,
    can tell the two apart.

    PDFium invents the same gap-filling spaces, but says so: it marks a character
    it generated rather than found drawn, so on that path the answer is read off
    the character instead of from a second trace of the page.
    """
    out: list[tuple[float, float]] = []
    if raw is not None and raw.get("source") == "pdftext":
        for block in raw.get("blocks", []):
            if block.get("type") != 0:
                continue
            for ln in block.get("lines", []):
                for span in ln.get("spans", []):
                    if not _needs_ink(span.get("font", "")):
                        continue
                    for c in span.get("chars", []):
                        if not c.get("generated"):
                            out.append(_point(c.get("origin", (0, 0)), M))
        return out
    try:
        for span in pdf_page.get_texttrace():
            if not _needs_ink(span.get("font", "")):
                continue
            for ch in span.get("chars", []):
                out.append(_point(ch[2], M))
    except Exception:
        return out
    return out


def _is_real_glyph(origin: tuple[float, float], origins: list[tuple[float, float]]) -> bool:
    return any(abs(origin[0] - x) <= 0.3 and abs(origin[1] - y) <= 0.3 for x, y in origins)


def _mupdf_text_flags() -> int:
    """The text flags the old reader reads MuPDF with (TRUEDOC_READER=mupdf and the fallbacks)."""
    pymupdf = pymupdf_module()
    return (pymupdf.TEXTFLAGS_RAWDICT & ~pymupdf.TEXT_PRESERVE_LIGATURES) | pymupdf.TEXT_MEDIABOX_CLIP


def _attach_ink_boxes(pdf_page: "pymupdf.Page", chars: list[Char], M, raw: dict | None = None) -> None:
    """Measure the drawn outline of maths-extension glyphs, and recover their codes.

    Their font boxes are meaningless: the glyph hangs below its origin and the
    box comes from the font's ascender and descender, so a bracket three lines
    tall is reported as one line tall (or five). MuPDF can measure the outline
    for most embedded fonts; where it cannot, the box is left as it is and the
    formula code falls back on the font's design metrics. Glyphs MuPDF could not
    name come back as U+FFFD in the first pass; this pass asks for the raw code
    instead, which the cmex tables understand.

    PDFium reports both boxes for every character in the one reading - the metric box
    and the drawn outline - so on that path the outline is already in hand and no
    second pass over the page is needed. That also makes the alignment exact rather
    than assumed: the outlines come from the very characters `chars` was built from.
    """
    measured: list[tuple[str, BBox]] = []
    if raw is not None and raw.get("source") == "pdftext":
        for block in raw.get("blocks", []):
            if block.get("type") != 0:
                continue
            for ln in block.get("lines", []):
                for span in ln.get("spans", []):
                    for c in span.get("chars", []):
                        if not c.get("c", ""):
                            continue
                        ink = c.get("ink")
                        measured.append((c["c"], _rect(ink or c["bbox"], M)))
        _apply_ink_boxes(chars, measured)
        return
    pymupdf = pymupdf_module()
    flags = _mupdf_text_flags()
    accurate = getattr(pymupdf, "TEXT_ACCURATE_BBOXES", 0)
    cid = getattr(pymupdf, "TEXT_CID_FOR_UNKNOWN_UNICODE", 0)
    if not accurate and not cid:
        return
    try:
        measured_raw = pdf_page.get_text("rawdict", flags=flags | accurate | cid)
    except Exception:
        return
    for block in measured_raw.get("blocks", []):
        if block.get("type") != 0:
            continue
        for ln in block.get("lines", []):
            for span in ln.get("spans", []):
                for c in span.get("chars", []):
                    if c.get("c", ""):
                        measured.append((c["c"], _rect(c["bbox"], M)))
    _apply_ink_boxes(chars, measured)


def _apply_ink_boxes(chars: list[Char], measured: list[tuple[str, BBox]]) -> None:
    """Give each maths-extension glyph its measured outline, and recover its code."""
    if len(measured) != len(chars):
        return
    for ch, (text, box) in zip(chars, measured):
        if not _needs_ink(ch.font):
            continue
        if ch.text == "�" and text != "�" and len(text) == 1:
            ch.text = chr(0xE000 + ord(text)) if text.isspace() else text
        elif text != ch.text:
            continue
        if abs(box.y0 - ch.bbox.y0) > 0.3 or abs(box.y1 - ch.bbox.y1) > 0.3:
            ch.ink = box


_MATH_FONT_MARKS = ("CMMI", "CMSY", "CMEX", "MATH", "TXMI", "TXSY", "MTMI", "MTSY", "PXMI", "PXSY", "MSAM", "MSBM", "EURM", "RSFS")


def _is_math_font_mark(font: str) -> bool:
    """A font whose name says it is a maths font (CMMI, CMSY, TXMI, ...)."""
    f = font.upper()
    return any(h in f for h in _MATH_FONT_MARKS)


def _has_scripts(line: Line) -> bool:
    """A line carrying maths-font glyphs (a formula). Character sizes alone are not
    used: OCR layers declare erratic sizes that would look like scripts."""
    for w in line.words:
        for c in w.chars:
            f = c.font.upper()
            if _needs_ink(c.font) or any(h in f for h in _MATH_FONT_MARKS):
                return True
    return False


def _words_interleave(a: list[Word], b: list[Word]) -> bool:
    """Two word lists share a span without any two words lying on top of each other.

    Wide accents and brackets from the maths-extension font sit on top of their
    base letters by design (MuPDF cuts the line at them); they do not count."""
    words = sorted((w for w in a + b if not all(_needs_ink(c.font) for c in w.chars)), key=lambda w: w.bbox.x0)
    for p, q in zip(words, words[1:]):
        overlap = p.bbox.x1 - q.bbox.x0
        # A numerator and its denominator share a span too, one above the other
        # (MuPDF starts a new line at the denominator): stacked words are fine,
        # only words at the same height would be a duplicated text layer.
        if overlap > 0.3 * min(p.bbox.width, q.bbox.width) and abs(p.baseline - q.baseline) <= 0.6 * min(p.size or 10.0, q.size or 10.0):
            # A script-sized word under or over a full-size one (the "++" of
            # S^{n x n}_{++} that MuPDF starts the next segment with) is a
            # script of it, not a copy; equal sizes are the duplicated layer.
            big_p = max((c.size for c in p.chars), default=p.size or 10.0)
            big_q = max((c.size for c in q.chars), default=q.size or 10.0)
            if min(big_p, big_q) >= 0.85 * max(big_p, big_q):
                return False
    return True


def _ink_box(ch: Char) -> BBox:
    """Where a character's ink can be: inside its box, from a fifth of an em under the baseline to
    three quarters of an em over it. A font's box is taller than anything printed in it - it holds
    the line's leading too - so a band of shading as tall as the line covers every stroke of a
    character while covering 87% of its box (a GIO Key Facts Sheet, 18 September 2026)."""
    top, bottom = max(ch.bbox.y0, ch.origin_y - 0.75 * ch.size), min(ch.bbox.y1, ch.origin_y + 0.22 * ch.size)
    if ch.size < 1.0 or bottom - top < 1.0:
        return ch.bbox
    return BBox(ch.bbox.x0, top, ch.bbox.x1, bottom)


class _Visibility:
    """Decides, per character, whether a reader can see it (decision D011).

    Reasons a character is hidden: "tiny" (under one point), "invisible" (render
    mode 3 or zero opacity, unless the page is a scan whose invisible text layer
    is its only text), "covered" (an opaque shape or image painted over it
    later), "same-colour" (its colour matches the page or the shape beneath it).
    Text over an image is left alone: the background is unknown.
    """

    def __init__(self, pdf_page: "pymupdf.Page", width: float, height: float, M,
                 raw: dict | None = None, objects: list | None = None) -> None:
        self.width, self.height = width, height
        self._span_at: dict[tuple[int, int], dict] = {}
        # The same, by position *and* character, in the order the page gives them. Position alone
        # is not enough where two texts are printed at one spot: an earlier wording's full stop
        # and a letter of the sentence set over it share an origin to half a point, the later
        # overwrote the earlier, and the hidden full stop was judged by the visible letter's
        # paint order (an Apia Key Facts Sheet, 18 September 2026: "item" went and "." stayed).
        self._span_queue: dict[tuple[int, int, str], list[dict]] = {}
        self.cover: list[tuple[int, BBox, str, tuple | None]] = []
        self.under: list[tuple[int, BBox]] = []  # anything painted (fills of any shape, images): the background is unknown there
        self.hidden: list[tuple[int, Char, str]] = []
        self.seen: list[Char] = []      # every character judged on paint and colour: `verify` asks which of them are printed over another
        self.total_chars = 0
        self.distrusted = False
        # The page-quality check's measure (`_assess_quality`): the characters the page draws and
        # how many of them are drawn invisibly, leaving out the blanks PDFium generates to fill gaps
        # (a trace of the drawing never sees those).
        self.drawn_invisible = self.drawn_total = 0
        invisible = total = 0
        image_area = 0.0
        page_area = width * height or 1.0
        if raw is not None and raw.get("source") == "pdftext" and objects is not None:
            invisible, total, image_area = self._from_pdfium(raw, objects, M, page_area)
        else:
            invisible, total, image_area = self._from_mupdf(pdf_page, M, page_area)
            self.drawn_invisible, self.drawn_total = invisible, total
        inv_fraction = invisible / total if total else 0.0
        coverage = min(1.0, image_area / (width * height or 1.0))
        # The same rule as the page-quality assessment: an invisible layer over a scan.
        self.ocr_layer = inv_fraction > 0.5 or (coverage > 0.6 and inv_fraction > 0.1)

    def _from_pdfium(self, raw: dict, objects: list, M, page_area: float) -> tuple[int, int, float]:
        """The same facts from PDFium: the reader's characters carry their object's painting
        order, render mode and opacity, and the page's objects supply what was painted where.

        This is the last stage of the reader swap (M18, D022), and the one the benchmark is
        least able to check: get it wrong and nothing crashes, text a reader cannot see simply
        lands in the body or visible text is quietly dropped. `tests/test_hidden_text_readers.py`
        holds the invariant - one word of each kind, and both readers must agree on which are
        hidden and why.
        """
        invisible = total = 0
        for block in raw.get("blocks", []):
            if block.get("type") != 0:
                continue
            for ln in block.get("lines", []):
                for span in ln.get("spans", []):
                    for c in span.get("chars", []):
                        if not c.get("c", ""):
                            continue
                        info = {"type": 3 if c.get("invisible") else 0,
                                "opacity": float(c.get("alpha", 1.0)),
                                "seqno": int(c.get("order", -1))}
                        drawn_invisibly = info["type"] == 3 or info["opacity"] == 0.0
                        total += 1
                        invisible += int(drawn_invisibly)
                        if not c.get("generated"):
                            self.drawn_total += 1
                            self.drawn_invisible += int(drawn_invisibly)
                        x, y = _point(c.get("origin", (0, 0)), M)
                        self._span_at[(round(x * 2), round(y * 2))] = info
                        self._span_queue.setdefault((round(x * 2), round(y * 2), c.get("c", "")), []).append(info)
        image_area = 0.0
        for o in objects:
            if o.kind in ("image", "shading"):
                box = _rect(o.bbox, M)
                self.under.append((o.order, box))
                if o.kind == "shading":
                    continue  # a gradient beneath text: background unknown, never a cover
                image_area += box.area
                # A picture covering most of the page is a scan; text under it
                # is the scan's text layer (D010), not hidden text.
                if box.area < 0.6 * page_area:
                    self.cover.append((o.order, box, "image", None))
            elif o.kind == "path" and o.fill is not None:
                if o.fill_alpha < 0.9:
                    continue
                self.under.append((o.order, _rect(o.bbox, M)))
                # Only the rectangles a path actually fills can hide text (see _from_mupdf).
                for r in o.rects:
                    self.cover.append((o.order, _rect(r, M), "fill", tuple(o.fill)))
        return invisible, total, image_area

    def _from_mupdf(self, pdf_page: "pymupdf.Page", M, page_area: float) -> tuple[int, int, float]:
        invisible = total = 0
        try:
            for span in pdf_page.get_texttrace():
                info = {"type": int(span.get("type", 0) or 0), "opacity": float(span.get("opacity", 1.0)), "seqno": int(span.get("seqno", -1))}
                n = len(span.get("chars", []))
                total += n
                if info["type"] == 3 or info["opacity"] == 0.0:
                    invisible += n
                for c in span.get("chars", []):
                    x, y = _point(c[2], M)
                    self._span_at[(round(x * 2), round(y * 2))] = info
                    glyph = chr(c[0]) if isinstance(c[0], int) and 0 < c[0] < 0x110000 else str(c[0])
                    self._span_queue.setdefault((round(x * 2), round(y * 2), glyph), []).append(info)
        except Exception:
            pass
        image_area = 0.0
        try:
            for i, (kind, rect) in enumerate(pdf_page.get_bboxlog()):
                if kind in ("fill-image", "fill-imgmask", "fill-shade"):
                    box = _rect(rect, M)
                    self.under.append((i, box))
                    if kind == "fill-shade":
                        continue  # a gradient beneath text: background unknown, never a cover
                    image_area += box.area
                    # A picture covering most of the page is a scan; text under it
                    # is the scan's text layer (D010), not hidden text.
                    if kind == "fill-image" and box.area < 0.6 * page_area:
                        self.cover.append((i, box, "image", None))
        except Exception:
            pass
        try:
            for d in pdf_page.get_drawings():
                fill = d.get("fill")
                if fill is None or str(d.get("type", "")) not in ("f", "fs"):
                    continue
                if float(d.get("fill_opacity", 1.0) or 1.0) < 0.9:
                    continue
                colour = tuple(float(v) for v in fill)
                seq = int(d.get("seqno", -1))
                self.under.append((seq, _rect(d["rect"], M)))
                # Only the rectangles a path actually fills can hide text. A path's
                # bounding box is not enough: a box border drawn as a filled path
                # spans the whole box while painting only its edges.
                for item in d.get("items", []):
                    if item and item[0] == "re":
                        self.cover.append((seq, _rect(item[1], M), "fill", colour))
        except Exception:
            pass
        return invisible, total, image_area

    def reason(self, ch: Char, origin: tuple[float, float]) -> str:
        if ch.text.isspace():
            return ""
        if 0 < ch.size < 1.0 and ch.bbox.height < 1.0:
            return "tiny"
        cx, cy = ch.bbox.cx, ch.bbox.cy
        if cx < -1.0 or cy < -1.0 or cx > self.width + 1.0 or cy > self.height + 1.0:
            return "off-page"  # beyond the visible page box (print-shop stamps, crop-mark text)
        key = (round(origin[0] * 2), round(origin[1] * 2))
        queue = self._span_queue.get(key + (ch.text,))
        if queue:
            # The page's characters are judged in the order they were recorded, so where the same
            # character stands twice at one spot each takes its own record in turn.
            info = queue.pop(0) if len(queue) > 1 else queue[0]
        else:
            info = self._span_at.get(key)
        if info is not None and not self.ocr_layer and (info["type"] == 3 or info["opacity"] == 0.0):
            return "invisible"
        seq = info["seqno"] if info is not None else -1
        box = ch.bbox
        ink = _ink_box(ch)
        self.seen.append(ch)
        background: tuple | None = (1.0, 1.0, 1.0)
        background_seq = -1
        for s, rect, kind, colour in self.cover:
            # Painted over later, and over the character's ink: that is what hides it. Its box
            # is taller than its ink, so a fill the height of the line would never count.
            if seq >= 0 and s > seq and ink.overlap_fraction(rect) >= 0.9:
                return "covered"
            if box.overlap_fraction(rect) < 0.9:
                continue
            if seq >= 0 and s > seq:
                return "covered"
            if s > background_seq:
                background, background_seq = (colour if kind == "fill" else None), s
        # Anything else painted beneath the text (a shaped fill, an image of any
        # size) makes the background unknown: white text on a dark masthead is visible.
        if background is not None and any(s < seq and s > background_seq and box.overlap_fraction(rect) > 0.1 for s, rect in self.under):
            background = None
        if background is not None and _same_colour(ch.color, background):
            return "same-colour"
        return ""

    def _runs(self) -> list[dict]:
        out: list[dict] = []
        for line_index, ch, reason in self.hidden:
            if not ch.hidden:
                continue
            if out and out[-1]["_line"] == line_index and out[-1]["reason"] == reason:
                prev = out[-1]
                gap = ch.bbox.x0 - prev["_x1"]
                prev["text"] += (" " if gap > 0.2 * max(ch.size, 1.0) else "") + ch.text
                prev["_x1"] = ch.bbox.x1
                prev["bbox"] = prev["bbox"].union(ch.bbox)
                prev["_chars"].append(ch)
            else:
                out.append({"text": ch.text, "reason": reason, "bbox": ch.bbox, "_line": line_index, "_x1": ch.bbox.x1, "_chars": [ch]})
        return out

    def verify(self, pdf_page: "pymupdf.Page", M) -> None:
        """Drop "covered" and "same-colour" verdicts that the rendered page contradicts.

        Reported colours and paint order can mislead (a producer that reports
        black text as white; a figure whose paint order says it lies over the
        text). Rendering the run's box is the ground truth: hidden text is a
        uniform patch, visible text shows contrast.

        But only the run's *own* ink is evidence. Where other, visible text is printed over the
        same spot - an earlier wording left under a row's shading with the present sentence set
        on top of it; a footer printed twice - the patch shows contrast that is not this run's,
        and a correct verdict was being overturned by it ("entered", "item.", "s at:" in the
        bodies of Key Facts Sheets; found 18 September 2026 by comparing our reading with a
        model's). So the render is asked about the characters that no visible character is
        printed over, a stretch at a time, and where there are none it cannot testify and the
        paint order stands.
        """
        render_failed = False
        visible = [c for c in self.seen if not c.hidden]
        for run in self._runs():
            if run["reason"] not in ("covered", "same-colour"):
                continue
            stretches = _clear_stretches(run["_chars"], visible)
            if not stretches:
                continue
            for box in stretches:
                uniform = _renders_uniform(pdf_page, box, M)
                if uniform is None:
                    render_failed = True
                elif not uniform:
                    for ch in run["_chars"]:
                        ch.hidden = ""
                    break
        # Without a render to check against, a page cannot be believed to be
        # almost entirely invisible: keep the text rather than trust the colours.
        # (With a render, a genuinely invisible duplicate text layer stays hidden.)
        doubtful = [ch for _, ch, reason in self.hidden if ch.hidden in ("covered", "same-colour")]
        if render_failed and doubtful and len(doubtful) > 0.5 * max(1, self.total_chars):
            for ch in doubtful:
                ch.hidden = ""
            self.distrusted = True

    def grouped(self) -> list[dict]:
        """Hidden characters joined into runs per text line and reason."""
        out = self._runs()
        for entry in out:
            entry.pop("_line", None)
            entry.pop("_x1", None)
            entry.pop("_chars", None)
        return out


_PRINTED_OVER = 0.1     # other visible ink over a tenth of a character's ink: more than a neighbour's kerning, so an overprint


def _clear_stretches(chars: list[Char], visible: list[Char]) -> list[BBox]:
    """The run's characters that no visible character is printed over, as the boxes of each
    unbroken stretch of them; a run with nothing printed over it is one stretch. The boxes are of
    the characters' ink, which is what was judged covered: a font box stands proud of a band of
    shading the height of its line, and the render would see the band's edge and call it ink."""
    chars = [c for c in chars if not c.text.isspace()]
    if not chars:
        return []
    own = {id(c) for c in chars}
    box = BBox.union_all(c.bbox for c in chars)
    near = [_ink_box(o) for o in visible
            if id(o) not in own and o.bbox.x1 > box.x0 and o.bbox.x0 < box.x1 and o.bbox.y1 > box.y0 and o.bbox.y0 < box.y1]
    stretches: list[BBox] = []
    current: list[BBox] = []
    for c in chars:
        ink = _ink_box(c)
        over = sum((ink.intersection(o).area if ink.intersection(o) is not None else 0.0) for o in near) if near else 0.0
        if ink.area > 0 and over / ink.area >= _PRINTED_OVER:
            if current:
                stretches.append(BBox.union_all(current))
                current = []
        else:
            current.append(ink)
    if current:
        stretches.append(BBox.union_all(current))
    # The patch is drawn at a pixel a point, and an edge that falls inside a pixel takes in what
    # lies beyond it - the white page below a band whose foot is the ink's foot. So the patch is
    # brought a point in from top and bottom and then to whole points: the letters' bodies stay in
    # view, the band's edge stays out, and `_renders_uniform`'s own half point lands on a pixel.
    out: list[BBox] = []
    for b in stretches:
        y0, y1 = math.ceil(b.y0 + 1.0), math.floor(b.y1 - 1.0)
        out.append(BBox(b.x0, float(y0), b.x1, float(y1)) if y1 - y0 >= 2 else b)
    return out


def _renders_uniform(pdf_page: "pymupdf.Page", box: BBox, M=None) -> bool | None:
    """Does this area of the page render as one flat colour (no visible ink)?
    None when the area could not be rendered.

    `box` is in the rendered page's own space and is used as it stands. Text and drawing
    coordinates come out of MuPDF unrotated and are turned once in `_rect`, but a clip is not
    text: `get_pixmap` takes the *rendered* space, so turning the box back would photograph the
    wrong part of a rotated page. Measured: clipping with the rendered-space rectangle reproduces
    the matching region of the full render exactly, where the turned-back one returned a
    differently shaped region elsewhere. `M` is accepted and ignored, so callers need not care.
    """
    try:
        rect = Rect(box.x0 - 0.5, box.y0 - 0.5, box.x1 + 0.5, box.y1 + 0.5)
        if rect.is_empty or rect.width < 1 or rect.height < 1:
            return True
        samples = render.render_image(pdf_page, 1.0, tuple(rect), grey=True).tobytes()
        if not samples:
            return None
        return (max(samples) - min(samples)) < 48
    except Exception:
        return None


def _same_colour(color: int, rgb: tuple) -> bool:
    r, g, b = ((color >> 16) & 255) / 255.0, ((color >> 8) & 255) / 255.0, (color & 255) / 255.0
    return max(abs(r - rgb[0]), abs(g - rgb[1]), abs(b - rgb[2])) < 0.12


def _extension_box(c: Char) -> BBox:
    """A box that reflects a maths-extension glyph: the measured outline's height
    when the reader provides one (PDFium does), else the cmex design metrics, else
    the font box.

    The width stays the metric box's, as MuPDF's design box keeps it. The outline's
    left edge follows the shape: the middle piece of a brace has its point 3pt left
    of the other pieces, and the maths stage, which stacks an extensible bracket's
    pieces only where they start within 0.15 em of each other, read one brace as
    three - a brace per row where MuPDF builds one cases environment (2503.03905,
    2503.05177, 2503.05062, 2503.09472)."""
    if c.ink is not None and c.ink.height > 0.3:
        return BBox(c.bbox.x0, c.ink.y0, c.bbox.x1, c.ink.y1)
    if is_extension_font(c.font) and len(c.text) == 1:
        from truedoc.math.symbols import CMEX_EXTENT, cmex_code

        ext = CMEX_EXTENT.get(cmex_code(c.text))
        if ext is not None:
            return BBox(c.bbox.x0, c.origin_y - ext[0] * c.size, c.bbox.x1, c.origin_y + ext[1] * c.size)
    return c.bbox


def _symbol_only(line: Line) -> bool:
    """A segment holding nothing but maths-extension glyphs (a big bracket, an operator)."""
    chars = [c for w in line.words for c in w.chars if not c.text.isspace()]
    return bool(chars) and all(_needs_ink(c.font) or _tall_symbol(c) for c in chars)


def _tall_symbol(c: Char) -> bool:
    """A radical or big operator from a maths symbol font: its origin sits well
    above the baseline of the text it belongs to, so it lands on a line of its own."""
    if c.text not in "√∑∏∫∮":
        return False
    f = c.font.upper()
    return is_extension_font(f) or any(k in f for k in ("CMSY", "CMEX", "MSAM", "MSBM", "MATH", "SYMBOL", "TXSY", "PXSY", "RTXSY", "MDSY", "LMMATHSYM"))


def extract_page(pdf_page: "pymupdf.Page", number: int) -> Page:
    rect = pdf_page.rect
    page = Page(number=number, width=float(rect.width), height=float(rect.height), rotation=int(pdf_page.rotation))
    M = pdf_page.rotation_matrix if pdf_page.rotation else None

    raw = None
    if pdftext_rawdict.enabled():
        # M18, D007, D023: read through PDFium instead of AGPL-licensed MuPDF. The default since
        # run 71 (TRUEDOC_READER=mupdf reads the old way), and it falls back rather than failing
        # a conversion.
        try:
            raw = pdftext_rawdict.build(pdf_page.parent.name, number)
        except Exception:
            raw = None
    if raw is None:
        try:
            raw = pdf_page.get_text("rawdict", flags=_mupdf_text_flags())
        except Exception:
            raw = {"blocks": []}

    lines: list[Line] = []
    chars_all: list[Char] = []
    pending: list[tuple[list[Char], tuple[float, float]]] = []
    extension = _page_has_extension_font(pdf_page, raw)
    glyph_origins = _extension_glyph_origins(pdf_page, M, raw) if extension else []
    objects = pdfium_objects.page_objects(pdf_page.parent.name, number) if pdfium_objects.enabled() else None
    visibility = _Visibility(pdf_page, page.width, page.height, M, raw, objects)
    line_index = 0
    for block in raw.get("blocks", []):
        if block.get("type") != 0:
            continue
        for ln in block.get("lines", []):
            line_index += 1
            direction = _direction(ln.get("dir", (1.0, 0.0)), M)
            line_chars: list[Char] = []
            drawn_origins: list[tuple[float, float]] = []
            if extension:
                # Origins of this line's visible characters: a synthetic blank is
                # placed at the origin of the glyph that follows it.
                drawn_origins = [_point(c.get("origin", (0, 0)), M) for span in ln.get("spans", []) for c in span.get("chars", []) if c.get("c", "") and not c["c"].isspace()]
            for span in ln.get("spans", []):
                font = span.get("font", "")
                size = float(span.get("size", 0.0))
                sflags = int(span.get("flags", 0))
                color = int(span.get("color", 0))
                for c in span.get("chars", []):
                    text = c.get("c", "")
                    if not text:
                        continue
                    origin = _point(c.get("origin", (0, 0)), M)
                    cbox = _rect(c["bbox"], M)
                    # Type 3 fonts report the font matrix scale (0.1) as their size;
                    # the glyph box is the only honest measure of size then.
                    csize = size if size >= 1.0 else round(max(size, 0.8 * cbox.height), 1)
                    if text.isspace() and extension and _needs_ink(font) and _is_real_glyph(origin, glyph_origins) and not _is_real_glyph(origin, drawn_origins):
                        # Maths-extension glyphs come back as their raw code; several
                        # brackets sit on whitespace codes (a size-4 "(" is 0x20, a
                        # "}" is a tab) and would be thrown away as blanks. Keep them
                        # on a private-use code that the formula code maps back.
                        # (A blank with no drawn glyph behind it is a synthetic space.)
                        text = chr(0xE000 + ord(text))
                    text = _small_caps(font, _central_european(font, _symbol_font_mark(font, unfold_truncated_surrogate(text, font))))
                    ch = Char(
                        text=text,
                        bbox=cbox,
                        font=font,
                        size=csize,
                        flags=sflags,
                        color=color,
                        origin_y=origin[1],
                    )
                    reason = visibility.reason(ch, origin)
                    if reason:
                        ch.hidden = reason  # provisional: "covered" and "same-colour" are verified against the rendered page below
                        visibility.hidden.append((line_index, ch, reason))
                    line_chars.append(ch)
            if not line_chars:
                continue
            chars_all.extend(line_chars)
            pending.append((line_chars, direction))

    # Maths-extension glyphs get their measured (or design-metric) boxes before
    # any line is built: their font boxes span several lines and would drag a
    # lone bracket into the wrong line.
    if extension and any(_needs_ink(c.font) for c in chars_all):
        _attach_ink_boxes(pdf_page, chars_all, M, raw)
        for c in chars_all:
            if _needs_ink(c.font):
                c.bbox = _extension_box(c)

    # Glyphs a TeX-era Type 3 font left unnamed arrive as their raw codes; in a
    # text font those are the ligatures "fi", "ff", "fl" (blanks in "classi cation").
    if any(_is_raw_code(c.text) for c in chars_all):
        if _recover_tex_codes(pending):
            chars_all = [c for line_chars, _ in pending for c in line_chars]
            page.meta["tex_codes_recovered"] = True

    # Verdicts that rest on reported colours and paint order are checked against
    # the rendered page: text a reader cannot see renders as a uniform patch.
    visibility.total_chars = sum(1 for c in chars_all if not c.text.isspace())
    visibility.verify(pdf_page, M)
    if visibility.distrusted:
        page.meta["visibility_distrusted"] = True

    vertical_down = vertical_up = text_chars = 0
    for line_chars, direction in pending:
        line_chars = _compose_spacing_accents([c for c in line_chars if not c.hidden])
        if not line_chars:
            continue
        n_visible = sum(1 for c in line_chars if not c.text.isspace())
        text_chars += n_visible
        if abs(direction[0]) < 0.5:
            # vertical or heavily rotated text: keep as one segment, mark it.
            # The counts let the pipeline turn a page whose text mostly runs
            # up or down (a scan lying on its side; `_sideways_text_turn`).
            if direction[1] > 0:
                vertical_down += n_visible
            else:
                vertical_up += n_visible
            words = _chars_to_words(line_chars, ocr_layer=visibility.ocr_layer)
            if words:
                seg = Line(words=words, bbox=BBox.union_all(w.bbox for w in words), rotated=True)
                lines.append(seg)
            continue
        words = _chars_to_words(line_chars, ocr_layer=visibility.ocr_layer)
        for seg in _split_line_segments(words):
            lines.append(seg)
    page.meta["text_chars"] = text_chars
    page.meta["vertical_chars_down"] = vertical_down
    page.meta["vertical_chars_up"] = vertical_up

    gutters = _column_gutters(lines)
    page.drawings = _extract_drawings(pdf_page, M)
    hlines = [d.bbox for d in page.drawings if d.kind == "hline"]
    lines = _join_drop_caps(_reassemble_lines(_split_at_gutters(lines, gutters), gutters, hlines))
    page.meta["column_gutters"] = gutters
    page.chars = [c for c in chars_all if not c.hidden]
    page.hidden_text = visibility.grouped()
    page.words = [w for l in lines for w in l.words]
    page.lines = lines
    if not visibility.ocr_layer:
        _read_private_glyphs(pdf_page, page)
    page.images = _extract_images(pdf_page, M)
    page.quality = _assess_quality(page, visibility)
    if page.quality.kind == "ocr":
        # Hidden OCR layers (archive.org, scanners) emit a text object per phrase or
        # word; rebuild lines by geometry, since their font sizes are meaningless.
        page.lines = _reassemble_ocr_layer(page.lines, gutters)
        # Some layers carry no space at all between words ("widespreadaccessorymineral");
        # only a dictionary can find the seams.
        page.lines = [_split_glued_words(l) for l in page.lines]
        page.words = [w for l in page.lines for w in l.words]
    else:
        # Digital text: pieces of one word emitted separately are one word (OCR
        # layers are excluded, their boxes overlap for other reasons).
        page.lines = [_fuse_touching_words(l) for l in page.lines]
        # An underscore TeX drew as a rule is a character of the word it sits in (`_read_drawn_underscores`).
        _read_drawn_underscores(pdf_page, page, M)
        page.words = [w for l in page.lines for w in l.words]
    page.body_font_size = _body_font_size(page)
    if page.quality.kind == "ocr" and page.lines:
        # Hidden OCR layers often declare a tiny nominal size; use the line boxes instead.
        heights = sorted(l.bbox.height for l in page.lines if not l.rotated)
        if heights:
            page.body_font_size = max(page.body_font_size, round(0.75 * heights[len(heights) // 2], 1))
    return page


import re as _re

_SHORT_WORDS = {"a", "an", "as", "at", "be", "by", "do", "he", "if", "in", "is", "it", "no", "of", "on", "or", "so", "to", "up", "us", "we", "am", "go", "me", "my",
                "the", "and", "for", "are", "was", "not", "but", "can", "has", "had", "its", "his", "her", "our", "you", "all", "any", "one", "two", "who", "how", "may", "new", "now", "out", "see", "use"}
# wordninja's cost is log(rank x log(N)); these bounds are roughly the 25,000th
# and the 8,000th word.
_COMMON_COST = 12.6
_EVERYDAY_COST = 11.45
# A semicolon or colon followed directly by a letter is a word break the layer's
# engine missed, and so is a comma followed by a word ("plant,and"; a single
# letter after a comma is a symbol in a list, "A,B"); a full stop or a closing
# bracket is one only before a capital ("1991).The"), since "e.g." is a word.
_GLUED_PUNCT = _re.compile(r"(?<=[;:])(?=[A-Za-z])|(?<=,)(?=[A-Za-z]{2})|(?<=[.)])(?=[A-Z])")
_vocab: dict | None = None


def _dictionary():
    """The English word list behind the splitter (loaded once; None if unavailable)."""
    global _vocab
    if _vocab is None:
        try:
            import wordninja

            _vocab = dict(wordninja.DEFAULT_LANGUAGE_MODEL._wordcost)
        except Exception:
            _vocab = {}
    return _vocab or None


def _split_token(token: str, monospace: bool = False) -> list[str] | None:
    """Split a run of letters with no spaces into real words, or None.

    Every part must be a common dictionary word, and the run itself must not
    be a word: that keeps "metamictization" and "Jolliffet" whole and splits
    "widespreadaccessorymineral". Short runs ("golfball") are split only in a
    monospaced layer, where the missing space is systematic rather than a rare
    compound the list lacks ("countship").
    """
    vocab = _dictionary()
    if vocab is None:
        return None
    low = token.lower()
    n = len(low)
    if n < 8 or not low.isalpha() or low in vocab:
        return None
    # A capitalised run is more often a name ("Whitehouse", "Goldsmith") than
    # glue; only a long one ("Transmissionelectron") is split.
    if token[0].isupper() and n < 12:
        return None
    import wordninja

    parts = wordninja.split(low)
    if len(parts) < 2 or len(parts) > 1 + n // 4:
        return None
    if n < 10:
        # A short run must be exactly two everyday words ("golfball") in a
        # monospaced layer; the list's tail would license far too much
        # ("countship" as "count ship").
        if not monospace or len(parts) != 2 or any(len(p) < 4 or p not in vocab or vocab[p] > _EVERYDAY_COST for p in parts):
            return None
        return [token[:len(parts[0])], token[len(parts[0]):]]
    if max(len(p) for p in parts) < 5:
        return None
    for p in parts:
        # Every part must be a common word (the list's tail holds fragments such
        # as "azar" and "ius" that would license splitting a name).
        if p not in vocab or vocab[p] > _COMMON_COST:
            return None
        if len(p) < 4 and p not in _SHORT_WORDS:
            return None
    # Keep the original capitalisation letter by letter.
    out, i = [], 0
    for p in parts:
        out.append(token[i:i + len(p)])
        i += len(p)
    return out


# TeX's original text encoding (OT1), the codes under 0x20. A Type 3 font made by
# dvips names its glyphs by code, so MuPDF hands these back raw; Python treats
# 0x0B-0x0D as whitespace, and "classi cation", "o -line" and "e cient" are how
# "fi", "ff" and "ffi" reached the output (13 multi-column checks, lateral round
# of 7 Sept 2026). The ligature slots are the signature of a text font in this
# encoding; a symbol font (cmsy, cmmi) uses the same codes for other glyphs and
# is told apart by its use: single letters, never words.
_OT1_CODES = {
    0x00: "Γ", 0x01: "Δ", 0x02: "Θ", 0x03: "Λ", 0x04: "Ξ", 0x05: "Π", 0x06: "Σ", 0x07: "Υ", 0x08: "Φ", 0x09: "Ψ", 0x0A: "Ω",
    0x0B: "ff", 0x0C: "fi", 0x0D: "fl", 0x0E: "ffi", 0x0F: "ffl",
    0x10: "ı", 0x11: "ȷ", 0x12: "`", 0x13: "´", 0x14: "ˇ", 0x15: "˘", 0x16: "¯", 0x17: "˚",
    0x18: "¸", 0x19: "ß", 0x1A: "æ", 0x1B: "œ", 0x1C: "ø", 0x1D: "Æ", 0x1E: "Œ", 0x1F: "Ø",
}
_OT1_LIGATURE_CODES = range(0x0B, 0x10)
# The Cork encoding (T1) keeps the five ligatures at 0x1B-0x1F. Its other low
# codes are quotation marks and dashes, which a text font uses constantly, so a
# font is only read as T1 when the ligature slots are the only raw codes it has.
# (No benchmark page uses it; the rule is covered by a unit test only.)
_T1_CODES = {0x1B: "ff", 0x1C: "fi", 0x1D: "fl", 0x1E: "ffi", 0x1F: "ffl"}


def _is_raw_code(text: str) -> bool:
    # (0x0D, a carriage return elsewhere, is "fl" here: MuPDF never puts line
    # breaks among a line's characters, so the code can only be a glyph's.)
    return len(text) == 1 and ord(text) < 0x20 and text not in ("\t", "\n")


def _recover_tex_codes(pending: list[tuple[list[Char], tuple[float, float]]]) -> bool:
    """Read the raw glyph codes of TeX text fonts as the letters they stand for.

    A font qualifies when its characters on the page are mostly letters set in
    words (runs of three or more letters of that font), and its raw codes carry
    the encoding's signature: any code in the OT1 ligature slots makes it OT1;
    codes only in the T1 ligature slots make it T1. A code is then replaced when
    a letter of the same font stands next to it, one character per letter, the
    glyph's box shared out between them. Returns True when anything changed.
    """
    total: dict[str, int] = {}
    in_runs: dict[str, int] = {}
    alpha: dict[str, int] = {}
    codes: dict[str, set[int]] = {}
    for line_chars, _ in pending:
        for c in line_chars:
            if c.text.isspace() and not _is_raw_code(c.text):
                continue
            total[c.font] = total.get(c.font, 0) + 1
            if _is_raw_code(c.text):
                codes.setdefault(c.font, set()).add(ord(c.text))
            elif c.text.isalpha():
                alpha[c.font] = alpha.get(c.font, 0) + 1
        j = 0
        while j < len(line_chars):
            c = line_chars[j]
            if c.text.isalpha():
                k = j
                while k < len(line_chars) and line_chars[k].font == c.font and line_chars[k].text.isalpha():
                    k += 1
                if k - j >= 3:
                    in_runs[c.font] = in_runs.get(c.font, 0) + (k - j)
                j = k
            else:
                j += 1
    tables: dict[str, dict[int, str]] = {}
    for font, cs in codes.items():
        n = total.get(font, 0)
        if n < 20 or alpha.get(font, 0) < 0.5 * n or in_runs.get(font, 0) < 0.5 * n:
            continue
        if any(code in _OT1_LIGATURE_CODES for code in cs):
            tables[font] = _OT1_CODES
        elif cs <= set(_T1_CODES):
            tables[font] = _T1_CODES
    if not tables:
        return False
    changed = False
    for entry in pending:
        line_chars = entry[0]
        out: list[Char] = []
        for i, c in enumerate(line_chars):
            table = tables.get(c.font) if _is_raw_code(c.text) else None
            text = table.get(ord(c.text)) if table else None
            if text is None or c.hidden:
                out.append(c)
                continue
            neighbours = [line_chars[k] for k in (i - 1, i + 1) if 0 <= k < len(line_chars)]
            if not any(n.font == c.font and n.text.isalpha() for n in neighbours):
                out.append(c)
                continue
            step = c.bbox.width / len(text)
            for k, letter in enumerate(text):
                box = BBox(c.bbox.x0 + k * step, c.bbox.y0, c.bbox.x0 + (k + 1) * step, c.bbox.y1)
                out.append(dataclasses.replace(c, text=letter, bbox=box))
            changed = True
        line_chars[:] = out
    return changed


def _split_glued_words(line: Line) -> Line:
    """On an OCR layer, break words the layer glued together: by dictionary for
    runs of letters, and at punctuation ("1991).The", "plant,and")."""
    new_words: list[Word] = []
    changed = False
    for w in line.words:
        pieces = [p for p in _GLUED_PUNCT.split(w.text) if p]
        if len(pieces) == 1:
            m = _re.match(r"^([A-Za-z]{8,})([^A-Za-z]*)$", w.text)
            mono = any((c.flags & 8) or "courier" in c.font.lower() or "mono" in c.font.lower() for c in w.chars[:1])
            parts = _split_token(m.group(1), monospace=mono) if m else None
            if parts:
                pieces = parts[:-1] + [parts[-1] + m.group(2)]
        if len(pieces) == 1 or sum(len(p) for p in pieces) != len(w.text) or len(w.chars) != len(w.text):
            new_words.append(w)
            continue
        changed = True
        i = 0
        for p in pieces:
            chars = w.chars[i:i + len(p)]
            new_words.append(Word(text=p, bbox=BBox.union_all(c.bbox for c in chars), chars=chars, after_space=(w.after_space if i == 0 else False)))
            i += len(p)
    if not changed:
        return line
    return Line(words=new_words, bbox=line.bbox, rotated=line.rotated)


# Marks set in symbol fonts. Their glyphs have no Unicode name, so MuPDF hands
# back the font's own code in the private-use range (U+F000 + code); the codes
# below are the ones a reader takes as a mark of meaning.
_SYMBOL_MARKS = {
    "wingdings": {0xFC: "✓", 0xFB: "✗", 0xFE: "☑", 0xFD: "☒", 0x6C: "●", 0x6D: "○", 0x6E: "■", 0x6F: "□", 0x75: "◆", 0xA8: "□"},
    "webdings": {0x61: "✓", 0x72: "✗"},
}
# Wingdings' arrows. An arrow set inside a word carries the word's meaning - "INTMRK→BRDORT" names a path of a model
# from one construct to another, and came out "INTMRKBRDORT" (benchmark tables/b5c5b866..._pg4, 20 September 2026):
# the code is private-use, the renderer strips those, and the reader of private-use glyphs leaves a font alone once it
# has set such a character inside a word. Each code below was DRAWN from the font file and looked at, not recalled:
# DF-E6 the light arrows, E7-EE the heavy, EF-F8 the open ones (FB-FE came out as the tick, cross and boxes already
# above, which checks the sheet). Wingdings proper only: Wingdings 2 and 3 draw other things at these codes.
_WINGDINGS_ARROWS = dict(zip(range(0xDF, 0xF9), "←→↑↓↖↗↙↘" "⬅➡⬆⬇⬉⬈⬋⬊" "⇦⇨⇧⇩⬄⇳⬁⬀⬃⬂"))
_WINGDINGS_PROPER = _re.compile(r"wingdings(?![\s_-]*[23])", _re.I)
# Webdings' triangles, each DRAWN from the font file and looked at (21 September 2026): 33 points left, 34 right, 35 up,
# 36 down, small and solid. The right-pointing one bullets lists in six documents of the owner's library - 608 of
# them, every one opening a line; the four that may be read are one design, a home PDS of June 2016 sold as Budget
# Direct, Aussie and Australia Post - and the text layer names it by its code: "4 INSURANCE CERTIFICATE", "4 artificial
# grass or turf", and "We will pay up to: 4 10% of your home sum insured", a figure a reader could take for 410%. The glyph reader takes it for
# an arrow head, which it rightly does not write, or cannot read it at all where the item's first letter reaches into its
# box, so the code names it (D013: marks set in symbol fonts are mapped from their font codes). It is written as the
# triangular bullet, which every list rule already knows; the other three as the shapes they are.
_WEBDINGS_TRIANGLES = {0x33: "◂", 0x34: "‣", 0x35: "▴", 0x36: "▾"}


# Free-standing accent glyphs and the combining marks they stand for. The grave
# accent is left out: in TeX fonts "`" is also the opening quotation mark.
_SPACING_ACCENTS = {
    "ˆ": "̂",   # circumflex
    "˜": "̃",   # tilde
    "´": "́",   # acute
    "¨": "̈",   # diaeresis
    "¸": "̧",   # cedilla
    "˚": "̊",   # ring
    "¯": "̄",   # macron
    "ˇ": "̌",   # caron
    "˘": "̆",   # breve
    "˙": "̇",   # dot above
    "˝": "̋",   # double acute
}


def _compose_spacing_accents(chars: list[Char]) -> list[Char]:
    """Join a free-standing accent glyph to the letter it sits over.

    Type 1 text fonts (TeX's accent command, some Adobe producers) draw an
    accent as a glyph of its own next to the base letter in the stream, before
    or after it: "Ram´on", "H¨older", "Geocieˆncias", "Evoluc¸a˜o" (296 such
    names in run 37's output). When the accent's centre lies over a neighbouring
    letter of the same font and the pair has a precomposed form, the letter
    becomes that form and the accent glyph goes. Maths accents are untouched: a
    hat over an italic x comes from a different font than the x, and x has no
    precomposed hat anyway.
    """
    if not any(c.text in _SPACING_ACCENTS for c in chars):
        return chars
    out = list(chars)
    i = 0
    while i < len(out):
        c = out[i]
        comb = _SPACING_ACCENTS.get(c.text)
        if comb is None:
            i += 1
            continue
        cx = (c.bbox.x0 + c.bbox.x1) / 2
        done = False
        for j in (i - 1, i + 1):
            if not (0 <= j < len(out)):
                continue
            b = out[j]
            if len(b.text) != 1 or not b.text.isalpha() or b.font != c.font:
                continue
            tol = 0.15 * max(b.size, 1.0)
            if not (b.bbox.x0 - tol <= cx <= b.bbox.x1 + tol):
                continue
            composed = unicodedata.normalize("NFC", b.text + comb)
            if len(composed) != 1:
                continue
            b.text = composed
            del out[i]
            done = True
            break
        if not done:
            i += 1
    return out


# Central European fonts of the 1990s ("Latin725PL", "SchadowPL", "...SCTCE") carry
# the Mac CE encoding, but their PDFs declare Mac Roman, so every Polish letter
# arrives as the Mac Roman character at the same byte: "powo∏uje" for "powołuje",
# "nale˝y" for "należy", "ksi´g´" for "księgę". Byte for byte, Mac Roman to Mac CE.
_MAC_CE_FROM_ROMAN = {
    "à": "ą", "Ñ": "Ą", "ç": "ć", "å": "Ć", "´": "ę", "¢": "Ę", "∏": "ł", "π": "Ł",
    "ƒ": "ń", "¡": "Ń", "Ê": "ś", "Â": "Ś", "ê": "ź", "è": "Ź", "˝": "ż", "¸": "Ż",
}


def _central_european(font: str, text: str) -> str:
    """Undo the Mac Roman reading of a Mac CE font (fonts named ...PL or ...CE)."""
    if text not in _MAC_CE_FROM_ROMAN:
        return text
    base = font.split("+", 1)[-1]
    name = base.split("-", 1)[0] if "-" in base else base
    if name.endswith(("PL", "CE")):
        return _MAC_CE_FROM_ROMAN[text]
    return text


_SMALL_CAPS_FONT = _re.compile(r"(?:SC|SmallCaps|Smallcaps|SCaps)(?:It|Ital|Italic|Bd|Bold|BoldItalic)?$")


def _small_caps(font: str, text: str) -> str:
    """A small-caps font ("TimesTen-RomanSC") prints its lowercase letters as
    small capitals: a reader sees "ROTTIER S., PIETTE J." where the text layer
    says "Rottier S., Piette J."; the page's reading is the capitals."""
    if not text or not any(c.islower() for c in text):
        return text
    base = font.split("+", 1)[-1]
    if _SMALL_CAPS_FONT.search(base):
        return text.upper()
    return text


# The symbol fonts of 2000s journal PDFs set with Advent 3B2 carry their own
# encoding, so their glyphs arrive as the Latin characters at the same codes:
# "(n ¼ 562)" is "(n = 562)", "m tð Þ ¼ m0 þ" is "m(t) = m0 +", and the minus
# sign sits on code 1, a control character that would otherwise be stripped and
# turn a negative correlation positive. Read off every use across the benchmark
# (6 Sept: 51 equals signs, 26 pairs of parentheses, 21 minus signs).
_ADVENT_SYMBOLS = {
    "AdvP4C4E74": {"¼": "=", "ð": "(", "Þ": ")", "þ": "+", "½": "[", "\x01": "−"},
    "AdvP40271B": {"¼": "=", "ð": "(", "Þ": ")", "þ": "+", "½": "[", "\x01": "−", "2": "∈", "f": "{", "g": "}", "j": "|"},
}


def _symbol_font_mark(font: str, text: str) -> str:
    table = _ADVENT_SYMBOLS.get(font.split("+", 1)[-1])
    if table is not None and text in table:
        return table[text]
    if len(text) != 1 or not (0xF000 <= ord(text) <= 0xF0FF):
        return text
    f = font.lower()
    if _WINGDINGS_PROPER.search(f) and ord(text) - 0xF000 in _WINGDINGS_ARROWS:
        return _WINGDINGS_ARROWS[ord(text) - 0xF000]
    for name, table in _SYMBOL_MARKS.items():
        if name in f:
            return table.get(ord(text) - 0xF000, text)
    return text


_READ_GLYPHS = ("tick", "cross", "dot", "circle", "square", "box")
# The marks a text layer names for itself: a bullet of one of these on a line of its own marks the line beside it,
# exactly as a mark read from its drawing does. Ticks and crosses are left out: a column of them is a table's answers.
_MARK_GLYPHS = frozenset("•◦▪●‣⁃·")
# Fonts that draw symbols and spell nothing: a Latin letter of theirs is a code, not a letter. "Symbol" is deliberately
# absent - it spells Greek and maths, and its own bullets already arrive as bullets.
_DINGBAT_FONTS = ("wingding", "webding", "dingbat", "marlett", "monotypesorts", "zapfdingbat")
# What a text layer can already name for itself: a character that is one of these means what it says.
_DRAWN_MARKS = frozenset("•◦▪●‣⁃·○□■✓✔✗✘☑☒"
                         "☐❏❐❑❒")   # and the dingbat boxes, which a form's empty checkbox already draws


def _dingbat_font(font: str) -> bool:
    name = (font or "").split("+")[-1].lower().replace("-", "").replace(" ", "").replace("_", "")
    return any(key in name for key in _DINGBAT_FONTS)


def _webdings_code(c: Char) -> str | None:
    """What a Webdings character draws, where its code alone says so (`_WEBDINGS_TRIANGLES`): the text layer gives the
    code either as itself ("4") or in the private-use range (U+F034)."""
    if len(c.text) != 1 or "webding" not in (c.font or "").split("+")[-1].lower().replace(" ", "").replace("-", ""):
        return None
    code = ord(c.text) - 0xF000 if 0xF000 <= ord(c.text) <= 0xF0FF else ord(c.text)
    return _WEBDINGS_TRIANGLES.get(code)


def _read_private_glyphs(pdf_page: "pymupdf.Page", page: Page) -> None:
    """A character whose code cannot mean what it draws is read by what its font draws.

    A code in Unicode's private-use area means nothing of its own; only the drawing says what it is. RAC's 2021 premium,
    excess and discount guides tick every pricing factor under "Buildings" and "Contents" with FontAwesome's check,
    U+F00C, and an RAA landlord policy bullets the causes a cell excludes with a Wingdings square: both were stripped
    with the raw glyph codes, so the pricing table's columns came out empty and the cell's list ran on as one line. The
    glyph is drawn and read as a drawn mark is (`truedoc.marks.classify_mark`): a tick, cross, dot, circle, square or
    box becomes that character. An arrow, a shape the reader cannot name, or a glyph with other drawing reaching into
    its box stays as it was - Suncorp's flow arrows sit on a rule, and read with it as a cross. Maths fonts are left
    alone: their private-use codes are pieces of brackets and letters that the formula code maps back.

    A dingbat font's Latin letter is the same problem wearing a different code. Wingdings, Webdings, ZapfDingbats,
    Marlett and Monotype Sorts hold no letters at all: their "n" draws a filled square, their "l" a circle, and the
    letter is what reaches the reader - "n admit guilt, fault or liability except to the police" in Australian Seniors'
    landlord PDS, and a marker that renders as nothing at all in Woolworths' target market determination, whose bullet
    is Wingdings U+009F. Over sixty documents of the owner's library, twelve pages each: 242 such characters over 27
    pages and seven distinct documents, every one of them opening a line. They are read by their drawing like any
    other, and a character whose code is already a mark is left alone, so a font that names its bullet correctly
    (SymbolMT's U+2022, 157 of them in the same sample) keeps what it says. The Symbol family itself is not a dingbat
    font - it spells Greek and maths - and is not included.
    """
    from truedoc.marks import MARK_TEXT, classify_mark
    from truedoc.math.reconstruct import is_math_font

    def private(c) -> bool:
        if len(c.text) != 1:
            return False
        return 0xE000 <= ord(c.text) <= 0xF8FF or (_dingbat_font(c.font) and c.text not in _DRAWN_MARKS)

    # A font of marks sets each private-use character as a word of its own; a font that spells words with them sets them
    # inside words. On the benchmark every private-use character of txfonts' small capitals (rtxsc, 218 on one page),
    # of an Advent journal font and of three unnamed embedded fonts sits in a word, where every tick and bullet on the
    # library sample's 24 pages stands alone - and a letter read on its own can pass for a box or a cross.
    spelled = {c.font for line in page.lines for word in line.words
               if sum(1 for ch in word.chars if ch.text and not ch.text.isspace()) > 1
               for c in word.chars if private(c)}
    read: set[int] = set()
    for line in page.lines:
        for word in line.words:
            for c in word.chars:
                if not private(c) or c.font in spelled or _needs_ink(c.font) or is_math_font(c.font):
                    continue
                named = _webdings_code(c)
                if named is not None:
                    word.text = word.text.replace(c.text, named)
                    c.text = named
                    read.add(id(word))
                    continue
                # Read through a square around the glyph's box. The box is the font's: a bullet's is as tall as its
                # line and a third as wide, and drawn onto the reader's square grid the dot inside came out flattened.
                side = max(c.bbox.width, c.bbox.height)
                square = BBox(c.bbox.cx - side / 2, c.bbox.cy - side / 2, c.bbox.cx + side / 2, c.bbox.cy + side / 2)
                try:
                    mark = classify_mark(pdf_page, square, glyph=True)
                except Exception:
                    continue
                if mark is not None and mark.kind in _READ_GLYPHS:
                    word.text = word.text.replace(c.text, MARK_TEXT[mark.kind])
                    c.text = MARK_TEXT[mark.kind]
                    read.add(id(word))
    # A mark read from a glyph that makes a line of its own starts the words beside it on its row, as a drawn mark does
    # (`pipeline._attach_marks`, by the same measures): RACQ's supplementary PDS sets each Symbol bullet 13pt before its
    # words, the text layer gives the two as separate lines, and every bullet came out as an empty list item. Another
    # line holding only such a mark is never the one joined, so two columns of ticks stay two columns.
    # A bullet the text layer already names is in the same position as one read from its drawing: ING's home SPDS, and
    # eighteen of sixty documents sampled from the library, set their bullets in a text run apart from their items, so
    # the line splitter leaves each one on a line of its own. With the layout model running, sixteen pages of that
    # sample's 386 still publish the orphan as an empty list item - 54 of them - while the items they marked run
    # together with nothing to tell them apart. The mark joins its words here, on the same measures.
    alone = {id(l): l for l in page.lines
             if not l.rotated and len(l.words) == 1
             and (id(l.words[0]) in read or l.words[0].text.strip() in _MARK_GLYPHS)}
    joined: set[int] = set()
    for key, mark_line in alone.items():
        m = mark_line.words[0]
        best = None
        for l in page.lines:
            if id(l) in alone or l.rotated or l.bbox.y1 < m.bbox.y0 or l.bbox.y0 > m.bbox.y1:
                continue
            if abs(l.bbox.cy - m.bbox.cy) > 0.7 * max(l.bbox.height, m.bbox.height):
                continue
            gap = l.bbox.x0 - m.bbox.x1
            if -1.0 <= gap <= 3.0 * max(m.size, 1.0) and (best is None or gap < best[0]):
                best = (gap, l)
        if best is not None:
            best[1].words.insert(0, m)
            best[1].bbox = best[1].bbox.union(m.bbox)
            joined.add(key)
    if joined:
        page.lines = [l for l in page.lines if id(l) not in joined]
        page.words = [w for l in page.lines for w in l.words]


def _big_numeral(a: Char, b: Char) -> bool:
    """One of two neighbours is a digit set at twice the size or more of the letter beside it.

    A numeral set far larger than the words beside it is a word of its own, and a space beside it is judged in the
    letters' type, not the numeral's. A Key Facts Sheet sets its step number at 48 points between "STEP" at 16 and
    "Understanding the Fact Sheet" at 12, 3.3 points from each: a word space for 12- or 16-point type, and under 8% of
    48, so it was taken for kerning and "STEP1Understanding" came out on every sheet of that design - noted on 16
    September 2026 and put down to the PDF, and found again by the word check (D040). Beside three step numbers in five
    the text layer does hold the space - the file's own, or one PDFium puts in the gap - and it was thrown away here;
    beside the rest the boxes touch, and the space the page shows comes from the type (`_numeral_then_capital`). A
    letter set large is not one: a drop cap is the start of its word."""
    big, small = (a, b) if a.size >= b.size else (b, a)
    return big.text.isdigit() and small.text.isalpha() and big.size >= 2.0 * max(small.size, 1.0)


def _numeral_then_capital(a: Char, b: Char) -> bool:
    """A numeral set large meets a letter where no word can run on: a new word however close the boxes sit.

    A digit is a narrow glyph in a wide box, so on some sheets of the same design the boxes touch though the page shows
    a clear space: the "1"'s box reaches the "U" of "Understanding" (144.9 against 144.8 on Apia's), and on others the
    "1" starts a point after the "P" of "STEP" (93.1 against 94.1 on AAMI's of 2023). A letter before a numeral twice
    its size never runs on into it, and a capital after one starts a word; a small letter after a numeral may be an
    ordinal's suffix ("1st"), and is left to the gap."""
    if not _big_numeral(a, b):
        return False
    return (a.text.isdigit() and b.text.isupper()) or (a.text.isalpha() and b.text.isdigit())


def _chars_to_words(chars: list[Char], ocr_layer: bool = False) -> list[Word]:
    """Group a line's characters into words.

    `ocr_layer`: the text is a hidden OCR layer, whose characters are spread
    evenly over each recognised word so that a real space shows up only as a
    gap somewhat larger than the letter gaps ("occurs as" with 0.6 pt against
    0.24 pt between letters).
    """
    words: list[Word] = []
    current: list[Char] = []
    after_space = False   # the word being built follows an explicit space character

    def flush():
        nonlocal current, after_space
        if current:
            text = "".join(c.text for c in current)
            if text.strip():
                words.append(Word(text=text, bbox=BBox.union_all(c.bbox for c in current), chars=list(current), after_space=after_space))
        current = []
        after_space = False

    # Letter-spaced text ("A n n u a l") has uniform gaps between every letter;
    # a gap only counts as a word break when it is also clearly larger than the
    # typical gap on this line.
    # The typical gap between neighbouring letters (touching letters count as
    # zero): a word break must stand clearly above it. Taking only the visibly
    # positive gaps would make the word gaps themselves the norm.
    gaps = []
    raw_gaps = []
    for a, b in zip(chars, chars[1:]):
        if a.text.isspace() or b.text.isspace():
            continue
        # Dot leaders ("Chapter 1 . . . . . 12") are spaced like words; only
        # letter and digit pairs say what the letter gap on this line is.
        if not (a.text.isalnum() and b.text.isalnum()):
            continue
        raw = b.bbox.x0 - a.bbox.x1
        raw_gaps.append(raw)
        gaps.append(max(0.0, raw))
    gaps.sort()
    raw_gaps.sort()
    median_gap = gaps[len(gaps) // 2] if gaps else 0.0
    # The unclipped median is negative when glyph boxes overlap their neighbours
    # (a font whose declared widths are wrong): the word-space rule below measures
    # from that baseline.
    raw_median = raw_gaps[len(raw_gaps) // 2] if raw_gaps else 0.0
    # The gap almost every letter pair on the line stays under: a word space in
    # a tiny bold caption (0.78 pt at 6.4 pt, "James Norwood") is under the
    # absolute floor below, yet stands far above the line's own letter gaps.
    high_gap = gaps[int(0.9 * (len(gaps) - 1))] if gaps else 0.0
    # OCR layers: the letter gap is judged per run between explicit spaces (one
    # run may be letter-spaced while its neighbours touch). A word gap inside a
    # run must stand clearly above that run's letter gap; when almost no letter
    # pair in the run shows a gap (a monospaced layer), any gap is a word gap.
    tok_stats: dict[int, tuple[float, float, float]] = {}
    if ocr_layer:
        start = 0
        for i in range(len(chars) + 1):
            if i == len(chars) or chars[i].text.isspace():
                run = chars[start:i]
                tg = sorted(max(0.0, b.bbox.x0 - a.bbox.x1) for a, b in zip(run, run[1:]) if a.text.isalnum() and b.text.isalnum())
                tpos = [g for g in tg if g > 0.05]
                stats = (tg[len(tg) // 2] if tg else 0.0, len(tpos) / len(tg) if tg else 0.0, tpos[len(tpos) // 2] if tpos else 0.0)
                for k in range(start, i):
                    tok_stats[k] = stats
                start = i + 1

    prev: Char | None = None
    for i, c in enumerate(chars):
        # (A space reported in a TeX symbol font is usually MuPDF's synthesised
        # word space wearing the neighbouring span's font, not an unmapped glyph:
        # reading such spaces as negation slashes lost 16 checks on five pages.)
        if c.text.isspace():
            # MuPDF inserts a space wherever it sees a gap; at a kerning gap the
            # "space" is spurious (Type 3 fonts mislead its width estimate). Not
            # on an OCR layer: its spaces are the engine's own word breaks, and
            # its glyph boxes overlap at them ("Fractures extend" glued into one
            # word on a scanned journal page lost thirteen checks).
            nxt = next((d for d in chars[i + 1:] if not d.text.isspace()), None)
            if not ocr_layer and prev is not None and not prev.text.isspace() and nxt is not None and current:
                # A space after a comma, or after a full stop before a capital, is
                # a real one however tight the setting ("However, state" at 0.07 em
                # in Caslon); the kerning-gap doubt is about spaces inside words.
                after_punct = prev.text in ",;:!?" or (prev.text == "." and nxt.text.isupper())
                # Beside a numeral set far larger than its words the space is real however narrow it looks against
                # the numeral (`_big_numeral`).
                if not after_punct and not _big_numeral(prev, nxt) and nxt.bbox.x0 - prev.bbox.x1 < 0.08 * max(prev.size, nxt.size, 1.0):
                    continue
            flush()
            after_space = True
            prev = c
            continue
        if prev is not None and current:
            gap = c.bbox.x0 - prev.bbox.x1
            size = max(c.size, prev.size, 1.0)
            if _dingbat_font(prev.font) != _dingbat_font(c.font) and prev.text.isalnum() and c.text.isalnum():
                # A letter or digit in a dingbat font is a code for a picture, not a letter (see
                # `_read_private_glyphs`), so it shares no word with the text beside it. A Webdings bullet set hard
                # against its item - its box a point into the next letter, no space between - made "4artificial grass
                # or turf" of a storm exclusion list (found by the word check, D040). A mark already named as one
                # ("→", "✓") is left where it stands: "INTMRK→BRDORT" is one path of a model, and one word.
                flush()
            elif _numeral_then_capital(prev, c) or (_big_numeral(prev, c) and gap > max(0.13 * min(c.size, prev.size), 0.9)):
                # The same numeral where the text layer has no space at all ("STEP" then "1", 3.3 points apart): the
                # gap is a word space in the letters' type, whatever it is in the numeral's.
                flush()
            # No explicit space but a visible gap: treat as a word break. Justified
            # narrow columns squeeze word spaces to about 0.14 em.
            elif gap > max(0.13 * size, 0.9) and gap > 1.6 * median_gap:
                flush()
            elif gap > raw_median + 0.25 * size:
                # Glyph boxes wider than the glyphs (a font whose declared widths are
                # wrong) overlap their neighbours by a constant amount; a word space
                # still stands a quarter of an em above that constant.
                flush()
            elif (not ocr_layer and len(gaps) >= 6 and gap > 0.1 * size and gap > 3.0 * high_gap
                  and gap > raw_median + 0.1 * size and c.text.isalnum() and prev.text.isalnum()):
                # Tiny type: a tenth of an em that nine letter pairs in ten stay
                # well under is a word space, whatever the absolute floor says.
                flush()
            elif ocr_layer and gap > max(0.04 * size, 0.3):
                tok_median, tok_pos_share, tok_pos_median = tok_stats.get(i, (median_gap, 0.0, 0.0))
                if gap > 2.0 * tok_median and (tok_pos_share < 0.3 or gap > 1.8 * tok_pos_median):
                    flush()
        current.append(c)
        prev = c
    flush()
    return _merge_letter_spaced(words)


def _merge_letter_spaced(words: list[Word]) -> list[Word]:
    """Re-join text typeset with a space between every letter ("A n n u a l").

    If most "words" on the line are single characters, the small uniform gaps
    are letter spacing and only clearly larger gaps are real word breaks.
    """
    if len(words) < 6:
        return words
    # Dot leaders ("Chapter 1 . . . . 12") are single characters too, but not letters.
    singles = sum(1 for w in words if len(w.text) == 1 and w.text.isalnum())
    if singles < 0.7 * len(words):
        return words
    gaps = [b.bbox.x0 - a.bbox.x1 for a, b in zip(words, words[1:])]
    pos = sorted(g for g in gaps if g > 0)
    if not pos:
        return words
    median = pos[len(pos) // 2]
    # Letter spacing is a fraction of the em; single characters standing more than three
    # quarters of one apart are a row of cells - a rating scale's "1 2 3 ... 10", 1.35 em
    # apart, read as one number 12345678910 (MuPDF never showed the rule such a line: it
    # cuts lines at those gaps itself, and the cells reached it one to a line).
    size = max((c.size for w in words for c in w.chars), default=0.0)
    if size > 0 and median > 0.75 * size:
        return words
    merged: list[Word] = [words[0]]
    for gap, w in zip(gaps, words[1:]):
        if gap <= 1.5 * median:
            last = merged[-1]
            merged[-1] = Word(text=last.text + w.text, bbox=last.bbox.union(w.bbox), chars=last.chars + w.chars)
        else:
            merged.append(w)
    return merged


def _column_gutters(lines: list[Line]) -> list[tuple[float, float]]:
    """Vertical white channels that separate columns of text.

    An x-interval that almost no line's words cross, with substantial text on
    both sides of it, is a column gutter. Segments are never joined across one
    (justified two-column text often leaves a gutter narrower than the word
    spaces it stretches). A table's column gaps qualify only when the table
    fills most of the page, and keeping its cells apart is right then.
    """
    segs = [l for l in lines if not l.rotated and l.words]
    if len(segs) < 12:
        return []
    x0 = min(l.bbox.x0 for l in segs)
    x1 = max(l.bbox.x1 for l in segs)
    width = x1 - x0
    if width < 50:
        return []
    size = max(1.0, sorted(l.size for l in segs)[len(segs) // 2])
    bins = int(width) + 1
    crossing = [0] * bins
    for l in segs:
        covered = set()
        for w in l.words:
            if _is_line_number(w):
                continue  # US patents number their lines in the gutter itself
            a = max(0, int(w.bbox.x0 - x0))
            b = min(bins, int(w.bbox.x1 - x0) + 1)
            covered.update(range(a, b))
        for i in covered:
            crossing[i] += 1
    limit = max(1, int(0.03 * len(segs)))
    gutters: list[tuple[float, float]] = []
    i = 0
    while i < bins:
        if crossing[i] > limit:
            i += 1
            continue
        j = i
        while j < bins and crossing[j] <= limit:
            j += 1
        gx0, gx1 = x0 + i, x0 + j
        centre = (gx0 + gx1) / 2 - x0
        # An old two-column paper with ragged column edges (OCR'd text layers)
        # leaves a channel only three or four points wide that almost no line
        # crosses; near the middle of the page that is a gutter too.
        # The channel's core: its longest stretch that next to no line crosses
        # (the channel itself may include shoulder bins crossed by a few lines).
        thr = max(1, int(0.015 * len(segs)))
        core = run = 0
        for k in range(i, j):
            run = run + 1 if crossing[k] <= thr else 0
            core = max(core, run)
        narrow_ok = core >= 0.3 * size and 0.35 * width <= centre <= 0.65 * width
        if os.environ.get("TRUEDOC_GUTTER_DEBUG"):
            print(f"[gutter] channel x={gx0:.0f}-{gx1:.0f} width={gx1 - gx0:.1f} core={core} size={size:.1f} centre={centre / width:.2f} narrow_ok={narrow_ok}")
        if (gx1 - gx0 >= 0.7 * size or narrow_ok) and 0.15 * width <= centre <= 0.85 * width:
            # Text on both sides, counted by words: MuPDF may already have joined
            # the two columns' lines, so segments alone would not show the split.
            words = [w for l in segs for w in l.words]
            left = sum(1 for w in words if w.bbox.x1 <= gx0 + 0.5)
            right = sum(1 for w in words if w.bbox.x0 >= gx1 - 0.5)
            if words and left >= 0.2 * len(words) and right >= 0.2 * len(words):
                gutters.append((gx0, gx1))
        i = j
    # Many channels means aligned text (a table, a listing), not columns; the
    # table finder owns those.
    if len(gutters) > 3:
        return []
    for g in _edge_gutters(segs, x0, width, size):
        # A strict channel inside an edge gutter is the core of it: the edges say how wide.
        inside = [h for h in gutters if g[0] < h[1] and h[0] < g[1]]
        for h in inside:
            gutters.remove(h)
        gutters.append((min([g[0]] + [h[0] for h in inside]), max([g[1]] + [h[1] for h in inside])))
    return sorted(gutters) if len(gutters) <= 3 else []


def _edge_gutters(segs: list[Line], x0: float, width: float, size: float) -> list[tuple[float, float]]:
    """Gutters shown by the columns' edges when lines cross the channel.

    A Physical Review Letters page sets its title, authors and abstract across both columns
    and MuPDF joins ten body lines across its 16-point gutter, so more lines cross the
    channel than the strict scan allows and the two columns read as one (53 pages of run
    60). The columns' edges still show it: a good share of the lines start at the right
    column's edge, and the lines wholly left of that edge end just before it. Lines that
    cross with words on both sides must stay a minority (a form's label and value columns
    are not two columns of text)."""
    n = len(segs)
    starts: dict[int, int] = {}
    for l in segs:
        k = int(round(l.bbox.x0 / 2.0)) * 2
        starts[k] = starts.get(k, 0) + 1
    out: list[tuple[float, float]] = []
    for k, count in sorted(starts.items(), key=lambda kv: -kv[1])[:6]:
        if count < 0.15 * n or not (x0 + 0.25 * width <= k <= x0 + 0.75 * width):
            continue
        right = float(k) - 1.0
        ends = [l.bbox.x1 for l in segs if l.bbox.x1 < right - 0.2 * size and l.bbox.x1 >= right - 0.35 * width]
        if len(ends) < 0.15 * n:
            continue
        left = max(ends)
        if right - left < 0.3 * size:
            continue
        both = sum(1 for l in segs if l.bbox.x0 < left - 0.2 * size and l.bbox.x1 > right + 0.2 * size
                   and any(w.bbox.x1 <= left + 0.5 for w in l.words) and any(w.bbox.x0 >= right - 0.5 for w in l.words))
        if both > 0.35 * n:
            continue
        words = [w for l in segs for w in l.words]
        mid = (left + right) / 2.0
        spanning = sum(1 for w in words if w.bbox.x0 < mid < w.bbox.x1)
        if spanning > 0.2 * n:
            continue
        if sum(1 for w in words if w.bbox.x1 <= left + 0.5) < 0.2 * len(words) or sum(1 for w in words if w.bbox.x0 >= right - 0.5) < 0.2 * len(words):
            continue
        out.append((left, right))
    return out


# TeX's underscore, in ems of the type it is set in. `\_` is not a character there: plain TeX and LaTeX's OT1
# encoding set it as `\kern.06em\vbox{\hrule width.3em}` - a rule three tenths of an em long and 0.4 pt thick, on the
# baseline, a kern after the word before and hard against the word after. Measured on the benchmark before this was
# written (`bench/probes/drawn_underscore_census.py`, 20 September 2026): every one of 18 on five pages reads
# length 0.30-0.34, kern 0.06-0.07, gap after 0.00, 0.02-0.03 above the baseline; the rules that are something else -
# a dotted underline's dashes, a plot's tick, a 0.9 em rule under a heading - miss at least two of the four.
_TEX_UNDERSCORE_LENGTH = (0.27, 0.37)
_TEX_UNDERSCORE_KERN = (0.03, 0.10)
_TEX_UNDERSCORE_TOUCH = 0.03
_TEX_UNDERSCORE_RISE = (-0.01, 0.06)          # how far its middle stands ABOVE the baseline
_TEX_UNDERSCORE_THICK = 0.08


def _short_rules(pdf_page: "pymupdf.Page", M=None) -> list[BBox]:
    """Horizontal rules no longer than a wide letter. `_extract_drawings` keeps nothing under 2.5 points, and an
    underscore in six-point type is 1.8 points long."""
    out: list[BBox] = []
    objs = pdfium_objects.page_objects(pdf_page.parent.name, pdf_page.number + 1) if pdfium_objects.enabled() else None
    if objs is not None:
        for o in objs:
            if o.kind != "path":
                continue
            # The segment a path strokes and the rectangle it fills, not its bounding box: PDFium's box for a stroked
            # rule is the rule grown by its stroke width on every side (3.49 points for a rule of 2.69), which is a
            # third of what is being measured.
            half = 0.5 * (o.stroke_width or 0.0)
            for x0, y0, x1, y1 in o.lines:
                r = _rect((min(x0, x1), min(y0, y1) - half, max(x0, x1), max(y0, y1) + half), M)
                if r.height <= 1.5 and 0.8 <= r.width <= 14.0:
                    out.append(r)
            for rect in o.rects:
                r = _rect(tuple(rect), M)
                if r.height <= 1.5 and 0.8 <= r.width <= 14.0:
                    out.append(r)
        return out
    try:
        for d in pdf_page.get_drawings():
            r = _rect(d["rect"], M)
            if r.height <= 1.5 and 0.8 <= r.width <= 14.0:
                out.append(r)
    except Exception:
        pass
    return out


def _read_drawn_underscores(pdf_page: "pymupdf.Page", page: Page, M=None) -> None:
    """An underscore TeX drew between two words is written between them, and they are one word.

    "Japanese_spaniel" in a table of class names, "F1 Score_RCNN" in a heading, "DECC23_012_DIP" in running text: the
    PDF's text holds the pieces and nothing between them, so they came out as separate words and an identifier lost
    what makes it one. It is a mark the page draws, like a tick or an arrow, and is read by where and how it is drawn
    - only TeX's own underscore, to the fingerprint above, between a letter or digit and a letter or digit."""
    if not any(len(l.words) >= 2 for l in page.lines):
        return
    rules = _short_rules(pdf_page, M)
    if not rules:
        return
    changed = False
    read: list[BBox] = []
    for li, line in enumerate(page.lines):
        if line.rotated or len(line.words) < 2:
            continue
        words = sorted(line.words, key=lambda w: w.bbox.x0)
        out: list[Word] = [words[0]]
        for w in words[1:]:
            prev = out[-1]
            mark = _tex_underscore_between(prev, w, rules)
            if mark is None:
                out.append(w)
                continue
            read.append(mark)
            first = w.chars[0]
            under = Char(text="_", bbox=mark, font=first.font, size=first.size, flags=first.flags, color=first.color, origin_y=first.origin_y)
            out[-1] = Word(text=prev.text + "_" + w.text, bbox=prev.bbox.union(w.bbox), chars=prev.chars + [under] + w.chars)
            changed = True
        if len(out) != len(words):
            page.lines[li] = Line(words=out, bbox=line.bbox, rotated=line.rotated)
    if changed:
        page.words = [w for l in page.lines for w in l.words]
        # It is a character now and no longer a rule: left among the drawings, the maths reader took the same stroke
        # for a bar over the new character and wrote `\overline{\_}` (arxiv_math/2503.04690 page 4).
        page.drawings = [d for d in page.drawings
                         if not (d.kind == "hline" and d.bbox.width <= 14.0
                                 and any(d.bbox.x0 <= m.x1 + 1.0 and d.bbox.x1 >= m.x0 - 1.0 and abs(d.bbox.cy - m.cy) <= 1.0 for m in read))]


def _tex_underscore_between(a: Word, b: Word, rules: list[BBox]) -> BBox | None:
    if not (a.chars and b.chars and a.text[-1:].isalnum() and b.text[:1].isalnum()):
        return None
    size = b.chars[0].size or 0.0
    base = b.chars[0].origin_y
    if size <= 0 or not base:
        return None
    for r in rules:
        if not (a.bbox.x1 - 0.5 <= r.x0 and r.x1 <= b.bbox.x0 + 0.5):
            continue
        if (_TEX_UNDERSCORE_LENGTH[0] <= r.width / size <= _TEX_UNDERSCORE_LENGTH[1]
                and _TEX_UNDERSCORE_KERN[0] <= (r.x0 - a.bbox.x1) / size <= _TEX_UNDERSCORE_KERN[1]
                and abs(b.bbox.x0 - r.x1) / size <= _TEX_UNDERSCORE_TOUCH
                and _TEX_UNDERSCORE_RISE[0] <= (base - r.cy) / size <= _TEX_UNDERSCORE_RISE[1]
                and r.height / size <= _TEX_UNDERSCORE_THICK):
            return r
    return None


def _fuse_touching_words(line: Line) -> Line:
    """Join words that touch or overlap: pieces of one word that the producer
    emitted as separate text objects (Type 3 fonts do this mid-word). A real
    word space is never narrower than about a tenth of the size."""
    words = line.words
    if len(words) < 2:
        return line
    # When glyph boxes overlap their neighbours throughout the line (a font whose
    # declared widths are wrong), "touching" is measured from that overlap, or
    # every word space would be fused away.
    chars = [c for w in words for c in w.chars if not c.text.isspace()]
    raw = sorted(b.bbox.x0 - a.bbox.x1 for a, b in zip(chars, chars[1:]))
    base = min(0.0, raw[len(raw) // 2]) if raw else 0.0
    out: list[Word] = [words[0]]
    for w in words[1:]:
        prev = out[-1]
        size = max(prev.size, w.size, 1.0)
        # A word that follows an explicit space character in the text layer is a
        # word of its own however close it sits: a tight sentence space after a
        # full stop ("platform. These", 0.1 em in Caslon), or a drop cap whose
        # box reaches the next word ("The" + "Chief").
        if w.after_space:
            out.append(w)
            continue
        # The two word breaks `_chars_to_words` makes by type rather than by gap hold here too, or this pass undoes
        # them: a numeral set far larger than its words is judged in the letters' type (3.3 points from "STEP" is
        # under a tenth of 48, not of 16), and a code in a dingbat font shares no word with text. Nor does the mark
        # `_read_private_glyphs` has since read from such a code - a bullet, box, tick or cross: Budget Direct's
        # Webdings bullet, its box a point into its item, came out "‣garages," 101 times over 40 pages. An arrow is
        # not such a mark, and stays inside its word ("INTMRK→BRDORT").
        a = next((c for c in reversed(prev.chars) if not c.text.isspace()), None)
        b = next((c for c in w.chars if not c.text.isspace()), None)
        if a is not None and b is not None:
            if ((_dingbat_font(a.font) != _dingbat_font(b.font) and a.text.isalnum() and b.text.isalnum())
                    or _numeral_then_capital(a, b)
                    or any(_dingbat_font(c.font) and c.text in _DRAWN_MARKS for c in (a, b))):
                out.append(w)
                continue
            if _big_numeral(a, b):
                size = max(min(a.size, b.size), 1.0)
        if w.bbox.x0 - prev.bbox.x1 < base + 0.1 * size and w.bbox.y_overlap(prev.bbox) > 0:
            out[-1] = Word(text=prev.text + w.text, bbox=prev.bbox.union(w.bbox), chars=prev.chars + w.chars)
        else:
            out.append(w)
    if len(out) == len(words):
        return line
    return Line(words=out, bbox=line.bbox, rotated=line.rotated)


def _is_line_number(w: Word) -> bool:
    return w.text.isdigit() and len(w.text) <= 3


def _in_gutter(w: Word, gutters: list[tuple[float, float]]) -> bool:
    return any(g0 - 1.0 <= w.bbox.cx <= g1 + 1.0 for g0, g1 in gutters)


def _gap_crosses_gutter(a: float, b: float, gutters: list[tuple[float, float]]) -> bool:
    """The gap between two neighbours touches a gutter (a line number printed in
    the gutter must not bridge the columns on either side of it)."""
    lo, hi = min(a, b), max(a, b)
    return any(hi > g0 and lo < g1 for g0, g1 in gutters)


def _gap_covers_gutter(a: float, b: float, gutters: list[tuple[float, float]], size: float) -> bool:
    """The gap between two neighbours covers a gutter: all of a narrow one, and of a wide
    one at least 0.7 em (a full-width title's word spaces touch a wide gutter without
    covering it)."""
    lo, hi = min(a, b), max(a, b)
    for g0, g1 in gutters:
        overlap = min(hi, g1) - max(lo, g0)
        if overlap >= min(0.7 * (g1 - g0), 0.7 * size) and overlap > 0:
            return True
    return False


def _lone_gutter_number(line: Line, gutters: list[tuple[float, float]]) -> bool:
    return len(line.words) == 1 and _is_line_number(line.words[0]) and _in_gutter(line.words[0], gutters)


def _split_at_gutters(lines: list[Line], gutters: list[tuple[float, float]]) -> list[Line]:
    """Split segments that MuPDF joined across a column gutter.

    A line number sitting in the gutter becomes a segment of its own, so that
    the columns on either side of it stay apart.
    """
    if not gutters:
        return lines
    out: list[Line] = []
    for l in lines:
        if l.rotated or len(l.words) < 2:
            out.append(l)
            continue
        groups: list[list[Word]] = [[l.words[0]]]
        size = max(l.size, 1.0)
        for prev, w in zip(l.words, l.words[1:]):
            # A word gap splits at a wide gutter only when it covers most of it: the word
            # spaces of a title set across both columns do not.
            if _gap_covers_gutter(prev.bbox.x1, w.bbox.x0, gutters, size) or (_is_line_number(w) and _in_gutter(w, gutters)) or (_is_line_number(prev) and _in_gutter(prev, gutters)):
                groups.append([w])
            else:
                groups[-1].append(w)
        if len(groups) == 1:
            out.append(l)
        else:
            out.extend(Line(words=g, bbox=BBox.union_all(w.bbox for w in g)) for g in groups)
    return out


def _ends_with_extension_glyph(line: Line) -> bool:
    """The segment's last drawn character comes from a maths-extension font."""
    for w in reversed(line.words):
        for c in reversed(w.chars):
            if not c.text.isspace():
                return _needs_ink(c.font)
    return False


def _reassemble_lines(lines: list[Line], gutters: list[tuple[float, float]] | None = None, rules: list[BBox] | None = None) -> list[Line]:
    """Re-join segments that a PDF producer emitted word by word.

    Some producers position every word separately, so MuPDF reports one line
    per word. Segments on the same baseline separated by no more than a word
    space (up to about one em, justified text stretches that far) are merged,
    never across a column gutter.
    """
    if len(lines) < 2:
        return lines
    gutters = gutters or []
    # A radical or a wide accent arrives as a segment of its own between the two
    # halves of its line; fold it in first, so the halves measure their gap
    # across it rather than around it.
    lines = _fold_symbol_lines(list(lines), early=True, rules=rules)
    ordered = sorted(lines, key=lambda l: (round(l.baseline, 1), l.bbox.x0))
    rows = _column_rows(ordered, gutters) if gutters else {}
    measures = _column_measures(rows) if rows else {}
    out: list[Line] = []
    for seg in ordered:
        if seg.rotated or not out:
            out.append(seg)
            continue
        last = out[-1]
        # OCR text layers carry meaningless font sizes; the box height is the reliable unit.
        size = max(seg.size, last.size, 0.7 * seg.bbox.height, 0.7 * last.bbox.height, 1.0)
        same_baseline = abs(seg.baseline - last.baseline) <= 0.3 * size
        gap = seg.bbox.x0 - last.bbox.x1
        # A wide accent at the end of a segment overhangs the letter it covers,
        # which MuPDF starts the next segment with: allow the overlap.
        overhang = 1.5 if _ends_with_extension_glyph(last) else 1.0
        similar_size = 0.8 <= (seg.size or size) / (last.size or size) <= 1.25
        # A justified line stretches its word gaps; a neighbour segment whose gap
        # matches those internal gaps is part of the same line.
        limit = 1.0 * size
        for ref in (last, seg):
            if len(ref.words) >= 3:
                inner = sorted(b.bbox.x0 - a.bbox.x1 for a, b in zip(ref.words, ref.words[1:]))
                limit = max(limit, min(1.4 * inner[len(inner) // 2], 2.2 * size))
        # Two segments that together run from a column's left edge to its right edge are
        # one justified line whatever the stretch of the gap between them, up to an em and
        # a half ("with the name, El Nino?" | "Resisting the tempta-", 09f90a8fad in run 60:
        # the second half became a block of its own, read after the other column).
        if measures:
            col = _column_of(seg, gutters)
            ext = rows.get((col, int(round(seg.baseline))))
            m = measures.get(col)
            if ext and m and _column_of(last, gutters) == col and abs(ext[0] - m[0]) <= 0.6 * size and abs(ext[1] - m[1]) <= 0.6 * size:
                limit = max(limit, 1.5 * size)
        # A stretched gap is joined unless a channel of white runs through it: two narrow
        # columns whose gutter went unfound (a newspaper page) leave their lines' word gaps
        # as wide as the gutter, and no word on any nearby line crosses the gutter.
        if gap > 1.0 * size and limit > 1.0 * size and _channel_through(last.bbox.x1, seg.bbox.x0, seg.baseline, ordered, size):
            limit = 1.0 * size
        # Segments may overlap horizontally when one starts with the denominator of an
        # inline fraction that sits under the previous segment's numerator.
        # A segment that is only a big bracket or operator has no baseline of its
        # own (the glyph's origin sits at its top): it joins on adjacency alone.
        # The symbol must stand at the end of the segment it joins: a bracket
        # inside the span of a full-width line above (whose baseline sort puts
        # it next) belongs to the line it overlaps, folded in afterwards.
        symbol = (_symbol_only(seg) or _symbol_only(last)) and seg.bbox.y_overlap(last.bbox) > 0 and -0.3 * size <= gap <= 0.6 * size
        # Segments that interleave (a formula's superscripts and the symbols after
        # them come out as separate, overlapping segments) are one line as long as
        # no two words coincide; coinciding words would be a duplicated text layer.
        # Only lines carrying scripts or maths symbols interleave this way; table cells
        # and OCR layers with loose boxes must keep their separate segments.
        interleaved = gap < -1.0 * size and same_baseline and similar_size and (_has_scripts(seg) or _has_scripts(last)) and _words_interleave(last.words, seg.words)
        # Whichever half sorts first (a maths glyph's baseline a tenth of a point off puts the
        # right half before the left), two segments on opposite sides of a gutter stay apart:
        # the formula path below used to glue a left column's line to the right column's.
        first, second = (last, seg) if last.bbox.x0 <= seg.bbox.x0 else (seg, last)
        across_gutter = (any(first.bbox.x1 <= g1 + 1.0 and second.bbox.x0 >= g0 - 1.0 for g0, g1 in gutters)
                         or _lone_gutter_number(seg, gutters) or _lone_gutter_number(last, gutters))
        # A sum sign with its limits, or a stacked fraction, stands between the
        # two halves of a text line as segments of its own ("the length of P is"
        # [sum, n, i=1] "w(v_i) and the ..."): the halves are one line when the
        # gap is filled by such a segment on either side of which the gaps are
        # ordinary. The filler is attached to the line as a satellite later.
        bridged = False
        if gap > limit and same_baseline and similar_size and not across_gutter and not os.environ.get("TRUEDOC_NO_BRIDGE"):
            for m in ordered:
                if m is seg or m is last or m.rotated:
                    continue
                # Only a maths filler bridges the halves: script-sized glyphs (a
                # stacked fraction, limits) or an extension-font sign. A full-size
                # word between two segments (a dictionary's entry word) is a line
                # of its own and must not be swallowed.
                m_chars = [c for w in m.words for c in w.chars if not c.text.isspace()]
                # A mark of punctuation alone is no filler: PDFium hands 2503.06630's comma between
                # two fractions over as a segment of its own, and taken for a filler it welded the two
                # denominators into one segment that no fraction bar covers, so neither fraction
                # formed (MuPDF keeps the comma with the numerator after it).
                if not m_chars or all(c.text in ",.;:" for c in m_chars):
                    continue
                # A text-size glyph in the filler is fine when it is set in a maths
                # font: the coefficient between a text-style sum's limits and the
                # fraction that follows ("c(t) = sum_{i=0}^inf c_i t^i/i! is ...").
                maths_only = all(c.size < 0.85 * size or _needs_ink(c.font) or _is_math_font_mark(c.font) for c in m_chars)
                if not (max(c.size for c in m_chars) < 0.85 * size or any(_needs_ink(c.font) for c in m_chars) or maths_only):
                    continue
                # The filler may overlap either half a little: a sum's lower limit
                # often starts the right half, under the sign's own box.
                if m.bbox.x0 >= last.bbox.x1 - 1.0 * size and m.bbox.x1 <= seg.bbox.x0 + 1.0 * size \
                        and m.bbox.x0 < seg.bbox.x0 and m.bbox.x1 > last.bbox.x1 \
                        and (m.bbox.y_overlap(last.bbox) > 0 or m.bbox.y_overlap(seg.bbox) > 0) \
                        and m.bbox.x0 - last.bbox.x1 <= limit and seg.bbox.x0 - m.bbox.x1 <= limit:
                    bridged = True
                    break
        # (Neither segment may be vertical text: a scanner's "Downloaded from ..."
        # stamp running up the margin shares a baseline with some body line and
        # used to be glued into it, only to be judged later as a header.)
        if (symbol or interleaved or (same_baseline and similar_size)) and not last.rotated and not seg.rotated and not across_gutter and (interleaved or bridged or -overhang * size <= gap <= limit):
            out[-1] = Line(words=sorted(last.words + seg.words, key=lambda w: w.bbox.x0), bbox=last.bbox.union(seg.bbox))
        else:
            out.append(seg)
    return _attach_satellites(_merge_uniform_rows(_fold_symbol_lines(out, rules=rules), gutters), rules)


def _channel_through(x0: float, x1: float, baseline: float, lines: list[Line], size: float) -> bool:
    """A vertical channel of white runs through the gap (x0, x1): on the lines within a dozen
    line heights, no word covers its middle. Two narrow columns whose gutter went unfound show
    as such a channel, and as their lines share baselines their union passed for one
    full-width line (a newspaper page, 20_pg46, and 03ccfe8bb1 in run 62)."""
    mid = (x0 + x1) / 2.0
    seen: set[int] = set()
    crossed = False
    for l in lines:
        if l.rotated or not l.words or not (0.5 * size < abs(l.baseline - baseline) <= 12.0 * size):
            continue
        seen.add(int(round(l.baseline)))
        if any(w.bbox.x0 < mid < w.bbox.x1 for w in l.words):
            crossed = True
    return len(seen) >= 6 and not crossed


def _column_of(line: Line, gutters: list[tuple[float, float]]) -> int:
    """Which column a segment sits in: the number of gutters to its left."""
    return sum(1 for g in gutters if line.bbox.x0 >= g[1] - 1.0)


def _column_rows(lines: list[Line], gutters: list[tuple[float, float]]) -> dict[tuple[int, int], list[float]]:
    """Per column and baseline, the extent of the segments on that line: a producer that
    places every word on its own gives a line as many segments, and their union is the line."""
    rows: dict[tuple[int, int], list[float]] = {}
    for l in lines:
        if l.rotated or not l.words:
            continue
        r = rows.setdefault((_column_of(l, gutters), int(round(l.baseline))), [l.bbox.x0, l.bbox.x1])
        r[0], r[1] = min(r[0], l.bbox.x0), max(r[1], l.bbox.x1)
    return rows


def _column_measures(rows: dict[tuple[int, int], list[float]]) -> dict[int, tuple[float, float]]:
    """Each column's left and right edge: the tenth and ninetieth percentiles of its lines'
    edges. A measure is one column's only when most of its lines run its full width: two
    columns whose gutter went unfound would otherwise pass for one wide measure, and lines
    joined across it (a newspaper page, 20_pg40)."""
    out: dict[int, tuple[float, float]] = {}
    for col in {c for c, _ in rows}:
        exts = [r for (c, _), r in rows.items() if c == col]
        if len(exts) < 4:
            continue
        x0s = sorted(r[0] for r in exts)
        x1s = sorted(r[1] for r in exts)
        c0, c1 = x0s[int(0.1 * (len(x0s) - 1))], x1s[int(0.9 * (len(x1s) - 1))]
        if sum(1 for r in exts if r[1] - r[0] >= 0.85 * (c1 - c0)) >= 0.5 * len(exts):
            out[col] = (c0, c1)
    return out


def _radical_or_accent_segment(line: Line) -> bool:
    """A segment that is only a root sign or a wide accent: it splits a text line
    in two and must be folded before the halves measure their gap. Bracket
    pieces are not: they frame matrix rows that are merged first."""
    for w in line.words:
        for c in w.chars:
            if c.text.isspace():
                continue
            latex = latex_for_char(c.text, c.font)
            if c.text != "√" and not latex.startswith(r"\sqrt") and not latex.startswith(_WIDE_ACCENT_COMMANDS):
                return False
    return True


_WIDE_ACCENT_COMMANDS = (r"\hat", r"\widehat", r"\tilde", r"\widetilde", r"\vec", r"\bar", r"\overline", r"\check", r"\breve")


def _fold_symbol_lines(lines: list[Line], early: bool = False, rules: list[BBox] | None = None) -> list[Line]:
    """Fold a line holding only maths-extension glyphs into the text line beside it.

    A tall bar or bracket is drawn from pieces whose origins sit on other
    baselines, so the baseline sort leaves them as lines of their own; they
    belong to the text line they overlap vertically and touch horizontally.

    Before the halves of a line are merged (`early`), only a host whose
    baseline runs through the symbol takes it, and a symbol taller than about
    two lines (a matrix bracket spanning several rows) waits for the fold after
    the merge: folded early, it landed in whichever row or prose line stood
    nearest. A one-line bracket or root sign must be folded early, or the
    baseline sort puts it next to the full-width line above and the two merge.
    """
    symbols = [l for l in lines if not l.rotated and _symbol_only(l)]
    if not symbols:
        return lines
    hosts = [l for l in lines if not l.rotated and not _symbol_only(l)]
    consumed: set[int] = set()
    for sym in symbols:
        size = max(sym.size, 1.0)
        # (A "root sign standing on a fraction bar goes to the line below" rule was
        # tried on 4-5 Sept for the inline "\frac{\sqrt{n-1}}{\sqrt{n-2}}" of
        # 2503.06459; it never won that page and, with two inline roots on
        # consecutive lines, took the lower root's bar for a fraction bar and
        # broke "(0.098, \sqrt{0.098})" on 2503.08374. Withdrawn; `rules` stays
        # in the signature for a better attempt.)
        best, best_key = None, (0.0, 1e9)
        for host in hosts:
            overlap = host.bbox.y_overlap(sym.bbox)
            if overlap <= 0:
                continue
            if early:
                hs = max(host.size, 1.0)
                if not (sym.bbox.y0 - 0.1 * hs <= host.baseline <= sym.bbox.y1 + 0.1 * hs):
                    continue
                if sym.bbox.height > 2.2 * hs and not _radical_or_accent_segment(sym):
                    continue
            gap = max(sym.bbox.x0 - host.bbox.x1, host.bbox.x0 - sym.bbox.x1)
            # The line the piece shares most of its height with, then the nearest
            # (a full-width line above would otherwise always "contain" it).
            key = (overlap, -gap)
            if gap <= 0.6 * size and key > best_key:
                best, best_key = host, key
        if best is not None:
            consumed.add(id(sym))
            best.words = sorted(best.words + sym.words, key=lambda w: w.bbox.x0)
            best.bbox = best.bbox.union(sym.bbox)
    return [l for l in lines if id(l) not in consumed]


_ACCENT_ONLY_CHARS = set("˙¯ˆ˜¨´`˘ˇ˚‾ˉ~^")
_BIG_OPERATOR_LATEX = {r"\int", r"\oint", r"\iint", r"\iiint", r"\sum", r"\prod", r"\coprod", r"\bigcup", r"\bigcap",
                       r"\bigoplus", r"\bigotimes", r"\bigodot", r"\bigvee", r"\bigwedge", r"\bigsqcup", r"\biguplus"}


_DISPLAY_TYPE_PT = 40.0  # text set larger than this is a headline, not a formula's host


def _join_drop_caps(lines: list[Line]) -> list[Line]:
    """Put a drop cap back on the first word of its paragraph.

    A newspaper or magazine sets the first letter of an article two to four
    lines tall, and MuPDF reports it as a line of its own beside the paragraph
    ("L" then "e gouvernement cultive ..."). The letter joins the first word of
    the topmost line that starts at its right edge within its height.
    """
    if len(lines) < 2:
        return lines
    consumed: set[int] = set()
    for cap in lines:
        if cap.rotated or len(cap.words) != 1:
            continue
        chars = [c for c in cap.words[0].chars if not c.text.isspace()]
        if len(chars) != 1 or not chars[0].text.isalpha() or _needs_ink(chars[0].font):
            continue
        cs = chars[0].size or cap.bbox.height
        firsts = []
        for l in lines:
            if l is cap or l.rotated or not l.words or id(l) in consumed:
                continue
            ls = l.size or l.bbox.height
            if cs < 2.0 * ls:
                continue  # an initial letter, not a drop cap
            gap = l.bbox.x0 - cap.bbox.x1
            if not -0.1 * cs <= gap <= 0.5 * cs:
                continue
            if not cap.bbox.y0 - 0.5 * ls <= l.bbox.y0 <= cap.bbox.y1 - 0.5 * ls:
                continue
            firsts.append(l)
        if not firsts:
            continue
        first = min(firsts, key=lambda l: l.bbox.y0)
        w0 = first.words[0]
        fused = Word(text=chars[0].text + w0.text, bbox=BBox(cap.bbox.x0, w0.bbox.y0, w0.bbox.x1, w0.bbox.y1), chars=cap.words[0].chars + w0.chars)
        first.words = [fused] + first.words[1:]
        first.bbox = BBox(min(first.bbox.x0, cap.bbox.x0), first.bbox.y0, first.bbox.x1, first.bbox.y1)
        consumed.add(id(cap))
    return [l for l in lines if id(l) not in consumed]


def _attach_satellites(lines: list[Line], rules: list[BBox] | None = None) -> list[Line]:
    """Fold script-sized fragments stacked on a line into that line.

    An inline fraction is typeset as a numerator above and a denominator below
    the line; MuPDF reports each as its own line. Any small segment whose
    baseline lies within the height of a full-size line and whose horizontal
    span lies inside that line's span is part of the line, and the formula
    rebuild later recovers the fraction from the glyph positions. Baselines,
    not box centres, decide which of two neighbouring lines a fragment belongs
    to: symbol fonts often carry a deep descender that drags a box centre down
    towards the next line.
    """
    if len(lines) < 2:
        return lines
    big = [l for l in lines if not l.rotated]
    # Display type (a 139 pt newspaper headline) hosts nothing: the page number
    # above it and the drop cap below it are not its scripts. Tall maths
    # delimiters are the exception.
    hosts = [l for l in big if len(l.words) >= 2
             and ((l.size or l.bbox.height) <= _DISPLAY_TYPE_PT or any(_needs_ink(c.font) for w in l.words for c in w.chars))]
    rules = rules or []
    radical_chars = [c for l in big for w in l.words for c in w.chars if c.text == "√" or _needs_ink(c.font)]
    plans: list[tuple[Line, Line]] = []
    handled: set[int] = set()
    # Display operators. A tall integral or sum sign often arrives on a line of its
    # own together with its upper limit, its lower limit on another, and the
    # integrand on a third, because the three baselines differ by a line or more.
    # The sign spans the integrand's line vertically: that line is the host of the
    # sign's line and of any small fragment sitting in the sign's column.
    ops: list[tuple[Line, BBox]] = []
    for l in big:
        ls = l.size or l.bbox.height
        for w in l.words:
            for c in w.chars:
                box = c.ink or c.bbox
                # Only a genuine operator sign: a tall bracket or a brace piece spans
                # its neighbours too, but its line is not their host (a cases brace
                # pulled the text line above it into the formula).
                if _needs_ink(c.font) and box.height >= 1.5 * max(ls, 6.0) and not c.text.isspace() \
                        and latex_for_char(c.text, c.font) in _BIG_OPERATOR_LATEX:
                    ops.append((l, box))
    sat_debug = bool(os.environ.get("TRUEDOC_SAT_DEBUG"))
    for op_line, box in ops:
        spanned = [h for h in hosts if h is not op_line and box.y0 - 0.3 * (h.size or 10.0) <= h.baseline <= box.y1 + 0.3 * (h.size or 10.0)
                   and h.bbox.x0 >= box.x0 - 0.5 * (h.size or 10.0) and h.bbox.x0 <= box.x1 + 2.5 * (h.size or 10.0)]
        if sat_debug:
            print(f"[sat] op {op_line.text[:12]!r} box=({box.x0:.0f},{box.y0:.0f},{box.x1:.0f},{box.y1:.0f}) spans {[h.text[:16] for h in spanned]}")
        if not spanned:
            continue
        host = min(spanned, key=lambda h: abs(h.baseline - box.cy))
        hs = host.size or host.bbox.height
        if len(op_line.words) <= 4 and id(op_line) not in handled:
            plans.append((op_line, host))
            handled.add(id(op_line))
        for sat in big:
            if sat is host or sat is op_line or id(sat) in handled or len(sat.words) > 4:
                continue
            ss = sat.size or sat.bbox.height
            if ss >= 0.85 * hs:
                continue
            # The limits of two signs on one line ("t ... t", "-inf ... -inf") arrive
            # as one text-layer line: a word in the sign's column is enough.
            if not any(box.x0 - 0.5 * ss <= w.bbox.cx <= box.x1 + 1.5 * ss for w in sat.words):
                continue
            if sat.bbox.y1 < box.y0 - 1.5 * ss or sat.bbox.y0 > box.y1 + 1.5 * ss:
                continue
            if sat.bbox.x0 < host.bbox.x0 - 2.0 * hs or sat.bbox.x1 > host.bbox.x1 + 2.0 * hs:
                continue
            plans.append((sat, host))
            handled.add(id(sat))
    for sat in big:
        if id(sat) in handled or len(sat.words) > 6:
            continue
        # The pieces of an extensible brace or bracket belong to the display
        # formula they frame, which is assembled from its region; as satellites
        # they would land in the text line whose baseline they happen to touch.
        sat_chars = [c for w in sat.words for c in w.chars if not c.text.isspace()]
        if sat_chars and all(is_piece_glyph(c.text, c.font) for c in sat_chars):
            continue
        # A tall bracket glued to a small numerator ("\Big(" then "1") must not
        # make the fragment look full-size: judge the size by the ordinary glyphs.
        plain_chars = [c for w in sat.words for c in w.chars if not _needs_ink(c.font) and not c.text.isspace()]
        # The size that most of the fragment is set in: a full-size comma that
        # MuPDF put on the denominator's line ("σmin(A)" then ",") must not make
        # the fragment look full-size either.
        sizes = sorted(c.size for c in plain_chars)
        ss = sizes[len(sizes) // 2] if sizes else (sat.size or sat.bbox.height)
        body_chars = [c for c in plain_chars if c.size <= 1.05 * ss] or plain_chars
        plain_box = BBox.union_all(c.bbox for c in body_chars) if body_chars else sat.bbox
        sat_base = max(c.origin_y for c in body_chars) if body_chars and any(c.origin_y for c in body_chars) else sat.baseline
        # A numerator sits on its fraction bar: the bar just below it says which
        # line it belongs to (the one whose baseline lies below the bar), even
        # when the line above is nearer by baseline.
        bar_below = next((r for r in rules if plain_box.y1 - 0.25 * ss <= r.cy <= plain_box.y1 + 0.7 * ss
                          and min(r.x1, plain_box.x1) - max(r.x0, plain_box.x0) >= 0.5 * plain_box.width), None)
        # A denominator hangs under its bar. Only a short bar counts (a fraction
        # bar is about as wide as its parts; a footnote or table rule is not), and
        # a radical's own bar does not: a numerator "sqrt(n-1)" over a fraction bar
        # has a bar above it too, drawn from the radical sign's top right corner.
        def radical_bar(r) -> bool:
            # The radical sign often sits on a line of its own, so look at the page's.
            return any(abs(c.bbox.x1 - r.x0) <= 1.0 * ss and c.bbox.y0 - 0.5 * ss <= r.cy <= c.bbox.y1 + 0.5 * ss
                       for c in radical_chars)

        bar_above = next((r for r in rules if plain_box.y0 - 0.7 * ss <= r.cy <= plain_box.y0 + 0.25 * ss
                          and min(r.x1, plain_box.x1) - max(r.x0, plain_box.x0) >= 0.5 * plain_box.width
                          and r.x1 - r.x0 <= 2.0 * plain_box.width + 2.0 * ss and not radical_bar(r)), None)
        short_bar_below = bar_below is not None and bar_below.x1 - bar_below.x0 <= 2.0 * plain_box.width + 2.0 * ss
        debug = os.environ.get("TRUEDOC_SAT_DEBUG") and len(sat.words) <= 4
        # A fragment made only of accent glyphs (a line of dots and bars set over
        # the letters of the line below, as for stacked accents) belongs to that
        # line whatever its size.
        accent_only = bool(plain_chars) and all(c.text in _ACCENT_ONLY_CHARS for c in plain_chars)
        best, best_d = None, 1e9
        for host in hosts:
            if host is sat:
                continue
            hs = host.size or host.bbox.height
            why = ""
            d = abs(sat_base - host.baseline)
            if accent_only:
                below = host.baseline - sat_base
                if not (0.2 * hs <= below <= 1.4 * hs):
                    why = "not the line below"
                elif d >= best_d:
                    why = "farther"
                elif sat.bbox.x0 < host.bbox.x0 - 0.5 * hs or sat.bbox.x1 > host.bbox.x1 + 0.5 * hs:
                    why = "outside host span"
                if debug:
                    print(f"[sat] accents {sat.text[:16]!r} -> host {host.text[:24]!r}: {why or 'OK'}")
                if why:
                    continue
                best, best_d = host, d
                continue
            # Bar-linked fragments: a numerator whose bar lies above the host's
            # baseline, or a denominator whose bar lies between the host's baseline
            # and its own. A display-style fraction set inside a text line has
            # full-size parts, so the size test is waived for a short bar-linked fragment.
            num_linked = bar_below is not None and host.baseline > bar_below.cy
            den_linked = bar_above is not None and bar_above.cy < host.baseline < sat_base
            reach = 1.1 * hs if (num_linked or den_linked) else 0.7 * hs
            full_size_ok = len(sat.words) <= 4 and ((num_linked and short_bar_below) or den_linked)
            if ss >= 0.85 * hs and not full_size_ok:
                why = "same size"
            elif d > reach or d >= best_d:
                why = f"d={d:.1f} reach={reach:.1f}"
            elif bar_below is not None and host.baseline < bar_below.cy:
                why = "above the bar"
            elif bar_above is not None and host.baseline > sat_base:
                why = "below the fragment"
            elif sat.bbox.x0 < host.bbox.x0 - 0.5 * hs or sat.bbox.x1 > host.bbox.x1 + 0.5 * hs:
                # (Letting a bar-linked fraction that starts just past the line's last
                # word join the line was tried on 4 Sept and made things worse: the
                # numerator joined, the rest scattered. Left as is.)
                why = "outside host span"
            if debug and d < 3 * hs:
                print(f"[sat] {sat.text[:24]!r} ss={ss:.0f} base={sat_base:.0f} -> host {host.text[:24]!r} base={host.baseline:.0f} hs={hs:.0f}: {why or 'OK'}")
            if why:
                continue
            best, best_d = host, d
        if best is not None:
            plans.append((sat, best))
    satellites = {id(s) for s, _ in plans}
    consumed: set[int] = set()
    for sat, host in plans:
        if id(host) in satellites:
            continue  # a fragment cannot host another fragment
        consumed.add(id(sat))
        host.words = sorted(host.words + sat.words, key=lambda w: w.bbox.x0)
        host.bbox = host.bbox.union(sat.bbox)
    return [l for l in lines if id(l) not in consumed]


def _reassemble_ocr_layer(lines: list[Line], gutters: list[tuple[float, float]] | None = None) -> list[Line]:
    """Merge same-baseline segments of an OCR layer unless the gap is a column gap.

    Within one printed line the gaps between phrases are word spaces (a bit
    stretched); between columns the gap is several times larger. A gap is
    treated as a column break when it exceeds both 2.5 line heights and three
    times the median gap on that baseline. Page-wide column gutters found
    beforehand (see `_column_gutters`) are column breaks too: a line number
    printed in the gutter must not bridge the two columns.
    """
    gutters = gutters or []
    ordered = sorted(lines, key=lambda l: (round(l.bbox.cy, 1), l.bbox.x0))
    rows: list[list[Line]] = []
    for seg in ordered:
        if seg.rotated:
            rows.append([seg])
            continue
        if rows and not rows[-1][0].rotated:
            ref = rows[-1][0]
            h = max(ref.bbox.height, seg.bbox.height, 1.0)
            if abs(seg.bbox.cy - ref.bbox.cy) <= 0.35 * h:
                rows[-1].append(seg)
                continue
        rows.append([seg])
    for row in rows:
        row.sort(key=lambda l: l.bbox.x0)

    # Column separators: x positions where many rows have a wide gap (a vertical
    # whitespace channel). Segments are never merged across one of those.
    # Any gap wider than a word space is a vote; what makes a column boundary is
    # many rows breaking at the same place (columns can be separated by a mere
    # 6 pt when a vertical rule sits between them).
    channel_votes: list[tuple[float, float, float]] = []   # (gap start, gap end, row centre y)
    all_gaps: list[float] = []
    for row in rows:
        h = max(l.bbox.height for l in row)
        row_cy = sum(l.bbox.cy for l in row) / len(row)
        # Votes come from every word gap on the baseline, so a producer that
        # already joined both columns into one line still reveals the boundary.
        row_words = sorted((w for l in row for w in l.words), key=lambda w: w.bbox.x0)
        for a, b in zip(row_words, row_words[1:]):
            gap = b.bbox.x0 - a.bbox.x1
            if gap > 0:
                all_gaps.append(gap)
            if gap > 0.6 * h:
                channel_votes.append((a.bbox.x1, b.bbox.x0, row_cy))
    all_gaps.sort()
    page_word_gap = all_gaps[len(all_gaps) // 2] if all_gaps else 0.0
    # A separator is a channel with a vertical range: the rows that voted for it.
    # A page that opens with a full-width abstract over two columns has its
    # channel only in the lower band; the abstract's lines neither vote nor
    # straddle it, and are never split by it.
    separators: list[tuple[float, float, float, float]] = []
    text_rows = [r for r in rows if not r[0].rotated]
    if len(text_rows) >= 8:
        votes = sorted(channel_votes, key=lambda v: (v[0] + v[1]) / 2)
        cluster: list[tuple[float, float, float]] = []
        row_cys = [sum(l.bbox.cy for l in r) / len(r) for r in text_rows]
        all_words = [w for r in text_rows for l in r for w in l.words]

        left_extent = min(w.bbox.x0 for w in all_words)
        right_extent = max(w.bbox.x1 for w in all_words)
        span = max(1.0, right_extent - left_extent)

        def close(cl):
            if len(cl) < 6:
                return
            s0, s1 = max(c[0] for c in cl), min(c[1] for c in cl)
            if s1 <= s0:
                return
            # A column boundary has real text on both sides; a list gutter does not.
            if s0 - left_extent < 0.2 * span or right_extent - s1 < 0.2 * span:
                return
            y0, y1 = min(c[2] for c in cl), max(c[2] for c in cl)
            band = [r for r, cy in zip(text_rows, row_cys) if y0 - 1 <= cy <= y1 + 1]
            if len(cl) < max(6, 0.5 * len(band)):
                return
            # A real column boundary is a channel no word straddles (within its band).
            band_words = [w for r in band for l in r for w in l.words]
            straddle = sum(1 for w in band_words if w.bbox.x0 < s0 - 1 and w.bbox.x1 > s1 + 1)
            if straddle <= 0.05 * len(band):
                separators.append((s0, s1, y0, y1))

        anchor = 0.0
        for v in votes:
            c = (v[0] + v[1]) / 2
            if cluster and abs(c - anchor) > 6.0:
                close(cluster)
                cluster = []
            if not cluster:
                anchor = c
            cluster.append(v)
        if cluster:
            close(cluster)

    separators.extend((s0, s1, float("-inf"), float("inf")) for s0, s1 in gutters)

    def crosses_separator(a: Line, b: Line) -> bool:
        if _lone_gutter_number(a, gutters) or _lone_gutter_number(b, gutters):
            return True
        cy = (a.bbox.cy + b.bbox.cy) / 2
        h = max(a.bbox.height, b.bbox.height, 1.0)
        return any(a.bbox.x1 <= s1 + 2 and b.bbox.x0 >= s0 - 2 and y0 - h <= cy <= y1 + h for s0, s1, y0, y1 in separators)

    out: list[Line] = []
    for row in rows:
        if separators:
            # Split any segment that itself spans a column boundary.
            split_row: list[Line] = []
            for seg in row:
                if seg.rotated or len(seg.words) < 2:
                    split_row.append(seg)
                    continue
                cur_words = [seg.words[0]]
                seg_cy, seg_h = seg.bbox.cy, max(seg.bbox.height, 1.0)
                for a, b in zip(seg.words, seg.words[1:]):
                    if any(a.bbox.x1 <= s1 + 2 and b.bbox.x0 >= s0 - 2 and y0 - seg_h <= seg_cy <= y1 + seg_h for s0, s1, y0, y1 in separators):
                        split_row.append(Line(words=cur_words, bbox=BBox.union_all(w.bbox for w in cur_words)))
                        cur_words = [b]
                    else:
                        cur_words.append(b)
                split_row.append(Line(words=cur_words, bbox=BBox.union_all(w.bbox for w in cur_words)))
            row = sorted(split_row, key=lambda l: l.bbox.x0)
        if len(row) == 1:
            out.append(row[0])
            continue
        gaps = [b.bbox.x0 - a.bbox.x1 for a, b in zip(row, row[1:])]
        h = max(l.bbox.height for l in row)
        cur = [row[0]]
        for gap, seg in zip(gaps, row[1:]):
            # A table-cell gap is far wider than the page's typical word space.
            wide = gap > 2.5 * h and gap > 3.0 * max(page_word_gap, 0.2 * h)
            if crosses_separator(cur[-1], seg) or wide or gap > 6.0 * h:
                out.append(Line(words=[w for l in cur for w in l.words], bbox=BBox.union_all(l.bbox for l in cur)))
                cur = [seg]
            else:
                cur.append(seg)
        out.append(Line(words=[w for l in cur for w in l.words], bbox=BBox.union_all(l.bbox for l in cur)))
    return out


def _merge_uniform_rows(lines: list[Line], gutters: list[tuple[float, float]] | None = None) -> list[Line]:
    """A baseline holding four or more single-word segments with near-equal gaps is one justified line."""
    gutters = gutters or []
    out: list[Line] = []
    i = 0
    ordered = sorted(lines, key=lambda l: (round(l.baseline, 1), l.bbox.x0))
    while i < len(ordered):
        j = i
        if ordered[i].rotated:
            # Vertical text (a scanner's "Downloaded from ..." stamp up the margin)
            # has a baseline somewhere mid-page and must not start a row: it was
            # being merged into the body line that shares that baseline.
            out.append(ordered[i])
            i += 1
            continue
        size = max(ordered[i].size, 0.7 * ordered[i].bbox.height, 1.0)
        while j + 1 < len(ordered) and abs(ordered[j + 1].baseline - ordered[i].baseline) <= 0.3 * size and not ordered[j + 1].rotated:
            j += 1
        row = ordered[i:j + 1]
        # Split the baseline into runs at wide gaps (margin line numbers, other columns).
        runs: list[list[Line]] = [[row[0]]]
        for a, b in zip(row, row[1:]):
            if b.bbox.x0 - a.bbox.x1 > 2.2 * size or _gap_crosses_gutter(a.bbox.x1, b.bbox.x0, gutters):
                runs.append([b])
            else:
                runs[-1].append(b)
        for run in runs:
            if len(run) >= 4 and all(len(l.words) <= 2 for l in run):
                gaps = [b.bbox.x0 - a.bbox.x1 for a, b in zip(run, run[1:])]
                if gaps and min(gaps) > 0 and max(gaps) / max(min(gaps), 0.1) <= 1.8:
                    out.append(Line(words=[w for l in run for w in l.words], bbox=BBox.union_all(l.bbox for l in run)))
                    continue
            out.extend(run)
        i = j + 1
    return out


def _split_line_segments(words: list[Word]) -> list[Line]:
    """Split a physical line into segments at large horizontal gaps.

    MuPDF sometimes joins text from neighbouring columns or table cells into
    one line when their baselines align; a large gap is the tell.
    """
    if not words:
        return []
    gaps = [w.bbox.x0 - prev.bbox.x1 for prev, w in zip(words, words[1:])]
    pos = sorted(g for g in gaps if g > 0)
    median_gap = pos[len(pos) // 2] if pos else 0.0
    segments: list[list[Word]] = [[words[0]]]
    for prev, w, gap in zip(words, words[1:], gaps):
        size = max(prev.size, w.size, 1.0)
        # A wide gap splits the line, unless every gap on the line is wide
        # (justified text stretched across a narrow column).
        if gap > 2.0 * size and (len(gaps) <= 2 or gap > 3.0 * median_gap):
            segments.append([w])
        else:
            segments[-1].append(w)
    out: list[Line] = []
    for seg in segments:
        out.append(Line(words=seg, bbox=BBox.union_all(w.bbox for w in seg)))
    return out


def _extract_drawings(pdf_page: "pymupdf.Page", M=None) -> list[Drawing]:
    if pdfium_objects.enabled():
        objs = pdfium_objects.page_objects(pdf_page.parent.name, pdf_page.number + 1)
        if objs is not None:
            return _drawings_from_objects(objs, M)
    return _drawings_from_mupdf(pdf_page, M)


def _drawings_from_objects(objs: list, M=None) -> list[Drawing]:
    """The same rulings and shaded boxes, from PDFium's list of what is drawn.

    One list does the work of MuPDF's two: `get_bboxlog` is consulted there only to catch rules
    drawn as one-pixel image masks rather than vector paths, and an image object is an image object
    whichever way it was drawn.
    """
    out: list[Drawing] = []
    seen: set[tuple[int, int, int, int]] = set()
    for o in objs:
        if o.kind not in ("path", "image", "shading"):
            continue
        r = _rect(o.bbox, M)
        width = o.stroke_width if o.kind == "path" else r.height
        fill = o.fill is not None or o.kind != "path"
        key = (int(r.x0), int(r.y0), int(r.x1), int(r.y1))
        if key in seen:
            continue
        if r.height <= 3.0 and r.width >= 2.5:
            seen.add(key)
            out.append(Drawing(kind="hline", bbox=r, width=width, fill=fill))
        elif r.width <= 3.0 and r.height >= 8.0:
            seen.add(key)
            out.append(Drawing(kind="vline", bbox=r, width=width, fill=fill))
        elif o.kind == "path" and r.width >= 8.0 and r.height >= 8.0:
            out.append(Drawing(kind="rect", bbox=r, width=width, fill=fill))
    return out


def _drawings_from_mupdf(pdf_page: "pymupdf.Page", M=None) -> list[Drawing]:
    out: list[Drawing] = []
    seen: set[tuple[int, int, int, int]] = set()
    # Some producers draw rules (fraction bars, table lines) as 1-pixel image
    # masks rather than vector paths; the bbox log catches those too.
    try:
        for kind, rect in pdf_page.get_bboxlog():
            if kind not in ("fill-imgmask", "fill-image", "fill-path", "stroke-path"):
                continue
            r = _rect(rect, M)
            key = (int(r.x0), int(r.y0), int(r.x1), int(r.y1))
            if r.height <= 3.0 and r.width >= 2.5 and key not in seen:
                seen.add(key)
                out.append(Drawing(kind="hline", bbox=r, width=r.height, fill=True))
            elif r.width <= 3.0 and r.height >= 8.0 and key not in seen:
                seen.add(key)
                out.append(Drawing(kind="vline", bbox=r, width=r.width, fill=True))
    except Exception:
        pass
    try:
        paths = pdf_page.get_drawings()
    except Exception:
        return out
    for p in paths:
        rect = p.get("rect")
        if rect is None:
            continue
        r = _rect(rect, M)
        width = float(p.get("width") or 0.0)
        fill = p.get("fill") is not None
        key = (int(r.x0), int(r.y0), int(r.x1), int(r.y1))
        if key in seen:
            continue
        # Thin, long shapes are rulings; filled rectangles may be cell shading.
        if r.height <= 3.0 and r.width >= 2.5:
            seen.add(key)
            out.append(Drawing(kind="hline", bbox=r, width=width, fill=fill))
        elif r.width <= 3.0 and r.height >= 8.0:
            seen.add(key)
            out.append(Drawing(kind="vline", bbox=r, width=width, fill=fill))
        elif r.width >= 8.0 and r.height >= 8.0:
            out.append(Drawing(kind="rect", bbox=r, width=width, fill=fill))
    return out


def _extract_images(pdf_page: "pymupdf.Page", M=None) -> list[ImageRef]:
    out: list[ImageRef] = []
    infos = None
    if pdfium_objects.enabled():
        objs = pdfium_objects.page_objects(pdf_page.parent.name, pdf_page.number + 1)
        if objs is not None:
            # Measured over 60 benchmark pages: 122 of 122 image boxes agree with MuPDF's to
            # within a point. `xref` has no reader anywhere in the project, so it is left at 0.
            infos = [{"bbox": o.bbox} for o in objs if o.kind == "image"]
    if infos is None:
        try:
            infos = pdf_page.get_image_info(xrefs=True)
        except Exception:
            return out
    page_rect = _rect(pdf_page.rect)
    for info in infos:
        r = _rect(info["bbox"], M)
        clipped = r.intersection(page_rect)
        if clipped is None or clipped.width < 4 or clipped.height < 4:
            continue
        out.append(ImageRef(bbox=clipped, xref=int(info.get("xref", 0))))
    return out


_LATIN_VOWELS = set("aeiouyáéíóúàèìòùâêîôûäëïöüãõåæøœ")


def _looks_garbled(token: str) -> bool:
    """A token that no language produces: a symbol inside a word, a digit between
    letters, several case flips inside a word, or (Latin script) no vowel at all.
    Broken OCR layers are made of these ("0Ql.5)')81", "t.AatcHng", "PIOI*Jnlboctenum")."""
    core = token.strip(".,;:!?()[]{}\"'“”‘’«»")
    if len(core) < 4:
        return False
    if "://" in core or core.lower().startswith("www.") or "@" in core:
        return False  # addresses are full of dots and symbols by design
    letters = [c for c in core if c.isalpha()]
    symbols = [c for c in core if not c.isalnum() and c not in "-'’/&."]
    if len(symbols) >= 2 and letters:
        return True  # "0Ql.5)')81": symbols strewn through a word
    if len(letters) < 3:
        return False
    if core[0] in "~*#|^`" or core[-1] in "~*#|^`":
        return True  # "~hlngomonas"
    inner = core[1:-1]
    if symbols and any(c in symbols for c in inner):
        return True
    if any(a.isalpha() and b.isdigit() and c.isalpha() for a, b, c in zip(core, core[1:], core[2:])):
        return True
    flips = sum(1 for a, b in zip(inner, inner[1:]) if a.isalpha() and b.isalpha() and a.islower() and b.isupper())
    if flips >= 2:
        return True
    latin = all(ord(c) < 0x0250 for c in letters)
    if latin and len(letters) >= 5 and not any(c.lower() in _LATIN_VOWELS for c in letters):
        return True
    return False


def _garbage_fraction(page: Page) -> tuple[float, int]:
    """Share of the page's longer tokens that look garbled, and how many tokens were judged.

    Pages carrying maths fonts are not judged: formulas are full of symbols
    inside "words", and a broken OCR layer never uses a maths font.
    """
    for c in page.chars:
        f = c.font.upper()
        if _needs_ink(c.font) or any(h in f for h in _MATH_FONT_MARKS):
            return 0.0, 0
    tokens = [w.text for w in page.words if len(w.text.strip(".,;:!?()[]{}\"'")) >= 4]
    if not tokens:
        return 0.0, 0
    return sum(1 for t in tokens if _looks_garbled(t)) / len(tokens), len(tokens)


def _assess_quality(page: Page, visibility: _Visibility) -> TextQuality:
    q = TextQuality()
    q.n_chars = sum(1 for c in page.chars if not c.text.isspace())
    q.n_alnum = sum(1 for c in page.chars if c.text.isalnum())
    bad = sum(1 for c in page.chars if _is_bad_char(c.text))
    q.bad_fraction = bad / q.n_chars if q.n_chars else 0.0
    q.garbage_fraction, n_tokens = _garbage_fraction(page)

    # Image coverage (union approximated by sum, capped).
    area = page.width * page.height or 1.0
    cov = sum(i.bbox.area for i in page.images) / area
    q.image_coverage = min(1.0, cov)

    # Invisible text (render mode 3 / zero opacity) is the signature of an OCR layer. Counted as the
    # page is read (`_Visibility`): PDFium's characters, or MuPDF's text trace on the old reader.
    invisible, total = visibility.drawn_invisible, visibility.drawn_total
    q.invisible_fraction = invisible / total if total else 0.0

    if q.n_alnum < 20:
        q.kind = "none"
    elif q.bad_fraction > 0.2:
        q.kind = "suspect"
    elif q.garbage_fraction > 0.2 and n_tokens >= 30:
        # A broken OCR layer, or a font with no usable character mapping. Ordinary
        # pages measure 0.00-0.02, a mediocre but readable OCR layer about 0.08, an
        # unreadable one about 0.24.
        q.kind = "suspect"
    elif q.invisible_fraction > 0.5 or (q.image_coverage > 0.6 and q.invisible_fraction > 0.1):
        q.kind = "ocr"
    elif q.image_coverage > 0.85 and q.n_alnum < 200:
        q.kind = "suspect"
    else:
        q.kind = "digital"
    return q


def _body_font_size(page: Page) -> float:
    counts: dict[float, int] = {}
    for w in page.words:
        s = round(w.size * 2) / 2.0
        if s <= 0:
            continue
        counts[s] = counts.get(s, 0) + len(w.text)
    if not counts:
        return 0.0
    return max(counts.items(), key=lambda kv: kv[1])[0]
