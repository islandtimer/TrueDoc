# Concept fan: ten ways round TrueDoc's remaining failures (7 September 2026)

Technique: concept extraction and the concept fan. For each failure group: the purpose (what we are really trying to do), the concept behind today's approach, then a fan of other concepts that would serve the same purpose, each with two or three mechanisms. Harvested first, judged after. Read-only: no conversions, no OCR runs, no code changes.

What I read: the evidence pack, `docs/ARCHITECTURE.md`, `docs/STATUS.md`, `docs/DECISIONS.md`; the checker (`olmocr/bench/tests.py`); `ocr/rapid.py`, `tables/aligned.py`, `render/okf.py`, `segment/order.py`, `pipeline._ocr_text_pictures`; run 48's 1,896 failing checks aligned against our outputs; the benchmark PDFs' embedded scan sizes. The census script is saved beside this file (`concept_fan_census.py`); it is the harness for the one-hour tests of ideas 3 and 4.

## Seven facts found on the way (all [verified] here unless tagged)

1. **A baseline check fails only when the output has no alphanumeric character at all.** The 71 empty pages are 71 failing baseline checks (61 old scans, 10 old-scan maths). One confident printed line per page would pass them.
2. **OCR pages are rendered at most 2,000 px on the long side** (`rapid.py`, `_MAX_SIDE`), about 182 dpi for a letter page [derived: 2000 / 792 pt x 72]. Of the 97 failing old-scan pages, 92 carry a scan larger than that (median long side 3,196 px, max 6,404); all 11 image-only failing table pages do too (median 2,144, max 7,020); old-scan maths 12 of 21 (median 3,583). The detector never shrinks the image further (`limit_type: min`, 736 only enlarges small images), so the cap is the resolution the recogniser sees. Tiny-text scans are the exception: only 5 of 16 image-only pages exceed 2,000 px.
3. **Picture OCR builds paragraphs, never a table.** `_ocr_text_pictures` calls `build_blocks` and runs after the table stage, so the 46 "table is a picture" checks were never reachable by the `--ocr-pictures` experiment.
4. **The checker reads HTML tables with `th`, `colspan` and `rowspan`**; every `th` above a column counts as that column's heading, so a stacked heading can be one joined cell or a `colspan` cell above the column's own heading. Our renderer already emits spans (`_render_html_table`) but marks `th` only on header rows.
5. **Tiny-text near misses are mostly punctuation, not letters.** Of the 90 failing checks, 38 are near misses (3 edits or fewer), 38 partial, 14 missing. Among the token errors in the near misses: 15 a space lost after `, ; :` ("closer;for", "Jason,slain"), 16 a stray or lost quote mark ("'The", `"' to`), 9 non-words for words ("socicties", "dclle", "Sfate"), 6 words for words ("bride" for "bridge"). Multi-column: 71 punctuation-only, 40 split words ("at a" as "ata"), 33 non-words ("tor" for "for"), 31 words-for-words, plus glyphs that lie in the text layer ("305e314" for "305-314"; "P50.0003$" for "§P=0.0003").
6. **On the 36 old-scan pages we do read, the type is read, with one- or two-character slips**: snippets found exactly 26 (the order check fails on the partner snippet), near 39, partial 63, weak 24, missing 31; typical slips "beanty", "meetiugs", "dopation", "19l4", "woman,tempted". The 61 empty pages carry 290 of the section's 417 failing present/order checks.
7. **Among the 226 failing table checks: `top_heading` 47, `up` 43, `right` 39, `down` 38, `left` 32, `left_heading` 27.** The one true fixed-width printout (the census page) is Courier 8 pt with every glyph exactly 4.8 pt wide, 9,536 characters: a perfect character grid. OCR word boxes are made by dividing each recognised line evenly (`_split_words`), so a heading line read as one box ("Beta Bull Bear Stocks") is split by guesswork.

## The fans, group by group

