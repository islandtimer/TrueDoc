"""An OCR that fails is tried again, and said out loud where it fails for good; its model is fetched once.

OCR is optional, so its failure never fails a conversion. It used to be silent as well: a warning in a log, and the
page then reported `unreadable-pages`, which reads as a verdict on the page when the reader had failed. On 24 September
six conversions started together on a fresh install lost OCR on the first page two of them read - in the half-minute the
English recognition model took to arrive, which each process fetched for itself. Now:
- a failed reading is tried once more with the engine started afresh (`pipeline._read_by_ocr`);
- a page that fails twice, and where something may be missing, is reported `ocr-failed` - not `unreadable-pages` -
  with what OCR met; the build record lists it, and the location map calls the page unreadable;
- the model is fetched by one process under a lock the others wait on (`ocr.rapid.english_rec_model_path`).
"""
import os
import threading
import time

import pymupdf

from truedoc.ocr import rapid
from truedoc.pipeline import ConvertOptions, convert_with_status

FAST = dict(frontmatter=False, layout=False, math=False, ocr=True)


def _circle(path):
    """A page with no text, holding a shape drawn with curves: where OCR did not look, it may hold words."""
    pdf = pymupdf.open()
    pdf.new_page().draw_circle((300, 400), 80)
    pdf.save(str(path))
    pdf.close()
    return str(path)


def _ocr_that(monkeypatch, outcomes):
    """Stand in for the OCR: each call takes the next outcome - an exception to raise, or "empty" for a reading that
    found nothing. The engine each call finds is recorded."""
    calls = []

    def fake(page, pdf_page, allow_turn=True):
        calls.append(rapid._engine)
        outcome = outcomes[min(len(calls), len(outcomes)) - 1]
        if isinstance(outcome, Exception):
            raise outcome
        page.meta["ocr_empty"] = True
        return False

    monkeypatch.setattr(rapid, "apply_ocr", fake)
    return calls


def test_a_reading_that_fails_once_is_tried_again_with_a_fresh_engine(tmp_path, monkeypatch):
    monkeypatch.setattr(rapid, "_engine", object())         # an engine already started, and at fault
    calls = _ocr_that(monkeypatch, [RuntimeError("model file cut short"), "empty"])
    result = convert_with_status(_circle(tmp_path / "once.pdf"), ConvertOptions(**FAST))
    assert len(calls) == 2 and calls[1] is None             # the second try starts its own engine
    assert result.completion == "complete"                  # OCR found nothing on it: a blank page, a note
    assert [i.code for i in result.issues] == ["blank-pages"]
    assert result.build["readers"]["ocr"]["retried"] == [{"page": 1, "error": "RuntimeError: model file cut short"}]
    assert "failed" not in result.build["readers"]["ocr"]


def test_a_page_whose_reading_fails_twice_says_so_and_is_not_called_unreadable(tmp_path, monkeypatch):
    calls = _ocr_that(monkeypatch, [RuntimeError("model file cut short")])
    result = convert_with_status(_circle(tmp_path / "twice.pdf"), ConvertOptions(location_map=True, **FAST))
    assert len(calls) == 2
    assert result.completion == "incomplete"
    assert [(i.code, i.severity, i.pages) for i in result.issues] == [("ocr-failed", "incomplete", [1])]
    assert "model file cut short" in result.issues[0].message and "converting again" in result.issues[0].message
    assert result.build["readers"]["ocr"]["failed"] == [{"page": 1, "error": "RuntimeError: model file cut short"}]
    assert result.location_map["pages"][0]["state"] == "unreadable"


def test_a_failed_reading_on_a_page_that_loses_nothing_raises_no_issue(tmp_path, monkeypatch):
    _ocr_that(monkeypatch, [RuntimeError("model file cut short")])
    pdf = pymupdf.open()
    pdf.new_page()                                          # nothing on it, not even a curve
    pdf.save(str(tmp_path / "blank.pdf"))
    pdf.close()
    result = convert_with_status(str(tmp_path / "blank.pdf"), ConvertOptions(**FAST))
    assert result.completion == "complete"
    assert [i.code for i in result.issues] == ["blank-pages"]
    assert result.build["readers"]["ocr"]["failed"] == [{"page": 1, "error": "RuntimeError: model file cut short"}]


def test_the_model_is_fetched_once_when_several_start_together(tmp_path, monkeypatch):
    import huggingface_hub

    monkeypatch.setenv("TRUEDOC_OCR_LANG", "en")
    monkeypatch.setattr(rapid, "_MODELS_DIR", str(tmp_path / "models"))
    fetched = []

    def slow_fetch(repo, filename, local_dir):
        fetched.append(filename)
        time.sleep(0.5)                                     # the model takes a while to arrive
        target = os.path.join(local_dir, filename.replace("/", os.sep))
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "wb") as f:
            f.write(b"model")
        return target

    monkeypatch.setattr(huggingface_hub, "hf_hub_download", slow_fetch)
    found = []
    starters = [threading.Thread(target=lambda: found.append(rapid.english_rec_model_path())) for _ in range(3)]
    for t in starters:
        t.start()
    for t in starters:
        t.join()
    assert len(fetched) == 1
    assert len(found) == 3 and len(set(found)) == 1 and found[0] and os.path.exists(found[0])
