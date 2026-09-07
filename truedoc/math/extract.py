"""Find formulas on a page (display regions and inline runs) and turn them into LaTeX."""

from __future__ import annotations

import re

from truedoc.math.reconstruct import Glyph, glyph, is_math_font, reconstruct, split_display_lines
from truedoc.math.symbols import is_piece_glyph
from truedoc.model import BBox, Block, BlockKind, Line, Page, Word

_OPERATOR_CHARS = set("=+−-×·<>≤≥≠±/()[]{}|∑∏∫√∞∂∇→←⇒⇔∈∉⊂⊆∪∩∧∨¬∀∃′°∼≈≡")
_RELATION_CHARS = set("=<>≤≥≠∈∉→≈≡∼≃≅⊂⊆:")


def page_rules(page: Page) -> list[BBox]:
    """Horizontal rules on the page, with near-duplicates (the same bar reported by two
    extraction routes with slightly different coordinates) collapsed to one."""
    out: list[BBox] = []
    for d in page.drawings:
        if d.kind != "hline":
            continue
        r = d.bbox
        if any(abs(r.cy - k.cy) <= 1.0 and abs(r.x0 - k.x0) <= 1.5 and abs(r.x1 - k.x1) <= 1.5 for k in out):
            continue
        out.append(r)
    return out


def _line_glyphs(line: Line) -> list[Glyph]:
    out: list[Glyph] = []
    for w in line.words:
        for c in w.chars:
            out.append(glyph(c.text, c.font, c.size, c.bbox, c.origin_y, c.ink))
    return out


_RELATIONS = (
    "=", "<", ">", r"\leq", r"\geq", r"\le", r"\ge", r"\neq", r"\ne", r"\approx", r"\equiv", r"\sim", r"\simeq",
    r"\cong", r"\propto", r"\ll", r"\gg", r"\rightarrow", r"\to", r"\leftarrow", r"\Rightarrow", r"\Leftarrow",
    r"\Leftrightarrow", r"\mapsto", r"\in", r"\ni", r"\subset", r"\subseteq", r"\supset", r"\supseteq",
    r"\models", r"\vdash", r"\perp", r"\parallel", r"\doteq", r"\triangleq", r"\coloneqq",
)
_OPENERS = (r"\left", r"\begin")
_CLOSERS = (r"\right", r"\end")


def _align_row(latex: str) -> str:
    """Put an alignment mark before the first top-level relation of a row (as authors do).

    "Top level" means outside braces, brackets, `\\left...\\right` pairs and
    inner environments: an `&` inside any of those is a LaTeX error and would
    stop the whole block from rendering.
    """
    depth = 0
    i = 0
    n = len(latex)
    while i < n:
        ch = latex[i]
        if ch in "{[":
            depth += 1
        elif ch in "}]":
            depth = max(0, depth - 1)
        elif ch == "\\":
            word = _command_at(latex, i)
            if word in _OPENERS:
                depth += 1
            elif word in _CLOSERS:
                depth = max(0, depth - 1)
            elif depth == 0 and word in _RELATIONS:
                return latex[:i] + "&" + latex[i:]
            i += max(1, len(word))
            continue
        elif depth == 0 and ch in "=<>":
            return latex[:i] + "&" + latex[i:]
        i += 1
    return latex


def _command_at(latex: str, i: int) -> str:
    """The control word starting at latex[i] (a backslash), e.g. `\\leq`."""
    j = i + 1
    while j < len(latex) and latex[j].isalpha():
        j += 1
    if j == i + 1:  # control symbol such as `\\,` or `\\\\`
        j = min(len(latex), i + 2)
    return latex[i:j]