### Tables (227 failing). Purpose: give each printed value the labels a reader would use to find it, and its neighbours.
Current concept: **find where the cells align** (whitespace channels through runs of aligned lines; drawn rules; the layout model's boxes).
Fan:
- *Find where the author put the rules* -> drawn rules (have); **typed rules**: `|`, `:`, `+----` in a Courier printout are rulings made of characters; the monospace grid itself is a ruling.
- *Find the columns from the numbers* -> numeric tokens vote by right edge or decimal point; heading words are handed down to the columns beneath them.
- *Find the columns from the header row alone* -> header word extents define columns; data assigned by overlap (the reverse direction).
- *Find what the reader's eye does* -> render the region and take the vertical ink profile; valleys are gutters; one method for text, OCR and pictures.
- *Ask each row to vote* -> today's channel vote (have).
- *Ask the layout model for the box and the OCR engine for the cells* -> picture tables.
- *Speak the checker's language* -> HTML with `th` on the first column and `rowspan` for group labels.
- *Read it twice and keep the consistent reading* -> two scales or two engines on a scanned table; keep the reading whose numeric columns agree.

### Multi-column (233 failing). Purpose: every sentence whole, in the author's order.
Current concept: **trust the hidden layer's characters, rebuild the geometry** (D010); order by recursive cuts.
Fan (the 148 text near misses): *two witnesses, one referee* (the layer and our recogniser read the same ink); *the language decides the spacing*; *the pixels decide the spacing*; *the glyph that lies* (a text-layer "e" whose ink is a dash); *confusion-aware spelling confirmed by pixels*.
Fan (the 52 cut sentences, 16 orderings): *the sentence knows its continuation* (interlopers wait); *non-body blocks go to the end of their column*; *columns as chains of baselines*.

### Long tiny text (90 failing). Purpose: each tiny sentence, exact.
Fan: the same two witnesses; *native-resolution line crops using the layer's line boxes as the detector*; *punctuation from the pixels*; *the language decides the spacing*.

### Old scans and old-scan maths (928 failing with baseline). Purpose: read what a human can read on an old page; leave honest gaps.
Current concept: **one general recogniser, a capped resolution, the page accepted or rejected whole**.
Fan: *accept by the line*; *change the picture, not the reader* (native resolution, binarise, deskew, crop by region); *several small readers vote*; *a formula reader on formula crops*; *the page teaches its own font* (cluster identical word images, majority reading; wild); *typewriter-specific models*.

### Formulas (387 failing). Purpose: LaTeX that renders like the page.
Current concept: **rules over glyphs and positions**.
Fan: *render and compare* (KaTeX is already installed for the scorer); *enumerate the ambiguity as candidates and let the page's ink referee*; *learn the reference's habits from the formulas that pass*.

### Headers and footers (28), baseline (74).
Baseline is covered by "accept by the line". For headers I found no new concept cheaper than the cost of the 28 checks; left alone.

## The ideas

### 1. Accept by the line, not by the page
- **Purpose / concept / fan:** honest partial reading; "confidence is a property of a line, not a page"; old scans -> accept by the line.
- **Mechanism:** `apply_ocr` today accepts or rejects a whole page on mean confidence 0.75 and word-likeness. When a page fails, keep the lines that individually pass a stricter bar (line score 0.9 or more, three or more tokens, at least 60% dictionary words or numbers, no repeated-character runs), write only those, and say so: a front-matter note "partially read: N of M lines; the rest unread" and a non-alphanumeric marker (an ellipsis line) where lines were left out, so the marker itself cannot pass a check. A handwritten letter's typed letterhead, date line and signature block appear; the handwriting stays out.
- **Group and reach:** baseline 71 (old scans 61, old-scan maths 10) plus whatever present/order checks sit in typed lines of those pages (some of 290). If every empty page has one such line, about +1.7 overall [derived: 61/526 + 10/458 section points, over 8]; realistically half.
- **Cost:** 3 to 4 hours, plus an owner decision (an amendment to D008/D009: a confident line of real print is not filler).
- **One-hour test:** for the 71 pages with empty bodies in run 48's outputs, run `ocr_page_turn`, list the lines with score 0.9 or more and three or more word-like tokens, count pages with at least one, print those lines for 15 pages and read them against the scans. Pass: 30 or more pages have one and none of the printed lines is noise.
- **Strongest objection:** half the gain is the benchmark rewarding "anything alphanumeric"; the reader's gain is a date and a letterhead without the letter, which can mislead. The note and marker are the mitigation, and the owner must want it.

### 2. Change the picture, not the reader: native resolution, region by region
- **Purpose / concept / fan:** read old print and small print correctly; "the recogniser sees only what we show it"; old scans and tables -> change the picture.
- **Mechanism:** for pages without a text layer, render at the scan's own resolution (`extract_image` gives the embedded image's pixel size; scale = pixels / page points) instead of the 2,000 px cap; to bound memory, read region by region (layout-model boxes, or horizontal bands of about 1,600 px) rather than the whole page. For small-print regions (a table of accession numbers), also try a 2x upsampled crop and keep the reading with the higher mean confidence; for old print, a binarised copy as a second input.
- **Group and reach:** old-scan read pages (127 checks, 102 of them near or partial), OCR'd tables (21) and, with idea 6, picture tables (46); old-scan maths text lines. Tiny text gains little (only 5 of 16 image-only pages exceed the cap). Estimate 30 to 60 checks.
- **Cost:** 2 to 4 hours.
- **One-hour test:** the ten old-scan pages with most failing checks (17, 75, 74, 70, 10, 24, 63, 62, 61, 71) and the table region of tables/008d1dbe (our read: "0Ql.5)')81" for "DQ453581"): OCR at 2,000 px and at native size; count failing snippets found with the checker's `partial_ratio` at each check's threshold. Pass: 15% more snippets found and no page's mean confidence drops under the gate.
- **Strongest objection:** the recogniser normalises every crop to 48 px tall, so extra pixels help only the detector and the resampling; on clean typescript the gain may be nil and only small print benefits. The test settles it in an hour.

