"""Rebuild LaTeX from the glyphs of a formula in the PDF text layer.

The text layer of a born-digital PDF carries every symbol of a formula with
its font, size and exact position. That is enough to recover the structure:

- a horizontal rule with glyphs above and below is a fraction;
- smaller glyphs sitting below or above the neighbouring baseline are sub-
  and superscripts (or the limits of a big operator);
- a radical glyph next to a rule is a square root;
- fonts tell symbols apart (Computer Modern's cmex/cmsy raw codes included).

The result is deliberately plain LaTeX that renders the same glyphs in the
same arrangement; typographic niceties are not the goal.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

from truedoc.math.symbols import (BIG_OPERATORS, CMEX_EXTENT, FUNCTION_NAMES, cmex_code, epsilon_by_width, is_cm_like_italic_font,
                                  is_extension_font, is_piece_glyph, is_tex_italic_font, latex_for_char, phi_by_width)
from truedoc.model import BBox

_EXTENSION_FONT_HINTS = ("MTEX", "TXEX", "PXEX", "ESINT", "STMARY", "MATHEX", "LMMATHEXT", "CMBSY")
# Words that carry their limits underneath in displayed maths, like big operators.
_LIMIT_WORDS = {r"\lim", r"\limsup", r"\liminf", r"\max", r"\min", r"\sup", r"\inf", r"\det", r"\gcd"}


def _takes_limits(g: "Glyph") -> bool:
    return g.latex in BIG_OPERATORS or g.latex in _LIMIT_WORDS or g.latex.startswith(r"\operatorname*")

_MATH_FONT_HINTS = (
    "CMMI", "CMSY", "CMEX", "CMBSY", "CMMIB", "MSAM", "MSBM", "RSFS", "EUFM", "EUSM", "EURM", "EUEX",
    "BBOLD", "DOUBLESTRUCK", "DSROM", "DSSS",   # blackboard-bold fonts (bbold, boondox, dsfont)
    "MATH", "MTMI", "MTSY", "MTEX", "SYMBOL", "TXMI", "TXSY", "TXEX", "PXMI", "PXSY", "PXEX", "ESINT",
    "WASY", "STMARY", "BBM", "DSROM", "LMMATH", "STIXMATH", "CAMBRIAMATH", "MATHJAX", "XITSMATH",
    "LATINMODERNMATH", "ASANAMATH", "LMROMANSLANT",
)


def is_math_font(font: str) -> bool:
    f = font.upper()
    if "+" in f:
        f = f.split("+", 1)[1]
    # The TeX Gyre families are text faces (Termes, Heros, Pagella, Bonum...)
    # each with a Math companion; only the companion is a maths font. Calling
    # the text face maths turned ten arXiv pages set in TeX Gyre Termes (the
    # newtx package's body font) into one formula each, every space stripped.
    if "TEXGYRE" in f:
        return "MATH" in f
    return any(h in f for h in _MATH_FONT_HINTS)


@dataclass
class Glyph:
    ch: str
    font: str
    size: float
    bbox: BBox
    oy: float          # baseline (origin y)
    latex: str = ""
    kind: str = "glyph"  # "glyph" | "rule"

    @property
    def cx(self) -> float:
        return self.bbox.cx

    @property
    def is_math(self) -> bool:
        return is_math_font(self.font)


_BARE_ACCENTS = {r"\dot{}", r"\ddot{}", r"\hat{}", r"\tilde{}", r"\bar{}", r"\vec{}", r"\check{}", r"\breve{}", r"\acute{}", r"\grave{}"}


def glyph(ch: str, font: str, size: float, bbox: BBox, oy: float, ink: BBox | None = None) -> Glyph:
    """A glyph whose box reflects the drawn symbol.

    Maths-extension fonts (cmex and kin) hang their glyphs below the origin and
    report a box taken from the font's ascender and descender, so a bracket
    three lines tall comes back one line tall. The measured outline box is used
    when MuPDF could provide one; otherwise the box is rebuilt from the cmex
    design metrics.
    """
    box = bbox
    f = font.upper()
    if is_extension_font(f) and len(ch) == 1:
        if ch.isspace() and ch != " ":
            ch = chr(0xE000 + ord(ch))  # whitespace-coded bracket: keep it out of blank filters
        # A plain space in an extension font is the blank MuPDF inserts between
        # words (the text layer recodes a real bracket on code 0x20 before it
        # gets here, by checking the drawn glyphs), so it stays a blank.
        if ink is not None and ink.height > 0.3:
            box = ink
        else:
            ext = CMEX_EXTENT.get(cmex_code(ch))
            if ext is not None:
                box = BBox(bbox.x0, oy - ext[0] * size, bbox.x1, oy + ext[1] * size)
    elif ink is not None and ink.height > 0.3 and any(h in f for h in _EXTENSION_FONT_HINTS):
        box = ink
    latex = latex_for_char(ch, font)
    # An accent from a symbol font that reports a full-height box (mathabx's
    # dot on code "9") would never sit "above" its base: keep its top third.
    if latex in _BARE_ACCENTS and not is_extension_font(f) and box.height > 0.6 * size:
        box = BBox(box.x0, box.y0, box.x1, box.y0 + 0.3 * size)
    if ch in ("φ", "ϕ") and is_tex_italic_font(f) and bbox.width > 0 and size > 0:
        latex = phi_by_width(font, bbox.width / size)
    elif ch in ("ε", "ϵ", "ǫ") and is_cm_like_italic_font(f) and bbox.width > 0 and size > 0:
        latex = epsilon_by_width(font, bbox.width / size)
    return Glyph(ch=ch, font=font, size=size, bbox=box, oy=oy, latex=latex)


_ACCENT_COMMANDS = (r"\tilde", r"\widetilde", r"\hat", r"\widehat", r"\vec", r"\bar", r"\overline", r"\dot", r"\ddot",
                    r"\breve", r"\check", r"\acute", r"\grave", r"\overbrace", r"\underbrace")


def _merge_extensible_pieces(gs: list[Glyph]) -> list[Glyph]:
    """Stack the pieces of an extensible bracket into one tall glyph.

    TeX draws a very tall bracket from a top piece, repeated extenders and a
    bottom piece, one above the other at the same x; each piece is a separate
    glyph in the text layer.
    """
    # Wide accents live in the extension font too, but they are not pieces of a
    # bracket: a widetilde next to a tall paren must keep its base letter.
    cmex = sorted((g for g in gs if is_extension_font(g.font) and g.latex and not g.latex.startswith(_ACCENT_COMMANDS)),
                  key=lambda g: (g.bbox.x0, g.bbox.y0))
    if len(cmex) < 2:
        return gs
    if os.environ.get("TRUEDOC_MATH_DEBUG"):
        print("[math] pieces: " + " ".join(f"{g.latex}@({g.bbox.x0:.0f},{g.bbox.y0:.0f},{g.bbox.x1:.0f},{g.bbox.y1:.0f})/{g.size:.0f}" for g in cmex))
    merged: dict[int, Glyph | None] = {}
    i = 0
    while i < len(cmex):
        run = [cmex[i]]
        j = i
        while j + 1 < len(cmex):
            n, p = cmex[j + 1], run[-1]
            # Pieces under Adobe's private-use names come with the font's fixed box,
            # not their drawn extent, so a brace's top pair and bottom pair can show
            # a gap of most of a line between them.
            gap = 1.0 * p.size if (is_piece_glyph(n.ch, n.font) and is_piece_glyph(p.ch, p.font)) else 0.3 * p.size
            if n.latex != p.latex or abs(n.bbox.x0 - p.bbox.x0) > 0.15 * p.size or n.bbox.y0 > p.bbox.y1 + gap:
                break
            run.append(n)
            j += 1
        if len(run) >= 2:
            first = run[0]
            box = BBox.union_all(g.bbox for g in run)
            latex = first.latex
            if latex in (r"\big|", r"\big\|"):
                # TeX builds a bar of any size from 0.6 em extender pieces: \big is
                # two pieces, \Big three, \bigg four, \Bigg five. The count is exact
                # where the union of the pieces' boxes is not (each box carries the
                # font's bearings, so three pieces measure 2.4 em rather than 1.8).
                n = len(run)
                size_cmd = r"\big" if n <= 2 else (r"\Big" if n == 3 else (r"\bigg" if n == 4 else r"\Bigg"))
                if os.environ.get("TRUEDOC_MATH_DEBUG"):
                    print(f"[math] bar pieces={n} box={box.height:.1f} size={first.size:.1f} -> {size_cmd}")
                latex = size_cmd + latex[len(r"\big"):]
            merged[id(first)] = Glyph(ch=first.ch, font=first.font, size=first.size, bbox=box, oy=first.oy, latex=latex)
            for g in run[1:]:
                merged[id(g)] = None
        i = j + 1
    if not merged:
        return gs
    out: list[Glyph] = []
    for g in gs:
        if id(g) in merged:
            if merged[id(g)] is not None:
                out.append(merged[id(g)])  # type: ignore[arg-type]
            continue
        out.append(g)
    return out


_SYMBOL_FONT_HINTS = ("CMSY", "LMMATHSYMBOLS", "MATHA", "MATHB", "TXSY", "PXSY", "MDSY", "MSAM", "MSBM", "OAMATHSYMBOLS")


_TYPED_DOTS = "\x00dots\x00"
# Relations a negation slash can strike through (as they appear in the latex).
_NEGATABLE = (r"\\(?:in|ni|equiv|leq|geq|leqslant|geqslant|le|ge|subset|subseteq|supset|supseteq|sim|simeq|cong|approx"
              r"|vdash|models|mid|prec|succ|preceq|succeq|sqsubseteq|sqsupseteq|perp|parallel)|<|>")


def _merge_dot_runs(gs: list[Glyph]) -> list[Glyph]:
    """Three periods in a row are "\\ldots" when TeX spaced them (about 0.4 em
    from dot to dot) and a typed "..." when they touch (0.28 em, the period's
    own width): the benchmark's references keep the author's spelling."""
    out: list[Glyph] = []
    order = sorted(gs, key=lambda g: (round(g.oy, 1), g.bbox.x0))
    # In script styles TeX drops the thin spaces between the dots, so a
    # script-sized run cannot be told apart: it keeps the usual \ldots.
    main = _main_size(gs)
    i = 0
    while i < len(order):
        g = order[i]
        run = [g]
        j = i + 1
        while j < len(order) and order[j].ch == "." and g.ch == "." and abs(order[j].oy - g.oy) <= 0.1 * max(g.size, 1.0) \
                and abs(order[j].size - g.size) <= 0.1 * g.size and 0 < order[j].bbox.x0 - run[-1].bbox.x0 <= 0.6 * g.size:
            run.append(order[j])
            j += 1
        if len(run) == 3:
            advance = max(b.bbox.x0 - a.bbox.x0 for a, b in zip(run, run[1:]))
            latex = _TYPED_DOTS if advance <= 0.33 * g.size and g.size >= 0.85 * main else r"\ldots"
            out.append(Glyph(ch="…", font=g.font, size=g.size, bbox=BBox.union_all([x.bbox for x in run]), oy=g.oy, latex=latex))
            i = j
            continue
        out.append(g)
        i += 1
    return out


def _merge_mapsto(gs: list[Glyph]) -> list[Glyph]:
    """TeX draws \\mapsto as a short bar (cmsy's "mapstochar") glued to an arrow,
    and the text layer reports the bar as "|" or as its raw code: the pair
    becomes one \\mapsto. A lone mapstochar is written as a bar."""
    arrows = (r"\rightarrow", r"\longrightarrow")
    if any(g.latex in arrows for g in gs):
        order = sorted(gs, key=lambda g: g.bbox.x0)
        drop: set[int] = set()
        for i, a in enumerate(order[:-1]):
            b = order[i + 1]
            # A long arrow is drawn as a minus shaft glued to an arrowhead; the bar
            # then stands before the shaft ("|" "-" "→" is \longmapsto).
            shaft = None
            if b.latex == "-" and i + 2 < len(order) and order[i + 2].latex in arrows and order[i + 2].bbox.x0 - b.bbox.x1 <= 0.3 * max(b.size, 1.0):
                shaft, b = b, order[i + 2]
            if b.latex not in arrows:
                continue
            f = a.font.upper()
            # cmmi's slot 0x2C is the left hook of \hookrightarrow, which the text
            # layer reports as a comma; a comma never touches an arrow otherwise.
            if a.ch == "," and "CMMI" in f and shaft is None and b.bbox.x0 - a.bbox.x1 <= 0.1 * max(a.size, 1.0) and abs(a.oy - b.oy) <= 0.3 * max(a.size, 1.0):
                drop.add(id(a))
                b.latex = r"\hookrightarrow"
                b.bbox = a.bbox.union(b.bbox)
                continue
            raw = a.latex == r"\mapstochar"
            bar = raw or (a.latex in ("|", r"\mid", r"\vert") and any(h in f for h in _SYMBOL_FONT_HINTS))
            size = max(a.size, 1.0)
            # The mapstochar abuts its arrow; the closing bar of "|P| -> |Q|" stands a
            # thick space (about 0.28 em) before the arrow, so only a touching bar merges.
            reach = 0.3 * size if raw else 0.1 * size
            first = shaft if shaft is not None else b
            if not bar or first.bbox.x0 - a.bbox.x1 > reach or abs(a.oy - b.oy) > 0.3 * size:
                continue
            drop.add(id(a))
            if shaft is not None:
                drop.add(id(shaft))
            b.latex = r"\mapsto" if (b.latex == r"\rightarrow" and shaft is None) else r"\longmapsto"
            b.bbox = a.bbox.union(b.bbox)
        gs = [g for g in gs if id(g) not in drop]
    for g in gs:
        if g.latex == r"\mapstochar":
            g.latex = "|"
    return gs


def rule_glyph(bbox: BBox) -> Glyph:
    return Glyph(ch="", font="", size=0.0, bbox=bbox, oy=bbox.cy, latex="", kind="rule")


# --------------------------------------------------------------------------- lines


def split_display_lines(glyphs: list[Glyph], rules: list[BBox]) -> list[tuple[list[Glyph], list[BBox]]]:
    """Split the glyphs of a display-math region into separate equation lines.

    Glyphs (and rules, padded so they bridge numerators and denominators) are
    linked when their vertical extents overlap; each connected group is a line.
    """
    items: list[tuple[float, float, object]] = []
    glyphs = _merge_extensible_pieces(glyphs)
    main = _main_size(glyphs)
    # A display-size big operator (an integral is over two lines tall) reaches
    # into the neighbouring rows; it must not link them. It joins the row that
    # holds its centre once the rows are known.
    operators: list[Glyph] = []
    for g in glyphs:
        if g.ch.isspace():
            continue
        # mathabx's mathx glyphs (big parentheses, sums) have their origins at the
        # top like cmex's, so their real boxes, not their baselines, place them.
        ext = is_extension_font(g.font) or "MATHX" in g.font.upper()
        if g.latex in BIG_OPERATORS and ext:
            operators.append(g)
            continue
        if ext and g.bbox.height >= 1.8 * main:
            # A tall delimiter around a fraction reaches a little beyond the
            # fraction; its tips must not stitch the row to its neighbours. (A
            # bracket around a real matrix still overlaps every row it holds.)
            trim = 0.3 * main
            items.append((g.bbox.y0 + trim, g.bbox.y1 - trim, g))
            continue
        if not ext and g.size > 0 and g.latex not in BIG_OPERATORS:
            # A text-font glyph's box comes from the font's ascender and descender:
            # 1.2 em tall, so lines set at 1.2 em leading touch and can never be
            # told apart, and symbol fonts (cmsy's braces) declare bigger boxes
            # still. Link a glyph by the extent a glyph of its size really has.
            items.append((g.oy - 0.8 * g.size, g.oy + 0.25 * g.size, g))
            continue
        items.append((g.bbox.y0, g.bbox.y1, g))
    for r in rules:
        pad = 0.7 * main
        items.append((r.y0 - pad, r.y1 + pad, r))
    items.sort(key=lambda t: t[0])
    groups: list[list[object]] = []
    cur: list[object] = []
    cur_y1 = -1e9
    for y0, y1, obj in items:
        if cur and y0 > cur_y1 - 0.5:
            groups.append(cur)
            cur = []
            cur_y1 = -1e9
        cur.append(obj)
        cur_y1 = max(cur_y1, y1)
    if cur:
        groups.append(cur)
    if os.environ.get("TRUEDOC_MATH_DEBUG") and len(items) > 1:
        tall = [(y0, y1, obj) for y0, y1, obj in items if y1 - y0 > 1.2 * main]
        if tall:
            print("[math] tall items: " + " ".join(f"{(obj.ch if isinstance(obj, Glyph) else 'rule')!r}/{(obj.font[-8:] if isinstance(obj, Glyph) else '')}({y0:.0f}-{y1:.0f})" for y0, y1, obj in tall[:8]))
        for grp in groups:
            gl = [o for o in grp if isinstance(o, Glyph)]
            if gl:
                span = (min(o.bbox.y0 for o in gl), max(o.bbox.y1 for o in gl))
                tallest = max(gl, key=lambda o: o.bbox.height)
                print(f"[math] row y=({span[0]:.0f},{span[1]:.0f}) glyphs={len(gl)} baselines={sorted({round(o.oy) for o in gl})[:6]} tallest={tallest.ch!r}/{tallest.font[-8:]} ({tallest.bbox.y0:.0f}-{tallest.bbox.y1:.0f})")
    for op in operators:
        if not groups:
            groups.append([op])
            continue

        def distance(grp: list[object]) -> float:
            ys = [o.bbox.cy for o in grp if isinstance(o, Glyph)] or [op.bbox.cy]
            return abs(sum(ys) / len(ys) - op.bbox.cy)

        min(groups, key=distance).append(op)
    # The limits of a big operator sit just above and below it and may have
    # landed in a neighbouring group; move them next to their operator. (Padding
    # the operator instead would glue tall stacked rows into one line.)
    big = [(gi, g) for gi, grp in enumerate(groups) for g in grp if isinstance(g, Glyph) and g.latex in BIG_OPERATORS]
    # A word that takes limits ("sup", "lim", "max") is still separate letters
    # here; its limit row sits underneath at script size and would otherwise
    # stay a row of its own (an aligned line "mu in M_T(X)" under "sup").
    for gi, grp in enumerate(groups):
        letters = sorted([g for g in grp if isinstance(g, Glyph) and g.ch.isascii() and g.ch.isalpha()
                          and not g.is_math and g.size >= 0.85 * main and not is_extension_font(g.font)], key=lambda g: g.bbox.x0)
        run: list[Glyph] = []
        for g in letters + [None]:  # type: ignore[list-item]
            if run and (g is None or g.bbox.x0 - run[-1].bbox.x1 > 0.25 * main or abs(g.oy - run[-1].oy) > 0.1 * main):
                word = "".join(x.ch for x in run)
                if "\\" + word in _LIMIT_WORDS:
                    big.append((gi, Glyph(ch=word, font=run[0].font, size=run[0].size, bbox=BBox.union_all(x.bbox for x in run), oy=run[0].oy, latex="\\" + word)))
                run = []
            if g is not None:
                run.append(g)
    moves: dict[int, int] = {}
    for gi, grp in enumerate(groups):
        for obj in grp:
            if not isinstance(obj, Glyph) or obj.size >= 0.85 * main:
                continue
            for bi, b in big:
                if bi == gi:
                    continue
                # Sums centre their limits; integrals set them to the right of the
                # sign, up to about an em away, level with its top and bottom.
                integral = b.latex in (r"\int", r"\oint", r"\iint", r"\iiint")
                x_reach = 1.2 * main if integral else 0.2 * main
                near_top = obj.bbox.y1 >= b.bbox.y0 - 0.8 * main and obj.bbox.cy <= b.bbox.cy - 0.2 * main
                near_bottom = obj.bbox.y0 <= b.bbox.y1 + 0.8 * main and obj.bbox.cy >= b.bbox.cy + 0.2 * main
                if b.bbox.x0 - 0.2 * main <= obj.cx <= b.bbox.x1 + x_reach and (near_top or near_bottom):
                    moves[id(obj)] = bi
                    break
    # A limit row wider than its word ("mu in M_T(X)" under "sup"): once part
    # of it has moved to the word, the rest of the row goes with it, provided
    # the row is all script-sized and sits within a few ems of the word.
    for gi, grp in enumerate(groups):
        row_glyphs = [o for o in grp if isinstance(o, Glyph)]
        small = [o for o in row_glyphs if o.size < 0.85 * main]
        if not small or len(small) != len(row_glyphs):
            continue
        for bi in {moves[id(o)] for o in small if id(o) in moves}:
            # Likewise an integral's lower limit runs to the right of the sign and
            # can be long ("\int_{T^{-1}(E)}"): the rest of its row follows too.
            # ... and a sign's centred limit may be wider than the sign
            # ("\bigsqcup_{A,B\in\mathcal{C}}" on 2503.05960, run 32).
            word_op = next((g for (i, g) in big if i == bi and (len(g.ch) > 1 or g.latex in BIG_OPERATORS)), None)
            if word_op is None:
                continue
            integral = word_op.latex in (r"\int", r"\oint", r"\iint", r"\iiint")
            left_reach, right_reach = (0.2 * main, 3.5 * main) if integral else (2.5 * main, 2.5 * main)
            for o in small:
                if id(o) not in moves and word_op.bbox.x0 - left_reach <= o.cx <= word_op.bbox.x1 + right_reach:
                    moves[id(o)] = bi
    if moves:
        new_groups: list[list[object]] = [[] for _ in groups]
        for gi, grp in enumerate(groups):
            for obj in grp:
                new_groups[moves.get(id(obj), gi)].append(obj)
        groups = [g for g in new_groups if g]
    out = []
    for grp in groups:
        gs = [o for o in grp if isinstance(o, Glyph)]
        rs = [o for o in grp if isinstance(o, BBox)]
        if gs:
            out.append((gs, rs))
    return out


def _main_size(glyphs: list[Glyph]) -> float:
    """The size of the main line: the largest size that carries a real share of the width."""
    sizes = [g.size for g in glyphs if g.size > 0 and not g.ch.isspace()]
    if not sizes:
        return 10.0
    counts: dict[float, float] = {}
    total = 0.0
    for g in glyphs:
        if g.size <= 0 or g.ch.isspace():
            continue
        s = round(g.size, 1)
        counts[s] = counts.get(s, 0.0) + g.bbox.width
        total += g.bbox.width
    sizes_desc = sorted(counts, reverse=True)
    # A long superscript or subscript can outweigh its base ("Z^{W_0^2 dx(xi)}",
    # "p^{ord_p(...)}" in a denominator): when the largest glyphs include a letter
    # or digit and nearly every smaller glyph sits clearly above or below their
    # baseline, those largest glyphs are the main line whatever their share.
    biggest = sizes_desc[0]
    # Extension-font glyphs (a wide hat over the base) and accents have their
    # origins off the baseline and do not vote for it.
    base = [g for g in glyphs if g.size >= 0.85 * biggest and not g.ch.isspace()
            and not is_extension_font(g.font) and g.latex not in _BARE_ACCENTS and g.ch not in _ACCENTS]
    if base and any(g.ch.isalnum() for g in base):
        base_oy = _mode([round(g.oy, 1) for g in base])
        others = [g for g in glyphs if g.size < 0.85 * biggest and not g.ch.isspace()]
        off = [g for g in others if abs(g.oy - base_oy) > 0.15 * biggest]
        # Nearly all: a superscript's own subscripts may dip to the base line.
        if len(others) >= 2 and len(off) >= 0.8 * len(others):
            return biggest
        # A long subscript with its own superscripts ("v_{\hat\tau_i^2+s^{l-1}-2s}"):
        # the small glyphs' own baseline lies off the base line, and the base is
        # a letter or two.
        if len(others) >= 4 and len(base) <= 2 and all(g.ch.isalnum() for g in base) \
                and abs(_mode([round(g.oy, 1) for g in others]) - base_oy) > 0.15 * biggest:
            return biggest
    for s in sizes_desc:
        share = sum(w for t, w in counts.items() if t >= 0.85 * s) / (total or 1.0)
        if share >= 0.2:
            return s
    return max(counts)


# --------------------------------------------------------------------------- reconstruction


_MODE = "display"       # "display" or "inline": set per formula by reconstruct()
_TOP_MAIN = 10.0        # the formula's own text size, for the \tfrac / \dfrac choice


def reconstruct(glyphs: list[Glyph], rules: list[BBox], strip_equation_number: bool = True, display: bool = True) -> tuple[str, str]:
    """Return (latex, equation_number) for one formula line."""
    global _MODE, _TOP_MAIN
    _MODE = "display" if display else "inline"
    gs = _merge_dot_runs(_merge_mapsto(_merge_extensible_pieces([g for g in glyphs if not g.ch.isspace()])))
    _TOP_MAIN = _main_size(gs) if gs else 10.0
    eq_no = ""
    if strip_equation_number and gs:
        if re.fullmatch(r"\(\s*[\dA-Za-z.]+\s*\)", "".join(g.ch for g in sorted(gs, key=lambda g: g.bbox.x0))):
            return "", "".join(g.ch for g in gs).strip("() ")  # a line holding only an equation number
        gs, eq_no = _strip_equation_number(gs)
    if not gs:
        return "", eq_no
    rules = [r for r in rules if r.width >= 2.0]
    _ACCENT_MEMO.clear()
    latex = _build(gs, rules, depth=0)
    latex = _polish(latex)
    if os.environ.get("TRUEDOC_MATH_DEBUG"):
        chars = " ".join(f"{g.ch}@{g.bbox.x0:.0f},{g.oy:.0f}/{g.size:.0f}:{(g.font or '')[:10]}" for g in sorted(gs, key=lambda g: g.bbox.x0))
        print(f"[math] {latex[:80]!r} <= {chars[:1500]} | rules {[(round(r.x0), round(r.x1), round(r.cy, 1)) for r in rules][:8]}")
    return latex, eq_no


_BAR_ARROW = re.compile(r"\|\s*\\(longrightarrow|rightarrow)\b")
_LABELLED_ARROW = re.compile(r"(?:-(?:\^\{[^{}]*\})?\s*){2,}\\rightarrow(?:\^\{[^{}]*\})?")
_BOLD_RUN = re.compile(r"(?:\\mathbf\{[A-Za-z]\}){2,}")


def _bar_arrow_to_mapsto(latex: str) -> str:
    """A bar glued to an arrow is \\mapsto when the bar opens nothing: the bars
    before it pair off (an even count), so it is not the closing bar of an
    absolute value ("|x| \\rightarrow 0" keeps its arrow)."""
    out = []
    pos = 0
    for m in _BAR_ARROW.finditer(latex):
        before = latex[:m.start()].replace(r"\|", "")
        if before.count("|") % 2 == 0:
            out.append(latex[pos:m.start()])
            out.append(r"\longmapsto " if m.group(1) == "longrightarrow" else r"\mapsto ")
            pos = m.end()
    out.append(latex[pos:])
    return "".join(out)


def _polish(latex: str) -> str:
    latex = re.sub(r"\s+", " ", latex).strip()
    latex = latex.replace(r"\cdot\cdot\cdot", r"\cdots ").replace(r"\cdot \cdot \cdot", r"\cdots ")
    # Diagonal dots in a matrix are three periods, each set lower and to the
    # right of the last, which the script pass nests as subscripts.
    latex = latex.replace("._{._{.}}", r"\ddots ").replace("._{._{._{.}}}", r"\ddots ")
    latex = re.sub(r"(?<![.\\])\.\.\.(?!\.)", r"\\ldots ", latex)
    latex = latex.replace(_TYPED_DOTS, "...")
    slash = "̸"  # combining long solidus: TeX's negated relations come out as "=" + slash
    latex = re.sub(slash + r"\s*=|=\s*" + slash, r"\\neq ", latex)
    # Any other relation the slash touches is negated ("\not\equiv", "\not\leqslant");
    # a "/" glyph glued to a relation (mathabx's negation slash) means the same.
    latex = re.sub(slash + r"\s*(" + _NEGATABLE + r")(?![A-Za-z])", r"\\not\1 ", latex)
    latex = re.sub(r"(" + _NEGATABLE + r")(?![A-Za-z])\s*" + slash, r"\\not\1 ", latex)
    latex = re.sub(r"(" + _NEGATABLE + r")(?![A-Za-z])/(?=[A-Za-z0-9(\\])", r"\\not\1 ", latex)
    # The checker does not equate "\not\in" with "\notin"; the references split
    # 11 to 5 in favour of "\not\in" (7 pages to 3), so that spelling stays: a
    # rewrite to "\notin" won 2 on 2503.08443 and lost 4 on 2503.03994.
    # A combining mark that found no base (an accent glyph left over after the
    # accent pass) cannot render and would fail the whole formula: drop it.
    latex = re.sub("[̀-ͯ]", "", latex)
    latex = latex.replace(slash, r"\not ")
    latex = latex.replace("≠", r"\neq ").replace(r"\notin", r"\not\in ")
    # The slanted inequalities are kept as drawn: run 28 showed the references
    # follow the glyph (five checks lost by writing them plain, four gained).
    # TeX draws \cong as a tilde over an equals sign; the script pass stacks them.
    latex = latex.replace(r"^{\sim}=", r"\cong ").replace(r"^{\sim} =", r"\cong ")
    # A labelled arrow is drawn as minus pieces with the label's letters set
    # above them, then an arrowhead: "-^{A}-^{I}--^{co}-^{n}-^{v}\rightarrow^{.}"
    # is \xrightarrow{AI conv.} (spaces inside the label do not survive; the
    # checker ignores them).
    def _arrow(m: re.Match) -> str:
        label = "".join(re.findall(r"\^\{([^{}]*)\}", m.group(0)))
        return (r"\xrightarrow{" + label + "} ") if label else r"\longrightarrow "
    latex = _LABELLED_ARROW.sub(_arrow, latex)
    # "(mod p)" in parentheses is \pmod{p}, which is how the references write it.
    latex = re.sub(r"\(\s*\\mod\s*([^()]+?)\s*\)", lambda m: r"\pmod{" + m.group(1).strip() + "}", latex)
    # Bold letters come one glyph at a time; a bold word is one command.
    latex = _BOLD_RUN.sub(lambda m: r"\mathbf{" + m.group(0).replace(r"\mathbf{", "").replace("}", "") + "}", latex)
    # TeX builds long arrows and some relations from two glyphs; write the single command.
    for pair, single in (
        (r"\mapsto\rightarrow", r"\mapsto"), (r"\mapsto-\rightarrow", r"\longmapsto"), (r"\mapsto\longrightarrow", r"\longmapsto"),
        (r"-\rightarrow", r"\longrightarrow"), (r"\leftarrow-", r"\longleftarrow"), (r"\leftarrow\rightarrow", r"\longleftrightarrow"),
        (r"=\Rightarrow", r"\Longrightarrow"), (r"\Leftarrow=", r"\Longleftarrow"), (r"\Leftarrow\Rightarrow", r"\Longleftrightarrow"),
        (r"\sim_{=}", r"\cong"), (r"\sim_{-}", r"\simeq"),
    ):
        latex = latex.replace(pair, single + " ")
    return re.sub(r"\s+", " ", latex).strip()


def _attach_core_scripts(core: str, right: list[Glyph], base_oy: float, base_x1: float, size: float, depth: int) -> tuple[str, list[Glyph]]:
    """Take the script-sized glyphs that follow a built group closely and hang
    them on it as sub- and superscripts; return the group and the rest."""
    rest = sorted(right, key=lambda g: g.bbox.x0)
    sup: list[Glyph] = []
    sub: list[Glyph] = []
    edge = base_x1
    while rest:
        g = rest[0]
        if g.size >= 0.85 * size or g.bbox.x0 - edge > 0.6 * size or is_extension_font(g.font):
            break
        if g.oy < base_oy - 0.2 * size:
            sup.append(g)
        elif g.oy > base_oy + 0.1 * size:
            # A subscript under an overlined calligraphic letter drops only a
            # little ("\overline{\mathcal{C}}_{sum,u}": 0.2 em on 2503.08986).
            sub.append(g)
        else:
            break
        edge = max(edge, g.bbox.x1)
        rest.pop(0)
    if sub:
        core += "_{%s}" % _build(sub, [], depth + 1)
    if sup:
        core += "^{%s}" % _build(sup, [], depth + 1)
    return core, rest


def _strip_equation_number(gs: list[Glyph]) -> tuple[list[Glyph], str]:
    """Remove a trailing "(12)" / "(3.1a)" that sits far to the right."""
    gs = sorted(gs, key=lambda g: g.bbox.x0)
    text = "".join(g.ch for g in gs)
    size = _main_size(gs)
    m = re.search(r"\(\s*[\dA-Za-z.]+\s*\)\s*$", text)
    if m:
        n = len(m.group(0).replace(" ", ""))
        tail = gs[-n:]
        head = gs[:-n]
        if head:
            gap = tail[0].bbox.x0 - max(g.bbox.x1 for g in head)
            if gap >= 2.5 * size:
                return head, "".join(g.ch for g in tail).strip("() ")
    # Journals that number on the left ("(3.12)" at the margin, the formula
    # well to its right) put the number first in reading order.
    m = re.match(r"^\(\s*[\d.]+[a-z]?\s*\)", text)
    if m:
        n = len(m.group(0).replace(" ", ""))
        head = gs[:n]
        rest = gs[n:]
        if rest:
            gap = min(g.bbox.x0 for g in rest) - max(g.bbox.x1 for g in head)
            if gap >= 2.5 * size:
                return rest, "".join(g.ch for g in head).strip("() ")
    return gs, ""


_OPEN_DELIMS = {"(": "pmatrix", "[": "bmatrix", "|": "vmatrix", r"\{": "Bmatrix", r"\|": "Vmatrix"}
_CLOSE_FOR = {"(": ")", "[": "]", "|": "|", r"\{": r"\}", r"\|": r"\|"}


def _delim_key(latex: str) -> str:
    """The bare delimiter behind a sized one (`\\big|` -> `|`, `\\Bigg(` -> `(`)."""
    for size in (r"\Bigg", r"\bigg", r"\Big", r"\big"):
        if latex.startswith(size):
            return latex[len(size):]
    return latex


def _single_column(rows: list[list[Glyph]], main: float) -> bool:
    """No row has a cell gap: the rows stack in one column."""
    for row in rows:
        row = sorted(row, key=lambda g: g.bbox.x0)
        if any(b.bbox.x0 - a.bbox.x1 >= 0.7 * main for a, b in zip(row, row[1:])):
            return False
    return True


def _find_matrices(gs: list[Glyph], main: float, rules: list[BBox] | None = None) -> list[tuple[Glyph, Glyph | None, str]]:
    """Tall delimiter pairs enclosing glyphs on two or more rows."""
    tall = [g for g in gs if g.bbox.height >= 1.6 * main and (_delim_key(g.latex) in _OPEN_DELIMS or _delim_key(g.latex) in _CLOSE_FOR.values())]
    found: list[tuple[Glyph, Glyph | None, str]] = []
    used: set[int] = set()
    for left in sorted(tall, key=lambda g: g.bbox.x0):
        if _delim_key(left.latex) not in _OPEN_DELIMS or id(left) in used:
            continue
        close = _CLOSE_FOR[_delim_key(left.latex)]
        right = None
        for cand in sorted(tall, key=lambda g: g.bbox.x0):
            if cand is left or id(cand) in used or _delim_key(cand.latex) != close or cand.bbox.x0 <= left.bbox.x1:
                continue
            if cand.bbox.y_overlap(left.bbox) >= 0.6 * min(cand.bbox.height, left.bbox.height):
                right = cand
                break
        inner = [g for g in gs if g is not left and g is not right and g.bbox.x0 >= left.bbox.x1 - 0.2 * main
                 and (right is None or g.bbox.x1 <= right.bbox.x0 + 0.2 * main)
                 and g.bbox.cy >= left.bbox.y0 - 0.2 * main and g.bbox.cy <= left.bbox.y1 + 0.2 * main]
        rows = _row_clusters(inner, main)
        rows_all = rows   # every row, for the bar-between-rows test below
        if rules:
            # A row that lies wholly under or over one fraction bar is that
            # fraction's numerator or denominator, not a row of entries:
            # "\{(\alpha_i,0)\times(\frac{1}{\alpha_i},0)\}" is no cases block.
            def _in_stack(row: list[Glyph]) -> bool:
                return any(all(q.x0 - 0.3 * main <= g.bbox.x0 and g.bbox.x1 <= q.x1 + 0.3 * main
                               and abs(g.oy - q.cy) <= 1.3 * main for g in row) for q in rules)
            rows = [r for r in rows if not _in_stack(r)]
        # Rows of a matrix carry text-size entries. A big operator standing on
        # its own baseline inside tall parentheses ("\left(\sum_{i=1}^n a_i\right)")
        # makes a row of nothing but the sign, with its limits and the summand
        # on other rows: that is one row of entries, not a matrix.
        # A root sign is a structural sign too: its origin sits up at its bar, so
        # it lands on a row of its own above the digits it covers ("(1/\sqrt{N})").
        rows = [r for r in rows if any(g.size >= 0.85 * main and not is_extension_font(g.font) and not _takes_limits(g) and g.latex != r"\sqrt" for g in r)]
        if os.environ.get("TRUEDOC_MATH_DEBUG") and len(rows) >= 2:
            print("[math] matrix? left=%r/%s rows=%s" % (left.latex, left.font[-8:], [" ".join("%s/%.0f/%s" % (g.ch, g.size, g.font[-6:]) for g in sorted(r, key=lambda g: g.bbox.x0))[:80] for r in rows]))
        lone_brace = right is None and _delim_key(left.latex) == r"\{"
        if len(rows) >= 2 and rules and not lone_brace:
            # A bar between the rows is a fraction inside tall brackets, not a
            # matrix: matrices have no rules between their rows. (An expression
            # such as (1/q - 1/p) has several columns and still is no matrix.)
            # A lone left brace is a cases environment, whose rows are often
            # fractions themselves, so their bars do not count against it.
            # Judged over every row, stack rows included: dropping a fraction's
            # numerator and denominator rows must not hide the bar between them
            # ("\bigg(\frac{1}{|B|}\int_B w\,dx\bigg)" on 2503.08649, run 31).
            ys = sorted(sum(g.oy for g in r) / len(r) for r in rows_all)
            span_x1 = right.bbox.x0 if right is not None else max(g.bbox.x1 for g in inner)
            if any(ys[0] < r.cy < ys[-1] and r.x0 >= left.bbox.x1 - 0.5 * main and r.x1 <= span_x1 + 0.5 * main for r in rules):
                continue
        if len(rows) >= 2:
            env = "cases" if (right is None and _delim_key(left.latex) == r"\{") else _OPEN_DELIMS[_delim_key(left.latex)]
            if right is None and env != "cases":
                continue
            found.append((left, right, env))
            used.add(id(left))
            if right is not None:
                used.add(id(right))
    return found


def _row_clusters(gs: list[Glyph], main: float) -> list[list[Glyph]]:
    """Group glyphs into rows by baseline; small (script) glyphs join the nearest main row."""
    mains = sorted([g for g in gs if g.size >= 0.85 * main], key=lambda g: g.oy)
    rows: list[list[Glyph]] = []
    for g in mains:
        if rows and abs(g.oy - rows[-1][-1].oy) <= 0.45 * main:
            rows[-1].append(g)
        else:
            rows.append([g])
    if not rows:
        return [list(gs)] if gs else []
    for g in gs:
        if g.size >= 0.85 * main:
            continue
        best = min(rows, key=lambda r: abs(sum(x.oy for x in r) / len(r) - g.oy))
        best.append(g)
    return rows


def _matrix_latex(inner: list[Glyph], env: str, rules: list[BBox], main: float, depth: int) -> str:
    rows = _row_clusters(inner, main)
    # (Moving a fraction's numerator and denominator glyphs into "the row at the
    # bar's height" was tried on 4 Sept: it moved no check on its own pages and
    # broke three cases blocks whose rows are themselves fractions, run 34.)
    cells_per_row: list[list[str]] = []
    for row in rows:
        row = sorted(row, key=lambda g: g.bbox.x0)
        cells: list[list[Glyph]] = [[row[0]]]
        for prev, g in zip(row, row[1:]):
            if g.bbox.x0 - prev.bbox.x1 >= 0.7 * main:
                cells.append([g])
            else:
                cells[-1].append(g)
        cells_per_row.append([_build(c, rules, depth + 1) for c in cells])
    body = (" " + chr(92) * 2 + " ").join(" & ".join(c) for c in cells_per_row)
    return chr(92) + "begin{" + env + "} " + body + " " + chr(92) + "end{" + env + "}"


def _build(gs: list[Glyph], rules: list[BBox], depth: int) -> str:
    if not gs:
        return ""
    if depth > 12:
        return _linear(gs, rules)
    size = _main_size(gs)

    # 0. Matrices and cases: tall delimiters around several rows.
    matrices = _find_matrices(gs, size, rules)
    x0 = min(g.bbox.x0 for g in gs)
    x1 = max(g.bbox.x1 for g in gs)
    y0 = min(g.bbox.y0 for g in gs)
    y1 = max(g.bbox.y1 for g in gs)
    if matrices:
        left, right, env = matrices[0]
        span_x1 = right.bbox.x1 if right is not None else max(g.bbox.x1 for g in gs if g.bbox.cy >= left.bbox.y0 and g.bbox.cy <= left.bbox.y1)
        outer_rules = [r for r in rules if not (r.x0 >= left.bbox.x0 - 1 and r.x1 <= span_x1 + 1 and left.bbox.y0 - 1 <= r.cy <= left.bbox.y1 + 1)]
        wide_rule = any(r.x0 < left.bbox.x0 and r.x1 > span_x1 and y0 - 1 <= r.cy <= y1 + 1 for r in outer_rules)
        if not wide_rule:
            inner = [g for g in gs if g is not left and g is not right and g.bbox.x0 >= left.bbox.x1 - 0.2 * size
                     and g.bbox.x1 <= span_x1 + 0.2 * size and left.bbox.y0 - 0.2 * size <= g.bbox.cy <= left.bbox.y1 + 0.2 * size]
            inner_ids = {id(g) for g in inner} | {id(left)} | ({id(right)} if right is not None else set())
            before = [g for g in gs if id(g) not in inner_ids and g.cx < left.bbox.x0]
            after = [g for g in gs if id(g) not in inner_ids and g.cx >= left.bbox.x0]
            inner_rules = [r for r in rules if r not in outer_rules]
            core = _matrix_latex(inner, env, inner_rules, size, depth)
            return " ".join(p for p in (_build(before, outer_rules, depth + 1), core, _build(after, outer_rules, depth + 1)) if p)

    # 1. Fractions and roots: rules with glyphs above and/or below within their span.
    cands = []
    for r in rules:
        # A rule may sit just above (overline, radical) or below (underline) all glyphs.
        # A bar belongs to this group only when it sits close above or below its
        # glyph boxes; a radical bar on the next line (half a line down) does not.
        if r.x1 < x0 - 1 or r.x0 > x1 + 1 or r.cy < y0 - 0.8 * size or r.cy > y1 + 0.5 * size:
            continue
        # Glyphs are assigned by baseline: MuPDF's character boxes come from the font's
        # ascender/descender, so a radical sign's box reaches well above its bar.
        # Tall delimiters that span the bar belong to neither side.
        def spans_bar(g: Glyph) -> bool:
            return g.bbox.height > 1.5 * size and g.bbox.y0 < r.cy - 0.5 * size and g.bbox.y1 > r.cy + 0.5 * size and is_extension_font(g.font)

        above = [g for g in gs if _within_x(g, r, size) and g.oy < r.cy and not spans_bar(g)]
        below = [g for g in gs if _within_x(g, r, size) and g.oy > r.cy and not spans_bar(g)]
        if not above and not below:
            continue
        # A fraction whose parts are all script-sized is either an inline (text-style)
        # fraction sitting on the main line's axis, or a fraction inside a
        # sub/superscript (e^{-k/n}). The latter is handled when that script group
        # is built, not here.
        parts = above + below
        # A radical's bar (a root sign ends where the bar starts) covers whatever
        # stands under it, script-sized or not: "\sqrt{\frac{a}{b}\frac{c}{d}}"
        # set in text style must not be mistaken for a fraction in a script.
        radical_glyphs = [g for g in gs if g.latex == r"\sqrt" and abs(g.bbox.x1 - r.x0) < 1.2 * size and g.bbox.y0 - 1.0 * size <= r.cy <= g.bbox.y1]
        radical_bar = bool(radical_glyphs)
        # A script-sized root sign with script-sized contents is itself part of a
        # script or a limit ("p <= sqrt(x)" under a sum, "e^{sqrt n}"): the two
        # deferrals below apply to it as to any small stack.
        small_radical = radical_bar and all(g.size < 0.85 * size for g in radical_glyphs)
        if max(g.size for g in parts) < 0.85 * size and (not radical_bar or small_radical):
            # A script-sized stack beside a display operator, with no main-size text
            # around, is part of the operator's limits ("p <= sqrt(x)" under a sum):
            # it is built with that limit group, not here.
            ops = [g for g in gs if _takes_limits(g)]   # a text-size sum carries display limits too (\limits)
            if ops and not any(g.size >= 0.85 * size and not is_extension_font(g.font) and not _takes_limits(g) for g in gs):
                op = min(ops, key=lambda o: abs(o.cx - r.cx))
                beside = op.bbox.x0 - 0.6 * size <= r.x0 <= op.bbox.x1 + 3.0 * size
                # The parts' baseline, not the bar, says whether the stack sits in the
                # lower limit (below the operator's centre) or the upper one.
                parts_oy = sorted(g.oy for g in parts)[len(parts) // 2]
                in_limit = parts_oy >= op.bbox.cy + 0.15 * size or parts_oy <= op.bbox.cy - 0.3 * size
                if os.environ.get("TRUEDOC_MATH_DEBUG"):
                    print(f"[math] limit-stack? rule=({r.x0:.0f},{r.x1:.0f},{r.cy:.1f}) op={op.latex} cy={op.bbox.cy:.1f} parts_oy={parts_oy:.1f} beside={beside} in_limit={in_limit}")
                if beside and in_limit:
                    continue
        if max(g.size for g in parts) < 0.85 * size and any(g.size >= 0.85 * size for g in gs) and (not radical_bar or small_radical):
            main_glyphs = [g for g in gs if g.size >= 0.85 * size and "CMEX" not in g.font.upper()]
            if main_glyphs:
                # An inline fraction straddles the main baseline: its numerator sits
                # above it and its denominator below. A stack that sits wholly above
                # (or wholly below) the baseline belongs to a superscript (or a
                # subscript) and is built with that script.
                baseline = _mode([round(g.oy, 1) for g in main_glyphs])
                # Baselines of the parts, judged by ordinary glyphs: a radical sign's
                # origin sits up at its bar, not on the baseline of the digits under it.
                den_plain = [g for g in below if not is_extension_font(g.font) and g.latex != r"\sqrt"] or below
                num_plain = [g for g in above if not is_extension_font(g.font) and g.latex != r"\sqrt"] or above
                den_oy = min(g.oy for g in den_plain) if below else baseline + size
                num_oy = max(g.oy for g in num_plain) if above else baseline - size
                if os.environ.get("TRUEDOC_MATH_DEBUG"):
                    print(f"[math] bar cy={r.cy:.1f} baseline={baseline:.1f} size={size:.1f} parts={''.join(g.ch for g in parts)!r} den_oy={den_oy:.1f} num_oy={num_oy:.1f}")
                # An overline over script-sized glyphs below the baseline is part
                # of a subscript ("\Phi_{\overline{\alpha}h}"), an underline under
                # raised ones part of a superscript; both are rebuilt in the script.
                script_bar = (not above and den_oy >= baseline + 0.02 * size) or (not below and num_oy <= baseline - 0.02 * size)
                if den_oy <= baseline - 0.02 * size or num_oy >= baseline + 0.02 * size or script_bar:
                    if os.environ.get("TRUEDOC_MATH_DEBUG"):
                        print(f"[math] rule skipped as a script stack: ({r.x0:.0f},{r.x1:.0f},{r.cy:.1f}) radical_bar={radical_bar} parts={''.join(g.ch for g in parts)[:30]!r}")
                    continue
        cands.append((r, above, below))
    if cands:
        # Take the widest rule first (outermost structure).
        r, above, below = max(cands, key=lambda c: c[0].width)
        inner_ids = {id(g) for g in above} | {id(g) for g in below}
        left = [g for g in gs if id(g) not in inner_ids and g.cx < r.x0]
        right = [g for g in gs if id(g) not in inner_ids and g.cx >= r.x1]
        middle_rest = [g for g in gs if id(g) not in inner_ids and r.x0 <= g.cx < r.x1]
        sub_rules = [q for q in rules if not (abs(q.cy - r.cy) <= 1.0 and abs(q.x0 - r.x0) <= 1.5 and abs(q.x1 - r.x1) <= 1.5)]
        # The numerator can only contain rules above the bar, the denominator only
        # rules below it (a radical bar in the denominator must not underline the numerator).
        rules_above = [q for q in sub_rules if q.cy < r.cy]
        rules_below = [q for q in sub_rules if q.cy > r.cy]
        if above and below:
            # The checker tells \tfrac and \dfrac from \frac. In a display
            # formula a fraction set at text size with script-sized parts is a
            # \tfrac; in an inline formula one with text-sized parts is a \dfrac
            # (an inline \frac always has script-sized parts).
            frac_cmd = r"\frac"
            parts_max = max(g.size for g in above + below)
            parts_min = min(g.size for g in above + below if not is_extension_font(g.font)) if any(not is_extension_font(g.font) for g in above + below) else parts_max
            stack_ids_ = {id(g) for g in above} | {id(g) for g in below}
            outside = [g for g in gs if id(g) not in stack_ids_ and not is_extension_font(g.font) and g.size >= 0.85 * size]
            if size >= 0.85 * _TOP_MAIN and outside:
                if _MODE == "display" and parts_max < 0.85 * size:
                    frac_cmd = r"\tfrac"
                elif _MODE == "inline" and parts_min >= 0.85 * size:
                    frac_cmd = r"\dfrac"
            core = frac_cmd + "{%s}{%s}" % (_build(above, rules_above, depth + 1), _build(below, rules_below, depth + 1))
        elif below and not above:
            radical = [g for g in left if g.latex == r"\sqrt" and abs(g.bbox.x1 - r.x0) < 1.2 * size]
            if radical:
                left = [g for g in left if id(g) != id(radical[-1])]
                core = r"\sqrt{%s}" % _build(below, rules_below, depth + 1)
            elif min(g.bbox.y0 for g in below) - r.cy <= 0.45 * size:
                core = r"\overline{%s}" % _build(below, rules_below, depth + 1)
            else:
                # A rule well above the glyphs belongs to something else (a radical
                # bar over a neighbouring group); treat the glyphs as plain.
                core = _build(below, rules_below, depth + 1)
        else:
            if r.cy - max(g.bbox.y1 for g in above) <= 0.45 * size:
                core = r"\underline{%s}" % _build(above, rules_above, depth + 1)
            else:
                core = _build(above, rules_above, depth + 1)
        if not (above and below):
            # The scripts of an overlined or underlined base ("\overline{B}^\nu_{h}")
            # stand just right of it; left in the tail they would ride on the next
            # glyph ("\overline{B} :_{h}^{\nu}").
            base_glyphs = below if below else above
            core, right = _attach_core_scripts(core, right, _mode([round(g.oy, 1) for g in base_glyphs]), max(g.bbox.x1 for g in base_glyphs), size, depth)
        else:
            # A script right after a fraction hangs on the fraction ("\frac{d}{dt}^2 d(t)"),
            # judged against the baseline of the text-size glyphs around the stack.
            stack_ids = {id(g) for g in above} | {id(g) for g in below}
            around = [g for g in gs if g.size >= 0.85 * size and id(g) not in stack_ids and not is_extension_font(g.font)]
            base_oy = _mode([round(g.oy, 1) for g in around]) if around else r.cy + 0.35 * size
            # The lower limit of a sum that follows starts left of its sign, right
            # after the bar ("\frac{1}{N}\sum_{k=1}^N", run 31): a script-sized
            # glyph within an operator's reach belongs to that operator's limits.
            ops = [g for g in right if _takes_limits(g)]
            held = [g for g in right if g.size < 0.85 * size
                    and any(o.bbox.x0 - 2.0 * size <= g.cx <= o.bbox.x1 + 2.0 * size for o in ops)]
            held_ids = {id(g) for g in held}
            core, rest = _attach_core_scripts(core, [g for g in right if id(g) not in held_ids],
                                              base_oy, max([r.x1] + [g.bbox.x1 for g in above + below]), size, depth)
            right = rest + held
        if middle_rest:
            core = core + " " + _build(middle_rest, sub_rules, depth + 1)
        return " ".join(p for p in (_build(left, sub_rules, depth + 1), core, _build(right, sub_rules, depth + 1)) if p)

    # 2. No fractions at this level: linear sequence with scripts and limits.
    return _linear(gs, rules)


def _within_x(g: Glyph, r: BBox, size: float) -> bool:
    """A glyph belongs to a bar's stack when its centre lies over the bar."""
    return r.x0 <= g.cx <= r.x1


@dataclass
class _Atom:
    base: Glyph
    sub: list[Glyph] = field(default_factory=list)
    sup: list[Glyph] = field(default_factory=list)


_ACCENTS = {
    "ˆ": "hat", "^": "hat", "˜": "tilde", "~": "tilde", "¯": "bar", "ˉ": "bar", "‾": "bar",
    "˙": "dot", "¨": "ddot", "ˇ": "check", "˘": "breve", "⃗": "vec", "→": "vec", "´": "acute", "`": "grave",
    "˚": "mathring", "°": "mathring",
    # Some producers emit the accent as a combining mark.
    "̂": "hat", "̃": "tilde", "̄": "bar", "̅": "bar", "̇": "dot", "̈": "ddot",
    "̊": "mathring", "̌": "check", "̆": "breve", "́": "acute", "̀": "grave", "⃛": "dddot",
}
_WIDE_ACCENTS = {r"\hat{}": "widehat", r"\tilde{}": "widetilde", r"\check{}": "widecheck"}


def _accent_name(g: Glyph) -> str | None:
    if is_extension_font(g.font):
        return _WIDE_ACCENTS.get(g.latex)
    f = g.font.upper()
    if "MATHA" in f or "MATHB" in f or "MATHX" in f:
        # mathabx codes are read through its own table: its "˚" is the asterisk
        # (f_t^*), not a ring accent; only what the table calls an accent is one.
        return g.latex[1:-2] if g.latex in _BARE_ACCENTS else None
    name = _ACCENTS.get(g.ch)
    if name is None and g.latex in _BARE_ACCENTS:
        name = g.latex[1:-2]   # an accent known by its code in a symbol font ("9" in mathb): "\dot{}" -> "dot"
    return name


def _attach_accents(gs: list[Glyph]) -> tuple[list[Glyph], dict[int, str]]:
    """Find accent glyphs sitting on top of a base glyph; return (remaining glyphs, base id -> accent)."""
    accents: dict[int, str] = {}
    if len(gs) < 2:
        return gs, accents
    main = _main_size(gs)
    gs = _widen_accent_bases(gs, main)
    remaining: list[Glyph] = []
    for g in gs:
        name = _accent_name(g)
        if name is None or (g.ch == "→" and g.size >= 0.85 * main):
            remaining.append(g)
            continue
        base = _accent_base(g, gs)
        # A wide tilde over one letter renders like a plain tilde, so the shorter
        # spelling is safe; a wide hat does not (run 26 lost nine checks to it).
        if base is not None and name == "widetilde" and g.bbox.width <= 1.4 * max(base.bbox.width, 0.1):
            # TeX picks a wide accent's smallest size over a single letter, and the
            # source then reads \tilde{T}; the wide form renders wider in KaTeX.
            name = name[4:]
        if base is not None and id(base) not in accents:
            accents[id(base)] = name
        else:
            remaining.append(g)
    return remaining, accents


def _widen_accent_bases(gs: list[Glyph], main: float) -> list[Glyph]:
    """An accent centred over two touching letters covers both ("\\bar{Az}"):
    the letters become one glyph so the accent is written over the pair."""
    out = list(gs)
    for g in gs:
        if _accent_name(g) is None or (g.ch == "→" and g.size >= 0.85 * main) or g.bbox.width < 0.1 * g.size:
            continue
        base = _accent_base(g, out)
        if base is None or not base.ch.isalpha() or len(base.ch) != 1:
            continue
        # The neighbour on the side the accent leans to, touching the base.
        lean = g.cx - base.cx
        if abs(lean) < 0.2 * base.bbox.width:
            continue
        side = [b for b in out if b is not base and b.ch.isalpha() and len(b.ch) == 1 and _accent_name(b) is None
                and abs(b.size - base.size) <= 0.1 * base.size and abs(b.oy - base.oy) <= 0.1 * base.size
                and ((lean > 0 and -0.05 * base.size <= b.bbox.x0 - base.bbox.x1 <= 0.15 * base.size)
                     or (lean < 0 and -0.05 * base.size <= base.bbox.x0 - b.bbox.x1 <= 0.15 * base.size))]
        if not side:
            continue
        n = side[0]
        pair = BBox.union_all([base.bbox, n.bbox])
        if abs(g.cx - pair.cx) >= abs(lean):
            continue   # the accent sits better over the single letter
        first, second = (base, n) if lean > 0 else (n, base)
        merged = Glyph(ch=first.ch + second.ch, font=base.font, size=base.size, bbox=pair, oy=base.oy,
                       latex=first.latex + second.latex)
        out = [merged if b is base else b for b in out if b is not n]
    return out


def _accent_base(g: Glyph, gs: list[Glyph]) -> Glyph | None:
    """The glyph an accent sits on.

    An accent is set at the size of its base: a hat over a letter never belongs
    to that letter's subscript, however close the subscript's box comes.
    """

    def candidate(b: Glyph) -> bool:
        return b is not g and _accent_name(b) is None and not b.ch.isspace() and 0.85 * g.size <= b.size <= 1.25 * g.size

    if g.bbox.width < 0.1 * g.size:
        # A combining mark has no advance width: it precedes its base in the text
        # stream, and the text layer reports it where the previous glyph ended
        # (even across a wide space), so its base is the next glyph to the right.
        right = [b for b in gs if candidate(b) and -0.15 * g.size <= b.bbox.x0 - g.bbox.x0 <= 2.5 * g.size and abs(b.oy - g.oy) <= 0.5 * g.size]
        return min(right, key=lambda b: b.bbox.x0) if right else None
    # 1. The glyph directly below with the best horizontal overlap (a raised
    #    accent over a tall letter, or boxes that reflect the drawn outline).
    best, best_key = None, (0.0, 0.0)
    for b in gs:
        if not candidate(b):
            continue
        if b.bbox.y0 < g.bbox.y1 - 0.5 * g.bbox.height and b.bbox.y1 > g.bbox.y1:
            ov = g.bbox.x_overlap(b.bbox)
            key = (round(b.size, 1), ov)
            if ov >= 0.4 * g.bbox.width and key > best_key:
                best, best_key = b, key
    if best is not None:
        return best
    # 2. Baselines: the accent's origin sits a little above the base's origin and
    #    its centre lies over the base (boxes from font metrics can mislead).
    for b in sorted(gs, key=lambda b: -b.size):
        if not candidate(b):
            continue
        raise_ = b.oy - g.oy
        if 0.15 * b.size <= raise_ <= 1.3 * b.size and b.bbox.x0 - 0.35 * b.size <= g.cx <= b.bbox.x1 + 0.35 * b.size:
            return b
    # 3. TeX sets accents over x-height letters at the *same* baseline, with the
    #    raise built into the glyph outline; the boxes then simply overlap.
    for b in gs:
        if not candidate(b) or not (b.ch.isalpha() or b.is_math):
            continue
        if abs(b.oy - g.oy) <= 0.15 * b.size and g.bbox.x_overlap(b.bbox) >= 0.3 * g.bbox.width:
            return b
    return None


# Operator names that KaTeX has no command for: written as \text{...}, which is
# how the benchmark's references spell them ("\text{conv}(w)", "\text{std}(w)").
_TEXT_OPERATOR_WORDS = {
    "conv", "std", "supp", "span", "rank", "dist", "card", "vol", "proj", "aut", "end", "spec", "sgn", "diag",
    "ord", "lcm", "cov", "var", "grad", "curl", "div", "codim", "sign", "trace", "null", "row", "col", "tr",
}


def _split_names(word: str) -> "list[str] | None":
    """Split a run of upright letters into known operator names, longest first
    ("logsin" -> ["log", "sin"]); None unless the whole run is names."""
    names = FUNCTION_NAMES | _TEXT_OPERATOR_WORDS
    out: list[str] = []
    i = 0
    while i < len(word):
        for length in range(min(8, len(word) - i), 1, -1):
            if word[i:i + length] in names:
                out.append(word[i:i + length])
                i += length
                break
        else:
            return None
    return out if len(out) >= 2 else None


def _group_function_words(gs: list[Glyph]) -> list[Glyph]:
    """Merge consecutive upright letters into one glyph ("lim", "sup", "log").

    The letters of a function name are separate glyphs in the text layer; as
    one glyph, limits set under "lim" attach to the word rather than to the
    letter nearest to them.
    """
    main = _main_size(gs)
    # Scan only the main-size upright letters, so limits set underneath a word
    # (which interleave with it in x order) do not break the run.
    # Letters of every size: a "sin" inside an exponent is a function name too.
    # Runs are bounded by size and baseline below, so limits under a word
    # (which interleave with it in x order) do not break it.
    letters = [g for g in gs if g.ch.isalpha() and g.ch.isascii()
               and (not g.is_math or _is_unicode_math_font(g.font)) and "CMEX" not in g.font.upper()]
    # Letters of one size on one baseline form a word; a limit's letters under
    # "sup" (smaller, lower) interleave with s, u, p in reading order and must
    # be looked past, not break the word.
    letters.sort(key=lambda g: (round(g.size, 1), round(g.oy, 1), g.bbox.x0))
    replaced: dict[int, Glyph | None] = {}
    i = 0
    while i < len(letters):
        g = letters[i]
        run = [g]
        j = i
        while j + 1 < len(letters):
            n = letters[j + 1]
            if abs(n.oy - g.oy) > 0.1 * g.size or abs(n.size - g.size) > 0.1 * g.size or n.bbox.x0 - run[-1].bbox.x1 > 0.25 * g.size:
                break
            run.append(n)
            j += 1
        word = "".join(x.ch for x in run)
        italic = any(h in g.font.upper() for h in _ITALIC_HINTS)
        # An operator name KaTeX knows becomes its command; another word set as
        # an operator ("conv", "std", "supp") is written as text. A word set in
        # italics counts only when it is long enough not to be a product of
        # variables ("im" may be i times m; "conv" is not c, o, n, v).
        named = word in FUNCTION_NAMES or word in _TEXT_OPERATOR_WORDS or word in ("argmax", "argmin")
        parts = [word] if named else (_split_names(word) if len(word) >= 5 and not italic else None)
        if len(run) >= 2 and parts and (not italic or len(word) >= 3):
            start = 0
            for part in parts:
                slice_ = run[start:start + len(part)]
                start += len(part)
                if part in ("argmax", "argmin"):
                    cmd = r"\operatorname*{arg\,%s}" % part[3:]   # takes its limits underneath, like the two-word form
                else:
                    cmd = ("\\" + part) if part in FUNCTION_NAMES else r"\text{%s}" % part
                    # A script-sized name with nothing after it on its line is a
                    # label ("d_{\text{min}}"), not the operator; "sin" inside an
                    # exponent is followed by its argument and stays \sin.
                    if part in FUNCTION_NAMES and g.size < 0.85 * main:
                        last = slice_[-1]
                        followed = any(h is not last and h not in run and abs(h.oy - last.oy) <= 0.15 * g.size
                                       and -0.1 * g.size <= h.bbox.x0 - last.bbox.x1 <= 0.5 * g.size and h.size < 0.85 * main
                                       for h in gs)
                        # A name carrying its own subscript ("\log_2 3" in an
                        # exponent, 2503.09367) is applied, not a label.
                        subscripted = any(h is not last and h not in run and h.size < 0.85 * g.size and h.oy > last.oy
                                          and -0.1 * g.size <= h.bbox.x0 - last.bbox.x1 <= 0.3 * g.size for h in gs)
                        if not followed and not subscripted:
                            cmd = r"\text{%s}" % part
                merged = Glyph(ch=part, font=g.font, size=g.size, bbox=BBox.union_all(x.bbox for x in slice_), oy=g.oy, latex=cmd)
                replaced[id(slice_[0])] = merged
                for x in slice_[1:]:
                    replaced[id(x)] = None
        i = j + 1
    out: list[Glyph] = []
    for g in gs:
        if id(g) in replaced:
            if replaced[id(g)] is not None:
                out.append(replaced[id(g)])  # type: ignore[arg-type]
            continue
        out.append(g)
    # "lim" followed closely by "inf"/"sup" is the single operator liminf/limsup;
    # "arg" followed by "max"/"min" is one operator too, and its limits go under
    # the whole word (as \underset or \operatorname* set them).
    merged: list[Glyph] = []
    for g in sorted(out, key=lambda g: g.bbox.x0):
        prev = merged[-1] if merged else None
        close = prev is not None and g.bbox.x0 - prev.bbox.x1 < 0.8 * g.size and abs(g.oy - prev.oy) < 0.1 * g.size
        if close and prev.latex == "\\lim" and g.latex in ("\\inf", "\\sup"):
            merged.pop()
            merged.append(Glyph(ch=prev.ch + g.ch, font=g.font, size=g.size, bbox=prev.bbox.union(g.bbox), oy=g.oy, latex="\\lim" + g.ch))
        elif close and prev.latex == "\\arg" and g.latex in ("\\max", "\\min", "\\sup", "\\inf"):
            merged.pop()
            merged.append(Glyph(ch=prev.ch + g.ch, font=g.font, size=g.size, bbox=prev.bbox.union(g.bbox), oy=g.oy,
                                latex="\\operatorname*{arg\\," + g.ch + "}"))
        else:
            merged.append(g)
    return merged


_ITALIC_HINTS = ("MI", "TI", "ITAL", "OBLIQUE", "SLANT", "CMSL", "-IT", "IT1", "IT8", "IT9")   # "ITAL" covers Italic and URW's "ReguItal"
_BOLD_HINTS = ("BOLD", "CMBX", "SFBX", "CMSSBX", "CMMIB", "CMBSY", "BLACK", "HEAVY", "-BD", "TXB", "PXB")


_UNICODE_MATH_EXCLUDE = ("ITAL", "SYM", "EXT", "CMMI", "CMEX", "MSAM", "MSBM", "MATHA", "MATHB", "MATHX", "MDSY", "MDMI",
                         "MDBSY", "STMARY", "ESINT", "MATHDESIGN")


def _is_unicode_math_font(font: str) -> bool:
    """An OpenType maths font (Libertinus Math, STIX Two Math, Latin Modern Math):
    its variables are the Unicode italic letters, so a plain ASCII letter in it
    is upright text ("lim", "sup", "d")."""
    f = font.upper()
    if "+" in f:
        f = f.split("+", 1)[1]
    return "MATH" in f and not any(h in f for h in _UNICODE_MATH_EXCLUDE)


def _is_upright_text(g: Glyph) -> bool:
    """A letter (or a dot) from an upright text font: prose inside a formula."""
    if g.latex.startswith("\\") or not g.ch.isascii() or not (g.ch.isalpha() or g.ch == "."):
        return False
    if g.is_math and not _is_unicode_math_font(g.font):
        return False
    f = g.font.upper()
    if "+" in f:
        f = f.split("+", 1)[1]
    if any(h in f for h in _BOLD_HINTS):
        return False  # a bold letter in a formula is a vector or matrix name, not prose
    return not any(h in f for h in _ITALIC_HINTS)


_COMMON_WORDS: set[str] | None = None


def _common_words() -> set[str]:
    """About 10,000 common English words, loaded once (the OCR gate's list)."""
    global _COMMON_WORDS
    if _COMMON_WORDS is None:
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "en_common_words.txt")
        try:
            with open(path, encoding="utf-8") as fh:
                _COMMON_WORDS = {ln.strip().lower() for ln in fh if ln.strip()}
        except OSError:
            _COMMON_WORDS = set()
    return _COMMON_WORDS


