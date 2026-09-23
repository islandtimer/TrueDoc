"""Reading order.

A recursive cut that prefers column splits: if the text blocks in a region can
be separated by a clear vertical gap that runs the full height of the region,
split into columns and read left to right. Otherwise peel off the topmost
block that spans the region (a title, a heading, a full-width paragraph) and
recurse above and below it. Figures and tables never block a column split;
they are assigned to the side their centre falls on.
"""

from __future__ import annotations

from truedoc.model import BBox, Block, BlockKind

_NON_TEXT = {BlockKind.FIGURE, BlockKind.TABLE}
_EXCLUDED = {BlockKind.HEADER, BlockKind.FOOTER, BlockKind.PAGE_NUMBER}

# A side label: a few words set in a narrow column at the left, the top of its first line level with the top of the
# first line of the block beside it - a "yes" beside what is covered, a term beside its definition, a step's number
# beside the step. It governs what runs beside and below it, so it is read immediately before that block.
_LABELLED = {BlockKind.TEXT, BlockKind.HEADING, BlockKind.LIST_ITEM, BlockKind.TITLE, BlockKind.CAPTION}
_LABEL_WORDS = 4          # a label is a few words ...
_LABEL_LINES = 4          # ... on a few lines ...
_LABEL_SHARE = 0.18       # ... in a column no wider than this share of the page
_LEVEL = 0.4              # the two tops level within this share of the shorter line's height
_GUTTER = 0.8             # the label stands apart from the block beside it by at least this many body sizes ...
_GUTTER_MAX = 0.4         # ... and by no more than this share of the page
_BODY_WORDS = 4           # the block beside it is running text, not the next of a row of short labels
_LABEL_COLUMN = 0.75      # the label's column holds labels: at least this share of what stands in it is label-shaped ...
_PAIRED = 0.5             # ... and at least this share of those labels head a block beside them


def assign_reading_order(blocks: list[Block], page_width: float, body_size: float) -> None:
    body = [b for b in blocks if b.kind not in _EXCLUDED]
    excluded = [b for b in blocks if b.kind in _EXCLUDED]
    min_gap = max(4.0, 0.6 * (body_size or 10.0))
    ordered = _seat_side_labels(_cut(body, min_gap, depth=0), page_width, body_size or 10.0)
    order = 0
    for b in ordered:
        b.order = order
        order += 1
    # Headers first, footers last, purely for a stable order if anyone renders them.
    for b in sorted(excluded, key=lambda b: (b.bbox.y0, b.bbox.x0)):
        b.order = order
        order += 1


def _words(b: Block) -> int:
    """Words of letters or figures: a tick or a bullet set before a label is not one of its words."""
    return sum(1 for l in b.lines for w in l.words if any(ch.isalnum() for ch in w.text))


def _letters(b: Block) -> int:
    return sum(1 for l in b.lines for w in l.words for ch in w.text if ch.isalpha())


def _label_shaped(b: Block, page_width: float) -> bool:
    """A few words, of letters: a figure alone ("05" beside a stage's title, the parts of a document numbered in a
    row of discs) is as often the ornament of a heading as the head of the text beside it."""
    return (b.kind in _LABELLED and bool(b.lines) and len(b.lines) <= _LABEL_LINES and 1 <= _words(b) <= _LABEL_WORDS
            and _letters(b) >= 2 and b.bbox.width <= _LABEL_SHARE * page_width)


