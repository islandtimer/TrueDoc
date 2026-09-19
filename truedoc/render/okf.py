"""Render a Document to OKF markdown (YAML front matter + markdown body)."""

from __future__ import annotations

import datetime as _dt
import re
from dataclasses import dataclass

import yaml

from truedoc import __version__
from truedoc.model import Block, BlockKind, Document, Line, Table

_FUNCTION_WORDS = {"the", "of", "and", "or", "to", "in", "on", "a", "an", "by", "for", "at", "as", "is", "it"}

# D015: text a model read from pixels or inferred carries a footnote tag; the
# definition is written once, at the end of the body, only when something is tagged.
INFERRED_TAG = "[^inferred]"
INFERRED_DEFINITION = (
    "[^inferred]: Marked text was read from the page image or inferred by a model, "
    "not taken from the document's own text. See truedoc.inferred in the front matter."
)


@dataclass
class RenderOptions:
    frontmatter: bool = True
    page_markers: bool = False
    drop_headers_footers: bool = True


def join_lines(lines: list[Line], texts: list[str] | None = None) -> str:
    """Join physical lines into a paragraph, repairing end-of-line hyphenation."""
    out = ""
    for idx, line in enumerate(lines):
        text = (texts[idx] if texts is not None and idx < len(texts) else line.text).strip()
        if not text:
            continue
        if not out:
            out = text
            continue
        # An inline formula broken across a line break: "\(a =\)" / "\(b + c\)" is one formula.
        if out.endswith("\\)") and text.startswith("\\(") and len(out) >= 3:
            out = out[:-2] + " " + text[2:]
            continue
        if out.endswith("-") and len(out) >= 2 and not out.endswith(" -"):
            out = _join_at_hyphen(out, text)
            continue
        # A word broken over the line break with no hyphen at all (an OCR'd text
        # layer that lost it: "typi" / "cally" on a multi-column page): join the
        # fragments when neither is a word and together they make one.
        if _broken_word(out.rsplit(" ", 1)[-1], text.split(" ", 1)[0]):
            out = out + text
            continue
        out = out + " " + text
    return out


def _join_at_hyphen(out: str, text: str) -> str:
    """Join the text after a line ending in a hyphen.

    The hyphen is dropped only when the two halves make one word: the English word list
    knows "research" ("re-" / "search"), so the halves join; it knows "racist" and "free"
    but not "racistfree", so "racist-free" keeps its hyphen (run 60 joined it, and
    "third-highest", "cluster-level": five checks). A half starting with a capital or a
    digit keeps the hyphen ("G-CSF", "2019-2020"); a hyphen before a function word is a
    suspended one and keeps its space ("40- to 100-μm"). Halves the list does not know
    join, a broken word being the commoner case."""
    prev_word = out.rsplit(" ", 1)[-1][:-1]
    core = text.split(" ", 1)[0].strip(".,;:!?)]\"'")
    if not text[0].islower() or "-" in prev_word or not core:
        return out + text
    from truedoc.extract.textlayer import _dictionary

    vocab = _dictionary()
    a, b = prev_word.lower().lstrip("([\"'"), core.lower()
    if core.lower() in _FUNCTION_WORDS:
        # Suspended - unless the halves are a word: "spir-" / "it" is "spirit", "benef-" / "it" is "benefit",
        # and asking about the function word first wrote them "spir- it" (found 19 September 2026 by the screen
        # of the table joiner, which borrows this rule).
        # A suspended hyphen stands before "and", "or", "to" and makes no word with them ("pre- and post-",
        # "two- to three-fold"); "with-" / "in", "there-" / "of", "un-" / "it" do.
        # A half of two letters at least, as the compound test below asks: "a minimum grade of C-" / "or ECON 402H"
        # is a grade and a minus, and the word list holds "cor" (the screen's other find, on 1,527 pages).
        if vocab is not None and a.isalpha() and len(a) >= 2 and (a + b) in vocab:
            return out[:-1] + text
        return out + " " + text
    # One letter and a hyphen is the head of a compound ("Q-" / "network", "T-" / "carbon", "L-" / "carnitine",
    # Maltese "l-" / "ewwel"): closing it up wrote "Deep Qnetwork". Unless the halves are a word - one page of 1,527
    # does break "s-" / "ingle".
    if len(a) == 1 and a.isalpha() and not (vocab is not None and b.isalpha() and (a + b) in vocab):
        return out + text
    if vocab is not None and a.isalpha() and b.isalpha() and (a + b) not in vocab and a in vocab and b in vocab and len(a) >= 2 and len(b) >= 2:
        # A prefix joins its word ("pre-" / "dialysis": the list lacks the compound), unless
        # the two vowels would meet ("anti-" / "inflammatory", "re-" / "enter").
        if a not in _PREFIXES or (a[-1] in "aeiou" and b[0] == a[-1]):
            return out + text
    return out[:-1] + text


