"""The conversion pipeline: PDF -> Document -> OKF markdown."""

from __future__ import annotations

import datetime as _dt
import hashlib
import os
import pathlib
import re
from dataclasses import dataclass, field

import pymupdf

from truedoc.classify.blocks import _assign_heading_levels, classify_blocks
from truedoc.extract import render as page_render
from truedoc.extract.handle import open_pdf
from truedoc.extract.textlayer import extract_page
from truedoc.layout.fuse import apply_layout
from truedoc.model import BBox, Block, BlockKind, Document, Page
from truedoc.render.okf import RenderOptions, render_document
from truedoc.segment.blocks import build_blocks
from truedoc.segment.order import assign_reading_order
from truedoc.tables.aligned import find_aligned_tables
from truedoc.tables.cells import clean_cell_text
from truedoc.tables.ruled import find_ruled_tables


@dataclass
class ConvertOptions:
    frontmatter: bool = True
    page_markers: bool = False
    pages: list[int] | None = None       # 1-based page numbers to convert; None = all
    tables: bool = True
    layout: bool = True                  # run the layout-detection model (CPU, ~3 s/page)
    layout_dpi: int = 120
    math: bool = True                    # rebuild formulas from the text layer
    ocr: bool = True                     # OCR pages that have no usable text layer
    ocr_pictures: bool = False           # also OCR text kept as pictures on digital pages (M13; experimental, off by default)
    doc_type: str = "Document"           # OKF `type` of the produced document
    marks: bool = True                   # read ticks, crosses and bullets drawn as shapes or tiny images
    vision_endpoint: str | None = None   # optional vision stage (D014): endpoint of a served olmOCR-style model
    vision_model: str = "olmocr"         # model name the endpoint expects
    vision_regions: bool = True          # with the vision stage on, also read icons in table cells and describe figures (D015)
    render: RenderOptions = field(default_factory=RenderOptions)


def load_document(path: str, opts: ConvertOptions | None = None) -> Document:
    opts = opts or ConvertOptions()
    doc = Document(path=path)
    with open(path, "rb") as fh:
        doc.sha256 = hashlib.sha256(fh.read()).hexdigest()
    doc.metadata["file_name"] = os.path.basename(path)
    doc.metadata["type"] = opts.doc_type
    # OKF provenance: the source document as a resource (a URI), and when it last changed.
    if "://" in path:
        doc.metadata["resource"] = path
    else:
        try:
            doc.metadata["resource"] = pathlib.Path(path).resolve().as_uri()
        except (OSError, ValueError):
            doc.metadata["resource"] = os.path.abspath(path).replace(os.sep, "/")
    try:
        mtime = os.path.getmtime(path)
        doc.metadata["last_modified"] = _dt.datetime.fromtimestamp(mtime, _dt.timezone.utc).replace(microsecond=0).isoformat()
    except OSError:
        pass
    pdf = open_pdf(path)
    try:
        md = pdf.metadata or {}
        if md.get("title"):
            doc.metadata["title"] = md["title"].strip()
        page_numbers = opts.pages or list(range(1, len(pdf) + 1))
        for n in page_numbers:
            if n < 1 or n > len(pdf):
                continue
            pdf_page = pdf[n - 1]
            page = process_page(pdf_page, n, opts)
            doc.pages.append(page)
    finally:
        pdf.close()
        # The renderer keeps a PDFium document open between calls (marks.py asks for one crop per
        # candidate shape); let go of it with the MuPDF one so the file is not left held.
        page_render.close_documents()
    _link_endnotes(doc)
    if opts.vision_endpoint:
        _read_unreadable_pages_with_model(doc, path, opts)
    doc.metadata["pages_with_ocr"] = [p.number for p in doc.pages if p.quality.kind == "ocr-truedoc"]
    # Pages that lay on their side were turned upright before reading (`_turn_page`); say so.
    turned = [{"page": p.number, "turn": p.meta["turned"]} for p in doc.pages if p.meta.get("turned")]
    if turned:
        doc.metadata["turned_pages"] = turned
        doc.warnings.append(f"pages turned upright before reading: {[t['page'] for t in turned]}")
    regions = [dict(page=p.number, **r) for p in doc.pages for r in (p.meta.get("ocr_regions") or [])]
    if regions:
        doc.metadata["ocr_regions"] = regions[:200]
    unreadable = [p.number for p in doc.pages if not p.quality.usable and p.quality.kind != "ocr-truedoc"]
    if unreadable:
        doc.warnings.append(f"pages without readable text: {unreadable}")
    # Text a reader cannot see is kept out of the body and recorded here (D011).
    hidden: list[dict] = []
    for p in doc.pages:
        for h in p.hidden_text:
            text = h["text"].strip()
            if not text:
                continue
            if len(hidden) < 200:
                hidden.append({"page": p.number, "reason": h["reason"], "text": text[:500]})
    if hidden:
        doc.metadata["hidden_text"] = hidden
        doc.warnings.append(f"hidden text removed from the body on pages: {sorted({h['page'] for h in hidden})}")
    doc.metadata["confidence"] = _estimate_confidence(doc)
    return doc


def _turn_page(pdf_page: "pymupdf.Page", number: int, turn: int) -> Page:
    """Turn a page that lies on its side (a landscape scan of a portrait page, a
    wide table printed sideways) and extract it again.

    The turn goes onto the in-memory page's rotation, so rendering, OCR, the
    drawings, the layout model and the vision stage all see the page upright
    and nothing downstream needs to know; the file itself is not changed.
    """
    pdf_page.set_rotation((int(pdf_page.rotation) + turn) % 360)
    page = extract_page(pdf_page, number)
    page.meta["turned"] = turn
    return page


def _sideways_text_turn(page: Page) -> int:
    """0 for a page whose text layer reads upright; else the turn (90 or 270
    degrees, clockwise positive) that would make it upright.

    Counted in characters, so a rotated stamp in the margin never turns a page.
    Text running down the page means the page was turned clockwise and needs
    the anticlockwise turn back (270); text running up the page needs 90.
    """
    down = page.meta.get("vertical_chars_down", 0)
    up = page.meta.get("vertical_chars_up", 0)
    total = page.meta.get("text_chars", 0)
    if down + up < 40 or down + up < 0.6 * max(1, total):
        return 0
    return 270 if down >= up else 90


def process_page(pdf_page: "pymupdf.Page", number: int, opts: ConvertOptions) -> Page:
    page = extract_page(pdf_page, number)
    turn = _sideways_text_turn(page) if page.quality.usable else 0
    if turn:
        page = _turn_page(pdf_page, number, turn)
    if not page.quality.usable:
        if opts.ocr:
            try:
                from truedoc.ocr.rapid import apply_ocr

                apply_ocr(page, pdf_page)
                turn = page.meta.pop("ocr_turn", 0)
                if turn:
                    page = _turn_page(pdf_page, number, turn)
                    apply_ocr(page, pdf_page, allow_turn=False)
            except Exception as exc:  # OCR is optional: never fail a conversion because of it
                import logging

                logging.getLogger("truedoc").warning("ocr failed: %s", exc)
        if not page.lines:
            page.blocks = []
            return page

    table_blocks: list[Block] = []
    lines = list(page.lines)
    if opts.tables:
        table_blocks = find_ruled_tables(pdf_page, page)
        if table_blocks:
            table_blocks, lines = _adopt_ruled_headers(table_blocks, lines, page.body_font_size)
            table_blocks = _rebuild_sparse_ruled_tables(table_blocks, lines, page.body_font_size)
            lines = [l for l in lines if not any(l.bbox.overlap_fraction(t.bbox) > 0.5 for t in table_blocks)]
        aligned, lines = find_aligned_tables(page, lines, page.body_font_size)
        table_blocks.extend(aligned)

    blocks = build_blocks(page, lines)
    blocks.extend(table_blocks)

    # Heuristic kinds first; the layout model then overrides what it is sure about.
    classify_blocks(page, blocks)

    regions = []
    if opts.layout:
        regions = _detect_layout(pdf_page, opts)
        page.meta["layout_regions"] = regions
        if regions:
            blocks = apply_layout(page, blocks, regions, pdf_page=pdf_page, ocr=opts.ocr)
    blocks = _merge_label_headings(blocks, page.body_font_size)
    blocks = _merge_wrapped_headings(blocks, page.body_font_size)

    _margin_cleanup(page, blocks)

    if opts.marks:
        _attach_marks(pdf_page, page, blocks)

    if opts.math:
        blocks = _apply_math(page, blocks, regions)

    _mark_footnotes(page, blocks)

    # Figures: image regions that are not mostly covered by text.
    for img in page.images:
        if img.bbox.width < 0.08 * page.width or img.bbox.height < 0.04 * page.height:
            continue
        if any(t.bbox.overlap_fraction(img.bbox) > 0.5 for t in table_blocks):
            continue
        text_inside = sum(b.n_chars for b in blocks if b.kind == BlockKind.TEXT and b.bbox.overlap_fraction(img.bbox) > 0.8)
        if text_inside > 400:
            continue  # a scanned text region with an OCR layer, not a figure
        blocks.append(Block(kind=BlockKind.FIGURE, bbox=img.bbox, provenance="textlayer-image"))

    if opts.ocr and opts.ocr_pictures:
        _ocr_text_pictures(pdf_page, page, blocks)

    assign_reading_order(blocks, page.width, page.body_font_size)
    page.blocks = blocks
    return page