def display_formula_blocks(page: Page, region_boxes: list[BBox]) -> list[Block]:
    """FORMULA blocks for each formula region.

    A region with one equation line becomes one `$$...$$` block. Several rows
    that sit close together (a multi-line derivation, a system of equations)
    become a single `aligned` block with each row aligned on its first relation,
    which is how authors write them; a reader (and the benchmark) treats the
    block as one formula. Rows separated by a clear vertical gap stay separate.
    """
    blocks: list[Block] = []
    if page.quality.kind == "ocr-truedoc":
        return _ocr_formula_blocks(page, region_boxes)
    rules = page_rules(page)
    for rb in region_boxes:
        # A glyph belongs to the region when its box centre or its x-height point
        # (from the baseline, which symbol fonts with deep descenders cannot skew)
        # lies inside.
        chars = [c for c in page.chars if rb.contains_point(c.bbox.cx, c.bbox.cy) or rb.contains_point(c.bbox.cx, c.origin_y - 0.3 * c.size)]
        if not chars:
            continue
        gs = [glyph(c.text, c.font, c.size, c.bbox, c.origin_y, c.ink) for c in chars]
        region_rules = [r for r in rules if rb.contains_point(r.cx, r.cy)]
        rows: list[tuple[str, str, BBox]] = []
        for line_glyphs, line_rules in split_display_lines(gs, region_rules):
            try:
                latex, eq_no = reconstruct(line_glyphs, line_rules)
            except Exception:  # a formula must never take the page down with it
                latex, eq_no = "".join(g.ch for g in sorted(line_glyphs, key=lambda g: g.bbox.x0)), ""
            if not latex:
                continue
            rows.append((latex, eq_no, BBox.union_all(g.bbox for g in line_glyphs)))
        if not rows:
            continue
        # Group rows whose vertical gap is small into one block.
        main = page.body_font_size or 10.0
        groups: list[list[tuple[str, str, BBox]]] = [[rows[0]]]
        for prev, row in zip(rows, rows[1:]):
            if row[2].y0 - prev[2].y1 <= 1.6 * main:
                groups[-1].append(row)
            else:
                groups.append([row])
        for grp in groups:
            bbox = BBox.union_all(r[2] for r in grp)
            numbers = [r[1] for r in grp if r[1]]
            if len(grp) == 1:
                text = "$$" + grp[0][0] + "$$"
            else:
                body = " \\\\ ".join(_align_row(r[0]) for r in grp)
                text = "$$\\begin{aligned} " + body + " \\end{aligned}$$"
            if numbers:
                text += " " + " ".join("(" + n + ")" for n in numbers)
            blocks.append(Block(kind=BlockKind.FORMULA, bbox=bbox, text_override=text, provenance="math-textlayer", confidence=0.6))
    return blocks


# Characters the engine read that TeX would otherwise swallow: a brace the
# reader saw is a brace ("x-[3y+{3z-(z-x)+y}-2x]" lost its braces, and three
# checks, as bare grouping in run 49).
_TEX_SPECIALS = str.maketrans({"%": r"\%", "&": r"\&", "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}"})


def _ocr_formula_blocks(page: Page, region_boxes: list[BBox]) -> list[Block]:
    """Formula regions on a page TrueDoc read by OCR: each line as the string the
    engine read, inside `$$...$$`, one per line.

    The rebuild from glyph geometry needs real glyph boxes and fonts; an OCR
    line has neither (its characters are spread evenly over the line box, all in
    one nominal font), so the rebuild invents superscripts, subscripts and
    fractions that are not on the page ("2_{c}c_{2}x" for "2c-x"). The engine's
    own reading, kept whole, says only what it saw (D008/D009).
    """
    blocks: list[Block] = []
    for rb in region_boxes:
        lines = sorted((l for l in page.lines if rb.contains_point(l.bbox.cx, l.bbox.cy)), key=lambda l: (l.bbox.y0, l.bbox.x0))
        rows = []
        for l in lines:
            text = " ".join(w.text for w in l.words).strip()
            if text:
                rows.append("$$" + text.translate(_TEX_SPECIALS) + "$$")
        if not rows:
            continue
        bbox = BBox.union_all(l.bbox for l in lines)
        blocks.append(Block(kind=BlockKind.FORMULA, bbox=bbox, text_override="\n".join(rows), provenance="math-ocr", confidence=0.4))
    return blocks


