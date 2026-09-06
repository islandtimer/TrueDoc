"""Symbol tables: Unicode and TeX-font glyph codes -> LaTeX."""

from __future__ import annotations

# Unicode characters that need a LaTeX command inside math mode.
UNICODE_TO_LATEX: dict[str, str] = {
    "∶": ":", "∷": "::",   # RATIO and PROPORTION: some fonts name their colon so
    "〈": r"\langle", "〉": r"\rangle", "⟨": r"\langle", "⟩": r"\rangle",   # angle brackets, CJK-coded in some fonts
    "◁": r"\lhd", "▷": r"\rhd", "⊲": r"\lhd", "⊳": r"\rhd", "○": r"\circ",   # normal-subgroup triangles; a ring drawn as a white circle
    "⋊": r"\rtimes", "⋉": r"\ltimes",   # semidirect products
    "⋆": r"\star",   # star operator (V_\epsilon^\star)
    "⋀": r"\bigwedge", "⋁": r"\bigvee", "⋂": r"\bigcap", "⋃": r"\bigcup",   # n-ary operators as Unicode (they take limits)
    # Greek lower
    "α": r"\alpha", "β": r"\beta", "γ": r"\gamma", "δ": r"\delta", "ε": r"\varepsilon", "ϵ": r"\epsilon",
    "ǫ": r"\varepsilon",  # some maths fonts (MathDesign) name their varepsilon so that MuPDF returns o-ogonek
    "⊢": r"\vdash", "⊣": r"\dashv", "⊨": r"\models", "⊩": r"\Vdash",
    "ζ": r"\zeta", "η": r"\eta", "θ": r"\theta", "ϑ": r"\vartheta", "ι": r"\iota", "κ": r"\kappa",
    "λ": r"\lambda", "μ": r"\mu", "ν": r"\nu", "ξ": r"\xi", "π": r"\pi", "ϖ": r"\varpi", "ρ": r"\rho",
    "ϱ": r"\varrho", "σ": r"\sigma", "ς": r"\varsigma", "τ": r"\tau", "υ": r"\upsilon", "φ": r"\varphi",
    "ϕ": r"\phi", "χ": r"\chi", "ψ": r"\psi", "ω": r"\omega", "µ": r"\mu",
    # Greek upper
    "Γ": r"\Gamma", "Δ": r"\Delta", "Θ": r"\Theta", "Λ": r"\Lambda", "Ξ": r"\Xi", "Π": r"\Pi",
    "Σ": r"\Sigma", "Υ": r"\Upsilon", "Φ": r"\Phi", "Ψ": r"\Psi", "Ω": r"\Omega",
    "∆": r"\Delta", "Ω": r"\Omega", "∏": r"\prod", "∑": r"\sum",
    # The Adobe glyph list maps the glyph names "Omega" and "Delta" to the ohm and
    # increment signs, so text fonts deliver those; KaTeX rejects them in maths.
    "Ω": r"\Omega", "∆": r"\Delta", "µ": r"\mu",
    # Operators and relations
    "−": "-", "–": "-", "—": "-", "·": r"\cdot", "⋅": r"\cdot", "∕": "/", "×": r"\times", "÷": r"\div", "±": r"\pm", "∓": r"\mp",
    "∗": "*", "∘": r"\circ", "◦": r"\circ", "•": r"\bullet", "⊥": r"\perp", "⊤": r"\top",
    "≤": r"\leq", "≥": r"\geq", "≠": r"\neq", "≈": r"\approx", "≡": r"\equiv", "∼": r"\sim", "≃": r"\simeq",
    "≅": r"\cong", "∝": r"\propto", "≪": r"\ll", "≫": r"\gg", "⩽": r"\leqslant", "⩾": r"\geqslant",
    "≺": r"\prec", "≻": r"\succ", "⪯": r"\preceq", "⪰": r"\succeq",
    "∈": r"\in", "∉": r"\notin", "∋": r"\ni", "⊂": r"\subset", "⊃": r"\supset", "⊆": r"\subseteq",
    "⊇": r"\supseteq", "∪": r"\cup", "∩": r"\cap", "∖": r"\setminus", "∅": r"\emptyset", "⊕": r"\oplus",
    "⊗": r"\otimes", "⊙": r"\odot", "⊖": r"\ominus", "⊥": r"\perp", "∧": r"\wedge",
    "∨": r"\vee", "¬": r"\neg", "∀": r"\forall", "∃": r"\exists", "∄": r"\nexists",
    "→": r"\rightarrow", "←": r"\leftarrow", "↔": r"\leftrightarrow", "⇒": r"\Rightarrow", "⇐": r"\Leftarrow",
    "⇔": r"\Leftrightarrow", "↦": r"\mapsto", "↑": r"\uparrow", "↓": r"\downarrow", "⟶": r"\longrightarrow",
    "⟵": r"\longleftarrow", "⟹": r"\Longrightarrow", "⟺": r"\Longleftrightarrow",
    "∞": r"\infty", "∂": r"\partial", "∇": r"\nabla", "∑": r"\sum", "∏": r"\prod", "∐": r"\coprod",
    "∫": r"\int", "∬": r"\iint", "∭": r"\iiint", "∮": r"\oint", "√": r"\sqrt", "∠": r"\angle",
    "ℓ": r"\ell", "ℏ": r"\hbar", "ℑ": r"\Im", "ℜ": r"\Re", "℘": r"\wp", "ℵ": r"\aleph",
    "′": r"\prime", "″": r"\prime\prime", "°": r"^{\circ}", "†": r"\dagger", "‡": r"\ddagger",
    "…": r"\ldots", "⋯": r"\cdots", "⋮": r"\vdots", "⋱": r"\ddots",
    "⟨": r"\langle", "⟩": r"\rangle", "〈": r"\langle", "〉": r"\rangle", "⌊": r"\lfloor", "⌋": r"\rfloor",
    "⌈": r"\lceil", "⌉": r"\rceil", "‖": r"\Vert", "∥": r"\Vert", "|": "|",
    "ℝ": r"\mathbb{R}", "ℕ": r"\mathbb{N}", "ℤ": r"\mathbb{Z}", "ℚ": r"\mathbb{Q}", "ℂ": r"\mathbb{C}",
    "𝔼": r"\mathbb{E}", "ℙ": r"\mathbb{P}",
    "{": r"\{", "}": r"\}", "%": r"\%", "&": r"\&", "#": r"\#", "_": r"\_", "$": r"\$",
    " ": " ", "ﬁ": "fi", "ﬂ": "fl",
}