_PREFIXES = {"pre", "post", "non", "anti", "co", "re", "de", "sub", "super", "inter", "intra", "multi", "semi", "pseudo", "micro",
             "macro", "over", "under", "ultra", "un", "dis", "mis", "counter", "extra", "hyper", "hypo", "meta", "mid", "neo", "pro",
             "trans", "bi", "tri", "uni", "poly", "mono", "auto", "bio", "geo", "electro", "photo", "thermo", "hydro", "immuno",
             "neuro", "cardio", "radio", "socio", "psycho", "eco", "pan", "peri", "para", "iso", "homo", "hetero", "cyto", "endo"}


def _broken_word(a: str, b: str) -> bool:
    a = a.lstrip("([\"'")
    b_core = b.rstrip(".,;:!?)]\"'")
    if not (a.isalpha() and a.islower() and b_core.isalpha() and b_core.islower()
            and len(a) >= 2 and len(b_core) >= 2 and len(a) + len(b_core) >= 6):
        return False
    from truedoc.extract.textlayer import _dictionary

    vocab = _dictionary()
    if not vocab:
        return False
    return (a + b_core) in vocab and a not in vocab and b_core not in vocab


def render_table(table: Table) -> str:
    grid = table.grid()
    # A list inside a cell (D028) needs HTML as a span does: a markdown table's cell holds one line.
    if table.has_merged or any(c.listing is not None for c in table.cells):
        return _render_html_table(table, grid)
    rows: list[list[str]] = []
    for r in range(table.n_rows):
        row = []
        for c in range(table.n_cols):
            cell = grid[r][c]
            # A cell spanning rows is written once, in the first row it covers.
            row.append(_md_cell(cell.text if cell and cell.row == r else ""))
        rows.append(row)
    if not rows:
        return ""
    lines = ["| " + " | ".join(rows[0]) + " |", "|" + "|".join([" --- "] * table.n_cols) + "|"]
    for row in rows[1:]:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


# Blocks that can be two halves of one paragraph: prose, and the list items a reference list is
# made of (a reference running over the column break has its last word split at a hyphen).
_JOINABLE = (BlockKind.TEXT, BlockKind.LIST_ITEM)

_DOLLAR = re.compile(r"(?<!\\)\$")
# What must not be touched: TrueDoc's own formulas, and only those. A span between two dollar signs is
# never spared, however TeX-looking, because the stretch between two prices can hold one: "about $5 and
# \(x^2\) and $6" would then have been read as a single formula and both prices left bare. A model that
# writes its maths between dollar signs has them escaped, which shows a reader the maths as it was typed
# rather than as italic gibberish.
_FORMULA_SPAN = re.compile(r"\\\[.*?\\\]|\\\(.*?\\\)", re.S)


_BARE_AMP = re.compile(r"(?<!\\)&")


def _escape_formula_ampersands(span: str) -> str:
    """A bare `&` inside a formula written `\\&`: LaTeX reads it as an alignment character.

    A model transcribing an old textbook writes a series as "1 - 3x + 6x^2 + &c." - the
    nineteenth-century abbreviation for "etc." - and that one character stops the whole formula
    rendering, so the reader is shown raw TeX. The benchmark's own references write it escaped.
    A span that opens an environment keeps its ampersands: there they are the alignment the
    environment is built from, and escaping them would break the formula this is meant to save.
    """
    if "\\begin{" in span:
        return span
    return _BARE_AMP.sub(r"\\&", span)


