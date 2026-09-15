"""Core data model.

Everything TrueDoc knows about a page is *evidence* (characters, words, lines,
drawings, images) or *structure* (blocks with a kind and a reading order).
Evidence is never modified; structure is derived from it and carries a
confidence and a provenance so later stages can second-guess earlier ones.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable, Optional


@dataclass(frozen=True)
class BBox:
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def width(self) -> float:
        return max(0.0, self.x1 - self.x0)

    @property
    def height(self) -> float:
        return max(0.0, self.y1 - self.y0)

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def cx(self) -> float:
        return (self.x0 + self.x1) / 2.0

    @property
    def cy(self) -> float:
        return (self.y0 + self.y1) / 2.0

    def union(self, other: "BBox") -> "BBox":
        return BBox(min(self.x0, other.x0), min(self.y0, other.y0), max(self.x1, other.x1), max(self.y1, other.y1))

    def intersection(self, other: "BBox") -> Optional["BBox"]:
        x0, y0 = max(self.x0, other.x0), max(self.y0, other.y0)
        x1, y1 = min(self.x1, other.x1), min(self.y1, other.y1)
        if x1 <= x0 or y1 <= y0:
            return None
        return BBox(x0, y0, x1, y1)

    def overlap_fraction(self, other: "BBox") -> float:
        """Fraction of *this* box's area covered by `other`."""
        inter = self.intersection(other)
        if inter is None or self.area <= 0:
            return 0.0
        return inter.area / self.area

    def x_overlap(self, other: "BBox") -> float:
        return max(0.0, min(self.x1, other.x1) - max(self.x0, other.x0))

    def y_overlap(self, other: "BBox") -> float:
        return max(0.0, min(self.y1, other.y1) - max(self.y0, other.y0))

    def contains_point(self, x: float, y: float) -> bool:
        return self.x0 <= x <= self.x1 and self.y0 <= y <= self.y1

    def expand(self, dx: float, dy: float | None = None) -> "BBox":
        if dy is None:
            dy = dx
        return BBox(self.x0 - dx, self.y0 - dy, self.x1 + dx, self.y1 + dy)

    @staticmethod
    def union_all(boxes: Iterable["BBox"]) -> Optional["BBox"]:
        result: Optional[BBox] = None
        for b in boxes:
            result = b if result is None else result.union(b)
        return result

    def as_tuple(self) -> tuple[float, float, float, float]:
        return (self.x0, self.y0, self.x1, self.y1)


@dataclass
class Char:
    text: str
    bbox: BBox
    font: str
    size: float
    flags: int = 0          # PyMuPDF span flags: 1 superscript, 2 italic, 4 serif, 8 mono, 16 bold
    color: int = 0
    origin_y: float = 0.0   # baseline y
    ink: BBox | None = None  # measured outline box, kept for maths-extension glyphs whose font box is meaningless
    hidden: str = ""         # why a reader cannot see this character ("" = visible): tiny, invisible, covered, same-colour

    @property
    def bold(self) -> bool:
        f = self.font.lower()
        if bool(self.flags & 16) or "bold" in f or "black" in f or "heavy" in f:
            return True
        # TeX's bold faces carry no "bold" in their names: cmbx, sfbx, cmssbx, cmbsy, cmmib.
        return any(h in f for h in ("cmbx", "sfbx", "cmssbx", "cmbsy", "cmmib", "txb", "pxb"))

    @property
    def italic(self) -> bool:
        low = self.font.lower()
        # URW/Nimbus Type 1 fonts (txfonts, pxfonts, mathptmx) name their italics
        # "ReguItal", "MediItal", "-Ital", "-BoldItal" and set no italic flag.
        return bool(self.flags & 2) or "italic" in low or "oblique" in low or low.endswith("ital") \
            or "-ital" in low or low.endswith("-it") or low.endswith("-bi")

    @property
    def superscript(self) -> bool:
        return bool(self.flags & 1)


