# Reversal round: ten ideas for TrueDoc (7 September 2026)

Technique: de Bono's reversal. For each stage I turned the direction of inference round, then moved from the reversed statement to something buildable. I read the evidence pack, ARCHITECTURE, STATUS and DECISIONS, the code for stages 1, 2, 3, 6 and 7 and the OCR engine, and I did not read the Marker/MinerU note. Nothing was converted or benchmarked; I inspected run 48's failing checks, our outputs and the benchmark PDFs read-only.

## The census the ideas rest on

Before generating, I re-counted run 48's failing text checks with the checker's own normalisation, so each idea below carries a number. Method: for every failing `present`/`order` snippet, the Levenshtein distance from the snippet to its best-aligned substring in (a) our markdown and (b) the PDF's own text layer, both normalised by `olmocr.bench.tests.normalize_text`; table checks were re-parsed with the checker's own `parse_markdown_tables`/`parse_html_tables`. "Near miss" means within three edits beyond the check's allowance. All figures below are derived here, per check unless stated.

| Section | What the census says |
|---|---|
| Multi-column, 233 | 4 on empty pages; 17 true order errors (both snippets present); 79 near misses, of which 32 fail on spaces alone; 133 further away (sentences broken or lost). 54 checks sit on scanned pages whose hidden layer is itself wrong; 92 pages are digital. |
| Long tiny text, 90 | 3 order-only; 46 near misses (17 on spaces alone); 41 further away. 53 of the 90 snippets are on 16 pages that have no text layer at all (0 characters): they are our own RapidOCR reads, not an old hidden layer. |
| Old scans, 417 present checks | 290 on the 71 rejected (empty) pages; 87 further away; 40 near misses (15 on spaces alone). |
| Tables, 226 | 79: cell matched, relation wrong. 39: the cell text sits inside a longer cell of a table we did produce ("Fund Type 5 Year Diver-"). About 45: the cell text is nowhere in our output (pictures, dropped text, OCR misreads). About 10: present but outside any table. 53: no table at all (39 of those have no cell text either, 5 on an empty page, 9 with the text present). |
| Headers and footers, 28 | 8 are lines we rendered as headings ("## OPEN ACCESS", "## Schedule A (Form 990) 2022" at the foot of a form, "## J. Appl. Cryst. (1974). 7, 222", "## 9 Ibid"); 6 are footnotes kept by decision D017; 3 are bare digits ("1", "2", "98"), which the checker fails whenever that digit string appears anywhere; the rest are URLs, a signature, a date line and "Notes". |
| Spaces | Of all edit operations inside near misses, 139 are a space: 78 where the reference has one and we do not ("closer;for", "Jason,slain", "received.I hereby", "usualormore"), 61 the other way (" A pesane", "Sirs ;", "trans- forming"). 49 of the 78 follow a punctuation mark. A spacing rule alone flips about 20 near-miss checks (3 multi-column, 8 tiny text, 9 old scans); 64 checks are space errors and nothing else. |
| Resolution | `ocr/rapid.py` renders a page for OCR at `min(300 dpi, 2000 px on the long side)`. The old-scan PDFs hold images 3,300 to 6,400 px wide, so we read them at between a half and a third of the scan's resolution: 414 of the 417 failing old-scan checks (the 290 on rejected pages included) are on such pages, plus 27 table, 17 tiny-text and 12 multi-column checks. RapidOCR itself never shrinks a large image (its detector only enlarges short sides under 736 px) and reads each line crop at 48 px tall, so sharper input reaches the recogniser directly. |
| Coverage | On the 91 failing digital multi-column pages, 73 have at least three runs of eight consecutive body-zone words from the text layer that are absent from our output; 44 have ten or more. Some are figure labels, but the examples include body sentences and a failing snippet ("treatment (applying dirt and saliva, tomato, salt, or AJINOMOTO"). |

---

## Idea 1. Tile the scan; never shrink it

**Reversal and movement.** "One page is one image" becomes "one page is many small pages". Movement: if the page is cut into tiles, each tile can be read at the scan's own resolution while the OCR engine still sees an image of the size it likes.

