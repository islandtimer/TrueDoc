# Ideas from Other People's Views (OPV) — 7 September 2026

Technique: take each failure group through the eyes of people who are not software engineers, ask what they would notice and do, then move from their view to a mechanism. Harvested first, judged after. Read: the evidence pack, ARCHITECTURE, STATUS, DECISIONS; the failing checks of run 48; our run-48 outputs; `truedoc/ocr/rapid.py` and the function list of `truedoc/tables/aligned.py`; the benchmark PDFs through PyMuPDF (inspection only). Nothing was edited or converted.

Tags: [verified] measured in this session; [derived] computed from those measurements; [assumed] chosen to proceed.

## What I measured before thinking (the facts the ideas stand on)

- **Every benchmark PDF was re-saved by pypdf (old scans by img2pdf); none has a tagged structure tree** [verified: 0 of 881 pages in six sections]. But 56 of 266 headers-and-footers pages, 41 of 231 multi-column and 50 of 188 table pages still carry the producer's own `/Artifact` marked-content tags in the page content stream, 38 / 25 / 39 of them with `/Pagination`; 7 of the 27 pages failing an "absent" check carry them [verified].
- **Our OCR stage sees scans at half to two-thirds of the resolution the scanner recorded.** `rapid.py` renders at most 300 dpi and at most 2,000 px on the long side (`_MAX_SIDE = 2000`, line 21; `scale = min(300/72, _MAX_SIDE/long_side)`, line 108) [verified]. The scans hold 2,100 to 5,100 px on their long side (500 dpi for the dictionary and old-maths books, 300 to 600 for the rest) [verified]. Ratio of our rendered pixels to the scan's pixels, long side: old scans median 0.62 (quarter of pages at or under 0.51), tiny text median 0.69 (quarter at 0.50), old-scan maths median 0.56 [derived]. The two experiments the pack sets aside ("re-reading hidden layers: worse"; "our OCR on tiny text: 13 of 66 against 9") were run at that reduced scale [derived from the code; I did not find a run at native resolution in the docs].
- **Hidden OCR layers come from two makers.** Font `GlyphLessFont` (Tesseract) on 22 pages, `Courier` (an older engine) on 22, `HiddenHorzOCR` on 4, real font names on the rest [verified]. Fifteen of the 36 old-scan-maths pages have a hidden layer; all their failing checks are formula checks, so nothing but a model helps that section.
- **Near misses by edit distance, on pages we did not leave empty** [verified with rapidfuzz on run-48 outputs, my own normalisation, so counts are approximate]: tiny text 18 within 2 edits, 23 at 3-5, 25 at 6-12, 24 far; multi-column 31 / 47 / 65 / 86; old scans (text and order together) 21 / 22 / 21 / 63. Ignoring spaces altogether would pass only 9 + 7 + 6 = 22 checks, so spacing is the commonest edit but not the commonest cause.
- **The commonest letter edits**: old scans e→a (20), e→o (8), e→s (5); tiny text and multi-column e→c (16 + 9); multi-column s→S (20, the small-caps fix already in the code for run 49); `$` inserted (11, inline maths). Dictionary pages want `ə` where the layer wrote o or a (7): no engine of that era knew the phonetic alphabet.
- **The far multi-column cases on hidden-layer pages are line-by-line interleaving of two columns**, not character errors: "…contain REE ex- Microbeam Analysis, 239-246. hibit such laser-induced…" (02e31046 page 2), the same on 0208fbb5 page 3. On those pages no layer line spans both columns (0 of 119 and 0 of 157 lines wider than 60 % of the page) and a 100-dpi ink profile shows an almost ink-free vertical band 8 and 19 px wide at x = 0.49-0.50 of the width [verified]. The picture shows the gutter; the layer's word gaps evidently do not.
- **Three table pages are fixed-width Courier** (0091c5b2 pg3, 26076dc3 pg3, ff19f6fe pg4 — the census printout) with 10 failing checks between them [verified].
- **The 27 failing "absent" checks** sort into: titles at the top that repeat the running head (7 or 8), footnotes we keep by decision D017 (7), single digits the checker finds inside other numbers ('98' in "95-98", '2' in "Monitor 2", '1'; 3, unwinnable), footer lines we wrote as headings or body ("## Schedule A (Form 990) 2022" as the last line, "## 9 Ibid", "## J. Appl. Cryst. (1974). 7, 222" mid-page, "euras.lt", "health.ucsd.edu/jacobs", a timetable code line; about 6), and a scanned letter's signature and date (2-3) [verified by reading each in context].