@dataclass
class Word:
    text: str
    bbox: BBox
    chars: list[Char] = field(default_factory=list)
    after_space: bool = False   # the text layer put an explicit space before this word

    @property
    def size(self) -> float:
        if not self.chars:
            return 0.0
        return sum(c.size for c in self.chars) / len(self.chars)

    @property
    def font(self) -> str:
        if not self.chars:
            return ""
        counts: dict[str, int] = {}
        for c in self.chars:
            counts[c.font] = counts.get(c.font, 0) + 1
        return max(counts.items(), key=lambda kv: kv[1])[0]

    @property
    def bold(self) -> bool:
        return bool(self.chars) and sum(1 for c in self.chars if c.bold) > len(self.chars) / 2

    @property
    def italic(self) -> bool:
        return bool(self.chars) and sum(1 for c in self.chars if c.italic) > len(self.chars) / 2

    @property
    def baseline(self) -> float:
        if not self.chars:
            return self.bbox.y1
        # The baseline of the word's main text: a subscript glued to a letter, or a
        # maths-extension glyph (whose origin sits at its top), must not drag it.
        big = max(c.size for c in self.chars)
        main = [c for c in self.chars if c.size >= 0.85 * big and "CMEX" not in c.font.upper()]
        if not main:
            main = self.chars
        return sum(c.origin_y for c in main) / len(main)


@dataclass
class Line:
    words: list[Word]
    bbox: BBox
    rotated: bool = False   # text running vertically (typical of "Downloaded from ..." stamps)

    @property
    def text(self) -> str:
        return " ".join(w.text for w in self.words)

    @property
    def size(self) -> float:
        """The size of the line's main text.

        The largest character size that covers a real share of the line, so a
        fragment heavy with sub- and superscripts ("λ−1" with two script-sized
        glyphs) still reports the size of its letters, and a lone drop cap does
        not inflate a body line.
        """
        counts: dict[float, int] = {}
        total = 0
        for w in self.words:
            for c in w.chars:
                if c.size > 0:
                    s = round(c.size, 1)
                    counts[s] = counts.get(s, 0) + 1
                    total += 1
        if not counts:
            ws = [w.size for w in self.words if w.size > 0]
            return sum(ws) / len(ws) if ws else 0.0
        for s in sorted(counts, reverse=True):
            if counts[s] >= 0.3 * total:
                return s
        return max(counts.items(), key=lambda kv: (kv[1], kv[0]))[0]

    @property
    def baseline(self) -> float:
        """Baseline of the main text (scripts and maths-extension glyphs excluded)."""
        size = self.size
        main = [c for w in self.words for c in w.chars if c.size >= 0.85 * size and "CMEX" not in c.font.upper()]
        if not main:
            main = [c for w in self.words for c in w.chars]
        if not main:
            return self.bbox.y1
        return sum(c.origin_y for c in main) / len(main)

    @property
    def bold(self) -> bool:
        n = sum(len(w.text) for w in self.words) or 1
        return sum(len(w.text) for w in self.words if w.bold) > n / 2

    @property
    def italic(self) -> bool:
        n = sum(len(w.text) for w in self.words) or 1
        return sum(len(w.text) for w in self.words if w.italic) > n / 2


class BlockKind(str, Enum):
    TEXT = "text"
    HEADING = "heading"
    LIST_ITEM = "list_item"
    TABLE = "table"
    FIGURE = "figure"
    CAPTION = "caption"
    HEADER = "header"          # running page header
    FOOTER = "footer"          # running page footer
    PAGE_NUMBER = "page_number"
    FOOTNOTE = "footnote"
    FORMULA = "formula"
    CODE = "code"
    TITLE = "title"
    UNKNOWN = "unknown"


@dataclass
class CellItem:
    """An entry of a list set inside a table cell (D028): its words with its tick or cross, the sub-list under it, and
    the words that carry it on after the sub-list."""
    text: str
    children: list[str] = field(default_factory=list)
    tail: str = ""