def block_is_display_math(block: Block) -> bool:
    """A text block set mostly in math fonts is a display formula the layout model missed."""
    chars = [c for l in block.lines for w in l.words for c in w.chars if not c.text.isspace()]
    if len(chars) < 3:
        return False
    math_font = sum(1 for c in chars if is_math_font(c.font))
    if math_font < 0.25 * len(chars):
        return False  # digits and brackets alone are prose (statutes, references), not maths
    # Two or more ordinary words ("variables and") make it a sentence with formulas
    # in it, not a displayed equation.
    prose_words = 0
    for l in block.lines:
        for w in l.words:
            core = w.text.strip(".,;:()[]")
            if len(core) >= 3 and core.isalpha() and w.chars and not any(is_math_font(c.font) for c in w.chars) and core.lower() not in _FUNCS:
                prose_words += 1
    if prose_words >= 2:
        return False
    mathy = sum(1 for c in chars if is_math_font(c.font) or c.text in _OPERATOR_CHARS or c.text.isdigit())
    return mathy >= 0.5 * len(chars) and sum(1 for c in chars if c.text.isalpha() and not is_math_font(c.font)) < 0.35 * len(chars)


def _word_on_fraction(w: Word, rules: list[BBox], words: list[Word]) -> bool:
    """A word sitting just above or just below a short rule, with another word on
    the rule's other side, is a numerator or a denominator: maths, whatever font
    its digits are set in ("1" over "2"). An underlined word has nothing under
    its rule and stays prose."""
    if not rules or not w.chars:
        return False
    size = max((c.size for c in w.chars), default=10.0) or 10.0
    for r in rules:
        if r.x1 - r.x0 > 6.0 * size:
            continue
        overlap = min(r.x1, w.bbox.x1) - max(r.x0, w.bbox.x0)
        if overlap < 0.5 * w.bbox.width:
            continue
        above = w.bbox.y1 - 0.2 * size <= r.cy <= w.bbox.y1 + 0.6 * size
        below = w.bbox.y0 - 0.6 * size <= r.cy <= w.bbox.y0 + 0.2 * size
        if not (above or below):
            continue
        # The other part of the fraction on the far side of the rule.
        for o in words:
            if o is w or min(r.x1, o.bbox.x1) - max(r.x0, o.bbox.x0) < 0.3 * o.bbox.width:
                continue
            osize = max((c.size for c in o.chars), default=size) or size
            if not 0.5 * size <= osize <= 2.0 * size:
                continue  # a headline under a page number is not a denominator
            if above and r.cy < o.bbox.y0 <= r.cy + 1.2 * size:
                return True
            if below and r.cy - 1.2 * size <= o.bbox.y1 < r.cy:
                return True
    return False


_HEADLINE_PT = 40.0  # glyphs larger than this are display type, not formulas


