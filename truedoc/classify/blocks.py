"""Assign a kind (heading, header, footer, list item, caption ...) to each block.

Heuristics only. Every rule here is a candidate for replacement by a model
later, which is why each block records its provenance.
"""

from __future__ import annotations

import re

from truedoc.model import Block, BlockKind, Page

_PAGE_NUMBER = re.compile(
    r"^\s*(?:page\s+)?(?:\d{1,4}|[ivxlcdm]{1,7})(?:\s*(?:/|of)\s*\d{1,4})?\s*$", re.IGNORECASE
)
_CAPTION = re.compile(r"^\s*(?:figure|fig\.?|table|tab\.?|chart|scheme|plate|exhibit)\s*[\dIVX]+[.:\-\s]", re.IGNORECASE)
_LIST_START = re.compile(
    r"^\s*(?:[•◦▪●‣⁃■□·]|[-–—\*](?=\s)|"
    r"\(?\d{1,3}[.)](?=\s)|\(?[a-z][.)](?=\s)|\([A-Z]\)(?=\s)|[A-Z]\)(?=\s)|\(?[ivx]{1,6}[.)](?=\s))",
)
_NUMBERED_HEADING = re.compile(r"^\s*(\d{1,2}(?:\.\d{1,2}){0,4})\.?\s+\S")
_CONTACT = re.compile(
    r"(https?://|www\.|\b[\w.+-]+@[\w-]+\.[\w.]+|\bdoi\b|\bdoi:|10\.\d{4,}/|journal homepage|available (online )?at|"
    r"downloaded from|\b\d{3}[-. ]\d{3}[-. ]\d{4}\b|\bfecha y hora\b|\bcustodiado\b|\bcopyright\b|©|"
    # a bare web address ("health.ucsd.edu/jacobs"): a host name with a familiar top-level domain
    r"\b[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:edu|org|com|gov|net|int|mil|ac\.uk|co\.uk|org\.uk|gov\.uk|de|fr|ch|au|ca|io|nl|es|it|se|no|dk|fi|be|at|nz|ie|jp|cn|in|br)(?:/[^\s]*)?(?=[\s.,;:)]|$)|"
    # journal running heads and dated stamps: "v. 19, n. 1 (2021)", "Vol. 3, No. 2", "ISSN", "Date: 2019-03-15".
    # A volume alone is not enough: manuscript citations read "Ff. v. 48, f. 114."
    r"\bv(?:ol)?\.?\s*\d+[,.]?\s*n[oº°]?\.?\s*\d+|\bissn\b|\bdate:\s*\d|\b\d{4}-\d{2}-\d{2}\b)",
    re.IGNORECASE,
)
_SECTION_WORDS = re.compile(
    r"^\s*(?:abstract|introduction|conclusions?|references|acknowledg\w*|appendix|bibliography|summary|"
    r"background|methods?|results?|discussion|keywords?)\b[:.]?\s*$",
    re.IGNORECASE,
)


