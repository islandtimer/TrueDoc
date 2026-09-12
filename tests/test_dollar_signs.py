r"""A price is not a formula (D024).

TrueDoc writes formulas as \(...\) and \[...\], so nothing of its own hangs on dollar signs, and it writes
a literal dollar sign as \$ so that no viewer can read the stretch between two prices as a formula. The
owner's insurance documents are full of prices: written bare, "The excess is $100 and the benefit limit is
$2,000 per claim" renders in a maths-aware viewer as "The excess is" followed by italic gibberish, and the
benchmark's own scorer reads it the same way - one stray dollar sign on 2503.05329 page 4 paired with the
formulas after it and cost the page its check.

An HTML table is left alone on purpose: markdown escapes do not apply inside one, so a backslash there
would show up as a backslash.
"""
import os
import tempfile

from truedoc.model import BBox, Block, BlockKind, Table, TableCell
from truedoc.pipeline import ConvertOptions, convert
from truedoc.render.okf import _escape_dollars, render_block

_CONTENT = (
    b"BT /F1 11 Tf 60 400 Td (The excess is $100 and the benefit limit is $2,000 per claim.) Tj ET\n"
    b"BT /F1 11 Tf 60 370 Td (Emergency accommodation costs up to $350 a night.) Tj ET\n"
)


def _pdf() -> str:
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 420 760] "
            b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
            b"<< /Length " + str(len(_CONTENT)).encode() + b" >>\nstream\n" + _CONTENT + b"\nendstream",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objs, start=1):
        offsets.append(len(out))
        out += str(i).encode() + b" 0 obj\n" + body + b"\nendobj\n"
    start = len(out)
    out += b"xref\n0 " + str(len(objs) + 1).encode() + b"\n0000000000 65535 f \n"
    for off in offsets:
        out += ("%010d 00000 n \n" % off).encode()
    out += (b"trailer\n<< /Size " + str(len(objs) + 1).encode() + b" /Root 1 0 R >>\n"
            b"startxref\n" + str(start).encode() + b"\n%%EOF\n")
    fd, path = tempfile.mkstemp(suffix=".pdf")
    with os.fdopen(fd, "wb") as fh:
        fh.write(bytes(out))
    return path


def test_prices_on_a_page_are_written_so_no_viewer_reads_them_as_maths():
    path = _pdf()
    try:
        md = convert(path, ConvertOptions(frontmatter=False, layout=False, ocr=False))
    finally:
        os.unlink(path)
    assert "\\$100" in md and "\\$2,000" in md and "\\$350" in md, md
    assert md.replace("\\$", "") .count("$") == 0, md          # no bare dollar sign left
    assert "The excess is" in md and "per claim" in md, md


def test_a_price_in_a_table_cell_is_escaped_and_a_formula_is_not():
    table = Table(n_rows=2, n_cols=2, bbox=BBox(0, 0, 10, 10), cells=[
        TableCell(text="Excess", row=0, col=0), TableCell(text="Amount", row=0, col=1),
        TableCell(text="Burst pipe", row=1, col=0), TableCell(text="$448", row=1, col=1)])
    md = render_block(Block(kind=BlockKind.TABLE, bbox=BBox(0, 0, 10, 10), table=table))
    assert "| \\$448 |" in md, md
    formula = render_block(Block(kind=BlockKind.FORMULA, bbox=BBox(0, 0, 10, 10),
                                 text_override=r"\[E = mc^2\]"))
    assert formula == r"\[E = mc^2\]", formula


def test_what_escaping_leaves_alone():
    """TrueDoc's own formulas, and a dollar sign already escaped.

    A model's dollar-delimited maths is escaped like anything else: the stretch between two prices can
    hold a formula, so a span between dollar signs cannot be taken for one. Escaped, the reader sees the
    maths as it was typed rather than as italic gibberish.
    """
    assert _escape_dollars(r"about $5 and \(x^2\) and $6") == r"about \$5 and \(x^2\) and \$6"
    assert _escape_dollars(r"\[E = mc^2\] costs $5") == r"\[E = mc^2\] costs \$5"
    assert _escape_dollars(r"a model may write $x^{2}$ itself") == r"a model may write \$x^{2}\$ itself"
    assert _escape_dollars(r"already \$7 stays") == r"already \$7 stays"
