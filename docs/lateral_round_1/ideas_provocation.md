# Provocation round ("Po") for TrueDoc, 7 September 2026

Technique: de Bono's provocation. Each "Po" is deliberately unreasonable; the movement from it (extract a principle, focus on the difference, moment-to-moment, positive aspects, special circumstances) is what yields the idea. Harvest first, judge after: the objections sit at the end of each idea, not in the way of it.

Read-only. No conversions, no benchmark runs, no code changed. Twelve inspection scripts (PyMuPDF and the installed checker) were run against run 48's failing checks and outputs; every number below is tagged [verified] (read in code or output), [derived] (computed here) or [recalled] (from the evidence pack, unchecked).

## Facts gathered before the provocations (the ideas cite these)

- F1 [verified] OCR renders a page at `min(300 dpi, 2000 px on the long side)` (`truedoc/ocr/rapid.py`, `_MAX_SIDE = 2000`). Old scans are stored larger. [derived] Of the 97 old-scan pages with failing checks, 84 are read at less than 1/1.3 of the stored resolution (old_scans/43.pdf: stored 4108 px wide, read at 2000, i.e. half size). The tiny-text clippings 17_pg4, 17_pg17, 17_pg86 are stored at 600 dpi and read at 300. Failing pages without a text layer read below 1/1.3 of stored size: old scans 84 pages (414 checks in that folder, 61 of the pages empty), old-scan maths 12 (148), tiny text 5 (17), tables 7 (27), multi-column 3 (12).
- F2 [verified] RapidOCR's detector does not shrink large images (`config.yaml`: `limit_side_len: 736, limit_type: min`); the cap is ours alone.
- F3 [verified] On OCR pages, word and character boxes are made by dividing each recognised line evenly by character count (`_split_words`). So the white channels between table columns are invisible to the unruled-table finder on OCR pages. Example: tables/11e12a3d..._pg8 (no text layer): all 10 failing cells are in our output, but the first table has 4 columns where the page has about 13 ("Fund Type 5 Year Diver- | Beta Bull Bear Stocks | ...").
- F4 [verified] Hidden OCR layers carry uniform character widths and missing spaces. long_tiny_text/13_pg501: the layer line is `estimated at 15,000sq.m.` with every character 2.87 pt wide. Rendering that line at 8x and projecting the ink gives five wide white gaps (13 to 17 px against a 4 px median) at x = 48.8, 56.5, 60.8, 76.7, 85.8 pt: four are the true word gaps (after "estimated", "at", "15,000", "sq."); one is the white space after a narrow "1". The reference wants `15,000 sq. m.` with zero edits allowed.
- F5 [derived] Missing text snippets in run 48's outputs (non-empty pages only), classified with the checker's own `normalize_text`, a partial alignment, and Levenshtein on the de-spaced strings within the check's `max_diffs`:

  | folder | missing snippets | spacing only | spacing + `$` | spacing + punctuation | letters wrong, otherwise near | far, split or absent |
  |---|---|---|---|---|---|---|
  | multi_column | 264 | 11 | 2 | 34 | 148 | 69 |
  | long_tiny_text | 87 | 7 | 0 | 23 | 38 | 19 |
  | old_scans | 153 | 11 | 0 | 8 | 63 | 71 |

  So 96 snippets (29 pure spacing) are wrong only in spaces and punctuation; 249 are one to three letters wrong. Examples: `15,000sq.m.`, `closer;for`, `usualormore`, `JamesNorwood stillfavourspink boots`, `dclle` for `delle`, `trce-lined` for `tree-lined`, `bride` for `bridge`.
