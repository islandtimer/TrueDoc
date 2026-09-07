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
    def __init__(self, folder: str, model: str = "olmocr") -> None:
        self.folder = folder
        self.name = model
        self._index: dict[str, str] = {}
        if not os.path.isdir(folder):
            raise FileNotFoundError(f"vision readings folder not found: {folder}")
        for root, _dirs, files in os.walk(folder):
            for name in files:
                if name.endswith(".md"):
                    self._index.setdefault(name, os.path.join(root, name))

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
        return None