### 3. Two witnesses, one referee: word-level arbitration on hidden OCR layers
- **Purpose / concept / fan:** exact sentences on scanned pages that carry an old OCR layer; "two independent readings of the same ink, arbitrated by plausibility; nothing a witness did not read"; multi-column and tiny text -> two witnesses.
- **Mechanism:** on a page whose text is a hidden OCR layer: (a) the layer is witness one; (b) our recogniser, recognition only, reads line crops at native resolution using the layer's own line boxes as the detector: witness two; (c) align the two readings token by token; (d) where they differ, a referee scores each candidate: dictionary word or number pattern +2, plausible letter and vowel shape +1, the difference is a known confusion pair (c/e, l/1/I, o/0, rn/m, quote/l, dash/e) +1, witness two's line confidence 0.9 or more +1; ties go to the layer; (e) only ever replace a token with the other witness's token; never add a word neither read. Where witness two has a space and the layer none, split (the pixels showed a gap). The count of arbitrated words goes in the front matter. Run 48 examples it would decide: "socicties" / "societies", "trce-lined" / "tree-lined", "305e314" / "305-314", "Sfate" / "State", "beanty", "meetiugs", "dopation".
- **Group and reach:** multi-column 148 near misses, tiny text 76 near or partial, old-scan read pages about 100. A third of those is about +2 overall [derived: 50/884 + 25/442 + 33/526 section points, over 8].
- **Cost:** 6 to 8 hours, on top of idea 2's rendering.
- **One-hour test:** `concept_fan_census.py long_tiny_text` prints the 76 REF/OUT pairs. For each differing token, crop the layer's line at native resolution, run `engine.text_rec`, and count tokens where witness two equals the reference; then run 200 undisputed tokens and count how often witness two contradicts a correct layer (false alarms). Pass: witness two right on 40% or more of disputed tokens and the referee choosing correctly on 80% or more of disagreements.
- **Strongest objection:** the pack says re-reading was worse than the layer. That was whole-page replacement at 2,000 px, and the log's own count (13 of 66 strings found by the fresh read, 9 by the layer) says the two are complementary. The real risk is the referee: a dictionary favours common words over rare right ones ("bride" and "bridge" are both words, so ties keep the layer; "Yulnus" stays wrong because neither witness offers "Vulnus"), and numbers must never be touched unless the layer's token is shape-impossible.