# Computer Modern math extension font (cmex10): raw codes -> LaTeX. Only the
# entries that matter for reconstruction; anything else is dropped.
CMEX_TO_LATEX: dict[str, str] = {
    "\x50": r"\sum", "\x58": r"\sum",
    "\x51": r"\prod", "\x59": r"\prod",
    "\x52": r"\int", "\x5a": r"\int",
    "\x48": r"\oint", "\x49": r"\oint",
    "\x60": r"\coprod", "\x61": r"\coprod",
    "\x53": r"\bigcup", "\x5b": r"\bigcup",
    "\x54": r"\bigcap", "\x5c": r"\bigcap",
    "\x4c": r"\bigoplus", "\x4d": r"\bigoplus",
    "\x4e": r"\bigotimes", "\x4f": r"\bigotimes",
    "\x55": r"\biguplus", "\x5d": r"\biguplus",
    "\x56": r"\bigwedge", "\x5e": r"\bigwedge",
    "\x57": r"\bigvee", "\x5f": r"\bigvee",
    "\x70": r"\sqrt", "\x71": r"\sqrt", "\x72": r"\sqrt", "\x73": r"\sqrt", "\x74": r"\sqrt", "\x75": r"\sqrt", "\x76": r"\sqrt",
    "\x00": "(", "\x01": ")", "\x02": "[", "\x03": "]", "\x04": r"\lfloor", "\x05": r"\rfloor",
    "\x06": r"\lceil", "\x07": r"\rceil", "\x08": r"\{", "\x09": r"\}", "\x0a": r"\langle", "\x0b": r"\rangle",
    "\x0c": r"\big|", "\x0d": r"\big\|", "\x0e": "/", "\x0f": r"\backslash",  # a bar from cmex is a sized bar
    "\x10": "(", "\x11": ")", "\x12": "(", "\x13": ")", "\x14": "[", "\x15": "]", "\x16": r"\lfloor", "\x17": r"\rfloor",
    "\x18": r"\lceil", "\x19": r"\rceil", "\x1a": r"\{", "\x1b": r"\}", "\x1c": r"\langle", "\x1d": r"\rangle",
    "\x1e": "/", "\x1f": r"\backslash",
    "\x20": "(", "\x21": ")", "\x22": "[", "\x23": "]", "\x24": r"\lfloor", "\x25": r"\rfloor",
    "\x26": r"\lceil", "\x27": r"\rceil", "\x28": r"\{", "\x29": r"\}", "\x2a": r"\langle", "\x2b": r"\rangle",
    "\x2c": "/", "\x2d": r"\backslash", "\x2e": "/", "\x2f": r"\backslash",
    "\x30": "(", "\x31": ")", "\x32": "[", "\x33": "]", "\x34": r"\lfloor", "\x35": r"\rfloor",
    "\x36": r"\lceil", "\x37": r"\rceil", "\x38": r"\{", "\x39": r"\}", "\x3a": r"\langle", "\x3b": r"\rangle",
    "\x3c": r"\big|", "\x3d": r"\big\|", "\x3e": "/", "\x3f": r"\backslash",
    "\x40": "(", "\x41": ")", "\x42": "[", "\x43": "]", "\x44": r"\Bigg\langle", "\x45": r"\Bigg\rangle",   # cmex 0x44/0x45 are the largest angle brackets
    "\x46": r"\bigsqcup", "\x47": r"\bigsqcup",   # cmex 0x46/0x47 are the square-cup operators, not ceilings
    "\x62": r"\hat{}", "\x63": r"\hat{}", "\x64": r"\hat{}", "\x65": r"\tilde{}", "\x66": r"\tilde{}", "\x67": r"\tilde{}",
    "\x68": "[", "\x69": "]", "\x6a": r"\lfloor", "\x6b": r"\rfloor", "\x6c": r"\lceil", "\x6d": r"\rceil",
    "\x6e": r"\{", "\x6f": r"\}",
    "\x77": r"\big\|", "\x78": r"\uparrow", "\x79": r"\downarrow", "\x7a": "", "\x7b": "", "\x7c": "", "\x7d": "",
    "\x7e": r"\Uparrow", "\x7f": r"\Downarrow",
}