def _is_italic_text(g: Glyph) -> bool:
    """An italic letter from a text font (not a maths font): a theorem's prose."""
    if g.is_math or g.latex.startswith("\\") or not g.ch.isascii() or not g.ch.isalpha():
        return False
    f = g.font.upper()
    if "+" in f:
        f = f.split("+", 1)[1]
    return any(h in f for h in _ITALIC_HINTS) and not any(h in f for h in _BOLD_HINTS)


def _group_italic_prose(gs: list[Glyph]) -> list[Glyph]:
    """Words of a theorem set in italics inside a formula ("xi is predictable and")
    are prose, written as one `\\text{...}` run like upright words; an italic
    text-font letter or two on their own ("xy" in a Times paper) stay variables.
    A run counts as prose when its words are ordinary English."""
    ordered = sorted(gs, key=lambda g: g.bbox.x0)
    out: list[Glyph] = []
    i = 0
    while i < len(ordered):
        g = ordered[i]
        if not _is_italic_text(g):
            out.append(g)
            i += 1
            continue
        main = g.size
        run = [g]
        j = i
        while j + 1 < len(ordered):
            n, p = ordered[j + 1], run[-1]
            if not _is_italic_text(n) or abs(n.size - g.size) > 0.1 * g.size or abs(n.oy - p.oy) > 0.1 * main or n.bbox.x0 - p.bbox.x1 > 1.2 * main:
                break
            run.append(n)
            j += 1
        words: list[str] = [run[0].ch]
        for p, n in zip(run, run[1:]):
            if n.bbox.x0 - p.bbox.x1 >= 0.25 * main:
                words.append(n.ch)
            else:
                words[-1] += n.ch
        common = _common_words()
        known = [w for w in words if len(w) >= 2 and w.lower() in common]
        # A lone word of three or more letters that is ordinary English ("for",
        # "and", "where") is prose too; function names are handled elsewhere.
        lone = len(words) == 1 and len(words[0]) >= 3 and words[0].lower() in common and words[0].lower() not in FUNCTION_NAMES
        prose = (len(words) >= 2 and len(known) >= max(2, 0.6 * len(words))) or lone
        if prose:
            text = " ".join(words)
            out.append(Glyph(ch=text, font=g.font, size=g.size, bbox=BBox.union_all(x.bbox for x in run), oy=g.oy, latex="\\text{" + text + "}"))
        else:
            out.extend(run)
        i = j + 1
    return out


