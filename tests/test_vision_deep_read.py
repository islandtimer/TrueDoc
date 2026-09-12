"""A second, more expensive reader for the pages the first one cannot manage.

Measured over the benchmark's 98 old-scan pages on 12 September: on the pages olmOCR reads well the two
readers score level to the check, 117 each, and on the hardest third a frontier model roughly doubles
the score, 25 to 54. So the deep reader is worth its cost on the hard tail and nothing anywhere else,
and the converter decides which is which from a number it already computes - how word-like its own OCR
of the page came back. Real text scores 0.6 to 0.9 there and handwriting noise under 0.3; the measured
medians were 0.84 where olmOCR coped and 0.36 where it did not.
"""
from truedoc.model import Page, TextQuality
from truedoc.pipeline import ConvertOptions, _needs_a_deeper_read


def _page(kind: str = "none", **meta) -> Page:
    page = Page(number=1, width=612.0, height=792.0)
    page.quality = TextQuality(kind=kind)
    page.meta.update(meta)
    return page


def test_a_page_our_own_reader_cannot_make_words_of_goes_deep():
    opts = ConvertOptions(vision_deep="anthropic")
    assert _needs_a_deeper_read(_page(ocr_wordlike=0.36), opts)
    assert _needs_a_deeper_read(_page(ocr_wordlike=0.0), opts)


def test_a_page_our_own_reader_handles_does_not():
    opts = ConvertOptions(vision_deep="anthropic")
    assert not _needs_a_deeper_read(_page(ocr_wordlike=0.84), opts)
    assert not _needs_a_deeper_read(_page(ocr_wordlike=0.6), opts)


def test_a_page_with_its_own_text_is_never_sent_anywhere():
    opts = ConvertOptions(vision_deep="anthropic")
    assert not _needs_a_deeper_read(_page("digital", ocr_wordlike=0.0), opts)


def test_a_page_our_engine_found_nothing_on_is_the_hardest_kind():
    # No lines at all is evidence about the page, not an absence of evidence.
    opts = ConvertOptions(vision_deep="anthropic")
    assert _needs_a_deeper_read(_page(ocr_empty=True), opts)


def test_without_a_signal_nothing_expensive_is_spent():
    # OCR switched off leaves no reading to judge by, so the ordinary reader keeps the page.
    opts = ConvertOptions(vision_deep="anthropic", ocr=False)
    assert not _needs_a_deeper_read(_page(), opts)
    # and a page nobody OCR'd, with OCR on, is no evidence either
    assert not _needs_a_deeper_read(_page(), ConvertOptions(vision_deep="anthropic"))


def test_the_line_can_be_moved():
    strict = ConvertOptions(vision_deep="anthropic", vision_deep_wordlike=0.3)
    assert not _needs_a_deeper_read(_page(ocr_wordlike=0.36), strict)
    generous = ConvertOptions(vision_deep="anthropic", vision_deep_wordlike=0.9)
    assert _needs_a_deeper_read(_page(ocr_wordlike=0.84), generous)


def test_the_deep_reader_is_off_unless_asked_for():
    assert ConvertOptions().vision_deep is None


class _Recorder:
    """A stand-in reader that says which pages it was given."""

    def __init__(self, name, answer="read by " + "the stand-in"):
        self.name = name
        self.answer = answer
        self.pages = []

    def read_page(self, path, number):
        self.pages.append(number)
        return self.answer

    def read_region(self, *a, **k):
        return None


