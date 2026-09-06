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


def assign_reading_order(blocks: list[Block], page_width: float, body_size: float) -> None:
    body = [b for b in blocks if b.kind not in _EXCLUDED]
    excluded = [b for b in blocks if b.kind in _EXCLUDED]
    min_gap = max(4.0, 0.6 * (body_size or 10.0))
    ordered = _cut(body, min_gap, depth=0)
    order = 0
    for b in ordered:
        b.order = order
        order += 1
    # Headers first, footers last, purely for a stable order if anyone renders them.
    for b in sorted(excluded, key=lambda b: (b.bbox.y0, b.bbox.x0)):
        b.order = order
        order += 1


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