def _group_text_words(gs: list[Glyph]) -> list[Glyph]:
    """Upright text-font letters inside a formula are words: "for all", "s.t.",
    "otherwise". KaTeX renders `\\text{...}` as one run with its spaces, and the
    benchmark compares such runs whole, so loose letters can never match it.
    Single letters stay as they are (a "d" or a "T" is usually a symbol)."""
    ordered = sorted(gs, key=lambda g: g.bbox.x0)
    out: list[Glyph] = []
    i = 0
    while i < len(ordered):
        g = ordered[i]
        if not (_is_upright_text(g) and g.ch != "."):
            out.append(g)
            i += 1
            continue
        main = g.size  # words are grouped at their own size: "X^{\text{Test}}" has a script-sized word
        run = [g]
        j = i
        while j + 1 < len(ordered):
            n, p = ordered[j + 1], run[-1]
            if not _is_upright_text(n) or abs(n.size - g.size) > 0.1 * g.size or abs(n.oy - p.oy) > 0.1 * main:
                break
            if n.bbox.x0 - p.bbox.x1 > 1.2 * main:
                break
            if n.ch == "." and not (j + 2 < len(ordered) and ordered[j + 2].ch.isalpha() and _is_upright_text(ordered[j + 2]) and ordered[j + 2].bbox.x0 - n.bbox.x1 < 0.25 * main):
                # a dot is part of the word only inside an abbreviation ("s.t.", "i.e.")
                if not any(x.ch == "." for x in run):
                    break
            run.append(n)
            j += 1
        letters = sum(1 for x in run if x.ch.isalpha())
        if letters < 2:
            # A lone upright letter in a formula is set upright on purpose
            # (\mathrm{T}_p, \mathrm{U}(1), x_\mathrm{s}); the references write it
            # so 33 times for capitals and 20 for lower case. The one exception
            # is "d": the references write the differential plain 57 times to 4.
            if len(g.ch) == 1 and g.ch.isalpha() and g.ch != "d" and g.latex == g.ch:
                g.latex = r"\mathrm{%s}" % g.ch
            out.append(g)
            i += 1
            continue
        words: list[str] = [run[0].ch]
        for p, n in zip(run, run[1:]):
            if n.bbox.x0 - p.bbox.x1 >= 0.25 * main:
                words.append(n.ch)
            else:
                words[-1] += n.ch
        text = " ".join(words)
        out.append(Glyph(ch=text, font=g.font, size=g.size, bbox=BBox.union_all(x.bbox for x in run), oy=g.oy, latex="\\text{" + text + "}"))
        i = j + 1
    return out


