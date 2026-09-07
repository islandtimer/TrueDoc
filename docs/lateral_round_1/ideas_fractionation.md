# Fractionation round: re-cutting the problem along unusual axes (7 September 2026)

Technique: fractionation (de Bono). The pipeline cuts the problem by stage and the benchmark cuts it by section. I re-cut it four other ways: by the physical substance on the page (ink, pixels, rules, glyph shapes, PDF operators, embedded fonts), by what a scanner did to the page, by document genre, and by the checker's arithmetic. In each fraction I asked what is lying there unread. Ideas were harvested first and judged afterwards; the objections are at the end of each idea.

Tags: [verified] measured here with a script over run-48 outputs and the benchmark PDFs; [derived] computed from those measurements; [recalled] from memory, unchecked; [assumed] chosen to proceed.

## What the fractions turned up before any ideas (all [verified] unless marked)

Counted over `failed_tests.jsonl` (1,896 failing checks) with the checker's own normalisation and `rapidfuzz.partial_ratio`, and over the PDFs with PyMuPDF.

- **Producer metadata is useless**: every PDF says producer `pypdf` (the benchmark rewrote them), except old scans, which say `img2pdf`. But page-level fingerprints survive: the font name of a hidden OCR layer names the engine that made it (`GlyphLessFont` = Tesseract, `HiddenHorzOCR` = Adobe Acrobat, `Courier` set invisible at 5-7 pt with 2-3 characters per text object = the archive.org/ABBYY pipeline, which also carries two JPX images, 166 dpi and 500 dpi) [derived; engine attribution recalled].
- **Hidden layers are a minority of scanned pages.** Pages with invisible text (`3 Tr`): tiny text 23 of 62, multi-column 24 of 231, tables 7 of 188, old-scan maths 15 of 36, old scans 0 of 98. Pages with no text layer at all: tiny text 23, old scans 98, old-scan maths 21, tables 13, multi-column 11.
- **The OCR pass reads scans at a fraction of their resolution.** `ocr/rapid.py` caps the rendered page at 2,000 px on the long side (`_MAX_SIDE`), while the embedded scans are 2,500-6,000 px. On failing pages with no text layer, the rendered/native ratio is below 0.75 for 411 of 479 old-scan checks (typical ratio 0.31-0.40), 148 of 260 old-scan-maths checks, 27 of 35 table checks, 17 of 53 tiny-text checks (those pages at exactly 0.5), 12 of 33 multi-column checks. About 615 failing checks sit on pages we read at under three-quarters of their pixels; of those, roughly 190 are on pages that produce text (the rest are the empty handwriting pages).
- **Tiny text is mostly our own OCR, not the hidden layer.** Of the 90 failing tiny-text checks, 53 are on 16 pages with no text layer (RapidOCR's reading), and 26 of those are within three edits of passing. Only 37 are on hidden-layer pages; of those 23 are near misses of the layer itself, 6 are in the layer but lost by us, 6 far off.
- **Near misses are about spaces.** Edit operations between failing snippets and our nearest text in tiny text: roughly half are a missing space after `;` `,` `:` or between words (`closer;for`, `usualormore`) or an extra space; the rest are OCR confusions (`e`→`c`, `,`→`.`, `ə`→`o`). Raising `max_diffs` by 2 on both sides would flip 44 of 90 tiny-text and 21 of 251 old-scan presence checks: that is the size of the "almost right" pool.
- **Multi-column order failures are mostly missing text.** Of 233: one snippet missing 160, both missing 52, page empty 4, a true misorder 17. Of the 17, the content stream's own order is right for 8, wrong for 2, and 7 have a snippet that is not in the raw layer at all. Only 47 of the 233 have both snippets findable in PyMuPDF's raw text at the check's tolerance (a lower bound: raw text still carries line-end hyphens).
- **Tables**: no table at all 48, cell nowhere in our output 41, cell in our text but not in a table 66, cell in a table with the wrong neighbour 66, page empty 5. Failing relations: top heading 47, up 43, right 39, down 38, left 32, left heading 27.
- **Old scans**: 351 of 479 failing checks are on empty outputs (handwriting rejected); 128 are on pages we do read (28 within three edits).
- **Checker arithmetic, dead ends checked and closed**: no failing `absent` check is caused by the YAML front matter (0 of 28); the checker's italics regex (`*...*`, `_..._` on one line are deleted before matching) erases none of the failing snippets, though 873 lines on failing pages carry two bare `*` or `_` and are at risk in future; 0 of the 2,927 arXiv maths references are short and backslash-free.
- **One-sided space repair on our OCR outputs** (space after `,;:!?` before a letter; no space before `.,;:`), scored over all presence checks of two sections: tiny text +6 / -0 of 442, old scans +4 / -1 of 279. A greedy word-splitter driven by the 8k common-word list was destructive (+5 / -96): it splits real words (`remarkable` → `remark able`).

## Ideas

### 1. Read the scan at its own resolution (fraction: pixels; what the scanner gave us that we throw away)

- **Movement**: the physical substance of a scanned page is its pixel grid; the pipeline renders the page into a smaller grid before the recogniser ever sees it. The scan's native size is metadata already in hand (`get_images` width/height).
- **Concept**: never show the OCR engine fewer pixels than the scanner captured; show it more only when the type is tiny.
- **Mechanism**: in `ocr/rapid.py`, set the render scale from the largest embedded image (`native_px / page_pt`, capped at about 600 dpi) instead of `min(300/72, 2000/long_side)`. When the rendered page would exceed what the detector handles well (about 3,000 px on a side), cut it into two or three overlapping horizontal bands, run detection and recognition per band, and drop boxes duplicated in the overlap. Keep the recogniser's crops at least 48 px tall (upscale a band when the median box is shorter).
- **Failure group and size**: every non-empty OCR page: old scans (128 failing checks on pages we read), tables on scans (27), tiny text (17 on the half-resolution pages), multi-column (12), headers (3). Exposure about 190 checks; a realistic gain 20-60 [assumed]. It also raises the pages' mean confidence honestly, so some pages now rejected at 0.75-0.80 may clear the gate.
- **Cost**: 3 hours.
- **One-hour falsification**: take old_scans/43.pdf, 30.pdf, 46.pdf (ratios 0.49-0.64), long_tiny_text/17_pg86_pg1.pdf and 17_pg17_pg1.pdf (0.5), tables/11e12a3ddca3…_pg8_pg1.pdf (CCITT 399 dpi, rendered at 0.56). Render each at native resolution, run RapidOCR, and count reference strings from the section jsonl found at the check's tolerance, against run 48's count on the same pages. No gain on six pages kills it.
- **Strongest objection**: RapidOCR's detector was trained around 1,000-px images; very large inputs can fragment lines or exhaust memory, and beyond about 48 px of line height the recogniser gains nothing. Also the biggest old-scan losses are handwriting pages that stay empty at any resolution.

### 2. Re-read single words with the hidden layer's own boxes, choosing by engine fingerprint (fraction: embedded fonts and PDF operators)

- **Movement**: the hidden layer is not only characters; its font name says which engine made it, and its text objects give word or phrase boxes. The pipeline uses the characters and rebuilds everything else.
- **Concept**: the layer is a map of where words are and a hint of how they went wrong; use both to re-read only the words worth re-reading.
- **Mechanism**: on a hidden-layer page, keep the layer as the reading. For each layer word that fails a cheap test (not in a large word list, not a number, contains the engine's known confusions such as `c`/`e`, `'`/`"`, `rn`/`m`), crop that word's box from the page image at native resolution, recognise it with RapidOCR, and replace the layer word only when the new read is within two edits of the old one and passes the word test with confidence at or above 0.9. Per-engine confusion lists come from the fingerprint (Tesseract's `GlyphLessFont`, Acrobat's `HiddenHorzOCR`, ABBYY's invisible Courier).
- **Failure group and size**: tiny text 23 near-miss-of-layer checks plus 6 lost; multi-column near misses on hidden-layer pages (the pack says most of 148); tables on hidden-layer pages. Realistic 20-40.
- **Cost**: a day.
- **One-hour falsification**: for the 23 tiny-text checks where the layer itself is within three edits, list the wrong words with `Levenshtein.editops`, crop them at native resolution and run RapidOCR on the crops; count how many come back matching the reference. Fewer than 5 of 23 kills it.
- **Strongest objection**: the page-level re-read was worse than the layer, and a word crop has even less context. But see the doubts below: that experiment ran at half the page's resolution.

### 3. The page teaches its own alphabet (fraction: ink shapes; the JBIG2 idea turned to good use)

- **Movement**: JBIG2 compresses old print by noticing that the same letter shape recurs and storing it once. A single page of letterpress is set from one fount, so every `e` is nearly the same bitmap. The pipeline reads each glyph as if it had never seen it before.
- **Concept**: consistency is evidence. If a shape occurs forty times and the recogniser calls it `e` thirty-six times and `c` four times, the four are wrong.
- **Mechanism**: binarise the page, find connected components, normalise each to a small bitmap and cluster by Hamming distance. Align RapidOCR's per-character output to the components (the line's characters spread over the line's components in order). Give each cluster its majority label; where a member's label disagrees with the majority and the majority is strong (at least 80 percent, at least 8 members), replace it. Unlabelled or ambiguous clusters are left as read. Nothing is invented: every label came from the recogniser on this page.
- **Failure group and size**: old-print near misses (old scans 28, tiny text 26), where the confusions are `e`→`a`, `n`→`m`, `e`→`s`, `f`→`t`. Realistic 10-25.
- **Cost**: 2 days.
- **One-hour falsification**: on old_scans/68.pdf, 69.pdf and 23.pdf, cluster the components and measure label purity using RapidOCR's output; if fewer than 85 percent of the big clusters are label-consistent, or the failing characters are not the outliers, drop it.
- **Strongest objection**: `rapid.py` places characters by estimated width, so the alignment is noisy; broken and touching glyphs in old print fragment the components; the gain is a few dozen checks at most.

### 4. Vote across several undoings of the scanner (fraction: what the scanner did)

- **Movement**: blur, thresholding and skew are each partly reversible in several ways, and each reversal makes the recogniser err differently.
- **Concept**: three cheap readings that disagree in different places beat one reading; agreement is a confidence measure that costs no model.
- **Mechanism**: read the page three ways (native-resolution grey; Sauvola-binarised; 1.5x upscaled with a light unsharp mask). Align words by box overlap. Where all agree, keep. Where they disagree, keep the candidate that is a word or number with the highest confidence; if none is, keep the native read. Report the agreement rate as the page's confidence, so the 0.75 gate judges agreement rather than one model's self-belief.
- **Failure group and size**: old scans read but wrong (128), tiny text no-layer (53), table scans (27). Realistic 15-40.
- **Cost**: 4 hours, and three times the OCR time per scanned page.
- **One-hour falsification**: ten near-miss old-scan and tiny-text pages; count checks flipped by the vote against the native single read (idea 1).
- **Strongest objection**: the three readings share the recogniser, so their errors are correlated on truly degraded type, and the gate change could admit noise pages that are now rightly empty.

### 5. Fixed-pitch printouts are tables by construction (fraction: genre, ledger and computer printout; substance, the font's advance widths)

- **Movement**: 70 failing table checks are text we already have but did not shape into a table: a census printout with `|` and `:` separators, an attendance list, lines of 149 characters in Courier (tables/ff19f6fe…_pg4.pdf: 64 text objects of 149 characters each).
- **Concept**: in a monospace block every glyph sits in a character column; a table in such a block is defined by the columns that are blank (or `|`) on nearly every line, and needs no whitespace-channel heuristics tuned for proportional type.
- **Mechanism**: detect a block whose glyph advances are all equal (Courier, or any font whose widths are one value). Map each glyph to `round((x - x0) / advance)`. Count, per character column, how many lines are blank or `|` there; columns blank on 90 percent of lines separate cells. Heading rows are the lines above the first row whose cells are mostly numeric. Emit a markdown table; fold a wrapped continuation line (blank in the first column) into the row above.
- **Failure group and size**: the 66 "cell in text, not in table" checks, of which the monospace pages are perhaps 10-20.
- **Cost**: 4 hours.
- **One-hour falsification**: build the grid for tables/ff19f6fe…_pg4.pdf and a769f9a3…_pg2.pdf and check whether the failing cells' expected up/down/left/right neighbours land in adjacent cells.
- **Strongest objection**: few benchmark pages are monospace, and ragged rows or wrapped cells break the blank-column vote.

### 6. Content-stream order as a veto on block breaks (fraction: PDF operators)

- **Movement**: a digital PDF's text arrives in the order the typesetter emitted it; the pipeline discards that order and rebuilds it from geometry alone.
- **Concept**: geometry decides layout; the stream decides continuity. A sentence whose glyphs are consecutive in the stream should not be interrupted by a block whose glyphs are far away in the stream.
- **Mechanism**: keep each character's sequence number from `rawdict`. When the block builder or reading-order pass places block B between two blocks A and C that are stream-adjacent and whose join reads as one sentence (A ends mid-sentence, C starts lower case), move B before A or after C. When the column rule is unsure (no full-height gap), fall back to stream order for the tied blocks.
- **Failure group and size**: the 17 true misorders (stream order is right for 8, wrong for 2), and a share of the 52 mid-sentence breaks on digital pages (unmeasured). Realistic 10-30.
- **Cost**: 4 hours.
- **One-hour falsification**: for the 52 broken-sentence pages, count how many failing snippets are contiguous in `page.get_text("text")` without sorting; under 20 kills it.
- **Strongest objection**: hidden OCR layers have no meaningful stream order, and some producers interleave columns line by line (the 2 stream-wrong cases), so the veto must be confined to digital pages with long text objects.

### 7. Write simple inline maths as prose (fraction: checker arithmetic)

- **Movement**: the checker strips bold and italics but keeps `$`. Our prose says `$k=2$`, the reference says `k = 2`: four edits, and the sentence fails. Zero of the 2,927 arXiv maths references are short and backslash-free, so nothing on the maths side depends on such expressions being wrapped.
- **Mechanism**: inside a prose block, an inline formula made only of letters, digits and `= < > + -` (no backslash, no script) is written plain, with spaces round relation signs. Everything else stays LaTeX.
- **Failure group and size**: the 11 multi-column checks named in the pack. Measured risk on the maths section: 0 checks.
- **Cost**: 1 hour. **Test**: re-render the 11 pages and re-check; run the two maths samples for no loss.
- **Strongest objection**: it bends output toward the checker's taste; but "k = 2" is also how a copy-editor would set it.

### 8. Punctuation spacing repair on OCR pages, and a cautious word-splitter later (fraction: checker arithmetic; genre, dictionary)

- **Movement**: half the near-miss edits are spaces. The recogniser drops the space after `;` `,` `:` in tiny type and glues short words.
- **Mechanism, part 1 (measured)**: on OCR-read pages only, insert a space after `, ; : ! ?` when a letter follows, remove a space before `. , ; :`. Measured one-sided on run-48 outputs: tiny text +6 / -0, old scans +4 / -1.
- **Mechanism, part 2 (not yet measured)**: split a glued token only when it is absent from a large frequency list (100k+ words), splits into parts all of which are frequent words of three or more letters, and the split is unique; otherwise leave it. My greedy splitter on the 8k list lost 96 checks, so the "do nothing when unsure" rule is the whole design.
- **Failure group and size**: tiny text 10-20, old scans 5-10.
- **Cost**: 2 hours for part 1, a day for part 2.
- **One-hour falsification**: part 1 is done (above); for part 2, score the splitter over all 442 tiny-text presence checks before trusting it, as I did.
- **Strongest objection**: dictionary pages are full of non-words (headwords, Middle English, etymologies), exactly where the splitter would be tempted; part 2 must be conservative or it repeats my -96.

### 9. A small formula-image model for old printed maths, gated by re-rendering (fraction: genre, 1900s maths journals)

- **Movement**: old-scan maths scores 4.1 with 313 failing checks on pages we do read; the layout model already draws "formula" boxes on those pages and we discard them.
- **Concept**: a small image-to-LaTeX model is allowed by the constraints if its licence is permissive; its output is accepted only when re-rendering it reproduces the ink, so nothing is invented and the acceptance is a measurement, not a belief.
- **Mechanism**: crop each formula region at native resolution; run pix2tex / LaTeX-OCR (MIT-licensed, about 25M parameters, CPU-capable per crop [recalled]); render the returned LaTeX with the KaTeX headless renderer already installed for the checker; binarise both, align by size, and accept when the overlap (IoU) is at least 0.6; mark accepted formulas as inferred (D015).
- **Failure group and size**: old-scan maths 313 non-empty checks; realistic 30-100.
- **Cost**: 2 days.
- **One-hour falsification**: 20 formula crops from old_scans_math/4_pg512.pdf, 2_pg349.pdf, 5_pg174.pdf; count LaTeX that the checker's own render comparison accepts against the reference. Under 3 of 20 kills it.
- **Strongest objection**: such models are trained on rendered TeX, not letterpress with broken type; and it is a model reading pixels, which the owner allows only as a small task model with a permissive licence to be confirmed.

### 10. Text drawn as outlines, read by rendering the drawing (fraction: substance, path outlines)

- **Movement**: "vector-outline text: nothing to read" was set aside. tables/fbeb6edc…_pg1.pdf has 4,431 small filled paths and 5 failing checks; the paths are glyph outlines from a CAD or plotter export.
- **Mechanism**: find clusters of glyph-sized filled paths sharing a baseline; render that region at 300 dpi and pass it through the existing picture-OCR route with the same confidence gate.
- **Failure group and size**: 5-15 checks across tables and multi-column.
- **Cost**: 3 hours. **Test**: render that page's paths, OCR, and look for the five failing cells.
- **Strongest objection**: tiny gain; risk of reading decorative artwork as text.

## Best bet

**Idea 1, native-resolution OCR.** It is the only idea with an exposure in the hundreds of checks, it uses evidence already in hand, it invents nothing, it costs an afternoon, and ideas 2, 4 and 8 stack on top of it. The fact that would flip it: if RapidOCR at native resolution finds no more reference strings on the six test pages than at 2,000 px, the recogniser is saturated and the remaining losses are the engine's, not the rendering's. Second bet: idea 2, because the hidden-layer pages are the ones where our reading and a second reading are both available for free.

## Claims in the evidence pack I doubt

1. "Long tiny text: 54 snippets are not in the hidden OCR layer at all" frames the loss as the layer's. Counted, 53 of the 90 failing tiny-text checks are on pages with no text layer whatsoever; what fails there is our own RapidOCR reading, 26 of them within three edits. The remedy is OCR quality in our hands, not a better layer.
2. "Our own OCR read of those pages is not better than the hidden layer (tried: 13 of 66 strings found against the layer's 9)" says the opposite of its numbers: 13 is more than 9, and the union of the two readings is the ceiling for a merge. More to the point, that experiment ran through `rapid.py`, which rendered those archive.org pages (500 dpi JPX, 2,470 x 4,030 px) at half their resolution.
3. "Re-reading poor hidden OCR layers with our OCR engine: worse than the layer" was therefore a test of half-resolution RapidOCR against full-resolution ABBYY; it should be re-run before being treated as closed.
4. Outside my brief but worth a line: D007 excludes AGPL components, and PyMuPDF (MuPDF, Artifex) is itself AGPL with a commercial licence [recalled]; the decision record should say how that is handled.

Scripts used (scratchpad, read-only over the repo): `census_physical.py` (page-level physical facts), `arith.py` (checker arithmetic over the failing set), `probe2.py` (front matter, italics regex, space repair, render resolution, inline-maths risk).