# Words set upright (roman) inside formulas that are LaTeX function names.
FUNCTION_NAMES = {
    "sin", "cos", "tan", "cot", "sec", "csc", "arcsin", "arccos", "arctan", "sinh", "cosh", "tanh", "coth",
    "log", "ln", "lg", "exp", "lim", "liminf", "limsup", "max", "min", "sup", "inf", "det", "dim", "ker", "deg",
    "gcd", "hom", "arg", "Pr", "mod",
}

BIG_OPERATORS = {r"\sum", r"\prod", r"\int", r"\oint", r"\coprod", r"\bigcup", r"\bigcap", r"\bigoplus", r"\bigotimes", r"\bigvee", r"\bigwedge", r"\iint", r"\iiint",
                 r"\bigsqcup", r"\bigodot", r"\biguplus"}


# mathabx symbol fonts (TeX-matha / mathb / mathx): no ToUnicode, codes come back as
# ordinary characters. Only mappings confirmed on real pages are listed.
# newtx/newpx extension fonts (txex/pxex) add glyphs above 0x7F to the cmex
# layout; the ones met so far, by the reference that named them.
_TXEX_RAW: dict[str, str] = {
    "Ö": r"\prod",   # 2503.04527: a display product with limits above and below
}


_MATHABX_RAW: dict[str, str] = {
    "p": "(", "q": ")", "r": "[", "s": "]", "b": r"\otimes", "a": r"\oplus", "`": "+", "“": "=",
    "K": r"\perp", "‚": r"\bullet", "Þ": "|", "Ñ": r"\rightarrow", "˚": "*", "˝": r"\circ",   # "˚" is the asterisk: \tau_* on 2503.09552 and 2503.05000
    "À": r"\lesssim",   # "|O_3(k_1)| À |k_1|^3"
    "B": r"\partial",   # "\frac{BS_t}{Bt}" on 2503.05000
    "}": r"\|", "8": r"\infty",   # "\sup_n }\sum e_i} < 8" on 2503.06880
    "1": r"\prime", "ˆ": r"\times",   # "f^{1}" for f', "X ˆ X" for X \times X on 2503.04488 (matha has no digits)
    "9": r"\dot{}",   # mathb's dot accent: "F^{9...}" for \dot{F} on 2503.04604
    "´": "-", "¨": r"\cdot", "ą": ">", "ă": "<", "ř": r"\sum", "ś": r"\prod", "ş": r"\int",
    "t": r"\{", "u": r"\}",  # braces ("\lbrace E_1, E_2 \rbrace" arrives as "tE_1, E_2u")
    "P": r"\in", "ď": r"\leq", "ě": r"\geq",   # element sign and the two inequalities ("f P L^2", "0 ď s ď t")
    "‰": r"\neq",   # "i ‰ j"
    "«": r"\approx", "‹": r"\star",   # "k « K_‹" (2503.08996)
    # Read off a contact sheet of every matha glyph on the benchmark pages (4 Sept).
    "!": r"\ll", '"': r"\gg", "6": r"\natural", ":": r"\dagger", "?": r"\sqrt", "@": r"\forall",
    "R": r"\notin", "X": r"\cap", "z": r"\setminus", "{": "/", "|": "|", "»": r"\simeq",
    "Ă": r"\subset", "Ď": r"\subseteq", "Ź": r"\triangleright", "˘": r"\pm", "˙": r"\ltimes",
    "–": r"\cong", "‘": r"\bigoplus", "”": r"\equiv", "„": r"\sim",
}

# mathb (matha's companion): a few codes mean something else there.
_MATHB_RAW: dict[str, str] = {
    "#": r"\#", ">": r"\angle", "l": r"\square", "ã": r"\hookrightarrow",
}

