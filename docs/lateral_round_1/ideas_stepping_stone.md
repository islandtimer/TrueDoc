# Stepping stones and wishful thinking (lateral-thinking round, 7 September 2026)

Technique: de Bono's stepping stone. Say "wouldn't it be wonderful if..." about the hardest failures, then move from the wish to the nearest real mechanism. Judgement was withheld until after the harvest; each idea ends with its strongest objection.

Evidence tags: [verified] = counted or inspected in this session from the run-48 failing checks, the benchmark files, the checker's code and our outputs; [recalled] = from memory, not checked here; [assumed] = a choice made to proceed.

## How I worked (read-only)

Read in order: the evidence pack, ARCHITECTURE, STATUS, DECISIONS. Then: the run-48 failing checks (1,896 rows), the benchmark's own test files, the checker's code (`olmocr.bench.tests`), our run-48 outputs, and a census of every benchmark PDF's internals (producer, structure tree, marked content, fonts, images) with PyMuPDF. Rendered pages and word crops for inspection only. No conversions, no benchmark runs, no OCR runs, no installs. Scratch files are in the session scratchpad, nothing under `truedoc/` or `docs/` was touched.

Facts that shaped the wishes [verified]:

- The pack's per-section failure counts exclude the baseline checks (old scans 479 rows = 418 + 61 baseline; old-scan maths 449 = 439 + 10). The two agree.
- No benchmark PDF carries a structure tree (pypdf's single-page extraction dropped it), but marked-content tags survive: `/Artifact` on 56 of 266 headers pages, 41 of 231 multi-column, 50 of 188 tables, 11 of 62 tiny-text; `/MCID` on 80, 58 and 69 of those sections. Old scans are all `img2pdf` images with no text; old-scan maths has 21 pages with no layer, 10 with a Tesseract-style "GlyphLess" layer, 5 with another layer.
- Table failures by the checker's own reasons: 94 "cell not found", 53 "no table in output", 79 relation errors (19 top heading, 16 right, 15 above, 9 left heading, 8 below, 6 left, 4 no top heading, 2 no left heading). Of 41 heading-relation failures where the cell *is* in one of our tables, the wanted heading text is present inside a table line in 33.
- Tiny-text failures by page kind: 53 of 90 are on the 23 pages with **no text layer at all** (our own RapidOCR, on 72 to 167 dpi page images); 28 on 27 pages with a non-Tesseract layer (Courier hidden layers and digital newspaper pages); only 9 on the 12 Tesseract-layer pages.
- Multi-column failures by page kind: 82 on digital pages (no page image), 119 on scanned pages with a hidden layer, 32 on pages with no layer.
- Old scans: the 61 empty pages carry 351 of the 479 failing rows; all 61 are cursive handwriting (contact sheets inspected), with printed letterheads on about six. The 37 pages we do read carry 128 failures, mostly typewriter spelling slips.
- Old-scan maths: all 458 checks are formula checks. 117 are plain one-line equations (16 pass), 134 need only super/subscripts (0 pass), 207 are structured (3 pass). On the 10 Tesseract-layer pages we trust the layer's characters (D010) and rebuild formulas from text such as `50 (11 —2) +102 = 810.` (the page reads `50 (11 − x) + 10 x = 310`).
- Content-stream order (PyMuPDF `get_texttrace` sequence numbers) over all 884 multi-column order checks: where both snippets can be found in the raw stream text, the stream has them in the right order for 290 of 314 passing checks (92 per cent) and 21 of 25 failing ones; a plain top-to-bottom sort of words finds both snippets in only 95 passing checks (stream: 314 of 545 not-found cases recovered). Digital pages: 134 of 142 right; hidden-layer pages: 156 of 172. The 32 wrong verdicts cluster: four pages hold 16 of them.
- Seven failing table pages have 35 to 100 per cent of their text running up or down the page (20 failing checks); two of them are picture tables with a stub text layer (10 checks). Three table pages are set entirely in Courier (10 failing checks).
- The checker: HTML tables honour `th`, `colspan` and `rowspan` (every header level above a column is recorded; a rowspan label is copied into every row it spans); markdown tables get first row and first column only. `normalize_text` leaves `<td>` tags in place, so table text inside HTML does not match text checks (seen on one multi-column page).
- RapidOCR's engine object exposes `text_rec`, `text_cls` and `get_crop_img_list` (already used in `ocr/rapid.py`); our OCR renders at `min(300/72, 2000/long_side)`, so a 600 dpi scan is read at half its resolution and a 72 dpi page image is read at roughly its own resolution. `sympy` 1.14, `cv2` 5.0 and `numpy` are in the venv; `scipy` and `skimage` are not.

## The wishes (harvest first)

1. Wouldn't it be wonderful if the PDF told us its reading order. It nearly does: the content stream is the order the producer wrote the text, and it is right 92 per cent of the time when it can be judged.
2. Wouldn't it be wonderful if the running head confessed. On some pages it does: `/Artifact` marked content wraps the running heads (the Food Act page's two failing heads sit inside one).
3. Wouldn't it be wonderful if every scanned word had a second witness. It has: the hidden layer read the ink once, our engine can read the same ink again, and the two disagree in different places.
4. Wouldn't it be wonderful if the scanner had a higher resolution. The page has hundreds of copies of each letter; averaging them is a resolution the scanner never had.
5. Wouldn't it be wonderful if the font program told us each letter. On old print there is no font, but the page's own glyph shapes repeat, so the page is its own font: cluster the shapes, name each cluster once.
6. Wouldn't it be wonderful if every table announced its grid. The body rows do: aligned numbers mark the columns better than the crowded headings above them; in monospace the grid is literally character positions.
7. Wouldn't it be wonderful if the table's headings said what they span. HTML can say it, and the checker listens to `colspan` and `rowspan`.
8. Wouldn't it be wonderful if the equations checked themselves. In a worked example each line follows from the one before; algebra is a checksum on the OCR.
9. Wouldn't it be wonderful if the sideways table turned itself. The engine's angle classifier can turn a region as well as a page.
10. Wouldn't it be wonderful if the page told us its genre. The fonts do: a page with no maths fonts is prose, and `k = 2` in prose is text, not LaTeX.
11. Wouldn't it be wonderful if the busy page were two pages. Body-sized text and small-type interlopers (captions, footnotes, references) separate by size and by stream position.
12. Wouldn't it be wonderful if handwriting were print. It is not, and nothing in the page makes it so; the honest mechanism there is the optional vision stage. Left as a wish.

