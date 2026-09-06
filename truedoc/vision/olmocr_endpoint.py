"""Read a page through an olmOCR 2 model served behind an OpenAI-style chat endpoint.

olmOCR 2 is trained on exactly this request: one page image and a fixed prompt
(`build_no_anchoring_v4_yaml_prompt`), answered with a small YAML front matter
(language, rotation, is_table, is_diagram) followed by the page's text. vLLM
serves the model at `<endpoint>/v1/chat/completions`; that is what the rented
GPU ran on 3 September 2026, only driven here page by page instead of through
olmOCR's own batch pipeline.

The page is rendered with PyMuPDF (longest side 1288 pixels, olmOCR's default)
so no poppler installation is needed on the caller's machine.
"""

from __future__ import annotations

import base64
import json
import logging
import urllib.error
import urllib.request

import pymupdf

log = logging.getLogger("truedoc")

_MAX_TOKENS = 8000


def _prompt() -> str:
    try:
        from olmocr.prompts.prompts import build_no_anchoring_v4_yaml_prompt

        return build_no_anchoring_v4_yaml_prompt()
    except Exception:  # olmocr not installed: the prompt text olmOCR 2 was trained with
        return (
            "Attached is one page of a document that you must process. Just return the plain text representation of this document as if you were reading it naturally. "
            "Convert equations to LateX and tables to markdown.\n"
            "Return your output as markdown, with a front matter section on top specifying values for the primary_language, is_rotation_valid, rotation_correction, "
            "is_table, and is_diagram parameters."
        )


def render_page_png_base64(pdf_path: str, page_number: int, longest_dim: int = 1288) -> str:
    """The page as a PNG, longest side `longest_dim` pixels, base64-encoded."""
    doc = pymupdf.open(pdf_path)
    try:
        page = doc[page_number - 1]
        rect = page.rect
        zoom = longest_dim / max(rect.width, rect.height, 1.0)
        pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
        return base64.b64encode(pix.tobytes("png")).decode("ascii")
    finally:
        doc.close()


def parse_response(content: str) -> tuple[dict, str]:
    """Split olmOCR's answer into its front matter (as a dict) and the page text."""
    meta: dict = {}
    text = content
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) == 3:
            for line in parts[1].splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip()
            text = parts[2]
    return meta, text.strip("\n")


class OlmocrEndpoint:
    name = "olmocr"

    def __init__(self, endpoint: str, model: str = "olmocr", timeout: float = 240.0, longest_dim: int = 1288):
        base = endpoint.rstrip("/")
        if base.endswith("/chat/completions"):
            self.url = base
        elif base.endswith("/v1"):
            self.url = base + "/chat/completions"
        else:
            self.url = base + "/v1/chat/completions"
        self.model = model
        self.timeout = timeout
        self.longest_dim = longest_dim
        self.name = model or "olmocr"

    def _query(self, image_b64: str, prompt: str | None = None, max_tokens: int = _MAX_TOKENS) -> dict:
        return {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt if prompt is not None else _prompt()},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
                    ],
                }
            ],
            "max_tokens": max_tokens,
            "temperature": 0.0,
        }

    def _chat(self, image_b64: str, prompt: str | None, max_tokens: int, what: str) -> str | None:
        body = json.dumps(self._query(image_b64, prompt, max_tokens)).encode("utf-8")
        req = urllib.request.Request(self.url, data=body, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                payload = json.load(resp)
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            log.warning("vision: endpoint %s failed for %s: %s", self.url, what, exc)
            return None
        try:
            return payload["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError):
            log.warning("vision: unexpected answer shape from %s", self.url)
            return None

    def read_page(self, pdf_path: str, page_number: int) -> str | None:
        try:
            image_b64 = render_page_png_base64(pdf_path, page_number, self.longest_dim)
        except Exception as exc:
            log.warning("vision: could not render page %s of %s: %s", page_number, pdf_path, exc)
            return None
        content = self._chat(image_b64, None, _MAX_TOKENS, f"page {page_number}")
        if content is None:
            return None
        meta, text = parse_response(content)
        if not text.strip():
            return None
        return text

    def read_region(self, pdf_path: str, page_number: int, bbox: tuple[float, float, float, float], kind: str) -> str | None:
        """An icon's meaning or a figure's description (D015 items 1 and 4)."""
        from truedoc.vision.regions import MAX_TOKENS, clean_answer, region_prompt, render_region_png_base64

        try:
            image_b64 = render_region_png_base64(pdf_path, page_number, bbox, kind)
        except Exception as exc:
            log.warning("vision: could not render a %s on page %s of %s: %s", kind, page_number, pdf_path, exc)
            return None
        content = self._chat(image_b64, region_prompt(kind), MAX_TOKENS.get(kind, 200), f"a {kind} on page {page_number}")
        return clean_answer(content, kind)