# mathx, mathabx's extension font: big delimiters in several sizes, big operators,
# integrals and wide accents. Read off the same contact sheet; codes not listed are
# bracket pieces not yet identified and are dropped rather than guessed.
_MATHX_RAW: dict[str, str] = {
    "!": r"\{", "#": r"\{", "$": r"\{", "%": r"\{", "&": r"\{", "␣": r"\{",
    "(": r"\}", ")": r"\}",
    "`": "(", "ˆ": "(", "˜": "(",
    "¸": ")", "˘": ")", "˙": ")",
    "›": r"\|",
    "ÿ": r"\sum", "ř": r"\sum", "ş": r"\int", "ż": r"\int",
    "´": "(", "¯": ")",   # another size of big parentheses ("\Bigl(u, v, w\Bigr)" on 2503.08646; the "´" seen on 2503.04467 was matha's minus)
    "À": r"\bigoplus", "à": r"\bigoplus", "Ť": r"\bigcup",
    "q": r"\check{}", "r": r"\tilde{}", "x": r"\hat{}", "Ă": r"\tilde{}",   # wide accents
}


# Vertical extent of cmex10 glyphs as (height above the origin, depth below it) in
# em, from the font's design [recalled]. The text layer reports a box for these glyphs
# that comes from the font's ascender and descender, not from the glyph: a
# three-line-tall bracket is reported as one line tall, or as five lines tall.
CMEX_EXTENT: dict[int, tuple[float, float]] = {}
for _c in range(0x00, 0x10):
    CMEX_EXTENT[_c] = (0.04, 1.16)      # delimiters, size 1 (\big)
for _c in (0x10, 0x11, 0x2E, 0x2F):
    CMEX_EXTENT[_c] = (0.04, 1.76)      # size 2 (\Big)
for _c in range(0x12, 0x20):
    CMEX_EXTENT[_c] = (0.04, 2.36)      # size 3 (\bigg)
for _c in range(0x20, 0x2E):
    CMEX_EXTENT[_c] = (0.04, 2.96)      # size 4 (\Bigg)
for _c in range(0x68, 0x70):
    CMEX_EXTENT[_c] = (0.04, 1.76)      # size 2 brackets, floors, ceilings, braces (measured 1.80 em on arXiv pages)

# Fixed-size delimiters carry their size: TeX picked the glyph for \big, \Big,
# \bigg or \Bigg (or \left/\right chose the same one), and the rendering of
# "\Big|" is not the rendering of "|". Measured ink heights on arXiv pages: size
# 1 = 1.20 em, size 2 = 1.80, size 3 = 2.40, size 4 = 3.00.
_DELIMS_IN_ORDER = ["(", ")", "[", "]", r"\lfloor", r"\rfloor", r"\lceil", r"\rceil", r"\{", r"\}", r"\langle", r"\rangle"]
_SIZED_DELIMS: dict[int, str] = {}
for _i, _d in enumerate(_DELIMS_IN_ORDER):
    _SIZED_DELIMS[0x00 + _i] = r"\big" + _d
    _SIZED_DELIMS[0x12 + _i] = r"\bigg" + _d
    _SIZED_DELIMS[0x20 + _i] = r"\Bigg" + _d
_SIZED_DELIMS[0x10], _SIZED_DELIMS[0x11] = r"\Big(", r"\Big)"
for _i, _d in enumerate(_DELIMS_IN_ORDER[2:10]):
    _SIZED_DELIMS[0x68 + _i] = r"\Big" + _d
for _code, _size in ((0x0E, r"\big"), (0x1E, r"\bigg"), (0x2C, r"\Bigg"), (0x2E, r"\Big")):
    _SIZED_DELIMS[_code] = _size + "/"
    _SIZED_DELIMS[_code + 1] = _size + r"\backslash"
for _code, _cmd in _SIZED_DELIMS.items():
    CMEX_TO_LATEX[chr(_code)] = _cmd
for _c in range(0x30, 0x48):
    CMEX_EXTENT[_c] = (0.0, 1.0)        # pieces of extensible delimiters
for _c in (0x48, 0x4A, 0x4C, 0x4E, 0x50, 0x51, 0x53, 0x54, 0x55, 0x56, 0x57, 0x60):
    CMEX_EXTENT[_c] = (0.0, 1.0)        # big operators, text size
for _c in (0x49, 0x4B, 0x4D, 0x4F, 0x58, 0x59, 0x5B, 0x5C, 0x5D, 0x5E, 0x5F, 0x61):
    CMEX_EXTENT[_c] = (0.1, 1.4)        # big operators, display size
CMEX_EXTENT[0x52] = (0.11, 1.0)         # integral, text size
CMEX_EXTENT[0x5A] = (0.22, 2.11)        # integral, display size
for _c in range(0x62, 0x68):
    CMEX_EXTENT[_c] = (0.75, 0.0)       # wide hats and tildes sit above the origin