## The ideas

### 1. The PDF tells us its reading order (content-stream order as a witness with a trust gate)

**Wish and movement.** Wish 1. The structure tree is gone from these files, but the order in which the producer *drew* the text survives in every content stream, and that order is what a typesetter emits: paragraph after paragraph, column after column. Our XY-cut never looks at it.

**Concept.** Treat the content stream as a second, independent opinion on reading order, and use it where geometry is ambiguous: islands, spanning blocks, and sentences that a caption or a reference list breaks in two.

**Mechanism.** In stage 1, keep each character's sequence number from `page.get_texttrace()` (already called for the maths pass). Give every line and block a median sequence number. Then (a) a trust gate per page: within each column we find, compute how often consecutive stream numbers agree with our top-to-bottom order (a rank correlation); trust the stream on the page only when agreement is high; (b) where trusted, order blocks by stream number inside each region the XY-cut produces, instead of by y; (c) a continuity rule: two blocks adjacent in the stream whose text joins mid-sentence (no terminal punctuation, next block starts lower-case or with a hyphen tail) stay adjacent in the output, and any block that would fall between them (a caption, a footnote, a reference entry) is deferred until the sentence is complete. Nothing is invented: the characters and their boxes are unchanged; only the order between blocks changes, and the front matter can record when the stream was used.

**Group and reach.** Multi-column order: 16 true ordering mistakes plus about 52 sentence breaks, ceiling around 68; the stream already has 21 of the 25 judgeable failing checks right, so 20 to 35 checks is a fair expectation. It also protects headers (running heads are often first or last in the stream).

