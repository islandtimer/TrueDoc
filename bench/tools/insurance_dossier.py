r"""The insurance dossier, rebuilt so a decision takes seconds.

The first version put all ten checks for a page in one box of text and four thousand characters of our
markdown in another, and asked the owner to keep, fix or drop the page. That is a research task per card,
not a decision, and he said so.

What changed, and why each change earns its place:

**One card per decision, not per page.** Of 229 checks, 191 pass *and* have their quotation confirmed by
a separate reading of the page — there is nothing to decide about those, so they are counted, collapsed
and kept out of the way. 38 need a person. The queue is 38 cards, and each asks one question: *is this
check a fair test of this page?*

**The reason is computed, not left to the reader.** A card does not say "this failed". It says which of
five things went wrong — the text is nowhere in our output; the words match but a few characters differ
(and here they are, marked); we made no table there; the cell is right but the heading above it is not;
an ordering check whose text is missing anyway — and shows our output beside the check. Cards are grouped
by that reason, so the same judgement is made once over a run of similar cards rather than rediscovered.

**absent checks were reading upside down.** The old dossier looked for each check's quotation in a second
reading of the page and flagged anything it could not find. For a check that says "the page number 6 must
NOT appear", a reading that omits the page number is *agreement*, not doubt — and that false alarm was 24
of the 38 flags. Now absent checks are read the right way up, and the seven where the second reading does
contain the text sit in their own short queue.

This is still propose-only. The second reading is another look at the same image, so its mistakes are not
independent of the check-writer's, and a short quotation ("6") fuzzy-matches almost anything. It points;
the owner decides.

usage (repo root): insurance_dossier.py [output html]
"""
import base64
import difflib
import glob
import html
import io
import json
import os
import re
import sys

from PIL import Image
from rapidfuzz import fuzz

from olmocr.bench.tests import (load_single_test, normalize_text, parse_html_tables,
                                parse_markdown_tables)

OUT = os.path.join("bench", "out", "insurance_set")
TARGET = sys.argv[1] if len(sys.argv) > 1 else os.path.join(OUT, "insurance_dossier.html")
ESCAPE = re.compile(r"\\([\\`*_{}\[\]()#+\-.!$|&%~<>])")

GROUPS = [
    ("missing", "We never produced this text",
     "The page has these words; our markdown does not, anywhere. These are all cover-page lines — the "
     "issuer, the ABN, the registered office — and we leave them out on purpose: the reader is told to "
     "omit page furniture, which is worth 35 checks on the public benchmark. So this is a policy "
     "question, and one decision covers all three. Is an insurer's ABN and licence number furniture, or "
     "is it content a reader of an insurance document needs?"),
    ("chars", "Same words, a few characters apart",
     "We produced this passage, but not character for character, and the check demands an exact match. "
     "The differing characters are marked below, in the sentence they belong to. Five of these seven are "
     "one page of the RAA landlord PDS, and the cause splits in two. The missing letters are not ours: "
     "that PDF's own text layer says \"ofer\", \"fnd\" and \"Certifcate\", because its font maps the "
     "ﬀ and ﬁ ligatures to a single letter — we checked the file itself. The missing spaces are ours: "
     "the file says \"If you\", \"Cooling-of Period\", \"of 21\" and we write \"Ifyou\", "
     "\"Cooling-ofPeriod\", \"of21\". So a fair call here is really two: the spacing is a defect to fix, "
     "and the page is a case for reading the image rather than trusting a text layer that has already "
     "lost letters. Say which in the note."),
    ("notable", "Not a table in our output",
     "The check treats this as a table cell with a neighbour. Either we produced no table there, or we "
     "produced the words as ordinary text. If the page really is laid out as a table, the check is fair "
     "and we have work to do. If it is a list the check-writer read as a grid, it is not."),
    ("celltext", "The cell is nearly right",
     "We built a table with this cell in it, but the cell does not read word for word the way the check "
     "quotes it, and the check demands an exact cell. Most of these are the same thing: the tick or "
     "cross that says whether the item is covered has been swept into the label beside it instead of "
     "staying in its own column, so our cell reads “✘ Loss or damage caused by lightning.”."),
    ("neighbour", "Right cell, wrong neighbour",
     "We found the cell and built a table around it, but the cell next to it is not the one the check "
     "expects. Read the page: if our grid matches what a person sees, the check has the geometry wrong."),
    ("order", "An ordering check, blocked by missing text",
     "These say one passage must come before another. They fail because one of the two passages is not "
     "in our output at all — so they are really the same problem as the first group, counted twice. "
     "Deciding them usually follows whatever you decided there."),
    ("look", "These pass — but worth one look",
     "Checks that say a passage must NOT appear, where a second reading of the page did contain it. If "
     "the words really are on the page as ordinary content, the check is wrong and we are passing it for "
     "the wrong reason. Be sceptical: a short quotation like \"6\" matches almost anything."),
]


def unescape(md: str) -> str:
    """Markdown escapes are syntax, not content — D024 writes a price as \\$500."""
    return ESCAPE.sub(r"\1", md)


def page_image(path: str) -> str:
    """One JPEG per page, embedded once and shared by every card that shows it."""
    im = Image.open(path).convert("RGB")
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=82, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def esc(text) -> str:
    return html.escape(str(text))


