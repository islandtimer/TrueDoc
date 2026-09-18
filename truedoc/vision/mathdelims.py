"""A model's dollar-delimited maths, rewritten into the delimiters the document uses.

D024 says every literal dollar sign in prose is escaped, because a reader's viewer would otherwise read
the stretch between two of them - between two prices, say - as a formula. TrueDoc's own formulas are
written `\\( ... \\)` and `\\[ ... \\]`, so nothing of ours depends on dollar signs and the rule is safe.

A model does not know that. olmOCR 2 happens to answer in our delimiters; a general model answers in the
LaTeX convention it learned, `$ ... $`, and D024 then escapes every one. On old_scans_math/1_pg131 that
turned fourteen integrals into literal text, and the category fell from 80.8 to 64.0 in run 90 - 77
checks, the largest single loss of the project so far.

So a model's maths is translated into the document's own delimiters before anything else sees it. Only
maths is translated: a span has to carry a LaTeX command or a script or a group to count, which leaves
"it costs $5 and $6 today" alone, exactly as D024 intends.
"""

from __future__ import annotations

import re

# $$...$$ first, so its dollars are consumed before the single-dollar pass sees them.
_DISPLAY = re.compile(r"(?<!\\)\$\$(?P<body>.+?)(?<!\\)\$\$", re.S)
_DOLLAR = re.compile(r"(?<!\\)\$")

# What makes a span maths rather than money: a command, a script, a group, or an equals sign. The last
# one earns its place on the same page as the rest of this: "let $p=x$ $dp = dx$" has no command and no
# script in it, and without `=` those two equations stayed dollar-delimited and were escaped into text.
# A stretch between two prices does not hold an equals sign ("between $5 and $6" gives "5 and "), so
# money is still left for D024.
_MATHS = re.compile(r"\\[A-Za-z]+|[\^_{}=]|\\[\\\[\](){}]")

# The second kind of maths has none of those: a variable, a function of one, an expression of letters
# and brackets - "$f(1)$", "$P$", "$a + [b - (a - b)]$". An algebra textbook's page is full of them
# (old_scans_math/4_pg380 and 4_pg48, 18 September), and escaping them into text cost seven checks with
# every reader that writes maths between dollars. Such a span is maths when it holds a letter, every
# word in it is a single letter or the name of a function, and nothing in it is outside the characters
# an expression is written with. Money fails all three ways: "5 and " has a word, "5, " has no letter,
# and a number followed by a word ("5 a day") is the shape of a price and not of a formula.
_LETTER_RUNS = re.compile(r"[^\W\d_]+")
_EXPRESSION = re.compile(r"^[\w\s+\-*/.,;:()\[\]|'!<>~\u00b7\u00d7\u00f7\u00b1\u2212]+$")
_PRICE_LEAD = re.compile(r"^\s*\d[\d,.]*\s+[^\W\d_]")
_FUNCTIONS = frozenset("sin cos tan cot sec csc log ln exp lim max min sup inf det dim deg gcd mod arg "
                       "sinh cosh tanh sqrt".split())


def _looks_algebraic(body: str) -> bool:
    body = body.strip()
    if not body or _PRICE_LEAD.match(body) or not _EXPRESSION.match(body):
        return False
    words = _LETTER_RUNS.findall(body)
    return bool(words) and all(len(w) == 1 or w.lower() in _FUNCTIONS for w in words)


def _is_maths(body: str) -> bool:
    return bool(body.strip()) and (bool(_MATHS.search(body)) or _looks_algebraic(body))


def _inline(text: str) -> str:
    """Pair up the single dollars, preferring the pairing that is maths.

    Left to right and greedy is wrong on a line that holds both: in "the fee is $5 and $\\int x dx$" the
    first dollar pairs with the second, the span "5 and " is not maths, and the formula is then left
    with one dollar and no partner. So a pairing that is not maths does not consume its opening dollar -
    the scan moves on to the next one and tries again, which finds the formula.
    """
    spots = [m.start() for m in _DOLLAR.finditer(text)]
    out, last, i = [], 0, 0
    while i < len(spots) - 1:
        open_at, close_at = spots[i], spots[i + 1]
        body = text[open_at + 1:close_at]
        if "\n" in body or not _is_maths(body):
            i += 1
            continue
        out.append(text[last:open_at])
        out.append("\\(" + body + "\\)")
        last = close_at + 1
        i += 2
    out.append(text[last:])
    return "".join(out)


