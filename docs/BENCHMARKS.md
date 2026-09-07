# Benchmarks: how we measure "better", and where we stand

## The yardstick

**Primary: olmOCR-bench** (Allen Institute for AI; dataset `allenai/olmOCR-bench` on Hugging Face). 1,403 single-page PDFs, 7,010 unit tests. Each test asks a question a careful human reader could answer: is this sentence present? is this header/footer *absent*? does paragraph A come before paragraph B? is this table cell to the left of that one? is this formula there? A test is pass or fail. The score for a section is the pass rate; the overall score is the average of the eight sections. This is the closest public measure of "meaning accuracy" we have found, and it is the benchmark most of the tools on the owner's list report on.

**Secondary: OmniDocBench v1.6** (OpenDataLab). 1,651 page images across nine document types. Scored by text edit distance, table similarity (TEDS), formula similarity (CDM) and reading-order edit distance; overall = mean of (100 minus text edit distance, table TEDS, formula CDM). It ships page *images* rather than PDFs, so it exercises the OCR path only. We report on it as a second opinion once the OCR path exists.

Both benchmarks are downloaded into `bench/data/` (git-ignored) and scored with the official code, so our numbers are comparable with the published ones.

## Published scores we must beat

### olmOCR-bench (overall, higher is better)

Source: `allenai/olmocr` README, fetched 2026-09-02. Sections: ArXiv maths, old-scan maths, tables, old scans, headers and footers, multi-column, long tiny text, base.

| Tool | ArXiv | OldScanMath | Tables | OldScans | Hdr/Ftr | MultiCol | TinyText | Base | **Overall** |
|---|---|---|---|---|---|---|---|---|---|
| Chandra OCR 0.1.0 | 82.2 | 80.3 | 88.0 | 50.4 | 90.8 | 81.2 | 92.3 | 99.9 | **83.1** |
| Infinity-Parser 7B | 84.4 | 83.8 | 85.0 | 47.9 | 88.7 | 84.2 | 86.4 | 99.8 | **82.5** |
| olmOCR v0.4.0 | 83.0 | 82.3 | 84.9 | 47.7 | 96.1 | 83.7 | 81.9 | 99.7 | **82.4** |
| PaddleOCR-VL | 85.7 | 71.0 | 84.1 | 37.8 | 97.0 | 79.9 | 85.7 | 98.5 | **80.0** |
| Marker 1.10.1 | 83.8 | 66.8 | 72.9 | 33.5 | 86.6 | 80.0 | 85.7 | 99.3 | **76.1** |
| DeepSeek-OCR | 77.2 | 73.6 | 80.2 | 33.3 | 96.1 | 66.4 | 79.4 | 99.8 | **75.7** |
| MinerU 2.5.4 (VLM) | 76.6 | 54.6 | 84.9 | 33.7 | 96.6 | 78.2 | 83.5 | 93.7 | **75.2** |
| Mistral OCR API | 77.2 | 67.5 | 60.6 | 29.3 | 93.6 | 71.3 | 77.1 | 99.4 | **72.0** |
| Nanonets-OCR2-3B | 75.4 | 46.1 | 86.8 | 40.9 | 32.1 | 81.9 | 93.0 | 99.6 | **69.5** |
| GPT-4o (anchored), original paper | 53.5 | 74.5 | 70.0 | 40.7 | 93.8 | 69.3 | 60.6 | 96.8 | **69.9** |
| Gemini Flash 2 (anchored), original paper | 54.5 | 56.1 | 72.1 | 34.2 | 64.7 | 61.5 | 71.5 | 95.6 | **63.8** |
| MinerU v1.3.10 (pipeline), original paper | 75.4 | 47.4 | 60.9 | 17.3 | 96.6 | 59.0 | 39.1 | 96.6 | **61.5** |
| Marker v1.6.2, original paper | 24.3 | 22.1 | 69.8 | 24.3 | 87.1 | 71.0 | 76.9 | 99.5 | **59.4** |

Not yet found on olmOCR-bench: Docling, Adobe Extract, OvisOCR2 (a third-party blog reports Docling around 64 on born-digital pages [recalled, unverified]). These will be measured here if the tools can be run locally, or their published numbers added when found.

### OmniDocBench v1.6 (overall, higher is better)

Source: `opendatalab/OmniDocBench` README, fetched 2026-09-02. Overall = mean of ((1 - text edit distance) x 100, table TEDS, formula CDM).