for _c, _d in ((0x70, 1.16), (0x71, 1.76), (0x72, 2.36), (0x73, 2.96), (0x74, 1.16), (0x75, 0.6), (0x76, 0.6)):
    CMEX_EXTENT[_c] = (0.04, _d)        # radicals and their pieces


_TEX_ITALIC_FONTS = ("CMMI", "TXMI", "PXMI", "RTXMI", "MTMI", "EURM", "LMMI", "ZEURM", "LMMATHITALIC", "MATHDESIGN")
# Bold fonts that TeX uses inside formulas for \mathbf and \boldsymbol.
_BOLD_MATH_FONTS = ("CMBX", "CMMIB", "CMBSY", "SFBX", "NIMBUSROMNO9L-MEDI", "LMROMAN10-BOLD", "LMROMAN12-BOLD", "LMMATHITALIC10-BOLD", "TXBF", "NTXBF")
_GREEK_LATEX = {
    "α": r"\alpha", "β": r"\beta", "γ": r"\gamma", "δ": r"\delta", "ε": r"\varepsilon", "ϵ": r"\epsilon", "ζ": r"\zeta", "η": r"\eta",
    "θ": r"\theta", "ϑ": r"\vartheta", "ι": r"\iota", "κ": r"\kappa", "λ": r"\lambda", "μ": r"\mu", "ν": r"\nu", "ξ": r"\xi",
    "π": r"\pi", "ϖ": r"\varpi", "ρ": r"\rho", "ϱ": r"\varrho", "σ": r"\sigma", "ς": r"\varsigma", "τ": r"\tau", "υ": r"\upsilon",
    "φ": r"\phi", "ϕ": r"\varphi", "χ": r"\chi", "ψ": r"\psi", "ω": r"\omega",
    "Γ": r"\Gamma", "Δ": r"\Delta", "Θ": r"\Theta", "Λ": r"\Lambda", "Ξ": r"\Xi", "Π": r"\Pi", "Σ": r"\Sigma", "Υ": r"\Upsilon",
    "Φ": r"\Phi", "Ψ": r"\Psi", "Ω": r"\Omega",
}


def is_tex_italic_font(font: str) -> bool:
    return any(h in font.upper() for h in _TEX_ITALIC_FONTS)


# Width of cmmi's straight phi ("phi", TeX's \phi) and curly phi ("phi1", \varphi),
# as a fraction of the size, per design size: 0.596 vs 0.654 em at 10 pt. The
# threshold sits between them. Measured on the benchmark's arXiv pages.
_PHI_THRESHOLDS = {5: 0.84, 6: 0.78, 7: 0.72, 8: 0.66, 9: 0.64, 10: 0.625, 12: 0.61}


# Likewise cmmi's lunate epsilon ("epsilon", \epsilon, 0.406 em at 10 pt) against
# the curly one ("epsilon1", \varepsilon, 0.472 em); other TeX italic families
# (Pazo, MathDesign) have their own widths, so the rule applies to the cm-like ones.
_EPSILON_THRESHOLDS = {5: 0.60, 6: 0.555, 7: 0.505, 8: 0.46, 9: 0.45, 10: 0.44, 12: 0.425}
_CM_LIKE_ITALIC = ("CMMI", "LMMATHITALIC", "LMMI", "TXMI", "RTXMI", "PXMI")


def is_cm_like_italic_font(font: str) -> bool:
    f = font.upper()
    return any(h in f for h in _CM_LIKE_ITALIC)


def _design_size(font: str) -> int:
    import re

    m = re.search(r"(\d+)", font.split("+")[-1])
    return int(m.group(1)) if m else 10


def epsilon_by_width(font: str, ratio: float) -> str:
    """\\epsilon or \\varepsilon for an epsilon glyph of a cm-like italic font, by its width."""
    threshold = _EPSILON_THRESHOLDS.get(_design_size(font), 0.44)
    return r"\epsilon" if ratio < threshold else r"\varepsilon"


def phi_by_width(font: str, ratio: float) -> str:
    """\\phi or \\varphi for a phi glyph of a TeX italic font, judged by its advance width.

    TeX distributions disagree on the Unicode they attach to the two phi glyphs
    (some name the straight one U+03C6, others U+03D5), so the character cannot
    tell them apart; the width can, at every design size.
    """
    import re

    m = re.search(r"(\d+)", font.split("+")[-1])
    design = int(m.group(1)) if m else 10
    threshold = _PHI_THRESHOLDS.get(design, 0.625)
    return r"\phi" if ratio < threshold else r"\varphi"