@dataclass
class CellList:
    """A list set inside a table cell (D028): the words before it, its entries, and a note after it."""
    items: list[CellItem]
    lead: str = ""
    note: str = ""


@dataclass
class TableCell:
    text: str
    row: int
    col: int
    rowspan: int = 1
    colspan: int = 1
    bbox: Optional[BBox] = None
    is_header: bool = False
    listing: Optional[CellList] = None   # the cell's text read as the list it is set as (D028); `text` stays whole


@dataclass
class Table:
    n_rows: int
    n_cols: int
    cells: list[TableCell]
    bbox: BBox
    has_merged: bool = False
    provenance: str = ""

    def grid(self) -> list[list[Optional[TableCell]]]:
        g: list[list[Optional[TableCell]]] = [[None] * self.n_cols for _ in range(self.n_rows)]
        for c in self.cells:
            for r in range(c.row, min(self.n_rows, c.row + c.rowspan)):
                for k in range(c.col, min(self.n_cols, c.col + c.colspan)):
                    if g[r][k] is None:
                        g[r][k] = c
        return g


@dataclass
class Block:
    kind: BlockKind
    bbox: BBox
    lines: list[Line] = field(default_factory=list)
    order: int = -1
    level: int = 0                      # heading level or list nesting
    confidence: float = 1.0
    provenance: str = "textlayer"
    table: Optional[Table] = None
    text_override: Optional[str] = None  # when content came from a model rather than lines
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def text(self) -> str:
        if self.text_override is not None:
            return self.text_override
        return "\n".join(l.text for l in self.lines)

    @property
    def size(self) -> float:
        ss = [l.size for l in self.lines if l.size > 0]
        return sum(ss) / len(ss) if ss else 0.0

    @property
    def n_chars(self) -> int:
        return sum(len(w.text) for l in self.lines for w in l.words)


@dataclass
class Drawing:
    """A vector path summary: we only keep straight segments and filled rectangles."""
    kind: str                    # "hline", "vline", "rect"
    bbox: BBox
    width: float = 0.0
    fill: bool = False


@dataclass
class ImageRef:
    bbox: BBox
    xref: int = 0


@dataclass
class TextQuality:
    """How much can the text layer be trusted?"""
    n_chars: int = 0
    n_alnum: int = 0
    bad_fraction: float = 0.0     # replacement chars, private-use, control chars
    garbage_fraction: float = 0.0  # tokens no language produces (symbols inside words, digits between letters): a broken OCR layer
    invisible_fraction: float = 0.0  # text drawn invisibly (typical of OCR layers)
    image_coverage: float = 0.0   # fraction of page covered by images
    kind: str = "none"            # "none" | "digital" | "ocr" | "suspect"

    @property
    def usable(self) -> bool:
        # "vision": the page was read from its image by a model (D014); the text
        # layer's own character count says nothing about that reading.
        return self.kind == "vision" or (self.kind in ("digital", "ocr", "ocr-truedoc") and self.n_alnum >= 20)


@dataclass
class Page:
    number: int                  # 1-based
    width: float
    height: float
    rotation: int = 0
    chars: list[Char] = field(default_factory=list)
    words: list[Word] = field(default_factory=list)
    lines: list[Line] = field(default_factory=list)
    blocks: list[Block] = field(default_factory=list)
    drawings: list[Drawing] = field(default_factory=list)
    images: list[ImageRef] = field(default_factory=list)
    quality: TextQuality = field(default_factory=TextQuality)
    body_font_size: float = 0.0
    meta: dict[str, Any] = field(default_factory=dict)
    hidden_text: list[dict[str, Any]] = field(default_factory=list)  # text a reader cannot see: {"text", "reason", "bbox"}

    @property
    def bbox(self) -> BBox:
        return BBox(0.0, 0.0, self.width, self.height)

    def ordered_blocks(self) -> list[Block]:
        return sorted(self.blocks, key=lambda b: b.order)


@dataclass
class Document:
    path: str
    pages: list[Page] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    sha256: str = ""