_HEADING_LABEL = re.compile(r"^(?:[IVXLC]{1,6}\.?|\d{1,2}(?:\.\d{1,2}){0,3}\.?|[A-Z]\.)$")
_NUMBERED_START = re.compile(r"^\s*(?:\d{1,2}(?:\.\d{1,2}){0,4}\.?|[IVXLC]{1,6}\.|[A-Z]\.)\s+\S")
_CONNECTIVE_END = re.compile(
    r"(?:\b(?:and|or|of|the|a|an|for|in|on|to|with|by|at|from|de|des|du|la|le|les|et|y|e|di|da|del|und|der|die|das|van|von|&)|[(\[,:;/\-\u2013])$",
    re.IGNORECASE,
)


def _merge_wrapped_headings(blocks: list[Block], body: float) -> list[Block]:
    """A heading wrapped over two or three lines is one heading.

    Headings are set with wider leading than body text, so the segmenter gives each line of
    a wrapped heading a block of its own and the classifier makes two headings of them ("4
    Determination of the electrical" over "parameters"; run 60's output held 98 headings
    starting with a lowercase letter on 56 pages). A one-line heading directly under a
    heading of the same size and weight continues it when the upper line does not end a
    sentence and the lower one starts lowercase, or the upper line ends on a connective or
    an open bracket, or both are long title-case lines aligned on the left or the centre.
    A numbered lower line is a heading of its own."""
    heads = sorted((b for b in blocks if b.kind == BlockKind.HEADING and b.lines), key=lambda b: (b.bbox.y0, b.bbox.x0))
    text_like = [b for b in blocks if b.lines and b.kind in (BlockKind.TEXT, BlockKind.HEADING, BlockKind.LIST_ITEM, BlockKind.CAPTION)]
    removed: set[int] = set()

    def something_between(a: Block, b: Block, size: float) -> bool:
        """A line of another block sits between the two (two run-in headings a line apart,
        03ccfe8bb1 in run 62): they are not one wrapped heading."""
        return any(c is not a and c is not b and id(c) not in removed and c.bbox.y0 >= a.bbox.y1 - 0.3 * size and c.bbox.y1 <= b.bbox.y0 + 0.3 * size
                   and c.bbox.x_overlap(a.bbox) > 0.3 * min(a.bbox.width, c.bbox.width) for c in text_like)

    for a in heads:
        if id(a) in removed:
            continue
        while len(a.lines) < 3:
            size = max(a.size or body, 1.0)
            nxt = None
            for b in heads:
                if b is a or id(b) in removed or len(b.lines) != 1:
                    continue
                gap = b.bbox.y0 - a.bbox.y1
                if not (-0.3 * size <= gap <= 1.2 * size) or something_between(a, b, size):
                    continue
                if b.bbox.x_overlap(a.bbox) <= 0.3 * min(a.bbox.width, b.bbox.width):
                    continue
                if abs((b.size or size) - size) > 0.12 * size or a.lines[-1].bold != b.lines[0].bold:
                    continue
                if not _wraps_heading(a, b, size):
                    continue
                if nxt is None or b.bbox.y0 < nxt.bbox.y0:
                    nxt = b
            if nxt is None:
                break
            a.lines.extend(nxt.lines)
            a.bbox = a.bbox.union(nxt.bbox)
            removed.add(id(nxt))
    return [b for b in blocks if id(b) not in removed]


def _wraps_heading(a: Block, b: Block, size: float) -> bool:
    ta, tb = a.text.strip(), b.text.strip()
    if not ta or not tb or len(ta) + len(tb) > 200 or ta[-1] in ".!?:":
        return False
    if _NUMBERED_START.match(tb):
        return False
    if tb[0].islower() or _CONNECTIVE_END.search(ta) or ta.count("(") > ta.count(")"):
        return True
    aligned = abs(b.bbox.x0 - a.bbox.x0) <= 0.5 * size or abs(b.bbox.cx - a.bbox.cx) <= 0.5 * size
    return aligned and len(ta) >= 25 and tb[0].isupper()


def _merge_label_headings(blocks: list[Block], body: float) -> list[Block]:
    """A section number set apart from its title is one heading.

    TeX and Word put about an em between "VI." and "CONCLUSIONS", wider than a
    word space, so the two arrive as separate lines and then separate heading
    blocks (55 times in run 37's output). The number block must be a heading
    holding only a label (a roman or decimal number, a lettered "A."), and the
    title a heading on the same baseline starting within 2.5 em of it.
    """
    labels = [b for b in blocks if b.kind == BlockKind.HEADING and len(b.lines) == 1 and _HEADING_LABEL.match(b.text.strip())]
    if not labels:
        return blocks
    removed: set[int] = set()
    for a in labels:
        if id(a) in removed:
            continue
        size = max(a.size, 1.0)
        best = None
        for b in blocks:
            if b is a or id(b) in removed or b.kind != BlockKind.HEADING or len(b.lines) > 2 or not b.lines:
                continue
            gap = b.bbox.x0 - a.bbox.x1
            if not (-0.2 * size <= gap <= 2.5 * size):
                continue
            if a.bbox.y_overlap(b.bbox) < 0.5 * min(a.bbox.height, b.bbox.height):
                continue
            if best is None or gap < best[0]:
                best = (gap, b)
        if best is None:
            continue
        b = best[1]
        a.lines = a.lines + b.lines
        a.bbox = a.bbox.union(b.bbox)
        removed.add(id(b))
    if not removed:
        return blocks
    out = [b for b in blocks if id(b) not in removed]
    _assign_heading_levels(out, body)
    return out