def inline_math_text(line: Line, rules: list[BBox]) -> str:
    """Render a text line, wrapping runs of math-font words in $...$."""
    words = line.words
    if not words:
        return ""
    # Display type (a newspaper headline at 139 pt) is never inline maths unless
    # it is set in a maths font.
    huge = [bool(w.chars) and max(c.size for c in w.chars) > _HEADLINE_PT and not any(is_math_font(c.font) for c in w.chars) for w in words]
    flags = [not huge[i] and (_word_is_math(w) or _word_on_fraction(w, rules, words)) for i, w in enumerate(words)]
    if not any(flags):
        return line.text
    # An upright word glued to the maths that follows it, with no space at all
    # ("Fix(Q)", "supp(m)", "Cont(X, G)"), is an operator name set in \mathrm or
    # \operatorname: it belongs to the formula.
    lsize = line.size or 10.0
    for i in range(len(words) - 1):
        w, nxt = words[i], words[i + 1]
        if flags[i] or not flags[i + 1]:
            continue
        if (2 <= len(w.text) <= 12 and w.text.isalpha() and nxt.text[:1] in "([{" and nxt.bbox.x0 - w.bbox.x1 <= 0.15 * lsize
                and any(is_math_font(c.font) for c in nxt.chars)):
            flags[i] = True
    # An equation set wholly in the text fonts: a formula-shaped word ("conv(v)",
    # "std(44425533116)") on either side of a bare relation sign ("=") is maths
    # even when no glyph comes from a maths font (2503.08911).
    for i, w in enumerate(words):
        if flags[i] or huge[i]:
            continue
        if not _FORMULA_SHAPED.fullmatch(w.text.rstrip(".,;:")):
            continue
        for j in (i - 1, i + 1):
            if 0 <= j < len(words) and words[j].text in _RELATION_WORDS and not huge[j]:
                flags[i] = True
                flags[j] = True
    # A run of dots and commas between two formula words is part of the formula:
    # a set "{τ1, . . . , τN}" reaches the layer as a maths word, five one-
    # character text-font words and a maths word, and a reader writes it as one
    # sequence (the single-word bridge below cannot chain through the run).
    i = 0
    while i < len(words):
        if not flags[i] or huge[i]:
            i += 1
            continue
        j = i + 1
        while j < len(words) and not flags[j] and not huge[j] and len(words[j].text) <= 2 and all(ch in ".,;…" for ch in words[j].text):
            j += 1
        if j < len(words) and flags[j] and 2 <= j - i <= 7:
            for k in range(i + 1, j):
                flags[k] = True
            i = j
        else:
            i += 1
    # Bridge single non-math words between math words when they are function names,
    # operators, numbers or symbols; and absorb operator/number words adjacent to a maths word.
    changed = True
    while changed:
        changed = False
        for i, w in enumerate(words):
            if flags[i] or huge[i]:
                continue
            left = i > 0 and flags[i - 1]
            right = i < len(words) - 1 and flags[i + 1]
            t = w.text.strip("()").lower()
            if left and right and (t in _FUNCS or len(w.text) <= 1 or _word_is_math_neighbour(w)):
                flags[i] = True
                changed = True
            elif (left or right) and ((_word_is_math_neighbour(w) and (any(ch in _OPERATOR_CHARS for ch in w.text) or w.text.strip(".,;").isdigit())) or _variable_with_script(w) or _text_term(w)):
                flags[i] = True
                changed = True
            elif (left or right) and _single_italic_letter(w):
                # Documents set in Times use the text italic for maths variables ("x" before "=").
                flags[i] = True
                changed = True
            elif left and w.text == "!" and w.bbox.x0 - words[i - 1].bbox.x1 <= 0.15 * lsize:
                # A factorial sign glued to the maths before it ("(l-m)!" split into two words).
                flags[i] = True
                changed = True
            elif right and w.text.isupper() and 2 <= len(w.text) <= 5 and words[i + 1].text[:1] in _RELATION_CHARS:
                # An upright run of capitals before a relation ("TOL = 10^-6", "SNR > 3") is an identifier.
                flags[i] = True
                changed = True
            elif right and t in _FUNCS and words[i + 1].bbox.x0 - w.bbox.x1 <= 0.4 * lsize:
                # A function name opens the formula ("ker F_n", "log |a|"): it belongs to it.
                flags[i] = True
                changed = True
    # Short connective phrases between two formulas ("for all", "if", "and",
    # "where") belong to one formula as \text{...}: that is how such lines are
    # written, and how the references read them.
    i = 0
    while i < len(words):
        if flags[i] or not (i > 0 and flags[i - 1]):
            i += 1
            continue
        j = i
        while j < len(words) and not flags[j] and j - i < 3 and words[j].text.strip(".,;:").lower() in _CONNECTIVES:
            j += 1
        if j > i and j < len(words) and flags[j]:
            for k in range(i, j):
                flags[k] = True
            changed = True
        i = max(j, i + 1)
    out: list[str] = []
    i = 0
    while i < len(words):
        if not flags[i]:
            out.append(words[i].text)
            i += 1
            continue
        j = i
        while j < len(words) and flags[j]:
            j += 1
        run = words[i:j]
        gs = [g for w in run for g in _line_glyphs_word(w)]
        # A piece of an extensible brace that MuPDF put on this line but that sits
        # far from its baseline belongs to the display formula above or below.
        base = line.baseline or line.bbox.y1
        gs = [g for g in gs if not (is_piece_glyph(g.ch, g.font) and abs(g.oy - base) > 0.6 * (line.size or 10.0))]
        # Prose glued to the formula without a space (a word such as "that" or
        # "generator" attached to the last symbol): a run of two or more
        # a run of two or more text-font letters at either end is not part of the maths.
        gs, lead_word, trail_word = _trim_prose(gs)
        # Sentence punctuation glued to the last symbol belongs to the prose, not the formula.
        trail = ""
        while gs and gs[-1].ch in ".,;:!?" and not gs[-1].is_math:
            # "n!" is a factorial when the "!" is glued to the maths glyph before it
            # (the "i!" under "t^i/i!" ends the formula, not the sentence).
            if gs[-1].ch == "!" and len(gs) > 1 and (gs[-2].is_math or gs[-2].ch in ")]") \
                    and gs[-1].bbox.x0 - gs[-2].bbox.x1 <= 0.2 * max(gs[-2].size, 1.0):
                break
            trail = gs[-1].ch + trail
            gs = gs[:-1]
        trail = trail + trail_word
        # A leading bracket stays inside the formula: an extra glyph at the edge of a
        # formula is harmless, a missing one is not.
        lead = ""
        try:
            latex, _ = reconstruct(gs, [r for r in rules if _rule_near(r, run)], strip_equation_number=False, display=False)
        except Exception:  # fall back to the plain words rather than lose the line
            latex = ""
        # A lone symbol ("|", "-", "*") is punctuation in prose, not a formula.
        if latex and len(gs) <= 2 and not any(g.ch.isalpha() or g.ch in _GREEK_AND_SYMBOLS for g in gs):
            latex = ""
        if latex:
            out.append(lead_word + lead + "$" + latex + "$" + trail)
        else:
            out.append(" ".join(w.text for w in run))
        i = j
    return " ".join(out)