def _escape_dollars(text: str) -> str:
    """A literal dollar sign written as `\\$` (D024), and a bare `&` inside a formula as `\\&`.

    TrueDoc writes formulas between `\\(` and `\\)`, so nothing of ours depends on dollar signs any
    more; a reader's viewer, though, may read the stretch between any two of them as a formula, and
    an insurance document is full of prices. Escaping is markdown's own answer and shows a dollar
    sign in every viewer. A formula keeps its dollar signs, and has its stray ampersands escaped so
    that it renders at all.
    """
    out, pos = [], 0
    for m in _FORMULA_SPAN.finditer(text):
        out.append(_DOLLAR.sub(r"\\$", text[pos:m.start()]))
        out.append(_escape_formula_ampersands(m.group(0)))
        pos = m.end()
    out.append(_DOLLAR.sub(r"\\$", text[pos:]))
    return "".join(out)


def _md_cell(text: str) -> str:
    return _escape_dollars(text.replace("|", "\\|").replace("\n", " ").strip())


def _render_html_table(table: Table, grid) -> str:
    out = ["<table>"]
    emitted: set[int] = set()
    for r in range(table.n_rows):
        out.append("<tr>")
        for c in range(table.n_cols):
            cell = grid[r][c]
            if cell is None:
                out.append("<td></td>")
                continue
            if id(cell) in emitted:
                continue
            emitted.add(id(cell))
            attrs = ""
            if cell.rowspan > 1:
                attrs += f' rowspan="{cell.rowspan}"'
            if cell.colspan > 1:
                attrs += f' colspan="{cell.colspan}"'
            tag = "th" if cell.is_header else "td"
            body = _listing_html(cell.listing) if cell.listing is not None else _html_escape(cell.text)
            out.append(f"<{tag}{attrs}>{body}</{tag}>")
        out.append("</tr>")
    out.append("</table>")
    return "\n".join(out)


def _html_escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _listing_html(listing) -> str:
    """A list set inside a table cell (D028): an element per entry with its sub-list nested, the words before the list
    and a note after it as paragraphs. Each element goes on a line of its own, so a reader that takes a cell's text
    whole (the benchmark's scorer does) still finds a break between one entry and the next."""
    nl = chr(10)
    parts = [f"<p>{_html_escape(listing.lead)}</p>"] if listing.lead else []
    parts.append("<ul>")
    for item in listing.items:
        inner = _html_escape(item.text)
        if item.children:
            inner += nl + "<ul>" + nl + nl.join(f"<li>{_html_escape(c)}</li>" for c in item.children) + nl + "</ul>"
        if item.tail:
            inner += nl + _html_escape(item.tail)
        parts.append(f"<li>{inner}</li>")
    parts.append("</ul>")
    if listing.note:
        parts.append(f"<p>{_html_escape(listing.note)}</p>")
    return nl.join(parts)


def _corroboration_summary(doc: Document) -> dict | None:
    """D008, M6: how much of what a model read we could corroborate from the page itself.

    A count per verdict, and the pages worth an eye. "unchecked" is the honest answer for a bare
    scan with no witness, and it is the commonest one: saying so beats implying a pass.
    """
    import collections

    rows = doc.metadata.get("corroboration") or []
    if not rows:
        return None
    counts = collections.Counter(r["state"] for r in rows)
    out: dict = {"pages_checked": len(rows)}
    out.update({state.replace(" ", "_"): n for state, n in sorted(counts.items())})
    flagged = [r["page"] for r in rows if r["state"] == "low support"]
    if flagged:
        out["low_support_pages"] = flagged
    return out