- F6 [derived] Snippets whose two ends are both found with other text between them: multi_column 35, tiny text 13, old scans 11 (59). True order errors (both ends found, wrong order): multi_column 17. Some interposals are whole paragraphs (17_pg86: 857 and 544 characters; 11_pg146: 2012), which is column interleaving, not a caption in the way.
- F7 [verified] 1507 of the 1896 failing checks allow zero edits; 236 allow one; 130 two. Median snippet length 64 characters.
- F8 [derived] One check is worth, in overall points (100 / checks in section / 8): tiny text 0.028, old-scan maths 0.027, old scans 0.024, headers 0.016, multi-column 0.014, tables 0.012, baseline 0.009. A tiny-text check is worth 2.3 table checks.
- F9 [verified] `--ocr-pictures` looks only at image blocks and demands at least 3 lines, 12 words, confidence 0.8 and 60% dictionary-like tokens. A picture of a table of numbers, or text drawn as vector outlines, never qualifies.
- F10 [derived] Of the 90 table pages with failures: 48 pages (92 checks) have every failing cell's text present in our output and a table in the output; 12 pages have no table in the output; 11 have no text layer; 3 are set in a monospaced face (10 checks). "Present" here is a fuzzy match anywhere in the body, so it is an upper bound.

## The harvest (provocations, unjudged)

1. Po: whitespace is the text.
2. Po: we read each page three times at three sizes.
3. Po: the text layer is the enemy.
4. Po: the scanner is a co-author.
5. Po: the reader writes the document.
6. Po: every page is a table.
7. Po: the output judges the input.
8. Po: the empty file is the best answer.
9. Po: the formula is prose.
10. Po: the column is a lie; each column is its own page.

Also raised, not developed: "Po: the reference is wrong" (20_pg49's reference drops the dashes the page prints; some misses cannot be fixed without copying the reference's error), "Po: read the page backwards", "Po: the page number is the title".

## Ideas

### 1. Gaps from ink

**Po and movement.** Po: whitespace is the text. Focus on the difference: the layer's spaces were typed by an old engine years ago; the page's spaces are white ink gaps that are still there. Principle: spacing is a property of the image, not of the text object.

**Concept.** On scanned pages (hidden layer or our own OCR), word boundaries come from the rendered line; characters are laid onto the ink runs.

**Mechanism.** For each line on a scanned page: render the line's box at 8x (or the stored resolution if higher); project ink onto columns; a blank run that is at least twice the median blank run and at least half a character pitch wide is a candidate word gap. Map candidate gaps onto the character string by position (the layer's characters are uniformly spaced, F4, so position is a count). Insert a space at a candidate gap when the layer has none there and the boundary shows a token signal: digit to letter, punctuation to letter, lower case to capital, or both halves are list words or numbers. Never remove an existing space, never split inside a run of digits. On OCR pages, replace the even division in `_split_words` with positions from the same ink runs, so column channels reappear for the unruled-table finder.

**Failure group and size.** F5: 96 snippets differ only by spacing or spacing plus punctuation (29 purely by spacing) across multi-column, tiny text and old scans; roughly 40 to 70 checks if half are recovered, at the highest per-check value (F8). Plus OCR-page tables: the 10 checks on 11e12a3d and the 21 OCR-wrong table checks in the pack.

**Cost.** 6 to 8 hours.

**One-hour test.** Over the 24 pages with spacing-only misses (7 tiny text, 9 multi-column, 8 old scans): find each missing snippet's line in the raw text layer, re-space by the rule from the rendered strip, then run the checker's `normalize_text` and `find_near_matches` with the check's `max_diffs`. Report recovered snippets and, on the same pages, any passing check that breaks (run every check for those pages, not only the failing ones).

**Strongest objection.** Newspaper pages stored at 72 dpi (10a, 16a) have word gaps of about one pixel, and the gap after a narrow "1" or "l" is as wide as a real gap (F4), so the token-boundary guard is load-bearing; some references lack the page's own punctuation (20_pg49) and stay lost.

### 2. Read at the scanner's resolution

**Po and movement.** Po: we read each page three times at three sizes. Moment-to-moment: at the instant we render for OCR we throw away half the pixels of most old scans (F1). Positive aspect of three readings: a second reading is a second witness for free.

**Concept.** OCR at the stored resolution, in tiles; where two scales disagree on a line, keep the more confident reading.

**Mechanism.** Take the largest embedded image's pixel size as native. If the native long side exceeds 2000 px, render at native (cap 4500) and cut into overlapping tiles of at most 2000 px with 8% overlap; OCR each tile; map boxes back to page points; merge duplicates in the overlaps (box overlap above 0.5, keep the higher confidence). Optionally also read at today's scale and, line by line matched by box, keep the reading with the higher confidence; both are readings of the page, nothing is invented.