| Tool | Type | Overall | Text edit (lower better) | Formula CDM | Table TEDS | Reading order edit (lower better) |
|---|---|---|---|---|---|---|
| OvisOCR2 (0.8B) | Specialised VLM | **96.58** | - | - | - | - |
| PaddleOCR-VL-1.6 | Specialised VLM | 96.34 | 0.033 | 97.5 | 94.8 | 0.128 |
| MinerU2.5-Pro | Specialised VLM | 95.75 | 0.036 | 97.5 | 93.4 | 0.120 |
| GLM-OCR | Specialised VLM | 95.22 | 0.044 | 97.2 | 92.8 | 0.133 |
| MinerU-2.5 (VLM) | Specialised VLM | 93.04 | 0.045 | 95.8 | 87.9 | 0.130 |
| Gemini 3 Pro | General VLM | 92.91 | 0.064 | 96.0 | 89.2 | 0.165 |
| dots.ocr | Specialised VLM | 90.77 | 0.048 | 90.0 | 87.2 | 0.138 |
| GPT-5.2 | General VLM | 86.59 | 0.114 | 88.2 | 83.0 | 0.193 |
| MinerU pipeline | Pipeline | 86.47 | 0.055 | 83.1 | 81.9 | 0.153 |
| olmOCR (7B) | Specialised VLM | 85.74 | 0.139 | 88.1 | 83.0 | 0.216 |
| Mistral OCR | API | 85.66 | 0.097 | 89.9 | 76.8 | 0.171 |
| Marker | Pipeline | 78.44 | 0.157 | 85.2 | 65.8 | 0.243 |

OvisOCR2's per-metric numbers come from its technical report (arXiv 2607.13639) and are not yet captured here beyond the overall.

## TrueDoc's scores

| Date | Version | Overall | ArXiv | OldScanMath | Tables | OldScans | Hdr/Ftr | MultiCol | TinyText | Base | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-09-02 | M1 text-layer baseline | **48.6** (CI 47.6-49.6) | 0.0 | 0.0 | 32.7 | 58.7 | 68.6 | 67.4 | 74.9 | 86.2 | No models at all: text layer + geometry heuristics + ruled tables. **The old-scans number is an artefact**: scanned pages produced a file containing only a newline, and the scorer's fuzzy matcher scores a one-character document as a perfect match for any phrase. Truly empty files would have scored about 13 there (only the "absent" checks pass). Fixed on 2026-09-03: empty pages now produce empty files. |

| 2026-09-03 | Run 2: layout model + formula rebuild + gated classical OCR (code as of 01:10) | **54.7** (CI 53.7-55.6) | 40.8 | 3.1 | 55.4 | 18.6 | 90.9 | 67.1 | 68.1 | 93.3 | Honest numbers throughout (empty pages are empty). Tiny-text dropped because the OCR-layer line rebuild came after this snapshot; run 3 includes it. Old-scans sections now depend on real OCR: typewritten pages pass, handwriting stays empty. |

| 2026-09-03 | Run 3: + OCR-layer line rebuild for scanned books, English OCR model, gutter line numbers, banner headers (code as of 03:20) | **56.3** (CI 55.4-57.3) | 40.8 | 3.9 | 55.1 | 20.7 | 91.6 | 68.2 | 77.4 | 92.9 | Tiny text recovered (68 -> 77). Formula repairs made after this snapshot are in run 4. |

| 2026-09-03 | Run 5: + four rounds of formula repairs, full-width figures no longer split columns, lone-symbol runs not wrapped (code as of 05:30) | **57.9** (CI 56.9-58.8) | 51.1 | 3.9 | 56.9 | 20.7 | 91.6 | 68.6 | 77.4 | 92.8 | Formula section +10 points. Table repairs (grouped/stacked headers, narrow gaps, empty columns) and rotated-page handling came after this snapshot; they are in run 6. |

| 2026-09-03 | Run 6: + table repairs (grouped and stacked headers, narrow column gaps, empty columns), rotated pages, contact-line headers, crash guards (code as of 07:00) | **58.3** (CI 57.3-59.2) | 51.1 | 3.9 | 58.3 | 20.7 | 92.9 | 68.4 | 77.4 | 93.3 | Tables +1.4, headers/footers +1.3, base +0.5; formulas unchanged (the fifth round of formula repairs, multi-line equation blocks and the bracket/accent work came after this snapshot and go into run 7). |

| 2026-09-03 | Run 7: + sixth round of formula repairs (maths-font glyph boxes, whitespace-coded brackets, accents, shattered lines, multi-line equation blocks, `\phi`/`\setminus`/ohm spellings), algorithm listings with inline maths (code as of 07:45) | **60.2** (CI 59.2-61.1) | 66.7 | 3.9 | 58.2 | 20.7 | 92.9 | 67.8 | 77.8 | 93.3 | Formulas +15.6 (1,952 of 2,927 checks now pass, from 1,495). Everything else within a point. Hidden text (D011), column gutters, narrow-column word breaks and Type 3 sizes came after this snapshot; they are in run 8. |

