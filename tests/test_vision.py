"""The optional vision stage (D014) and its "inferred" marks (D015).

A fake model endpoint answers like olmOCR 2; the tests check that only pages
without text are sent to it, that its reading is marked, and that failures
never break a conversion.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pymupdf
import yaml

from truedoc.pipeline import ConvertOptions, convert
from truedoc.vision.olmocr_endpoint import parse_response

ANSWER = "---\nprimary_language: en\nis_rotation_valid: True\nrotation_correction: 0\nis_table: False\nis_diagram: False\n---\nHello from the model. The scan says the meeting is on Tuesday.\n"


class _Fake(BaseHTTPRequestHandler):
    calls: list[dict] = []
    answer: str = ANSWER
    picture_answer: str = "none"   # what a picture holds when asked to transcribe it

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length) or b"{}")
        prompt = " ".join(p.get("text", "") for m in body.get("messages", []) for p in m.get("content", []) if isinstance(p, dict))
        kind = "icon" if "icon or symbol" in prompt else ("figure" if "figure taken from a document" in prompt else ("picture-text" if "picture cut out of a document" in prompt else "page"))
        _Fake.calls.append({"path": self.path, "model": body.get("model"), "has_image": "image_url" in json.dumps(body), "kind": kind})
        answer = {"icon": "Covered", "figure": "A bar chart of premiums by year, rising from 100 to 140.", "picture-text": _Fake.picture_answer, "page": _Fake.answer}[kind]
        payload = json.dumps({"choices": [{"message": {"content": answer}}]}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):  # keep the test output quiet
        pass


def _serve():
    server = HTTPServer(("127.0.0.1", 0), _Fake)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://127.0.0.1:{server.server_port}"


def _pdf(tmp_path, with_text: bool, image: bool = True, running_head: str | None = None):
    doc = pymupdf.open()
    page = doc.new_page(width=400, height=300)
    if image:
        pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 40, 30), 0)
        pix.clear_with(200)
        page.insert_image(page.rect, pixmap=pix)  # a scan: an image, with or without a text layer over it
    if running_head:
        page.insert_text((40, 20), running_head, fontsize=9)   # inside the head strip (12% of 300 pt)
    if with_text:
        page.insert_text((40, 60), "Ordinary text that the PDF carries itself, enough to be usable on its own here.", fontsize=11)
    path = tmp_path / ("text.pdf" if with_text else "scan.pdf")
    doc.save(str(path))
    doc.close()
    return str(path)


def _split(md):
    _, fm, body = md.split("---\n", 2)
    return yaml.safe_load(fm), body


def test_unreadable_page_is_read_by_the_model_and_marked(tmp_path):
    server, url = _serve()
    _Fake.calls.clear()
    try:
        md = convert(_pdf(tmp_path, with_text=False), ConvertOptions(layout=False, ocr=False, vision_endpoint=url, vision_model="olmocr-test"))
    finally:
        server.shutdown()
    fm, body = _split(md)
    assert "Hello from the model" in body
    assert "read from its image by a model (olmocr-test)" in body
    assert "[^inferred]" in body and "[^inferred]: Marked text" in body
    assert fm["truedoc"]["pages_with_model"] == [1]
    assert fm["truedoc"]["inferred"] == [{"page": 1, "kind": "page", "model": "olmocr-test"}]
    assert len(_Fake.calls) == 1 and _Fake.calls[0]["path"].endswith("/v1/chat/completions") and _Fake.calls[0]["has_image"]
    assert _Fake.calls[0]["model"] == "olmocr-test"


def test_digital_page_is_never_sent(tmp_path):
    # The author's own text is exact; no model re-reads it (D014, D019).
    server, url = _serve()
    _Fake.calls.clear()
    try:
        md = convert(_pdf(tmp_path, with_text=True, image=False), ConvertOptions(layout=False, ocr=False, vision_endpoint=url))
    finally:
        server.shutdown()
    assert "Ordinary text that the PDF carries" in md
    assert "Hello from the model" not in md and "[^inferred]" not in md
    assert _Fake.calls == []


def test_text_over_a_scan_is_read_by_the_model_and_its_running_head_witnessed(tmp_path):
    # D019: text drawn over a full-page image is a hidden OCR layer, another machine's guess,
    # so the model reads the page; the layer's own line in the head strip witnesses the running
    # head the model transcribed, which is dropped and recorded.
    server, url = _serve()
    _Fake.calls.clear()
    _Fake.answer = ANSWER.replace("Hello from the model", "JOURNAL OF EXAMPLES 1921\n\nHello from the model", 1)
    try:
        md = convert(_pdf(tmp_path, with_text=True, running_head="JOURNAL OF EXAMPLES 1921"), ConvertOptions(layout=False, ocr=False, vision_endpoint=url))
    finally:
        _Fake.answer = ANSWER
        server.shutdown()
    assert len(_Fake.calls) == 1
    assert "Hello from the model" in md and "[^inferred]" in md
    assert "Ordinary text that the PDF carries" not in md
    assert "JOURNAL OF EXAMPLES 1921" not in md
    assert "OCR layer" in md


def test_endpoint_failure_leaves_the_page_empty_with_a_warning(tmp_path):
    md = convert(_pdf(tmp_path, with_text=False), ConvertOptions(layout=False, ocr=False, vision_endpoint="http://127.0.0.1:9"))
    # Nothing readable, nothing invented: an empty body, as without the vision stage.
    assert "Hello from the model" not in md


def test_parse_response_splits_front_matter():
    meta, text = parse_response(ANSWER)
    assert meta["primary_language"] == "en" and meta["is_table"] == "False"
    assert text.startswith("Hello from the model")
    meta2, text2 = parse_response("Plain answer without front matter")
    assert meta2 == {} and text2 == "Plain answer without front matter"


def _figure_pdf(tmp_path):
    """A text page with a chart-sized image below the paragraph."""
    doc = pymupdf.open()
    page = doc.new_page(width=400, height=500)
    page.insert_text((40, 60), "Premiums have risen every year since 2019, as the chart below shows.", fontsize=11)
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 60, 40), 0)
    pix.clear_with(90)
    page.insert_image(pymupdf.Rect(60, 120, 340, 320), pixmap=pix)
    page.insert_text((40, 380), "Source: annual reports of the insurer, adjusted for inflation.", fontsize=9)
    path = tmp_path / "chart.pdf"
    doc.save(str(path))
    doc.close()
    return str(path)


def test_figure_is_described_and_tagged(tmp_path):
    server, url = _serve()
    _Fake.calls.clear()
    try:
        md = convert(_figure_pdf(tmp_path), ConvertOptions(layout=False, ocr=False, vision_endpoint=url, vision_model="olmocr-test"))
    finally:
        server.shutdown()
    fm, body = _split(md)
    assert "![A bar chart of premiums by year, rising from 100 to 140.](figure)[^inferred]" in body, body
    assert "[^inferred]: Marked text" in body
    assert "Premiums have risen every year" in body
    assert [c["kind"] for c in _Fake.calls] == ["picture-text", "figure"]   # a picture with no words inside is first asked whether it holds text (D019)
    entry = fm["truedoc"]["inferred"][0]
    assert entry["kind"] == "figure" and entry["page"] == 1 and entry["model"] == "olmocr-test" and entry["text"].startswith("A bar chart")


def test_pages_only_leaves_figures_alone(tmp_path):
    server, url = _serve()
    _Fake.calls.clear()
    try:
        md = convert(_figure_pdf(tmp_path), ConvertOptions(layout=False, ocr=False, vision_endpoint=url, vision_regions=False))
    finally:
        server.shutdown()
    assert "![](figure)" in md and "[^inferred]" not in md
    assert _Fake.calls == []


def _icon_table_pdf(tmp_path):
    """A ruled table whose third column holds pictograms instead of words."""
    doc = pymupdf.open()
    page = doc.new_page(width=400, height=300)
    page.insert_text((40, 40), "What is covered", fontsize=12)
    xs = [40, 200, 300, 370]
    ys = [60, 105, 150, 195]
    for y in ys:
        page.draw_line((xs[0], y), (xs[-1], y), width=0.8)
    for x in xs:
        page.draw_line((x, ys[0]), (x, ys[-1]), width=0.8)
    rows = [("Event", "Limit", ""), ("Storm damage", "$20,000", None), ("Flood", "$5,000", None)]
    for r, (a, b, _) in enumerate(rows):
        page.insert_text((xs[0] + 6, ys[r] + 26), a, fontsize=10)
        page.insert_text((xs[1] + 6, ys[r] + 26), b, fontsize=10)
    page.insert_text((xs[2] + 6, ys[0] + 26), "Cover", fontsize=10)
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 24, 24), 0)
    pix.clear_with(30)
    for r in (1, 2):  # a 36-pt pictogram in the third column: too big for a bullet, an icon to read
        page.insert_image(pymupdf.Rect(xs[2] + 16, ys[r] + 4, xs[2] + 52, ys[r] + 40), pixmap=pix)
    path = tmp_path / "icons.pdf"
    doc.save(str(path))
    doc.close()
    return str(path)


def test_icon_in_a_table_cell_gets_its_meaning(tmp_path):
    server, url = _serve()
    _Fake.calls.clear()
    try:
        md = convert(_icon_table_pdf(tmp_path), ConvertOptions(layout=False, ocr=False, vision_endpoint=url))
    finally:
        server.shutdown()
    fm, body = _split(md)
    assert body.count("Covered[^inferred]") == 2, body
    assert "Storm damage" in body and "$20,000" in body
    kinds = [c["kind"] for c in _Fake.calls]
    assert kinds.count("icon") == 2 and "page" not in kinds
    assert [e["kind"] for e in fm["truedoc"]["inferred"]] == ["icon", "icon"]


class _FakeAnthropic(BaseHTTPRequestHandler):
    calls: list[dict] = []

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length) or b"{}")
        blocks = body["messages"][0]["content"]
        _FakeAnthropic.calls.append({
            "key": self.headers.get("x-api-key"),
            "version": self.headers.get("anthropic-version"),
            "model": body.get("model"),
            "types": [b.get("type") for b in blocks],
            "media": next((b["source"]["media_type"] for b in blocks if b.get("type") == "image"), None),
        })
        payload = json.dumps({"content": [{"type": "text", "text": "Not covered"}]}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass


def test_anthropic_provider_sends_the_messages_api_shape(tmp_path):
    from truedoc.vision.anthropic_api import AnthropicVision

    server = HTTPServer(("127.0.0.1", 0), _FakeAnthropic)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    _FakeAnthropic.calls.clear()
    try:
        provider = AnthropicVision(model="claude-test", api_key="test-key", api_url=f"http://127.0.0.1:{server.server_port}/v1/messages")
        answer = provider.read_region(_icon_table_pdf(tmp_path), 1, (320.0, 95.0, 340.0, 115.0), "icon")
    finally:
        server.shutdown()
    assert answer == "Not covered"
    call = _FakeAnthropic.calls[0]
    assert call["key"] == "test-key" and call["version"] and call["model"] == "claude-test"
    assert call["types"] == ["image", "text"] and call["media"] == "image/png"


def test_anthropic_provider_without_a_key_is_a_warning_not_a_crash(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    md = convert(_figure_pdf(tmp_path), ConvertOptions(layout=False, ocr=False, vision_endpoint="anthropic"))
    fm, body = _split(md)
    assert "Premiums have risen" in body and "[^inferred]" not in body
    assert any("ANTHROPIC_API_KEY" in w for w in fm["truedoc"]["warnings"])


def test_clean_answer_rules():
    from truedoc.vision.regions import clean_answer

    assert clean_answer("Covered.", "icon") == "Covered"
    assert clean_answer("decorative", "icon") is None
    assert clean_answer("```\nOptional extra\n```", "icon") == "Optional extra"
    assert clean_answer("This icon means: Not covered", "icon") == "Not covered"
    assert clean_answer("one two three four five six seven eight nine", "icon") is None
    assert clean_answer("---\nis_diagram: True\n---\nA line chart of claims per month.", "figure") == "A line chart of claims per month."
    assert clean_answer("Decorative picture of a house.", "figure") is None


def test_picture_holding_a_table_is_transcribed_as_the_figure_content(tmp_path):
    # D019 on a region: a pay-advice screenshot pasted into a help page holds a table the page's
    # own text does not; the model transcribes the picture and the transcription follows the
    # placeholder with the inferred tag, while the page's own words stay exact.
    doc = pymupdf.open()
    page = doc.new_page(width=400, height=600)
    page.insert_text((40, 60), "To begin, subtract the balances shown below from your pay advice figures here.", fontsize=11)
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 60, 30), 0)
    pix.clear_with(180)
    page.insert_image(pymupdf.Rect(40, 100, 360, 260), pixmap=pix)   # a picture, a fifth of the page, no words inside
    path = tmp_path / "advice.pdf"
    doc.save(str(path))
    doc.close()
    server, url = _serve()
    _Fake.calls.clear()
    _Fake.picture_answer = "| YEAR-TO-DATE | PAID TIME OFF | SICK LEAVE |\n|---|---|---|\n| Start Balance | 0.0 | 0.0 |\n| + Earned | 1,393.5 | 949.9 |"
    try:
        md = convert(str(path), ConvertOptions(layout=False, ocr=False, vision_endpoint=url))
    finally:
        _Fake.picture_answer = "none"
        server.shutdown()
    assert "subtract the balances" in md
    assert "| + Earned | 1,393.5 | 949.9 |" in md and "![](figure)" in md and "[^inferred]" in md
    assert [c["kind"] for c in _Fake.calls] == ["picture-text"]
    fm, _ = _split(md)
    assert fm["truedoc"]["inferred"][0]["kind"] == "picture-text"