def _trim_prose(gs: list[Glyph]) -> tuple[list[Glyph], str, str]:
    """Split off leading/trailing runs of >=2 text-font letters (ordinary words).

    Only full-size letters count: a small upright word is a subscript such as
    N_{init} and belongs to the formula.
    """
    main = max((g.size for g in gs), default=0.0)

    def is_prose(g: Glyph) -> bool:
        return g.ch.isalpha() and not g.is_math and g.ch not in _GREEK_AND_SYMBOLS and g.size >= 0.85 * main

    def is_word(text: str) -> bool:
        # An upright run of capitals next to a relation ("TOL = 10^-6", "SNR") is an
        # identifier, part of the formula; only an ordinary word is prose.
        return text.lower() not in _FUNCS and not text.isupper()

    lead = ""
    k = 0
    while k < len(gs) and is_prose(gs[k]):
        k += 1
    # An upright word glued to an opening bracket ("Fix(Q)", "supp(m)") is an
    # operator name, part of the formula, however ordinary the word looks.
    glued_operator = (2 <= k < len(gs) and gs[k].ch in "([{" and gs[k].bbox.x0 - gs[k - 1].bbox.x1 <= 0.15 * main
                      and any(g.is_math for g in gs[k:]))
    if k >= 2 and k < len(gs) and is_word("".join(g.ch for g in gs[:k])) and not glued_operator:
        lead = "".join(g.ch for g in gs[:k])
        gs = gs[k:]
    trail = ""
    k = len(gs)
    while k > 0 and is_prose(gs[k - 1]):
        k -= 1
    n = len(gs) - k
    if n >= 2 and k > 0 and is_word("".join(g.ch for g in gs[k:])) and not _differential(gs[k:]):
        trail = "".join(g.ch for g in gs[k:])
        gs = gs[:k]
    return gs, lead, trail


