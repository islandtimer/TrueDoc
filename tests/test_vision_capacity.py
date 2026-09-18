"""A transcription cannot hold more print than its region (truedoc.vision.capacity)."""

from truedoc.vision.capacity import capacity, holds_more_than_fits, load, printed_characters


def test_a_region_holds_its_area_in_four_point_characters():
    assert capacity(200, 80) == 200 * 80 / 8.0
    assert capacity(0, 80) == 0 and capacity(-5, 80) == 0


def test_markup_and_table_bars_are_not_print():
    table = "| Event | Yes |\n| --- | --- |\n| Flood | Yes |\n"
    assert printed_characters(table) == len("EventYesFloodYes")
    assert printed_characters("<table><tr><td>Flood</td><td>Yes</td></tr></table>") == len("FloodYes")
    assert printed_characters("---\ncut_off: true\n---\nBody text\n") == len("Bodytext")


def test_an_invented_table_of_eighteen_hundred_rows_does_not_fit_a_scatter_plot():
    rows = "\n".join("|  | %.2f | %.2f |" % (i * 0.05, i * 0.05 + 0.15) for i in range(1800))
    assert holds_more_than_fits(rows, 196, 328)             # the crop it was written for, 18 September
    assert load(rows, 196, 328) > 2.0


def test_one_line_written_four_thousand_times_does_not_fit_a_figure():
    assert holds_more_than_fits("- V_i^50s\n" * 4095, 438, 270)


def test_a_real_table_in_a_picture_fits_with_room_to_spare():
    # a geology table of twenty rows and seven columns in a picture 462 x 591 points
    rows = "\n".join("| %d | Dcrc/G3S | Dacite | Ridge | > 30 | A 3222/sc | < 40 | Sand |" % i for i in range(1, 21))
    assert not holds_more_than_fits(rows, 462, 591)
    assert load(rows, 462, 591) < 0.1


def test_the_densest_real_page_we_have_seen_still_fits():
    # a tiny-print book scan: 4,918 characters on a page box of 297 x 200 points, three readers agreeing
    assert not holds_more_than_fits("x" * 4918, 297, 200)
    assert 0.6 < load("x" * 4918, 297, 200) < 0.7


def test_nothing_fits_no_region_and_nothing_is_always_fine():
    assert not holds_more_than_fits("", 100, 100)
    assert not holds_more_than_fits("some words", 0, 0)       # no region to judge by: say nothing


# --- wired into the pipeline: a whole page, and a picture on a digital page -----------------------

import io
from unittest.mock import patch

import pymupdf
from PIL import Image

from truedoc import pipeline
from truedoc.layout.base import Region, RegionKind
from truedoc.model import BBox
from truedoc.pipeline import ConvertOptions, convert_with_status


class _Reader:
    name = "stub"
    last_cut_off = False

    def __init__(self, page=None, region=None):
        self._page, self._region = page, region

    def read_page(self, pdf_path, page_number):
        return self._page

    def read_region(self, pdf_path, page_number, bbox, kind, turn=0):
        return self._region if kind == "picture-text" else None


def _blank(path):
    pdf = pymupdf.open()
    pdf.new_page(width=612, height=792)
    pdf.save(str(path))
    pdf.close()
    return str(path)


def test_a_whole_page_reading_that_cannot_fit_the_page_is_set_aside_and_said(tmp_path):
    loop = "- the same line again\n" * 9000                        # some 160,000 characters on a page that holds 60,588
    with patch("truedoc.vision.make_provider", return_value=_Reader(page=loop)):
        result = convert_with_status(_blank(tmp_path / "scan.pdf"), ConvertOptions(vision_endpoint="stub:", layout=False, math=False, ocr=False))
    assert "the same line again" not in result.markdown
    codes = {i.code: i for i in result.issues}
    assert codes["reading-implausible"].pages == [1] and codes["reading-implausible"].severity == "degraded"
    assert result.completion == "incomplete"                        # and the page nothing else could read is still reported


def test_a_reading_that_fits_is_used(tmp_path):
    with patch("truedoc.vision.make_provider", return_value=_Reader(page="A short page of scanned text, read in full.")):
        result = convert_with_status(_blank(tmp_path / "scan.pdf"), ConvertOptions(vision_endpoint="stub:", layout=False, math=False, ocr=False))
    assert "A short page of scanned text" in result.markdown and result.completion == "complete"


def test_an_invented_table_for_a_picture_is_set_aside_and_the_picture_stays_a_figure(tmp_path, monkeypatch):
    png = io.BytesIO()
    Image.new("RGB", (196, 328), (200, 200, 200)).save(png, format="PNG")
    pdf = pymupdf.open()
    page = pdf.new_page(width=612, height=792)
    page.insert_text((72, 100), "A paragraph of the page's own text stands above the picture, as on any digital page.")
    page.insert_image(pymupdf.Rect(72, 200, 268, 528), stream=png.getvalue())        # a scatter plot's size
    path = str(tmp_path / "plot.pdf")
    pdf.save(path)
    pdf.close()
    monkeypatch.setattr(pipeline, "_detect_layout", lambda pdf_page, opts, page=None: [Region(RegionKind.FIGURE, BBox(72, 200, 268, 528), 0.9)])
    invented = "| A | q | mu |\n| --- | --- | --- |\n" + "\n".join("|  | %.2f | %.2f |" % (i * 0.05, i * 0.05 + 0.15) for i in range(1800))
    with patch("truedoc.vision.make_provider", return_value=_Reader(region=invented)):
        result = convert_with_status(path, ConvertOptions(vision_endpoint="stub:", math=False, ocr=False))
    assert "44.95" not in result.markdown and result.markdown.count("](figure)") == 1
    assert [i.code for i in result.issues] == ["reading-implausible"] and result.completion == "degraded"
    with patch("truedoc.vision.make_provider", return_value=_Reader(region="| Item | Limit |\n| --- | --- |\n| Jewellery | 5,000 |")):
        kept = convert_with_status(path, ConvertOptions(vision_endpoint="stub:", math=False, ocr=False))
    assert "Jewellery" in kept.markdown and kept.completion == "complete"