def render_block(block: Block) -> str:
    k = block.kind
    if k == BlockKind.TABLE and block.table is not None:
        return render_table(block.table)
    if k == BlockKind.FIGURE and not block.lines and block.text_override is None:
        only = block.meta.get("mark_only")
        if only:
            # A picture whose whole content is one readable drawn mark is that mark, not an
            # anonymous placeholder (D013). Insurance policies chain statements down a page with
            # an arrow in a disc between them, where the arrow is carrying the word "then".
            return only
        # A figure has no text of its own; it renders as an image placeholder, with a
        # model's description as alt text when the vision stage supplied one (D015).
        desc = block.meta.get("inferred_text")
        if desc:
            return "![%s](figure)%s" % (_alt_text(desc), INFERRED_TAG)
        return "![](figure)"
    if block.text_override is not None:
        text = block.text_override.strip()
    elif block.meta.get("preserve_lines"):
        # An algorithm listing: one statement per line, hard line breaks kept.
        texts = block.meta.get("line_texts") or [l.text for l in block.lines]
        text = "  \n".join(t.strip() for t in texts if t.strip())
    else:
        text = join_lines(block.lines, block.meta.get("line_texts"))
    if not text:
        return ""
    if k == BlockKind.HEADING or k == BlockKind.TITLE:
        level = max(1, min(6, block.level or 2))
        return "#" * level + " " + re.sub(r"\s+", " ", text)
    if k == BlockKind.LIST_ITEM:
        return _render_list_item(text, block.level or 1)
    if k == BlockKind.FIGURE:
        if block.meta.get("transcribed"):
            # D015, D019: a picture that held text or a table, transcribed by a model: the
            # placeholder stays, the transcription follows it, tagged as inferred.
            tag_line = INFERRED_TAG if text.rstrip().endswith("|") else None
            body = text if tag_line else text + INFERRED_TAG
            return "![](figure)\n\n" + body + ("\n\n" + tag_line if tag_line else "")
        desc = block.meta.get("inferred_text")
        if desc:
            # D015: a model's description of the figure is its alt text, tagged as inferred.
            return "![%s](figure)%s" % (_alt_text(desc), INFERRED_TAG)
        return "![](figure)"
    if k == BlockKind.FORMULA:
        return text
    if k == BlockKind.FOOTNOTE:
        if block.meta.get("footnotes"):
            return "\n\n".join("[^%s]: %s" % (key, note) for key, note in block.meta["footnotes"])
        return text
    return text


def _alt_text(text: str) -> str:
    """Alt text may not hold brackets or line breaks."""
    return re.sub(r"\s+", " ", text).replace("[", "(").replace("]", ")").strip()


def _render_list_item(text: str, level: int = 1) -> str:
    # A sub-list is indented under the entry it belongs to, two spaces a level, which is what markdown reads as
    # nesting. The level is the marker's own place on the page (`pipeline._list_levels`).
    pad = "  " * max(0, min(level, 4) - 1)
    m = re.match(r"^\s*([\u2022\u25e6\u25aa\u25cf\u2023\u2043\u25a0\u25a1\u00b7\-\u2013\u2014\*])\s*(.*)$", text, re.S)
    if m:
        return pad + "- " + m.group(2).strip()
    m = re.match(r"^\s*\(?(\d{1,3})[.)]\s*(.*)$", text, re.S)
    if m:
        return pad + f"{m.group(1)}. " + m.group(2).strip()
    # Letter and roman-numeral markers ("(a)", "iv.") are kept verbatim: they carry meaning.
    return pad + text.strip()


_DANGLING_END = r"(?:=|\+|-|<|>|\\leq|\\geq|\\le|\\ge|\\neq|\\to|\\rightarrow|\\times|\\cdot|\\pm|\\approx|\\sim|\\subset|\\in)"
_PLAIN_TERM = r"(?:[0-9]+(?:\.[0-9]+)?%?|[-+=<>/*×·]|\([0-9,\s]+\))"
_DANGLING_FORMULA = re.compile(r"(" + _DANGLING_END + r")\\\)[ \n]+(" + _PLAIN_TERM + r"(?:[ \n]+" + _PLAIN_TERM + r")*)(?=[.,;:]?(?:\s|$))")
_SPLIT_FORMULA = re.compile(r"(" + _DANGLING_END + r")\\\)[ \n]+\\\(")


def _join_dangling_formulas(body: str) -> str:
    """Pull the arithmetic that follows a line break back into its formula.

    A formula broken across two lines ends the first with a relation or an
    operator ("maj(σ) =") and continues on the next with plain numbers ("2 + 1
    + 1 + 1 = 5"), which the line-by-line detector leaves as prose because
    numbers alone are not maths. A formula that ends in a dangling relation
    or operator has no such reading: the numbers belong to it.
    """
    def repl(m: re.Match) -> str:
        arithmetic = m.group(2).replace(" ", "").replace("\n", "").replace("×", r"\times ").replace("·", r"\cdot ")
        return m.group(1) + arithmetic + "\\)"
    body = _DANGLING_FORMULA.sub(repl, body)
    # Two inline formulas split by a line break, the first ending in a dangling
    # relation ("\(\sigma(x)=\)" then "\([\sigma(x_1),...]^T\)"), are one formula.
    body = _SPLIT_FORMULA.sub(r"\1 ", body)
    return body