# Fonts laid out like cmex10 (TeX's "math extension" encoding): Computer Modern's
# own, Latin Modern's clone, and the Times and Palatino maths families' clones.
EXTENSION_FONT_HINTS = ("CMEX", "LMMATHEXTENSION", "LMEX", "TXEX", "PXEX", "RTXEX", "MTEX", "EUEX")
# (mathabx's mathx is an extension font too, but listing it here let the text
# layer fold its braces into neighbouring prose lines: -2 on 2503.06880. Only the
# display-row linking treats it as one, see split_display_lines.)


# Adobe's private-use code points for the pieces of extensible delimiters (the
# names cmex glyphs carry in many Type 1 fonts: parenlefttp, braceleftmid, ...).
_ADOBE_PUA_PIECES: dict[str, str] = {
    "": r"\big(", "": r"\big(", "": r"\big(",       # parenleft top / extender / bottom
    "": r"\big[", "": r"\big[", "": r"\big[",       # bracketleft
    "": r"\{", "": r"\{", "": r"\{", "": r"\{",  # braceleft top / mid / bottom / extender
    "": r"\int",                                                 # integral extender
    "": r"\big)", "": r"\big)", "": r"\big)",       # parenright
    "": r"\big]", "": r"\big]", "": r"\big]",       # bracketright
    "": r"\}", "": r"\}", "": r"\}",                 # braceright
}


def is_extensible_piece(ch: str) -> bool:
    """A piece of an extensible delimiter under Adobe's private-use names."""
    return ch in _ADOBE_PUA_PIECES


def is_piece_glyph(ch: str, font: str) -> bool:
    """A piece of an extensible delimiter: under Adobe's private-use names, or as
    a raw cmex code (0x30-0x43 hold the tops, bottoms and extenders of the
    parentheses, brackets and braces) in a maths-extension font."""
    if ch in _ADOBE_PUA_PIECES:
        return True
    if len(ch) == 1 and is_extension_font(font):
        code = cmex_code(ch)
        return 0x30 <= code <= 0x43 and code != 0x3F
    return False


def is_extension_font(font: str) -> bool:
    f = font.upper()
    if "MATHDESIGN" in f and "-EX" in f:
        return True   # MathDesign (Charter, Utopia, Garamond maths): "MathDesign-CH-Regular-Ex" is its cmex clone
    return any(h in f for h in EXTENSION_FONT_HINTS)


def cmex_code(ch: str) -> int:
    """The cmex glyph code of a text-layer character (whitespace codes are carried
    on private-use characters 0xE000 + code so that they survive blank filters)."""
    code = ord(ch) if len(ch) == 1 else -1
    if 0xE000 <= code < 0xE100:
        code -= 0xE000
    return code


def _math_alphanumeric(ch: str, font: str) -> str | None:
    """Unicode's Mathematical Alphanumeric Symbols (U+1D400-U+1D7FF): the letter
    itself plus a style. Word and OpenType maths fonts (Cambria Math, STIX)
    put these in the text layer where TeX puts plain letters."""
    import unicodedata

    if not (0x1D400 <= ord(ch) <= 0x1D7FF):
        return None
    name = unicodedata.name(ch, "")
    base = unicodedata.normalize("NFKC", ch)
    if not name.startswith("MATHEMATICAL ") or len(base) != 1:
        return None
    inner = latex_for_char(base, font) or base
    style = name.split(" ")[1:]
    if "SCRIPT" in style:
        return r"\mathcal{%s}" % inner
    if "DOUBLE-STRUCK" in style:
        return r"\mathbb{%s}" % inner
    if "FRAKTUR" in style:
        return r"\mathfrak{%s}" % inner
    if "MONOSPACE" in style:
        return r"\mathtt{%s}" % inner
    if "SANS-SERIF" in style:
        return r"\mathsf{%s}" % inner
    if "BOLD" in style:
        return (r"\boldsymbol{%s}" if inner.startswith(chr(92)) else r"\mathbf{%s}") % inner
    return inner


_TRUNCATED_SURROGATE_FONTS = ("TX", "STIX", "CMMI", "MATH", "LMMI", "LMMATH", "XITS", "ASANA", "CAMBRIA", "TEX", "MI", "SY")


def unfold_truncated_surrogate(ch: str, font: str) -> str:
    """A maths letter whose code lost its top bits.

    Some producers write the ToUnicode entry for a Mathematical Alphanumeric
    Symbol (U+1D400 and up) with only sixteen bits, so an italic alpha (U+1D6FC)
    arrives as U+D6FC, a Hangul syllable. The arithmetic is exact: adding 0x10000
    gives the letter back. Applied to maths fonts only, so Korean text in Korean
    fonts is untouched.
    """
    if len(ch) == 1 and 0xD400 <= ord(ch) <= 0xD7FF and any(h in font.upper() for h in _TRUNCATED_SURROGATE_FONTS):
        return chr(ord(ch) + 0x10000)
    return ch


