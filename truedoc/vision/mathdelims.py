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


def normalise_math_delimiters(text: str) -> str:
    """Rewrite a model's `$...$` and `$$...$$` maths as `\\(...\\)` and `\\[...\\]`."""
    if not text or "$" not in text:
        return text

    def display(m: re.Match) -> str:
        body = m.group("body")
        return "\\[" + body + "\\]" if _is_maths(body) else m.group(0)

    return _inline(_DISPLAY.sub(display, text))