def classify_blocks(page: Page, blocks: list[Block], pdf_page=None) -> None:
    body = page.body_font_size or 10.0

    def runs(b: Block) -> bool:
        """Not shown to stop at this page: a page beside it prints it at its head, or none can be asked."""
        from truedoc.layout.fuse import _repeated_beside    # imported here: fuse imports this module
        return _repeated_beside(b, page, pdf_page) is not False
    top_zone = 0.09 * page.height
    bottom_zone = page.height - 0.09 * page.height

    # Main text mass: where do most characters live vertically?
    for b in blocks:
        if b.kind != BlockKind.TEXT:
            continue
        text = b.text.strip()
        n_lines = len(b.lines)
        size = b.size or body

        if _PAGE_NUMBER.match(text) and (b.bbox.y1 <= top_zone * 1.3 or b.bbox.y0 >= bottom_zone * 0.97):
            b.kind = BlockKind.PAGE_NUMBER
            continue

        # Web addresses, e-mails, phone numbers and signing stamps in the margins are
        # running headers or footers whatever their length.
        if _CONTACT.search(text) and n_lines <= 6:
            # (up to six lines: a "how to cite this article" block with the journal
            # line and page number is a running footer too)
            if b.bbox.y1 <= 0.18 * page.height:  # journal heads ("journal homepage: ...") sit as low as 15%
                b.kind = BlockKind.HEADER
                continue
            if b.bbox.y0 >= page.height - 0.14 * page.height:
                b.kind = BlockKind.FOOTER
                continue
        # Running headers: small, short, in the top margin - and running: a line no page beside it prints at its head
        # is the page's own, however small. With no page beside it to ask, the zone decides.
        if b.bbox.y1 <= top_zone and n_lines <= 2 and len(text) <= 160 and size <= body * 1.3 and runs(b):
            b.kind = BlockKind.HEADER
            continue
        # Running footers: short text in the bottom margin (footnotes are longer, handled below).
        if b.bbox.y0 >= bottom_zone and n_lines <= 3 and len(text) <= 200 and size <= body * 1.05:
            if size < body * 0.9 and n_lines >= 2 and len(text) > 90:
                b.kind = BlockKind.FOOTNOTE
            else:
                b.kind = BlockKind.FOOTER
            continue

        if _CAPTION.match(text) and n_lines <= 6:
            b.kind = BlockKind.CAPTION
            continue

        if _LIST_START.match(text):
            b.kind = BlockKind.LIST_ITEM
            continue

        # Headings: larger than body, or bold and short. (Font sizes in hidden OCR
        # layers are meaningless, so size-based rules are skipped there.)
        is_short = n_lines <= 3 and len(text) <= 200 and not text.endswith((".", ",", ";"))
        sizes_reliable = page.quality.kind != "ocr"
        if sizes_reliable and size >= body * 1.15 and is_short:
            b.kind = BlockKind.HEADING
        elif sizes_reliable and b.lines and b.lines[0].bold and n_lines <= 2 and len(text) <= 120 and size >= body * 0.9 and not text.endswith((",", ";")):
            b.kind = BlockKind.HEADING
        elif (_NUMBERED_HEADING.match(text) and n_lines == 1 and len(text) <= 100 and (b.lines[0].bold or size >= body * 1.05 or b.meta.get("heading_like"))
              and not (size < 0.9 * body and b.bbox.y0 >= 0.8 * page.height)):   # "9 Ibid" in small type at the foot is a note
            b.kind = BlockKind.HEADING
        elif _SECTION_WORDS.match(text) and n_lines == 1:
            b.kind = BlockKind.HEADING

    _drop_margin_line_numbers(page, blocks)
    _assign_heading_levels(blocks, body)


_INTEGER = re.compile(r"^\s*\d{1,4}\s*$")


def _drop_margin_line_numbers(page: Page, blocks: list[Block]) -> None:
    """Manuscript line numbers: a vertical column of increasing small integers.

    They sit in the left or right margin, or (patents) in the gutter between two
    columns. Any x-aligned column of at least four increasing integers spanning
    a good part of the page height is one.
    """
    ints = [
        b for b in blocks
        if b.kind in (BlockKind.TEXT, BlockKind.PAGE_NUMBER, BlockKind.HEADER, BlockKind.FOOTER) and _INTEGER.match(b.text)
    ]
    if len(ints) < 4:
        return
    ints.sort(key=lambda b: b.bbox.cx)
    clusters: list[list[Block]] = [[ints[0]]]
    for b in ints[1:]:
        if abs(b.bbox.cx - clusters[-1][-1].bbox.cx) <= 15.0:
            clusters[-1].append(b)
        else:
            clusters.append([b])
    for cl in clusters:
        if len(cl) < 4:
            continue
        ordered = sorted(cl, key=lambda b: b.bbox.y0)
        span = ordered[-1].bbox.y1 - ordered[0].bbox.y0
        if span < 0.25 * page.height:
            continue
        values = [int(b.text.strip()) for b in ordered]
        increasing = sum(1 for a, c in zip(values, values[1:]) if c > a)
        if increasing < 0.7 * (len(values) - 1):
            continue
        for b in cl:
            b.kind = BlockKind.PAGE_NUMBER
            b.provenance = "margin-line-number"


def _assign_heading_levels(blocks: list[Block], body: float) -> None:
    heads = [b for b in blocks if b.kind == BlockKind.HEADING]
    if not heads:
        return
    sizes = sorted({round(b.size, 1) for b in heads}, reverse=True)
    for b in heads:
        m = _NUMBERED_HEADING.match(b.text)
        if m:
            depth = m.group(1).count(".") + 1
            b.level = min(6, depth + 1)
            continue
        rank = sizes.index(round(b.size, 1)) + 1
        if b.size >= body * 1.6:
            b.level = 1
        else:
            b.level = min(6, max(1, rank + (1 if sizes and sizes[0] >= body * 1.6 else 0)))