**Cost.** 6 to 10 hours.

**One-hour falsification.** Already half done here. For the 32 checks where the stream order is wrong on passing checks, and the 21 where it is right on failing ones, compute the per-page rank agreement between stream order and our column order. If a single threshold separates the two groups (it should: the wrong verdicts sit on four pages), build it; if the wrong verdicts are spread over pages that look trustworthy, stop.

**Strongest objection.** Some producers (page-composition tools, print drivers) emit text in an order that is neither geometric nor logical, and hidden OCR layers emit in the OCR engine's order, which is line-by-line across columns on some pages. The trust gate must be strict, and a page that fails it must fall back to today's behaviour with no change at all.

### 2. Two witnesses for every scanned word (word-level arbitration between the hidden layer and our engine)

**Wish and movement.** Wish 3. The pack set aside a page-level re-read: replace the whole layer with our engine's reading, and the result was worse. But its own numbers say the two readers find *different* strings (our engine found 13 of 66 failing snippets, the layer 9). Two witnesses who err in different places can be combined; one cannot be replaced by the other.

**Concept.** Keep the hidden layer as the incumbent and let our engine challenge it one word at a time, with the image as the judge and a lexicon as the tie-breaker.

**Mechanism.** On a page with a hidden layer, skip our detector: the layer's line boxes say where the lines are. Crop each line from the rendered page (this is also a better crop than the detector makes on tiny type) and run only the recogniser (`engine.text_rec` on `get_crop_img_list` crops, as the sideways-turn code already does). Align the two readings token by token (difflib on tokens). Where they agree, done. Where they differ: accept the challenger only if (a) the recogniser's confidence for the line is high, (b) the two tokens differ by a known confusion (e/c, l/I/1, G/6, rn/m, o/0, curly and straight quotes, a dropped or added space), and (c) the challenger is a word in the English list or in the page's own vocabulary while the incumbent is not, or both are numbers and the challenger's digit pattern matches its neighbours (an accession number column). Otherwise keep the layer. Record the number of arbitrated words in the front matter. Extend the same arbitration to the two scanned-table cases: a layer whose word-likeness on a table region is very low (the "Sohom O..t Sompk 117" page) is challenged region by region.

**Group and reach.** Tiny text on hidden-layer pages (37 failing), multi-column near misses on hidden-layer pages (119 failing, many of them character slips), scanned table pages with garbage layers (about 21 pages). A realistic 30 to 50 checks.

**Cost.** 8 to 12 hours.

**One-hour falsification.** Take the 36 failing tiny-text pages. For each failing snippet, find the words where the reference and our output differ. Crop those words' lines (layer boxes), run `text_rec`, and count (i) how many snippets would pass under a union of the two readings (the ceiling) and (ii) how many under the arbitration rule above. Also count how many *passing* snippets the rule would break. If the ceiling is under 15 of 90, the idea is dead.

**Strongest objection.** Where the layer is wrong the image is often bad too (72 dpi page images, 6-point type), and the recogniser's charset lacks the phonetic and accented letters dictionary pages use; the challenger may be confidently wrong in exactly the places the layer is wrong.

### 3. The page is its own high-resolution scan (glyph clustering, prototype averaging, one label per shape)

**Wish and movement.** Wishes 4 and 5. A 72 dpi dictionary page has perhaps two thousand instances of "e". Each is a blurred 8-pixel blob; their average is a clean letter. And once the page's shapes are clustered, naming a cluster once names every instance, so errors become consistent instead of random, and one dictionary vote fixes fifty words. This is how JBIG2 symbol dictionaries and the "unsupervised OCR by decipherment" line of work treat print [recalled].

**Concept.** For pages with no usable layer and small or old type, recognise the page's alphabet, not its words.

