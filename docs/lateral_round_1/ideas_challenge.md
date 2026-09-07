# Challenge round: every assumption the pipeline makes, and what happens if it is wrong

_Thinker: CHALLENGE (de Bono). Read-only. 7 September 2026, on run 48's outputs and `bench/runs/truedoc47-20260907-090140/failed_tests.jsonl` (1,896 failing checks)._

How to read the tags: **[verified]** I measured it here with a short script on the failed-tests file, our outputs, the PDFs or the checker's own code; **[recalled]** from memory, not checked; **[assumed]** a choice made to proceed. Hours are estimates [assumed].

Two things I learned about the yardstick that shape everything below [verified from `olmocr/bench/tests.py`]:

- A *presence* check passes when the snippet's best partial match is within `max_diffs` edits; an *order* check is stricter: each snippet must be found as a contiguous near-match with at most `max_diffs` (0 to 2) edits, and only then is position compared. So a multi-column "reading order" failure is almost always a "these 60 characters are not all right" failure.
- The normaliser collapses whitespace, strips `**`, `__`, `*`, `_`, `<b>`, `<i>`, maps curly quotes, dashes and the minus sign, and applies NFC. `$` and `#` survive. The benchmark outputs are rendered **without front matter** (`truedoc/bench/olmocr.py`, `frontmatter=False`), so nothing in the front matter can help or hurt a check.

---

## 1. The assumption ledger (harvested, not judged)

For each: what the code assumes, then "why must it be so? what if it were not?" in one line.

**Stage 1, reading the PDF**

1. The text layer is the truth for characters, and it is *complete* (D004; `extract/textlayer.py`). Why must it be? Because a producer wrote it. What if not: a glyph with no Unicode mapping arrives as a blank or U+FFFD and the word has a hole in it ("classi cation").
2. A hidden OCR layer's characters are right; only its layout is rebuilt (D010). What if not: 54 tiny-text snippets are simply not in the layer; the layer is a witness, not the truth.
3. A word is a run of glyphs whose gap is smaller than the line's letter gap (`_chars_to_words`). What if not: letter-spaced headings, tiny type and justified narrow columns all break it, and every repair is another threshold.
4. A hyphen at a line end is soft unless a function word follows (`render/okf.py` `join_lines`). What if not: "racist-free" becomes "racistfree" and "trans-" + "forming" stays "trans- forming".
5. A column gutter is a page-wide channel crossed by at most 3% of lines, and there are at most three (`_column_gutters`). What if not: a page whose columns start under a full-width abstract needed a banded rule (4 Sept) and will need another for every new shape.
6. Hidden text is decided per character from colour, paint order and clipping, then checked against a render (D011). Fine as far as it goes.
7. A page is upright, or one quarter-turn from upright (`_turn_page`). What if not: a page with a sideways table *and* upright text keeps only one of them.
8. The body size is the modal glyph size, and every threshold on the page scales from it (`_body_font_size`). What if not: a dictionary page with large headwords and tiny entries scales everything wrongly.

**OCR**

9. A page either has a usable text layer or is OCR'd, never both (`process_page`). What if not: a sideways picture table under a typed title is never read (known limit).
10. OCR is accepted or rejected *whole*, on the mean line confidence and the share of word-like tokens (D009). What if not: a handwritten letter on a printed letterhead is thrown away with its letterhead.
11. One recogniser, one reading, of the page image as the scanner made it, at most 2,000 px on the long side (`ocr_page_turn`, `_MAX_SIDE`). What if not: two readers that agree are better evidence than one reader's confidence; tiny type gets 11 to 22 px line boxes at that scale [verified, see idea 1].
12. Handwriting is unreadable, so the page is empty (D008). What if not: the printed parts are readable.

**Blocks and kinds**

13. Blocks are built bottom-up from lines (gap, overlap, size, typeface) before any model sees the page (`segment/blocks.py`); the model then relabels and splits. What if not: the model's boxes could define blocks first and lines be assigned to them.
14. Running heads and feet live in the top and bottom 9% strips, are short, and on a single page cannot be confirmed by repetition (`classify/blocks.py`, `_margin_cleanup`). What if not: a fifth of the digital pages carry the producer's own marks saying exactly what is furniture [verified, idea 8].
15. A confident TEXT region from the layout model vetoes an aligned table (`layout/fuse.py`, `vetoed`). What if not: a six-row label/value list is a table to the benchmark and "text" to the model [verified, idea 6].
16. The layout model decides kinds and never adds characters (except a table box holding a picture). What if not: figure boxes full of vector-drawn text hold readable characters [verified, idea 7].