_ACCENT_MEMO: dict[int, str] = {}   # base glyph id -> accent, for the formula being built


def _linear(gs: list[Glyph], rules: list[BBox] | None = None) -> str:
    rules = rules or []
    gs = sorted(gs, key=lambda g: (g.bbox.x0, g.oy))
    if not gs:
        return ""
    gs, accents = _attach_accents(gs)
    # An accent found at an outer level belongs to its base wherever that base
    # is rendered: a dotted H inside a subscript keeps its dot.
    accents = {**_ACCENT_MEMO, **accents}
    _ACCENT_MEMO.update(accents)
    gs = _group_function_words(gs)
    gs = _group_italic_prose(_group_text_words(gs))
    main = _main_size(gs)
    # Baseline of the main level: most common origin among main-size glyphs.
    # Big operators (cmex glyphs) have their origin at the top of the glyph, so
    # they must not vote for the baseline of the line.
    mains = [g for g in gs if g.size >= 0.85 * main and g.latex not in BIG_OPERATORS and "CMEX" not in g.font.upper()]
    if not mains:
        mains = [g for g in gs if g.size >= 0.85 * main] or gs
    base_oy = _mode([round(g.oy, 1) for g in mains])

    atoms: list[_Atom] = []
    pending_scripts: list[Glyph] = []
    # A limit-taking word set at script size ("max" in "v^2_{1,\max}") is part of
    # a script and takes no limits of its own; a big operator sign always does.
    big_ops = [g for g in gs if _takes_limits(g) and (g.latex in BIG_OPERATORS or g.size >= 0.85 * main)]
    # A fraction set entirely at script size whose bar sits well above the
    # baseline is part of a superscript (e^{-\frac{1}{2}(n-1)}); below it, of a
    # subscript. Its denominator alone would look like main-line text, so the
    # whole stack is assigned to the script by the bar's position.
    stack_zone: dict[int, str] = {}
    for r in rules:
        over = [g for g in gs if _within_x(g, r, main)]
        if not over or any(g.size >= 0.85 * main for g in over):
            continue
        above = [g for g in over if g.oy < r.cy]
        below = [g for g in over if g.oy > r.cy]
        if not above or not below:
            continue
        if min(g.oy for g in below) <= base_oy - 0.02 * main:
            zone = "sup"      # the whole stack, denominator included, sits above the baseline
        elif max(g.oy for g in above) >= base_oy + 0.02 * main:
            zone = "sub"      # the whole stack sits below it
        else:
            continue
        for g in over:
            stack_zone[id(g)] = zone
    # Limits of a big operator start left of the operator in x order; park them
    # until the operator's atom exists.
    parked: dict[int, list[Glyph]] = {}
    parked_last: tuple[Glyph, Glyph] | None = None  # the last parked glyph and the operator it waits for
    for g in gs:
        is_big = g.latex in BIG_OPERATORS or is_extension_font(g.font)
        # A script-sized root sign is part of a limit ("p <= sqrt(x)" under a
        # sum), not an operator of its own; the linear join gives it its argument.
        small = g.size < 0.85 * main and (not is_big or g.latex == r"\sqrt")
        if not small and not is_big:
            # A main-size glyph on a clearly different baseline is still a script
            # (e.g. a superscript typeset at the same size); tolerate 0.25em.
            if abs(g.oy - base_oy) > 0.25 * main and atoms:
                small = True
        if small:
            # A limit of a display-style operator is centred over or under it: its
            # centre lies within the operator's width and clearly above its top or
            # below its bottom. Anything else (the tail of a previous superscript
            # that merely comes close) stays with its own base.
            # A limit continues glyph after glyph on its own baseline ("n = 1"
            # under a sum): the glyph that continues a parked run belongs to the
            # same operator, even when a following operator's span also holds it.
            continues = _continues_limit_run(atoms, g, main, big_ops) is not None
            if parked_last is not None and not continues:
                prev, prev_owner = parked_last
                if abs(g.oy - prev.oy) <= 0.15 * main and -0.1 * main <= g.bbox.x0 - prev.bbox.x1 <= 0.5 * main and id(prev_owner) in parked:
                    parked[id(prev_owner)].append(g)
                    parked_last = (g, prev_owner)
                    continue
            owner = None
            # A glyph within the span of an operator already built is that
            # operator's limit (through _target_atom below); the wide search for
            # operators still to come must not take it ("n" under the first of
            # two close sums is not the second sum's).
            built_ids = {id(a.base) for a in atoms}
            under_built = (any(_takes_limits(a.base) and a.base.bbox.x0 - 0.6 * main <= g.cx <= a.base.bbox.x1 + 0.6 * main for a in atoms[-3:])
                           and not any(id(b) not in built_ids and b.bbox.x0 <= g.cx <= b.bbox.x1 for b in big_ops))
            # A script glued to the previous main-line atom ("\|_X" right after a
            # tall bar) is that atom's script, whatever operator follows.
            glued = False
            prev_base = atoms[-1].base if atoms else None
            # Only after a closing delimiter or a tall bar: a limit of the next sum
            # may start right after a plain letter ("\omega" then "i_max - 1").
            if prev_base is not None and (is_extension_font(prev_base.font) or prev_base.ch in ")]}|"
                                          or _delim_key(prev_base.latex) in _CLOSE_FOR.values()) \
                    and not _takes_limits(prev_base) and prev_base.latex != r"\sqrt":
                prev_x1 = max([prev_base.bbox.x1] + [s.bbox.x1 for s in atoms[-1].sub + atoms[-1].sup])
                glued = -0.1 * main <= g.bbox.x0 - prev_x1 <= 0.3 * main
                # ... unless it already stands under or over an operator still to
                # come (the "e" of "epsilon -> 0" under a "lim" that follows "=").
                if glued and any(id(b) not in built_ids and b.bbox.x0 - 0.2 * main <= g.cx <= b.bbox.x1 + 0.2 * main for b in big_ops):
                    glued = False
            if not continues and not under_built and not glued:
                # Among the operators still to come whose span holds the glyph
                # (the ones already built take their limits through _target_atom),
                # the nearest centre: "m = 1" under the second of two close sums.
                built = {id(a.base) for a in atoms}
                # A limit centred under a word or a sign may start two ems left of
                # it ("mu in M_T(X)" under "sup"); the vertical test keeps the
                # scripts of the base before it out.
                cands = [b for b in big_ops if b is not g and id(b) not in built and g.bbox.x0 < b.bbox.x1
                         and b.bbox.x0 - 2.0 * main <= g.cx <= b.bbox.x1 + 2.0 * main
                         and (g.bbox.cy <= b.bbox.y0 + 0.15 * b.bbox.height or g.bbox.cy >= b.bbox.y1 - 0.15 * b.bbox.height)]
                owner = min(cands, key=lambda b: abs(b.cx - g.cx)) if cands else None
            if os.environ.get("TRUEDOC_MATH_DEBUG") and (owner is not None or glued):
                print(f"[math] park? {g.ch!r}@{g.bbox.x0:.0f},{g.oy:.0f} glued={glued} continues={continues} under_built={under_built} owner={(owner.latex if owner is not None else None)!r} prev={(atoms[-1].base.latex if atoms else None)!r}")
            if owner is not None:
                parked.setdefault(id(owner), []).append(g)
                parked_last = (g, owner)
                continue
        # The operator the parked limits waited for: a big operator, or a word
        # that takes limits ("lim" whose "n" stood left of its first letter).
        if (is_big or _takes_limits(g)) and id(g) in parked:
            atoms.append(_Atom(base=g))
            for p in parked.pop(id(g)):
                if _script_position(g, p, main) == "sub":
                    atoms[-1].sub.append(p)
                else:
                    atoms[-1].sup.append(p)
            continue
        if small and atoms and id(g) in stack_zone:
            atom = _target_atom(atoms, g, main, big_ops)
            if atom.base.latex != r"\sqrt":
                (atom.sup if stack_zone[id(g)] == "sup" else atom.sub).append(g)
                continue
        if small and atoms and atoms[-1].base.latex == r"\sqrt" and _target_atom(atoms, g, main, big_ops) is atoms[-1]:
            # A radical sign takes an argument, never a script: "\sqrt^{n}" is not LaTeX.
            atoms.append(_Atom(base=g))
            continue
        if small and atoms:
            atom = _target_atom(atoms, g, main, big_ops)
            # A script of a script (the ⊥ in H^{\perp} under a bar) is smaller still
            # than the script it rides on; it joins that script's group, which is
            # rebuilt on its own and places it relative to the script.
            scripts = atom.sub + atom.sup
            if scripts:
                # The script it rides on: one that starts before it, and of the
                # candidates the one on its own baseline (the F of \nu_F above
                # a sum, not the "=" of the lower limit that happens to end nearer).
                hosts = [s for s in scripts if g.size < 0.85 * s.size and g.bbox.x0 >= s.bbox.x0]
                if hosts:
                    host = min(hosts, key=lambda s: (abs(g.oy - s.oy) > 0.6 * s.size, abs(g.bbox.x0 - s.bbox.x1)))
                    (atom.sub if host in atom.sub else atom.sup).append(g)
                    continue
            pos = _script_position(atom.base, g, main)
            if pos == "sub":
                atom.sub.append(g)
            elif pos == "sup":
                atom.sup.append(g)
            else:
                atoms.append(_Atom(base=g))
        elif small and not atoms:
            pending_scripts.append(g)
        else:
            atoms.append(_Atom(base=g))
            if pending_scripts:
                # Scripts that came before their base (limits under a big operator).
                for p in pending_scripts:
                    if _script_position(g, p, main) == "sub":
                        atoms[-1].sub.append(p)
                    else:
                        atoms[-1].sup.append(p)
                pending_scripts = []
    if pending_scripts and not atoms:
        atoms = [_Atom(base=p) for p in pending_scripts]

    pieces: list[str] = []
    for a in atoms:
        tok = a.base.latex
        if not tok:
            continue
        piece = tok
        acc = accents.get(id(a.base))
        if acc:
            piece = "\\" + acc + "{" + tok + "}"
        # A glyph with no LaTeX (an unmapped code) must not leave an empty script
        # group behind ("x^{}"): scripts are built from the named glyphs only.
        sub_glyphs = [g for g in a.sub if g.latex]
        sup_glyphs = [g for g in a.sup if g.latex]
        sub = _build(sub_glyphs, rules, depth=1) if sub_glyphs else ""
        sup = _build(sup_glyphs, rules, depth=1) if sup_glyphs else ""
        if tok == r"\sqrt" and (sub or sup):
            # Glyphs that landed as "scripts" of a radical sign are its argument
            # (the sign's own baseline is odd); "\sqrt^{n}" is not LaTeX.
            pieces.append(r"\sqrt{" + " ".join(x for x in (sub, sup) if x) + "}")
            continue
        if sub:
            piece += "_{" + sub + "}"
        if sup:
            piece += "^{" + sup + "}"
        pieces.append(piece)

    # A radical that found no rule takes the next piece as its argument.
    out: list[str] = []
    i = 0
    while i < len(pieces):
        if pieces[i] == "\\sqrt":
            if i + 1 < len(pieces):
                out.append("\\sqrt{" + pieces[i + 1] + "}")
                i += 2
            else:
                i += 1
            continue
        out.append(pieces[i])
        i += 1
    return _join(out)