def render_document(doc: Document, opts: RenderOptions | None = None) -> str:
    opts = opts or RenderOptions()
    parts: list[str] = []
    prev_block: Block | None = None     # the last text block rendered, for paragraph joins
    prev_index = -1                     # its index in `parts`
    figures_since = True                # only figure placeholders rendered since it
    for page in doc.pages:
        if opts.page_markers:
            parts.append(f"<!-- page: {page.number} -->")
            figures_since = False
        if page.meta.get("vision_model"):
            # D015: a page read by a model says so where the reader will see it. D019: a hidden
            # OCR layer is not the author's text, so such a page is read by the model too.
            why = "the PDF's own text layer is an OCR layer, not the author's text" if page.meta.get("vision_replaced") in ("ocr", "suspect") else "the PDF holds no text for it"
            parts.append(f"> This page was read from its image by a model ({page.meta['vision_model']}); {why}.{INFERRED_TAG}")
            prev_block = None
        for block in page.ordered_blocks():
            if opts.drop_headers_footers and block.kind in (BlockKind.HEADER, BlockKind.FOOTER, BlockKind.PAGE_NUMBER):
                continue
            text = render_block(block)
            if not text:
                continue
            if block.kind not in (BlockKind.FORMULA, BlockKind.TABLE):
                text = _escape_dollars(text)      # D024; a table escapes its own cells
            # Join a paragraph continued across a column or page break. A figure
            # sitting at the foot of the column does not break the paragraph: its
            # placeholder stays where it was, after the joined paragraph.
            if (
                prev_block is not None
                and figures_since
                and 0 <= prev_index < len(parts)
                and block.kind in _JOINABLE
                and prev_block.kind in _JOINABLE
                and (
                    (block.kind == BlockKind.TEXT and prev_block.kind == BlockKind.TEXT)
                    # A list item the column break cut in two is one item, not two: a hyphen at the
                    # end of one block and the other half of the word at the start of the next.
                    # A journal's reference list is list items, so the rule below never saw them.
                    or (parts[prev_index].rstrip().endswith("-") and text[:1].islower())
                )
                and _continues(parts[prev_index], text)
                and (
                    prev_block.meta.get("page") != page.number
                    or _column_break(prev_block, block)
                    # A block that ends in a hyphenated word half and a block that
                    # starts with the other half are one paragraph wherever they
                    # sit ("nega-" / "tive effects" in a reference list).
                    or (parts[prev_index].rstrip().endswith("-") and text[:1].islower())
                )
            ):
                parts[prev_index] = _join_paragraphs(parts[prev_index], text)
            else:
                parts.append(text)
                if block.kind == BlockKind.FIGURE:
                    block.meta["page"] = page.number
                    continue  # a figure neither starts nor ends a paragraph
                prev_index = len(parts) - 1
                figures_since = True
            block.meta["page"] = page.number
            prev_block = block
    if any(p and INFERRED_TAG in p for p in parts):
        parts.append(INFERRED_DEFINITION)
    body = "\n\n".join(p for p in parts if p is not None).rstrip()
    # Raw glyph codes of maths-extension fonts (control and private-use characters)
    # that no formula claimed must not leak into the text.
    body = _RAW_GLYPH_CODES.sub("", body)
    # The ellipsis character is written as three dots: that is how readers type
    # it when they search or quote, and the meaning is the same.
    body = body.replace("…", "...")
    body = _join_dangling_formulas(body)
    # A page with nothing readable yields an empty body, not a lone newline: fuzzy matchers
    # treat a one-character document as matching anything. With a front matter block asked for,
    # the block is still written - it is where the file says that nothing could be read, and an
    # empty file says nothing at all (D037; without one, `convert_with_status` carries it).
    if not body:
        return render_frontmatter(doc, body) + "\n" if opts.frontmatter else ""
    if opts.frontmatter:
        return render_frontmatter(doc, body) + "\n\n" + body + "\n"
    return body + "\n"


_RAW_GLYPH_CODES = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-]")


