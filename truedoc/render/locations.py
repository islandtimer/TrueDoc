"""The location map: where each passage of a conversion's text came from on the pages, in a file of its own.

The markdown stays exactly as it is; the map says, for every stretch of it, which page and which box it was read from.
A caller that quotes a passage can then point at the page, and at the place on it, and so can a person checking it. The
text has page markers already, but a paragraph that runs over a page break is one paragraph and a marker would cut it
in two; the map gives such a paragraph both of its boxes instead.

**What it holds** (plain JSON, one file per conversion):
- `markdown`: the text the map describes - its length in characters, where the body starts (after any front matter),
  and the SHA-256 of its UTF-8 bytes, so a map is never read against another text. Offsets count characters (Unicode
  code points) of the text as written, lines ending in `\\n`: a file saved with other line endings is read back as text
  first.
- `pages`: each page's number in the file, its size, how it was read (`text layer`, `ocr` or `model`), its state
  (`read`, `empty` - nothing of it in the body - or `unreadable`), the stretch of the text it wrote, and the numbers it
  prints where TrueDoc has read them.
- `blocks`: each paragraph, heading, list item, table, figure or note as written - an identifier, its kind, its
  `range` in the text, and the page and box of every piece of the page that went into it (two for a paragraph joined
  over a page or column break, with each piece's own range).
- `cells`: each table cell - its table's identifier, row, column, spans, whether it is a heading cell, its page and
  box, and its range (`null` for a cell with nothing written in it, marked `empty`).
- `emphasis`: `bold` and `italic`, each a list of ranges - always written, empty when there is none - so that a
  definition whose term is set bold keeps its boundary.

**How a range is found.** The renderer notes, as it writes, which block wrote which part of the body and, where a
paragraph was joined across a break, which piece; nothing it writes changes. The parts are then joined as the renderer
joins them and its last cleanups replayed with its own patterns - stray glyph codes dropped, "…" written "...", a
formula split over two lines joined up - keeping track of where every character goes; when the replay gives the
finished body character for character (`all_found_in_place`), every range is exact. Should it ever not, each part is
looked for in order instead, and one that cannot be found is kept with `range: null`, never guessed. A cell is found
inside its table in the order the table is written; an emphasised word inside its block, whole.
"""
from __future__ import annotations

import hashlib

from truedoc.model import BlockKind, Document


def _box(b, size: tuple[float, float] | None = None) -> list[float] | None:
    """A box in the page's points, top-left origin; clipped to the page, since a picture set to bleed past the edge is
    pointed at by the part of it the page shows."""
    if b is None:
        return None
    x0, y0, x1, y1 = b.x0, b.y0, b.x1, b.y1
    if size is not None:
        w, h = size
        x0, x1 = min(max(x0, 0.0), w), min(max(x1, 0.0), w)
        y0, y1 = min(max(y0, 0.0), h), min(max(y1, 0.0), h)
    return [round(v, 2) for v in (x0, y0, x1, y1)]


def _sub_with_positions(pattern, repl, text: str) -> tuple[str, list[int]]:
    """`pattern.sub(repl, text)`, and where each position of `text` (and its end) lands in the result. Inside a
    replaced stretch a position keeps its distance from the stretch's start, up to the replacement's length: the
    renderer's replacements keep the head of what they replace."""
    out: list[str] = []
    step = [0] * (len(text) + 1)
    last = n = 0
    for m in pattern.finditer(text):
        s, e = m.span()
        for i in range(last, s):
            step[i] = n + (i - last)
        n += s - last
        rep = repl(m)
        for i in range(s, e):
            step[i] = n + min(len(rep), i - s)
        out.append(text[last:s])
        out.append(rep)
        n += len(rep)
        last = e
    for i in range(last, len(text) + 1):
        step[i] = n + (i - last)
    out.append(text[last:])
    return "".join(out), step


def _after_cleanups(pre: str) -> tuple[str, list[int]]:
    """The body the renderer finishes with, rebuilt from its joined parts with its own cleanups, and where each
    position of the joined parts ends up in it."""
    from truedoc.render import okf

    pos = _through_cleanups(pre)
    text = _cleaned(pre)
    for pattern, repl in ((okf._DANGLING_FORMULA, okf._dangling_arithmetic),
                          (okf._SPLIT_FORMULA, lambda m: m.expand(okf._SPLIT_FORMULA_JOIN))):
        text, step = _sub_with_positions(pattern, repl, text)
        pos = [step[p] for p in pos]
    return text, pos


