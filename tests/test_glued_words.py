"""Hidden OCR layers that carry no spaces between words are split with a dictionary."""

import pymupdf

from truedoc.extract.textlayer import _split_token
from truedoc.pipeline import ConvertOptions, convert


def test_split_token_finds_real_words_only():
    assert _split_token("widespreadaccessorymineral") == ["widespread", "accessory", "mineral"]
    assert _split_token("characteristicswere") == ["characteristics", "were"]
    assert _split_token("Transmissionelectron") == ["Transmission", "electron"]
    # Real long words, names and old spellings stay whole, even when the word
    # list could be chopped into fragments ("Albumazar" as "album azar").
    for word in ["metamictization", "birefringence", "Jolliffet", "Albumazar", "countship", "marquisate", "Palsgrave", "constreyned", "Whitehouse"]:
        assert _split_token(word) is None, word
    # Short runs are left to the gap rule: too many real words are absent from the list.
    assert _split_token("occursas") is None


def test_ocr_layer_glued_words_are_split(tmp_path):
    # A scan: a full-page image with an invisible text layer whose words run together.
    doc = pymupdf.open()
    page = doc.new_page(width=400, height=300)
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 40, 30), 0)
    pix.clear_with(255)
    page.insert_image(page.rect, pixmap=pix)
    y = 40
    for text in [
        "Zircon occursas a widespreadaccessorymineral in almost all types of terrestrial rocks.",
        "The chemical composition and some vibrational spectroscopic characteristicswere studied.",
        "Fractures extend into the matrix (Jolliff 1991).The grain is zoned; twinning is rare.",
    ] * 3:
        page.insert_text((30, y), text, fontsize=9, render_mode=3)
        y += 14
    path = tmp_path / "scan.pdf"
    doc.save(str(path))
    doc.close()

    md = convert(str(path), ConvertOptions(frontmatter=False, layout=False, ocr=False))
    assert "widespread accessory mineral" in md, md
    assert "characteristics were" in md
    assert "1991). The grain" in md