def latex_for_char(ch: str, font: str) -> str:
    """LaTeX for one text-layer character, given its font name."""
    f = font.upper()
    ch = unfold_truncated_surrogate(ch, font)
    if ch == "ˆ" and "ESINT" in f:
        # The esint extension font names its integral sign so that MuPDF reports
        # it as a circumflex. (mathx's "ˆ" is a big left parenthesis, see _MATHX_RAW.)
        return r"\int"
    styled = _math_alphanumeric(ch, font) if len(ch) == 1 and ord(ch) >= 0x1D400 else None
    if styled is not None:
        return styled
    if "MATHX" in f:
        # mathabx's extension font has its own layout, read off a contact sheet;
        # it must not go through the cmex code tables below.
        return _MATHX_RAW.get(ch, "")
    if is_extension_font(f):
        if ch in _ADOBE_PUA_PIECES:
            # Pieces of extensible brackets under Adobe's private-use names
            # (bracelefttp, braceleftmid, ...): each piece is the bracket, and the
            # pieces are stacked into one tall glyph later.
            return _ADOBE_PUA_PIECES[ch]
        code = cmex_code(ch)
        cmd = CMEX_TO_LATEX.get(chr(code), "") if code >= 0 else ""
        if not cmd and ("TXEX" in f or "PXEX" in f):
            cmd = _TXEX_RAW.get(ch, "")
        if not cmd and ch in UNICODE_TO_LATEX and ord(ch) > 0x7F:
            # An extension font that carries an ordinary symbol under its own name
            # (Euler's euex10 holds ∞): the text layer's Unicode says what it is.
            return UNICODE_TO_LATEX[ch]
        return cmd
    if len(ch) == 1 and (ch.isalnum() or ch in _GREEK_LATEX) and any(h in f for h in _BOLD_MATH_FONTS):
        # Bold maths: cmbx letters are \mathbf, cmmib (bold italic) \boldsymbol;
        # the checker's renderer sets bold glyphs apart from plain ones.
        inner = _GREEK_LATEX.get(ch) or UNICODE_TO_LATEX.get(ch, ch)
        if inner.startswith(chr(92)) or "CMMIB" in f:
            return r"\boldsymbol{%s}" % inner
        return r"\mathbf{%s}" % inner
    if ch in ("φ", "ϕ") and (any(h in f for h in _TEX_ITALIC_FONTS) or "SYMBOL" in f or "STANDARDSYM" in f):
        # Adobe Symbol (mathptmx) follows TeX: its "phi" slot is the straight
        # letter that \phi draws, and "phi1" the looped \varphi.
        # TeX's \phi glyph is *named* "phi" and so comes back as U+03C6, the code
        # KaTeX draws for \varphi; the two are swapped for TeX-encoded fonts.
        return r"\phi" if ch == "φ" else r"\varphi"
    if ch in ("ε", "ϵ") and any(h in f for h in _TEX_ITALIC_FONTS):
        # Likewise TeX's \epsilon glyph (the lunate one) is named "epsilon" and
        # comes back as U+03B5, the code KaTeX draws for \varepsilon.
        return r"\epsilon" if ch == "ε" else r"\varepsilon"
    if "MATHB" in f and ch in _MATHB_RAW:
        return _MATHB_RAW[ch]
    if "MATHA" in f or "MATHB" in f:
        return _MATHABX_RAW.get(ch, ch if ch.isprintable() else "")
    if "MSBM" in f and ch == "κ":
        return r"\varkappa"   # msbm's kappa is the variant one
    if "STIX" in f and len(ch) == 1 and 0xE22D <= ord(ch) <= 0xE246:
        # STIX Math Calligraphy keeps its capitals in the private-use area,
        # A at U+E22D through Z at U+E246 (B and D seen on 2503.06111).
        return r"\mathcal{%s}" % chr(ord("A") + ord(ch) - 0xE22D)
    if ch in UNICODE_TO_LATEX:
        return UNICODE_TO_LATEX[ch]
    if ch.isalpha() and ch.isupper() and len(ch) == 1:
        # The letter slots of cmsy hold the calligraphic alphabet, those of
        # msbm the blackboard-bold one.
        if "CMSY" in f or "CMBSY" in f or ("MATHDESIGN" in f and ("-MA" in f or "-SY" in f)) or "EUSM" in f:
            return r"\mathcal{%s}" % ch
        if "RSFS" in f:
            return r"\mathscr{%s}" % ch   # Ralph Smith's formal script: the \mathscr alphabet
        if "MSBM" in f or "TXSYB" in f or "PXSYB" in f or "BBOLD" in f or "DOUBLESTRUCK" in f or "DSROM" in f or "DSSS" in f:
            return r"\mathbb{%s}" % ch   # msbm, newtx/newpx's blackboard-bold symbol fonts, bbold, boondox, dsfont
    if "CMSY" in f and ch == "*":
        # cmsy's asteriskmath (0x03) reaches the text layer as "*" in some PDFs;
        # read as a raw code it would be 0x2A, \Uparrow ("Input*Gradient" on 2503.08240).
        return "*"
    if ("TXSY" in f or "PXSY" in f) and ch in "()[]+-=<>|/*":
        # newtx/newpx symbol fonts map their brackets and operators to the plain
        # characters in the PDF (unlike cmsy, whose 0x28 is a double arrow and
        # whose 0x2B is \Downarrow): trust the text.
        return ch
    if "CMSY" in f or "MSAM" in f or "MSBM" in f or "OAMATHSYMBOLS" in f or "MDSY" in f or "TXSY" in f or "PXSY" in f or "LMMATHSYMBOLS" in f:
        # Symbol fonts laid out like cmsy (OMS encoding): characters MuPDF could not
        # map to Unicode come back as raw codes; the common ones are rescued.
        if "MSBM" in f and ch == "κ":
            return r"\varkappa"   # msbm's kappa is the variant one
        return _CMSY_RAW.get(ch, ch if ch.isprintable() else "")
    if ch == "\\":
        return r"\backslash"
    if ch in "^~":
        return r"\%s{}" % ("hat" if ch == "^" else "tilde")
    return ch