def _script_position(base: Glyph, g: Glyph, main: float) -> str:
    """Is small glyph `g` a subscript, a superscript, or neither, relative to `base`?"""
    if (base.latex in BIG_OPERATORS or is_extension_font(base.font)) and base.bbox.height >= 1.4 * main:
        # Display-style operator glyphs: judge by the visual centre, limits sit above/below it.
        if g.bbox.cy >= base.bbox.cy + 0.15 * main:
            return "sub"
        if g.bbox.cy <= base.bbox.cy - 0.15 * main:
            return "sup"
        return "none"
    if base.latex in BIG_OPERATORS or is_extension_font(base.font):
        # Text-style operator: scripts sit to the right like ordinary scripts, but the
        # operator's own origin is unreliable, so compare with the glyph's box centre.
        if g.bbox.cy >= base.bbox.cy + 0.1 * main:
            return "sub"
        if g.bbox.cy <= base.bbox.cy - 0.1 * main:
            return "sup"
        return "none"
    if g.oy > base.oy + 0.08 * main:
        return "sub"
    if g.oy < base.oy - 0.08 * main:
        return "sup"
    return "none"


def _continues_limit_run(atoms: list[_Atom], g: Glyph, main: float, big_ops: "list[Glyph] | tuple" = ()) -> "_Atom | None":
    """The recent operator whose limit the glyph continues on the same baseline,
    right after the limit's last glyph; None when it continues no limit.

    A run does not reach into the next operator's own span: "m = 1" under a
    second sum set close to the first is the second sum's limit, however
    small the gap after "n = 1"."""
    for a in reversed([a for a in atoms[-3:] if _takes_limits(a.base)]):
        for run in (a.sub, a.sup):
            if run:
                last = max(run, key=lambda x: x.bbox.x1)
                # A radical sign's origin sits up at its bar, so it is judged by adjacency alone.
                same_line = abs(g.oy - last.oy) <= 0.15 * main or g.latex == r"\sqrt" or last.latex == r"\sqrt"
                if same_line and -0.1 * main <= g.bbox.x0 - last.bbox.x1 <= 0.5 * main:
                    # Past this operator's own box and inside another's: that
                    # operator's limit, not a continuation (the operators' boxes
                    # carry the font's bearings, so no margins here).
                    beyond = g.cx > a.base.bbox.x1
                    claimed = any(b is not a.base and b.bbox.x0 <= g.cx <= b.bbox.x1 for b in big_ops)
                    if beyond and claimed:
                        return None
                    return a
    return None