### 4. Punctuation and spaces from the language and the pixels, not from the layer's geometry
- **Purpose / concept / fan:** the 31 tiny-text and about 120 multi-column token errors that are spacing and quote marks; "on a hidden OCR layer the geometry is meaningless (D010), so spacing must come from somewhere else"; tiny text -> language decides, pixels decide.
- **Mechanism:** on OCR-layer pages only: (a) after `,` `;` `:` followed directly by a letter, insert a space unless the token is a number, a time, a known abbreviation pattern or a URL, and confirm on the rendered line that there is a white gap of 0.15 em or more at that x; (b) a quote mark glued to a word with no partner in the sentence: look at the pixels above the x-height at that spot, no ink means no quote; (c) a full stop followed by a lowercase word inside a line ("woodwork.is") is re-read from the pixels (a comma has a descender, a full stop none).
- **Group and reach:** tiny text 31 token errors in 90 checks; multi-column 71 punctuation, 40 split, 10 space errors in 233; old scans 28. A check needs every one of its errors fixed, so 30 to 50 checks.
- **Cost:** 2 to 3 hours.
- **One-hour test (30 minutes, no conversion):** apply rule (a) as a regex to copies of run 48's outputs for the OCR-layer pages of `long_tiny_text` and `multi_column`, then run the checker's `TextPresenceTest` and `TextOrderTest` classes on the failing checks and on the passing checks of the same pages. Count wins and losses.
- **Strongest objection:** a text regex is exactly the kind of rule that has fired elsewhere and cost this project points ("w i t h"); run 39 already added a punctuation-space rule and these 15 survived it, so the trigger must differ (probably the geometry vetoed it). The pixel confirmation is what keeps it honest, and that needs idea 2's rendering.

### 5. Ask the numbers where the columns are; hand the heading words down to them
- **Purpose / concept / fan:** right headings and neighbours; "the data knows the columns better than the heading does"; tables -> numbers vote, headings from the data.
- **Mechanism:** inside a table region, rows with 60% or more numeric tokens vote for column centres (token centre, or right edge for right-aligned numbers); cluster into columns. Heading lines above the first numeric row are then split by those columns: each heading word joins the column whose span covers its centre; a word bridging two columns spans both (`colspan`); words stacked over the same column join top to bottom with a space ("5 Year" + "Return %"; "Local council" + "only"; "Beta" + "(Risk)"; "Gestation (weeks)" parted from "Comment"). On OCR pages take word x-positions from a re-detection on the crop or from the recogniser's time axis, not from dividing the line evenly.
- **Group and reach:** tables, the 47 `top_heading` failures and the glued or stacked headings among `up`/`left`/`right`; pages 11e12a3d (10 checks, an OCR page whose header boxes hold four headings each), 26076dc3 (4), 0091c5b2 (1), the census printout (5). Estimate 30 to 50 checks.
- **Cost:** 4 to 6 hours.
- **One-hour test:** on 26076dc3 and 0091c5b2 (text-layer pages: `rawdict` gives word boxes) prototype the vote and the split in a scratch script and compare the headings produced with the failing checks' `top_heading`, `up` and `down` values; for 11e12a3d use the OCR lines. Pass: the reference headings come out on all three pages.
- **Strongest objection:** text-only tables get nothing (fall back to the channel finder), and a wide heading over five numeric columns ("No (%) of inpatients immunised by various providers") must become a `colspan`, not a join, or the stacked join makes a wrong cell. The checker accepts either form.
- **Variant, typed rulings:** on a monospace page (every character the same width) put the characters on the grid (column = round((x - x0) / width)); a grid column that is blank or holds only `|` or `:` in every data row is a separator, a `----` row is a rule, the header block is the rows above the first numeric row, joined per column span. Five checks on the benchmark (the census page), but every mainframe and census report in the world; 3 hours; one-hour test on tables/ff19f6fe with `rawdict`.