def quote(text) -> str:
    return f'<q>{esc(" ".join(str(text).split()))}</q>'


def statement(check: dict) -> str:
    """What the check asks, in a sentence."""
    kind = check.get("type")
    if kind == "present":
        return f'The page says {quote(check.get("text", ""))} &mdash; so our markdown must too.'
    if kind == "absent":
        return (f'{quote(check.get("text", ""))} is furniture, not content &mdash; it must <b>not</b> '
                'appear in our markdown.')
    if kind == "order":
        return (f'{quote(check.get("before", ""))} must come <b>before</b> '
                f'{quote(check.get("after", ""))}.')
    if kind == "table":
        where = next((k for k in ("left", "right", "up", "down", "top_heading", "left_heading")
                      if check.get(k)), None)
        said = {"left": "immediately to its left", "right": "immediately to its right",
                "up": "directly above it", "down": "directly below it",
                "top_heading": "as the column heading above it",
                "left_heading": "as the row heading beside it"}.get(where, "next to it")
        return (f'The page has a table. The cell {quote(check.get("cell", ""))} must have '
                f'{quote(check.get(where, ""))} {said}.')
    return esc(json.dumps(check)[:200])


def visible(text: str) -> str:
    """A difference that is only whitespace has to be made visible, or the mark looks empty."""
    if text and not text.strip():
        return '<span class="ws">' + "&middot;" * len(text) + "</span>"
    return esc(text)


def word_gloss(wanted: str, got: str, i1: int, i2: int, j1: int, j2: int) -> str:
    """The whole word each side of a difference, so "a dropped f" reads as "offer" against "ofer"."""
    def around(text: str, lo: int, hi: int) -> str:
        while lo > 0 and not text[lo - 1].isspace():
            lo -= 1
        while hi < len(text) and not text[hi].isspace():
            hi += 1
        return text[lo:hi].strip()
    a, b = around(wanted, i1, i2), around(got, j1, j2)
    if a == b or len(a) > 40 or len(b) > 40:
        return ""
    if not b:
        return f'<span class="gloss">the page says <b>{esc(a)}</b>, we left it out</span>'
    if not a:
        return f'<span class="gloss">we added <b>{esc(b)}</b>, the page has no such thing here</span>'
    return f'<span class="gloss">the page says <b>{esc(a)}</b>, we wrote <b>{esc(b)}</b></span>'


def marked_diff(wanted: str, got: str, pad: int = 0) -> str:
    """The two passages with their differing characters marked, so the eye lands on them.

    The aligner's window stops a character or two short of the passage, which turns the head and tail
    into diff noise and hides the one real difference in the middle. So the window is padded, and the
    padding — an insertion at either end — is dropped before anything is marked.
    """
    sm = difflib.SequenceMatcher(None, wanted, got, autojunk=False)
    ops = sm.get_opcodes()
    if pad:
        while ops and ops[0][0] == "insert":
            ops.pop(0)
        while ops and ops[-1][0] == "insert":
            ops.pop()
        if ops:
            got = got[ops[0][3]:ops[-1][4]]
            shift = ops[0][3]
            ops = [(t, i1, i2, j1 - shift, j2 - shift) for t, i1, i2, j1, j2 in ops]
    top, bottom, glosses = [], [], []
    for tag, i1, i2, j1, j2 in ops:
        if tag == "equal":
            top.append(esc(wanted[i1:i2]))
            bottom.append(esc(got[j1:j2]))
            continue
        if i2 > i1:
            top.append(f'<mark class="gone">{visible(wanted[i1:i2])}</mark>')
        if j2 > j1:
            bottom.append(f'<mark class="new">{visible(got[j1:j2])}</mark>')
        gloss = word_gloss(wanted, got, i1, i2, j1, j2)
        if gloss and gloss not in glosses:
            glosses.append(gloss)
    return (f'<div class="cmp"><span class="cmp-lbl">the page says</span>'
            f'<div class="passage">{"".join(top)}</div></div>'
            f'<div class="cmp"><span class="cmp-lbl">we wrote</span>'
            f'<div class="passage">{"".join(bottom)}</div></div>'
            + ("".join(glosses) if glosses else ""))


def best_window(needle: str, hay: str, pad: int = 0):
    """Where in our markdown does this passage come closest to appearing?"""
    if not needle or not hay:
        return 0.0, ""
    align = fuzz.partial_ratio_alignment(needle, hay)
    if align is None:
        return 0.0, ""
    lo = max(0, align.dest_start - pad)
    hi = min(len(hay), align.dest_end + pad)
    return align.score, hay[lo:hi]