def _apply_math(page: Page, blocks: list[Block], regions) -> list[Block]:
    from truedoc.layout.base import RegionKind
    from truedoc.math.extract import block_is_display_math, display_formula_blocks, inline_math_text, page_rules

    formula_boxes: list[BBox] = []
    for r in sorted((r for r in regions if r.kind == RegionKind.FORMULA and r.score >= 0.5), key=lambda r: -r.score):
        # The raw detector output holds near-duplicate boxes at different scores; keep one.
        if not any(r.bbox.overlap_fraction(fb) > 0.8 and fb.overlap_fraction(r.bbox) > 0.8 for fb in formula_boxes):
            formula_boxes.append(r.bbox)
    # Text blocks that are really display maths (no region, but math fonts dominate).
    for b in blocks:
        if b.kind in (BlockKind.TEXT, BlockKind.FORMULA) and b.lines and not any(b.bbox.overlap_fraction(fb) > 0.5 for fb in formula_boxes):
            if block_is_display_math(b):
                formula_boxes.append(b.bbox)
    # Fragments of one displayed equation (wide spacing splits it into several
    # blocks) share a baseline; merge boxes that overlap vertically and sit close.
    size = page.body_font_size or 10.0
    mid = page.width / 2.0
    merged = True
    while merged and len(formula_boxes) > 1:
        merged = False
        for i in range(len(formula_boxes)):
            for j in range(i + 1, len(formula_boxes)):
                a, b2 = formula_boxes[i], formula_boxes[j]
                yo = a.y_overlap(b2)
                # A gap that contains the page's middle is a column gutter, not the
                # spacing inside one equation.
                straddles = (a.x1 <= mid <= b2.x0) or (b2.x1 <= mid <= a.x0)
                if not straddles and yo >= 0.5 * min(a.height, b2.height) and (b2.x0 - a.x1 <= 3 * size and a.x0 - b2.x1 <= 3 * size):
                    formula_boxes[i] = a.union(b2)
                    del formula_boxes[j]
                    merged = True
                    break
            if merged:
                break
    if formula_boxes:
        formula_blocks = display_formula_blocks(page, formula_boxes)
        if formula_blocks:
            kept = []
            for b in blocks:
                if b.kind in (BlockKind.TABLE, BlockKind.FIGURE):
                    kept.append(b)
                    continue
                if b.lines and any(b.bbox.overlap_fraction(fb) > 0.5 for fb in formula_boxes):
                    continue
                if b.lines:
                    remaining = [l for l in b.lines if not any(fb.contains_point(l.bbox.cx, l.bbox.cy) for fb in formula_boxes)]
                    if not remaining:
                        continue
                    if len(remaining) != len(b.lines):
                        b.lines = remaining
                        b.bbox = BBox.union_all(l.bbox for l in remaining)
                kept.append(b)
            blocks = kept + formula_blocks
    # Inline maths inside ordinary text lines. A "code" region full of maths
    # glyphs is an algorithm listing: its lines are text with formulas, kept one
    # per line.
    from truedoc.math.reconstruct import is_math_font

    rules = page_rules(page)
    for b in blocks:
        if b.kind == BlockKind.CODE and b.lines:
            chars = [c for l in b.lines for w in l.words for c in w.chars if not c.text.isspace()]
            if chars and sum(1 for c in chars if is_math_font(c.font)) >= 0.1 * len(chars):
                b.kind = BlockKind.TEXT
                b.meta["preserve_lines"] = True
        if b.kind in (BlockKind.TEXT, BlockKind.LIST_ITEM, BlockKind.CAPTION, BlockKind.FOOTNOTE, BlockKind.HEADING) and b.lines:
            texts = [inline_math_text(l, rules) for l in b.lines]
            if any("$" in t for t in texts):
                b.meta["line_texts"] = texts
    return blocks


def _detect_layout(pdf_page: "pymupdf.Page", opts: ConvertOptions):
    try:
        from truedoc.extract.render import render_page
        from truedoc.layout.docling_layout import get_detector

        img, scale = render_page(pdf_page, dpi=opts.layout_dpi)
        return get_detector().detect(img, scale)
    except Exception as exc:  # the model is optional: never fail a conversion because of it
        import logging

        logging.getLogger("truedoc").warning("layout detection failed: %s", exc)
        return []


_NOTE_SYMBOLS = {"*": "star", "†": "dagger", "‡": "ddagger", "§": "sect", "¶": "para", "‖": "dbar"}


def _mark_footnotes(page: Page, blocks: list[Block]) -> None:
    """Footnote markers and their notes, as markdown footnotes.

    A small raised digit (or *, †, ‡) glued to a word in running text is a
    reference to a note: it becomes `[^n]`. A block at the foot of the page
    (or a small-type block anywhere) that starts with the same number becomes
    the note, rendered as `[^n]: text`, so a reader or a program can follow
    the link instead of meeting "face.8" and a stray paragraph.
    """
    body = page.body_font_size or 10.0
    H = page.height
    ids_seen: list[str] = []
    raw_by_key: dict[str, str] = {}   # key -> the marker as printed, to restore when no note is ever found

    def marker_runs(line) -> list[tuple[int, int, str]]:
        """(word index, char index of the marker's first char, id) for raised small markers."""
        out = []
        base = line.baseline or line.bbox.y1
        lsize = line.size or body
        for wi, w in enumerate(line.words):
            chars = w.chars
            i = 0
            while i < len(chars):
                c = chars[i]
                raised = c.origin_y and base - c.origin_y >= 0.2 * lsize
                small = c.size <= 0.8 * lsize
                if raised and small and (c.text.isdigit() or c.text in _NOTE_SYMBOLS):
                    j = i
                    ident = ""
                    while j < len(chars) and chars[j].size <= 0.8 * lsize and (chars[j].text.isdigit() or chars[j].text in _NOTE_SYMBOLS):
                        ident += chars[j].text
                        j += 1
                    # A marker follows text (or ends a word); a lone raised number at
                    # the start of a line is not one, and neither is a run of many digits.
                    if 0 < i and len(ident) <= 3:
                        out.append((wi, i, ident))
                    i = j
                else:
                    i += 1
        return out

    # 1. Markers in running text.
    for b in blocks:
        if b.kind not in (BlockKind.TEXT, BlockKind.LIST_ITEM, BlockKind.HEADING, BlockKind.CAPTION) or not b.lines:
            continue
        existing = b.meta.get("line_texts")
        texts: list[str] = []
        changed = False
        for li, line in enumerate(b.lines):
            text = existing[li] if existing and li < len(existing) else line.text
            runs = marker_runs(line)
            if not runs or "$" in text:
                texts.append(text)
                continue
            words = []
            for wi, w in enumerate(line.words):
                marks = [(ci, ident) for (wj, ci, ident) in runs if wj == wi]
                if not marks:
                    words.append(w.text)
                    continue
                pieces = []
                last = 0
                for ci, ident in marks:
                    pieces.append("".join(c.text for c in w.chars[last:ci]))
                    key = _NOTE_SYMBOLS.get(ident, ident)
                    pieces.append("[^%s]" % key)
                    ids_seen.append(key)
                    raw_by_key[key] = ident
                    last = ci + len(ident)
                pieces.append("".join(c.text for c in w.chars[last:]))
                words.append("".join(pieces))
            texts.append(" ".join(words))
            changed = True
        if changed:
            b.meta["line_texts"] = texts

    if not ids_seen:
        return
    page.meta["note_ids"] = list(dict.fromkeys(ids_seen))
    page.meta["note_raw"] = raw_by_key
    # 2. The notes: lines starting with a seen marker, in small type or at the
    #    foot of the page. Several notes often share one block, one per line.
    found: list[str] = []
    for b in blocks:
        # A heading is never a note ("2. Materials and Methods" is a section, whatever
        # citation "2" appeared above it); body-size notes sit at the very foot.
        if b.kind not in (BlockKind.TEXT, BlockKind.FOOTNOTE, BlockKind.LIST_ITEM) or not b.lines:
            continue
        small = (b.size or body) <= 0.92 * body
        low = b.bbox.y0 >= 0.75 * H
        if not (small or low):
            continue
        notes = _notes_in_block(b, set(ids_seen))
        if not notes:
            continue
        b.kind = BlockKind.FOOTNOTE
        b.meta["footnotes"] = [(k, t) for k, t in notes]
        b.meta.pop("line_texts", None)
        found.extend(k for k, _ in notes)
    page.meta["notes_found"] = found


_NOTE_PATTERN = re.compile(r"^([0-9]{1,3}|[*†‡§¶])[.)]?\s+(\S.*)$", re.S)
_NOTES_HEADINGS = {"notes", "endnotes", "end notes", "footnotes", "references", "notes and references", "sources"}


def _notes_in_block(b: Block, keys: set[str]) -> list[list[str]]:
    """The notes a block holds, one per line that starts with a wanted key;
    other lines continue the note above. Empty when the block does not start
    with a note."""
    notes: list[list[str]] = []
    for line in b.lines:
        m = _NOTE_PATTERN.match(line.text.strip())
        key = _NOTE_SYMBOLS.get(m.group(1), m.group(1)) if m else None
        if m and key in keys:
            notes.append([key, re.sub(r"\s+", " ", m.group(2)).strip()])
        elif notes:
            notes[-1][1] = (notes[-1][1] + " " + line.text.strip()).strip()
        else:
            return []
    return notes