**Concept.** We are throwing away most of the pixels of exactly the pages we read worst. The engine has been judged ("cannot read old typefaces") on images shrunk to a third.

**Mechanism.** In `ocr/rapid.py`, render at the larger of 300 dpi and the page image's native pixel size (PyMuPDF gives each image's width in pixels). If the render exceeds 2,000 px on a side, cut it into tiles of about 1,600 px with a 10 per cent overlap, run the engine on each tile, map the boxes back to page points, and de-duplicate lines in the overlaps (drop a box whose centre lies inside a neighbouring tile's non-overlap core). Then the existing gate, word-building and layout run unchanged. Line crops reach the recogniser at 48 px tall from a sharp source instead of an upsampled blur.

**Failure group and reach.** Old scans (127 non-empty failing checks, and a share of the 290 on rejected pages if the confidence of old print rises above 0.75 when it is read sharp), old-scan maths text checks, 27 table checks on image-only pages, 17 tiny-text, 12 multi-column. Realistic first gain: tens of checks; ceiling: a few hundred.

**Cost.** 4 to 6 hours including the de-duplication.

**One-hour test.** Take `old_scans/48.pdf`, `51.pdf`, `57.pdf`, `70.pdf` (native 5,300 to 6,400 px, currently read at 2,000 px) and `long_tiny_text/17_pg4_pg1.pdf` (2,592 px, read at 1,296). Render at native size, OCR four overlapping quarters, and count reference snippets from the section JSONL found within their allowance, against the current whole-page read. Also record the mean confidence on the four old-scan pages: if it crosses 0.75 where it was under, the rejected-page share is in play too.

**Strongest objection.** The engine's recogniser was trained on modern print; a sharper blackletter or 1890s typeface may still come back as noise, and handwriting certainly will. Nine engine calls a page cost time (about 9 x 1 s on this CPU). The flip fact: no more snippets found at native resolution on those five pages.

---

## Idea 2. Let the characters place the spaces

**Reversal and movement.** "Words are built from the gaps between glyphs" becomes "gaps are built from the words". Movement: the text itself says where spaces must and must not be; geometry is only a tie-breaker.

**Concept.** A comma followed by a letter in running text has a space after it whatever the glyph boxes say; a semicolon has no space before it; "usualormore" is three words because the word list says so; "trans-" at a line end followed by "forming" is one word because "transforming" is a word.

**Mechanism.** A pass after `_chars_to_words` (and after `_split_words` on OCR lines and on hidden layers, where most of the damage is): (1) insert a space after `, ; : ! ?` when a letter follows; after `.` when a lower-case letter precedes and a capital follows; never inside digits, URLs, e-mails or two-letter abbreviations; (2) remove a space before `, ; : . ! ? )` and after `( " '` opening; (3) for a token not in the word list, try the split into two or three list words (the existing `_split_token`, extended to OCR lines and to tokens glued to punctuation); (4) at a line end, a hyphenated fragment joins the next line's first token when the joined word is in the list, including across a block or column boundary, which is where "trans- forming" and "nega- tive" come from today.

**Failure group and reach.** Near misses in multi-column, tiny text and old scans. 64 checks are space errors and nothing else; the punctuation part alone is worth about 20; with the hyphen joins and dictionary splits perhaps 35 to 50.

**Cost.** 3 to 4 hours.

**One-hour test.** Apply rules (1), (2) and (4) as a text filter to the run-48 outputs of those three sections and rescore with the official checker; expect about 20 wins, and confirm no `absent` or table check is lost. Then list the tokens rule (3) would split on the same outputs and eyeball fifty.

**Strongest objection.** Some references are themselves glued ("betweentwo", "salutationsto", "metalfoams": at least five) so a correct fix cannot win those; and a space after "." can break "e.g." or "Ph.D" style abbreviations unless the digit and abbreviation guards hold. Non-English word lists are missing, so rule (3) does nothing for Polish or Indonesian pages.

---

## Idea 3. Read the markdown back against the page (a coverage audit)

**Reversal and movement.** "Read the page to write the markdown" becomes "read the markdown to find what the page still has". Movement: we cannot render markdown to pixels cheaply, but we can hold the output against the text layer word by word, which is the same check in one dimension.

**Concept.** Nothing invented is the rule; nothing lost should be its twin. Today no stage knows when a sentence fell out between blocks, and the benchmark only samples a few sentences a page, so losses hide.

**Mechanism.** After rendering, take the visible text layer's words in MuPDF order, slide a window of eight words, normalise both sides the checker's way, and test each window against the output. A run of two or more consecutive missing windows inside the body band (idea 4) and outside figure and table boxes is a "lost text" event. Two uses: first a report (page, words, position) that ranks pages by lost text for the engineer; second an automatic repair that writes the lost run back as its own paragraph immediately before the first found window that follows it, and lists it in the front matter under `truedoc.recovered_text`. Every recovered word is the PDF's own.

**Failure group and reach.** The 39 multi-column snippets and 6 tiny-text snippets that are in the layer but not in our output, the 15 table checks the pack calls "text we dropped", and the 52 sentences broken at a block boundary become findable. Realistic: 20 to 40 checks, plus a lasting instrument.

**Cost.** 3 hours for the audit report, 3 more for the repair.

**One-hour test.** Run the audit over the 91 failing digital multi-column pages (it took two minutes here) and hand-check the ten pages with most missing windows: body text or margin and figure matter? If at least half are body text, the repair is worth building; either way the report is.

**Strongest objection.** A recovered paragraph lands in a plausible but not certain place, so it may fix a `present` check and still fail the `order` check; a false miss (a table cell split by "|" that the normaliser does not join) would duplicate text, which the repetition baseline and `absent` checks punish. Guards: only runs of twelve words or more, never in the margin band, never inside a table box.

---

## Idea 4. Find the body; the margin is what is left

**Reversal and movement.** "Find and drop the running head" becomes "find the body; everything outside it is margin matter". Movement: on a single page repetition can never be observed, but the body can.

**Concept.** The classifier's comment says "Main text mass: where do most characters live vertically?" and then the code never computes it; it judges each block alone against fixed 9 per cent zones and size ratios, which is how "OPEN ACCESS" became a heading and "Schedule A (Form 990) 2022" a heading at the foot of a form.

**Mechanism.** Compute the body band: the tallest vertical run of lines at the modal size whose leading is regular (each line's baseline within 1.5 x the modal leading of the next). A line outside the band, short (two lines or fewer, twelve words or fewer), and separated from the band by more than one leading is margin matter: page number, journal mark, form footer, date stamp, "Notes" label. A bare integer in the margin is a page number regardless of repetition. Nothing in the margin band may become a heading unless it is the largest type on the page (a title). The same band is a free exclusion zone for the table finder and a free "start of body" for reading order.

**Failure group and reach.** Headers and footers: about 8 to 12 of the 28 (the lines we promoted to headings, the bare numbers where the page has no other such digits). The five titles that repeat the running head and the footnotes stay lost by decision.

**Cost.** 3 hours.

**One-hour test.** Run the body-band rule over the text layers of the 28 failing pages and list which of the 28 strings fall outside the band; then over the pages of the 732 passing checks and list any body line the rule would push into the margin (regression count).

**Strongest objection.** Pages without a body mass (title pages, forms, a page that is one table) have no band, so the rule must fall back to the current zones; a caption under a full-width figure can look like margin matter. Three of the 28 ("1", "2", "98") are checker artifacts and cannot be won while any "1" exists in the output.

---

## Idea 5. Order by sentence continuity; peel the page from the bottom

**Reversal and movement.** "Order the blocks, then join the text" becomes "find where the text continues, and let that constrain the order". "Read top-down" becomes "peel the bottom first": footnotes, captions and form fields are removed from the bottom before the body is ordered.

**Concept.** A sentence that has not finished is the strongest reading-order evidence on the page, stronger than any gap.

**Mechanism.** After blocks are built, mark each block's end as open (last line has no `. ! ? :` or closing quote and runs the full width of its column) and its start as open (begins lower-case, with a continuation word, or an unindented first line). In `segment/order.py`, when the block just placed ends open, the next block must be an open-start block of the same column width in the same column; interleaved captions, footnotes, tables and form boxes are placed after the sentence closes. Two small sub-rules from the same continuity test: (a) consecutive heading blocks, the first ending open and the gap at most 1.5 leading, join into one heading ("## 4 Determination of the electrical" + "## parameters", "###### Tell Gov. Bullock to" + "### Leave a Wild Legacy": 6 near-miss checks carry a stray "#" for this reason); (b) a body-size line the layout model promoted to a heading between an open end and an open start is demoted.

**Failure group and reach.** The 17 true order errors, the 52 mid-sentence breaks (the pack's count), the 6 heading-marker near misses: perhaps 20 to 35 checks.

**Cost.** 6 to 8 hours.

**One-hour test.** From the census, list the multi-column snippets that are in the layer but more than three edits from our output (39 snippets). For each page, count blocks in our order that end open and are followed by a block that does not start open, and whether an open-start block of the same width exists in the same column. The share where it exists bounds the gain.

**Strongest objection.** Two open blocks in one column (a list item, then a paragraph) can pair wrongly; lower-case starts occur legitimately ("pH", "et al.", "mRNA"); a sidebar set in the same width as the column passes the width test. Needs the width and column tests together, not either alone.

---

## Idea 6. Word boxes from ink, not from counting characters

**Reversal and movement.** "Divide the OCR line evenly into characters" becomes "let the ink say where the words are". Movement: the engine gives one box per line and the text; the picture still holds the gaps.

**Concept.** `_split_words` in `ocr/rapid.py` spreads characters evenly across the line box, so a scanned table row that the detector read as one line ("Fund Type 5 Year Diver-") has no gaps for the aligned-table finder to see, and 39 table checks fail with the cell inside a longer cell.

**Mechanism.** For each OCR line, take its crop from the rendered page, binarise, and compute the share of dark pixels per pixel column; blank runs wider than 1.5 x the median blank run are word gaps. If the number of ink runs equals the token count, each token takes its run's x-range; if not, assign tokens to runs by cumulative character width. Word boxes now carry real gaps, so `tables/aligned.py` finds channels between cells, and word-space decisions on OCR pages ("received.I hereby") improve too. Combine with idea 1: the same crops at native resolution.

**Failure group and reach.** OCR'd tables (the 21 checks on pages with no layer plus a share of the 39 merged cells), word spacing on old scans. Perhaps 15 to 30 checks.

**Cost.** 4 to 5 hours.

**One-hour test.** On `tables/11e12a3ddca3b1743f6ec1c22a52...pg8` (10 failing checks, a mutual-fund table read as merged columns), dump the OCR lines with ink-run boxes and check whether whitespace channels now appear at the column boundaries the reference expects (`table_tests.jsonl` gives the neighbours).

**Strongest objection.** A skewed scan makes one detector box span two rows; underlines and rules break the ink profile; a table with tight columns has gaps no wider than word spaces, so channels still fail to form.

---

## Idea 7. A row is a baseline: numbers define the rows, labels attach, columns come from the right

**Reversal and movement.** "Cluster lines into rows, then merge wrapped label lines" becomes "let the numbers define the rows; labels attach to them". "Columns from left edges" becomes "columns from the right edges of the numbers".

**Concept.** On `tables/904a1b4e...pg141` three separate labels were merged into one wrapped cell while the numeric rows beneath have empty label cells; on `9c38972...pg17` group cells hold several lines that the reference reads as rows; the pack lists "a label column offset from its numbers" and "two-line cells the reference splits into rows". In each case the numbers already say how many rows there are.

**Mechanism.** Inside a table region, cluster numeric tokens by baseline: that is the row count. Attach each label line to the numeric row whose baseline is nearest within 0.6 em; a label line with no numeric row of its own is a wrapped continuation and joins the previous label. Column boundaries for numeric columns come from the clustered right edges of right-aligned numbers (and decimal points), so a label that overhangs its numbers no longer shifts the column.

**Failure group and reach.** Part of the 79 relation-wrong and 39 merged-cell checks: perhaps 20 to 30.

**Cost.** 5 to 6 hours.

**One-hour test.** For the 64 relation-wrong pages, count baseline clusters of numeric tokens inside each table box we emitted and compare with the number of grid rows we wrote; pages where they differ are the candidates. Hand-check five against the reference relations.

**Strongest objection.** Text-only tables have no numeric anchor and fall back to the current rule; sometimes the reference wants the wrapped cell joined, so the "one numeric row per label line" evidence must be required, not assumed.

---

## Idea 8. Two readers of the same pixels: OCR arbitrates the hidden layer word by word

**Reversal and movement.** "The text layer decides whether OCR runs" becomes "OCR judges the text layer". Movement: page-level replacement was tried and set aside; word-level arbitration was not.

**Concept.** The hidden layer and RapidOCR err independently: the layer's errors here are e to c, dropped letters and glued words; the engine's are e to s, e to a, l for 1. Where two independent readers agree, the word is almost certainly right; where they disagree, the word list breaks the tie. Nothing is invented: every character comes from one of two readings of the same pixels.

**Mechanism.** On pages whose layer quality is `ocr` (D010), read the page with the engine (line crops at native resolution, idea 1). Align engine lines to layer lines by position, then align words within a line pair by Levenshtein alignment. Keep agreements. On a disagreement take the reading that is in the word list; if both or neither, take the layer's unless the two differ only by a known confusion pair and the engine's version is a list word. Record every substitution in the front matter.

**Failure group and reach.** The 54 multi-column and 17 tiny-text checks on hidden-layer pages where the layer itself is wrong. Realistic 15 to 30.

**Cost.** 6 to 8 hours.

**One-hour test.** On the 23 multi-column and 11 tiny-text failing hidden-layer pages, run the engine on line crops, align to the layer, and count failing snippets whose arbitrated text lands within the allowance. Also report the reverse: snippets the layer had right that the arbitration would break.

**Strongest objection.** When both readers are wrong differently, the arbitration picks one wrong reading with false confidence; the English word list is biased against names and non-English pages (Polish, Croatian, Indonesian are all in the set); and it adds an engine pass to every scanned page with a layer.

---

## Idea 9. Certainly-not-a-table first

**Reversal and movement.** "Find tables" becomes "find what is certainly not a table; what remains is the candidate set". Movement: prose is easy to recognise with high confidence; tables are not, so start from the easy side.

**Concept.** The aligned finder starts from rows with two segments and a gap, so a botanical key, an attendance list with tick marks, a form of "label: value" lines, or a census printout in fixed-width type never become candidates, however un-prose-like they are.

**Mechanism.** Score every line for prose: share of tokens in the word list, sentence punctuation, width close to the column width, six or more words, a justified right edge. Lines that are certainly prose (and lines in the margin band of idea 4) are removed. What remains, grouped by vertical contiguity, are candidates even with no whitespace channel; those get looser column rules: printed separators (`|`, `:`, tab-like runs of spaces in monospace fonts), tick and cross marks as cells (D013), and the right edges of numbers (idea 7). At least two aligned tokens per line, over at least three lines, to keep reference lists and addresses out.

**Failure group and reach.** The 9 checks with text present and no table, the ~10 present outside a table, and part of the relation errors on pages where the table was found too small. Perhaps 15 to 25 checks.

**Cost.** 5 to 6 hours.

**One-hour test.** For the 13 no-table pages with text present in the layer (from the census) compute the prose score per line and check whether the failing cells' lines survive as non-prose and form contiguous runs. If eight or more of the 13 do, build.

**Strongest objection.** The 39 picture-only table checks have no lines at all and are untouched; a poem, a programme listing or a bibliography is non-prose without being a table, so the "two aligned tokens per line" guard carries the weight and will need tuning against the owner's library.

---

## Idea 10. Write what the reader sees for trivial inline maths

**Reversal and movement.** "The font says maths, so write LaTeX" becomes "the reader sees k = 2, so write k = 2". Movement: check what the maths checks actually need before deciding.

**Concept.** Eleven multi-column checks fail because we write `$k=2$` where the reference has `k = 2`. None of the 2,927 ArXiv maths checks is a run of eight characters or fewer without a backslash, so writing such runs plain costs nothing there.

**Mechanism.** In `math/extract.py`'s inline path: an inline run of at most three tokens containing only letters, digits and `= < > + - . ,`, with no scripts, fractions or maths-only glyphs, is written as plain text with single spaces round the relation sign. Everything else stays LaTeX.

**Failure group and reach.** About 11 multi-column checks.

**Cost.** 1 hour.

**One-hour test.** Rewrite `$...$` runs matching that shape in the run-48 outputs with a regex and rescore multi-column and ArXiv maths; expect about 11 up, 0 down.

**Strongest objection.** A reader of the markdown loses the maths markup on those variables, and the reference's spacing is one transcriber's habit: `l/R = 0.05, 0.1` may be written three ways.

---

## A wild one, for the owner rather than the engineer

"Accept lines, not pages." The OCR gate rejects a page by its mean confidence (D009), so a typed form with handwritten entries is empty. Reversed: keep lines with their own confidence at 0.9 or more whose tokens are word-like, whatever the page mean. It needs the owner's sign-off because confident noise exists (a scrawl can read "the" at 0.95) and D008 was written to keep such text out. One-hour test: OCR the 76 empty pages, count lines at 0.9 or more that are word-like, and compare them with the reference snippets. Not counted among the ten.

---

## Best bet

**Idea 1, tile the scan at native resolution**, with idea 2 as the sure thing to do alongside it. Reason: idea 1 rests on a hard fact read from the code and the PDFs (a 2,000 px cap against 3,300 to 6,400 px scans), it touches the two sections that have not moved in five days (old scans 20.5, old-scan maths 4.1) and the pages behind 414 of their failing checks, it costs an afternoon, and its one-hour test on five pages settles it either way. The fact that flips it: no more reference snippets found at native resolution than at 2,000 px on `old_scans/48, 51, 57, 70` and `long_tiny_text/17_pg4`. If it flips, idea 2 (about 20 checks by a text filter, 35 to 50 with the joins) takes its place, and idea 3's audit report is the instrument to keep regardless of the score.

## Claims in the evidence pack I doubt

1. "Our own OCR read of those pages is not better than the hidden layer (tried: 13 of 66 strings found against the layer's 9)." As written, 13 is more than 9. Either way the trial was a page-level replacement at up to a third of the scan's resolution; word-level arbitration at native resolution (ideas 1 and 8) is a different experiment.
2. "54 snippets are not in the hidden OCR layer at all." 53 of the failing tiny-text snippets are on 16 pages with no text layer whatever (the 10a-16c dictionary and encyclopaedia scans and the five 17_* pages): they are our own RapidOCR reads. Five of those pages are 600-dpi scans we read at half resolution. The failure owner is our OCR path, not an old layer.
3. "Tables: 152 are a cell not found or no table at all ... 70 are text present but not structured as a table." With the checker's own parser, only 53 checks have no table in our output (9 with the text present), while 39 have the cell inside a table we produced but merged with a neighbour and 79 have the cell matched with a wrong relation. The bigger problem is cell boundaries inside tables we already find.
4. "Multi-column: 148 are near misses in the text." Within three edits of the allowance there are 79; 133 are further away, mostly sentences broken or lost. The distinction matters because the 32 pure-space checks are fixable by a text rule and the 133 are not.
5. "Headers and footers: titles that repeat the running head, footnotes, page numbers..." Eight of the 28 are lines we ourselves promoted to headings, including a journal mark and a form footer that are not titles; three are checker artifacts on bare digits.
6. "RapidOCR's English model cannot read old typefaces" was concluded from reads at up to a third of the scans' resolution. Untested at native.
