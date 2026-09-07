"""A model reading far shorter than the page's own text is partial: the page's own text stays.

Run 55 (7 September 2026) showed a table page the model reduced to 59 words from the 228 its
layer holds, and a dictionary page cut to 906 words from 1,660. Nothing invented and nothing
lost silently (D008): when the model returns less than two thirds of a substantial reading the
page already has, the page keeps its own text, the front matter carries a warning, and no
inferred note is written. A full reading replaces the page as D019 says.
"""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

import pymupdf

from truedoc.pipeline import ConvertOptions, convert

LONG = " ".join("word%d" % i for i in range(160))


class _Short(BaseHTTPRequestHandler):
    answer = "---\nprimary_language: en\n---\nOnly a few words came back."

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        self.rfile.read(length)
        payload = json.dumps({"choices": [{"message": {"content": _Short.answer}}]}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *a):  # noqa: D102
        pass


def _serve():
    server = HTTPServer(("127.0.0.1", 0), _Short)
    Thread(target=server.serve_forever, daemon=True).start()
    return server, "http://127.0.0.1:%d" % server.server_address[1]


def _pdf(tmp_path):
    doc = pymupdf.open()
    page = doc.new_page(width=400, height=600)
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 40, 60), 0)
    pix.clear_with(200)
    page.insert_image(page.rect, pixmap=pix)          # a scan with an invisible text layer over it
    words = LONG.split()
    for i in range(0, len(words), 8):
        page.insert_text((20, 40 + 3 * i), " ".join(words[i:i + 8]), fontsize=8, render_mode=3)   # invisible: a hidden OCR layer
    path = tmp_path / "layer.pdf"
    doc.save(str(path))
    doc.close()
    return str(path)


def test_short_model_reading_keeps_the_page_text(tmp_path):
    server, url = _serve()
    _Short.answer = "---\nprimary_language: en\n---\nOnly a few words came back."
    try:
        md = convert(_pdf(tmp_path), ConvertOptions(layout=False, ocr=False, vision_endpoint=url, vision_regions=False))
    finally:
        server.shutdown()
    assert "word37" in md and "Only a few words" not in md
    assert "read from its image by a model" not in md
    assert "reading was partial" in md          # the warning in the front matter


def test_full_model_reading_replaces_the_page(tmp_path):
    server, url = _serve()
    _Short.answer = "---\nprimary_language: en\n---\n" + " ".join("model%d" % i for i in range(150))
    try:
        md = convert(_pdf(tmp_path), ConvertOptions(layout=False, ocr=False, vision_endpoint=url, vision_regions=False))
    finally:
        server.shutdown()
    assert "model37" in md and "word37" not in md
    assert "read from its image by a model" in md