def _link_endnotes(doc: Document) -> None:
    """Notes kept at the end of a document or chapter, and note keys unique
    across pages.

    Markdown footnote keys name the whole document, so a "1" on page 3 and a
    "1" on page 12 cannot both be `[^1]`: the later one becomes `[^1-p12]`.
    A marker whose note was not on its own page is looked for on later pages,
    in a block that starts with its number under a "Notes" heading, or in a
    run of several numbered notes; a lone "1 Introduction" is not a note.
    """
    used: set[str] = set()
    pending: dict[str, list[tuple[int, str]]] = {}   # original key -> [(page, final key)] awaiting a note
    for page in doc.pages:
        ids = page.meta.get("note_ids") or []
        if not ids:
            continue
        found = set(page.meta.get("notes_found") or [])
        rename: dict[str, str] = {}
        for key in ids:
            final = key
            if key in used:
                final = f"{key}-p{page.number}"
                rename[key] = final
            used.add(final)
            if key not in found:
                pending.setdefault(key, []).append((page.number, final))
        if rename:
            _rename_note_keys(page, rename)
    if not pending:
        return
    first_page = min(p for entries in pending.values() for p, _ in entries)
    for page in doc.pages:
        if page.number < first_page:
            continue
        wanted = {k for k, entries in pending.items() if any(p <= page.number for p, _ in entries)}
        if not wanted:
            continue
        heading = any(
            b.kind in (BlockKind.HEADING, BlockKind.TITLE)
            and re.sub(r"[^a-z ]", "", b.text.lower()).strip() in _NOTES_HEADINGS
            for b in page.blocks
        )
        candidates: list[tuple[Block, list[list[str]]]] = []
        for b in page.blocks:
            if b.kind not in (BlockKind.TEXT, BlockKind.LIST_ITEM) or not b.lines or b.meta.get("footnotes"):
                continue
            notes = _notes_in_block(b, wanted)
            if notes and all(len(t.split()) >= 3 for _, t in notes):
                candidates.append((b, notes))
        total = sum(len(n) for _, n in candidates)
        ascending = _ascending([k for _, n in candidates for k, _ in n])
        if not candidates or not (heading or (total >= 3 and ascending) or any(len(n) >= 2 for _, n in candidates)):
            continue
        for b, notes in candidates:
            linked: list[tuple[str, str]] = []
            for key, text in notes:
                queue = pending.get(key) or []
                match = next((i for i, (p, _) in enumerate(queue) if p <= page.number), None)
                if match is None:
                    continue
                _, final = queue.pop(match)
                linked.append((final, text))
            if linked and len(linked) == len(notes):
                b.kind = BlockKind.FOOTNOTE
                b.meta["footnotes"] = linked
                b.meta.pop("line_texts", None)
    # A marker whose note is nowhere in the document (a citation number pointing
    # at a bibliography, a note on a page that was not converted) goes back to
    # the digits the page printed: a `[^3]` with no definition is worse than a 3.
    for key, entries in pending.items():
        for page_no, final in entries:
            page = next((p for p in doc.pages if p.number == page_no), None)
            if page is None:
                continue
            raw = (page.meta.get("note_raw") or {}).get(key, key)
            _restore_note_marker(page, final, raw)


def _restore_note_marker(page: Page, key: str, raw: str) -> None:
    tag = "[^%s]" % key
    for b in page.blocks:
        texts = b.meta.get("line_texts")
        if texts:
            b.meta["line_texts"] = [t.replace(tag, raw) for t in texts]
        if b.text_override and tag in b.text_override:
            b.text_override = b.text_override.replace(tag, raw)


def _ascending(keys: list[str]) -> bool:
    nums = [int(k) for k in keys if k.isdigit()]
    return len(nums) >= 2 and all(a < b for a, b in zip(nums, nums[1:]))


def _rename_note_keys(page: Page, rename: dict[str, str]) -> None:
    for b in page.blocks:
        texts = b.meta.get("line_texts")
        if texts:
            b.meta["line_texts"] = [_replace_keys(t, rename) for t in texts]
        if b.text_override:
            b.text_override = _replace_keys(b.text_override, rename)
        if b.meta.get("footnotes"):
            b.meta["footnotes"] = [(rename.get(k, k), t) for k, t in b.meta["footnotes"]]


def _replace_keys(text: str, rename: dict[str, str]) -> str:
    for old, new in rename.items():
        text = text.replace("[^%s]" % old, "[^%s]" % new)
    return text


_SENTENCE_END = re.compile(r"[.!?][\"')\]]?(?:\s+[A-Z]|\s*$)")


_KEY_VALUE = re.compile(r"^[A-Za-z][\w .()/-]{0,24}:\s*\S")


def _control_stamp(table) -> bool:
    """Short cells, at least half of them "key: value" pairs ("issued: 2019-04-17",
    "reviewed: --"): the shape of a document-control box, not of a data table."""
    filled = [c.text.strip() for c in table.cells if c.text.strip()]
    if len(filled) < 2 or any(len(t.split()) > 4 for t in filled):
        return False
    keyed = sum(1 for t in filled if _KEY_VALUE.match(t) or t.endswith(":"))
    return keyed * 2 >= len(filled)


def _margin_cleanup(page: Page, blocks: list[Block]) -> None:
    """Running heads and feet that survive the layout model's labels.

    A short "heading" in the outermost strip of the page is a running head
    ("STAR FLEET UNIVERSE" beside the page's header), a short text line next
    to a header block belongs to it ("Revision 2" under "issued: 2019-04-17"),
    and a short line in the bottom strip is a running foot whatever its size.
    """
    H = page.height
    body = page.body_font_size or 10.0

    def words(b: Block) -> int:
        return len(b.text.split())

    headers = [b for b in blocks if b.kind == BlockKind.HEADER]
    text_blocks = [b for b in blocks if b.kind in (BlockKind.TEXT, BlockKind.HEADING, BlockKind.LIST_ITEM) and b.lines]

    def gap_above(b: Block) -> float:
        """Vertical white space between a block and the nearest text above it."""
        above = [o.bbox.y1 for o in text_blocks if o is not b and o.bbox.y1 <= b.bbox.y0 + 1.0 and o.bbox.x_overlap(b.bbox) > 0]
        return b.bbox.y0 - max(above) if above else 1e9

    def gap_below(b: Block) -> float:
        """Vertical white space between a block and the nearest text below it."""
        below = [o.bbox.y0 for o in text_blocks if o is not b and o.bbox.y0 >= b.bbox.y1 - 1.0 and o.bbox.x_overlap(b.bbox) > 0]
        return min(below) - b.bbox.y1 if below else 1e9

    first_heading = min((b.bbox.y0 for b in blocks if b.kind == BlockKind.HEADING and b.lines), default=None)
    for b in blocks:
        size = b.size or body
        # A document-control stamp at the head of a page ("Revision 2 | issued:
        # 2019-04-17", "supersedes: Revision 1 | dated: 2016-09-06"): a small
        # table of key: value cells above the page's first heading is furniture,
        # however well its rows line up (five checks on one page in run 50).
        if (b.kind == BlockKind.TABLE and b.table is not None and b.table.n_rows <= 4 and b.table.n_cols <= 2
                and b.bbox.y1 <= 0.15 * H and (first_heading is None or b.bbox.y1 <= first_heading) and _control_stamp(b.table)):
            b.kind = BlockKind.HEADER
            b.provenance = "control-stamp"
            continue
        if b.kind == BlockKind.HEADING and words(b) <= 8 and len(b.lines) <= 2:
            # At the top a title in display type stays a title; at the foot a short line
            # is a running foot whatever its size (a newspaper's masthead line, "Surfside
            # Gazette • AUGUST 2013" in 18 pt, eac8e314 in run 62).
            if b.bbox.y1 <= 0.08 * H and size <= 1.4 * body:
                b.kind = BlockKind.HEADER
                b.provenance = "margin-heading"
                headers.append(b)
            elif b.bbox.y0 >= 0.92 * H and (gap_above(b) >= 1.0 * size or size > 1.4 * body):
                # (a heading sits above its text: display type this low, with no text below
                # it, is a masthead line even when a column's last line touches it)
                b.kind = BlockKind.FOOTER
                b.provenance = "margin-heading"
        # A few short lines of body-sized text at the very top of the page, set
        # apart from the text below by white space, are a running head: a
        # catalogue's "Programs of Graduate Study ... 1", a journal's "2
        # Advances in Materials Science", a statute's "Part 2 / Division 1"
        # lines. A title is larger; a paragraph runs on without the gap.
        elif (b.kind == BlockKind.TEXT and len(b.lines) <= 3 and all(len(l.text.split()) <= 10 for l in b.lines)
              and size <= 1.2 * body and b.bbox.y0 <= 0.08 * H and gap_below(b) >= 1.0 * size
              # The tail of a paragraph carried over to the top of a column
              # ("each condition was averaged across all three subjects.") starts
              # in lowercase or holds a sentence end; a running head does neither.
              and not b.text[:1].islower() and not _SENTENCE_END.search(b.text)):
            b.kind = BlockKind.HEADER
            b.provenance = "top-strip"
            headers.append(b)
        # A short line in the bottom strip is a running foot only when white space
        # sets it apart from the body: the last line of a letter that runs to the
        # foot of the page ("good luck attend you.") is body text. A single line
        # may run longer ("PLOS ONE | DOI:... September 23, 2015 1 / 9").
        elif (b.kind == BlockKind.TEXT and len(b.lines) <= 2 and (words(b) <= 8 or (len(b.lines) == 1 and words(b) <= 14))
              and b.bbox.y0 >= 0.93 * H and gap_above(b) >= 1.0 * size):
            b.kind = BlockKind.FOOTER
            b.provenance = "bottom-strip"
        elif b.kind == BlockKind.TEXT and len(b.lines) <= 2 and words(b) <= 6 and b.bbox.y0 >= 0.89 * H and size <= 0.8 * body and gap_above(b) >= 0.8 * body:
            b.kind = BlockKind.FOOTER
            b.provenance = "bottom-strip"
    # Short text lines stacked with a header block share its fate.
    changed = True
    while changed:
        changed = False
        for b in blocks:
            # ("J. Appl. Cryst. (1974). 7, 222" under the page number "222")
            if b.kind != BlockKind.TEXT or len(b.lines) > 2 or words(b) > 8 or b.bbox.y1 > 0.14 * H:
                continue
            size = b.size or body
            for h in headers:
                gap = max(b.bbox.y0 - h.bbox.y1, h.bbox.y0 - b.bbox.y1)
                if gap <= 1.5 * size and (b.bbox.x_overlap(h.bbox) > 0 or abs(b.bbox.x0 - h.bbox.x0) <= 2 * size):
                    b.kind = BlockKind.HEADER
                    b.provenance = "header-stack"
                    headers.append(b)
                    changed = True
                    break
    # A short line in a running head's or foot's own size that repeats its text is furniture
    # wherever it sits, whatever the layout model called it (a form's label at the foot of its
    # box, "Schedule A (Form 990) 2022", 8e953483); a title in display type that repeats it
    # is the title.
    furniture = {re.sub(r"\s+", " ", b.text).strip().lower(): (b.size or body) for b in blocks if b.kind in (BlockKind.HEADER, BlockKind.FOOTER) and b.text.strip()}
    for b in blocks:
        if b.kind in (BlockKind.TEXT, BlockKind.HEADING) and b.lines and len(b.lines) <= 2 and len(b.text) <= 80:
            fsize = furniture.get(re.sub(r"\s+", " ", b.text).strip().lower())
            if fsize is not None and (b.size or body) <= 1.2 * fsize:
                b.kind = BlockKind.HEADER if b.bbox.y0 < H / 2 else BlockKind.FOOTER
                b.provenance = "repeated-head"