def test_only_the_hard_pages_reach_the_deep_reader(tmp_path, monkeypatch):
    """End to end: two unreadable pages, one our OCR makes words of and one it does not."""
    import truedoc.vision
    from truedoc import pipeline

    ordinary, deep = _Recorder("olmocr"), _Recorder("deep")
    monkeypatch.setattr(truedoc.vision, "make_provider",
                        lambda endpoint, model="olmocr": deep if endpoint == "deep" else ordinary)

    doc = pipeline.Document(path=str(tmp_path / "x.pdf"), pages=[], metadata={}, warnings=[])
    easy, hard = _page(ocr_wordlike=0.84), _page(ocr_wordlike=0.2)
    easy.number, hard.number = 1, 2
    doc.pages = [easy, hard]
    opts = ConvertOptions(vision_endpoint="served", vision_deep="deep", vision_regions=False)
    pipeline._read_unreadable_pages_with_model(doc, str(tmp_path / "x.pdf"), opts)

    assert deep.pages == [2], "only the page our own reader could not make words of"
    assert ordinary.pages == [1]
    assert hard.meta["deep_read"]["model"] == "deep"
    assert "deep_read" not in easy.meta


def test_a_silent_deep_reader_does_not_lose_the_page(tmp_path, monkeypatch):
    import truedoc.vision
    from truedoc import pipeline

    ordinary, deep = _Recorder("olmocr"), _Recorder("deep", answer=None)
    monkeypatch.setattr(truedoc.vision, "make_provider",
                        lambda endpoint, model="olmocr": deep if endpoint == "deep" else ordinary)
    doc = pipeline.Document(path=str(tmp_path / "x.pdf"), pages=[_page(ocr_wordlike=0.2)],
                            metadata={}, warnings=[])
    pipeline._read_unreadable_pages_with_model(
        doc, str(tmp_path / "x.pdf"),
        ConvertOptions(vision_endpoint="served", vision_deep="deep", vision_regions=False))
    assert deep.pages == [1] and ordinary.pages == [1], "the ordinary reader still had its turn"
    assert any("deep reader returned nothing" in w for w in doc.warnings)


def test_a_page_is_attributed_to_the_reader_that_read_it(tmp_path, monkeypatch):
    """D015: what a model wrote is marked as inferred, and the mark has to name the right model.

    The first wiring routed the page correctly and then stamped it with the ordinary reader's name, so
    a page read by a frontier model told the reader it came from olmOCR (12 September).
    """
    import truedoc.vision
    from truedoc import pipeline

    ordinary, deep = _Recorder("olmocr"), _Recorder("a-frontier-model")
    monkeypatch.setattr(truedoc.vision, "make_provider",
                        lambda endpoint, model="olmocr": deep if endpoint == "deep" else ordinary)
    easy, hard = _page(ocr_wordlike=0.9), _page(ocr_wordlike=0.1)
    easy.number, hard.number = 1, 2
    doc = pipeline.Document(path=str(tmp_path / "x.pdf"), pages=[easy, hard], metadata={}, warnings=[])
    pipeline._read_unreadable_pages_with_model(
        doc, str(tmp_path / "x.pdf"),
        ConvertOptions(vision_endpoint="served", vision_deep="deep", vision_regions=False))

    assert hard.meta["vision_model"] == "a-frontier-model"
    assert hard.blocks[0].provenance == "vision:a-frontier-model"
    assert easy.meta["vision_model"] == "olmocr"
    named = {entry["page"]: entry["model"] for entry in doc.metadata["inferred"]}
    assert named == {1: "olmocr", 2: "a-frontier-model"}


def test_the_benchmark_runner_passes_the_deep_reader_to_its_workers():
    """Run 90 launched, converted nothing and died in seconds: the switch had been added to the
    `convert` command only, and the benchmark uses `bench`. Every layer has to carry it (12 September).
    """
    import inspect

    from truedoc.bench.olmocr import _convert_one, run_olmocr_bench

    assert "vision_deep" in inspect.signature(run_olmocr_bench).parameters
    assert "vision_deep" in inspect.signature(_convert_one).parameters
    source = inspect.getsource(run_olmocr_bench)
    assert "vision_deep)" in source, "the workers are handed it, not just the runner"
    assert "vision_deep=vision_deep" in inspect.getsource(_convert_one), "and it reaches ConvertOptions"