def _seat_side_labels(ordered: list[Block], page_width: float, body_size: float) -> list[Block]:
    """Each side label read immediately before the block it heads.

    The cut reads a label column in one of two wrong ways. A column this narrow is not split off (the guard against a
    gutter of line numbers), so the label is weighed against the wide line beside it by their centres - and a label
    whose box reaches a fraction of a point lower comes after the first line it governs, which then reads as the last
    line of the group above: an exclusion as a thing covered. A wider label column is split off and read whole, every
    label before any of the text they head. Both are repaired by pairing, after the cut: a label goes immediately
    before the block whose first line is level with its own. Only where the label's column holds labels - a
    paper's section heading in its left column, level by chance with a line of the right column, stands among long
    lines of body text and is left where it is.
    """
    labels = [b for b in ordered if _label_shaped(b, page_width)]
    if not labels:
        return ordered
    text = [b for b in ordered if b.kind in _LABELLED and b.lines and _letters(b)]
    lines = [(b, l.bbox) for b in ordered if b.lines for l in b.lines]
    found: dict[int, Block] = {}
    for lab in labels:
        top = lab.lines[0].bbox
        # Not a piece of running text: a word a justified line's wide spaces cut loose has the paragraph's lines
        # crossing it above and below; a label's column is clear over and under it, or holds the next label.
        near = 1.5 * top.height

        def crossing(ln: BBox) -> bool:
            return ln.x0 < lab.bbox.x0 - 1.0 and ln.x1 > lab.bbox.x1 + 1.0

        over = any(b is not lab and crossing(ln) and 0 <= top.y0 - ln.y1 <= near for b, ln in lines)
        under = any(b is not lab and crossing(ln) and 0 <= ln.y0 - lab.bbox.y1 <= near for b, ln in lines)
        if over and under:
            continue
        best = None
        for other in text:
            if other is lab or _label_shaped(other, page_width):
                continue
            first = other.lines[0].bbox
            gap = first.x0 - lab.bbox.x1
            if gap < _GUTTER * body_size or gap > _GUTTER_MAX * page_width:
                continue
            if abs(first.y0 - top.y0) > _LEVEL * min(top.height, first.height):
                continue
            if _words(other) < _BODY_WORDS or other.bbox.width < 2.0 * lab.bbox.width:
                continue
            # Nothing stands between the label and its line: in a row of cells, the next cell, not a later one.
            if any(b is not lab and b is not other and ln.x0 >= lab.bbox.x1 - 1.0 and ln.x1 <= first.x0 + 1.0
                   and min(ln.y1, top.y1) - max(ln.y0, top.y0) > 0.5 * min(ln.height, top.height) for b, ln in lines):
                continue
            if best is None or gap < best[0]:
                best = (gap, other)
        if best is not None:
            found[id(lab)] = best[1]
    # The column must be one of labels, each heading the text beside it. A list set in two columns of short entries
    # has its first entry level with the first entry of the other column, and nothing more: the rest of its entries
    # face nothing.
    partner: dict[int, Block] = {}
    for lab in labels:
        if id(lab) not in found:
            continue
        edge = found[id(lab)].lines[0].bbox.x0
        column = [o for o in text if o.bbox.x1 < edge - 1.0 and o.bbox.x0 <= lab.bbox.x1 and o.bbox.x1 >= lab.bbox.x0]
        shaped = [o for o in column if _label_shaped(o, page_width)]
        if len(shaped) < _LABEL_COLUMN * len(column) or sum(1 for o in shaped if id(o) in found) < _PAIRED * len(shaped):
            continue
        partner[id(lab)] = found[id(lab)]
    if not partner:
        return ordered
    seated = [b for b in ordered if id(b) not in partner]
    for lab in sorted((b for b in ordered if id(b) in partner), key=lambda b: b.bbox.x0):
        seated.insert(seated.index(partner[id(lab)]), lab)
    return seated


def _region(blocks: list[Block]) -> BBox:
    return BBox.union_all(b.bbox for b in blocks)  # type: ignore[return-value]


def _vertical_gap(blocks: list[Block], min_gap: float) -> float | None:
    """Return the x position of the widest full-height vertical gap, or None."""
    text = [b for b in blocks if b.kind not in _NON_TEXT]
    if len(text) < 2:
        return None
    region = _region(blocks)
    xs = sorted(text, key=lambda b: b.bbox.x0)
    # Sweep: maintain the running max x1; a gap opens when next x0 > running max.
    best_gap = 0.0
    best_x = None
    run_x1 = xs[0].bbox.x1
    for b in xs[1:]:
        gap = b.bbox.x0 - run_x1
        if gap >= min_gap and gap > best_gap:
            # Both sides must contain text blocks.
            left = [t for t in text if t.bbox.x1 <= run_x1 + 0.01]
            right = [t for t in text if t.bbox.x0 >= b.bbox.x0 - 0.01]
            if left and right:
                # Avoid splitting off a tiny sliver (e.g. a line number gutter)
                lw = max(t.bbox.width for t in left)
                rw = max(t.bbox.width for t in right)
                if lw >= 0.12 * region.width and rw >= 0.12 * region.width:
                    best_gap = gap
                    best_x = run_x1 + gap / 2.0
        run_x1 = max(run_x1, b.bbox.x1)
    return best_x


