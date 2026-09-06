from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from PIL import Image

from truedoc.model import BBox


class RegionKind(str, Enum):
    TEXT = "text"
    TITLE = "title"
    SECTION_HEADER = "section_header"
    LIST_ITEM = "list_item"
    TABLE = "table"
    FIGURE = "figure"
    CAPTION = "caption"
    FORMULA = "formula"
    PAGE_HEADER = "page_header"
    PAGE_FOOTER = "page_footer"
    FOOTNOTE = "footnote"
    CODE = "code"
    KEY_VALUE = "key_value"
    FORM = "form"
    OTHER = "other"


@dataclass
class Region:
    kind: RegionKind
    bbox: BBox            # PDF points
    score: float = 1.0
    source: str = ""


class LayoutDetector(Protocol):
    name: str

    def detect(self, image: Image.Image, scale: float) -> list[Region]:
        """Detect regions on a rendered page.

        `scale` is pixels per PDF point for `image`; implementations must
        divide pixel coordinates by it so that regions come back in points.
        """
        ...