def render_table(data, focus, expected_at=None, limit=9) -> str:
    """Our table, trimmed to the rows around the cell in question, with the two cells marked."""
    nrows, ncols = data.shape
    lo = max(0, focus[0] - limit // 2)
    hi = min(nrows, lo + limit)
    out = ['<table class="grid">']
    for i in range(lo, hi):
        out.append("<tr>")
        for j in range(ncols):
            cls = ""
            if (i, j) == focus:
                cls = ' class="focus"'
            elif expected_at and (i, j) == expected_at:
                cls = ' class="nbr"'
            text = " ".join(str(data[i, j]).split())
            out.append(f"<td{cls}>{esc(text[:90])}</td>")
        out.append("</tr>")
    out.append("</table>")
    if hi - lo < nrows:
        out.append(f'<div class="tiny">showing rows {lo + 1}&ndash;{hi} of {nrows}</div>')
    return "".join(out)


DIGITS = re.compile(r"\d+")


def find_cell(tables, wanted: str):
    """The closest thing to this cell in any table we produced.

    A cell whose digits differ is a *different cell*, however alike it looks. On this page "$10,000"
    fuzzy-matches our "$1,000" at 92%, and calling that a near miss told the owner we had written the
    wrong amount — when the truth is that our table is missing the row entirely, and the $1,000 we do
    have is correct and passes its own check. In an insurance document the digits are the content, so
    they have to match before anything is called close.
    """
    best = (0.0, None, None)
    target = normalize_text(wanted)
    want_digits = DIGITS.findall(target)
    for t in tables:
        data = t.data
        for i in range(data.shape[0]):
            for j in range(data.shape[1]):
                text = normalize_text(str(data[i, j]))
                score = fuzz.ratio(target, text)
                if score > best[0] and DIGITS.findall(text) == want_digits:
                    best = (score, t, (i, j))
    return best


def evidence(check: dict, md: str, norm: str, tables) -> tuple:
    """(group, one-line verdict, evidence html) — the computed reason this check failed.

    Everything is compared on normalised text, because that is what the benchmark compares: it strips
    bold and italics and squeezes whitespace before it looks. Diffing our raw markdown instead shows the
    reader a wall of pipes and newlines and hides the one character that actually failed.
    """
    kind = check.get("type")

    if kind in ("present", "absent"):
        wanted = normalize_text(str(check.get("text", "")))
        score, window = best_window(wanted, norm, pad=30)
        if score >= 85:
            return ("chars",
                    f"We wrote this passage, but not character for character ({score:.0f}% alike).",
                    marked_diff(wanted, window, pad=30))
        whole = md.strip()
        short = len(whole) <= 1300
        return ("missing",
                f"Nothing in our markdown resembles this ({score:.0f}% at best).",
                f'<div class="cmp"><span class="cmp-lbl">the page says, and we do not</span>'
                f'<div class="passage">{esc(wanted)}</div></div>'
                f'<div class="cmp"><span class="cmp-lbl">'
                f'{"everything we produced for this page" if short else "the nearest thing we produced"}'
                f'</span><div class="passage dim">'
                f'{esc(whole if short else window) or "&mdash; nothing close &mdash;"}</div></div>')

    if kind == "order":
        parts = []
        missing = []
        for role in ("before", "after"):
            text = normalize_text(str(check.get(role, "")))
            score, _ = best_window(text, norm)
            if score < 99:
                missing.append(role)
            parts.append(
                f'<div class="cmp"><span class="cmp-lbl">the {role} passage'
                f'{" &mdash; missing from our output" if score < 99 else " &mdash; we have this one"}'
                f'</span><div class="passage{"" if score >= 99 else " dim"}">{esc(text)}</div></div>')
        verdict = ("Neither passage is in our output, so the ordering never gets tested."
                   if len(missing) == 2 else
                   f"The {missing[0]} passage is not in our output, so the ordering never gets tested."
                   if missing else "Both passages are there, in the wrong order.")
        return ("order" if missing else "chars", verdict, "".join(parts))

    if kind == "table":
        cell = str(check.get("cell", ""))
        where = next((k for k in ("left", "right", "up", "down", "top_heading", "left_heading")
                      if check.get(k)), None)
        cell_n = normalize_text(cell)
        score, table, at = find_cell(tables, cell)
        prose, window = best_window(cell_n, norm, pad=40)
        if not tables:
            tail = ("are in our output as ordinary text" if prose >= 85
                    else "are not in our output either")
            body = (f'<div class="cmp"><span class="cmp-lbl">the cell the check wants</span>'
                    f'<div class="passage">{esc(cell)}</div></div>'
                    f'<div class="cmp"><span class="cmp-lbl">we built no table here. the words {tail}'
                    f'</span><div class="passage dim">'
                    f'{esc(window) or "&mdash; nothing close &mdash;"}</div></div>')
            return ("notable", "We produced no table anywhere on this page.", body)
        if score < 70 or table is None:
            near = ("these words are in our output, but as ordinary text, not a table cell"
                    if prose >= 85 else "the nearest thing anywhere in our output")
            body = (f'<div class="cmp"><span class="cmp-lbl">the cell the check wants</span>'
                    f'<div class="passage">{esc(cell)}</div></div>'
                    f'<div class="cmp"><span class="cmp-lbl">{near}</span>'
                    f'<div class="passage dim">{esc(window) or "&mdash; nothing close &mdash;"}</div>'
                    '</div>'
                    '<span class="cmp-lbl">the table we did build on this page</span>'
                    + render_table(tables[0].data, (-1, -1), limit=12))
            return ("notable",
                    ("The words are in our output, but not inside a table." if prose >= 85 else
                     "No cell in any table we built reads like this."),
                    body)
        data = table.data
        ours = " ".join(str(data[at]).split())
        if score < 99.5:
            return ("celltext",
                    f"Our cell reads &ldquo;{esc(ours[:60])}&rdquo; &mdash; close, but the check wants "
                    "the cell word for word.",
                    marked_diff(cell_n, normalize_text(ours))
                    + '<span class="cmp-lbl">our table &mdash; blue is the cell</span>'
                    + render_table(data, at))
        i, j = at
        step = {"left": (0, -1), "right": (0, 1), "up": (-1, 0), "down": (1, 0),
                "top_heading": (-i, 0), "left_heading": (0, -j)}.get(where, (0, 0))
        nbr = (i + step[0], j + step[1])
        inside = 0 <= nbr[0] < data.shape[0] and 0 <= nbr[1] < data.shape[1]
        actual = " ".join(str(data[nbr]).split()) if inside else ""
        said = {"left": "to the left", "right": "to the right", "up": "above", "down": "below",
                "top_heading": "as the column heading", "left_heading": "as the row heading"}.get(where, "")
        body = (f'<div class="cmp"><span class="cmp-lbl">the check expects, {said}</span>'
                f'<div class="passage">{esc(check.get(where, ""))}</div></div>'
                f'<div class="cmp"><span class="cmp-lbl">what our table has there</span>'
                f'<div class="passage dim">{esc(actual) or "&mdash; nothing; the cell sits at the edge "
                                                           "of our table &mdash;"}</div></div>'
                f'<span class="cmp-lbl">our table &mdash; blue is the cell, amber is its neighbour</span>'
                + render_table(data, at, nbr if inside else None))
        return ("neighbour",
                f"We have the cell, but {said} we have "
                f"{('&ldquo;' + esc(actual[:44]) + '&rdquo;') if actual else 'nothing'}.",
                body)

    return ("missing", "This check could not be read.", esc(json.dumps(check)[:400]))