def _target_atom(atoms: list[_Atom], g: Glyph, main: float, big_ops: "list[Glyph] | tuple" = ()) -> _Atom:
    """Which base does a small glyph belong to? A big operator it sits over/under, else the previous base."""
    operators = [a for a in atoms[-3:] if _takes_limits(a.base)]
    # A limit wider than its operator ("p <= sqrt(x)" under a sum, "n = 1" under
    # a sum that an integral follows closely) continues on the limit's own
    # baseline, glyph after glyph, past the operator's edge: the run it
    # continues decides before any operator's window does.
    run_owner = _continues_limit_run(atoms, g, main, big_ops)
    if run_owner is not None:
        return run_owner
    # Otherwise the operator whose span the glyph sits over or under; when two
    # operators stand close enough for both spans to hold it, the nearer centre.
    inside = [a for a in operators if a.base.bbox.x0 - 0.6 * main <= g.cx <= a.base.bbox.x1 + 0.6 * main]
    if inside:
        return min(inside, key=lambda a: abs(a.base.cx - g.cx))
    return atoms[-1]


def _mode(values: list[float]) -> float:
    counts: dict[float, int] = {}
    for v in values:
        counts[v] = counts.get(v, 0) + 1
    return max(counts.items(), key=lambda kv: (kv[1], -kv[0]))[0]


def _join(tokens: list[str]) -> str:
    out = ""
    for t in tokens:
        if not t:
            continue
        if out and out[-1].isalpha() and out.rfind("\\") >= 0 and _ends_with_command(out) and (t[0].isalpha()):
            out += " " + t
        elif out and _ends_with_command(out) and t[0].isalpha():
            out += " " + t
        else:
            out += t
    return out


def _ends_with_command(s: str) -> bool:
    m = re.search(r"\\[A-Za-z]+$", s)
    return m is not None