### 6. A table box with no text inside is read into a table, not into paragraphs
- **Purpose / concept / fan:** cells from tables that are pictures; "the layout model already says table; the picture-OCR path throws that away"; tables -> the layout model for the box, OCR for the cells.
- **Mechanism:** when a layout-model table box contains no text-layer lines (a screenshot or a scanned table on a digital page, or any box on a scanned page), OCR the crop at native or 3x resolution (idea 2), then build the table with `table_from_lines(lines, trusted=True, extent=box)` under D009's numeric-share gate, and list the region under `truedoc.ocr_regions` as picture OCR does today.
- **Group and reach:** tables, the 46 picture-table checks and some of the 21 rejected-OCR tables. Estimate 20 to 40.
- **Cost:** 3 hours.
- **One-hour test:** the four picture-table pages from the set-aside experiment plus 11e12a3d: `ocr_region` on the layout box at 3x, then `table_from_lines`; check the failing cells and their neighbours by hand. Pass: 10 or more of the 46 checks' cells found with the right neighbour.
- **Strongest objection:** the experiment "gained 4 checks on one page, nothing elsewhere" could not have won a table check at all (fact 3), so it is not evidence against this; the real objection is OCR quality on small screenshots, which is idea 2's question.

### 7. A formula reader for scanned maths
- **Purpose / concept / fan:** LaTeX from old printed maths; "the recogniser must match the content, and a text recogniser cannot write LaTeX"; old-scan maths -> a formula reader on formula crops.
- **Mechanism:** on scanned pages, take the layout model's formula boxes (RT-DETR labels formulas on the rendered page whatever the text source), crop at native resolution, and run a small image-to-LaTeX model on the CPU: pix2tex / LaTeX-OCR (MIT licence [recalled], about 25 million parameters [recalled], a second or two per crop). Accept a reading only if KaTeX renders it (the checker's `render_equation` is installed) and the render's ink roughly matches the crop (idea 8's referee); write it as `$$...$$` tagged `[^inferred]` per D015, the model named in the front matter.
- **Group and reach:** old-scan maths, 439 failing (the section stands at 4.1). Every 10% of them is about +1.2 overall [derived: 44/458 = 9.6 section points, over 8].
- **Cost:** 6 to 8 hours; install in a scratch environment first.
- **One-hour test (after a ten-minute install):** crop 15 display formulas from five failing pages (boxes from the layout model, or by hand), run the model, compare each result with the reference `math` string in `failed_tests.jsonl` through `compare_rendered_equations`. Pass: 3 or more of 15 match; that rate would already double the section.
- **Strongest objection:** trained on rendered modern LaTeX; 1900s Indian-press scans with broken type and old notation may defeat it, and a formula wrong in one glyph scores nothing. It is a model reading pixels, so its output must be marked inferred, which the owner may not want inside a maths book.

### 8. Render and compare: the page's own ink as referee for formula ambiguities
- **Purpose / concept / fan:** the remaining arXiv formulas; "test the answer against the picture"; formulas -> render and compare.
- **Mechanism:** where the rebuild is unsure (hat or wide hat, whether a radical covers the whole numerator, the level of a script of a script, the delimiters of a matrix) emit two or three candidate LaTeX strings built from the same glyphs; render each with KaTeX (installed for the scorer; its fonts derive from Computer Modern [recalled], as do most arXiv PDFs); render the PDF's formula box with PyMuPDF at the same height; binarise, align, and keep the candidate with the best ink overlap. Nothing is invented: every candidate is built from the glyphs on the page.
- **Group and reach:** arXiv maths, 387 failing, of which the pack's list names four ambiguity families. Estimate 30 to 60.
- **Cost:** 6 to 10 hours (candidate generation is the work; the comparison is two).
- **One-hour test:** for 20 failing formulas whose failure is a known binary choice, render our output and the alternative with `render_equation`, render the PDF crop, compute the overlap. Pass: the overlap picks the reference-matching candidate in 15 or more of 20.
- **Strongest objection:** KaTeX and TeX differ in spacing and sizes at exactly the script level where the ambiguities live, so the overlap may be noisy; and if KaTeX cannot tell two candidates apart, neither can the checker, and the choice does not matter.