def _cleaned(text: str) -> str:
    """A part's text as the finished body holds it: the renderer's per-character cleanups applied."""
    from truedoc.render import okf

    return okf._RAW_GLYPH_CODES.sub("", text).replace("…", "...")


def _pieces(part: str, texts: list[str]) -> list[tuple[int, int]]:
    """Where each piece joined into one part lies in it, before the cleanups: a joined piece is always the part's tail
    (`_join_paragraphs` writes it after the part, with or without a space, and may drop the hyphen before it)."""
    from truedoc.render.okf import _join_paragraphs

    spans: list[tuple[int, int]] = []
    built = ""
    for i, text in enumerate(texts):
        if i == 0:
            built = text
            spans.append((0, len(text)))
            continue
        built = _join_paragraphs(built, text)
        start = len(built) - len(text)
        s0, e0 = spans[-1]
        spans[-1] = (s0, min(e0, len(built[:start].rstrip(" "))))
        spans.append((start, len(built)))
    return spans if built == part else [(0, len(part))] + [(len(part), len(part))] * (len(texts) - 1)


def _through_cleanups(text: str) -> list[int]:
    """For each character position of `text` (and its end), the position it takes once cleaned. The cleanups work a
    character at a time, so the cleaned text is the characters cleaned one by one."""
    from truedoc.render import okf

    dropped = {m.start() for m in okf._RAW_GLYPH_CODES.finditer(text)}     # a class of single characters
    out, n = [], 0
    for i, ch in enumerate(text):
        out.append(n)
        if i not in dropped:
            n += 3 if ch == "…" else 1
    out.append(n)
    return out


def _find_word(text: str, word: str, start: int) -> int:
    """A word where it stands whole: not the tail of a longer word, nor its head."""
    at = text.find(word, start)
    while at >= 0:
        before = text[at - 1] if at > 0 else " "
        after = text[at + len(word)] if at + len(word) < len(text) else " "
        if not (word[0].isalnum() and before.isalnum()) and not (word[-1].isalnum() and after.isalnum()):
            return at
        at = text.find(word, at + 1)
    return -1


def _cells_written(table):
    """Each cell of a table with the text the renderer writes for it, in the order it writes them."""
    from truedoc.render import okf

    grid = table.grid()
    if table.has_merged or any(c.listing is not None or c.inner is not None for c in table.cells):
        emitted: set[int] = set()
        for r in range(table.n_rows):
            for c in range(table.n_cols):
                cell = grid[r][c]
                if cell is None or id(cell) in emitted:
                    continue
                emitted.add(id(cell))
                if cell.inner is not None:
                    body = okf._render_html_table(cell.inner, cell.inner.grid()).replace("\n", "")
                else:
                    body = okf._listing_html(cell.listing) if cell.listing is not None else okf._html_escape(cell.text)
                yield cell, body
        return
    for r in range(table.n_rows):
        for c in range(table.n_cols):
            cell = grid[r][c]
            if cell is not None and cell.row == r and cell.col == c:
                yield cell, okf._md_cell(cell.text)


def _emphasis(block, text: str, start: int, bold: list, italic: list) -> None:
    """The bold and italic words of a block, found in order in the stretch of text it wrote."""
    from truedoc.render.okf import _escape_dollars

    cursor = 0
    first = {id(bold): len(bold), id(italic): len(italic)}      # runs of this block: only these may be extended
    for line in block.lines:
        for word in line.words:
            if not word.text.strip():
                continue
            wanted = _cleaned(_escape_dollars(word.text))
            if not wanted:
                continue
            at = _find_word(text, wanted, cursor)
            if at < 0:
                continue
            cursor = at + len(wanted)
            for flag, runs in ((word.bold, bold), (word.italic, italic)):
                if not flag:
                    continue
                s, e = start + at, start + cursor
                if len(runs) > first[id(runs)] and runs[-1][1] <= s and not text[runs[-1][1] - start:s - start].strip():
                    runs[-1][1] = e
                else:
                    runs.append([s, e])