def _differential(gs: list[Glyph]) -> bool:
    """"dx", "dt" set in the text italic at the end of an integral (2503.04536):
    two italic letters starting with d are the differential, not a word."""
    if len(gs) != 2 or gs[0].ch != "d" or not gs[1].ch.isalpha():
        return False
    low = gs[1].font.lower()
    return "ital" in low or "oblique" in low or low.endswith("-it")


_FUNCS = {"span", "rank", "tr", "diag", "codim", "grad", "curl", "liminf", "limsup",
          "sin", "cos", "tan", "cot", "sec", "csc", "log", "ln", "exp", "lim", "max", "min", "sup", "inf", "det", "dim", "ker", "deg", "gcd", "mod", "arg","sinh", "cosh", "tanh", "arcsin", "arccos", "arctan", "tr", "rank", "span", "diag", "var", "cov", "pr",
          "range", "im", "re", "supp", "hom", "end", "aut", "spec", "proj", "conv", "cl", "int", "sgn", "lcm", "argmax", "argmin", "col", "row", "null", "vol", "id", "sim", "dist", "card", "ord"}


def _line_glyphs_word(w: Word) -> list[Glyph]:
    return [glyph(c.text, c.font, c.size, c.bbox, c.origin_y, c.ink) for c in w.chars]


def _rule_near(r: BBox, run: list[Word]) -> bool:
    bb = BBox.union_all(w.bbox for w in run)
    return r.x0 >= bb.x0 - 2 and r.x1 <= bb.x1 + 2 and r.cy >= bb.y0 - 2 and r.cy <= bb.y1 + 2


_GREEK_AND_SYMBOLS = set("αβγδεϵζηθϑικλμνξπϖρϱσςτυφϕχψωΓΔΘΛΞΠΣΥΦΨΩ∈∉≤≥≠≈≡∼≃∞∂∇∑∏∫√→←↔⇒⇐⇔↦∀∃∅⊂⊃⊆⊇∪∩⊕⊗⊥∥∧∨¬ℓℏℜℑℝℕℤℚℂ⟨⟩")
# The Adobe glyph list delivers "Omega", "Delta" and "mu" from text fonts as the ohm,
# increment and micro signs.
_GREEK_AND_SYMBOLS |= {"Ω", "∆", "µ"}


def _word_is_math(w: Word) -> bool:
    """Words carrying a glyph from a maths font, a Greek letter or a maths symbol.

    Purely numeric or operator-only words ("2010-2015", "p<0.05") are left
    alone: wrapping them in $...$ would change ordinary prose.
    """
    if not w.chars:
        return False
    return any(is_math_font(c.font) or c.text in _GREEK_AND_SYMBOLS for c in w.chars)


def _variable_with_script(w: Word) -> bool:
    """An italic letter carrying a smaller script ("X^{Test}", "S_n") in a document
    whose maths is set in the text fonts: a variable, not a word."""
    chars = [c for c in w.chars if not c.text.isspace()]
    # A text-font accent over the letter ("\tilde{\mathbf u}_1" set in cmbx on
    # 2503.04033) comes as its own character; a bold letter is a variable too.
    while chars and (chars[0].text in "([{" or chars[0].text in "˜ˆ¯´`¨˙ˇ˘~^"):
        chars = chars[1:]
    if not chars or not chars[0].text.isalpha() or not (chars[0].italic or chars[0].bold):
        return False
    big = max(c.size for c in chars)
    return any(c.size < 0.85 * big and (c.text.isalnum() or c.text in "+-*′") for c in chars[1:])


