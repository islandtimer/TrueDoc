# Escape from dominant ideas: TrueDoc lateral round (7 September 2026)

Technique: name an idea that the pipeline, and the whole field, builds on; ask what we would do if it were simply unavailable; move from that to a mechanism concrete enough to build. Judgement is held back to the "strongest objection" line of each entry and to the closing section. Everything marked [verified] was checked here on the run-48 outputs, the failed-tests file, the benchmark PDFs and the checker's source; nothing was converted or scored.

## Ground truth I established before generating

- **How a check is worth points** [verified from `score_output.txt`]. The overall score is the mean of eight group pass-rates, and baseline is its own group (1,394 checks; 8,413 tests scored in all). One check is therefore worth 12.5/N points: old-scan maths 0.027, tiny text 0.028, old scans 0.024, headers 0.016, multi-column 0.014, tables 0.012, baseline 0.009, arXiv 0.004. One old-scan-maths check is worth six arXiv checks.
- **The 61 empty old-scan pages are handwritten letters** [verified, contact sheet of all 61]; about eight carry a printed letterhead ("Beckner Printing Company", "Commonwealth of Massachusetts, Executive Department").
- **Old-scan maths** [verified]: 36 pages, 10 empty (8 of book 1's 9 pages, whose print is clean 1890s calculus, plus one page each from books 3 and 5). 313 of the 449 failing checks sit on pages we *do* read. The references are short (median 27 characters: `OA=a`, `mn=pq`, `12 x = 42`, `y = sin x`). Our output on those pages already contains 25 of the references as plain OCR text (`mn = pq`, `x = 0.2`, `y = sin x`, `y=f(x)`) outside any `$`. Meanwhile the geometric maths rebuild, running on OCR characters, wraps nonsense in `$$…$$` that KaTeX cannot parse (the scorer's log shows "Double superscript" errors coming from our own files).
- **The maths checker** [verified from `tests.py` and `render.py`]: it reads only `$…$`, `$$…$$`, `\(…\)`, `\[…\]`; it passes on an exact string match, or when the reference's rendered MathML is *contained* in the hypothesis's MathML with all whitespace stripped. `$mn = pq$` matches `mn=pq`; `$x^2 = 1$` matches `x^{2}=1`.
- **Multi-column** [verified]: of 233 failing order checks, 131 fail *only* through near-misses (best window at least 90% similar). The 89 near-miss pages split 61 digital, 28 scanned. The commonest differences are letter case (small caps; the fix is queued for run 49), e read as c, punctuation, and the benchmark's own wrong references (our "Heinesch, B., Yernaux, M." is the real author list; the reference says "Heinsch, F., Vernaux"). 46 snippet failures are a sentence broken by an interleaved block (one half or both halves found); 99 snippets are absent, and 46 of those exist in the PDF's text layer (we dropped or altered them) while 53 do not (pictures).
- **Tables** [verified with the checker's own parsers]: 79 failing checks where our table holds the cell but a relation is wrong (23 test the column heading, 16 the right neighbour, 15 the cell above, 11 the row heading, 8 below, 6 left); 78 where the text is present in our file but is not a cell of any table; 69 where the text is absent (pictures, rejected OCR).
- **Tiny text** [verified]: 38 snippets at 95% similarity or better, 33 at 85% or better; dominant differences are missing word spaces (queued for run 49), comma/period, e/c. The scans behind pages 10a-16c are 1,054-1,272 pixels wide at one pixel per point, about 120 dpi: the hidden layer was almost certainly made from a better image than the one we hold.

---

## Idea 1. Characters by agreement, arbitrated by the page's own ink

**Dominant idea escaped.** "The text layer is the truth for characters" (D004, D010): on a scanned page the hidden OCR layer *is* the reading. **Movement:** if the layer were unavailable we would read the ink; if the ink is poor we would let two readers argue and settle the argument with evidence from the page itself. There is no truth-teller, only witnesses, and the page image is the court of appeal.

**Concept.** Two witnesses per line (the layer, and our recogniser on the line's own crop), with a page-local arbiter for the characters they dispute.

**Mechanism.** For every line of a hidden layer, crop the line's box from the page image at 2-3x and binarise it, and run only RapidOCR's recogniser (no detector: the layer already gives the boxes). Align the two strings character by character. Where they agree, done. Where they differ by one to three characters, decide by (a) the recogniser's per-character probability, then (b) the page's own glyphs: from words both witnesses agree on, cut every e, c, a, n, m, l, i at the layer's character boxes, average them into page-specific templates, and send the disputed crop to the nearest template. Larger disagreements keep the layer (never rewrite a word wholesale). Provenance "layer+recogniser", a count in the front matter.

**Failure group and reach.** Near-miss characters: tiny text (about 40 of the 71 near misses), multi-column on the 28 scanned pages (25-40 checks), old-scan present checks on typed pages (about 15). Roughly 60-90 checks, 1.5-2 points.

**Cost.** 8-12 hours (crop-and-recognise 2-3, alignment 2, templates 3-4, gating and tests 2).

**One-hour test.** Take the 38 tiny-text snippets at 95%+ (my diff names the disputed characters). Crop those lines from `bench/data/olmocr-bench/bench_data/pdfs/long_tiny_text` at 3x, run the recogniser alone, count how often it reads the disputed character as the reference does. Under a third: dead for tiny text. Separately, on three pages, cut every e and c from agreed words, average them, and classify the nine e/c errors; fewer than six right kills the template half.

**Strongest objection.** The tiny-text scans are about 120 dpi, so the layer was made from a better image than we have and our witness may be systematically worse there (the pack's page-level re-OCR was worse). The idea then lives only on the multi-column and old-scan pages scanned at 200 dpi or more.

## Idea 2. Sentences stitch the order

**Dominant idea escaped.** "Geometry first": reading order is a recursive geometric cut of blocks (`segment/order.py`), and text is only cargo. **Movement:** if geometry were unavailable, the text would have to order itself, and it can: a sentence that stops in mid-air resumes somewhere, and usually only one block can resume it.

**Concept.** Sentence continuity as a second, text-level ordering signal that repairs and vetoes geometric decisions.

**Mechanism.** After the geometric order, walk the text blocks. Block A "hangs" when its last line has no terminal punctuation and reaches the column's right edge, or ends in a hyphen. Look ahead up to three blocks in the same column for a block B that begins lowercase, or completes A's hyphenated word (dictionary check). If found, every block between A and B of another kind (caption, footnote, figure, table, form box, sidebar, letterhead line) moves to after B. The same test vetoes a column cut: if reading across the cut gives continuity at most line ends and reading down does not, the cut is wrong.

**Failure group and reach.** Multi-column sentences broken by an interleaved block: 46 snippet failures on 37 pages; old-scan letters where letterhead lines interleave with the body. About 25-35 checks, 0.4-0.5 points.

**Cost.** 4-6 hours.

**One-hour test.** List the 37 pages (my census marks them one-half-found or both-halves-found). On ten, read our output, apply the rule by hand, count fixes and breakages. Then grep our arXiv and table outputs for "hanging block followed by a lowercase block" to count false triggers.

**Strongest objection.** The pack found "no single pattern" in these 52 pages; lists, references and some languages begin blocks in lowercase legitimately; a moved footnote can land after the wrong paragraph for a human reader even when the checker is satisfied.

## Idea 3. The line is the unit of trust

**Dominant idea escaped.** "A confidence gate accepts or rejects a page whole" (D009: mean line confidence 0.75, word-like share 0.5). **Movement:** a page is not read or unread; lines are.

**Concept.** Per-line acceptance with a page-level sanity floor, and page means that ignore formula-shaped lines.

**Mechanism.** Accept each OCR line on its own merits: confidence at least 0.85 and word-like or numeric (or agreed by two reads, idea 4). Reject the rest, and list them with box and confidence under `truedoc.ocr_rejected_lines` in the front matter. Write the page when at least three lines are accepted. When any page-level mean is computed, exclude formula-shaped lines (symbol-heavy, few dictionary words) so a page of worked examples is not thrown away because its equations read as noise.

**Failure group and reach.** The 10 empty old-scan-maths pages (book 1 is clean print; see the doubts below), the printed letterhead on about eight handwritten pages, and the garbage lines on the 37 typed old-scan pages (reader quality rather than checks). About 20-30 checks, 0.4 points, and it is the door that idea 5 and idea 9 walk through on those pages.

**Cost.** 2-3 hours.

**One-hour test.** Run `ocr_page_turn` on the ten empty old-scan-maths PDFs and print per-line confidence and word-likeness; count the lines at 0.85 or better that are real words (eyeball twenty). If the book-1 pages each have ten or more such lines, the page mean was the culprit and the "old typeface" explanation is wrong.

**Strongest objection.** Confident fragments without context: "Vory truly your" scores 0.9. D008's reasoning (noise is worse than a gap) applies to fragments too, and a reader who sees three lines of a letter may assume that is all it said.

## Idea 4. Read three ways, keep what agrees

**Dominant idea escaped.** "One OCR engine, one pass, and its confidence number measures truth." **Movement:** with no confidence number available, the only evidence for a character is that independent reads agree on it.

**Concept.** Agreement across reads as confidence; test-time variety from a single engine.

**Mechanism.** For pages without a text layer, OCR three renders: the 2,000 px cap, native resolution (tiled where needed; the old-scan images are 2,400-6,400 px on the long side and are currently read at about 180 dpi-equivalent, spreads at 120), and a Sauvola-binarised version. Align lines by box overlap and characters by edit alignment; take the majority character; confidence becomes the agreement rate. Lines agreed by all three are accepted even when the engine's own score is under 0.75.

**Failure group and reach.** Old-scan near misses on typed pages (e read as a, n as m, l as i: about 35 present checks under 95%), old-scan-maths characters that feed idea 5, and perhaps a few rejected pages. About 30-50 checks, 0.8-1.2 points.

**Cost.** 4-6 hours; OCR time triples on the ~180 image-only pages.

**One-hour test.** On the 37 typed old-scan pages, run OCR at 2,000 px and at native size; my census script counts snippets found and near-missed. If the union of the two reads finds fewer than ten more snippets than the single read, drop the idea.

**Strongest objection.** Same network, same training data, so the errors are correlated: an e/a confusion on a Caslon face is a knowledge gap, not noise, and the majority repeats it. The honest second witness is a genuinely different engine (Tesseract, Apache-2.0 [recalled], with historical-print models), which means an install and a licence check.

## Idea 5. On OCR pages a formula is a string, not glyph geometry

**Dominant idea escaped.** "LaTeX is rebuilt from the maths fonts' glyphs and positions" (the crown jewel: arXiv 86.8). On an OCR page there are no fonts, only strings, yet the geometric rebuild runs anyway and emits unparseable LaTeX. **Movement:** if glyph geometry were unavailable, the equation is the string the engine read, lightly grammared.

**Concept.** A string grammar replaces the geometric rebuild on pages of kind ocr-truedoc.

**Mechanism.** On OCR pages, switch the geometric rebuild off. Detect equation lines (a line containing `=` or `:` ratios, or a run of digits and single letters, with few dictionary words). Normalise only typed cues: `==` to `=`, `--` and dashes to `-`, letter-then-digit `x2` to `x^{2}` on equation lines, `a/b` with one-token sides to `\frac{a}{b}`, the radical sign to `\sqrt`, `×` to `\times`. Wrap the line in `$…$`, provenance "ocr-grammar". Never add a symbol the engine did not read. The checker ignores whitespace and accepts containment, so `$mn = pq$` passes `mn=pq` and `$y^2 = 4ax$` passes `y^2 = 4 ax`.

**Failure group and reach.** Old-scan maths on the 26 pages we read: a floor of 25 checks today (verified present as plain text), rising with every character gain from ideas 3, 4 and 9 (313 failing checks on read pages; the section holds 12 points of headroom). Plus the reader-facing removal of invalid LaTeX from every OCR page. About 25 checks now, 0.7 points, with the largest upside on this list.

**Cost.** 4-8 hours.

**One-hour test.** No conversion needed. Write the ten-line normaliser, apply it to copies of our existing old-scan-maths `.md` files (wrap the equation lines), and run `olmocr.bench.tests.MathTest` for the 26 non-empty pages' checks only; count passes against today's 19 for the whole section.

**Strongest objection.** OCR of old maths is riddled with errors (`Ga == bc` for `ad = bc`, `12%=42` for `12 x = 42`), so the floor stays small until character accuracy rises; and a stray `$` in OCR prose can break present and order checks on old-scan pages, so the wrapping must be limited to whole equation lines.

## Idea 6. Tables as local relations, not grids

**Dominant idea escaped.** "A table is a grid found top-down: rulings or whitespace channels define cells, and the heading line is split at its own gaps." **Movement:** what the checker tests, and what a reader needs, is local: what is above, beside and heading this cell. Columns are defined by the body's numbers; headings are words to be *assigned* to those columns; and some "tables" are not grids at all but lists of records.

**Concept.** Body-defined columns with assigned headings; records for forms and keys; typed characters as rulings.

**Mechanism.** (a) Find body columns from the numeric cells' whitespace channels; assign every heading word to the column whose x-range overlaps it most (stacked heading lines join inside the column); a word overlapping two columns becomes a spanning heading (HTML colspan). Before emitting, self-check: every numeric body cell must have a non-numeric heading above it and a label to its left; if not, reassign. (b) When the aligned finder sees two columns of label:value pairs (the Polish form: "typ | do 15 pkt."; the botanical key's couplets A/aa, B/bb; the attendance list with marks), emit a two-column table label | value (the checker reads the first column as row heading). (c) On fixed-width printouts, runs of `|`, `+`, `-`, `=` characters are rulings: hand them to the ruled-table finder as if drawn.

**Failure group and reach.** 79 relation-wrong checks (23 column heading, 11 row heading) and 78 present-but-not-a-cell checks. Perhaps 50 checks together, 0.6 points.

**Cost.** (a) 4-6 hours; (b) 4-6 hours; (c) 2-3 hours.

**One-hour test (the judge as an instrument).** For six of the 52 relation-wrong pages, rewrite our own table by hand with headings assigned by body columns, using only the cell text we already emit, and run `TableTest` on the edited file; if the checks pass, the target is reachable from our text alone. Do the same for the Polish form and the botanical key with a label | value table.

**Strongest objection.** Several heading rules have already been built (runs 40-48, roughly five checks each), and the odd pages' reference structure is an annotator's choice (a dichotomous key rendered as a table) that a general rule may never reproduce.

## Idea 7. Nothing is lost: the character ledger

**Dominant idea escaped.** "The layout model and the classifiers decide what a region is, and the renderer prints what survives"; dropped text is nobody's fault. **Movement:** a conservation law. Every visible character of the text layer must land in the body or be accounted for by name (header, footer, hidden, page number, figure label).

**Concept.** An inventory invariant enforced after rendering, doubling as a regression guard.

**Mechanism.** Diff the visible text-layer words (minus the named exclusions) against the body's words. Any run of five or more consecutive missing words is re-inserted beside its nearest neighbour in reading order (same column, nearest baseline), and the front matter records what came back and which block kind had swallowed it. The diff runs on every page and turns a rule that silently drops text into a visible imbalance before any benchmark run.

**Failure group and reach.** Multi-column absent snippets that exist in the text layer: 46 snippet failures on about 25 pages (20-30 checks); tiny text 4; tables 15 (the lake diagram's label stacks, the sideways table). About 40 checks, 0.6 points.

**Cost.** 3-4 hours.

**One-hour test.** For the 46 in-layer absent snippets, print which of our block kinds covers each snippet's box (figure, hidden, header, or nothing). The count by cause says whether re-insertion is safe or whether specific rules must be fixed instead.

**Strongest objection.** Some text is dropped for a good reason (hidden text under D011, a chart's axis labels) and re-inserting it hurts readers and the 96.3 headers section; and order checks need position, not mere presence.

## Idea 8. The honest note for pages we cannot read

**Dominant idea escaped.** "A page is either transcribed or empty" (D008). **Movement:** a careful human transcriber writes neither nonsense nor nothing; they write what they can honestly say.

**Concept.** An observed description in place of silence: counts and confident lines, no guessed words.

**Mechanism.** When OCR is rejected, classify the page cheaply (line-detector count, confidence profile, confident letterhead lines from idea 3) and write one bracketed note in the body, for example `[Handwritten page, about 23 lines, not transcribed. Printed letterhead: "Beckner Printing Company, Lexington, Ky."]`, repeated in the front matter. Every word in the note is observed.

**Failure group and reach.** The 71 baseline checks on empty pages (0.64 points) plus a few present checks on letterhead text.

**Cost.** 2 hours.

**One-hour test.** Run the line detector on the 61 handwritten and 37 typed old-scan pages and confirm the note would fire only on rejected pages. The real test is the owner's decision, not a script.

**Strongest objection.** This is the owner's D008 line: a note is not the page's content, and a competitor could call it score-gaming. The counter is that the baseline check exists to punish garbage and silence, the note is neither, and it is what an archivist writes on an uncatalogued letter.

## Idea 9. A formula reader as a second witness, gated by the first

**Dominant idea escaped.** "No vision model, so maths on scans is out of reach; CPU OCR reads words, not formulas." **Movement:** the constraint bars *large* vision-language models, not small task models with permissive licences. A formula-crop recogniser (an image-to-LaTeX model of the pix2tex / LaTeX-OCR kind: MIT-licensed [recalled, must be verified], tens of millions of parameters, CPU-viable per crop [recalled]) reads formula lines, and the OCR string gates it so nothing is invented.

**Concept.** Two witnesses of different kinds on the same crop; the text witness vetoes the formula witness.

**Mechanism.** Formula lines come from the layout model's formula regions or idea 5's equation-line detector. Crop at native resolution, run the recogniser, keep its LaTeX only if its letters and digits, stripped of commands, match the OCR read of the same crop within a small edit distance; wrap in `$…$` with provenance "formula-model" and the D015 inferred tag.

**Failure group and reach.** Old-scan maths: 313 failing checks on read pages and, with idea 3, the 126 on empty ones. Even a third is 100-150 checks, 3-4 points, the largest headroom on the board.

**Cost.** 8-16 hours (install and licence check, crop pipeline, gating, tests) and a model download.

**One-hour test.** Crop twenty formula lines by hand from `4_pg186`, `4_pg451` and `2_pg238` (PyMuPDF clip at native resolution), run the recogniser, render both sides with the checker's `render_equation`, count matches. Fewer than five of twenty: dead on old print.

**Strongest objection.** A model trained on rendered LaTeX may collapse on letterpress ink and yellow paper; the gate discards good readings whenever OCR itself misreads the same crop (on old print, often); and the owner must agree that a model of this size counts as a "small task model".

## Idea 10. Plain maths stays plain on digital pages

**Dominant idea escaped.** "Markdown with LaTeX is the target, so anything mathematical goes into `$…$`." **Movement:** the output is a reading; the markup should be the least that carries the meaning. `k = 2` in a sentence is prose.

**Mechanism.** An inline formula with no LaTeX command, no script and no brace, at most 12 characters long, is written as plain text with the page's own spacing (`k = 2`), not `$k=2$`. The checker does not strip `$`, so today the dollar signs and the missing spaces fail the snippet.

**Failure group and reach.** Multi-column order checks whose snippets contain such maths: 6 by my count, 11 by the pack's. Risk on arXiv: only 7 of 2,927 references are plain formulas and all are longer than 12 characters [verified], so the loss is about zero. Net 6-11 checks, 0.1-0.15 points; nearly free.

**Cost.** 1 hour.

**One-hour test.** Apply the rule to copies of the failing multi-column outputs and re-run those order checks; count the arXiv references the rule would touch (I count none).

**Strongest objection.** Tiny gain; and a reader who wants every formula machine-readable loses the delimiters on the trivial ones.

---

## Single best bet

**Idea 5, formulas as strings on OCR pages**, with idea 3 as its door. It has the highest per-check weight on the board (0.027 points a check), a verified floor of 25 checks without any OCR improvement, a one-hour test that needs no conversion (edit copies of existing outputs, run the maths checker), it removes reader-facing garbage (LaTeX that KaTeX cannot parse) from every OCR page, and it compounds: every character gained later by ideas 3, 4 or 9 in the old-scan-maths section flows straight through it. The fact that would flip it: if the test shows fewer than 15 of the 25 floor checks passing because stray `$` pairing or the checker's regex defeats the wrapping, the idea shrinks to a reader-quality fix and idea 9 becomes the bet.

If the owner will entertain a small task model, idea 9 has the largest headroom (3-4 points) and its one-hour test is cheap; run that test before committing the 8-16 hours.

## Claims in the evidence pack I doubt

1. **"Our own OCR read of those pages is not better than the hidden layer (tried: 13 of 66 strings found against the layer's 9)."** As written, 13 is more than 9: either the sentence or the numbers is wrong. Either way the quantity that matters for idea 1 is the *union* of the two readings, which the sentence forecloses.
2. **"Multi-column: 148 near misses ... the hidden OCR layer's own character errors on scanned pages."** My census: 89 near-miss pages, 61 digital and 28 scanned [verified]. The commonest differences are letter case (small caps, fix queued for run 49) and the benchmark's own wrong references, not scanned layers. Expect run 49 to recover a sizeable slice by itself; the scanned-layer share is about a third.
3. **"RapidOCR's English model cannot read old typefaces" as the reason the old-scan-maths pages are empty.** Eight of the ten are book 1, clean 1890s print [verified from the contact sheet]; those pages are mostly formulas, so the page mean most likely fell under the bar because equations read as noise. Idea 3's one-hour test settles it.
4. **The 2,000 px OCR cap** is not mentioned in the pack. The old-scan letters are stored at 2,400-3,200 px and read at about 180 dpi-equivalent; the spreads (pages 48, 51, 57) at about 120 [verified]. Not the cause of the handwriting failures, but a free variable in idea 4's test.
5. Cosmetic: the seven section files hold 7,019 tests, and 1,394 baseline checks are scored as an eighth group (8,413 in all), not "7,010 checks".
