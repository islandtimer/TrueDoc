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
    lines, conf, _ = ocr_page_turn(pdf_page, want_turn=False)
    return lines, conf


def ocr_page_turn(pdf_page: "pymupdf.Page", want_turn: bool = True) -> tuple[list[Line], float, int]:
    """Run OCR on a page. Returns (lines in PDF points, mean confidence, turn).

    `turn` is 0 when the page reads upright, else the rotation in degrees (90 or
    270, PyMuPDF's clockwise-positive convention) that would make it upright: a
    landscape scan of a portrait page, or a wide table printed sideways on a
    portrait page. The caller turns the page and reads it again (see
    `_sideways_turn`); a sideways read is not worth keeping, because every line
    of it would be filed as a rotated stamp.
    """
    rect = pdf_page.rect
    long_side = max(rect.width, rect.height)
    scale = min(300.0 / 72.0, _MAX_SIDE / max(1.0, long_side))
    pix = pdf_page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), colorspace=pymupdf.csRGB, alpha=False)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
    engine = _get_engine()
    result, _ = engine(img)
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
    turn = _sideways_turn(engine, img, result) if want_turn and lines and conf >= _TURN_MIN_CONFIDENCE else 0
    return lines, conf, turn


_TURN_MIN_CONFIDENCE = 0.6   # the sideways read must be a read, not noise, before a page is turned
_TURN_MIN_LINES = 3
_TURN_SHARE = 0.6            # share of the read characters that must sit in tall boxes


def _box_sides(box) -> tuple[float, float]:
    """Width and height of a detector quadrilateral, measured the way the engine does."""
    pts = np.asarray(box, dtype=np.float32)
    w = max(np.linalg.norm(pts[0] - pts[1]), np.linalg.norm(pts[2] - pts[3]))
    h = max(np.linalg.norm(pts[0] - pts[3]), np.linalg.norm(pts[1] - pts[2]))
    return float(w), float(h)


def _sideways_turn(engine, img: np.ndarray, result) -> int:
    """0 when a page reads upright; else the turn (90 or 270 degrees, clockwise
    positive) that makes it upright.

    On a page lying on its side most text boxes are taller than wide. Which way
    the text runs comes from the engine's own angle classifier: before reading
    a tall box the engine turns its crop a quarter turn anticlockwise, and the
    classifier then says whether that crop is upright ("0") or upside down
    ("180"). Upright means the text ran down the page, so the page turns
    anticlockwise (270); upside down means the text ran up the page, so the
    page turns clockwise (90). Verified on a landscape scan of a Spanish decree
    (tables/0684e33b..., 6 Sept): 62 of 74 boxes read "0", and the 270 turn
    reads the page in order, letterhead first.
    """
    tall = []
    n_tall = n_all = 0
    for box, text, score in result or []:
        text = str(text).strip()
        if len(text) < 3 or float(score) < _MIN_SCORE:
            continue
        w, h = _box_sides(box)
        n_all += len(text)
        if h >= 1.5 * w:   # the engine's own threshold for turning a crop
            tall.append(np.asarray(box, dtype=np.float32))
            n_tall += len(text)
    if len(tall) < _TURN_MIN_LINES or n_tall < _TURN_SHARE * max(1, n_all):
        return 0
    try:
        crops = engine.get_crop_img_list(img, tall)
        _, labels, _ = engine.text_cls(crops)
    except Exception:
        return 0
    up = sum(1 for label, score in labels if "180" in str(label) and float(score) > 0.9)
    down = sum(1 for label, score in labels if "180" not in str(label) and float(score) > 0.9)
    if up + down < _TURN_MIN_LINES:
        return 0
    return 90 if up > down else 270


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


# The engine reads "plant,and" or "Smith;Jones" as one token when the printed
# space after the mark is narrow: a comma, semicolon or colon followed directly
# by a word is a word break. A single letter after the mark is a symbol in a
# list ("A,B", "x,y") and stays; web and e-mail addresses keep their colons.
# Measured on run 48's outputs (7 Sept): 12 checks won, none lost (the single-
# letter guard keeps a table cell "A,B" that the bare rule lost).
_GLUED_PUNCT = re.compile(r"(?<=[,;:])(?=[A-Za-z]{2})")


def _punct_parts(tok: str) -> list[str]:
    if "://" in tok or "@" in tok or "www." in tok:
        return [tok]
    return [p for p in _GLUED_PUNCT.split(tok) if p]


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
        for part in _punct_parts(tok):
            chars: list[Char] = []
            for ch in part:
                x0 = bbox.x0 + pos * cw
                chars.append(Char(text=ch, bbox=BBox(x0, bbox.y0, x0 + cw, bbox.y1), font="OCR", size=size, origin_y=bbox.y1))
                pos += 1
            words.append(Word(text=part, bbox=BBox.union_all(c.bbox for c in chars), chars=chars))
        pos += 1  # the space
    return words


_MIN_PAGE_CONFIDENCE = 0.75
_MIN_WORDLIKE = 0.5
# The confidence a page must reach for the non-English and numeric rescues below.
# 0.85 until 6 Sept; lowered to 0.80 on the evidence of an OCR census of the 182
# image-only benchmark pages: in the 0.80-0.85 band 16 of 18 pages were already
# accepted as English-word-like text and the two rejected ones score under 0.65 on
# language-likeness, so they stay rejected; every handwriting page sits under 0.75.
# The change admits a turned Spanish decree (0.84) and a scanned financial table
# (0.82, numeric share 0.45), both real text.
_RESCUE_MIN_CONFIDENCE = 0.8
# A page that is mostly numbers (a scanned table of measurements) is accepted
# from the page floor up: no word list can vouch for numbers, and the engine's
# confidence on clean digits runs lower than on words. Census of 7 Sept over
# the 73 benchmark pages that came out empty: one page has a numeric share of
# 0.5 or more with a confidence above the floor (a wastewater table, 0.785,
# share 0.74, 248 lines); the other three such pages are a single line or read
# under 0.7, and every handwriting page stays under 0.75.
_NUMERIC_RESCUE_SHARE = 0.5
_NUMERIC_RESCUE_MIN_LINES = 20


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


def apply_ocr(page: Page, pdf_page: "pymupdf.Page", allow_turn: bool = True) -> bool:
    """Replace the page's (missing) text evidence with OCR output. Returns True if text was found.

    Handwriting and very poor scans produce confident-looking noise from a
    classical OCR engine; a page is only accepted when the engine is confident
    and most tokens look like words. Otherwise the page is left empty rather
    than filled with invented text.

    A page that lies on its side is not read here: `page.meta["ocr_turn"]` is
    set to the turn that makes it upright and False is returned, so the caller
    can turn the page (`pipeline._turn_page`) and call again with
    `allow_turn=False`.
    """
    lines, conf, turn = ocr_page_turn(pdf_page, want_turn=allow_turn)
    if turn:
        page.meta["ocr_turn"] = turn
        return False
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
    rescued = conf >= _RESCUE_MIN_CONFIDENCE and (numeric_share >= 0.3 or language_like >= 0.7)
    rescued = rescued or (numeric_share >= _NUMERIC_RESCUE_SHARE and len(lines) >= _NUMERIC_RESCUE_MIN_LINES)
    if conf < _MIN_PAGE_CONFIDENCE or (wordlike < _MIN_WORDLIKE and not rescued):
        page.meta["ocr_rejected"] = True
        # The rejected lines still witness the page's running heads for the vision stage (D019).
        page.meta["witness_lines"] = [(l.text, l.bbox.y0, l.bbox.y1) for l in lines[:400]]
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