def build() -> None:
    names = sorted(os.path.splitext(os.path.basename(p))[0]
                   for p in glob.glob(os.path.join(OUT, "checks_a", "*.jsonl")))
    verification = json.load(open(os.path.join(OUT, "verification.json"), encoding="utf-8"))
    manifest = {p["name"]: p for p in
                json.load(open(os.path.join(OUT, "manifest.json"), encoding="utf-8"))["pages"]}

    images, cards, pages, tally = {}, [], [], {"total": 0, "passed": 0, "settled": 0}
    for name in names:
        raw_md = open(os.path.join(OUT, "converted", name + ".md"), encoding="utf-8").read()
        md = unescape(raw_md)
        norm = normalize_text(md)
        tables = parse_markdown_tables(md) + parse_html_tables(md)
        read_path = os.path.join(OUT, "independent_read", name + ".md")
        second_read = (normalize_text(open(read_path, encoding="utf-8").read())
                       if os.path.exists(read_path) else "")
        rows = verification.get(name, [])
        checks = [json.loads(l) for l in open(os.path.join(OUT, "checks_a", name + ".jsonl"),
                                              encoding="utf-8") if l.strip()]
        img_path = os.path.join(OUT, "pages", name + ".png")
        if name not in images and os.path.exists(img_path):
            images[name] = page_image(img_path)

        listed, n_pass = [], 0
        for i, raw in enumerate(checks):
            item = dict(raw)
            item.setdefault("id", f"{name}_{i}")
            try:
                good, why = load_single_test(item).run(md)
            except Exception as exc:
                good, why = False, repr(exc)[:90]
            tally["total"] += 1
            n_pass += bool(good)
            tally["passed"] += bool(good)
            found = rows[i].get("found", -1) if i < len(rows) else -1
            kind = raw.get("type")
            if kind == "absent":
                agrees = found < 85
                second = ("a second reading of the page left this text out too &mdash; both readers "
                          "call it furniture" if agrees else
                          f"a second reading of the page <b>did</b> contain this text ({found:.0f}% "
                          "match), so it may be real content")
            else:
                agrees = found >= 85
                second = (("a second reading of the page found this text word for word"
                           if found >= 99 else
                           f"a second reading found this text, near enough ({found:.0f}%)") if agrees
                          else f"a second reading could not find this text ({found:.0f}%)")

            listed.append({"check": raw, "passed": bool(good), "agrees": agrees, "found": found})
            if good and agrees:
                tally["settled"] += 1
                continue
            if good:
                _, seen = best_window(normalize_text(str(raw.get("text", ""))), second_read, pad=70)
                group, verdict = "look", "We pass this, but the text may really be on the page."
                body = (f'<div class="cmp"><span class="cmp-lbl">the text the check forbids</span>'
                        f'<div class="passage">{esc(raw.get("text", ""))}</div></div>'
                        f'<div class="cmp"><span class="cmp-lbl">where the second reading has it '
                        f'&mdash; is this real content, or the furniture the check calls it?</span>'
                        f'<div class="passage dim">{esc(seen) or "&mdash; nowhere &mdash;"}</div></div>')
            else:
                group, verdict, body = evidence(raw, md, norm, tables)
            cards.append({
                "id": f"{name}__{i}", "page": name, "kind": kind, "group": group,
                "statement": statement(raw), "verdict": verdict, "body": body, "second": second,
                "why": " ".join(str(why or "").split())[:220],
                "why_page": manifest.get(name, {}).get("why", ""),
            })
        pages.append({"name": name, "checks": listed, "pass": n_pass, "md": raw_md,
                      "why": manifest.get(name, {}).get("why", "")})

    order = {key: n for n, (key, _, _) in enumerate(GROUPS)}
    cards.sort(key=lambda c: (order.get(c["group"], 9), c["page"]))
    for n, card in enumerate(cards, 1):
        card["n"] = n

    payload = {"cards": cards, "pages": pages, "images": images, "tally": tally,
               "groups": [{"key": k, "title": t, "blurb": b} for k, t, b in GROUPS]}
    with open(TARGET, "w", encoding="utf-8") as fh:
        fh.write(PAGE.replace("__DATA__", json.dumps(payload, ensure_ascii=False)))
    size = os.path.getsize(TARGET) / 1e6
    print(f"{tally['total']} checks, {tally['passed']} pass, {len(cards)} need a person")
    print(f"dossier: {TARGET}  ({size:.1f} MB)")


PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Insurance checks &mdash; are they a fair test?</title>
<style>
:root{
  --ink:#16181d; --soft:#5b6170; --faint:#8a91a0; --line:#e2e5ea; --bg:#f6f7f9; --card:#fff;
  --good:#0f8a4a; --goodbg:#e8f6ee; --bad:#c0392b; --badbg:#fdecea; --warn:#a86400; --warnbg:#fdf3e2;
  --pick:#1f6feb; --pickbg:#e8f1ff;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;}
q{quotes:none;background:#fff8d8;padding:1px 4px;border-radius:3px;font-weight:500;
  box-shadow:inset 0 -1px 0 #efe0a0}
header{background:#fff;border-bottom:1px solid var(--line);padding:22px 26px 0}
.wrap{max-width:1420px;margin:0 auto}
h1{margin:0 0 6px;font-size:23px;letter-spacing:-.2px}
.lede{margin:0 0 16px;color:var(--soft);max-width:78ch}
.lede b{color:var(--ink)}
.scoreline{display:flex;gap:26px;flex-wrap:wrap;margin:0 0 16px;align-items:baseline}
.stat{display:flex;gap:8px;align-items:baseline}
.stat .big{font-size:26px;font-weight:650;letter-spacing:-.5px}
.stat .lbl{color:var(--soft);font-size:13px}
.tabs{display:flex;gap:4px}
.tab{border:1px solid var(--line);border-bottom:none;background:#fbfcfd;color:var(--soft);
  padding:9px 16px;border-radius:8px 8px 0 0;cursor:pointer;font-size:14px;font-weight:550}
.tab.on{background:var(--bg);color:var(--ink);box-shadow:inset 0 2px 0 var(--pick)}
main{max-width:1420px;margin:0 auto;padding:22px 26px 120px}
.grouphead{margin:34px 0 14px;padding:14px 16px;background:#fff;border:1px solid var(--line);
  border-left:4px solid var(--pick);border-radius:10px}
.grouphead:first-child{margin-top:6px}
.grouphead h2{margin:0 0 5px;font-size:17px}
.grouphead p{margin:0;color:var(--soft);font-size:14px;max-width:88ch}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;margin:0 0 16px;
  overflow:hidden;scroll-margin-top:16px}
.card.done{opacity:.55}
.card.cur{border-color:var(--pick);box-shadow:0 0 0 3px var(--pickbg)}
.chead{display:flex;gap:10px;align-items:center;padding:11px 15px;border-bottom:1px solid var(--line);
  background:#fbfcfd;flex-wrap:wrap}
.num{font-weight:700;color:var(--faint);font-size:13px}
.chip{font-size:11.5px;font-weight:650;border-radius:5px;padding:3px 8px;letter-spacing:.2px}
.chip.kind{background:#eef1f6;color:var(--soft)}
.chip.fail{background:var(--badbg);color:var(--bad)}
.chip.pass{background:var(--goodbg);color:var(--good)}
.src{color:var(--faint);font-size:12.5px;margin-left:auto;font-family:ui-monospace,Menlo,Consolas,monospace}
.split{display:grid;grid-template-columns:minmax(0,42%) minmax(0,58%)}
@media(max-width:1040px){.split{grid-template-columns:1fr}}
.pane-img{border-right:1px solid var(--line);background:#f1f2f5;padding:12px;display:flex;
  align-items:flex-start;justify-content:center}
.pane-img img{width:100%;height:auto;border:1px solid var(--line);border-radius:6px;background:#fff;
  cursor:zoom-in;display:block}
.pane{padding:16px 18px}
.ask{font-size:15.5px;line-height:1.6;margin:0 0 14px}
.verdict{display:flex;gap:9px;align-items:flex-start;background:var(--badbg);border-radius:9px;
  padding:10px 13px;margin:0 0 14px;color:#7d2b21;font-size:14.5px;font-weight:500}
.verdict.ok{background:var(--warnbg);color:#7a4a00}
.verdict .ico{font-weight:700}
.cmp{margin:0 0 10px}
.cmp-lbl{display:block;font-size:11.5px;font-weight:650;letter-spacing:.3px;text-transform:uppercase;
  color:var(--faint);margin:0 0 4px}
.passage{background:#fbfbfc;border:1px solid var(--line);border-radius:7px;padding:9px 11px;
  font-size:14px;line-height:1.55;white-space:pre-wrap;word-break:break-word;max-height:200px;
  overflow:auto}
.passage.dim{color:var(--soft);background:#f7f7f9}
mark.gone{background:#ffd9d4;color:#8a1f12;border-radius:2px;padding:0 1px;
  outline:1px solid #f3b3aa}
mark.new{background:#d6f0e0;color:#0c5c34;border-radius:2px;padding:0 1px;outline:1px solid #a9dcc0}
.ws{opacity:.75;letter-spacing:1px}
.gloss{display:inline-block;background:#f2f4f8;border:1px solid var(--line);border-radius:7px;
  padding:6px 11px;font-size:13.5px;color:var(--soft);margin:2px 6px 2px 0}
.gloss b{color:var(--ink);font-family:ui-monospace,Menlo,Consolas,monospace;font-size:13px}
table.grid{border-collapse:collapse;margin:8px 0 2px;font-size:12.5px;width:100%;table-layout:fixed}
table.grid td{border:1px solid var(--line);padding:4px 6px;vertical-align:top;color:var(--soft);
  overflow:hidden;text-overflow:ellipsis}
table.grid td.focus{background:var(--pickbg);color:var(--ink);font-weight:600;
  outline:2px solid var(--pick);outline-offset:-2px}
table.grid td.nbr{background:var(--warnbg);color:#7a4a00;font-weight:600}
.tiny{font-size:11.5px;color:var(--faint)}
.second{font-size:13.5px;color:var(--soft);border-top:1px dashed var(--line);padding:11px 0 0;
  margin:14px 0 0}
.second b{color:var(--ink)}
.controls{display:flex;gap:8px;align-items:center;margin:14px 0 0;flex-wrap:wrap}
button.pick{border:1px solid var(--line);background:#fff;border-radius:8px;padding:9px 14px;
  cursor:pointer;font-size:14px;font-weight:600;color:var(--ink)}
button.pick:hover{border-color:var(--faint)}
button.pick .k{color:var(--faint);font-weight:500;font-size:12px;margin-left:6px}
button.pick.on[data-d="fair"]{background:var(--goodbg);border-color:var(--good);color:var(--good)}
button.pick.on[data-d="unfair"]{background:var(--badbg);border-color:var(--bad);color:var(--bad)}
button.pick.on[data-d="unsure"]{background:var(--warnbg);border-color:var(--warn);color:var(--warn)}
.note{flex:1;min-width:200px;border:1px solid var(--line);border-radius:8px;padding:9px 11px;
  font:inherit;font-size:13.5px}
.hint{font-size:12.5px;color:var(--faint);margin:9px 0 0}
footer{position:fixed;left:0;right:0;bottom:0;background:#fff;border-top:1px solid var(--line);
  padding:11px 26px;display:flex;gap:16px;align-items:center;z-index:40}
.bar{flex:1;height:7px;background:var(--line);border-radius:4px;overflow:hidden;max-width:320px}
.bar i{display:block;height:100%;background:var(--pick);width:0}
button.go{border:1px solid var(--pick);background:var(--pick);color:#fff;border-radius:8px;
  padding:9px 16px;cursor:pointer;font-size:14px;font-weight:600}
button.ghost{border:1px solid var(--line);background:#fff;color:var(--soft);border-radius:8px;
  padding:9px 14px;cursor:pointer;font-size:13.5px}
.prow{background:#fff;border:1px solid var(--line);border-radius:11px;margin:0 0 10px;overflow:hidden}
.psum{display:flex;gap:13px;align-items:center;padding:11px 14px;cursor:pointer}
.psum img{width:54px;height:74px;object-fit:cover;object-position:top;border:1px solid var(--line);
  border-radius:4px;background:#fff}
.pname{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:13px;flex:1;min-width:0;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.pwhy{font-size:12.5px;color:var(--faint)}
.pbody{display:none;border-top:1px solid var(--line)}
.prow.open .pbody{display:block}
.checkline{display:flex;gap:10px;padding:7px 14px;border-bottom:1px solid #f0f2f5;font-size:13.5px;
  align-items:baseline}
.checkline .st{font-size:11px;font-weight:700;width:64px;flex:none;padding-top:2px}
.st.p{color:var(--good)} .st.f{color:var(--bad)}
.md{white-space:pre-wrap;word-break:break-word;font:12.5px/1.5 ui-monospace,Menlo,Consolas,monospace;
  background:#fbfbfc;padding:13px 15px;max-height:440px;overflow:auto;border-top:1px solid var(--line)}
#zoom{position:fixed;inset:0;background:rgba(12,14,18,.9);z-index:90;display:none;overflow:auto;
  padding:20px;cursor:zoom-out}
#zoom img{display:block;margin:0 auto;max-width:none;box-shadow:0 8px 40px rgba(0,0,0,.5)}
.hide{display:none}
</style></head><body>
<header><div class="wrap">
  <h1>Are these checks a fair test of the page?</h1>
  <p class="lede">A model read 25 insurance pages as images and wrote <b>229 checks</b> about what any
  honest conversion must say. Nothing downstream is worth anything if those checks are wrong &mdash; a
  check that misquotes the page by one character fails for ever and makes a correct converter look
  broken. <b>Your job is on this page: for each card, say whether the check is a fair test.</b> The 191
  checks that both pass and read correctly are already settled and are not shown.</p>
  <div class="scoreline" id="scores"></div>
  <div class="tabs">
    <div class="tab on" data-tab="decide" id="tab-decide">Decide</div>
    <div class="tab" data-tab="pages" id="tab-pages">Browse all 25 pages</div>
  </div>
</div></header>
<main>
  <div id="decide"></div>
  <div id="pages" class="hide"></div>
</main>
<footer>
  <div id="prog" style="font-weight:600"></div>
  <div class="bar"><i id="pbar"></i></div>
  <div style="color:var(--faint);font-size:12.5px">keys: <b>f</b> fair &middot; <b>u</b> unfair &middot;
    <b>s</b> unsure &middot; <b>j</b>/<b>k</b> move</div>
  <div style="margin-left:auto;display:flex;gap:8px">
    <button class="ghost" id="reset">Clear my answers</button>
    <button class="go" id="export">Export decisions</button>
  </div>
</footer>
<div id="zoom"><img alt="page, full size"></div>
<script>
const DATA = __DATA__;
const KEY = "truedoc_insurance_fairness_v2";
let saved = {};
try { saved = JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (e) { saved = {}; }
let cur = 0;

const el = (h) => { const d = document.createElement("div"); d.innerHTML = h.trim(); return d.firstChild; };
const esc = (s) => String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

function scores() {
  const t = DATA.tally, need = DATA.cards.length;
  document.getElementById("scores").innerHTML =
    `<div class="stat"><span class="big">${t.passed}/${t.total}</span>
       <span class="lbl">checks TrueDoc passes today (${(100*t.passed/t.total).toFixed(1)}%)</span></div>
     <div class="stat"><span class="big">${t.settled}</span>
       <span class="lbl">settled &mdash; pass, and a second reading agrees</span></div>
     <div class="stat"><span class="big" style="color:var(--pick)">${need}</span>
       <span class="lbl">need your call, grouped by cause below</span></div>`;
}

function cardHTML(c) {
  const img = DATA.images[c.page] || "";
  return `<div class="card" id="c${c.id}" data-id="${esc(c.id)}">
    <div class="chead">
      <span class="num">#${c.n}</span>
      <span class="chip kind">${esc(c.kind)}</span>
      <span class="chip ${c.group === "look" ? "pass" : "fail"}">${
        c.group === "look" ? "we pass it" : "we fail it"}</span>
      <span class="src">${esc(c.page)}</span>
    </div>
    <div class="split">
      <div class="pane-img"><img loading="lazy" src="${img}" alt="the page"></div>
      <div class="pane">
        <p class="ask">${c.statement}</p>
        <div class="verdict ${c.group === "look" ? "ok" : ""}">
          <span class="ico">${c.group === "look" ? "?" : "×"}</span><span>${c.verdict}</span></div>
        ${c.body}
        <div class="second"><b>Second opinion:</b> ${c.second}. That reading is another look at the same
          image, so it can point, not prove.</div>
        <div class="controls">
          <button class="pick" data-d="fair">Fair check<span class="k">f</span></button>
          <button class="pick" data-d="unfair">Not fair &mdash; drop it<span class="k">u</span></button>
          <button class="pick" data-d="unsure">Unsure<span class="k">s</span></button>
          <input class="note" placeholder="note (optional)">
        </div>
        <p class="hint">Fair = the page really says this and we should pass it; this becomes work for
          us. Not fair = the check misreads the page; it gets dropped and never scores us again.</p>
      </div>
    </div></div>`;
}

function drawDecide() {
  const host = document.getElementById("decide");
  host.innerHTML = "";
  DATA.groups.forEach(g => {
    const mine = DATA.cards.filter(c => c.group === g.key);
    if (!mine.length) return;
    host.appendChild(el(`<div class="grouphead"><h2>${esc(g.title)} &nbsp;<span
      style="color:var(--faint);font-weight:500">${mine.length} check${mine.length > 1 ? "s" : ""}</span></h2>
      <p>${esc(g.blurb)}</p></div>`));
    mine.forEach(c => host.appendChild(el(cardHTML(c))));
  });
  host.querySelectorAll(".card").forEach(card => {
    const id = card.dataset.id, rec = saved[id] || {};
    card.querySelectorAll("button.pick").forEach(b => {
      if (rec.decision === b.dataset.d) b.classList.add("on");
      b.onclick = () => choose(id, b.dataset.d);
    });
    const note = card.querySelector(".note");
    note.value = rec.note || "";
    note.oninput = () => { saved[id] = Object.assign({}, saved[id], {note: note.value}); store(); };
    if (rec.decision) card.classList.add("done");
  });
  mark();
}

function choose(id, d) {
  const rec = saved[id] || {};
  rec.decision = (rec.decision === d) ? null : d;
  saved[id] = rec; store();
  const card = document.getElementById("c" + id);
  card.querySelectorAll("button.pick").forEach(b => b.classList.toggle("on", b.dataset.d === rec.decision));
  card.classList.toggle("done", !!rec.decision);
  progress();
  if (rec.decision) { const i = DATA.cards.findIndex(c => c.id === id); if (i >= 0) move(i + 1); }
}

function store() { try { localStorage.setItem(KEY, JSON.stringify(saved)); } catch (e) {} }

function mark() {
  document.querySelectorAll(".card").forEach(c => c.classList.remove("cur"));
  const c = DATA.cards[cur];
  if (!c) return;
  const node = document.getElementById("c" + c.id);
  if (node) node.classList.add("cur");
}
function move(i) {
  cur = Math.max(0, Math.min(DATA.cards.length - 1, i));
  mark();
  const c = DATA.cards[cur], node = c && document.getElementById("c" + c.id);
  if (node) node.scrollIntoView({behavior: "smooth", block: "start"});
}

function progress() {
  const done = DATA.cards.filter(c => (saved[c.id] || {}).decision).length;
  const n = DATA.cards.length;
  document.getElementById("prog").textContent = `${done} / ${n} decided`;
  document.getElementById("pbar").style.width = (100 * done / n) + "%";
}

function drawPages() {
  const host = document.getElementById("pages");
  host.innerHTML = "";
  DATA.pages.forEach(p => {
    const bad = p.checks.length - p.pass;
    const lines = p.checks.map(c => {
      const t = c.check.type;
      const said = t === "present" ? "must say: " + (c.check.text || "")
        : t === "absent" ? "must NOT say: " + (c.check.text || "")
        : t === "order" ? (c.check.before || "") + "  → then →  " + (c.check.after || "")
        : "cell " + (c.check.cell || "") + "  ↔  " +
          ["left","right","up","down","top_heading","left_heading"]
            .filter(k => c.check[k]).map(k => k.replace("_"," ") + ": " + c.check[k]).join(", ");
      return `<div class="checkline"><span class="st ${c.passed ? "p" : "f"}">${
        c.passed ? "we pass" : "WE FAIL"}</span><span>${esc(said)}</span></div>`;
    }).join("");
    host.appendChild(el(`<div class="prow">
      <div class="psum"><img src="${DATA.images[p.name] || ""}" alt="">
        <span class="pname">${esc(p.name)}</span>
        <span class="pwhy">${esc(p.why || "")}</span>
        <span class="chip ${bad ? "fail" : "pass"}">${p.pass}/${p.checks.length} pass</span></div>
      <div class="pbody">${lines}<div class="md">${esc(p.md)}</div></div></div>`));
  });
  host.querySelectorAll(".psum").forEach(s => s.onclick = () => s.parentNode.classList.toggle("open"));
}

document.querySelectorAll(".tab").forEach(t => t.onclick = () => {
  document.querySelectorAll(".tab").forEach(x => x.classList.toggle("on", x === t));
  document.getElementById("decide").classList.toggle("hide", t.dataset.tab !== "decide");
  document.getElementById("pages").classList.toggle("hide", t.dataset.tab !== "pages");
});

document.addEventListener("click", e => {
  if (e.target.tagName === "IMG" && e.target.closest(".pane-img")) {
    const z = document.getElementById("zoom");
    z.querySelector("img").src = e.target.src;
    z.style.display = "block";
  } else if (e.target.closest("#zoom")) {
    document.getElementById("zoom").style.display = "none";
  }
});

document.addEventListener("keydown", e => {
  if (e.target.tagName === "INPUT" || e.metaKey || e.ctrlKey) return;
  const c = DATA.cards[cur];
  if (e.key === "j") { move(cur + 1); e.preventDefault(); }
  else if (e.key === "k") { move(cur - 1); e.preventDefault(); }
  else if (c && "fus".includes(e.key)) {
    choose(c.id, {f: "fair", u: "unfair", s: "unsure"}[e.key]); e.preventDefault();
  } else if (e.key === "Escape") { document.getElementById("zoom").style.display = "none"; }
});

document.getElementById("export").onclick = () => {
  const out = DATA.cards.map(c => ({
    id: c.id, page: c.page, kind: c.kind, group: c.group, why_it_failed: c.verdict,
    decision: (saved[c.id] || {}).decision || null, note: (saved[c.id] || {}).note || ""
  }));
  const blob = new Blob([JSON.stringify({
    note: "Decisions on the checks that needed a person. Every check not listed here passed and was " +
          "corroborated by a second reading; those stay. A proposal record, not a clearance.",
    settled_without_review: DATA.tally.settled, decisions: out}, null, 1)], {type: "application/json"});
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob); a.download = "insurance_check_fairness.json"; a.click();
};
document.getElementById("reset").onclick = () => {
  if (confirm("Clear every answer on this page?")) { saved = {}; store(); drawDecide(); progress(); }
};

scores(); drawDecide(); drawPages(); progress(); mark();
</script></body></html>"""


if __name__ == "__main__":
    build()