### 9. Defer the interloper: a sentence finishes before a footnote, caption or form field is read
- **Purpose / concept / fan:** the 52 sentences cut at a block boundary; "the sentence knows where it continues; blocks that are not body text wait"; multi-column order -> the sentence knows its continuation.
- **Mechanism:** after reading order is assigned, scan consecutive blocks A, X, B: if A ends without terminal punctuation and its last line is not short, B starts lowercase or with the second half of A's hyphenated word, and X is not body text (caption, footnote, figure, form field, small type), move X after B. Repeat until stable. It needs no pattern of what interrupts, only the cut sentence.
- **Group and reach:** multi-column, about 52 checks. Estimate 20 to 30.
- **Cost:** 3 to 4 hours.
- **One-hour test:** on the 52 pages, dump block kinds and count how many interlopers our own classifier already labels non-body. Pass: 30 or more; if the interlopers are mostly labelled body text the idea becomes "classify the interloper first".
- **Strongest objection:** the pack says "no single pattern": true of what interrupts, not of the cut sentence. The risk is moving a genuine paragraph; the guard is that X must be non-body and shorter than a column.

### 10. Several small readers vote on old print
- **Purpose / concept / fan:** the one- and two-character slips on typed old scans; "no single classical recogniser knows old typefaces; agreement is evidence, disagreement a referee's job"; old scans -> several readers.
- **Mechanism:** read each line with RapidOCR's English v3 (as now) and v4 models (same Apache-2.0 zoo [recalled]) and with Tesseract 5 (Apache-2.0 [recalled], trained on many historical fonts); per line keep the reading with the best dictionary share and confidence, or merge tokens as in idea 3. TrOCR-base-handwritten (MIT [recalled], about 334 million parameters [recalled]) is the handwriting variant, one line at a time: heavier, a separate test, and its output must be marked inferred.
- **Group and reach:** old-scan read pages, 127 checks (102 near or partial); possibly some rejected pages if Tesseract reads typescript RapidOCR does not. Estimate 20 to 40.
- **Cost:** 4 to 6 hours plus an optional dependency (Tesseract is a system binary).
- **One-hour test (after install):** Tesseract on the ten old-scan pages with most failures; count failing snippets found by each engine and by the union.
- **Strongest objection:** a system install is a packaging burden for a product; and a second engine's plausible-looking wrong words on handwriting are exactly what D008 forbids, so it must go through the same referee as idea 3.

## Best bet

**Idea 3, two witnesses with one referee, built on idea 2's native-resolution rendering.** It addresses the largest mechanical pool (148 + 76 + about 100 checks across three sections, about +2 overall at a one-third success rate [derived]); it keeps the evidence-first principle exactly (both witnesses read the page's own ink, the referee only chooses, nothing is added); its one-hour test is decisive and the harness is already written; and the pack's own evidence says the two witnesses are complementary (13 strings found by the fresh read, 9 by the layer, of 66). The cheapest sure points are idea 1, but it needs the owner's yes on D008 and half its gain is the benchmark rather than the reader. The highest ceiling is idea 7 (old-scan maths at 4.1), and it is the least certain.

The fact that would flip the best bet: if witness two is right on fewer than a quarter of the disputed tokens, or the referee is wrong on more than a fifth of the disagreements, idea 3 collapses to idea 4 (punctuation and spaces only) and idea 1 becomes the best bet.

## Claims in the evidence pack I doubt

1. **"Our own OCR read of those pages is not better than the hidden layer (tried: 13 of 66 strings found against the layer's 9)."** 13 is more than 9. The two readings are complementary, which argues for a union, not against re-reading; and the fresh read ran at the 2,000 px cap while the failing scans' median long side is 3,196 px.
2. **"OCR of pictures on digital pages: one page gained 4 checks, everything else nothing."** The picture path builds paragraphs and never a table (fact 3), so the 46 picture-table checks were structurally out of reach; the experiment says nothing about whether OCR can read those tables.
3. **"RapidOCR's English model cannot read old typefaces."** On the 36 old-scan pages we do read, the type is read with one- or two-character slips (fact 6); that is an arbitration problem, not a "cannot read" problem. Handwriting is a different matter and the statement holds there.
4. **The multi-column near misses are described as "the hidden OCR layer's own character errors".** Most are, but in tiny text a third of the token errors are spacing and quote marks (fact 5), which a spacing rule fixes without any re-reading, and in multi-column the punctuation-only class (71) is the largest single class.