# A model transcribes a column of equations as one aligned environment, and the page holds a column of
# equations: each row is an equation of its own, which is how the reader meets them and how a reference
# transcription writes them (old_scans_math/3_pg39, 18 September: "x' = ax + by + cz" over "y' = ..."
# over "z' = ...", four checks). A row is written as a display formula by itself, its alignment marks
# dropped, so a row that continues a derivation reads "= ..." as the page prints it. Only the aligned
# family is split: a matrix or a cases brace is one object, and its rows are not equations.
_ALIGNED = re.compile(r"\\begin\{(aligned|align\*?|gather\*?|split|eqnarray\*?)\}(?P<rows>.*?)\\end\{\1\}", re.S)
_ROW_BREAK = re.compile(r"\\\\(?:\[[^\]]*\])?")
_ALIGN_MARK = re.compile(r"(?<!\\)&")
_EQUATION_NUMBER = re.compile(r"(?:\\q?quad\s*)*(?:\(\d+[a-z]?\)|\\tag\{[^}]*\})\s*")


def _aligned_rows(body: str) -> list[str] | None:
    """The pieces of a display formula holding an aligned environment of two rows or more: what came
    before it, each row, what came after it (old_scans_math/3_pg39 sets a bracketed alternative after
    the column, "& \\left( \\text{or} ... \\right)"), each a formula of its own; or None."""
    m = _ALIGNED.search(body)
    if not m:
        return None
    rows = [_ALIGN_MARK.sub("", r).strip() for r in _ROW_BREAK.split(m.group("rows"))]
    rows = [re.sub(r"\s+", " ", r) for r in rows if r.strip()]
    # An equation number set as a row of its own ("& (12)") belongs to the equation above it.
    merged: list[str] = []
    for r in rows:
        if merged and _EQUATION_NUMBER.fullmatch(r):
            merged[-1] = merged[-1] + " " + r
        else:
            merged.append(r)
    rows = merged
    if len(rows) < 2:
        return None
    before = re.sub(r"\s+", " ", _ALIGN_MARK.sub("", body[:m.start()])).strip()
    after = re.sub(r"\s+", " ", _ALIGN_MARK.sub("", body[m.end():])).strip()
    return [p for p in [before, *rows, after] if p]


# A model sometimes closes a formula and opens the next in the middle of one expression, so that
# "$...- 7n\\}$ $+ [9m - ...]$" is one sum of the page's written as two (old_scans_math/4_pg48). Two
# inline formulas with nothing but blanks between them are joined when the seam is an operator: the
# first ends with one or the second begins with one. "$x$ $y$" is left as two, because it may be two.
_OPERATOR_END = re.compile(r"[-+=<>*/\u00b1\u2212]\s*$|\\(?:cdot|times|pm|mp|div|leq|geq|neq|le|ge|ne|to)\s*$")
_OPERATOR_START = re.compile(r"^\s*(?:[-+=<>*/\u00b1\u2212]|\\(?:cdot|times|pm|mp|div|leq|geq|neq|le|ge|ne|to)\b)")
_SEAM = re.compile(r"\\\((?P<a>[^\n]*?)\\\)[ \t]+\\\((?P<b>[^\n]*?)\\\)")


def _join_split_expressions(text: str) -> str:
    def seam(m: re.Match) -> str:
        a, b = m.group("a"), m.group("b")
        if _OPERATOR_END.search(a) or _OPERATOR_START.search(b):
            return "\\(" + a.rstrip() + " " + b.lstrip() + "\\)"
        return m.group(0)

    before = None
    while before != text:  # three pieces need two passes
        before, text = text, _SEAM.sub(seam, text)
    return text


def normalise_math_delimiters(text: str) -> str:
    """Rewrite a model's `$...$` and `$$...$$` maths as `\\(...\\)` and `\\[...\\]`."""
    if not text or "$" not in text:
        return text

    def display(m: re.Match) -> str:
        body = m.group("body")
        if not _is_maths(body):
            return m.group(0)
        rows = _aligned_rows(body)
        if rows:
            return "\n\n".join("\\[" + r + "\\]" for r in rows)
        return "\\[" + body + "\\]"

    return _join_split_expressions(_inline(_DISPLAY.sub(display, text)))