def _cut(blocks: list[Block], min_gap: float, depth: int) -> list[Block]:
    if len(blocks) <= 1:
        return list(blocks)
    if depth > 40:
        return sorted(blocks, key=lambda b: (b.bbox.y0, b.bbox.x0))

    region = _region(blocks)

    # 2a. A full-width figure or table does not interrupt the text flow of the
    #     columns around it: order the text without it, then insert it before the
    #     first block that lies entirely below it.
    span_w = 0.6 * region.width
    wide_nontext = [b for b in blocks if b.bbox.width >= span_w and b.kind in _NON_TEXT]
    if wide_nontext and len(wide_nontext) < len(blocks):
        rest = [b for b in blocks if b not in wide_nontext]
        ordered = _cut(rest, min_gap, depth + 1)
        for fig in sorted(wide_nontext, key=lambda b: b.bbox.y0):
            pos = len(ordered)
            for i, b in enumerate(ordered):
                if b.bbox.y0 >= fig.bbox.y1 - 0.25 * b.bbox.height:
                    pos = i
                    break
            ordered.insert(pos, fig)
        return ordered

    # 1. Column split.
    x = _vertical_gap(blocks, min_gap)
    islands: list[Block] = []
    if x is None:
        # A pull quote or boxed note straddling the gutter hides the column gap;
        # taken out, the columns show, and it goes back in beside the column it
        # interrupts rather than cutting both columns in two.
        narrow = [b for b in blocks if b.bbox.width < 0.5 * region.width and b.kind not in _NON_TEXT]
        for cand in sorted(narrow, key=lambda b: -b.bbox.width):
            rest = [o for o in blocks if o is not cand]
            gx = _vertical_gap(rest, min_gap)
            if gx is None or not (cand.bbox.x0 < gx < cand.bbox.x1):
                continue
            # Real columns on both sides, each running above and below the
            # island; two short lines side by side in a letter are not columns.
            left_side = [o for o in rest if o.bbox.cx < gx and o.kind not in _NON_TEXT]
            right_side = [o for o in rest if o.bbox.cx >= gx and o.kind not in _NON_TEXT]
            if not left_side or not right_side or len(left_side) + len(right_side) < 3:
                continue

            def runs_past(side: list[Block]) -> bool:
                # the column reaches above and below the island: as separate blocks
                # or as one block that spans it
                above = any(o.bbox.y1 <= cand.bbox.y0 + 1 for o in side)
                below = any(o.bbox.y0 >= cand.bbox.y1 - 1 for o in side)
                spans = any(o.bbox.y0 <= cand.bbox.y0 + 1 and o.bbox.y1 >= cand.bbox.y1 - 1 for o in side)
                return spans or (above and below)

            if not (runs_past(left_side) and runs_past(right_side)):
                continue
            islands, x = [cand], gx
            break
    if x is not None:
        base = [b for b in blocks if b not in islands]
        left = [b for b in base if b.bbox.cx < x]
        right = [b for b in base if b.bbox.cx >= x]
        if left and right:
            # The island goes after the column it interrupts, never inside a
            # paragraph that continues beneath it (a pull quote's place in the
            # reading order is loose; a broken paragraph is not).
            ordered_left = _cut(left, min_gap, depth + 1) + sorted(islands, key=lambda b: b.bbox.y0)
            return ordered_left + _cut(right, min_gap, depth + 1)

    # 2. Peel off the topmost spanning text block (a title, a heading, a full-width paragraph).
    spanning = [b for b in blocks if b.bbox.width >= span_w]
    if spanning and len(spanning) < len(blocks):
        top = min(spanning, key=lambda b: b.bbox.y0)
        above: list[Block] = []
        below: list[Block] = []
        for b in blocks:
            if b is top:
                continue
            if b.bbox.y1 <= top.bbox.y0 + 0.25 * b.bbox.height:
                above.append(b)
            elif b.bbox.y0 >= top.bbox.y1 - 0.25 * b.bbox.height:
                below.append(b)
            else:
                (above if b.bbox.cy < top.bbox.cy else below).append(b)
        return _cut(above, min_gap, depth + 1) + [top] + _cut(below, min_gap, depth + 1)

    # 3. Horizontal split at the largest vertical whitespace.
    ys = sorted(blocks, key=lambda b: b.bbox.y0)
    best_gap, best_y = 0.0, None
    run_y1 = ys[0].bbox.y1
    for b in ys[1:]:
        gap = b.bbox.y0 - run_y1
        if gap > best_gap and gap > 0.5:
            best_gap, best_y = gap, run_y1 + gap / 2.0
        run_y1 = max(run_y1, b.bbox.y1)
    if best_y is not None:
        top_part = [b for b in blocks if b.bbox.cy < best_y]
        bottom_part = [b for b in blocks if b.bbox.cy >= best_y]
        if top_part and bottom_part:
            return _cut(top_part, min_gap, depth + 1) + _cut(bottom_part, min_gap, depth + 1)

    # 4. Give up: top-to-bottom, left-to-right.
    return sorted(blocks, key=lambda b: (b.bbox.y0, b.bbox.x0))
