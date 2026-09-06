"""A frontier-model provider: Anthropic's Messages API (the product's "deep read").

The key is read from the `ANTHROPIC_API_KEY` environment variable, which the
owner sets; nothing in TrueDoc stores or prints it. The provider answers the
same two questions as the served open model: read a whole page (only pages
with no text of their own) and read a region (an icon or a figure). Everything
it returns is marked as inferred (D015).

The request is plain HTTP (no SDK to install): one image block and one text
block per message, `max_tokens` sized to the question.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request

from truedoc.vision.regions import MAX_TOKENS, clean_answer, region_prompt, render_region_png_base64

log = logging.getLogger("truedoc")

DEFAULT_MODEL = "claude-sonnet-5"
API_URL = "https://api.anthropic.com/v1/messages"
_PAGE_MAX_TOKENS = 8000


class AnthropicVision:
    def __init__(self, model: str = DEFAULT_MODEL, api_key: str | None = None, api_url: str = API_URL, timeout: float = 180.0):
        self.model = model or DEFAULT_MODEL
        self.name = self.model
        self.api_url = api_url
        self.timeout = timeout
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if not self.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set; the frontier-model vision stage needs it in the environment")

    def _ask(self, prompt: str, image_b64: str, max_tokens: int) -> str | None:
        body = json.dumps(
            {
                "model": self.model,
                "max_tokens": max_tokens,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": image_b64}},
                            {"type": "text", "text": prompt},
                        ],
                    }
                ],
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            self.api_url,
            data=body,
            headers={"Content-Type": "application/json", "x-api-key": self.api_key, "anthropic-version": "2023-06-01"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                payload = json.load(resp)
        except urllib.error.HTTPError as exc:
            log.warning("vision: the Anthropic API answered %s for model %s", exc.code, self.model)
            return None
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            log.warning("vision: the Anthropic API call failed: %s", exc)
            return None
        try:
            return "".join(part.get("text", "") for part in payload["content"] if part.get("type") == "text")
        except (KeyError, TypeError):
            log.warning("vision: unexpected answer shape from the Anthropic API")
            return None

    def read_page(self, pdf_path: str, page_number: int) -> str | None:
        from truedoc.vision.olmocr_endpoint import _prompt, parse_response, render_page_png_base64

        try:
            image_b64 = render_page_png_base64(pdf_path, page_number)
        except Exception as exc:
            log.warning("vision: could not render page %s of %s: %s", page_number, pdf_path, exc)
            return None
        answer = self._ask(_prompt(), image_b64, _PAGE_MAX_TOKENS)
        if not answer:
            return None
        _, text = parse_response(answer)
        return text if text.strip() else None

    def read_region(self, pdf_path: str, page_number: int, bbox: tuple[float, float, float, float], kind: str, turn: int = 0) -> str | None:
        try:
            image_b64 = render_region_png_base64(pdf_path, page_number, bbox, kind, turn=turn)
        except Exception as exc:
            log.warning("vision: could not render a %s on page %s of %s: %s", kind, page_number, pdf_path, exc)
            return None
        return clean_answer(self._ask(region_prompt(kind), image_b64, MAX_TOKENS.get(kind, 200)), kind)
