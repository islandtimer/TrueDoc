"""The optional vision stage (decision D014).

A vision provider looks at an *image* and answers in text. TrueDoc calls it in
two situations, both behind the one `--vision-endpoint` switch and both marked
as inferred (D015): a whole page that has no usable text of its own (no text
layer, no confident OCR), and a region that carries meaning the mechanical
reading cannot extract (an icon in a table cell, a chart, a diagram).

Providers implement two methods:

    read_page(pdf_path, page_number) -> str | None
    read_region(pdf_path, page_number, bbox, kind) -> str | None

returning markdown for the page, or a short answer for the region ("Covered",
"A bar chart of premiums by year ..."), or None when there is nothing to write.
`kind` is "icon" or "figure"; `bbox` is (x0, y0, x1, y1) in page points.

Two providers exist: `OlmocrEndpoint`, an OpenAI-compatible chat endpoint
serving a vision model as vLLM does (olmOCR 2 for pages; any Qwen-VL-style
model answers region questions), chosen by giving its URL; and
`AnthropicVision`, the frontier-model "deep read", chosen with the endpoint
name `anthropic` (or `anthropic:<model>`) and the `ANTHROPIC_API_KEY`
environment variable, which the owner sets. A third, `FileReadings`, replays a
model's saved page readings from a folder (`file:<folder>`), so a run made once
on a rented GPU can go through the whole pipeline again without a served model.
"""

from __future__ import annotations

from typing import Protocol


class VisionProvider(Protocol):
    name: str

    def read_page(self, pdf_path: str, page_number: int) -> str | None: ...

    def read_region(self, pdf_path: str, page_number: int, bbox: tuple[float, float, float, float], kind: str, turn: int = 0) -> str | None: ...


def make_provider(endpoint: str, model: str = "olmocr") -> VisionProvider:
    """A provider for an endpoint address or name.

    `http://host:port` (any OpenAI-style chat endpoint) -> OlmocrEndpoint;
    `anthropic` or `anthropic:claude-sonnet-5` -> AnthropicVision.

    A frontier provider may be asked to read a page in overlapping slices rather than whole, at one
    call a slice, by adding `/bands=2` to the name (`anthropic/bands=2`,
    `anthropic:claude-sonnet-5/bands=3`). That is for a page an ordinary read struggles with; on a page
    it does not, the extra calls buy nothing.
    """
    spec = (endpoint or "").strip()
    bands = 1
    if "/bands=" in spec:
        spec, _, count = spec.partition("/bands=")
        try:
            bands = max(1, int(count.strip()))
        except ValueError:
            bands = 1
    if spec.lower().startswith("anthropic"):
        from truedoc.vision.anthropic_api import DEFAULT_MODEL, AnthropicVision

        _, _, named = spec.partition(":")
        chosen = named.strip() or (model if model and model != "olmocr" else DEFAULT_MODEL)
        return AnthropicVision(model=chosen, bands=bands)
    if spec.lower().startswith("file:"):
        from truedoc.vision.file_readings import FileReadings

        return FileReadings(spec[5:].strip(), model=model)
    from truedoc.vision.olmocr_endpoint import OlmocrEndpoint

    return OlmocrEndpoint(spec, model=model)
