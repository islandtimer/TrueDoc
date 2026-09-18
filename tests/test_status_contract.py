"""How a conversion ended is carried apart from the markdown (D037).

Each test is one of the probes of the 17-18 September review, turned into an acceptance case: a
document nothing could read still says so; a model's reply cut off at its token limit is named; a
page selection the document cannot meet is refused; a saved reading salvaged from a cut-off reply
is reported when it is replayed. Everything here is synthetic: no source document, no network.
"""

import io
import json
from unittest.mock import patch

import pymupdf
import pytest
import yaml
from typer.testing import CliRunner

from truedoc.cli import _parse_pages, app
from truedoc.model import Document, Issue, Page
from truedoc.pipeline import ConvertOptions, PageSelectionError, convert, convert_with_status, load_document
from truedoc.render.okf import RenderOptions, render_document
from truedoc.vision.anthropic_api import AnthropicVision
from truedoc.vision.file_readings import FileReadings
from truedoc.vision.olmocr_endpoint import OlmocrEndpoint

FAST = dict(layout=False, math=False, ocr=False)


def _two_pages(path):
    pdf = pymupdf.open()
    for number in (1, 2):
        page = pdf.new_page()
        page.insert_text((72, 120), f"Unique review page {number} contains enough readable words for the text layer.")
    pdf.save(str(path))
    pdf.close()
    return str(path)


def _blank_page(path):
    pdf = pymupdf.open()
    pdf.new_page()
    pdf.save(str(path))
    pdf.close()
    return str(path)


def _front_matter(markdown: str) -> dict:
    assert markdown.startswith("---\n")
    return yaml.safe_load(markdown.split("\n---", 1)[0][4:])


# --- P01: an empty body must not take the status with it -----------------------------------------

def test_a_document_nothing_could_read_still_says_so_in_its_front_matter():
    doc = Document(path="unreadable.pdf", pages=[Page(number=1, width=400, height=600)])
    doc.add_issue("unreadable-pages", "pages without readable text: [1]", "incomplete", [1])
    out = render_document(doc, RenderOptions(frontmatter=True))
    td = _front_matter(out)["truedoc"]
    assert td["completion"] == "incomplete"
    assert td["warnings"] == ["pages without readable text: [1]"]
    assert td["issues"] == [{"code": "unreadable-pages", "severity": "incomplete", "pages": [1],
                             "message": "pages without readable text: [1]"}]
    assert out.split("\n---", 1)[1].strip() == ""          # and the body is still empty: nothing is invented


def test_without_front_matter_the_body_stays_empty_and_the_result_carries_the_status(tmp_path):
    result = convert_with_status(_blank_page(tmp_path / "blank.pdf"), ConvertOptions(frontmatter=False, **FAST))
    assert result.markdown == ""
    assert result.completion == "incomplete"
    assert [(i.code, i.pages) for i in result.issues] == [("unreadable-pages", [1])]
    assert json.loads(json.dumps(result.as_dict()))["issues"][0]["severity"] == "incomplete"


def test_a_clean_conversion_is_complete_and_says_so(tmp_path):
    result = convert_with_status(_two_pages(tmp_path / "two.pdf"), ConvertOptions(**FAST))
    assert result.completion == "complete" and result.issues == [] and result.pages == [1, 2]
    assert _front_matter(result.markdown)["truedoc"]["completion"] == "complete"
    assert "issues" not in _front_matter(result.markdown)["truedoc"]


def test_a_warning_nobody_classified_is_still_reported():
    doc = Document(path="x.pdf")
    doc.warnings.append("something an older caller appended as a bare sentence")
    assert [i.code for i in doc.all_issues()] == ["warning"]
    assert doc.completion == "complete"                     # a note: nothing is known to be missing


def test_the_worst_issue_decides():
    doc = Document(path="x.pdf")
    doc.add_issue("hidden-text", "hidden text removed from the body on pages: [2]", "note", [2])
    assert doc.completion == "complete"
    doc.add_issue("stage-unavailable", "the layout model was asked for and could not run", "degraded", [1, 2])
    assert doc.completion == "degraded"
    doc.add_issue("reply-cut-off", "page 2: the model's reply was cut off", "incomplete", [2])
    assert doc.completion == "incomplete"
    with pytest.raises(ValueError):
        doc.add_issue("x", "y", "catastrophic")


# --- P05: a page selection the document cannot meet is refused -----------------------------------

@pytest.mark.parametrize("spec", ["2-1", "0", "1-2-3", "two", "", " , ", "-3"])
def test_a_page_range_that_names_nothing_is_refused(spec):
    with pytest.raises(ValueError):
        _parse_pages(spec)


def test_page_ranges_that_mean_something_still_parse():
    assert _parse_pages("1,3-5") == [1, 3, 4, 5]
    assert _parse_pages(" 2 , 2-2 ") == [2, 2]


def test_the_pipeline_refuses_pages_the_document_does_not_have(tmp_path):
    pdf = _two_pages(tmp_path / "two.pdf")
    with pytest.raises(PageSelectionError, match=r"\[99\] are not in this document, which has 2 page"):
        load_document(pdf, ConvertOptions(pages=[1, 99], **FAST))
    with pytest.raises(PageSelectionError, match="names no page"):
        load_document(pdf, ConvertOptions(pages=[], **FAST))        # it used to convert every page
    assert "Unique review page 2" in convert(pdf, ConvertOptions(pages=[2], **FAST))