# cmsy10 raw codes seen when a PDF lacks a ToUnicode map for the symbol font.
_CMSY_RAW: dict[str, str] = {
    "\x00": "-", "\x01": r"\cdot", "\x02": r"\times", "\x03": "*", "\x04": r"\div", "\x05": r"\diamond",
    "\x06": r"\pm", "\x07": r"\mp", "\x08": r"\oplus", "\x09": r"\ominus", "\x0a": r"\otimes", "\x0b": r"\oslash",
    "\x0c": r"\odot", "\x0d": r"\bigcirc", "\x0e": r"\circ", "\x0f": r"\bullet",
    "\x10": r"\asymp", "\x11": r"\equiv", "\x12": r"\subseteq", "\x13": r"\supseteq", "\x14": r"\leq", "\x15": r"\geq",
    "\x16": r"\preceq", "\x17": r"\succeq", "\x18": r"\sim", "\x19": r"\approx", "\x1a": r"\subset", "\x1b": r"\supset",
    "\x1c": r"\ll", "\x1d": r"\gg", "\x1e": r"\prec", "\x1f": r"\succ",
    "\x20": r"\leftarrow", "\x21": r"\rightarrow", "\x22": r"\uparrow", "\x23": r"\downarrow", "\x24": r"\leftrightarrow",
    "\x25": r"\nearrow", "\x26": r"\searrow", "\x27": r"\simeq", "\x28": r"\Leftarrow", "\x29": r"\Rightarrow",
    "\x2a": r"\Uparrow", "\x2b": r"\Downarrow", "\x2c": r"\Leftrightarrow", "\x2d": r"\nwarrow", "\x2e": r"\swarrow",
    "\x2f": r"\propto", "\x30": r"\prime", "\x31": r"\infty", "\x32": r"\in", "\x33": r"\ni", "\x34": r"\triangle",
    "\x35": r"\bigtriangledown", "\x36": "/", "\x37": r"\mapstochar", "\x38": r"\forall", "\x39": r"\exists",
    "\x3a": r"\neg", "\x3b": r"\emptyset", "\x3c": r"\Re", "\x3d": r"\Im", "\x3e": r"\top", "\x3f": r"\bot",
    "\x40": r"\aleph", "\x5b": r"\cup", "\x5c": r"\setminus",  # the glyph at 0x6e is named "backslash": MuPDF reports it as this character "\x5d": r"\uplus", "\x5e": r"\wedge", "\x5f": r"\vee",
    "\x60": r"\vdash", "\x61": r"\dashv", "\x62": r"\lfloor", "\x63": r"\rfloor", "\x64": r"\lceil", "\x65": r"\rceil",
    "\x66": r"\{", "\x67": r"\}", "\x68": r"\langle", "\x69": r"\rangle", "\x6a": "|", "\x6b": r"\|",
    "\x6c": r"\updownarrow", "\x6d": r"\Updownarrow", "\x6e": r"\backslash", "\x6f": r"\wr", "\x70": r"\sqrt",
    "\x71": r"\amalg", "\x72": r"\nabla", "\x73": r"\int", "\x74": r"\sqcup", "\x75": r"\sqcap", "\x76": r"\sqsubseteq",
    "\x77": r"\sqsupseteq", "\x78": r"\S", "\x79": r"\dagger", "\x7a": r"\ddagger", "\x7b": r"\P", "\x7c": r"\clubsuit",
    "\x7d": r"\diamondsuit", "\x7e": r"\heartsuit", "\x7f": r"\spadesuit",
}