**Tables**

17. A table is a grid: columns are whitespace channels (or voted gaps), rows are baselines (`tables/aligned.py`). What if not: columns can be *repeated left edges* with no clear channel, and rows can be *stacks* of baselines.
18. An unruled table needs three rows, 60% of them multi-cell (`_find_runs`). What if not: two-row and six-row label/value forms are tables.
19. Rulings are drawn lines; characters are never rulings. What if not: a mainframe printout draws its rules with `|`, `:`, `+`, `=` and `-` [verified, idea 4].
20. Lines in the top or bottom 9% strip never belong to a table (`find_aligned_tables`). What if not: a table running to the page edge loses its first or last rows — but only 5 failing cells sit in those strips [verified], so this one is not load-bearing.
21. A cell is the text on one baseline in one column; a second line joins only when it reads as a continuation (`_merge_wrapped_rows`). What if not: regression tables stack a value over its "(4.07)" and the reference reads them as one cell [verified, idea 5].
22. Pictures and vector drawings hold nothing to read; picture OCR (off by default) expects prose (12+ words, 60% word-like). What if not: tables are numbers and codes, and vector text renders crisply.

**Order and rendering**

23. Reading order is decided once, by geometric cuts, and blocks are emitted in that order; a sentence lives in one block. What if not: see section 5 — this turns out *not* to be load-bearing (17 true order errors in 233).
24. Inline maths is always written `$…$`. What if not: 11 prose checks want `k = 2` plain (from the pack).
25. Formulas are rebuilt only from glyphs; scans have none. Holds without a model.
26. A page yields one body, whole or empty; there is no honest "partial". What if not: a partial page with a declared gap invents nothing.

**Benchmark-facing**

27. The reference is right. What if not: a share of the "near misses" are the reference's own errors and cannot be won [verified examples, section 5].
28. Zones are page fractions whatever the page size or orientation. Minor.

---

## 2. The ten that carry the most weight

| # | Assumption | Movement (what if it were not so) | Concrete alternative | Idea |
|---|---|---|---|---|
| 2, 11 | The hidden OCR layer is the truth; one reader, one reading | The layer is a witness; cross-examine it line by line with a second witness that sees the ink at full resolution | Line-level arbitration between the layer and a high-resolution re-read | 1 |
| 1 | The text layer is complete | The producer forgot some glyphs; MuPDF can still hand over their codes | Recover unmapped glyphs by CID and font encoding (TeX ligatures) | 2 |
| 10, 12, 26 | OCR is all-or-nothing; a rejected page is empty | Rejection reasons are line-local; printed lines on a handwritten page are real | Per-line acceptance with a declared gap | 3 |
| 19 | Characters are content, never rulings | In a monospaced printout the characters *are* the rules | Character-grid tables | 4 |
| 21 | A cell is one baseline | A cell is a stack (value over statistic) | Stacked-cell merge | 5 |
| 15, 17, 18 | Columns are emptiness; the model may veto a table | Columns are repeated left edges and drawn boxes; geometry that strong cannot be vetoed | Alignment columns, box cells, veto guard | 6 |
| 16, 22 | Pictures hold nothing | Vector text is crisp at any resolution | Render-and-read dense path regions | 7 |
| 14 | A single page cannot say what its furniture is | The producer already said it (`/Artifact /Pagination`) | Producer marks as an exact header/footer source | 8 |
| 11 | Confidence from one network is the evidence | Agreement between two independent readers is stronger evidence; and the image can be handed over in better shape | Two bundled recognisers voting, on a binarised, deskewed page | 9 |
| 23 | Reading order is where multi-column loses | It is not: 17 of 233 | Stop investing there; the losses are character-level | section 5 |

---

## 3. Ideas

### Idea 1. Two witnesses, not one truth (hidden OCR layers)