def test_the_command_line_says_no_with_exit_code_2(tmp_path):
    pdf = _two_pages(tmp_path / "two.pdf")
    runner = CliRunner()
    common = ["convert", pdf, "--no-layout", "--no-math", "--no-ocr"]
    for spec in ("2-1", "99", "0"):
        r = runner.invoke(app, [*common, "--pages", spec])
        assert r.exit_code == 2, (spec, r.output)
        assert "Unique review page" not in r.output
    r = runner.invoke(app, [*common, "--pages", "1"])
    assert r.exit_code == 0 and "Unique review page 1" in r.output and "Unique review page 2" not in r.output


def test_strict_turns_an_incomplete_conversion_into_exit_code_3_and_status_is_written(tmp_path):
    pdf = _blank_page(tmp_path / "blank.pdf")
    out, status = tmp_path / "blank.md", tmp_path / "blank.status.json"
    runner = CliRunner()
    common = ["convert", pdf, "--no-layout", "--no-math", "--no-ocr", "-o", str(out), "--status", str(status)]
    r = runner.invoke(app, common)
    assert r.exit_code == 0                                  # the default: converted, and told
    assert "incomplete - 1 issue" in r.output and "unreadable-pages" in r.output
    assert json.loads(status.read_text(encoding="utf-8"))["completion"] == "incomplete"
    assert _front_matter(out.read_text(encoding="utf-8"))["truedoc"]["completion"] == "incomplete"
    r = runner.invoke(app, [*common, "--strict"])
    assert r.exit_code == 3 and out.exists()                 # strict: still written, and refused as complete


# --- P04: a reply cut off at its token limit is not a finished reading ---------------------------

def _reply(payload):
    return patch("urllib.request.urlopen", return_value=io.BytesIO(json.dumps(payload).encode()))


def test_the_anthropic_provider_notices_a_reply_cut_off_at_its_token_limit():
    provider = AnthropicVision(api_key="placeholder", api_url="http://127.0.0.1/none")
    cut = {"content": [{"type": "text", "text": "A partial statement ending before its exclusion"}], "stop_reason": "max_tokens"}
    with _reply(cut):
        assert provider._ask("synthetic", "", 8) == "A partial statement ending before its exclusion"
    assert provider.last_cut_off is True
    provider.last_cut_off = False
    with _reply(dict(cut, stop_reason="end_turn")):
        provider._ask("synthetic", "", 8)
    assert provider.last_cut_off is False


def test_a_served_model_says_the_same_with_finish_reason_length():
    provider = OlmocrEndpoint("http://127.0.0.1:9")
    with _reply({"choices": [{"message": {"content": "Half a page"}, "finish_reason": "length"}]}):
        assert provider._chat("", None, 8, "page 1") == "Half a page"
    assert provider.last_cut_off is True


class _CutOffReader:
    """A reader whose one reply stopped at the token limit."""
    name = "stub"

    def __init__(self):
        self.last_cut_off = False

    def read_page(self, pdf_path, page_number):
        self.last_cut_off = True
        return "A cover statement that was read in full. An exception that stops in the middle of"

    def read_region(self, *args, **kwargs):
        self.last_cut_off = False
        return None


def test_the_pipeline_names_the_page_and_keeps_what_was_read(tmp_path):
    pdf = _blank_page(tmp_path / "scan.pdf")
    with patch("truedoc.vision.make_provider", return_value=_CutOffReader()):
        result = convert_with_status(pdf, ConvertOptions(vision_endpoint="stub:", **FAST))
    assert "A cover statement that was read in full" in result.markdown      # most of a page beats none of it
    assert result.completion == "incomplete"
    cut = [i for i in result.issues if i.code == "reply-cut-off"]
    assert len(cut) == 1 and cut[0].pages == [1] and cut[0].severity == "incomplete"


# --- P2-01: a saved reading salvaged from a cut-off reply says so when it is replayed ------------

def test_a_saved_reading_marked_cut_off_is_reported_on_replay(tmp_path):
    folder = tmp_path / "readings"
    folder.mkdir()
    (folder / "whole_pg1_repeat1.md").write_text("A reading that ran to its end.\n", encoding="utf-8")
    (folder / "short_pg1_repeat1.md").write_text("---\ncut_off: true\n---\nA cover statement, and then\n", encoding="utf-8")
    readings = FileReadings(str(folder))
    assert readings.read_page("short.pdf", 1) == "A cover statement, and then"
    assert readings.last_cut_off is True
    assert readings.read_page("whole.pdf", 1) == "A reading that ran to its end."
    assert readings.last_cut_off is False                    # the flag belongs to the last reading only


def test_an_issue_is_plain_data():
    assert Issue("reply-cut-off", "page 3: cut off", "incomplete", [3]).as_dict() == {
        "code": "reply-cut-off", "severity": "incomplete", "pages": [3], "message": "page 3: cut off"}