def _attach_marks(pdf_page: "pymupdf.Page", page: Page, blocks: list[Block]) -> None:
    """Put the meaning of drawn marks (ticks, crosses, bullets) into the text.

    A mark inside a table cell joins that cell; a mark just left of a line
    starts that line. Anything else (a decorative icon in a figure) is left
    alone. Every mark is also listed in `page.meta["marks"]`.
    """
    from truedoc.marks import find_marks
    from truedoc.model import Char, Word

    try:
        M = pdf_page.rotation_matrix if pdf_page.rotation else None
        marks = find_marks(pdf_page, page, M)
    except Exception as exc:  # never fail a conversion over an icon
        import logging

        logging.getLogger("truedoc").warning("mark detection failed: %s", exc)
        return
    if not marks:
        return
    page.meta["marks"] = [{"kind": m.kind, "colour": m.colour, "score": round(m.score, 2), "bbox": [round(v, 1) for v in (m.bbox.x0, m.bbox.y0, m.bbox.x1, m.bbox.y1)]} for m in marks]
    size = page.body_font_size or 10.0
    tables = [b for b in blocks if b.kind == BlockKind.TABLE and b.table is not None]
    lines = [l for b in blocks if b.kind not in (BlockKind.TABLE, BlockKind.FIGURE) for l in b.lines]
    taken: set[int] = set()
    for m in marks:
        cx, cy = m.bbox.cx, m.bbox.cy
        placed = False
        for t in tables:
            for cell in t.table.cells:
                if cell.bbox is not None and cell.bbox.contains_point(cx, cy):
                    if m.kind != "unknown":
                        # An icon at the left edge of the cell leads the line it
                        # sits on ("✗ damage caused by..."); elsewhere it follows.
                        leading = cx < cell.bbox.x0 + 0.25 * cell.bbox.width
                        if not cell.text:
                            cell.text = m.text
                        elif leading:
                            cell.text = _insert_before_line(cell, page, m)
                        else:
                            cell.text = cell.text + " " + m.text
                    elif not cell.text:
                        cell.text = m.text  # an icon-only cell keeps a placeholder
                    placed = True
                    break
            if placed:
                break
        if placed or m.kind == "unknown":
            # Only a mark we can read starts a line; an unreadable shape next to
            # text is more often decoration than meaning.
            continue
        # A cluster of marks (a decorative row of dots) is not a line marker.
        if any(o is not m and abs(o.bbox.cy - cy) < 0.6 * m.bbox.height and abs(o.bbox.cx - cx) < 1.5 * max(size, m.bbox.width) for o in marks):
            continue
        # A mark at the head of a line: a bullet, a checklist tick.
        best = None
        for l in lines:
            if l.rotated or l.bbox.y1 < m.bbox.y0 or l.bbox.y0 > m.bbox.y1:
                continue
            if abs(l.bbox.cy - cy) > 0.7 * max(l.bbox.height, m.bbox.height):
                continue
            gap = l.bbox.x0 - m.bbox.x1
            # Hanging layouts put the icon a couple of ems left of the text.
            if -1.0 <= gap <= 3.0 * size and (best is None or gap < best[0]):
                best = (gap, l)
        if best is not None and id(best[1]) not in taken:
            l = best[1]
            taken.add(id(l))
            lsize = l.size or size
            ch = Char(text=m.text, bbox=m.bbox, font="mark", size=lsize, origin_y=l.bbox.y1)
            l.words.insert(0, Word(text=m.text, bbox=m.bbox, chars=[ch]))
            l.bbox = l.bbox.union(m.bbox)
            continue
        # A mark standing on its own in a picture region, with no line on its baseline to lead:
        # the arrow an insurance policy puts between two statements, carrying the word "then".
        # Only when it is the picture's whole content, so a decorative row of dots stays a
        # picture rather than becoming one character.
        for b in blocks:
            if b.kind is not BlockKind.FIGURE or b.lines or b.meta.get("mark_only"):
                continue
            if not b.bbox.contains_point(cx, cy):
                continue
            if sum(1 for o in marks if b.bbox.contains_point(o.bbox.cx, o.bbox.cy)) == 1:
                b.meta["mark_only"] = m.text
            break


def _insert_before_line(cell, page: Page, m) -> str:
    """Put the mark's character in front of the line of the cell it sits beside;
    a cell holding several ticked lines then reads "✓ item one ✓ item two"."""
    inside = [l for l in page.lines if cell.bbox.contains_point(l.bbox.cx, l.bbox.cy) and not l.rotated]
    beside = [l for l in inside if l.bbox.y1 > m.bbox.y0 and l.bbox.y0 < m.bbox.y1]
    if beside:
        line = min(beside, key=lambda l: abs(l.bbox.cy - m.bbox.cy))
        text = line.text.strip()
        if text:
            head = " ".join(text.split()[:4])
            pos = cell.text.find(head)
            if pos > 0:
                return cell.text[:pos] + m.text + " " + cell.text[pos:]
            if pos == 0:
                return m.text + " " + cell.text
    return m.text + " " + cell.text