## The ideas

### 1. Read the page at the resolution the scanner chose

**Whose view.** The scanner operator. They set 500 dpi for the dictionary and the old maths journal because the type was tiny, and 300-400 for the typed letters. Movement: they would be puzzled to learn the reader throws away half the pixels before looking (our 0.5-0.7 scale, above). "I gave you 2,470 by 4,030; you looked at 1,230 by 2,000."

**Concept.** Resolution is evidence we already own and are discarding; the two negative OCR experiments never tested the pixels the operator recorded.

**Mechanism.** For a page whose text will come from OCR, render at the embedded image's own pixel size (scale = image pixels / page points, not a fixed 300 dpi), cut the render into horizontal strips of about 1,000 px with a 60-px overlap, run detection and recognition per strip, drop duplicate boxes in the overlaps, and stitch. Memory stays bounded and the detector (which does not shrink its input: `limit_type: min, 736`) sees every line at full size; the recogniser gets crisper crops (a 5-point line is 17 px tall at our current scale and 35 px at 500 dpi, against the 48-px height the model is trained on). Report confidence the same way as today so the D009 gate is unchanged.

**Failure group and reach.** Old scans: 127 text and order checks on pages we already read; some of the 61 rejected pages may now clear the 0.75 bar (typed letters, not handwriting). Tables read by OCR (21). Old-scan maths: none (formula checks). Tiny text and hidden-layer multi-column pages through idea 6. Honest range: 20 to 80 checks [assumed; the test decides].

**Cost.** 4-6 hours, plus 2-4× OCR time on scanned pages only.

**One-hour test.** Take the ten old-scan pages with the most failing checks on non-empty output (from `failed_tests.jsonl`, sections `old_scans`) and `long_tiny_text/11_pg146_pg1.pdf` (9 failing checks, 501-dpi scan). Render each at native scale, run RapidOCR in strips, and count the wanted snippets found within their `max_diffs` and the mean confidence, against run 48's outputs. If found snippets do not rise by a third, stop.

**Strongest objection.** The recogniser normalises every crop to 48 px high, so pixels beyond about twice the line height may add nothing, and old typefaces (long s, blackletter, worn type) are a typeface problem, not a resolution problem. Then the section is a model's ground and no cheap trick moves it.

### 2. The gutter is in the picture, not in the layer

**Whose view.** A child copying the page by hand. The child does not read the hidden layer; the child sees a white strip down the middle, puts a ruler on it, and copies the left column to the bottom before starting the right. The typesetter agrees: a gutter is a fixed white channel (a pica or so) the full height of the columns.

**Movement.** On the interleaved scanned pages the layer's lines sit correctly within one column each, yet our order alternates left and right lines; the layer's fake glyph widths spill into the gutter so the word-gap voting (`_reassemble_ocr_layer`) finds no clean channel, while the 100-dpi ink profile shows the channel plainly at x ≈ 0.49-0.50 [verified on three pages].

**Concept.** For scanned pages, take geometry from the image and characters from the layer (D010 already says "layout rebuilt from geometry"; this makes the geometry the picture's rather than the layer's boxes).

**Mechanism.** Render at 150 dpi in grey, compute the share of dark pixels per pixel column, find bands under 0.5 % ink in the middle 30-70 % of the width that run over at least 60 % of the text height (a band interrupted by a full-width heading or figure yields a band with a vertical range, exactly as the channel voting already carries). Use the band centre as the column cut for the rows it spans; assign each layer line to a column by its centre; split a line straddling the cut at the character nearest the cut. Apply to OCR-layer pages and to our own OCR pages.

**Failure group and reach.** Multi-column far cases on the 22 hidden-layer pages (3-5 failing checks each, about 60 checks in all); old-scans order checks on read pages (56). Perhaps 30-50 checks [assumed].

**Cost.** 3-4 hours.

**One-hour test.** For the 22 multi-column hidden-layer pages, compute the band and compare with the cut the code chose (page meta); on the pages where the picture finds a band the code did not, re-order the layer lines by the band by hand (a 20-line script) and re-score their order checks with the installed checker.