**Assumption challenged and movement.** D010 trusts the hidden layer's characters and the pack judged our own OCR at page level ("13 of 66 against the layer's 9") and set it aside. Movement: the layer and our recogniser are two witnesses; neither is the truth; the question is which to believe *per line*, and whether the second witness was ever given a fair look. At the engine's own page scale (`_MAX_SIDE` 2,000 px, at most 300 dpi) the failing tiny-text pages get line boxes of 11 to 22 px, and the failing multi-column scans a median of 33 px with one page at 12 px [verified from page sizes and span heights]; the recogniser was trained on 48-px crops [recalled].

**Concept.** Line-level arbitration between two readings, with nothing emitted that neither reader saw.

**Mechanism.**
1. On a page of kind `ocr` (hidden layer), keep the layer's lines as the skeleton: boxes, order, columns (all the 4 to 6 Sept work stands).
2. For each line, render *only that line's box* (plus a point of margin) from the PDF at whatever scale makes the box at least 48 px tall (600 dpi for 5-pt type), and run recognition on the crop — the engine already exposes crop recognition; `_sideways_turn` calls `get_crop_img_list` and `text_cls` the same way, so `text_rec` on the crops is the missing third call [recalled: the RapidOCR object has a `text_rec` member].
3. Align the two strings word by word (difflib). Agreement: keep. Disagreement: prefer the reading that is a dictionary word when the other is not; else prefer the recogniser only when its line confidence is at least 0.9; else keep the layer (today's behaviour). Never emit a word neither witness read.
4. Write every swap to the front matter (`truedoc.ocr_arbitration`: line, layer's word, chosen word, reason), so nothing changes silently.

**Failure group and reach.** Long tiny text: 54 snippets absent from the layer and 32 near misses (86 checks). Multi-column scanned pages: 77 missing snippets, 19 of them within 4 edits [verified]. A realistic 15 to 40 checks; a section-point on tiny text is 4.4 checks.

**Cost.** 6 to 10 hours.

**One-hour falsification.** Take the 54 long-tiny-text `present` checks whose text is not in the layer. For each, find the layer line(s) with the best partial ratio to the snippet (that locates the region even when the words are wrong), crop those line boxes at 600 dpi, run crop recognition, substitute the crop readings into our output for those lines, and re-run `TextPresenceTest`. Bar: 12 or more of 54 turn green. Five or fewer: the pack's verdict stands and the resolution story is dead.

**Strongest objection.** The pack's page-level test found our engine *worse* than the layer, and the arbitration rule decides names and numbers (which no dictionary knows) by confidence alone; one wrong choice in a 60-character sentence fails the check. If the layer is wrong because the print itself is bad, no witness helps.

### Idea 2. The glyph the layer forgot

**Assumption challenged and movement.** "Characters come from the PDF's own text layer" assumes the layer is complete. It is not: on a TeX-set page the `fi` ligature has no Unicode mapping and arrives as a blank, so our output reads "classi cation" and "o -line" [verified on multi_column 09f90a8f…]. Asking MuPDF for the raw code (`TEXT_CID_FOR_UNKNOWN_UNICODE`, already used in `_attach_ink_boxes` but only on extension-font pages) returns `classi\x0ccation`: code 0x0C, which is `fi` in TeX's OT1 layout (0x0B ff, 0x0C fi, 0x0D fl, 0x0E ffi, 0x0F ffl); the T1 layout puts the same five at 0x1B to 0x1F [recalled; check against the font's `/Differences`].

**Concept.** The layer lies by omission; the ink and the code are still there.

**Mechanism.** Run the CID pass on every page. A control-range code in a font whose name or encoding says TeX (cm*, lm*, SFRM, T1/OT1 `/Differences` naming `fi`) maps by the table above. Any other unmapped code that has ink (the text trace lists it) is either named from the font's `/Differences` array or, failing that, its box is rendered at 300 dpi and given to the recogniser, which reads a crisp single glyph well. Count the recoveries in the front matter.

**Failure group and reach.** Multi-column: **13 order checks** fail only because of ligature gaps [verified: blanking ff/fi/fl/ffi/ffl in the reference snippets brings 13 failing checks within their edit allowance against our output]. Pages carrying such glyphs: 9 multi-column, 48 arxiv maths (mostly inside `\text{}`), 6 headers/footers, 1 tables; 1,639 glyphs in all [verified].

**Cost.** 2 hours.

**One-hour falsification.** Done (20 minutes): the 13 checks above. Confirm on the nine multi-column pages that the CID pass returns 0x0B to 0x0F where our output has a blank inside a word.

**Strongest objection.** Small: 13 checks is about +0.2 overall. The mapping must be gated by encoding; code 0x0C in a non-TeX font is something else entirely.

### Idea 3. A page may be read in part

**Assumption challenged and movement.** D009 accepts or rejects a page's OCR whole; D008 makes a rejected page empty. The reasons for rejection are line-local: handwriting reads as noise, but the printed letterhead above it does not. Of six empty old-scan pages I looked at, two carry a printed letterhead ("THE BECKNER PRINTING COMPANY, 136, 138, 140 West Short Street, LEXINGTON, KY.", with a printed date line) [verified by rendering]. Movement: "nothing invented" forbids guessed text; it does not forbid an honest partial with a declared gap.

**Concept.** Per-line acceptance, with the unread remainder said out loud.

**Mechanism.** After `ocr_page_turn`, score each line on its own: keep it when its confidence is at least 0.85, its tokens are language-like (`_looks_like_language` at least 0.7) and it has two or more words (or is a date or number). Accept the page when at least two such lines remain. Emit them in reading order. Put a visible note at the head of the body ("Only the printed parts of this page could be read; N lines were left out as handwriting or unreadable.") and `truedoc.partial_ocr: {lines_kept, lines_unread}` in the front matter. The note is written only when kept lines exist, so it can never pass a check on its own. The whole-page gate stays for pages that pass it today.

**Failure group and reach.** Baseline: 71 checks (61 old scans, 10 old-scan maths) fail only because the file is empty [verified]. If a third of those pages have printed lines, 20 to 30 baseline checks, plus a handful of presence checks on letterhead and date lines; and for real documents, the sender, date and address of every handwritten letter.

**Cost.** 3 hours.

**One-hour falsification.** Run `ocr_page_turn` on the 71 empty pages (an OCR census, not a conversion); count pages with two or more lines at confidence 0.85 and language-likeness 0.7; view the ten best crops to confirm they are print, not confident nonsense. Bar: 15 pages or more.

**Strongest objection.** It reopens a decision the owner made (D008): a letter reduced to its letterhead could mislead a reader into thinking the page was read, and the checks it wins (baseline) are the least meaningful in the benchmark. The note and the front-matter count are the answer, but the owner must agree.

### Idea 4. Characters as rulings

**Assumption challenged and movement.** Rulings are drawn lines (`tables/ruled.py`); characters are content. A Census 2000 printout in Courier draws its box with `+====+`, its columns with `|` and `:`, its heading bands with `---` [verified from the text layer of tables/ff19f6fe…]. Our output turns it into a six-column table of `\|` and `:` fragments, and the five checks on it fail. Movement: in a monospaced layer the rulings *are* characters, sitting on a character grid.

**Concept.** A character-grid table builder.

**Mechanism.** Detect a monospaced layer (equal glyph advances; Courier-like font name or the mono flag). Map every character to (row, column) on the grid. A grid column where `|` or `:` occupies at least 60% of the rows of the region is a vertical rule; a grid row made of `-`, `=`, `+` is a horizontal rule; drop those characters from the content. Cells are the rectangles between rules; a cell's text is its characters, lines joined with a space (the census page has a six-line stacked heading, so the output is HTML with `th`). This is exactly what `ruled.py` does with drawn lines, fed synthetic rules.

**Failure group and reach.** Tables: 5 checks on the census page [verified]; other printouts and colon-separated forms in the wild (the handball referee report in the same section already passes).

**Cost.** 3 hours.

**One-hour falsification.** Build the grid from the page's `rawdict` character positions, cut at the `|`/`:` columns and the `---` rows, render as HTML, run the five `TableTest`s.

**Strongest objection.** One page in the benchmark. Courier prose with stray colons needs a guard (a rule column must be shared by three or more rows).

### Idea 5. A cell is a stack, not a baseline

**Assumption challenged and movement.** `_cluster_rows` makes a row of every baseline and `_merge_wrapped_rows` folds a second line only when it reads as a continuation. Statistics tables stack a coefficient over its standard error or t-statistic; the reference reads "0.150 (4.07)" as one cell with "Germany" as its heading, and "-0.0248 (0.0796)" likewise, where our HTML has "(4.07)" as its own row [verified on tables/dad8f9b8… and 981f5f24…].

**Concept.** Merge parenthesised-number rows into the value row above.

**Mechanism.** After the grid is built: a body row whose label cell is empty and whose filled cells are *all* parenthesised numbers (with optional significance stars) merges into the row above, cell by cell with a space, provided the row above holds numbers in the same columns; the merged row's box spans both lines so up/down relations stay right.

**Failure group and reach.** Tables relation failures: 8 checks on 5 pages name such a stacked cell [verified: dad8f9b8 3, 981f5f24 2, 2d54e996, 0091c5b2, a38ac67e]. Regression tables are common in real documents.

**Cost.** 2 hours.

**One-hour falsification.** Apply the merge to the five pages' grids in a script (no conversion) and run their `TableTest`s. Bar: 6 of 8.

**Strongest objection.** The opposite convention exists in the same benchmark ("two-line cells the reference splits into rows"), so the rule must stay narrow — parenthesised numeric rows only — and any check expecting "(4.07)" as its own cell is lost.

### Idea 6. Columns by alignment and by boxes; and geometry this strong cannot be vetoed

**Assumption challenged and movement.** Three assumptions stack up: a table needs three rows with whitespace channels (`_find_runs`, `_channels`); a confident TEXT region from the layout model vetoes an aligned table (`fuse.py`); and a ruled box's content is read by baselines across boxes. The Polish "form" is a six-row, two-column table — labels at x = 83.6, values ("do 15 pkt.") at x = 226.7, rows 12.4 pt apart — and the reference asks for exactly those left/up/down relations; our output reads the label column then the value column as prose [verified from word positions]. The boxed legal form comes out as "Claimant (including The federal Republic of ref.) Defendant Nigeria (including…": neighbouring boxes interleaved line by line [verified].

**Concept.** Repeated left edges are columns; box rectangles are cells; a channel that runs through every row cannot be vetoed by a model that says "text".

**Mechanism.** (a) Word x-starts shared by three or more rows (within 0.3 em) with a channel of at least 2 em to their left define a column, even for two- to six-row regions of short phrases. (b) The layout veto applies only when the geometry is weak: never when a channel 5 em or wider runs through every row. (c) For ruled boxes, the cell is the rectangle and its text is every line inside it, joined; rows across boxes are never formed by baseline.

**Failure group and reach.** Tables "present but unstructured": the pack counts 70; my own count of "cell present in our output but relation or structure wrong" is 134 [verified]. The two verified pages carry 7 checks; a realistic 10 to 20.

**Cost.** 4 hours.

**One-hour falsification.** On f30f3060… and f2ad0cd0…, call `find_aligned_tables` and `find_ruled_tables` alone on the page's lines, no layout model, and print what they return. If the aligned finder already returns the six-by-two table, the veto is the culprit and a one-line guard wins 4 checks.

**Strongest objection.** Two-column lists are also definition lists and dialogue; every widening of the table finder has shredded prose somewhere (run 10). And the layout veto exists because line-numbered prose was being taken for a table.

### Idea 7. Vector text is crisp text

**Assumption challenged and movement.** The pack files 46 checks under "text that exists only as a picture" and notes "vector-outline text: nothing to read". Two of those pages hold no images at all: a trial-results table drawn as 513 filled paths, and a power-cord specification sheet with its parts table drawn as 5,875 paths ("BS1363 P 2G 1.0mm² BLACK 1PC", "ZIP BAG:250X110X0.06mm") [verified: `get_drawings` counts, rendered and viewed]. Movement: text drawn as paths renders perfectly at any resolution; the recogniser's trouble with scans does not apply.

**Concept.** Render and read dense path regions, gated on confidence, not on prose-likeness.

**Mechanism.** A region dense with small filled paths (200 or more, median height under 6 pt), or a layout figure/table box with fewer than three text lines inside, is rendered at 300 dpi and read with `ocr_region`; accept on confidence alone (0.85 or better) — tables are numbers and codes, so the word-likeness gate that `--ocr-pictures` applied is wrong for them; build with `table_from_lines(trusted=True)`; provenance `ocr-vector`, listed in the front matter (it is a reading of the page's own ink, but whether it wears the D015 tag is the owner's call).

**Failure group and reach.** Tables: 10 checks on the two vector pages [verified]; the image-based pictures (the rest of the 46) may partly follow from the same gate change, at scan-quality accuracy.

**Cost.** 3 hours.

**One-hour falsification.** Render the two pages' table regions at 300 dpi, run `ocr_region` and `table_from_lines`, run the 10 `TableTest`s. Bar: 6 of 10.

**Strongest objection.** `--ocr-pictures` gained 4 checks in total when tried — though with a prose gate that tables cannot pass. The trial-results page mixes a forest plot with its columns and may defeat the column finder even when every word is read.

### Idea 8. The producer already said what is furniture

**Assumption challenged and movement.** "Running heads cannot be confirmed by repetition when there is one page." But a fifth of the digital pages carry the producer's own marks: `/Artifact` marked content, 38 headers/footers pages, 39 tables pages and 25 multi-column pages with `/Pagination` [verified by scanning content streams]. pdfplumber (installed) exposes the tag per character, and the artifact text on sample pages is exactly the running head: "Scripta Uniandrade, v. 19, n. 1 (2021) …", "29-01-2020 Dr. Manas Khatua 6" [verified]. No benchmark PDF has a structure tree, so there is no `/Table` structure to harvest.

**Concept.** The page declares its own furniture; use the declaration before any zone rule.

**Mechanism.** Read the marked-content tags (pdfplumber chars carry `tag`), match artifact characters to our `Char`s by position, and make any block whose characters are 80% artifact-marked a HEADER or FOOTER with provenance `producer-artifact` — before the zone and size rules, so a title that repeats the running head's words stays a title when it is not marked.

**Failure group and reach.** Headers/footers: 3 checks on 2 pages are exactly the artifact text [verified: 9f896cbb… "Part 2—Offences relating to food" and "Division 1—…", 39466c5e… "SKRIPSI"]. On the failing tables and multi-column pages, artifact text is already out of our body on 30 of 32 pages [verified], so little more there. Small on this benchmark; exact on real documents.

**Cost.** 2 hours.

**One-hour falsification.** Done (20 minutes): pdfplumber's artifact text matches the two pages' absent snippets at 100.

**Strongest objection.** A second PDF parser in the conversion path, with its own coordinate frame and character order; producers mislabel (some mark whole text frames as artifacts); three checks.

### Idea 9. Agreement as evidence: two recognisers already on disk

**Assumption challenged and movement.** A classical read is accepted by one network's confidence (0.75, or 0.80 for the rescues), and "RapidOCR's English model cannot read old typefaces". Movement: agreement between two *independent* readers is stronger evidence than one reader's confidence — and TrueDoc already ships two recognisers: the English PP-OCRv3 model it downloads and the Chinese+English PP-OCRv4 model bundled with the package (`ocr/rapid.py` notes it) — different networks, different training. And the image can be handed over in better shape than the scanner left it.

**Concept.** Two readings of the same boxes; keep what they agree on; clean the image first.

**Mechanism.** For pages that fail the gate or are read with low confidence: binarise (Sauvola or OpenCV adaptive threshold; OpenCV ships with RapidOCR [recalled]), deskew by projection profile, upscale small type 2×; detect boxes once; recognise each crop with both models; accept a line when the two readings agree within one edit per ten characters, whatever the confidence; where they disagree, keep the reading with confidence 0.85 or better, else drop the line (honest gap, as in idea 3). Front matter records the agreement rate per page.

**Failure group and reach.** Old scans: 251 presence and 166 order checks on pages we do read but read badly; old-scan maths text. Unknown yield: 20 to 40 checks if agreement filters the wrong characters, near zero if both models share the errors.

**Cost.** 4 hours; no install.

**One-hour falsification.** Twenty old-scan pages with failing presence checks; run both recognisers on the same boxes, with and without binarisation; count snippets found by either; on lines where the two agree, measure whether the reference snippet is matched more often than on lines where they disagree. If agreement does not separate right from wrong, stop.

**Strongest objection.** Both models come from the same PaddleOCR lineage and largely the same data, so their errors correlate; old typefaces defeat both; agreement can be shared error.

### Smaller exact things noticed on the way (not full ideas)

- **Hyphen repair by vocabulary, not by function words.** "racist-free" → "racistfree" and "trans-" + "forming" left as "trans- forming" are the same rule failing both ways [verified in aligned diffs]. Ask the word list: joined form in the vocabulary, join; else both halves are words, keep the hyphen; else join. One hour; a few multi-column checks.
- **Heading fragments and drop caps** on digital pages: "Loi NOTRe" → "OI NOTR # et", "1995 Instructions for Form 1116" → " Instructions for Form 1116 ###", "The Best of the Best Foods" → "Feature ## the Best Foods" [verified]. The renderer inserts `#` mid-sentence when a heading block is split; a heading whose neighbour on the same baseline is body text should not be one.
- **Inline maths written plain** when the run has no LaTeX command (`$k=2$` → `k = 2`, spacing from the glyph gaps): 11 multi-column checks per the pack, but every arxiv inline formula check would then lose its `$` delimiters, so it needs a per-page rule (maths font share) and a check on the maths sample first.
- The 9% table-exclusion strips cost 5 failing cells [verified]; not worth a rule.

---

## 4. Single best bet

**Idea 3, per-line acceptance**, with idea 2 as the surest two hours on the list.

Why: it attacks the most load-bearing assumption in the whole design (a page is read whole or not at all), the pool is the largest certain one (71 checks that fail for no reason but an empty file, plus real content — sender, date, address — on every handwritten letter with a printed head), it invents nothing, the falsification is one OCR census over 71 pages, and it costs three hours. The fact that would flip it: fewer than 15 of the 71 empty pages carrying two or more confident printed lines, or the owner holding to "empty rather than partial" after seeing the note-and-count design. Idea 1 is the bigger idea but the uncertain one; idea 2 is certain (13 checks) but small.

---

## 5. Claims in the evidence pack I doubt

1. **"About 52 are sentences broken at a block boundary (footnotes, captions and forms interleaved)."** Interposition is not the mechanism. Removing any single paragraph from our output repairs 1 of the 233 multi-column order checks; both halves of a missing snippet are present anywhere in the output for only 44 of the 272 missing snippets, so at most 44 could be breaks of any kind [verified]. The misses are character-level: ligature gaps (13 checks), hyphen repair, drop caps and heading fragments, symbol-font glyphs ("P50.005" for "†P=0.005"), and the reference's own errors.
2. **"148 are near misses … small-caps names (now fixed), glued words."** A share cannot be won because the reference is wrong: of 16 digital-page diffs I aligned, about 6 look like reference errors ("Yatogami" for Yadvinder; "Heinsch, F., Vernaux" for Heinesch, B., Yernaux; "U.S.source"; a dropped "1993,"; "la contrainte" for "la solidarité"; "line 2" for "line 37a") [verified diffs; which side is wrong is my reading of the text, not checked against the page images]. The winnable pool is perhaps 60% of 148.
3. **"Our own OCR read of those pages is not better than the layer (13 of 66 against 9)."** Measured at page level, at the engine's scale, where the failing tiny-text pages get 11 to 22 px line boxes [verified]. A line-level union of the two readers at full resolution has not been measured; idea 1's test is that measurement. Not refuted; not proven either.
4. **"46 are text that exists only as a picture."** At least 10 of those checks, on two pages, are vector-drawn text with no image on the page [verified], which is a different and easier problem.
5. **Reading order as a target.** Only 17 checks are true order errors [verified: both snippets found, wrong order], so "multi-column, all reading-order checks" is the section's name, not its diagnosis.
6. **A benchmark error to add to the noted ones:** the multi-column check on 02e310…/"Furthermore, above 70% of the activity takes place in the afternoon…" has identical `before` and `after` text, so it can only pass if the sentence appears twice.
7. Minor: the file holds 27 absent + 3 baseline headers/footers failures (pack: 28) and 76 baseline failures (pack: 74).