def _read_unreadable_pages_with_model(doc: Document, path: str, opts: ConvertOptions) -> None:
    """The vision stage (D014, D019): every page without a digital text layer is
    read from its image by the model (a hidden OCR layer, or our own engine's
    reading, is another machine's guess at the words, not the document's text),
    and everything it returns is marked as inferred (D015): the page's text is one
    block with a note, the page number goes into `pages_with_model`, and the front
    matter lists the inference. The page's own lines witness the running heads and
    feet the model transcribed (`truedoc.vision.witness`); dropped lines are kept
    in the page's `vision_dropped`."""
    from truedoc.vision import make_provider

    try:
        provider = make_provider(opts.vision_endpoint, opts.vision_model)
    except Exception as exc:
        doc.warnings.append(f"vision stage unavailable: {exc}")
        return
    inferred: list[dict] = doc.metadata.setdefault("inferred", [])
    pages_with_model: list[int] = doc.metadata.setdefault("pages_with_model", [])
    from truedoc.vision.witness import strip_lines, strip_lines_from_ocr, strip_running_heads
    from truedoc.vision import corroborate

    corroboration: list[dict] = doc.metadata.setdefault("corroboration", [])

    for page in doc.pages:
        has_text = any(b.kind not in (BlockKind.FIGURE,) and (b.lines or b.table is not None or b.text_override) for b in page.blocks)
        if page.quality.kind == "digital" and has_text:
            continue
        text = provider.read_page(path, page.number)
        if not text:
            continue
        if _model_reading_is_partial(page, text):
            # The model returned far less text than the page demonstrably holds (a table it gave
            # up on, a dense page cut short): the page's own reading stays, and the file says so.
            page.meta["vision_partial"] = {"model_words": _word_count(text), "own_words": _own_words(page)}
            doc.warnings.append(f"page {page.number}: the model's reading was partial ({_word_count(text)} words against {_own_words(page)} in the page's own text); the page's own text kept")
            continue
        witness = page.lines or page.meta.get("witness_lines") or []
        top, bottom = strip_lines(witness, page.height)
        if (not top or not bottom) and opts.ocr:
            # A layer that covers only part of the page (a download stamp at the foot of a bare
            # scan) leaves a strip without a witness: our engine reads that strip.
            try:
                pdf = open_pdf(path)
                try:
                    pdf_page = pdf[page.number - 1]
                    if page.meta.get("turned"):
                        pdf_page.set_rotation((pdf_page.rotation + page.meta["turned"]) % 360)
                    t2, b2 = strip_lines_from_ocr(pdf_page, page.width, page.height, not top, not bottom)
                    top, bottom = top or t2, bottom or b2
                finally:
                    pdf.close()
            except Exception as exc:  # the witness is optional: never fail a conversion for it
                doc.warnings.append(f"strip witness failed on page {page.number}: {exc}")
        text, dropped = strip_running_heads(text, top, bottom)
        if dropped:
            page.meta["vision_dropped"] = dropped
        if not text:
            continue
        # D008, M6: check the model's reading against what we can read of the page ourselves,
        # before its own blocks are replaced. This only ever reports - measured over the 281
        # model-read benchmark pages, every low-support page had a broken witness rather than an
        # inventing model (a Persian page whose layer is mojibake, a formula our own rebuild
        # mangled), so acting on it would destroy correct readings.
        own = " ".join(l.text for l in page.lines) if page.lines else \
            " ".join(t for t, _y0, _y1 in (page.meta.get("witness_lines") or []))
        verdict = corroborate.check(text, own)
        page.meta["corroboration"] = verdict
        corroboration.append(dict(verdict, page=page.number))
        if verdict["state"] == "low support":
            doc.warnings.append(
                f"page {page.number}: {verdict['reason']}")
        page.meta["vision_replaced"] = page.quality.kind
        page.blocks = [Block(kind=BlockKind.TEXT, bbox=BBox(0.0, 0.0, page.width, page.height), text_override=text, provenance=f"vision:{provider.name}")]
        page.blocks[0].order = 0
        page.meta["vision_model"] = provider.name
        page.quality.kind = "vision"
        pages_with_model.append(page.number)
        inferred.append({"page": page.number, "kind": "page", "model": provider.name})
    if opts.vision_regions:
        _read_regions_with_model(doc, path, provider, inferred)


_PARTIAL_MIN_OWN_WORDS = 100    # the page's own reading must be substantial before it can outweigh the model's
_PARTIAL_RATIO = 2.0            # and hold this many times the model's words
_WORD_CHARS = re.compile(r"[^\W_]{2,}", re.UNICODE)


def _word_count(text: str) -> int:
    """Words of two letters or digits or more, the same way on both sides: a markdown table's
    pipes and rules are not words."""
    return len(_WORD_CHARS.findall(text))
_PARTIAL_MAX_GARBAGE = 0.1      # a suspect layer counts only when its text is clean


def _own_words(page: Page) -> int:
    """Words the page's own blocks carry (lines and table cells): the reading a reader would get."""
    parts = [l.text for b in page.blocks for l in (b.lines or [])]
    parts += [c.text for b in page.blocks if b.table is not None for c in b.table.cells]
    return _word_count(" ".join(parts))


def _model_reading_is_partial(page: Page, text: str) -> bool:
    """True when the model's reading is far shorter than the page's own text (D008 on model pages).

    The page's own reading is the hidden OCR layer or our engine's accepted reading; a rejected
    reading (a blank page) never counts, and a suspect layer counts only when its text is clean.
    Measured on run 55's 281 model pages (7 September): at a ratio of 2 three pages qualify, among
    them a table the model reduced to 59 words from 228, and keeping the page's own text there
    recovers four checks and gives back none; at 1.5 a dictionary page the model cut to 906 words
    from 1,660 joins them (+4/-1), and run 56 showed the raw layer count firing the rule wrongly on
    six more pages (-10), so the count is taken from the blocks and the ratio kept at 2."""
    # The page's own reading is what its blocks carry, not the raw layer: a hidden layer often
    # holds every word twice or words the body drops, and run 56 (8 September) lost ten checks
    # on six pages where the raw count was double the rendered one.
    own = _own_words(page)
    if own < _PARTIAL_MIN_OWN_WORDS or not page.lines:
        return False
    if page.quality.kind == "suspect" and page.quality.garbage_fraction > _PARTIAL_MAX_GARBAGE:
        return False
    if page.quality.kind not in ("ocr", "ocr-truedoc", "suspect"):
        return False
    return own >= _PARTIAL_RATIO * max(1, _word_count(text))


_ICON_MAX_PT = 80.0        # an image inside a table cell up to this size is an icon
_PICTURE_TEXT_MIN_AREA = 0.02   # a picture at least this share of the page may hold a table or text of its own
_MAX_REGIONS_PER_PAGE = 12  # a page of pictograms is not a page of forty model calls


def _read_region(provider, path: str, page: Page, box: BBox, kind: str):
    """Ask the vision provider about one region. A page that was turned upright
    (`_turn_page`) sends its turn along, so the crop the model sees is upright too;
    providers that predate the parameter are still called the old way."""
    turn = page.meta.get("turned", 0)
    if turn:
        return provider.read_region(path, page.number, (box.x0, box.y0, box.x1, box.y1), kind, turn=turn)
    return provider.read_region(path, page.number, (box.x0, box.y0, box.x1, box.y1), kind)