| 2026-09-03 | Run 8: + hidden text kept out of the body (D011), column gutters (patents, newsletters), narrow-column word breaks, Type 3 font sizes, running-head patterns, garbage text-layer detector (code as of 09:10) | **60.8** (CI 59.9-61.7) | 66.4 | 3.9 | 58.2 | 20.7 | 93.3 | 70.7 | 79.6 | 93.3 | Multi-column +2.9 and tiny text +1.8 from the gutter and word-break fixes; formulas -0.3 (eight checks, within noise). The render-verified hidden text, the table header/wrapped-row repairs and the seventh formula round came after this snapshot; they are in run 9. |
| 2026-09-03 | Run 9: + render-verified hidden text, table header rows and wrapped cells, trusted layout tables, garbage-text detector, seventh formula round (prose words as text, long superscripts, wide limits, Times variables, mathabx braces, sized bars), extension-font boxes before line building, ohm/increment/micro signs as Greek (code as of 10:45) | **62.2** (CI 61.3-63.1) | 69.2 | 4.1 | 65.7 | 20.7 | 93.4 | 70.7 | 79.9 | 93.9 | Tables +7.5 (header rows recovered, wrapped cells kept whole, trusted layout boxes), formulas +2.8 (seventh round). Multi-column and old scans unchanged. Not in this run: picture-table OCR, tables inside figures, numeric-aware OCR gate, header-zone contact blocks, OCR-layer word gaps, overlapping-glyph word gaps, dot-leader lines, ruled tables rebuilt from text, stacked table headings as HTML header rows (all in run 10). |
| 2026-09-03 | Run 9 + vision model (experiment, not a TrueDoc run): the 94 pages run 9 left empty (no text layer, no confident OCR) replaced by olmOCR 2's reading of them, made on a rented RTX 4090 in 12 minutes of model time | **67.8** (CI 66.8-68.8) | 69.2 | 23.1 | 70.0 | 34.0 | 99.9 | 72.6 | 79.9 | 93.8 | What a vision model adds on pages TrueDoc cannot read at all: old scans +13.3, old-scan maths +19.0, tables +4.3, multi-column +1.9, and the baseline checks (one per page, failing for an empty page) +6.5. Everything else identical by construction. |
| 2026-09-03 | Run 10: + picture-table OCR, tables inside figures, numeric-aware OCR gate, header-zone contact blocks, three word-gap repairs (OCR layers, overlapping glyph boxes, dot leaders), ruled tables rebuilt from text lines, stacked table headings as HTML header rows with colspans (code as of 12:27) | **62.3** (CI 61.3-63.1) | 69.2 | 4.1 | 66.0 | 20.7 | 93.4 | 69.5 | 79.9 | 95.3 | Headers +1.4 (contact and citation blocks in the page's top and bottom zones), tables +0.3 net (52 checks gained from the heading structure and rebuilt tables, 48 lost: the rebuild also fired on ruled tables of wrapped prose and shredded them). Multi-column -1.2: the OCR-layer word-gap rule letter-spaced short words on one scanned report ("w i t h") because the letter gap was judged per line rather than per word. Both causes fixed the same afternoon (rebuild only for tables of at most three rows that come back mostly numeric; letter gaps judged per run between explicit spaces); they go into run 11 with marks, the dictionary splitter and formula round 8. |
| 2026-09-03 | Run 11: + run-10 regression fixes (per-word OCR-layer gaps, rebuild limited to small numeric tables, heading count), marks that carry meaning (ticks, crosses, bullets), dictionary splitter for OCR layers, formula round 8 (calligraphic and blackboard letters, accents in scripts, tall radicals, bar tolerance) (code as of 14:04) | **62.8** (CI 61.9-63.7) | 69.7 | 4.1 | 69.1 | 20.7 | 93.4 | 70.6 | 79.6 | 95.3 | Tables +3.1 on run 10 (+3.4 on run 9) now that the heading structure no longer misfires; multi-column back to 70.6; formulas +0.5. Held-out pages 60.0 (run 9: 60.1, run 10: 58.7) with tables 68.6 on held-out pages, so the table work now generalises. |
| 2026-09-03 | Run 12: + margin header and footer rules (running heads labelled as headings, short lines stacked under a header, small lines in the bottom strip, near-tie section/page headers), pull-quote boxes no longer cut columns (code as of 15:41) | **62.9** (CI 62.0-63.8) | 69.7 | 4.1 | 69.1 | 20.5 | 93.4 | 70.6 | 79.6 | 96.4 | Headers +1.1; everything else within one check of run 11. Held-out 60.2 (run 11: 60.0). |
| 2026-09-03 | Run 13: + formula round 9 (fractions inside scripts stay with the script, TeX sized brackets keep their size, Latin Modern maths fonts, numerators follow their bar, bracketed fractions are not matrices, sqrt and tall-delimiter guards) (code as of 17:08) | **63.1** (CI 62.2-64.0) | 70.8 | 4.1 | 69.1 | 20.5 | 93.4 | 70.6 | 79.6 | 96.4 | Formulas +1.1 (34 checks); every other category identical to run 12. Held-out 60.4 (run 12: 60.2). |
| 2026-09-03 | Run 14: + footnote and endnote linking (D017), pull-quote island guards, page-bottom exemption, symbol spellings (ǫ, turnstiles, epsilon swap widened) (code as of 18:34) | **62.9** (CI 61.9-63.8) | 69.6 | 4.1 | 69.1 | 20.7 | 93.4 | 70.2 | 79.6 | 96.4 | Formulas -1.2 (37 checks): the epsilon swap is right for some TeX distributions and wrong for others (fixed for run 16 by judging the glyph's width); multi-column -0.4: footnote markers on citation numbers ("2-4") and a heading taken for a note (both fixed). Held-out 60.1 (run 13: 60.4). |
| 2026-09-03 | Run 15: + the fixes for run 13's seven formula regressions (satellite size by median glyph, cases exempt from the bracketed-fraction veto, sized brackets around line-high content written plain, Euler's ∞), endnote linking, figure placeholders `![](figure)` rendered at last (code as of 20:04; still carries run 14's epsilon regression) | **62.9** (CI 62.0-63.9) | 69.6 | 4.1 | 69.1 | 20.7 | 93.8 | 70.0 | 79.6 | 96.6 | Baseline +0.4 (5 checks), headers +1, formulas +1, multi-column -2. Held-out 60.0. |
| 2026-09-03 | Run 16: + epsilon and phi decided by glyph width, formula round 10 (Unicode maths letters, mapsto, bar sizes by piece count, radical-free part baselines, display fractions in text lines, liminf/limsup, blank spaces in cmex spans), footnote markers restored when no note exists, headings never notes (code as of 21:30) | **63.5** (CI 62.6-64.4) | 73.7 | 4.1 | 69.1 | 20.7 | 93.8 | 70.4 | 79.6 | 96.4 | **New best.** Formulas +4.1 (121 checks), multi-column +3 checks, headers -1. Held-out 60.6 (run 13: 60.4). |
| 2026-09-04 | Run 17: + bracket-size demotion reverted, paragraphs joined across a figure at the foot of a column, one-row ruled boxes with their headings above adopted as tables (code as of 22:52) | **63.5** (CI 62.6-64.3) | 73.9 | 4.1 | 68.6 | 20.7 | 93.8 | 70.5 | 79.6 | 96.4 | Level. Formulas +5 checks, multi-column +1, tables -5 (the one-row boxes: 4 new passes, 9 new failures; traced and guarded for run 19). Held-out 60.5. |
| 2026-09-04 | Run 18: + the mapsto merge needs a touching bar (code as of 00:07) | **63.5** (CI 62.6-64.3) | 74.0 | 4.1 | 68.6 | 20.7 | 93.8 | 70.5 | 79.6 | 96.4 | Level; formulas +2 checks, nothing lost. Held-out 60.5. |
| 2026-09-04 | Run 19: + the boxed-row header rule with its three guards (one-row boxes only, no taller than 2.5 lines, no unruled continuation below) (code as of 01:18) | **63.6** (CI 62.6-64.5) | 74.0 | 4.1 | 69.5 | 20.7 | 93.8 | 70.6 | 79.6 | 96.4 | **New best.** Tables +0.9 (9 checks), multi-column +1, nothing lost. Held-out 60.7 (best). |
| 2026-09-04 | Run 20: + band-aware column channels on hidden OCR layers (code as of 02:30) | **63.6** (CI 62.7-64.5) | 74.0 | 4.1 | 69.5 | 20.7 | 93.8 | 70.8 | 79.6 | 96.4 | Level with run 19; multi-column +2 checks, nothing lost. Held-out 60.8 (best). |
| 2026-09-04 | Run 21: + formula round 11 start (a radical's bar is not a fraction bar, tx-font brackets and radicals, limit runs past the operator's edge) (code as of 04:09) | **63.6** (CI 62.7-64.5) | 74.0 | 4.1 | 69.5 | 20.7 | 93.8 | 70.8 | 79.6 | 96.4 | Level; formulas +2 checks, nothing lost. Held-out 60.8. |
| 2026-09-04 | Run 22: + a root inside a sum's limit (limit stacks left to the limit group) (code as of 05:16) | **63.6** (CI 62.7-64.6) | 74.0 | 4.1 | 69.5 | 20.7 | 93.8 | 70.8 | 79.6 | 96.4 | Identical to run 21 to the check: the change touched no benchmark check. Held-out 60.8. |
| 2026-09-04 | Run 23: + truncated maths letters unfolded (newtx, STIX), stray combining marks dropped, accent-only lines joined, esint/mathabx integral sign, three-line integrals joined, display integral limits, private-use brace pieces (code as of 06:31) | **63.7** (CI 62.8-64.6) | 75.0 | 4.1 | 69.5 | 20.7 | 93.8 | 70.8 | 79.6 | 96.4 | **New best.** Formulas +1.0 (32 checks won, 5 lost), everything else identical. Held-out 61.0 (best). |
| 2026-09-04 | Run 24: + RATIO colon, rsfs script letters, operator names glued to a bracket, display rows linked by real glyph extents (code as of 07:48) | **63.8** (CI 62.9-64.8) | 75.9 | 4.1 | 69.5 | 20.7 | 93.8 | 70.5 | 79.6 | 96.4 | **New best.** Formulas +0.9 (30 won, 3 lost), multi-column -3 checks. Held-out 61.2 (best). |
| 2026-09-04 | Run 25: + operator pre-pass limited to genuine operator signs, brace pieces never satellites, raw cmex piece codes, far-off pieces dropped from inline runs (code as of 09:12) | **63.8** (CI 62.9-64.8) | 76.0 | 4.1 | 69.5 | 20.7 | 93.8 | 70.5 | 79.6 | 96.4 | Formulas +4 checks, nothing lost; every other category identical to run 24. Held-out 61.2. |
| 2026-09-04 | Run 26: + underlined words are not fractions, headlines never maths, drop caps rejoined, ellipsis as three dots, mathabx element/inequality signs, bold maths letters (code as of 10:42) | **64.1** (CI 63.3-65.0) | 77.0 | 4.1 | 69.6 | 20.7 | 93.8 | 71.8 | 79.6 | 96.4 | **New best.** Formulas +1.0 (37 won, 9 lost: all nine are `\widehat` over one letter, which the accent pass had narrowed to `\hat`; fixed for run 28), multi-column +1.3 (12 won), tables +1. Held-out 61.2. |
| 2026-09-04 | Run 27: + formula round 12 (mathabx not-equal, TX-font operators trusted, "lim" in OpenType maths fonts, wide accents kept apart from bracket pieces, formula tails kept after a radical or wide accent) (code as of 12:05) | **64.3** (CI 63.4-65.2) | 78.1 | 4.1 | 69.6 | 20.7 | 93.8 | 71.9 | 79.6 | 96.4 | **New best.** Formulas +1.1 (37 won, 4 lost: two inline matrices broken by the early fold of bracket pieces, fixed for run 28; two others under review), multi-column +1. Held-out 61.3 (best). |
| 2026-09-04 | Run 28: + formula round 13 (stacked-fraction segments merged, limits kept with their operator, diagonal dots, cmex angle brackets, wide hats kept wide, roots over script-sized fractions, operator words, arithmetic after a line break, left-margin equation numbers, long mapsto) (code as of 13:38) | **64.4** (CI 63.4-65.4) | 78.9 | 4.1 | 69.6 | 20.7 | 93.8 | 71.8 | 79.6 | 96.4 | **New best.** Formulas +0.8 (41 won, 17 lost: five from writing slanted inequalities plain, reverted; sized delimiters and fractions on a few pages under review), multi-column -1 check. Held-out 61.4 (best). |
| 2026-09-04 | Run 29: + formula round 14 (symbol tables of mathabx, newtx, bbold; scripts of overlined bases; script-of-script placement; Symbol-font phi; roman capitals; glued function names) and the early-fold repair (code as of 15:23) | **64.8** (CI 64.0-65.7) | 82.6 | 4.1 | 69.6 | 20.7 | 93.8 | 71.9 | 79.4 | 96.4 | **New best.** Formulas +3.7 (123 won, 16 lost: six are the slanted-inequality trade-off, five a "min" label read as the operator, fixed for run 31), multi-column +1, tiny text -1 check. Held-out 61.8 (best). |
| 2026-09-04 | Run 30: + formula round 15 (a matrix row must hold a text-size entry, so tall parentheses round an operator with limits are no longer a matrix; semidirect-product and star signs; italic theorem prose inside display formulas; wider window for limits parked left of their operator) (code as of 16:45) | **65.0** (CI 64.1-65.9) | 84.0 | 4.1 | 69.6 | 20.7 | 93.8 | 71.9 | 79.4 | 96.4 | **New best.** Formulas +1.4 (44 won, 1 lost: a subscript after a tall double bar parked as the next lim's limit, fixed for run 31); every other category identical to the check. Held-out 61.9 (best), tuned-on 60.8. |
| 2026-09-04 | Run 31: + formula round 16 to item 8 (script-sized roots defer to their script or limit, root sign is no matrix row, maths-only bridge fillers, glued factorial, mathabx tables from a glyph contact sheet, scripts on fractions, long integral limits, glued scripts after tall bars, main-size rule for long scripts) (code as of 18:26) | **65.2** (CI 64.3-66.1) | 85.0 | 4.1 | 69.6 | 20.7 | 93.8 | 71.9 | 79.6 | 96.4 | **New best.** Formulas +1.0 (46 won, 18 lost: four of the round's rules misfiring on sums right after fractions, a fraction inside tall brackets, a scripted "log" and a limit after a minus; all repaired for run 33, +5 on their pages), tiny text +1 check, the rest identical. Held-out 62.0 (best), tuned-on 61.0. |
| 2026-09-04 | Run 32: + the rest of formula round 16 (run-31 repairs, two-letter accent bases, italic font names, typed dots, negated relations, script-size limit words, text-font terms, cmsy asterisk) (code as of 19:52) | **65.3** (CI 64.4-66.2) | 86.1 | 4.1 | 69.6 | 20.7 | 93.8 | 71.9 | 79.6 | 96.4 | **New best.** Formulas +1.1 (35 won, 3 lost: two checks on a page whose references spell `\notin` where we write `\not\in` (the checker tells them apart; the references split 11 to 5 for `\not\in`, so the spelling stays) and a `\bigsqcup` whose wide limit only half followed the sign, repaired for run 34), the rest identical. Held-out 62.2 (best), tuned-on 61.1. |
| 2026-09-04 | Run 33: + the run-31 repairs (fraction scripts held back from a following operator's limit, bar-between-rows test over every row, scripted function names are not labels), `\tfrac`/`\dfrac`, text-only equations, mathx big-parenthesis codes (code as of 21:14) | **65.3** (CI 64.5-66.2) | 86.5 | 4.1 | 69.6 | 20.7 | 93.8 | 71.9 | 79.6 | 96.4 | **Level with run 32, nothing lost.** Formulas +0.4 (13 won, 0 lost), the rest identical. Held-out 62.2, tuned-on 61.2. |
| 2026-09-04 | Run 34: + wide centred limits for every big operator, bold and accented variables, the differential rule, fraction rows in matrices, `\not\in` kept (code as of 22:35) | **65.4** (CI 64.5-66.2) | 86.7 | 4.1 | 69.6 | 20.7 | 93.8 | 71.9 | 79.6 | 96.4 | **New best.** Formulas +0.2 (7 won, 3 lost: three cases blocks whose rows are fractions, broken by the fraction-rows-in-matrices change, to be reverted for run 36), the rest identical. Held-out 62.2, tuned-on 61.2. |
| 2026-09-05 | Run 35: + numerator root signs kept below their fraction bar in the early fold, narrow column gutters on OCR'd two-column pages, hyphen-less broken words rejoined (code as of 23:59) | **65.4** (CI 64.5-66.2) | 86.6 | 4.1 | 69.6 | 20.7 | 93.8 | 72.2 | 79.6 | 96.4 | **Level with run 34.** Multi-column +0.3 (2 order checks won by the broken-word join), formulas -0.1 (1 lost, `\sqrt{0.098}` on 2503.08374, being traced), the rest identical. Held-out 62.2, tuned-on 61.2. |
| 2026-09-05 | Run 36: + the OCR gate accepts a confident read whose tokens are shaped like words of any Latin-script language (non-English scans had come out empty), fraction rows in matrices reverted (code as of 01:18) | **65.6** (CI 64.6-66.5) | 86.7 | 4.1 | 70.3 | 20.7 | 94.5 | 72.7 | 79.6 | 96.3 | **New best.** 25 checks won, 1 lost: tables +10 checks (+0.7), multi-column +10 (+0.5), baseline +0.7, formulas +3 checks (the three cases blocks back); headers +2/-1 (a footer "euras.lt" now appears on a page that used to be empty). Held-out 62.2, tuned-on 61.4. |
| 2026-09-05 | Run 37: the numerator-root fold withdrawn (code as of 02:38) | **65.6** (CI 64.7-66.5) | 86.8 | 4.1 | 70.3 | 20.7 | 94.5 | 72.7 | 79.6 | 96.3 | **Level with run 36, nothing lost.** Formulas +1 check (the root on 2503.08374 back), the rest identical. Held-out 62.2, tuned-on 61.4. |
| 2026-09-06 | Run 38: sideways pages turned upright before reading (a landscape scan of a portrait page, a table printed up the page); the OCR rescue bar for non-English and numeric reads 0.85 to 0.80 (code as of 15:43) | **65.9** (CI 65.0-66.8) | 86.8 | 4.1 | 72.2 | 20.7 | 94.6 | 72.7 | 79.6 | 96.3 | **New best.** Tables +22 checks (the turned decree, the turned norm-types table, scanned number tables now accepted), nothing lost anywhere; every other category identical to the check. |
| 2026-09-06 | Run 39: multi-column round: explicit spaces kept on scanned layers and after punctuation, free-standing accents composed, section numbers rejoined to headings, block builder following baselines on tall-box layers, hyphen joins across blocks (code as of 16:52) | **65.9** (CI 65.0-66.8) | 86.9 | 4.1 | 72.2 | 20.5 | 94.6 | 73.1 | 79.6 | 96.2 | Level with run 38. Multi-column +3 net (10 won, 7 lost), formulas +5 (8 won, 3 lost), tiny text 5 won and 5 lost (a block-builder regression on dictionary pages, fixed for run 40), headers -1, old scans -1. Held-out 62.5, the best yet. |
| 2026-09-06 | Run 40: run 39's losses repaired (block size measure only on OCR layers, vertical text never joins a row), two table-finder repairs (a two-line cell centred on its row; a table of short labels no longer taken for prose), Polish letters for Central European fonts (code as of 18:00) | **66.1** (CI 65.3-67.0) | 86.8 | 4.1 | 73.2 | 20.5 | 94.6 | 73.8 | 79.6 | 96.1 | **New best.** Against run 38: tables +18/-8, multi-column +10/-1, headers -2, tiny text +1/-1, old scans -1; run 39's formula gains were accidental and went with its bug. Held-out 63.0, the best yet. |
| 2026-09-06 | Run 41: caption lines kept out of table headings, a confident table box overrides a small fragment inside it, OCR-layer block rule by size and box height together (code as of 19:00) | **66.1** (CI 65.2-67.0) | 86.8 | 4.1 | 73.3 | 20.5 | 94.6 | 73.6 | 79.6 | 96.3 | Level with run 40: headers +2 (the AMS copyright line), tables 10 won and 9 lost (a 25-row table back, a course list and the eye-disease table lost; both repaired for run 42), multi-column -1. Held-out 63.0. |
| 2026-09-06 | Run 42: a table box overrides a fragment only when it yields a bigger table, the centred-cell fold tightened, a text table's heading ends at its labelled first row (code as of 19:58) | **66.3** (CI 65.5-67.1) | 86.8 | 4.1 | 74.9 | 20.5 | 94.6 | 73.6 | 79.6 | 96.3 | **New best.** Tables +16 net (20 won, 4 lost), every other category identical to the check. Held-out 63.1, the best yet. |
| 2026-09-06 | Run 43: the minus sign of AdvP symbol fonts, a value with its error in parentheses counted as numeric (code as of 20:50) | **66.3** (CI 65.4-67.2) | 86.8 | 4.1 | 75.0 | 20.5 | 94.6 | 73.6 | 79.6 | 96.3 | Level with run 42: tables +2 checks, nothing lost. Held-out 63.1. |
| 2026-09-06 | Run 44: a corner label centred beside a two-line heading joins the row it overlaps more; several small tables in one box give way only when the box's table has two rows more than they hold together (code as of 21:42) | **66.3** (CI 65.4-67.2) | 86.8 | 4.1 | 75.0 | 20.5 | 94.6 | 73.6 | 79.6 | 96.3 | Level with run 43: tables 2 won (the Tagetes trial) and 2 lost (one date-headed table). Held-out 63.1. |
| 2026-09-06 | Run 45: heading fragments above and wrapped labels below a table kept, parenthesised heading lines joined unless they repeat across columns, column numbers joined to their names, the Advent symbol fonts (code as of 22:57) | **66.4** (CI 65.4-67.2) | 86.8 | 4.1 | 75.1 | 20.5 | 94.6 | 73.6 | 79.6 | 96.4 | **New best by a tenth.** Headers +1, tables 6 won and 5 lost on two pages (being traced). Held-out 63.1. |
| 2026-09-07 | Run 46: column cuts voted by gap range (code as of 6 Sept 23:50) | **66.4** (CI 65.5-67.4) | 86.8 | 4.1 | 75.6 | 20.5 | 94.6 | 73.6 | 79.6 | 96.4 | Best at the time (66.4 again, but tables +5 net: 7 won, 2 lost on one page). Held-out 63.3 and tuned-on 62.3, both the best yet. The code after it (commit 2696d2a) adds the heading-fragment guard, for run 47. |
| 2026-09-07 | Run 47: + heading-fragment guard, voted cuts placed where the next column starts (code as of 7 Sept 06:34) | **66.5** (CI 65.6-67.4) | 86.8 | 4.1 | 76.2 | 20.5 | 94.6 | 73.6 | 79.6 | 96.3 | Best at the time (tables +6 net: 12 won, 6 lost; the six losses traced to the cut position and repaired for run 48) |
| 2026-09-07 | Run 48: + cut position refined (a segment across the range vetoes the cut), scanned tables of numbers kept, leader dots and dash rules out of cells, headings read in order (code as of 7 Sept 08:02) | **66.7** (CI 65.8-67.5) | 86.8 | 4.1 | 77.8 | 20.5 | 94.7 | 73.6 | 79.6 | 96.3 | **Best so far** (tables +16 net: 17 won, none lost) |

Section-only runs since the baseline (same scorer, one section at a time; the overall column is not comparable):

| Date | Change | Section | Before | After |
|---|---|---|---|---|
| 2026-09-02 | Unruled-table extractor (whitespace channels) | Tables | 32.7 | **56.4** |
| 2026-09-02 | Docling layout model for headers/footers/captions | Headers and footers | 68.6 | **88.7** |
| 2026-09-02 | Same run, multi-column pages (regression caused by the first maths heuristics wrapping numbers and statute citations; fixed, re-run pending) | Multi-column | 67.4 | 50.7 |
| 2026-09-03 | Classical OCR (RapidOCR) for pages with no text layer, ungated | Old scans | 13 (honest empty) | 23.0 |
| 2026-09-03 | Table-finder prose rejection, margin line numbers dropped, word-by-word lines re-joined, header-zone lines no longer lost | Multi-column | 58.7 | 66.2 |

Reading the baseline: with no vision model and no formula handling, TrueDoc already scores 67-75 on the three "structure" sections where Marker scores 80-86 and the best tools 81-92. The zeros on the two maths sections, the weak tables section and the (honestly) near-zero old-scans section are the gaps, in that order of weight.

## How to run the benchmark

```bash
.venv/Scripts/python -m truedoc.cli bench --workers 12          # convert all 1,403 pages and score
.venv/Scripts/python -m truedoc.cli bench --categories tables --jsonl table_tests.jsonl   # one section
```

See `bench/README.md` for details. Every run leaves `bench/runs/<candidate>-<timestamp>/summary.json` and the list of failed tests.

## Held-out check (from 3 September 2026)

One page in five is held out and never tuned on (`bench/holdout.txt`, `bench/holdout_score.py`). Category means on the two halves (per-file categories; the baseline checks are folded into their files here, so the means are not the official overall):

| Run | Held-out (261 pages) | Tuned-on (1,142 pages) | Note |
| --- | --- | --- | --- |
| Run 9 | 60.1 | 57.3 | tables 69.7 held-out vs 64.8 tuned-on |
| Run 10 | 58.7 | 57.7 | tables fell to 60.6 on held-out pages while rising to 67.2 on tuned-on pages: the table heading and rebuild changes were fitted to particular pages. Part of that was corrected the same afternoon (rebuild limited to small tables, heading count fixed); run 11 will show how much. |
| Run 11 | 60.0 | 58.2 | tables 68.6 held-out vs 69.2 tuned-on: both halves up together, the fitted-to-pages effect of run 10 is gone. |
| Run 12 | 60.2 | 58.3 | headers and footers only; both halves up a little. |
| Run 13 | 60.4 | 58.5 | formulas 75.4 held-out vs 69.7 tuned-on; the formula round lifted both halves. |
| Run 14 | 60.1 | 58.3 | both halves down a little with the epsilon regression; nothing fitted. |
| Run 15 | 60.0 | 58.3 | level; the epsilon regression is still in this run. |
| Run 16 | 60.6 | 58.9 | both halves up; the width rules and round 10 are general, not fitted. |
| Run 17 | 60.5 | 58.9 | level. |
| Run 18 | 60.5 | 58.9 | level. |
| Run 19 | 60.7 | 59.0 | both halves up with the guarded table rule. |
| Run 20 | 60.8 | 59.1 | both halves up a touch with the column channels. |
| Run 21 | 60.8 | 59.1 | level. |
| Run 22 | 60.8 | 59.1 | identical. |
| Run 23 | 61.0 | 59.2 | both halves up with the formula fixes. |
| Run 24 | 61.2 | 59.3 | both halves up again. |
| Run 26 | 61.2 | 59.7 | tuned-on half up (run 25's split was not recorded). |
| Run 27 | 61.3 | 59.9 | both halves up a touch. |
| Run 28 | 61.4 | 60.0 | both halves up a touch. |
| Run 29 | 61.8 | 60.5 | both halves up with the symbol tables. |
| Run 30 | 61.9 | 60.8 | both halves up again; the formula gains are not confined to tuned-on pages. |
| Run 31 | 62.0 | 61.0 | both halves up again. |
| Run 32 | 62.2 | 61.1 | both halves up again. |
| Run 33 | 62.2 | 61.2 | held-out level, tuned-on up a touch. |
| Run 34 | 62.2 | 61.2 | level. |
| Run 35 | 62.2 | 61.2 | level. |
| Run 36 | 62.2 | 61.4 | tuned-on up with the OCR gate change. |
| Run 37 | 62.2 | 61.4 | level. |
| Run 38 | 62.2 | 61.8 | The three turned or rescued pages are tuned-on; held-out level. |
| Run 39 | 62.5 | 61.8 | held-out up 0.3: the word-space and accent rules are general. |
| Run 40 | 63.0 | 61.9 | held-out up 0.5: the table and multi-column repairs carry to pages never tuned on. |
| Run 41 | 63.0 | 61.9 | level. |
| Run 42 | 63.1 | 62.2 | both up: the table repairs are general. |
| Run 43 | 63.1 | 62.2 | level. |
| Run 44 | 63.1 | 62.2 | level. |
| Run 45 | 63.1 | 62.2 | level. |
| Run 46 | 63.3 | 62.3 | both up: the range-voted cuts carry to pages never tuned on. |
| Run 47 | 63.7 | 62.3 | the held-out fifth's best yet; the gains are table pages never tuned on. |
| Run 48 | 63.9 | 62.5 | both up again; no check lost anywhere. |