def _single_italic_letter(w: Word) -> bool:
    """A lone italic or bold letter is a variable when it sits next to maths."""
    core = w.text.strip("(),.;:")
    return len(core) == 1 and core.isalpha() and bool(w.chars) and all((c.italic or c.bold) for c in w.chars if c.text.isalpha())


_PUNCT_WORD = set(":;,.=+-*/<>|!?()[]{}'\"^_~&%$#@\\")
_CONNECTIVES = {"for", "all", "and", "or", "if", "iff", "where", "with", "such", "that", "then", "otherwise", "s.t", "st", "when", "some", "every", "in", "on", "as", "whenever", "else", "resp"}
_FORMULA_SHAPED = re.compile(r"[A-Za-z]{1,5}(\[[A-Za-z0-9,]+\]|\([A-Za-z0-9,]+\))")   # "f(x)", "E[T]", "std(w)", "conv(w)"


_RELATION_WORDS = {"=", ":=", "=:", "≤", "≥", "<", ">", "≠", "≈", "∈", "⊂", "⊆", "∼", "≡", "≃", "≅"}
_TERM_SHAPED = re.compile(r"[0-9]*[A-Za-z]?(?:[-+*/][0-9]*[A-Za-z]?){0,4}")   # "4k+1", "2n", "k-1"
_OPEN_APPLICATION = re.compile(r"[A-Za-z]{1,2}\([A-Za-z0-9]{1,6}")             # "V(BS" closed in a later word


def _text_term(w: Word) -> bool:
    """A term set wholly in the text fonts, as Times-based maths is ("4k+1" after
    "\\kappa(BS_{n-1})=" on 2503.05442): digits and operators with at most one
    letter per factor, every letter italic; or an italic letter applied to a
    bracket that closes in a later word ("V(BS")."""
    if not w.chars:
        return False
    core = w.text.rstrip(".,;:")
    letters = [c for c in w.chars if c.text.isalpha()]
    if _TERM_SHAPED.fullmatch(core) and letters and all(c.italic for c in letters) \
            and any(ch.isdigit() or ch in "+-*/" for ch in core):
        return True
    # A differential set in the text fonts ("dx", "dt", "dμ": an upright or italic
    # d and an italic variable), the tail of "\int ... \rho_0(x)\,dx" on 2503.04536.
    if len(core) == 2 and core[0] == "d" and core[1].isalpha() and len(letters) == 2 and letters[1].italic:
        return True
    return bool(_OPEN_APPLICATION.fullmatch(core)) and w.chars[0].text.isalpha() and w.chars[0].italic


def _word_is_math_neighbour(w: Word) -> bool:
    """Words that may join a maths run when they sit between maths words."""
    if not w.chars:
        return False
    text = w.text
    if text and all(ch in _PUNCT_WORD or ch in _OPERATOR_CHARS for ch in text) and len(text) <= 4:
        return True  # ":=", "|", "(", "=" between two maths words
    if _FORMULA_SHAPED.fullmatch(text.rstrip(".,;:")):
        return True  # "E[T]", "f(x)", "P(A)": a letter applied to a bracketed argument
    if _text_term(w):
        return True
    sizes = [c.size for c in w.chars]
    if len(set(round(s, 1) for s in sizes)) > 1 and any(c.text.isalnum() for c in w.chars):
        big = max(sizes)
        small = [c for c in w.chars if c.size < 0.85 * big]
        if small and any(c.text.isalnum() for c in small):
            return True
    return all(ch in _OPERATOR_CHARS or ch.isdigit() or ch in ".,;" for ch in text) and len(text) <= 12