**Mechanism.** Binarise the rendered page (adaptive threshold), take connected components (`cv2.connectedComponentsWithStats`), drop rules and pictures by size, normalise each component to a fixed box, cluster by shape (agglomerative on a Hamming or correlation distance; no scipy needed for a greedy leader-cluster pass). Average each cluster's members into a prototype. Recognise prototypes, not instances: paste a cluster's prototype into a synthetic line at a comfortable size and read it with the existing recogniser, or read whole lines re-rendered from prototypes (a "clean copy" of the page). Then decode the page as the sequence of cluster labels along each baseline, and let a dictionary vote flip a cluster's label when that single flip turns many non-words into words. Touching letters (a cluster that is two letters) are split by the recogniser's reading of the prototype. Output only lines whose words pass the existing word-likeness gate; the rest stay empty, so nothing is invented.

**Group and reach.** Tiny text on the 23 no-layer pages (53 failing), the 37 typewritten old-scan pages we read poorly (128 failing), and the prose lines of old-print maths pages. A realistic 30 to 60 checks, and the largest long-run reach of anything here, because dictionaries, gazetteers and old newspapers are exactly the pages customers scan badly.

**Cost.** 20 to 30 hours. The wild one.

**One-hour falsification.** On `long_tiny_text/14b_pg1.pdf` (a 72 dpi dictionary page, 5 failing checks): components, greedy clustering, and a contact sheet of the sixty largest clusters' averaged prototypes. If the prototypes are legible letters and sixty clusters cover most of the ink, the mechanism holds; if the clusters are mush or number in the thousands, stop. Half an hour more on `old_scans/22.pdf` (typewriter) tells whether it transfers to old print.

**Strongest objection.** Cursive and badly touching print defeat component analysis, and the pages that matter most (72 dpi dictionary type) are the ones where letters touch most. It may only work on the pages that RapidOCR already reads at 90 per cent.

### 4. Let the body define the columns (column channels from the data rows; headings inherit them)

**Wish and movement.** Wish 6. The mutual-funds page (10 failing checks) has twelve narrow columns whose stacked headings ("5 Year Return %", "Diver-sity", "Beta (Risk)") crowd together, so the whitespace finder sees four columns and glues headings across them. But the body rows are unambiguous: every number sits under its own heading, right-aligned, on every row.

**Concept.** Find the columns from the rows that are easiest (short aligned tokens), then assign the hard rows (headings) to those columns by overlap.

**Mechanism.** In the aligned-table finder, build the column channels from data rows only: rows whose tokens are short (numbers, codes, yes/no, single letters). Each channel is the x-range of tokens that stack vertically. Then place heading words by x-overlap with the channels: a word over one channel joins that heading; a word over two or more channels becomes a group heading spanning them (see idea 5); heading fragments stacked in several lines above the same channel are joined top-down into one heading. A label column offset from its numbers is handled by the same overlap test in reverse.

**Group and reach.** Tables: the 10 checks on that page, and a share of the 79 relation errors (glued headings, stacked headings, label offset): 15 to 30 checks.

**Cost.** 6 to 8 hours.

**One-hour falsification.** On `tables/11e12a3ddca3b1743f6ec1c22a52cdbf9ffe_pg8_pg1.pdf`, dump the words with boxes, keep the numeric rows, compute channels, and check by hand that every heading word overlaps exactly one channel (or a contiguous run of them). If heading words straddle channels ambiguously on this easy page, the idea is weaker than it looks.

**Strongest objection.** Tables of prose cells have no clean data rows; the rule must only fire when a majority of rows are short-token rows, or it will shred wrapped-text tables the way the run-10 rule did.

### 5. Headings announce their spans (HTML header stacks with colspan and rowspan)

**Wish and movement.** Wish 7. The checker reads HTML tables properly: every `th` level above a column is a heading of that column, and a `rowspan` label is a heading of every row it covers. Markdown can say neither, so we join stacked headings into one cell (which then fails when the reference wants only the group heading, "Triacylglycerols (%)" over "CCLa") and repeat group labels down rows. Our renderer already writes HTML with `colspan` for some ruled tables.

**Concept.** Say what we know: when a table has more than one heading level or a label that spans rows, write it as an HTML table with the spans.

