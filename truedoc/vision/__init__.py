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
environment variable, which the owner sets.
"""

from __future__ import annotations

from typing import Protocol


class VisionProvider(Protocol):
    name: str

    def read_page(self, pdf_path: str, page_number: int) -> str | None: ...

    def read_region(self, pdf_path: str, page_number: int, bbox: tuple[float, float, float, float], kind: str) -> str | None: ...


def make_provider(endpoint: str, model: str = "olmocr") -> VisionProvider:
    """A provider for an endpoint address or name.

    `http://host:port` (any OpenAI-style chat endpoint) -> OlmocrEndpoint;
    `anthropic` or `anthropic:claude-sonnet-5` -> AnthropicVision.
    """
    spec = (endpoint or "").strip()
    if spec.lower().startswith("anthropic"):
        from truedoc.vision.anthropic_api import DEFAULT_MODEL, AnthropicVision

        _, _, named = spec.partition(":")
        chosen = named.strip() or (model if model and model != "olmocr" else DEFAULT_MODEL)
        return AnthropicVision(model=chosen)
    from truedoc.vision.olmocr_endpoint import OlmocrEndpoint

    return OlmocrEndpoint(spec, model=model)
