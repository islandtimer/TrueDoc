"""RapidOCR (PaddleOCR models on ONNX Runtime, Apache-2.0) as the CPU OCR engine.

The OCR result is turned into the same Char/Word/Line evidence the text-layer
path produces, so everything downstream (blocks, reading order, tables,
classification) works unchanged. Character boxes are approximated by dividing
each recognised line evenly, which is good enough for word and line geometry.
"""

from __future__ import annotations

import os
import re
import threading
from typing import Optional

import numpy as np
import pymupdf

from truedoc.model import BBox, Char, Line, Page, Word

_MAX_SIDE = 2000  # pixels on the long side; old scans are stored at huge page sizes
_MIN_SCORE = 0.5

_engine = None
_lock = threading.Lock()

# The bundled recognition model is Chinese+English and tends to drop the spaces
# between English words; the English PP-OCRv3 model (same Apache-2.0 model zoo)
# keeps them. It is fetched once into models/ (git-ignored).
_EN_REC_REPO = "SWHL/RapidOCR"
_EN_REC_FILE = "PP-OCRv3/en_PP-OCRv3_rec_infer.onnx"
_MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "models", "rapidocr")


def english_rec_model_path() -> Optional[str]:
    """Path to the English recognition model, downloading it on first use. None if unavailable."""
    if os.environ.get("TRUEDOC_OCR_LANG", "en").lower() != "en":
        return None
    local = os.path.join(_MODELS_DIR, _EN_REC_FILE.replace("/", os.sep))
    if os.path.exists(local):
        return local
    try:
        from huggingface_hub import hf_hub_download

        return hf_hub_download(_EN_REC_REPO, _EN_REC_FILE, local_dir=_MODELS_DIR)
    except Exception:
        return None


def _limit_onnx_threads() -> None:
    """Cap ONNX Runtime's per-session threads (RapidOCR does not expose the setting).

    With several worker processes, each session otherwise grabs every core and
    they thrash; TRUEDOC_OCR_THREADS (default 4) sets the intra-op pool size.
    """
    try:
        import onnxruntime as ort

        n = int(os.environ.get("TRUEDOC_OCR_THREADS", "4"))
        if getattr(ort.SessionOptions, "_truedoc_patched", False):
            return
        base = ort.SessionOptions

        class _Options(base):  # type: ignore[misc,valid-type]
            _truedoc_patched = True

            def __init__(self):
                super().__init__()
                self.intra_op_num_threads = n
                self.inter_op_num_threads = 1

        ort.SessionOptions = _Options
    except Exception:
        pass


def _get_engine():
    global _engine
    if _engine is None:
        with _lock:
            if _engine is None:
                _limit_onnx_threads()
                from rapidocr_onnxruntime import RapidOCR

                rec = english_rec_model_path()
                _engine = RapidOCR(rec_model_path=rec) if rec else RapidOCR()
    return _engine


def ocr_page(pdf_page: "pymupdf.Page") -> tuple[list[Line], float]:
    """Run OCR on a page. Returns (lines in PDF points, mean confidence)."""
    rect = pdf_page.rect
    long_side = max(rect.width, rect.height)
    scale = min(300.0 / 72.0, _MAX_SIDE / max(1.0, long_side))
    pix = pdf_page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), colorspace=pymupdf.csRGB, alpha=False)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
    result, _ = _get_engine()(img)
    lines: list[Line] = []
    scores: list[float] = []
    for item in result or []:
        box, text, score = item
        score = float(score)
        text = str(text).strip()
        if not text or score < _MIN_SCORE:
            continue
        xs = [p[0] / scale for p in box]
        ys = [p[1] / scale for p in box]
        bbox = BBox(min(xs), min(ys), max(xs), max(ys))
        words = _split_words(text, bbox, score)
        if not words:
            continue
        lines.append(Line(words=words, bbox=bbox, rotated=bbox.height > 2.5 * bbox.width and len(text) > 3))
        scores.append(score)
    conf = sum(scores) / len(scores) if scores else 0.0
    return lines, conf