**Strongest objection.** Narrow gutters blur at low dpi (page 10 of 02e31046 shows a 4-px band at 100 dpi, about 3 pt), and figures or rules spanning both columns break the band; the vertical-range treatment must be right or the rule will cut a single-column page whose ink happens to be light in the middle (a poem, a centred list).

### 3. The producer already marked the running head; read the mark

**Whose view.** A blind reader with a screen reader. Their software skips whatever the producing application marked as `/Artifact /Pagination` (header, footer, page number) and reads only the content. The structure tree is gone from these pages, but the marks inside the content stream survived pypdf's page copy [verified: 56 headers-and-footers pages carry `/Artifact`, 38 with `/Pagination`, including 7 of the 27 failing ones — the legislation page whose "Part 2 — Offences relating to food / Division 1 — …" we print as body, the "Notes"-only page, "SKRIPSI", "TÓXICOS E GUERRAS"].

**Movement.** On a single page repetition cannot confirm a running head; the producer's declaration can, and it is on the page.

**Concept.** Nothing invented: this is the author's own statement of what is pagination.

**Mechanism.** Read the page's content stream (`page.read_contents()`), tokenise just enough to track `BDC … EMC` nesting, and for every `/Artifact` block whose dictionary says `/Type /Pagination` (or `/Subtype /Header`, `/Footer`), remove the block from a copy of the stream held in memory (`doc.update_stream`), then extract text from the copy: what disappears is the running head, foot or page number. Write it to the front matter (`truedoc.running_head`, `truedoc.page_number`), not to the body. Ignore `/Artifact` blocks without a pagination type unless they sit in the top or bottom 10 % band (Word marks table borders and backgrounds as artifacts too).

**Failure group and reach.** Headers and footers: 4-6 of the 27 failing checks [derived from the 7 marked pages]; it also protects the 733 passing ones because the producer's word outranks the heuristic. Much larger for the owner's own documents: InDesign and Word product disclosure statements are tagged, and the same marks tell a PDS's running "Product Disclosure Statement — Home Insurance" from a heading.

**Cost.** 2-3 hours.

**One-hour test.** For the 38 `/Pagination` pages in headers-and-footers, strip the blocks in memory, extract text, and check (a) every absent-check string on those pages is gone and (b) no present-check or order-check string is lost; then look by eye at the 7 failing pages.

**Strongest objection.** Reach on the benchmark is tiny (about a tenth of a point) and some producers mark real content as artifacts (letterhead lines that the benchmark wants dropped are fine; a marked pull quote would not be). Gate by pagination type and band.

### 4. The order the author typed it in

**Whose view.** The typesetter, or the author of the file: "I set the left column first, then the right; the caption went in after the figure." PDF producers (LaTeX, Word, InDesign, browsers) write text into the file in logical order; only scanners, OCR layers and some print drivers scramble it. A screen reader with no tags reads in exactly this order and is usually right.

**Movement.** Our reading order is rebuilt from geometry alone ("column split, else peel the top spanning block, else horizontal cut"). Where geometry is ambiguous — a caption between columns, a sidebar, a form interleaved with prose, a footnote inside a column — the file already carries the author's answer, and we never consult it.

**Concept.** Content-stream order is a second, independent witness to reading order; agree with it when it is consistent with the columns, ignore it when it contradicts them.

**Mechanism.** PyMuPDF's `get_text("rawdict")` without `sort=True` returns blocks in content-stream order; record each character's sequence number in stage 1. In `segment/order.py`, when the geometric rules must choose between placements (peeling a spanning block, ordering blocks inside a horizontal cut, placing a caption or footnote), prefer the placement whose block sequence follows the median sequence numbers of the blocks; refuse it when it would put a lower block before a higher one within the same column, or when the page's sequence numbers are geometrically chaotic (a scan, an OCR layer, a print driver — detectable as high disagreement with y order inside blocks).

**Failure group and reach.** Multi-column: the 16 true ordering mistakes and the 52 mid-sentence block breaks on digital pages; 20-40 checks [assumed].

**Cost.** 3-4 hours.

**One-hour test.** For every failing multi-column order check on a page with a real text layer (not the 22 hidden-layer pages), re-order run 48's blocks by their first character's stream position and re-score the checks with the installed checker; count flips to pass and flips to fail among the passing checks of the same pages. If the net is not clearly positive, the witness is unreliable and the idea dies cheaply.