**Failure group and size.** Old scans on the 36 non-empty failing pages (63 letters-wrong and 71 far snippets, F5), the 5 tiny-text and 7 table pages read at half size, and any print page now rejected at the 0.75 gate for lack of pixels rather than handwriting. Realistically 30 to 80 checks; the 61 handwriting pages gain nothing.

**Cost.** 3 to 4 hours.

**One-hour test.** Ten old-scan pages with output but failing checks plus the three 17_* clippings: OCR at native (tiled) against the current render; count reference snippets found with the checker's matcher at each check's `max_diffs`; also record mean confidence per page to see whether any rejected print page crosses 0.75.

**Strongest objection.** The detector was trained on images of about a thousand pixels; on a 4000-pixel page a text line 80 px tall may come back in fragments, and OCR time per page rises about four-fold on this CPU.

### 3. Two witnesses, one page

**Po and movement.** Po: the text layer is the enemy. Positive aspect: we stop trusting it blindly and cross-examine it. Special circumstance: the layer is wrong exactly where its token is not a word.

**Concept.** Word-level arbitration between the hidden layer and our recogniser, with the page image as the judge. The pack's experiment replaced whole pages; this replaces single tokens.

**Mechanism.** For each hidden-layer line, crop at native resolution and run only the recogniser (`engine.text_rec` on the crop, no detector). Align the layer's string and ours (Levenshtein alignment). For each differing span, form the two candidate tokens and take ours only when the line's recogniser confidence is at least 0.9, the layer's token is not a list word or number and ours is, and the edit is at most two characters. Otherwise keep the layer. List every change under `truedoc.layer_corrections`.

**Failure group and size.** Letters-wrong near misses on layer pages: 148 multi-column and 38 tiny-text snippets (F5). Target 30 to 60 checks.

**Cost.** 8 to 10 hours.

**One-hour test.** The 38 tiny-text letters-wrong snippets: crop their lines from the raw text layer's boxes, recognise, apply the rule, count recovered and broken with the checker's matcher.

**Strongest objection.** At 5 pt type on a 167-dpi scan (11_pg146 has a median size of 5.0 pt) the recogniser sees about twelve pixels of x-height and is probably worse than the layer; and the 10,000-word list rejects dictionary headwords and Middle English ("daunteden", "delle"), so the guard never fires where the misses are.

### 4. The page is its own font

**Po and movement.** Po: the scanner is a co-author. The co-author is consistent: the same metal type on every line. Principle: identical ink shapes must carry identical letters, whatever the layer says.

**Concept.** Cluster the page's glyph images and let the majority label correct the layer's isolated misreads (e to c, o to c, l to i, h to b, rn to m).

**Mechanism.** For each hidden-layer line: binarise the rendered strip and take connected components; if their count equals the number of non-space characters, pair them in order (else skip the line). Thumbnail each component (24 by 24, normalised), cluster by Hamming distance under 8%. In a cluster of at least 8 members with a 90% majority label, relabel minority members to the majority when the pair is a known confusion and the new token is more word-like (list word, or vowel share) than the old. List changes in the front matter.

**Failure group and size.** The same 186 letters-wrong snippets as idea 3, by a different witness; 30 to 60 checks.

**Cost.** 10 to 14 hours.