_NUMBERISH = re.compile(r"[-+±]?[\d.,]+%?|[\d.,]+[-–][\d.,]+|\d+(st|nd|rd|th)")


def ocr_region(pdf_page: "pymupdf.Page", bbox: BBox) -> tuple[list[Line], float, float]:
    """Run OCR on one area of a page (a table drawn as a picture on an otherwise
    digital page). Returns (lines in page points, mean confidence, word-like share).

    `bbox` is in the rendered (rotated) page space; the clip is mapped back to
    MuPDF's unrotated space and the results mapped forward again.
    """
    M = pdf_page.rotation_matrix if pdf_page.rotation else None
    clip = pymupdf.Rect(bbox.x0, bbox.y0, bbox.x1, bbox.y1)
    if M is not None:
        clip = clip * ~M
    if clip.is_empty or clip.width < 20 or clip.height < 10:
        return [], 0.0, 0.0
    long_side = max(clip.width, clip.height)
    scale = min(300.0 / 72.0, _MAX_SIDE / max(1.0, long_side))
    pix = pdf_page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), clip=clip, colorspace=pymupdf.csRGB, alpha=False)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
    result, _ = _get_engine()(img)
    lines: list[Line] = []
    scores: list[float] = []
    for item in result or []:
        box, text, score = item
        score = float(score)
        text = str(text).strip()
        if not text or score < _MIN_SCORE:
            continue
        xs = [clip.x0 + p[0] / scale for p in box]
        ys = [clip.y0 + p[1] / scale for p in box]
        rect = pymupdf.Rect(min(xs), min(ys), max(xs), max(ys))
        if M is not None:
            rect = rect * M
        line_box = BBox(float(rect.x0), float(rect.y0), float(rect.x1), float(rect.y1))
        words = _split_words(text, line_box, score)
        if not words:
            continue
        lines.append(Line(words=words, bbox=line_box, rotated=line_box.height > 2.5 * line_box.width and len(text) > 3))
        scores.append(score)
    conf = sum(scores) / len(scores) if scores else 0.0
    return lines, conf, (_looks_like_text(lines) if lines else 0.0)


def _split_words(text: str, bbox: BBox, score: float) -> list[Word]:
    tokens = text.split()
    if not tokens:
        return []
    n_chars = sum(len(t) for t in tokens) + max(0, len(tokens) - 1)
    cw = bbox.width / max(1, n_chars)
    size = bbox.height * 0.8
    words: list[Word] = []
    pos = 0
    for tok in tokens:
        chars: list[Char] = []
        for ch in tok:
            x0 = bbox.x0 + pos * cw
            chars.append(Char(text=ch, bbox=BBox(x0, bbox.y0, x0 + cw, bbox.y1), font="OCR", size=size, origin_y=bbox.y1))
            pos += 1
        pos += 1  # the space
        words.append(Word(text=tok, bbox=BBox.union_all(c.bbox for c in chars), chars=chars))
    return words


_MIN_PAGE_CONFIDENCE = 0.75
_MIN_WORDLIKE = 0.5


_WORDS: Optional[set] = None


def _common_words() -> set:
    """About 10,000 common English words (public list, MIT licence), loaded once."""
    global _WORDS
    if _WORDS is None:
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "en_common_words.txt")
        try:
            with open(path, encoding="utf-8") as fh:
                _WORDS = {ln.strip().lower() for ln in fh if ln.strip()}
        except OSError:
            _WORDS = set()
    return _WORDS


