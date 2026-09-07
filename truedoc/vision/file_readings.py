"""A vision provider that reads a model's saved page readings from disk.

Chosen with `--vision-endpoint file:<folder>`. The folder holds one markdown file per page,
named as the benchmark candidates are (`<category>/<stem>_pg1_repeat1.md`), or `<stem>_pg<N>.md`
or `<stem>.md` anywhere below the folder. It exists so that a model's readings made once on a
rented GPU (olmOCR 2 over the 281 benchmark pages without a digital text layer, 7 September
2026) can be replayed through the whole pipeline, page selection, running-head witness and
inferred markers included, without a served model: the proper benchmark run with the vision
switch on, from disk. Regions (icons, figures) are not answered from disk.
"""

from __future__ import annotations

import os
import re

_YAML_BLOCK = re.compile(r"\A---\s*\n.*?\n---\s*\n", re.S)


class FileReadings:
    """`folder` may name several folders joined with '+': page readings in one, crop readings in
    another. A folder holding a `manifest.json` (written by `bench/gpu/select_regions.py`: crop
    name, page id, bbox) answers region questions of kind "picture-text" for those crops."""

    def __init__(self, folder: str, model: str = "olmocr") -> None:
        self.folder = folder
        self.name = model
        self._index: dict[str, str] = {}
        self._regions: dict[str, list[tuple[tuple[float, float, float, float], str]]] = {}
        folders = [f.strip() for f in folder.split("+") if f.strip()]
        for f in folders:
            if not os.path.isdir(f):
                raise FileNotFoundError(f"vision readings folder not found: {f}")
        for f in folders:
            for root, _dirs, files in os.walk(f):
                for name in files:
                    if name.endswith(".md"):
                        self._index.setdefault(name, os.path.join(root, name))
            manifest = os.path.join(f, "manifest.json")
            if os.path.exists(manifest):
                import json

                for entry in json.load(open(manifest, encoding="utf-8")):
                    stem = entry["page"].split("/", 1)[-1]
                    crop_stem = os.path.basename(entry["crop"])[:-4] if entry["crop"].endswith(".pdf") else os.path.basename(entry["crop"])
                    self._regions.setdefault(stem, []).append((tuple(entry["bbox"]), crop_stem))

    def _find(self, stem: str, page_number: int) -> str | None:
        for name in (f"{stem}_pg{page_number}_repeat1.md", f"{stem}_pg{page_number}.md", f"{stem}.md"):
            if name in self._index:
                return self._index[name]
        return None

    def read_page(self, pdf_path: str, page_number: int) -> str | None:
        stem = os.path.splitext(os.path.basename(pdf_path))[0]
        path = self._find(stem, page_number)
        if path is None:
            return None
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        text = _YAML_BLOCK.sub("", text, count=1).strip()
        return text or None

    def read_region(self, pdf_path: str, page_number: int, bbox, kind: str, turn: int = 0) -> str | None:
        if kind != "picture-text":
            return None
        stem = os.path.splitext(os.path.basename(pdf_path))[0]
        best, best_iou = None, 0.0
        for box, crop_stem in self._regions.get(stem, []):
            iou = _iou(box, tuple(bbox))
            if iou > best_iou:
                best, best_iou = crop_stem, iou
        if best is None or best_iou < 0.5:
            return None
        path = self._find(best, page_number) or self._find(best, 1)
        if path is None:
            return None
        with open(path, encoding="utf-8") as fh:
            text = _YAML_BLOCK.sub("", fh.read(), count=1).strip()
        return text or None


def _iou(a, b) -> float:
    ix0, iy0, ix1, iy1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, ix1 - ix0) * max(0.0, iy1 - iy0)
    if inter <= 0:
        return 0.0
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0