def build_map(doc: Document, markdown: str, trace: dict) -> dict:
    """The location map of a rendered document, from the renderer's trace (`render_document(..., trace=...)`)."""
    parts, sources = trace.get("parts") or [], trace.get("sources") or []
    body_start = trace.get("body_start", 0)
    body = markdown[body_start:]
    blocks, cells = [], []
    bold: list[list[int]] = []
    italic: list[list[int]] = []
    page_spans: dict[int, list[int]] = {}
    size = {p.number: (p.width, p.height) for p in doc.pages}

    def box(page, b):
        return _box(b, size.get(page)) if b is not None else None

    # Where each character of each part ends up. The parts joined as the renderer joins them, and its cleanups replayed
    # with its own patterns, give the finished body character for character: then every position is exact. Should the
    # replay ever not give the body, each part is looked for instead, in order, and the map says so.
    pre = "\n\n".join(parts).rstrip()
    rebuilt, pos = _after_cleanups(pre)
    exact = rebuilt == trace.get("body", body.rstrip("\n"))
    starts, total = [], 0
    for part in parts:
        starts.append(total)
        total += len(part) + 2
    cursor = 0
    for n, (part, pieces) in enumerate(zip(parts, sources)):
        if exact:
            def at_char(i, n=n):
                return pos[min(starts[n] + i, len(pre))]
        else:
            cleaned = _cleaned(part)
            found = body.find(cleaned, cursor)
            if found >= 0:
                cursor = found + len(cleaned)
                moved = _through_cleanups(part)

                def at_char(i, found=found, moved=moved):
                    return found + moved[i]
            else:
                at_char = None
        kinds = [b.kind.value if b is not None else ("page-marker" if part.startswith("<!-- page:") else "note")
                 for _, b, _ in pieces]
        entry = {"id": "b%d" % (len(blocks) + 1), "kind": kinds[0], "range": None,
                 "boxes": [{"page": p, "box": box(p, b.bbox if b is not None else None)} for p, b, _ in pieces]}
        blocks.append(entry)
        if at_char is None:
            continue
        entry["range"] = [body_start + at_char(0), body_start + at_char(len(part))]
        spans = _pieces(part, [t for _, _, t in pieces])
        if len(pieces) > 1:
            entry["pieces"] = [{"page": p, "box": box(p, b.bbox if b is not None else None), "range": [body_start + at_char(s), body_start + at_char(e)]}
                               for (p, b, _), (s, e) in zip(pieces, spans)]
        for (page, block, _), (s, e) in zip(pieces, spans):
            start, end = at_char(s), at_char(e)
            if page is not None and block is not None:
                span = page_spans.setdefault(page, [body_start + start, body_start + end])
                span[0] = min(span[0], body_start + start)
                span[1] = max(span[1], body_start + end)
            if block is None:
                continue
            piece_text = body[start:end]
            if block.kind == BlockKind.TABLE and block.table is not None:
                inner = 0
                for cell, written in _cells_written(block.table):
                    hit = piece_text.find(_cleaned(written), inner) if written else -1
                    rng = None
                    if hit >= 0:
                        inner = hit + len(_cleaned(written))
                        rng = [body_start + start + hit, body_start + start + inner]
                    record = {"id": "c%d" % (len(cells) + 1), "table": entry["id"], "row": cell.row, "col": cell.col,
                              "rowspan": cell.rowspan, "colspan": cell.colspan, "header": bool(cell.is_header),
                              "page": page, "box": box(page, cell.bbox), "range": rng}
                    if not written:
                        record["empty"] = True      # nothing written in it, so no range
                    cells.append(record)
            elif block.lines:
                _emphasis(block, piece_text, body_start + start, bold, italic)
    found_exact = exact
    unreadable = {p for i in doc.all_issues() if i.code == "unreadable-pages" for p in (i.pages or [])}
    ocr = set(doc.metadata.get("pages_with_ocr") or [])
    pages = []
    for page in doc.pages:
        read = "model" if page.meta.get("vision_model") else "ocr" if page.number in ocr else "text layer"
        state = "unreadable" if page.number in unreadable else ("read" if page.number in page_spans else "empty")
        pages.append({"page": page.number, "size": [round(page.width, 2), round(page.height, 2)], "read": read,
                      "state": state, "range": page_spans.get(page.number),
                      "printed": list(page.meta.get("printed_numbers") or [])})
    return {
        "format": "truedoc-location-map",
        "version": 1,
        "markdown": {"characters": len(markdown), "body_start": body_start,
                     "sha256": hashlib.sha256(markdown.encode("utf-8")).hexdigest(), "newline": "\n",
                     "all_found_in_place": found_exact},
        "document": {"sha256": doc.sha256, "pages": len(doc.pages)},
        "build": doc.metadata.get("build") or None,
        "pages": pages,
        "blocks": blocks,
        "cells": cells,
        "emphasis": {"bold": bold, "italic": italic},
    }