def _read_regions_with_model(doc: Document, path: str, provider, inferred: list[dict]) -> None:
    """Icons and figures read by a model (D015, items 1 and 4).

    An icon-only table cell (a pictogram the shape rules could not name, or an
    image sitting in a cell) is asked for its meaning, which goes into the cell
    with the inferred tag ("Covered[^inferred]"). A figure is asked for a
    description, which becomes the image's alt text with the same tag. Both go
    into the front matter's audit list. Cells that already hold text are left
    alone: the text says what the icon says.
    """
    from truedoc.render.okf import INFERRED_TAG
    from truedoc.vision.regions import split_picture_answer

    for page in doc.pages:
        if page.meta.get("vision_model"):
            continue  # the whole page was read by the model already
        budget = _MAX_REGIONS_PER_PAGE
        tables = [b.table for b in page.blocks if b.kind == BlockKind.TABLE and b.table is not None]
        page_area = max(page.width * page.height, 1.0)
        has_text = any(b.lines or b.text_override for b in page.blocks if b.kind != BlockKind.FIGURE)
        # 1. Icons in table cells: unnamed marks, and images small enough to be icons.
        candidates: list[BBox] = []
        for m in page.meta.get("marks") or []:
            if m.get("kind") == "unknown":
                candidates.append(BBox(*m["bbox"]))
        for img in page.images:
            b = img.bbox
            if max(b.width, b.height) > _ICON_MAX_PT or min(b.width, b.height) < 3.0:
                continue
            if any(c.overlap_fraction(b) > 0.5 for c in candidates):
                continue
            candidates.append(b)
        for box in candidates:
            cell = _cell_at(tables, box.cx, box.cy)
            if cell is None or (cell.text.strip() and cell.text.strip() != "[icon]"):
                continue
            if budget <= 0:
                break
            budget -= 1
            answer = _read_region(provider, path, page, box, "icon")
            if not answer:
                continue
            cell.text = answer + INFERRED_TAG
            inferred.append({"page": page.number, "kind": "icon", "text": answer, "model": provider.name, "bbox": [round(v, 1) for v in (box.x0, box.y0, box.x1, box.y1)]})
        # 2. Figures: charts, diagrams, pictures that are blocks of their own.
        for b in page.blocks:
            if b.kind != BlockKind.FIGURE or b.meta.get("inferred_text"):
                continue
            box = b.bbox
            if min(box.width, box.height) < 36.0:
                continue  # smaller than half an inch: a rule, an ornament, an inline icon
            if _cell_at(tables, box.cx, box.cy) is not None:
                continue  # an image inside a table cell is an icon, handled above
            if has_text and box.width * box.height > 0.6 * page_area:
                continue  # a background or scan behind the page's own text
            if budget <= 0:
                break
            budget -= 1
            # 3. A picture that holds none of the page's own words may hold text of its own (a
            # table pasted as a screenshot, a scanned block): the model transcribes it, and the
            # transcription becomes the figure's content (D019 applied to a region). Only then
            # is a figure asked for a description.
            words_inside = sum(1 for w in page.words if box.contains_point(w.bbox.cx, w.bbox.cy))
            if words_inside == 0 and box.width * box.height >= _PICTURE_TEXT_MIN_AREA * page_area:
                transcript, description = split_picture_answer(_read_region(provider, path, page, box, "picture-text"))
                if transcript:
                    b.text_override = transcript
                    b.meta["transcribed"] = True
                    b.meta["inferred_model"] = provider.name
                    inferred.append({"page": page.number, "kind": "picture-text", "text": transcript[:500], "model": provider.name, "bbox": [round(v, 1) for v in (box.x0, box.y0, box.x1, box.y1)]})
                    continue
                if description:
                    # The model saw a picture without text and described it: that is alt text (D015).
                    b.meta["inferred_text"] = description
                    b.meta["inferred_model"] = provider.name
                    inferred.append({"page": page.number, "kind": "figure", "text": description, "model": provider.name, "bbox": [round(v, 1) for v in (box.x0, box.y0, box.x1, box.y1)]})
                    continue
            answer = _read_region(provider, path, page, box, "figure")
            if not answer:
                continue
            b.meta["inferred_text"] = answer
            b.meta["inferred_model"] = provider.name
            inferred.append({"page": page.number, "kind": "figure", "text": answer, "model": provider.name, "bbox": [round(v, 1) for v in (box.x0, box.y0, box.x1, box.y1)]})


def _cell_at(tables, x: float, y: float):
    for t in tables:
        for cell in t.cells:
            if cell.bbox is not None and cell.bbox.contains_point(x, y):
                return cell
    return None


_PICTURE_OCR_MIN_SIDE = 72.0      # an inch: smaller pictures are icons and ornaments
_PICTURE_OCR_MAX_PER_PAGE = 6


def _ocr_text_pictures(pdf_page: "pymupdf.Page", page: Page, blocks: list[Block]) -> None:
    """Text that lives inside a picture on an otherwise digital page (a sidebar
    box saved as an image, a reference column, a screenshot) is read with the
    OCR engine and stands in for the picture (roadmap M13).

    Gated like page OCR: the engine must be confident and most tokens must look
    like words, and there must be a paragraph's worth of them, so a photograph
    with a caption or a chart with axis labels stays a figure. Whole-page OCR
    handles pages that have no text of their own; this runs only where the page
    does. What was read is listed under `truedoc.ocr_regions` in the front matter.
    """
    if not any(b.lines for b in blocks if b.kind != BlockKind.FIGURE):
        return
    try:
        from truedoc.ocr.rapid import _looks_like_text, ocr_region
    except Exception:
        return
    page_area = max(page.width * page.height, 1.0)
    tables = [b for b in blocks if b.kind == BlockKind.TABLE]
    done = 0
    for fig in [b for b in blocks if b.kind == BlockKind.FIGURE]:
        box = fig.bbox
        if min(box.width, box.height) < _PICTURE_OCR_MIN_SIDE or box.width * box.height > 0.6 * page_area:
            continue
        if any(t.bbox.overlap_fraction(box) > 0.5 or box.overlap_fraction(t.bbox) > 0.5 for t in tables):
            continue
        # Text the page already carries inside the picture's box (a banner drawn
        # over an image) must not be read twice.
        if any(b.kind != BlockKind.FIGURE and b.lines and b.bbox.overlap_fraction(box) > 0.2 for b in blocks):
            continue
        if done >= _PICTURE_OCR_MAX_PER_PAGE:
            break
        done += 1
        try:
            lines, conf, wordlike = ocr_region(pdf_page, box)
        except Exception as exc:  # OCR is optional: never fail a conversion over a picture
            import logging

            logging.getLogger("truedoc").warning("picture ocr failed: %s", exc)
            continue
        words = [w for l in lines for w in l.words]
        if len(lines) < 3 or len(words) < 12 or conf < 0.8 or wordlike < 0.6:
            continue
        new_blocks = build_blocks(page, lines)
        if not new_blocks:
            continue
        for b in new_blocks:
            b.provenance = "ocr-region"
            b.confidence = min(b.confidence, round(conf, 2))
            b.meta["ocr_region"] = True
        blocks.remove(fig)
        blocks.extend(new_blocks)
        page.meta.setdefault("ocr_regions", []).append({"bbox": [round(v, 1) for v in (box.x0, box.y0, box.x1, box.y1)], "confidence": round(conf, 2), "words": len(words)})


