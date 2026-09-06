"""Layout detection with the Docling "heron" layout model (RT-DETR v2, Apache-2.0).

Weights are fetched once from Hugging Face (ds4sd/docling-layout-heron) into
the local HF cache and the model runs on CPU through `transformers`.
Detection returns regions in PDF points.
"""

from __future__ import annotations

import os
import threading
from typing import Optional

from PIL import Image

from truedoc.layout.base import LayoutDetector, Region, RegionKind
from truedoc.model import BBox

_LABEL_MAP = {
    "caption": RegionKind.CAPTION,
    "footnote": RegionKind.FOOTNOTE,
    "formula": RegionKind.FORMULA,
    "list_item": RegionKind.LIST_ITEM,
    "page_footer": RegionKind.PAGE_FOOTER,
    "page_header": RegionKind.PAGE_HEADER,
    "picture": RegionKind.FIGURE,
    "section_header": RegionKind.SECTION_HEADER,
    "table": RegionKind.TABLE,
    "text": RegionKind.TEXT,
    "title": RegionKind.TITLE,
    "document_index": RegionKind.TABLE,
    "code": RegionKind.CODE,
    "checkbox_selected": RegionKind.OTHER,
    "checkbox_unselected": RegionKind.OTHER,
    "form": RegionKind.FORM,
    "key_value_region": RegionKind.KEY_VALUE,
}

_DEFAULT_REPO = os.environ.get("TRUEDOC_LAYOUT_REPO", "ds4sd/docling-layout-heron")


class DoclingLayoutDetector(LayoutDetector):
    name = "docling-heron"

    def __init__(self, repo_id: str = _DEFAULT_REPO, threshold: float = 0.3, num_threads: int = 4):
        self.repo_id = repo_id
        self.threshold = threshold
        self.num_threads = num_threads
        self._model = None
        self._processor = None
        self._lock = threading.Lock()

    def _load(self):
        if self._model is not None:
            return
        with self._lock:
            if self._model is None:
                import torch
                from transformers import AutoImageProcessor, RTDetrV2ForObjectDetection
                from transformers.utils import logging as hf_logging

                hf_logging.set_verbosity_error()
                hf_logging.disable_progress_bar()
                torch.set_num_threads(self.num_threads)
                self._processor = AutoImageProcessor.from_pretrained(self.repo_id)
                model = RTDetrV2ForObjectDetection.from_pretrained(self.repo_id)
                model.eval()
                self._model = model

    def detect(self, image: Image.Image, scale: float) -> list[Region]:
        self._load()
        import torch

        img = image.convert("RGB")
        inputs = self._processor(images=[img], return_tensors="pt")
        with torch.inference_mode():
            outputs = self._model(**inputs)
        target_sizes = torch.tensor([[img.height, img.width]])
        results = self._processor.post_process_object_detection(outputs, threshold=self.threshold, target_sizes=target_sizes)[0]
        id2label = self._model.config.id2label
        out: list[Region] = []
        for score, label_id, box in zip(results["scores"], results["labels"], results["boxes"]):
            label = id2label[int(label_id)]
            kind = _LABEL_MAP.get(label, RegionKind.OTHER)
            x0, y0, x1, y1 = [float(v) / scale for v in box.tolist()]
            out.append(Region(kind=kind, bbox=BBox(x0, y0, x1, y1), score=float(score), source=self.name))
        return out


_shared: Optional[DoclingLayoutDetector] = None


def get_detector() -> DoclingLayoutDetector:
    global _shared
    if _shared is None:
        _shared = DoclingLayoutDetector()
    return _shared