**Strongest objection.** Some producers emit text by font or by text box rather than by reading order, and two-column LaTeX with floats emits the float where it was placed, not where it is read; the rule only ever helps when geometry is ambiguous, so its gating matters more than its signal.

### 5. The typist's clogged "e"

**Whose view.** The typist, and the proof-reader who reads her letters. Every typist knows the "e" is the key that fills with ink; a proof-reader reading "hespital", "Vory truly", "Republican perty" corrects them without a second look because the blob is an e-shaped blob and the word says so. On the old book scans the failure is the opposite: a thin "e" loses its bar and reads "c" ("trce-lined", "dclle").

**Movement.** OCR errors carry a signature per source: typewriter scans e→a/o/s (33 of the counted edits), hidden book layers e→c (25), and a small fixed set beyond them (l/1/I, rn/m, 0/O, u/n, f/t).

**Concept.** Choosing between two readings of the same ink, with the engine's own known confusions and a word list as the judge, is not invention; the reading "hospital" was one the engine nearly gave.

**Mechanism.** Only for text of OCR origin (our engine or a hidden layer; never the PDF's own characters): for every lower-case token not in a word list (the `_common_words` list in `rapid.py` grown to a 50,000-word list, plus the page's own repeated tokens), generate candidates by one substitution from the confusion set; accept only if exactly one candidate is in the list and the original is not; never touch capitalised tokens, numbers or tokens inside formulas; record each change in the front matter under `truedoc.ocr_corrections` so the reader can audit it.

**Failure group and reach.** Old scans near misses on read pages (about 40 checks within 5 edits), tiny text (about 40), multi-column hidden layers (part of 78 within 12 edits). Realistic 30-50 checks [assumed].

**Cost.** 3 hours.

**One-hour test.** Apply the rule offline to run 48's output files for the three sections (they are plain markdown) and re-score every text and order check on those pages with the installed checker; count flips both ways.

**Strongest objection.** D008 in spirit: the owner must decide whether an engine's second choice, chosen by a word list and recorded in the front matter, counts as "nothing invented". And names are where references fail ("Yernaux", "Heinesch") and a word list cannot help them; the capital-letter guard is essential.

### 6. Their lines, our letters

**Whose view.** The person who made the hidden OCR layer in 2009. "I ran the engine at default settings and never proof-read it. My line boxes are right — I found every line, even the six-point ones; my letters are what my engine could do then." Tesseract's `GlyphLessFont` layers (22 pages) and the Courier-layer engine (22 pages) make different mistakes from RapidOCR.

**Movement.** The pack's page-level re-read compared whole pages, at reduced resolution, and let our detector — the weak part on tiny type — redo the layer maker's best work. Give the recogniser the maker's line boxes instead.

**Concept.** Two readers who err differently can arbitrate line by line; the maker supplies the lines, our engine supplies a second opinion on the letters.

**Mechanism.** For a hidden-layer page, crop each layer line from the scan image at native resolution (idea 1), run only the recognition model on the crop (no detection), and compare with the layer's text for that line: identical, keep; different, keep whichever reading has more tokens in the word list (ties to the layer); with idea 5's confusion set, prefer the reading that the other one differs from by a known confusion only. Mark nothing as inferred: both readings are OCR of the same ink and the front matter already records the page as an OCR layer.