**Mechanism.** In the renderer, switch a table to HTML when the finder recorded a header stack (two or more heading rows) or a row-spanning label. Write `<thead>` with one `<tr>` per heading level, `colspan` on a heading whose x-range covers several columns, and `rowspan` on a group label instead of repeating its text. Keep markdown for plain tables (readers prefer it). Nothing changes in what is read, only in how the structure is written.

**Group and reach.** Tables: of 41 heading-relation failures where the cell is in our table, the wanted heading is present in a table line in 33; realistic 15 to 25 checks.

**Cost.** 4 to 6 hours (the spans are mostly already known to the finder; the run-49 "label spans its rows" rule supplies the rowspans).

**One-hour falsification.** Hand-write the HTML for the `c8cdd4c476` table (group heading over sub-headings) and the `9c38972000` table, run the checker's `TableTest` on the hand-written file, and confirm the failing relations pass. Then confirm that the same page's other checks still pass with the HTML form.

**Strongest objection.** Text inside HTML tables no longer matches text-presence and order checks (`<td>` tags are not stripped), so HTML must be confined to pages that are tables, and a reader loses the plain markdown look.

### 6. In monospace the grid is literal (a character-grid parser for printouts)

**Wish and movement.** Wish 6 again, at its extreme. The census printout is set in Courier: every character sits at a column position, the separators `:` and `|` are drawn *as characters*, and rows are lines. The whitespace finder treats it as free text and produces a tangle of pipes.

**Concept.** When the page is monospace, parse it as a text file, not as geometry.

**Mechanism.** Detect a monospace page (over 90 per cent of characters in a fixed-pitch font, or all advances equal). Map each character to (row, column) by rounding its origin by the pitch and the line height. Columns of the table are runs of grid columns that are blank (or `:` / `|`) on every data row; stacked headings above a data column join top-down; a heading spanning several data columns becomes a group heading (idea 5); indented row labels are group rows. Emit the table from the grid.

**Group and reach.** Tables: 10 failing checks on three Courier pages here; in the real world, mainframe reports, bank statements and census printouts.

**Cost.** 4 to 6 hours.

**One-hour falsification.** On `tables/ff19f6fe9ce187ea79f84df52004534e6ff7_pg4.pdf`, write the character grid to a text file and look at it: if the numbers line up under the headings in the text file, the parser is a day's work; if the pitch drifts (kerned "monospace"), stop.

**Strongest objection.** Small reach on this benchmark, and a monospace page of prose (a typewritten letter) must be left alone: the rule needs the blank-column signature before it fires.

### 7. The equations check themselves (algebra as a checksum on old-print maths)

**Wish and movement.** Wish 8. Old-scan maths is not a text problem: all 458 checks are formulas, and 251 of them are one-line equations with at most super/subscripts. Our reading of `50 (11 − x) + 10 x = 310` is `50 (11 —2) +102 = 810` (from the Tesseract layer we trust). But this is a worked example: "Simplifying", "Transposing", "Uniting", "Dividing" label each line, and each line is algebraically derivable from the last. The page contains its own answer key.

**Concept.** Read equation lines as sets of candidate strings (OCR confusions), and pick the reading under which consecutive lines are consistent.