def _looks_like_text(lines: list[Line]) -> float:
    """Share of tokens that are real words or numbers (OCR noise scores low).

    A token counts when it is a number, a one- or two-letter token, or a word
    from the common-English list. Names and rare words are not in the list, so
    real text typically scores 0.6-0.9 while handwriting noise scores under 0.3.
    """
    tokens = [w.text for l in lines for w in l.words]
    if not tokens:
        return 0.0
    words = _common_words()
    good = 0
    for t in tokens:
        core = t.strip(".,;:!?()[]\"'-")
        if not core:
            continue
        low = core.lower()
        if core.isdigit() or (core.isalpha() and len(core) <= 2):
            good += 1
        elif low in words or low.rstrip("s") in words or low.rstrip("d") in words:
            good += 1
        elif not words and core.isalpha() and _vowel_ratio(core) >= 0.2:
            good += 1
    return good / len(tokens)


def _vowel_ratio(word: str) -> float:
    w = word.lower()
    return sum(1 for ch in w if ch in "aeiouyáéíóúàèìòùäöüâêîôûãõñç") / max(1, len(w))


def _looks_like_language(lines: list[Line]) -> float:
    """Share of tokens shaped like words in any Latin-script language: numbers,
    short tokens, or letter runs with a plausible vowel share. The English word
    list behind `_looks_like_text` scores a Spanish or French page as noise; the
    engine's confident read of "MIEMBRO DE LA ASOCIACION" is text all the same."""
    tokens = [w.text for l in lines for w in l.words]
    if not tokens:
        return 0.0
    good = 0
    for t in tokens:
        core = t.strip(".,;:!?()[]\"'-")
        if not core:
            continue
        if core.isdigit() or (core.isalpha() and len(core) <= 2):
            good += 1
        elif core.isalpha() and 0.2 <= _vowel_ratio(core) <= 0.8:
            good += 1
    return good / len(tokens)


def apply_ocr(page: Page, pdf_page: "pymupdf.Page") -> bool:
    """Replace the page's (missing) text evidence with OCR output. Returns True if text was found.

    Handwriting and very poor scans produce confident-looking noise from a
    classical OCR engine; a page is only accepted when the engine is confident
    and most tokens look like words. Otherwise the page is left empty rather
    than filled with invented text.
    """
    lines, conf = ocr_page(pdf_page)
    if not lines:
        return False
    wordlike = _looks_like_text(lines)
    page.meta["ocr_confidence"] = conf
    page.meta["ocr_wordlike"] = wordlike
    # A scanned table is mostly numbers, which no word list knows; a confident
    # read with a large numeric share is accepted on that evidence.
    tokens = [w.text for l in lines for w in l.words]
    numeric_share = sum(1 for t in tokens if _NUMBERISH.fullmatch(t)) / max(1, len(tokens))
    page.meta["ocr_numeric_share"] = round(numeric_share, 2)
    # A confident read whose tokens are shaped like words of some Latin-script
    # language (a Spanish or French scan) is text too, whatever the English
    # word list says: 89 benchmark pages came out empty for this (5 Sept).
    language_like = _looks_like_language(lines)
    page.meta["ocr_languagelike"] = round(language_like, 2)
    rescued = conf >= 0.85 and (numeric_share >= 0.3 or language_like >= 0.7)
    if conf < _MIN_PAGE_CONFIDENCE or (wordlike < _MIN_WORDLIKE and not rescued):
        page.meta["ocr_rejected"] = True
        return False
    page.lines = lines
    page.words = [w for l in lines for w in l.words]
    page.chars = [c for w in page.words for c in w.chars]
    page.quality.kind = "ocr-truedoc"
    page.quality.n_chars = sum(len(w.text) for w in page.words)
    page.quality.n_alnum = sum(1 for c in page.chars if c.text.isalnum())
    page.meta["ocr_confidence"] = conf
    sizes: dict[float, int] = {}
    for w in page.words:
        s = round(w.size)
        sizes[s] = sizes.get(s, 0) + len(w.text)
    page.body_font_size = max(sizes.items(), key=lambda kv: kv[1])[0] if sizes else 10.0
    return True