**One-hour test.** On 11_pg186 ("dclle") and 14b ("trce"): cluster the components and report whether the misread "c" glyphs fall inside the "e" cluster; also report the share of lines on each page where component count equals character count (the method's coverage).

**Strongest objection.** Touching letters in old print break the one-to-one pairing, so coverage may be a third of the lines; italics and small capitals mix clusters; and because the layer's positions are uniform (F4) one dropped letter shifts every later pair on the line.

### 5. The sentence isn't over

**Po and movement.** Po: the reader writes the document. The reader carries the sentence across a caption without noticing. Principle: grammatical continuity is evidence for order, as strong as geometry.

**Concept.** Sentence-continuity stitching after block ordering.

**Mechanism.** Walk the ordered body. Block P ends without terminal punctuation (or with a hyphen). The next block Q is a caption, footnote, heading, table, figure or pull quote, or starts with a capital while P dangles. Within the next four blocks a block R starts with a lower-case letter, or completes P's hyphenated word. Move Q up to R-1 after R. Guards: never cross a heading that R sits under; never move a footnote definition above its marker; one move per gap.

**Failure group and size.** F6: 59 split snippets (35 multi-column, 13 tiny text, 11 old scans), less the paragraph-sized interposals that belong to idea 10; 25 to 45 checks.

**Cost.** 4 to 6 hours.

**One-hour test.** For the 59 split snippets print P's last three words, the interposed text's length and kind, and R's first three words; count those fitting the rule; apply the move by text surgery on the markdown and rerun all checks for those pages to see the collateral.

**Strongest objection.** References written by a vision model often place the caption exactly where we did, and the 17 true order errors show sidebars where a lower-case resumption is ambiguous.

### 6. Typewriter grids

**Po and movement.** Po: every page is a table. Special circumstance: when every character has the same width, the page really is a grid.

**Concept.** Monospaced blocks become a character grid; grid columns blank on every row are the separators.

**Mechanism.** For a block where at least 95% of characters share one advance width (PyMuPDF's monospace flag, or measured): column index = round((x0 - block.x0) / pitch); build the rows-by-columns grid; a grid column that is blank, `|` or `:` in every data row separates cells; heading rows are the rows above the first numeric row, stacked headings joined; emit a markdown table, HTML when a heading spans.

**Failure group and size.** Tables: 3 pages, 10 checks (F10: ff19f6fe_pg4 at mono share 1.0 with all five cells present and a wrong table; 26076dc3_pg3 at 0.96), plus the census printout the pack names if it is monospaced.

**Cost.** 3 to 4 hours.

**One-hour test.** Print the character grid of those two pages from the raw text layer and check that the blank columns fall between the reference's cells and that the nine failing cells land in separate grid cells.

**Strongest objection.** Ten checks is 0.12 overall points; the pack's 70 "present but unstructured" checks are mostly proportional fonts (forms, keys, attendance lists) where no grid exists.

### 7. Ink accounting

**Po and movement.** Po: the output judges the input. Our output is a claim about the page; the page can be asked whether the claim covers all its ink. Difference from picture OCR: that looks where images are; this looks where claims are not.

**Concept.** Leftover ink is unread text: vector-outline text, screenshots, picture tables, sideways tables, figure labels.

**Mechanism.** Render at 150 dpi in grey; paint white every glyph box the text layer or accepted OCR claims, every photographic image (high colour variance) and every ruling; threshold; in each remaining connected region, a horizontal projection finds row bands of text-like height (0.5 to 3 times body size); a region with at least three rows is OCR'd at native resolution; lines are accepted by the existing numeric-rescue or language-like rule; if the rows share white channels, hand them to the unruled-table finder; otherwise place the block at its reading position, provenance `ocr-leftover`.

**Failure group and size.** Tables: the pack's 46 picture-text checks and the 11 no-text-layer table pages (F10); some multi-column figure text. Realistic 15 to 40 checks.

**Cost.** 6 to 8 hours.

**One-hour test.** Compute the leftover-ink fraction for the 23 failing table pages with under 50 characters or no table in the output, and for 20 passing table pages; the idea survives if the distributions separate (say above 3% against under 0.5%).

**Strongest objection.** Charts, logos, handwriting and photos are leftover ink too, so the yield rests on the OCR gate, and the pack's picture-OCR trial gained four checks; the new ground (vector text, numeric tables, native resolution) may still be small.

### 8. Say what you can read

**Po and movement.** Po: the empty file is the best answer. Its positive aspect is honesty. Focus on the difference between "empty" and "partial with a warning": nothing is invented in either.

**Concept.** Line-level acceptance on pages the page-level gate rejects.

**Mechanism.** When the gate rejects, keep lines with confidence at least 0.92, at least three tokens, every token a list word, number or initial, and no token repeated three times; write them in reading order; front matter `truedoc.partial_read: {kept: n, of: m}` and a warning; no note in the body (that would be invented text).

**Failure group and size.** Baseline: the 71 empty pages (0.6 overall points at most); old-scan presence checks on typed letters with handwritten parts, unknown, perhaps 20 to 60.

**Cost.** 2 to 3 hours, and the owner's decision: this amends D008.

**One-hour test.** Run the engine on the 71 empty pages, dump per-line confidence and tokens, count pages with at least one qualifying line, and read ten of them by eye for junk.

**Strongest objection.** "Dear Sir, 14 May 1923" alone on a page of unread handwriting can mislead a reader unless the warning is prominent; the owner chose empty files for a reason, and the score gain is capped.

### 9. Plain maths in prose

**Po and movement.** Po: the formula is prose. When a formula is only letters, digits and an equals sign, the reader sees prose. Special circumstance: multi-column pages with `$k=2$` inline.

**Concept.** Write trivial inline maths as the page's characters with the page's spacing.

**Mechanism.** An inline maths run whose LaTeX has no backslash, `^`, `_`, `{` or `}`, at most one operator, on a page with no display formula, is written plain with a space either side of the operator when the glyph gap is at least 0.2 em.

**Failure group and size.** Multi-column: 17 snippets carry a `$` in our aligned text (F5), the pack counts 11; 8 to 15 checks.

**Cost.** 1 to 2 hours.

**One-hour test.** Apply the rewrite by regex to the affected outputs and rerun the checker for those pages and for every arXiv page's maths checks (the collateral test).

**Strongest objection.** On arXiv pages the same run may be a maths check that needs the `$`; hence the "no display formula on the page" restriction, which is a heuristic.

### 10. Each column is its own page

**Po and movement.** Po: the column is a lie. If there were no columns, only narrow pages side by side, OCR would read each in order and never glue lines across a gutter.

**Concept.** Find gutters from ink before OCR; OCR each column strip separately.

**Mechanism.** On a page without a text layer (and as a check on hidden-layer pages): render at 100 dpi; the body band is the rows with ink; smooth the column ink profile; gutters are white valleys at least one em wide running at least 60% of the body height; if any, OCR each strip separately (idea 2's tiles can follow the strips); read strips left to right, with full-width elements peeled first by the existing order stage.

**Failure group and size.** The paragraph-sized interposals in F6 (17_pg86 with three splits, 11_pg146) and order errors on OCR pages: 10 to 30 checks.

**Cost.** 4 to 6 hours.

**One-hour test.** On 17_pg86, 17_pg17 and 11_pg146 compute the ink profile, print the valleys, and list the OCR boxes that straddle them.

**Strongest objection.** Run 46's voted column cuts already do this from boxes on hidden layers; the new ground is only no-text pages and boxes that straddle a gutter, and headlines and rules disturb the profile.

## Best bet

**Idea 1, gaps from ink.** The failure is measured, not guessed (96 snippets wrong only in spacing and punctuation, 29 in spacing alone, F5); the mechanism is demonstrated on a real line (F4: four of five image gaps are the reference's word gaps); the checks it touches are the most valuable per check (F8); it invents nothing (a space is white on the page); and the same rendered line strips are the foundation for ideas 3 and 4 later. Flip-fact: if the one-hour test recovers fewer than 10 of the 29 spacing-only snippets, the gaps are unmeasurable at newspaper resolution and the idea shrinks to the OCR-table half (F3). Idea 2 is the cheapest experiment (an afternoon, F1 is a hard fact) and is independent, so it can run first while idea 1 is built.

## Claims in the evidence pack I doubt

1. "Our own OCR read of those pages is not better than the hidden layer (13 of 66 strings found against the layer's 9)." As written, ours found more. The conclusion holds only for whole-page replacement, and the 17_* clippings in that set were read at half their stored resolution (F1), so the trial was handicapped. Token-level merging (idea 3) is untested.
2. "Vector-outline text: nothing to read." Nothing in the text layer; the ink is on the page (idea 7).
3. Tables: "152 cell not found, 75 relation errors." I find 92 failing checks on 48 pages where every failing cell's text is present and the output has a table (F10, an upper bound); the relation share may be nearer 40% than 33%.
4. "52 sentences broken at a block boundary, no single pattern." I count 35 in multi-column, 59 in all (F6), and the largest interposals are whole paragraphs: column interleaving on OCR pages, which is one pattern with one fix (idea 10).
5. "The rest are pages we do read, with many wrong characters." True, but 84 of the 97 old-scan pages with failures were read at 77% or less of their stored size (F1); some of the wrongness is ours.