def _adopt_ruled_headers(tables: list[Block], lines, size: float) -> tuple[list[Block], list]:
    """Column headings printed just above a ruled box become the table's header row.

    Forms and minutes often box the body rows and set the headings unruled
    above the box ("Action Item / Who Will Do / Due Date" over one boxed row).
    A text line sitting within a line height of the box's top, whose words fall
    into the box's columns (at least two of them, none outside), is that
    header. A boxed single row is only a table once it has such a header;
    without one it is a framed line of text and is left alone.
    """
    from truedoc.model import TableCell

    kept: list[Block] = []
    used: set[int] = set()
    for tb in tables:
        t = tb.table
        if t is None:
            kept.append(tb)
            continue
        cols = [c for c in t.cells if c.row == 0 and c.bbox is not None]
        cols.sort(key=lambda c: c.col)
        adopted = None
        # Only a one-row box wants a header from outside: a ruled table of several
        # rows carries its own, and the line above it is a caption. A one-row box
        # whose columns continue in unruled lines directly below it is the header
        # of a larger table that the whitespace finder builds whole, so it is
        # dropped here rather than adopted.
        def _in_columns(l) -> bool:
            if l.bbox.x0 < t.bbox.x0 - size or l.bbox.x1 > t.bbox.x1 + size:
                return False
            hit_cols = set()
            for w in l.words:
                hit = next((c.col for c in cols if c.bbox.x0 - 0.3 * size <= w.bbox.cx <= c.bbox.x1 + 0.3 * size), None)
                if hit is None:
                    return False
                hit_cols.add(hit)
            return len(hit_cols) >= 2

        continues_below = t.n_rows == 1 and any(
            not l.rotated and l.words and t.bbox.y1 - 1.0 <= l.bbox.y0 <= t.bbox.y1 + 1.8 * size and _in_columns(l)
            for l in lines if id(l) not in used)
        # A frame taller than a couple of lines is a box around a column of rows, not a row.
        single_row = t.n_rows == 1 and t.bbox.height <= 2.5 * size
        # A box of several rows carries its own heading, unless its first row is
        # plainly data (a cell of more than four words, or one starting lowercase
        # or with a symbol: "driverTypeAddress | Address of the Driver Type"); then
        # the heading printed above the box ("# | Attribute | Description") is its
        # heading as much as a one-row box's is.
        first = [c.text.strip() for c in t.cells if c.row == 0 and c.text.strip()]
        headerless = t.n_rows >= 2 and bool(first) and any(len(x.split()) > 4 or x[:1].islower() or not x[:1].isalnum() for x in first)
        if ((single_row and not continues_below) or headerless) and len(cols) >= 2 and len(cols) == t.n_cols:
            # The headings of one row may arrive as separate lines (wide gaps between
            # columns split a line), so the band above the box is taken as a whole,
            # nearest baseline first.
            band = [l for l in lines if id(l) not in used and not l.rotated and l.words
                    and l.bbox.y1 <= t.bbox.y0 + 1.0 and l.bbox.y1 >= t.bbox.y0 - 1.6 * max(size, l.size or size)
                    and l.bbox.x0 >= t.bbox.x0 - size and l.bbox.x1 <= t.bbox.x1 + size]
            if band:
                nearest = max(l.bbox.y1 for l in band)
                row_lines = [l for l in band if nearest - l.bbox.y1 <= 0.6 * size]
                words = [w for l in row_lines for w in l.words]
                buckets: dict[int, list] = {}
                outside = False
                for w in sorted(words, key=lambda w: w.bbox.x0):
                    hit = next((c.col for c in cols if c.bbox.x0 - 0.3 * size <= w.bbox.cx <= c.bbox.x1 + 0.3 * size), None)
                    if hit is None:
                        outside = True
                        break
                    buckets.setdefault(hit, []).append(w)
                if not outside and len(buckets) >= 2:
                    # Headings start at their column's left edge (or sit centred in it); a
                    # sentence that merely spans the box lines up with one column at most.
                    aligned = sum(1 for c in cols if c.col in buckets and abs(min(w.bbox.x0 for w in buckets[c.col]) - c.bbox.x0) <= 1.2 * size)
                    centred = sum(1 for c in cols if c.col in buckets
                                  and abs(sum(w.bbox.cx for w in buckets[c.col]) / len(buckets[c.col]) - c.bbox.cx) <= 1.0 * size)
                    if max(aligned, centred) >= 2:
                        adopted = (row_lines, buckets)
        if adopted is None:
            if t.n_rows >= 2:
                kept.append(tb)
            continue
        row_lines, buckets = adopted
        used.update(id(l) for l in row_lines)
        top = min(l.bbox.y0 for l in row_lines)
        for c in t.cells:
            c.row += 1
            if headerless:
                c.is_header = False   # the box's first row was data, not a heading
        for c in cols:
            t.cells.append(TableCell(text=clean_cell_text(" ".join(w.text for w in buckets.get(c.col, []))), row=0, col=c.col,
                                     bbox=BBox(c.bbox.x0, top, c.bbox.x1, t.bbox.y0), is_header=True))
        t.n_rows += 1
        t.bbox = BBox(t.bbox.x0, min(t.bbox.y0, top), t.bbox.x1, t.bbox.y1)
        tb.bbox = t.bbox
        kept.append(tb)
    if used:
        lines = [l for l in lines if id(l) not in used]
    return kept, lines


def _short_cell_share(table) -> float:
    """Share of filled cells of three words or fewer: a grid of labels or names."""
    filled = [c.text.strip() for c in table.cells if c.text.strip()]
    if not filled:
        return 0.0
    return sum(1 for t in filled if len(t.split()) <= 3) / len(filled)


def _numeric_share(table) -> float:
    """Share of filled cells that are numbers: a data block reads mostly numbers."""
    import re

    filled = [c.text.strip() for c in table.cells if c.text.strip()]
    if not filled:
        return 0.0
    numeric = sum(1 for t in filled if re.fullmatch(r"[-+(]?[\d.,]+%?\)?|-|--|n/?a", t, re.I))
    return numeric / len(filled)


_NUMBER_TOKEN = re.compile(r"^[<>≤≥(]?[-+−]?[\d.,]+%?\)?[*†‡]{0,2}$")


def _rebuild_sparse_ruled_tables(tables: list[Block], lines, size: float) -> list[Block]:
    """A ruled table whose rules only frame the header (a crop report: boxed
    headings over an unruled body) comes back from the rule-based finder as one
    tall cell per column. When the text inside has far more rows than the table,
    rebuild it from the text lines, which know where the rows are."""
    from truedoc.tables.aligned import table_from_lines

    out: list[Block] = []
    size = size or 10.0
    for b in tables:
        inside = [l for l in lines if b.bbox.contains_point(l.bbox.cx, l.bbox.cy) and not l.rotated]
        if b.table is None or len(inside) < 6:
            out.append(b)
            continue
        centres = sorted(l.bbox.cy for l in inside)
        baselines = 1 + sum(1 for a, c in zip(centres, centres[1:]) if c - a > 0.5 * size)
        # A body cell holding a run of numbers ("2.82 <0.001 1.96 0.001 2.94
        # <0.001 2.63 0.04") is a sub-table the rules did not divide: a logistic
        # regression table ruled around its header and its two model blocks only.
        # (Only in a table of few rows: a bus timetable's note row holds many
        # numbers too, and rebuilding the timetable from its lines dragged a
        # running head into a cell.)
        crowded = b.table.n_rows <= 8 and any(c.row > 0 and sum(1 for tok in c.text.split() if _NUMBER_TOKEN.match(tok)) >= 6 for c in b.table.cells)
        # Only a table whose rules frame just the heading (one or two body rows
        # holding many lines) is suspect; a ruled table of wrapped prose cells
        # has many rows of its own and is left alone.
        if not crowded and (b.table.n_rows > 3 or b.table.n_rows * 2 >= baselines):
            out.append(b)
            continue
        rebuilt = table_from_lines(inside, size, trusted=True)
        # A crowded cell is evidence enough; its rebuild carries a title and
        # stacked headings that dilute the numeric share (0.21 on the regression table).
        share_needed = 0.15 if crowded else 0.3
        # A grid of short cells in several columns over many rows (a committee
        # list of names with tick columns, boxed as one cell by the rules) is a
        # table on its own evidence, numbers or not; boxed prose rebuilds, if at
        # all, as long cells in one or two columns.
        # (Only where the box holds three times more lines than the rules gave it
        # rows: an ordinary ruled schedule with a few wrapped cells is left as the
        # rules drew it.)
        grid_like = (rebuilt is not None and rebuilt.n_cols >= 3 and rebuilt.n_rows >= 6 and _short_cell_share(rebuilt) >= 0.8
                     and baselines >= 3 * b.table.n_rows)
        if rebuilt is not None and rebuilt.n_rows > b.table.n_rows and rebuilt.n_cols >= 2 and (_numeric_share(rebuilt) >= share_needed or grid_like):
            rebuilt.bbox = b.bbox
            rebuilt.provenance = "ruled-rebuilt"
            out.append(Block(kind=BlockKind.TABLE, bbox=b.bbox, table=rebuilt, provenance="ruled-rebuilt", confidence=b.confidence))
        else:
            out.append(b)
    return out


def _remove_blocks_inside_tables(blocks: list[Block], tables: list[Block]) -> list[Block]:
    kept: list[Block] = []
    for b in blocks:
        inside = False
        for t in tables:
            if b.bbox.overlap_fraction(t.bbox) > 0.5:
                inside = True
                break
        if not inside:
            kept.append(b)
    return kept


def _estimate_confidence(doc: Document) -> float:
    if not doc.pages:
        return 0.0
    scores = []
    for p in doc.pages:
        if not p.quality.usable:
            scores.append(0.0)
        elif p.quality.kind == "digital":
            scores.append(0.9)
        elif p.quality.kind == "vision":
            scores.append(0.5)   # a model's reading of an image: useful, not evidence
        else:
            scores.append(0.6)
    return round(sum(scores) / len(scores), 3)


def convert(path: str, opts: ConvertOptions | None = None) -> str:
    opts = opts or ConvertOptions()
    doc = load_document(path, opts)
    ropts = RenderOptions(frontmatter=opts.frontmatter, page_markers=opts.page_markers)
    return render_document(doc, ropts)