**Mechanism.** (a) On pages with a Tesseract-style layer, stop trusting the layer on equation lines (centred, contains `=`, mostly digits and single letters); read those lines with our engine too (idea 2's crops). (b) Build candidates per token from a confusion table for this typeface (`%` and `x`, `4` and `+`, `8` and `3`, `—` and `-`, `l` and `1`, `O` and `0`, `2` and `x` in italic). (c) Parse candidates with sympy; keep the combination where line k+1 equals line k transformed by one step (expand, move terms, collect, divide by a constant), and where a labelled step matches its label. (d) Put super/subscripts from the ink: a digit whose ink top sits above the x-height of its neighbour is an exponent (script-only checks are 134 of the section). (e) Emit `$...$` for the chosen reading, and mark the line as arbitrated in the front matter. If no consistent combination exists, emit the plain reading unchanged.

**Group and reach.** Old-scan maths: ceiling 251 (117 plain plus 134 script-only); a realistic 30 to 80 if the characters can be got right on the clean textbook pages.

**Cost.** 12 to 16 hours.

**One-hour falsification.** Take the four checks of `old_scans_math/4_pg98.pdf` and the layer's four readings. With the confusion table and sympy, enumerate candidates and test whether the algebra-consistent combination is unique and equals the references. Then count over the section how many failing one-line checks sit on pages whose lines carry step labels or `=` chains (the redundancy the idea needs).

**Strongest objection.** Choosing among OCR candidates by consistency is one step from inventing, and the owner's rule is strict; it must be limited to candidates the ink supports (each substitution a known confusion for a glyph that is actually there) and be marked. The structured half of the section (matrices, fractions) stays out of reach.

### 8. The running head confesses (marked content and stream position for single-page running heads)

**Wish and movement.** Wish 2. Running heads cannot be confirmed by repetition on a single page, but a producer that tags pagination artifacts has already confirmed them: `/Artifact` (often with `/Type /Pagination` and `/Subtype /Header`) wraps exactly the running head, and page-composition tools draw master-page items first or last in the stream.

**Concept.** Read the producer's own declaration of what is not body text.

**Mechanism.** Parse the page's content stream for `/Artifact ... BDC ... EMC` blocks (a small depth-aware scan; done here in a dozen lines) and count the text-showing operators before each block to map it onto texttrace sequence numbers; lines inside such blocks are headers or footers whatever their position or length. Second signal: lines in the top or bottom 12 per cent whose sequence numbers are the first or last few of the stream. Both are recorded as provenance.

**Group and reach.** Headers and footers: 2 to 4 of the 27 failing checks (the Food Act page's two heads are inside an artifact block); mostly insurance against regressions, and it generalises to other documents.

**Cost.** 3 to 4 hours.

**One-hour falsification.** Over the 266 headers pages, for those with artifact blocks, extract the strings inside them and count how many of the benchmark's "must be absent" strings they contain, and how many body snippets from the other sections they wrongly contain (should be none).

**Strongest objection.** Tiny reach on this benchmark; only a fifth of pages carry the tags, and some producers tag footnotes or printer's slugs, so the tag cannot override a footnote decision.

### 9. Turn the picture, not the page (sideways picture tables on stub-text pages)

**Wish and movement.** Wish 9. Two failing table pages (10 checks) are a photograph of a table lying on its side with a few dozen characters of real text (a title, a product line); the text makes the page "readable", so OCR never runs, and `--ocr-pictures` reads the picture unturned. Five more pages have most of their text running up or down and their tables unstructured (10 more checks).

**Concept.** Apply the page-turning machinery to a region.

**Mechanism.** When an image covers more than half the page and the text layer is under a few hundred characters, OCR the image region; if most boxes are tall, ask the angle classifier which way (the existing `_sideways_turn` logic on the crop), rotate the crop, read again, map boxes back, and run the aligned-table finder on the region. For rotated text-layer tables, transpose the region's coordinates (swap x and y within the region) before the table finder and transpose the result back.

**Group and reach.** Tables: about 10 checks certain, up to 20.

**Cost.** 3 to 4 hours.

**One-hour falsification.** Crop the picture on `tables/fbeb6edcf6ad16adbd2a27b54da0c1771389_pg1.pdf`, rotate it both ways, run RapidOCR, and see which orientation reads with confidence at or above 0.8 and contains "ZIP BAG". Same for `4db371aebdbbfa28531a816f9bf26ed0a028_pg52_pg1.pdf`.

**Strongest objection.** The pictures are low-resolution photographs; the read may fall under the confidence bar, and then the honest output is still empty.

### 10. The fonts tell the genre (inline maths in prose is prose)

**Wish and movement.** Wish 10. Eleven multi-column checks want `k = 2` and we write `$k=2$`; the checker strips bold and italics but not dollar signs. A maths paper needs the dollars (its checks render LaTeX); a prose page does not. The page says which it is: maths papers carry maths fonts (cmmi, cmsy, MathTime, STIX and kin, which `is_extension_font` already names); prose pages do not.

**Concept.** Decide the notation per page from the fonts, not per run from the characters.

**Mechanism.** If a page has no maths font and no display formula, write inline runs that consist only of letters, digits, relation signs and spaces as plain text with spaces around the relation (`k = 2`, `n > 3`), keep Greek as Unicode, and keep `$...$` for anything with a fraction, script or operator. Record the choice in the front matter.

**Group and reach.** Multi-column: 11 checks; small but nearly certain.

**Cost.** 2 to 3 hours.

**One-hour falsification.** List the fonts of the 11 pages and of a sample of arXiv pages; confirm the rule separates them cleanly, then rewrite the 11 outputs by hand and run the order checks.

**Strongest objection.** A prose page with a rare real formula written in the body font would lose its LaTeX; the guard "no fraction, script or operator" limits the damage to expressions that read fine as text anyway.

## Discards from the harvest (kept for the record)

- Arithmetic checksums on table totals (a "Total" row constrains OCR digits): only one failing table check mentions a total; no reach here.
- Read the printed letterheads on handwritten pages (line-level acceptance): about five snippets ("WE NEVER DISAPPOINT", "BROCKHURST, VICE-PRES'T E.G.", "Willow Brook Running and Driving Park"); real but tiny, and confident noise lines are a risk.
- Looking up public transcriptions (these are Roosevelt and Holt letters with published transcripts): not a converter's job, and it would be invention by another name.

## Best bet

**Idea 1, the content-stream order.** The evidence is already in hand rather than hoped for: right on 290 of 314 judgeable passing checks, right on 21 of 25 judgeable failing ones, and it keeps sentences findable where a geometric sort loses them (326 against 545 not-found). It needs no model, changes no characters, costs a week-day, and its failure mode is visible in the same data (four pages hold half the wrong verdicts), so the trust gate can be tuned before a run. It also gives the sentence-break problem (52 checks, "no single pattern" in the pack) a single pattern: stream adjacency plus sentence continuity. The fact that would flip it: if the per-page agreement score cannot separate the 32 wrong verdicts from the 311 right ones, the idea is a coin toss on those pages and should be dropped.

Second, for certainty per hour: idea 5 (HTML header stacks), because the checker's semantics are exact and the test is a hand-written file. Third, for the largest long-run reach: idea 3 (the page as its own font), which is the only mechanism here that attacks the biggest honest pool, tiny type and old print with no layer, without a vision model.

## Claims in the evidence pack I doubt

1. "Long tiny text: 54 snippets are not in the hidden OCR layer at all... 32 near misses... our own OCR is not better than the layer." [verified otherwise] 53 of the 90 failing checks are on the 23 pages that have **no text layer at all**; they are our own OCR's reads of 72 to 167 dpi page images. Only 37 failures are on hidden-layer pages (28 non-Tesseract, 9 Tesseract). The section's problem is mostly small type at low resolution, not somebody else's OCR.
2. "Our own OCR read of those pages is not better than the hidden layer (13 of 66 found against the layer's 9)." The numbers as given say our engine found *more* of the failing strings. Two readers that find different strings are a case for word-level merging (idea 2), not for choosing one.
3. "Old-scan maths: old printed maths, scanned: text and formulas must be present." [verified otherwise] The section's 458 checks are all formula checks; there is no text-presence check in it, so better prose OCR gains nothing there, and 251 of the checks are one-line equations that need correct characters and script placement, not a vision model.
4. "A table printed sideways on a landscape page" (one item). [verified otherwise] Seven failing table pages have 35 to 100 per cent of their text running up or down the page, 20 failing checks, and two of them are picture tables with a stub text layer that never reaches OCR.
5. Not a claim in the pack but a consequence of D010 worth flagging: on the 10 Tesseract-layer old-maths pages (117 checks, 108 failing) the layer's characters are trusted although the layer is garbage on equations (`50 (11 —2) +102 = 810`), and our own engine is never run on them.
6. Milder: "multi-column near misses are the hidden OCR layer's own character errors". 82 of the 233 failing order checks are on digital pages with no page image, where no layer exists; the near misses there are hyphenation, ligatures, inline maths and dropped spaces, which are ours.
