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

# olmOCR 2 is asked for a page at 1288 px on its longest side, which is the size it was trained at.
# A general model has no such training size; the API scales anything larger than about 1568 px down
# to it, so that is the useful maximum. Measured 12 September on the 98 old-scan pages: reading them
# larger is part of why a frontier model read the handwriting better than olmOCR did.
_PAGE_LONGEST_DIM = 1568

# What to leave out. olmOCR 2 was trained to drop a page's furniture and says nothing about it in its
# prompt; a general model transcribes whatever it sees unless told, and on the benchmark's old scans
# that cost 35 of 68 "this text must not appear" checks - dockets, catalogue numbers, letterhead and
# running heads, not one of them a misreading. Adding this paragraph recovered every one of them and
# changed nothing else (12 September).
_OMIT = (
    " Transcribe the document, not the page's furniture: leave out running heads and feet, page and"
    " folio numbers, printed letterhead and cable addresses, and anything a later hand added to file"
    " or catalogue the document (a docket date written sideways, a clerk's acknowledgement, an"
    " archivist's note, a form number, a collection number). The document's own dateline, salutation,"
    " signature and address panel are part of it and stay."
)

# What a specialist reader does by training and a general one has to be told. Measured over the
# benchmark's 98 old-scan pages (12 September): adding this paragraph took one Sonnet call from 267 of
# 517 checks to 273, where moving up to Opus and paying several times as much bought 271. A paragraph
# beat a bigger model.
_FAITHFUL = (
    " Write exactly what the document says: keep the writer's spelling, including mistakes, their"
    " capitalisation, including mid-sentence capitals, and their punctuation, including the dashes and"
    " ampersands they wrote. Do not correct grammar, modernise spelling, expand abbreviations or tidy"
    " anything. Where a word is illegible, write your best single reading of it rather than a"
    " placeholder, and do not add anything that is not on the page."
)


# olmOCR's prompt ends by asking for a front matter block of five parameters. olmOCR 2 answers with
# "---" front matter, which `parse_response` strips; a general model answers with a fenced yaml block
# instead, which nothing strips, so five lines of metadata land in the reader's document (seen on the
# first API page, 12 September). Nothing reads those fields - `read_page` throws the parsed metadata
# away - so a general model is not asked for them.
_FRONT_MATTER_ASK = ", with a front matter section on top specifying values for the primary_language, is_rotation_valid, rotation_correction, is_table, and is_diagram parameters."


def page_prompt() -> str:
    """The page question for a general model: olmOCR's, without the front matter, plus what to omit."""
    from truedoc.vision.olmocr_endpoint import _prompt

    base = _prompt()
    if base.endswith(_FRONT_MATTER_ASK):
        base = base[: -len(_FRONT_MATTER_ASK)] + "."
    return base + _OMIT + _FAITHFUL


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
        from truedoc.vision.olmocr_endpoint import parse_response, render_page_png_base64

        try:
            image_b64 = render_page_png_base64(pdf_path, page_number, longest_dim=_PAGE_LONGEST_DIM)
        except Exception as exc:
            log.warning("vision: could not render page %s of %s: %s", page_number, pdf_path, exc)
            return None
        answer = self._ask(page_prompt(), image_b64, _PAGE_MAX_TOKENS)
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