def _column_break(prev: Block, nxt: Block) -> bool:
    """True when `nxt` starts a new column or page region rather than following `prev` vertically."""
    if nxt.bbox.y0 >= prev.bbox.y1 - 2.0 and nxt.bbox.x_overlap(prev.bbox) > 0:
        return False  # directly below: a new paragraph, not a continuation
    return nxt.bbox.y0 < prev.bbox.y0 + 2.0 and nxt.bbox.x0 > prev.bbox.x0 + 0.5 * prev.bbox.width


def _continues(prev: str, nxt: str) -> bool:
    if not prev or not nxt:
        return False
    if prev.startswith("#") or prev.startswith("|") or prev.startswith("<table"):
        return False
    last = prev.rstrip()[-1]
    return last not in ".!?:\"')]" and (nxt[0].islower() or last == "-")


def _join_paragraphs(prev: str, nxt: str) -> str:
    if prev.endswith("-") and nxt[0].islower():
        return _join_at_hyphen(prev, nxt)
    return prev + " " + nxt


def _description_from(body: str) -> str | None:
    """A one-sentence summary for previews (OKF's `description`): the first sentence
    of the first real paragraph. Short lead-ins ("certifica que:") are skipped when a
    fuller paragraph follows."""
    fallback: str | None = None
    for para in body.split("\n\n"):
        p = para.strip()
        if not p or p.startswith(("#", "|", "!", "\\[", "- ", "* ", "<!--")):
            continue
        p = re.sub(r"\s+", " ", p)
        m = re.match(r"(.+?[.!?])(\s|$)", p)
        sentence = m.group(1) if m else p
        if len(sentence) > 200:
            sentence = sentence[:197].rstrip() + "..."
        if len(sentence.split()) >= 6 and not sentence.endswith(":"):
            return sentence
        fallback = fallback or sentence
    return fallback


def _title_from(body: str) -> str | None:
    """The first heading of the body, when the PDF carries no title of its own."""
    for line in body.split("\n"):
        if line.startswith("#"):
            title = line.lstrip("#").strip()
            if title:
                return title[:200]
    return None


def render_frontmatter(doc: Document, body: str = "") -> str:
    """YAML front matter following the Open Knowledge Format (OKF) v0.2.

    OKF requires `type`; recommends `title`, `description`, `resource`, `tags`;
    records production under `generated` and provenance under `sources`; a
    conversion nobody has reviewed is `status: draft`. TrueDoc's own details
    (checksum, page count, how the conversion ended, confidence, OCR pages,
    hidden text, imprint, the marks nothing took, warnings and the same as
    typed issues) live under the `truedoc` key, which the format allows as
    an extension.
    """
    now = _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()
    resource = doc.metadata.get("resource") or doc.metadata.get("file_name", "")
    source = {"resource": resource, "title": doc.metadata.get("file_name", "")}
    if doc.metadata.get("last_modified"):
        source["last_modified"] = doc.metadata["last_modified"]
    truedoc = {
        "version": __version__,
        "sha256": doc.sha256,
        "pages": len(doc.pages),
        "completion": doc.completion,
        "confidence": doc.metadata.get("confidence", None),
        "language": doc.metadata.get("language") or None,
        "pages_with_ocr": doc.metadata.get("pages_with_ocr", []),
        "turned_pages": doc.metadata.get("turned_pages") or None,
        "ocr_regions": doc.metadata.get("ocr_regions") or None,
        "pages_with_model": doc.metadata.get("pages_with_model") or None,
        "inferred": doc.metadata.get("inferred") or None,
        "corroboration": _corroboration_summary(doc) or None,
        "hidden_text": doc.metadata.get("hidden_text") or None,
        "imprint": doc.metadata.get("imprint") or None,
        "marks_not_placed": doc.metadata.get("marks_not_placed") or None,
        "warnings": list(doc.warnings),
        "issues": [i.as_dict() for i in doc.all_issues()] or None,
    }
    fm = {
        "type": doc.metadata.get("type") or "Document",
        "title": doc.metadata.get("title") or _title_from(body),
        "description": _description_from(body),
        "resource": resource,
        "tags": doc.metadata.get("tags") or None,
        "generated": {"by": f"truedoc/{__version__}", "at": now},
        "status": "draft",
        "sources": [source],
        "truedoc": {k: v for k, v in truedoc.items() if v is not None},
    }
    fm = {k: v for k, v in fm.items() if v is not None}
    return "---\n" + yaml.safe_dump(fm, sort_keys=False, allow_unicode=True).rstrip() + "\n---"