**Failure group and reach.** Tiny text: the 24 far and 25 mid cases plus some of the 23 at 3-5 edits (the pack's "54 not in the layer at all"); multi-column hidden-layer near misses. Perhaps 20-40 checks [assumed].

**Cost.** 4 hours after idea 1's rendering exists.

**One-hour test.** On `11_pg146_pg1.pdf` and `13_pg162_pg1.pdf` (12 failing checks together; one Courier layer, one Tesseract layer): crop the layer lines at native resolution, recognise, arbitrate, and count wanted snippets found against run 48. This test is also idea 1's test for tiny type; run them together.

**Strongest objection.** The pack's page-level result (13 of 66 against 9) says the engines are close; if the native-resolution test in idea 1 fails, this fails with it. And a dictionary page is half abbreviations and phonetic symbols, which no word list contains, so arbitration must fall back to the layer for such lines.

### 7. Count the characters

**Whose view.** A typist reading a line-printer census page, or a child copying it with a ruler. In Courier every character sits in a cell of the same width; a column boundary is a vertical run of blank cells, and `|` and `:` are drawn rules between columns; you find the columns by counting characters, not by measuring.

**Movement.** Three table pages are 96-100 % Courier with 10 failing checks [verified]; the whitespace-channel finder treats them as proportional type and measures in points what is really an integer.

**Concept.** On a monospaced page, geometry is exact; build the text-mode picture and read it like a terminal screen.

**Mechanism.** When over 90 % of a block's characters carry PyMuPDF's monospace flag or a Courier-family font name, snap each character to a grid (column = round((x − left)/character width), row = line), producing a character matrix; a column separator is a grid column that is blank, `|` or `:` for every row of the run; cells are slices of the matrix; consecutive heading rows are joined per column (the stacked-heading convention). Hand the result to the existing table renderer.

**Failure group and reach.** Tables: about 10 checks on the benchmark [derived]; for the owner, government printouts and bank statements.

**Cost.** 3 hours.

**One-hour test.** Thirty minutes: dump the three pages as character matrices with a 20-line script and see whether the blank grid columns delimit "16 and 17 Years", "5,303", "10.6 %" and "Gestation (weeks)" by eye.

**Strongest objection.** Three pages. And `|` and `:` on the census page may be separators inside a cell string rather than between cells, so the rule needs to see them line up over most rows before treating them as rules.

### 8. The librarian's catalogue card

**Whose view.** The librarian cataloguing the page reads the running head first — journal, volume, year, page — and writes it on the card, never into the transcription. She also knows a heading with nothing under it is not a heading: at the foot of a page it is the footer.

**Movement.** About six of the failing absent checks are footer lines we wrote as headings or body: "## Schedule A (Form 990) 2022" as the last line of the page, "## 9 Ibid", "## J. Appl. Cryst. (1974). 7, 222" in mid-page (the running mark of an old journal), domain-only lines ("euras.lt", "health.ucsd.edu/jacobs"), a timetable's code line [verified].

**Concept.** The front matter is the catalogue card; running marks belong there, and the benchmark's "absent from the body" is satisfied without losing anything.

**Mechanism.** (a) A block classed as a heading that is the last text on the page, of body size or smaller, in the bottom 8 % band, becomes a footer. (b) A line matching a journal mark (abbreviated title, year in parentheses, volume, page) anywhere becomes `truedoc.running_head`. (c) A line that is only a URL or domain in the bottom band becomes `truedoc.footer`. All three write to the front matter rather than dropping.

**Failure group and reach.** Headers and footers: 4-6 of 27 [derived]; complements idea 3 (which needs the producer's marks; this works on scans).

**Cost.** 2 hours.

**One-hour test.** Apply to the 27 failing pages and re-score; run the section's 733 passing checks on the same rule and count losses.

**Strongest objection.** A tenth of a point at best, and rule (a) can eat a real heading that starts a section continuing on the next page; the 8 % band is the guard.

### 9. The proof-reader's dangling hyphen

**Whose view.** The proof-reader reads for sense: a line ending in "ex-" must be continued by "hibit"; a sentence that has not reached its full stop cannot be interrupted by a reference-list entry; an open bracket must close.

**Movement.** The far multi-column cases on scans show exactly this ("ex- Microbeam Analysis, 239-246. hibit"), and the 52 mid-sentence block breaks on digital pages are the same fault with a caption or footnote as the intruder. Where geometry failed, the text itself still says what follows what.

**Concept.** Text carries order evidence of its own: hyphen continuation, lowercase starts, unmatched brackets.

**Mechanism.** After reading order is set, walk consecutive blocks: if block A ends with a hyphenated fragment (or with no terminal punctuation and an open bracket) and the next block B starts with a capital, a citation pattern or a caption/footnote marker, look for a block C in the same column band that begins in lowercase and whose first token, joined to A's last fragment, is a word in the page's own vocabulary or the word list; move C to follow A and B after it. Apply only where the geometric stage recorded low confidence (no clean column cut) so it is a backstop, not a guess.

**Failure group and reach.** Multi-column far cases and block breaks: 15-30 checks [assumed]; overlaps with ideas 2 and 4, which fix the geometry first.

**Cost.** 4 hours.

**One-hour test.** From the far multi-column checks, count those whose wanted text contains a hyphen break or lowercase continuation that our output separates by an intruding block; fewer than 15 means do not build.

**Strongest objection.** The pack says there is no single pattern, and moving a footnote to the wrong place invents an order; hence the gating to pages where geometry already gave up.

### 10. Write "k = 2" the way the page shows it

**Whose view.** The author of the benchmark, copying the sentence as it reads on the page: "when k = 2". The blind reader's screen reader says the same: "k equals 2". Only LaTeX wants `$k=2$`.

**Movement.** Eleven multi-column failures are `$` inserted around a run of plain letters, digits and one relation sign [verified count of `''→'$'` edits]. The checker strips bold and italic markers but not `$`.

**Concept.** Inline maths that is only letters, digits and one relation is prose to every human reader; render it as the page shows it, with the glyph gaps as spaces.

**Mechanism.** An inline maths run is written without dollars when it contains no fraction, radical, script, Greek, operator name or accent — only `[A-Za-z0-9]` around one relation or binary sign — with a space either side of the sign when the glyphs show a gap; everything else stays `$…$`. Apply only on pages with no display formulas (multi-column pages are not maths papers), so the arXiv section is untouched.

**Failure group and reach.** Multi-column: up to 11 checks [derived].

**Cost.** 1 hour.

**One-hour test.** Thirty minutes on run 48's outputs: rewrite `$x=y$`-shaped runs to plain text on non-maths pages and re-score those 11 checks plus every formula check on pages that changed (expect none to change).

**Strongest objection.** The arXiv section's 2,927 checks include inline maths in prose; the page-type gate is the whole protection, and a maths page with one such run in the introduction is a coin toss either way.

### Also harvested, not developed

- **The forensic accountant's cross-foot.** For numeric tables with a Total row or column, or percentages summing to 100, test the column assignment by arithmetic and prefer the assignment the whitespace channels allow under which the sums check. Touches some of the 75 relation errors (label column offset from its numbers, headings glued across columns); needs two independent sums to agree before moving anything. 4-5 hours; test by listing the relation-error pages with a Total row and checking five by hand.
- **The insurance broker reads the legend first.** In a tick-mark table the blanks carry meaning ("not covered") and the legend at the foot names the symbols; when marks from `marks.py` line up in two or more columns beside a column of names (the attendance list in the table failures), build the table from name lines × mark columns and keep blank cells. One benchmark page; many of the owner's.
- **Relation signs from symbol fonts by rendering.** "P50.005" for "P=0.005": a symbol-font glyph with no Unicode map drawn as `=`; extend D013's template matching (ticks and crosses) to `=`, `<`, `>`, `≤`, `≥`, `±`, `†`, `§`. Two or three checks.

## Best bet

**Idea 1, read the page at the resolution the scanner chose, with idea 6 tested in the same hour.** Reasons: it is the only idea that touches the two biggest groups (old scans, 418 failing; the OCR-side of tables and multi-column) without a model; it rests on a measured fact nobody in the docs has examined (our OCR sees scans at 0.5-0.7 of their pixels, and both negative OCR experiments ran at that scale); it invents nothing; and its test costs an hour with the engine already installed. The fact that would flip it: if the ten worst old-scan pages and `11_pg146` yield no more wanted snippets at native resolution than at the current scale, resolution is not the bottleneck, typeface is, and those sections are the vision stage's ground exactly as the pack says. Runner-up: idea 2 (the gutter is in the picture), because its premise is already verified on three pages and its test is a 20-line script.

## Claims in the evidence pack I doubt

1. **"Our own OCR read of those pages is not better than the hidden layer" and "re-reading hidden layers: worse than the layer".** Both true as run, but run at half to two-thirds of the scans' resolution [verified from `rapid.py`]; they do not yet show what the engine does with the pixels the operator recorded.
2. **"148 of the multi-column failures are near misses in the text, 16 true ordering mistakes, 52 block breaks."** My census finds 86 far cases on non-empty pages, and the far cases on hidden-layer scans are line-by-line interleaving of two columns — an ordering fault that the "hidden OCR layer's own character errors" heading hides. The true-ordering count is higher than 16 once scanned pages are included.
3. **"Page numbers and journal marks survive on single pages because running heads cannot be confirmed by repetition."** Three of the 27 are single digits the checker finds inside other numbers and cannot be won; and 7 of the 27 pages carry the producer's own pagination marks, so on those the confirmation is on the page.
4. **"Every page is one page: nothing can be learned from a document's other pages."** True of other pages; but each page still carries its producer's marked content and its content-stream order, two witnesses the pipeline does not call.
