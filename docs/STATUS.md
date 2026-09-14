# Status (plain English)

_Last updated: 2026-09-15, 04:06 (**Two scores, and they mean different things.** **Open weights: 84.1** (run 89; held-out 81.4, tuned-on 82.0) - your own machine plus olmOCR 2's saved readings, nothing leaving the building, reproducible by anyone with a rented GPU. This is the default: the deep reader is off unless asked for. **With a hosted service: 85.4** (run 91, CI 84.5-86.3; held-out 82.4 and tuned-on 83.5, both the best ever) - the same converter, with the 103 pages of 1,403 that have no text layer and that our own OCR can make nothing of read by Claude Sonnet 5 over the API. **That is the best score the project has had, and the whole interval sits above the previous best of 84.2.** Against the open-weight run: old scans +35, old-scan maths +11, tables +6, tiny text +4, headers -2, multi-column -1. The route there was not straight: run 90 scored 82.8 because D024 escapes every dollar sign outside our own delimiters and a general model writes its maths between dollar signs, so fourteen integrals on one page became literal text and old-scan maths fell 17 points. Fixed by translating a model's delimiters before anything else sees the text. **The method error mattered more than the fix: a change measured on one category was shipped to all eight, and the category it broke was the one never looked at; `bench/tools/compare_categories.py` now makes that impossible to miss.** Also settled this week: a paragraph of prompt beat moving from Sonnet to Opus, reading a page in overlapping bands measured 28 checks worse and is switched off, and the evidence for all of it is in `docs/MODEL_CHOICE.md`. **M7 is met**: 85.4 against a best published 83.1, and OmniDocBench was investigated on 13 September and declined as a measure of TrueDoc - every page in it is an image, so our text reader, formula rebuilder and both table builders never run and the score would belong to whichever model reads the pages (D026). **Your insurance library now has a score too, and it is a different measure: 198 of 229 checks, 86.5%**, written by a model reading 25 of your PDS pages as images and never seeing our output (tables are the weak spot at 14 of 27). **All 38 were ruled on: 31 fair, 7 unsure, nothing dropped**, so the score is confirmed and every failure is ours. Building the set already found five things the public benchmark cannot show, including a PDF whose own text layer has lost letters to its ligatures and which TrueDoc trusts anyway. The section below has them. **The Key Facts Sheets have become an oracle for table rules (D027)**: the prescribed header now reads whole on 95% of the sheets tuned on and 97% of the hidden fifth, from 34% and 16%, and the Yes/No answer sits in its own column for 99.9% of prescribed events tuned on and 100% in the hidden fifth - every rule written in geometry, none of them knowing what an insurance document is. **A benchmark zero is no longer taken on trust**: on 14 September a rule that moved no score had changed 16 pages, and reading them against their images caught a false table and phrases cut in two, both fixed before anything was committed. Next: a label set tight against its answer (Honey's landlord building sheet), then the cover page's ABN.)_

## Scoreboard (olmOCR-bench, higher is better)

| | Score |
|---|---|
| Best published tool (Chandra) | 83.1 |
| Marker 1.10.1 | 76.1 |
| MinerU 2.5.4 | 75.2 |
| TrueDoc run 1 (text layer only, no models), 2 Sept | 48.6 (honest figure about 43, see note) |
| TrueDoc run 2 (layout model, formula rebuild, classical OCR), 3 Sept | 54.7 |
| TrueDoc run 3 (+ scanned-book line rebuild, English OCR model), 3 Sept | 56.3 |
| TrueDoc run 5 (+ four rounds of formula repairs, figure-aware reading order), 3 Sept | 57.9 |
| TrueDoc run 6 (+ table repairs, sideways pages, contact-line headers), 3 Sept | 58.3 |
| TrueDoc run 7 (+ sixth round of formula repairs), 3 Sept | 60.2 |
| TrueDoc run 8 (+ hidden text, column gutters, narrow-column word breaks), 3 Sept | 60.8 |
| **TrueDoc run 9 (+ table header rows and wrapped cells, seventh formula round, render-checked hidden text), 3 Sept** | **62.2** |
| Run 9 with a vision model reading the 94 pages TrueDoc could not read (experiment on your rented GPU), 3 Sept | 67.8 |
| TrueDoc run 10 (+ header zones, word-gap repairs, rebuilt ruled tables, stacked headings), 3 Sept | 62.3 |
| TrueDoc run 11 (+ regression fixes, icons and marks, dictionary word-splitting, eighth formula round), 3 Sept | 62.8 |
| **TrueDoc run 12 (+ running-head rules, pull-quote reading order), 3 Sept** | **62.9** |
| **TrueDoc run 13 (+ formula round 9: fractions in scripts, sized brackets, Latin Modern), 3 Sept** | **63.1** |
| TrueDoc run 14 (+ footnotes and endnotes, island guards, symbol spellings), 3 Sept | 62.9 |
| TrueDoc run 15 (+ run-13 regression fixes, endnotes, figure placeholders), 3 Sept | 62.9 |
| **TrueDoc run 16 (+ epsilon and phi by glyph width, formula round 10, footnote fixes), 3 Sept** | **63.5** |
| TrueDoc run 17 (+ demotion revert, figure joins, boxed-row headers), 4 Sept | 63.5 |
| TrueDoc run 18 (+ arrow fix), 4 Sept | 63.5 |
| **TrueDoc run 19 (+ guarded boxed-row table rule), 4 Sept** | **63.6** |
| TrueDoc run 20 (+ column channels on hidden OCR layers), 4 Sept | 63.6 |
| TrueDoc run 21 (+ formula round 11, first three), 4 Sept | 63.6 |
| TrueDoc run 22 (+ a root inside a sum's limit), 4 Sept | 63.6 |
| **TrueDoc run 23 (+ truncated maths letters, integrals, cases braces), 4 Sept** | **63.7** |
| TrueDoc run 24 (+ colon, script letters, operator names, display-row linking), 4 Sept | 63.8 |
| TrueDoc run 26 (+ underline, headline, drop-cap and ellipsis fixes, mathabx signs), 4 Sept | 64.1 |
| TrueDoc run 27 (+ formula round 12: font spellings, formula tails after radicals and wide accents), 4 Sept | 64.3 |
| TrueDoc run 28 (+ formula round 13: stacked fractions, operator limits, equation numbers, operator words), 4 Sept | 64.4 |
| TrueDoc run 29 (+ formula round 14: symbol tables, scripts, roman letters, function names; early-fold repair), 4 Sept | 64.8 |
| TrueDoc run 30 (+ formula round 15: operator-in-parentheses matrices, italic prose in formulas, parked limits), 4 Sept | 65.0 |
| TrueDoc run 31 (+ formula round 16, first half: mathabx tables, roots in scripts, scripts on fractions, integral limits), 4 Sept | 65.2 |
| TrueDoc run 32 (+ formula round 16, second half: run-31 repairs, italic font names, typed dots, negated relations, text-font terms), 4 Sept | 65.3 |
| TrueDoc run 33 (+ run-31 repairs, tfrac/dfrac, text-only equations, mathx parentheses), 4 Sept | 65.3 |
| TrueDoc run 34 (+ wide centred limits, bold and accented variables, differentials), 4 Sept | 65.4 |
| TrueDoc run 35 (+ narrow column gutters, hyphen-less broken words rejoined), 5 Sept | 65.4 |
| TrueDoc run 36 (+ OCR gate accepts confident non-English reads; non-English scans were empty), 5 Sept | 65.6 |
| TrueDoc run 37 (the numerator-root fold withdrawn), 5 Sept | 65.6 |
| TrueDoc run 38 (+ sideways pages turned upright, OCR rescue bar 0.80), 6 Sept | 65.9 |
| TrueDoc run 39 (+ word spaces on scanned layers, accents composed, section numbers rejoined, baseline-following blocks), 6 Sept | 65.9 |
| TrueDoc run 40 (+ run-39 repairs, centred table cells, label tables, Polish letters), 6 Sept | 66.1 |
| TrueDoc run 41 (+ captions kept out of table headings, table boxes override fragments, OCR-layer block rule), 6 Sept | 66.1 |
| TrueDoc run 42 (+ fragments give way only to a bigger table, centred cells and heading depth repaired), 6 Sept | 66.3 |
| TrueDoc run 43 (+ AdvP minus sign, values with errors in parentheses), 6 Sept | 66.3 |
| TrueDoc run 44 (+ centred corner labels, table boxes versus pieces), 6 Sept | 66.3 |
| TrueDoc run 45 (+ stacked headings joined, heading fragments and wrapped labels kept, Advent symbol fonts), 6 Sept | 66.4 |
| TrueDoc run 46 (+ column cuts voted by gap range), 7 Sept | 66.4 |
| TrueDoc run 47 (+ heading-fragment guard, cut placed where the next column starts), 7 Sept | 66.5 |
| TrueDoc run 48 (+ cut refined, scanned number tables kept, leader dots out, headings in order), 7 Sept | 66.7 |
| TrueDoc run 49 (+ seven table and text rules of the morning, wave 1 of the lateral plan), 7 Sept 14:15 | 67.1 |
| TrueDoc run 50 (+ wave 2's first repairs), 7 Sept 15:40 | 67.1 (held-out 64.9, tables 79.2, arXiv 87.0) |
| TrueDoc run 51 (+ run 50's losses repaired), 7 Sept 16:50 | 67.2 (held-out 65.0, tables 79.5, headers 95.9) |
| TrueDoc run 52 (+ the document-control stamp rule), 7 Sept 17:58 | 67.3 (held-out 65.0, headers 96.6) |
| TrueDoc run 53 (+ headings adopted by headerless ruled boxes, the head-strip chain), 7 Sept 19:02 | 67.3 (tables 79.6; one check more than run 52) |
| **TrueDoc run 54 (+ the key-table rule: enumerated leads beside short names), 7 Sept 20:02** | **67.4** (tables 80.0; four checks more than run 53, none lost; held-out 65.0) |
| Run 54 + a vision model (olmOCR 2) on the 281 pages without a digital text layer (experiment from disk, 7 Sept 21:35) | 82.7 (CI 81.8-83.7; held-out 79.4) |
| **TrueDoc run 55: the vision switch on (D019 built in; the model's saved readings replayed from disk; running heads witnessed), 7 Sept 23:27** | **82.9** (CI 82.0-83.8; held-out 79.7; olmOCR itself 82.4, Chandra 83.1) |
| TrueDoc run 56 (+ the partial-reading rule, first form), 8 Sept 00:33 | 82.8 (a regression of ten checks on six pages: the raw layer counted as the page's reading; repaired for run 57) |
| TrueDoc run 57 (+ the partial-reading rule, repaired), 8 Sept 01:26 | 82.9 (tables 84.0, four checks more than run 55, none lost; held-out 80.0) |
| TrueDoc run 58 (+ picture-text regions: pictures holding tables on digital pages transcribed by the model, GPU session 3), 8 Sept 09:16 | 83.0 (CI 82.1-84.1; tables 85.1, twelve checks more, none lost; held-out 80.0) |
| TrueDoc run 59 (+ four table rules from run 58's failures), 8 Sept 11:17 | 83.2 (CI 82.3-84.1; tables 86.2, sixteen won, five lost; held-out 80.3) |
| TrueDoc run 60 (+ four more table shapes), 8 Sept 12:57 | 83.3 (CI 82.3-84.2; tables 87.3, nineteen won, eight lost; held-out 80.2; Chandra 83.1) |
| TrueDoc run 61 (the eight losses repaired, the units rule), 8 Sept 14:24 | 83.5 (CI 82.6-84.4; tables 88.2, multi-column 80.7; fourteen won, none lost; held-out 80.6; Chandra 83.1) |
| TrueDoc run 62 (five multi-column repairs), 8 Sept 15:45 | 83.7 (CI 82.7-84.6; multi-column 81.7, tiny text 88.2; fourteen won, four lost; held-out 80.8; Chandra 83.1) |
| TrueDoc run 63 (run 62's losses repaired, three furniture shapes), 8 Sept 16:57 | 84.0 (CI 83.1-84.8; multi-column 82.9, arXiv 87.4, headers 96.8; twenty-eight won, one lost; held-out 80.9; Chandra 83.1 is now the interval's lower bound) |
| TrueDoc run 64 (a subscript arriving in two pieces is joined), 8 Sept 18:05 | 84.0 (CI 83.0-84.8; every section unchanged; one arXiv check won, none lost; held-out 80.9) |
| **TrueDoc run 65 (a baseline, not a change: the day's arrow marks and invented-text check), 9 Sept 20:35** | **84.0** (CI 82.9-84.9; every category identical to run 64, zero won and zero lost; held-out 80.9) |
| TrueDoc run 66 (every PDFium switch on - the first full measurement of the licence swap; not shipped), 10 Sept 17:25 | 81.4 (CI 80.4-82.3; held-out 76.9; arXiv 84.3, tables 81.1, multi-column 75.3; 290 checks lost, 46 won; three causes traced, all silent, none of them visible on the quick gate) |
| TrueDoc run 67 (every PDFium switch on, six silent reader faults fixed; not shipped), 10 Sept 20:19 | 82.4 (CI 81.5-83.4; held-out 78.5; 89 checks won and 17 lost against run 66; tiny text 88.7, now above MuPDF; tables 81.4 and arXiv 84.8 still short, the table gap traced to model pages being lost on this path) |
| TrueDoc run 68 (every PDFium switch on, the night's twelve reader and table fixes; not shipped), 11 Sept 07:37 | 83.6 (CI 82.7-84.6; held-out 80.3; against run 65: 51 won, 77 lost - arXiv -1 from -78, tables -15 from -69, multi-column -9 from -25; 0.4 short of the MuPDF run overall, 0.6 on the held-out fifth) |
| TrueDoc run 69 (every PDFium switch on, run 68's fixes plus fractions, whitespace codes, glyph names and the text-object cut; not shipped yet), 11 Sept 09:38 | 83.9 (CI 83.0-84.8; **held-out 80.9, level with the MuPDF run on five more checks**; against run 65: 51 won, 57 lost - arXiv +3, tables -7, multi-column -1; 0.1 short overall) |
| TrueDoc run 70 (every PDFium switch on, font-metric character boxes, shaded cells as rules; not shipped yet), 11 Sept 11:01 | 83.7 (CI 82.8-84.6; **held-out 81.0, above the MuPDF run's 80.9**; against run 69: 14 won, 26 lost, thirteen of them on two pages the new shaded-cell rule turned into wrong tables - fixed for run 71) |
| TrueDoc run 71 (every PDFium switch on; the table finder and the reader corrected against whole benchmark categories), 11 Sept 14:43 | 84.0 (CI 83.2-84.9; **held-out 81.1, the best yet; tuned-on 81.9**; against the MuPDF baseline run 65: 53 won, 44 lost, +9; against run 70: 30 won, 3 lost). The PDFium path is level with MuPDF's overall and above it on the held-out fifth, and becomes the default (D023). |
| TrueDoc run 72 (the line join, PDFium's own line ends and baseline steps as line breaks; unnamed Type 3 fonts read through their own tables), 11 Sept 17:30 | 84.1 (CI 83.2-84.9; held-out 81.1, tuned-on 82.0, the best tuned-on yet; against run 71: 5 won, 3 lost) |
| TrueDoc run 73 (a negative font size read the right way round; the page box is the crop box within the media box), 11 Sept 18:47 | 84.1 (CI 83.2-85.0; held-out 81.2, the best yet; tuned-on 82.0; against run 72: 2 won, 0 lost) |
| TrueDoc run 74 (font names without the subset tag), 11 Sept 19:52 | 84.1 (CI 83.1-85.0; held-out 81.2, tuned-on 82.0; identical to run 73 check for check) |
| TrueDoc run 75 (a list's marker kept with its item; a stranded accent put back before its letter), 11 Sept 21:45 | 84.1 (CI 83.2-85.0; held-out 81.2, tuned-on 82.0; against run 74: 2 won, 0 lost; fifteen checks ahead of the MuPDF run) |
| TrueDoc run 76 (a line-end hyphen boxed at its own width), 12 Sept 00:32 | 84.1 (CI 83.2-85.1; held-out 81.2, tuned-on 82.1; against run 75: 1 won, 0 lost; sixteen checks ahead of the MuPDF run) |
| TrueDoc run 77 (a tilde drawn over its letter read as its accent), 12 Sept 01:55 | 84.1 (CI 83.3-85.0; held-out 81.2, tuned-on 82.1; against run 76: 3 won, 0 lost; nineteen checks ahead of the MuPDF run) |
| TrueDoc run 78 (a maths-extension glyph as wide as its metric box; cmmi's hook read however the reader names it), 12 Sept 03:26 | 84.2 (CI 83.3-85.0; the best TrueDoc run yet; held-out 81.2, tuned-on 82.1; against run 77: 11 won, 2 lost; twenty-eight checks ahead of the MuPDF run) |
| TrueDoc run 79 (a spacing accent PDFium emits out of order keeps its line; glyphs its text page leaves out fill their gap), 12 Sept 04:55 | 84.2 (CI 83.3-85.1; held-out 81.2, tuned-on 82.2, the best tuned-on yet; against run 78: 5 won, 0 lost; thirty-three checks ahead of the MuPDF run) |
| TrueDoc run 80 (six parity repairs: an accent's base by its centre, an accent kept off the pen, three AMS symbol codes, punctuation no filler, no invented blank beside a script), 12 Sept 06:10 | 84.2 (CI 83.3-85.1; held-out 81.3, but its two new checks come from a rule traced on a held-out page - 81.2 without them; tuned-on 82.2; against run 79: 6 won, 0 lost; thirty-nine checks ahead of the MuPDF run) |
| GPU session 4 (experiment, not a TrueDoc run): the densest pages read a band at a time, 8 Sept 20:52 | 84.2 (CI 83.3-85.1; eleven net checks where 3.0 points were projected; held-out unchanged at 80.9, so none of it generalised; `docs/GPU_PLAN.md` has the breakdown) |

Note on run 1: about 6 points of it were an accident. Pages we could not read at all were written as a file holding one blank line, and the marking script treats a one-character answer as matching any phrase. That is fixed; every number since is honest.

What moved across the runs, section by section: formulas 0 to 41 (rebuilt from the letters and positions in the PDF), headers and footers 69 to 92, tables 33 to 55, tiny-text book scans 75 to 77 (after a dip to 68). What has not moved much: reading order on multi-column pages (68) and the two old-scans sections (21 and 4), which need a vision model to go further. Run 4 (converting) adds four rounds of formula repairs that lifted the formula sample checks from about 44% to about 50%; run 5 will add a table fix that recovers tables with grouped headers.

## Where we are

**14 September.** On the public exam TrueDoc scores **84.1 on open weights** (run 89) and **85.4 with the hosted deep
reader** (run 91), against a best published 83.1: M7 is met. On your insurance library it scores **199 of 229 checks**,
a score your rulings confirmed. Your Key Facts Sheets have become an oracle for table rules (D027); where they stand
is in their own section below. Every stage reads the PDF through PDFium, and the product path no longer imports
PyMuPDF (D023). The unit tests pass at every commit: 528 at 12c2137.

### As it stood on 8 September, kept for the record

**Day 7 (8 September, morning): a working converter scoring 67.4 on the public exam without a model (run 54; held-out pages 65.0) and 84.0 with the vision switch on (run 63; multi-column 82.9, tables 88.2; held-out 80.9), against a best published 83.1, which is now the lower end of our confidence interval; 65.6 at the first commit three days earlier.** **The vision stage is inside the converter (D014, D019): every page without a digital text layer goes to a model, the page's own lines witness the running heads it transcribes, and every such page carries a note and the inferred tag. Run 55 replayed a model's readings from disk; a served model end to end is the next step.** The converter reads the PDF's own text, works out columns, paragraphs, headings, running heads and feet, tables (ruled and unruled), rebuilds formulas as LaTeX from the letters and positions in the PDF, uses a free layout-detection model (about 3 seconds a page on this CPU) to settle structure, reads image-only pages with a classical OCR engine and refuses its reading when it looks like noise, and writes Open Knowledge Format markdown with YAML front matter. Nothing is invented: an unreadable page comes out empty, hidden text stays out of the body, and anything a model wrote is marked as inferred.

Section by section (run 54): formulas 87.0, above every published tool's figure for that section; headers and footers 96.6; plain pages 94.7; tiny-text book scans 81.2; tables 80.0 (70.3 two days ago); multi-column 73.9; old scans 21.5 and old-scan maths 4.1. The last two, a quarter of the exam, are handwriting and old print that no classical rule reads; they move only with the vision tier, which is your call (D014): with olmOCR 2 reading every page that has no digital text layer the same run scores 82.7 (old-scan maths 80.8, old scans 46.6; measured 7 September, 21:35, from a 21-minute GPU session costing 85 cents). A held-out fifth of the pages, never tuned on, scores 65.0 (63.3 two days ago).

What exists right now:

- The output format follows the Open Knowledge Format (OKF v0.2), which you confirmed on 3 September (see `docs/OKF_SPEC.md` for how each field is filled). Every file starts with `type`, `title`, `description`, where it came from (`sources`), who made it (`generated`) and `status: draft`; TrueDoc's own notes (confidence, OCR pages, hidden text, warnings) sit under a `truedoc` key.
- The benchmark harness (see `docs/BENCHMARKS.md` and `bench/README.md`): the public exam of 1,403 PDF pages with 7,010 "did the tool understand this?" checks is on this machine with the official marking code, a 10-minute regression gate, two maths spot-check samples, a held-out score, the helper tools in `bench/tools/` that verify a rule page by page before a full run, and the census (`bench/tools/ceiling_census.py`) that counts how many failing checks still have their text in evidence we hold: 218 after run 53, the stopping rule of D018.
- The lateral-thinking round of 7 September (`docs/LATERAL_ROUND_1.md`): eleven facts, a shortlist of fourteen ideas, and the record of what each one did when tested; and the Marker and MinerU reading (`docs/M14_MARKER_MINERU.md`).
- 215 unit tests, all passing at the commit.

## What "winning" means in numbers

Think of the main benchmark as an exam with eight sections (maths papers, old scans, tables, multi-column layouts, tiny text, headers and footers, and so on). Each section is scored out of 100 and the overall mark is the average of the sections. The best published tools score in the low 80s. The tools you named score between roughly 60 and 80. TrueDoc's target is to beat the best published score, not only the tools on your list. Current numbers are in `docs/BENCHMARKS.md`.

## The plan in one breath

Trust the PDF's own text when it has any (it is exact, and no model can beat it), use image models only to work out *structure* (columns, tables, headings) and to read scanned pages, and check every model's answer against the raw evidence before believing it. This is different from every tool on the list: pipeline tools trust their layout model blindly, and vision models trust their own eyes blindly.

## Things you may need to do

- (Done 3 Sept, evening: you agreed the "inferred" marker proposal as written, one tag for every model source, and confirmed the GPU instance is stopped.)
- **A weekly spending cap** for GPU rental once the vision stage is built (20 US dollars suggested). Until then nothing is spent without you renting an instance by hand.
- **A backup of the code.** The repository is committed locally (6 September) but has no remote: add one (GitHub or similar) and push when you want an off-machine copy. Nothing is pushed unless you ask.
- **Optional: name documents with icon-based tables.** Three of your insurance PDFs are in `samples/` and read correctly now; more examples of icons that carry meaning (legends, symbols other than ticks and crosses) would sharpen the recogniser.

- (Done 8 Sept, evening: you rented the GPU and session 4 ran for about 40 cents. It answered its question in the negative - reading a dense page a band at a time is a wash, and none of the gain reached the held-out pages. `docs/GPU_PLAN.md` has the numbers. Nothing further is owed on it.)
- (Answered 13 Sept, D025: not a stronger model for every page but a second, paid reader for the pages the first cannot manage, off unless asked for. `docs/MODEL_CHOICE.md` has the measurements.)
- (Done 12 Sept, D023: the product path no longer imports PyMuPDF at all. `tests/test_no_pymupdf.py` converts a document in an interpreter where `import pymupdf` raises, and the package is now an optional extra, for the `TRUEDOC_READER=mupdf` comparison reader and the measurement tools. D007's evidence lists the licence of every package the product path imports.)
- (Done 7 Sept, evening, recorded as D020 on 8 Sept: partial pages stay closed and small task models stay out. Keeping the shaky reads of pages the OCR gate rejects was worth at most +1.4 against the model's +4.8 on the same pages, and the pages a reader would want are ones the model reads anyway; a formula-image reader and a second OCR engine have no territory left now that every page without a digital text layer goes to a model. One product question remains, in `docs/DECISIONS.md`: whether the free tier, which has no model, should emit a partial-page note instead of an empty file for the handful of pages our own OCR read confidently but the word-likeness gate rejected.)

## What is being worked on right now

**14 September: table rules drawn from your Key Facts Sheets.** Each rule is written in geometry and typography,
never for Key Facts Sheets as such (D027). It is measured on the sheets, with the hidden fifth reported beside the
rest, and on the three benchmark categories it can touch; then every benchmark page whose markdown changes is read
against its page image before the rule is committed, because a score that does not move can still hide a false
table. The Key Facts Sheets section below says where the sheets stand and what is next, and `docs/PROGRESS_LOG.md`
has each rule with its numbers.

### Earlier work, kept for the record

**11 September: off PyMuPDF's licence (M18, D023).** Every stage that reads a PDF now goes through
PDFium by default, and **the product scores what it scored on MuPDF: run 71 reads 84.0 with every
switch on, level with the MuPDF run's 84.0, and above it on the fifth of the pages never tuned on
(81.1 against 80.9).** MuPDF is still installed and reachable by name (`TRUEDOC_READER=mupdf` and the
two like it) so that every future change can be measured against it, but no page is read through it.

| what moved | switch | where it stands (no model, whole category, against MuPDF) |
|---|---|---|
| Characters and fonts | `TRUEDOC_READER=pdftext` (default) | tiny text 364 against 361 of 442; quick gate 100 of 128 |
| Turning pages into pictures | `TRUEDOC_RENDERER=pdfium` (default) | 100 of 128 - no difference at all; **but not in effect from 10 Sept 10:43 until run 83: a call left on a renamed function made every PDFium render fail, and the silent fallback drew every page with MuPDF** |
| Drawings and picture positions | `TRUEDOC_OBJECTS=pdfium` (default) | multi-column 681 against 678 of 884 |
| Finding ruled tables | (same switch) | tables 852 against 848 of 1,022 (was 830 when first built) |

**Since run 71: the PDFium path fixed by points.** Runs 72 to 75 took it from 84.0 to 84.1, with held-out 81.2 and tuned-on 82.0, both the best yet. Each change was proved against what MuPDF does before it was written: the line join, a negative font size read the right way round, the crop box, a list's marker kept with its item, a stranded accent put back before its letter, and bold and italic read from the font program when the name says nothing. The latest: PDFium marks a hyphen at a line end with a control code, and the reader asked the font for that code's width - a full em - so a two-column page lost its gutter and read a paragraph out of order. On 4,058 such hyphens the width now agrees with MuPDF's on all but two, and the whole categories moved by exactly that page. Run 76 measured it: one check won, the page it was traced on, and nothing lost. Run 77 added a tilde drawn over its letter, read as that letter's accent - PDFium reports such a mark where it is drawn, and the maths stage expected it where MuPDF moves it - and won exactly the three arXiv checks its measurement named. Run 78 added two more: a maths-extension glyph as wide as its metric box, which stops a brace from reading as three, and cmmi's hook read however the reader names it. It scored 84.2, the best TrueDoc run yet: eleven checks won and two lost, exactly the pages the measurements named, the two losses each now at MuPDF's own score. **Correction:** the last update called run 65 "the MuPDF run of the same code". It is the MuPDF run of 9 September's code, and the MuPDF path has not been rerun since, so "checks ahead of the MuPDF run" compares today's PDFium path with the MuPDF path as it was then. Run 79 added a spacing accent PDFium emits out of order no longer ending its line and the repair for the glyphs PDFium's text page leaves out, and won exactly the five checks measured for them, losing none. Run 80 added six repairs for the pages where MuPDF's reading still scored higher - an accent's base found by its centre, an accent left standing kept off the pen, three more AMS symbol codes, a lone comma no longer welding two fractions' denominators, and no invented blank between a subscript and a full-size glyph - and won exactly the six checks measured, losing none. **Correction on the held-out figure:** one of those repairs was traced on a held-out page (2503.05183), against D016, and so, on 11 Sept, was the Type 3 work of run 72 (0b65b6a5); run 80's held-out 81.3 includes that page's two checks, and the clean figure is 81.2. From now every held-out page is left out before anything is traced. MuPDF's own rules for where a line and a block end are now measured - a new line wherever the pen jumps 0.8 em forward, up or down; a new block wherever a line steps down 1.5 em - but applied as MuPDF applies them they lose checks here, because PDFium's text page leaves out spaces and glyphs that MuPDF's pen counts; the repair for those missing glyphs is the one part that goes in.

What is left of M18 is housekeeping, not reading: the document handle, two geometry types and a
rotation call still come from the PyMuPDF package, so it cannot be uninstalled yet.

Three things worth knowing:

- **The 13-page quick test cannot be trusted alone, and today proved it.** The table swap reads 100
  of 128 on it - perfect - and loses 38 checks when the whole category is scored, because the gate
  samples 188 table pages with three. Tracing that found three real defects, two of them in the
  drawing reader rather than the table code, and closed the gap to 18. It stays switched off.
- **The item recorded as the hard part turned out to be the easy one.** MuPDF's log of every mark
  made on a page has no PDFium equivalent, but TrueDoc only ever took two things from it - where
  the pictures are and what was painted over what - and PDFium gives both.
- **One bug was found in the shipped product and fixed** (your instruction: check it where it
  matters). On pages turned sideways, the hidden-text check and the tick reader were looking at the
  wrong part of the page. Measured across all 82 rotated pages in the benchmark and your insurance
  library: 80 unchanged, including every one of your 67 library pages.

**Thursday evening: the first full measurement, and what it found.** Run 66 - every switch on -
scored **81.4 against 84.0**, and the quick test had read a perfect 97 of 128 for it. Six faults
traced the same evening, every one silent, none of them where I first looked:

- pages that shrink everything with a graphics-state scale reported text at 4/3 its real size, so
  small print glued its words together;
- end-of-line hyphens arrived as an invisible control character, so no broken word was rejoined;
- the maths symbol fonts arrived as raw codes - `k` for the parallel sign - so the formula
  rebuild never saw a symbol;
- the letter **f** overhangs its own width, and PDFium's box included the overhang, so at 7pt a
  gap that MuPDF read as a word space read as nothing (`ofthe`);
- fixing that broke the **fi** ligature, one drawn shape carrying two letters, until a character
  sharing its box with a neighbour was told to keep it;
- a combining slash attached itself to the character after it instead of the one before.

Each was proved against a direct measurement of what MuPDF does, and each is pinned by a test
built by hand. Quick test 98 of 128 with every switch on; **run 67 is measuring the whole
benchmark now.** The hidden-text machinery is done and checked on 120 real pages (117 identical).
Left to do: the last 18 table checks. Nothing needs a rental.

**Plan agreed 7 September, midday (`docs/LATERAL_ROUND_1.md`):** wave 1 after the compact (punctuation spaces on OCR text, TeX ligatures, formulas as strings on OCR pages, stacked statistics cells, the native-resolution OCR test), then run 49; wave 2 through the week with an hour's test before each build; wave 3 on the owner's decisions. Target 70 without a model; 72.5 is the ceiling; the census pool (`bench/tools/ceiling_census.py`) is the stopping rule. Run 49 is on hold until wave 1 is in. **Wave 1 progress (13:10):** items 1 to 4 are in the code with tests (punctuation spaces on OCR text, TeX ligature codes, formulas as plain strings on OCR pages, stacked statistics folded into their values): 16 checks won and none lost in page checks against run 48; the ligature claim of 13 checks proved wrong (a fidelity fix only). Item 5, OCR at the scan's own resolution, was tested on the fourteen pages the round named and gained nothing (the engine resizes every line it reads, so extra pixels buy nothing); set aside with its numbers in the log. Run 49 launched at 13:16 with wave 1 and the morning's seven rules and **scored 67.1 at 14:15** (held-out 64.7): tables 78.7, tiny text 81.2, headers 96.6, multi-column 73.9, old scans 21.5; 36 checks won, 13 lost (traced next). Wave 2 so far, from an afternoon of hour tests while the run converted: four fixes in the code with tests (a table in the page's head strip, lowercase label rows, a checklist with sparse tick columns, and TeX Gyre text faces no longer counted as maths, which had swallowed ten arXiv pages whole); the content-stream order, native-resolution OCR, the character grid and the running-head rules set aside with their numbers.


**As of 7 September, 21:40: run 54 scored 67.4 (tables 80.0; held-out 65.0), the sixth run of the day. The same evening, wave 3: olmOCR 2's readings merged over run 54's pages score 72.2 on the blank pages alone and 82.7 (CI 81.8-83.7, held-out 79.4) on all 281 pages without a digital text layer, read in a 21-minute GPU session the owner rented for 85 cents; old-scan maths 4.1 to 80.8, old scans 21.5 to 46.6, tiny text 81.2 to 87.8, multi-column 73.9 to 80.1, tables 80.0 to 83.6, digital formulas unchanged at 87.0. That is level with the best published tool (Chandra 83.1) and above olmOCR's own 82.4: the hybrid of exact text on digital pages and a model on the rest. D019 is built into the converter (page selection by text-layer kind, a file provider that replays saved readings, the page's own lines as a witness for running heads: +3 checks, none lost, 82.8 from disk), and **run 55, the first TrueDoc run with the vision switch on, scored 82.9 at 23:27 (CI 82.0-83.8; held-out 79.7; 725 checks won and 48 lost against run 54; 5 won and none lost against the merge)**: above olmOCR's own 82.4, level with Chandra's 83.1 inside the interval. Next: a served model end to end, the invented-text check on model pages, and the classical tail (tables) to pass 83.1. Partial pages closed (a reader's question, at most +1.4). Open with the owner: PyMuPDF's licence direction, the library sample.** The day in one paragraph: the morning added seven table and text rules (hyphen-wrapped cells, group labels, paired lines in ruled cells, crowded cells rebuilt, running heads at the top of a page, word spaces in tiny type, small caps read as capitals), then the owner paused run 49 for a review: the Marker and MinerU reading (`docs/M14_MARKER_MINERU.md`) and a ten-thinker lateral round on de Bono's methods (`docs/LATERAL_ROUND_1.md`), which set the plan of three waves, the target of 70 without a model and the census as the stopping rule (D018). Wave 1 went into run 49: punctuation spaces on OCR text (+12), TeX ligature codes (a fidelity fix; the round's claim of 13 checks was wrong), formulas as plain strings on OCR pages (their braces escaped after run 49 lost three), stacked statistics folded into their values (+4); the native-resolution OCR test gained nothing and was set aside. Wave 2 so far (each idea tested for an hour on run 48's outputs before any code): set aside with numbers, the content-stream order, the character grid, the running-head widening, the digital-page punctuation rule; built with tests and in run 50, tables in the head strip of a page, lowercase label rows, a checklist's sparse tick columns, a roster's wrapped title, TeX Gyre text faces no longer counted as maths (ten arXiv pages had been swallowed whole into one formula each, found by the conservation census), numeric blocks kept from the running-head rules, boxed grids of names rebuilt. The run-by-run history is in `docs/PROGRESS_LOG.md`; the benchmark rows in `docs/BENCHMARKS.md`.
- **Run 7 scored 60.2** (run 6: 58.3). The formula section went from 51.1 to 66.7: 1,952 of its 2,927 checks now pass, up from 1,495. The wins came from reading the maths font's tall brackets and operators correctly (their reported boxes were wrong, and some arrived as "space" characters and were thrown away), from putting hats and arrows on the right letter, and from re-joining lines that the PDF had shattered around superscripts. Every other section stayed within a point.
- **Run 8 scored 60.8.** It carried the hidden-text rule you decided on, a fix for two-column pages whose columns sit very close (patents, newsletters: lines from both columns were being joined into one), a fix for words glued together in narrow justified newspaper columns, a fix for a font type whose text size is reported as 0.1 point, and a detector for unreadable OCR text layers. Multi-column pages went from 67.8 to 70.7 and tiny-text scans from 77.8 to 79.6.
- **Run 9 scored 62.2** (run 8: 60.8). Tables went from 58.2 to 65.7: tables get their header row back when the layout model's box starts under it, wrapped cells stay whole, and the layout model's table boxes are trusted. Formulas went from 66.4 to 69.2 with the seventh round of repairs (prose words inside formulas, long superscripts, wide limits, variables set in Times). Hidden-text verdicts are now checked against the rendered page, so no real text is lost to a producer that mislabels its colours.
- **The vision-model experiment scored 67.8** (run 9 was 62.2). On your rented RTX 4090 the olmOCR 2 model read the 111 benchmark pages TrueDoc leaves empty (scans with no text layer and no confident OCR); 94 of those pages replaced TrueDoc's empty output and nothing else changed. Old scans went from 20.7 to 34.0, old-scan maths from 4.1 to 23.1, tables from 65.7 to 70.0. The model time was 12 minutes; the whole instance session about 55 minutes and under a dollar. This is a decision for you (see below): TrueDoc stays CPU-only by default, but an optional vision stage for image-only pages is worth about 5.6 points on this benchmark and, more to the point, turns unreadable scans into text.
- **Run 10 scored 62.3** (run 9: 62.2). Headers and footers went from 93.9 to 95.3; tables from 65.7 to 66.0. Multi-column fell from 70.7 to 69.5, and the reason was found within the hour: a new rule for scanned pages whose hidden text squeezes the space between words was judging the letter gap per line, so on one report it spaced short words out letter by letter ("w i t h"). The tables gain was also smaller than it should have been because the rebuild of ruled tables whose rules only frame the heading also fired on ordinary ruled tables of wrapped prose and shredded them. Both are fixed and gated.
- **Run 11 scored 62.8** (run 10: 62.3). Tables went from 66.0 to 69.1 once the two run-10 misfires were fixed, multi-column recovered to 70.6, formulas edged up to 69.7. The new held-out check (a fifth of the pages that no rule is tuned on) reads 60.0, level with run 9 and up from run 10's 58.7, so the gain is real rather than fitted.
- **The vision stage exists** (built 3 Sept, after your decision): one switch, `--vision-endpoint`, used only for pages with no usable text; the model's reading is marked as inferred in the text and listed in the front matter. It is tested against a stand-in model; the first real use needs a GPU instance serving olmOCR 2, and I will ask you to rent one when the mechanical work has settled. Since the evening of 3 Sept the same switch also asks about icons in table cells ("Covered[^inferred]") and describes figures (the description becomes the image's alt text, tagged), and can use Anthropic's API instead of a served model when you set `ANTHROPIC_API_KEY` and pass `--vision-endpoint anthropic`. Nothing calls a model unless you switch it on.
- **Footnotes are linked** (built 3 Sept evening, after your question): a raised marker in the text becomes `[^8]` and the note at the foot of the page becomes `[^8]: ...`, the standard markdown footnote form, so readers and programs can follow it. Notes kept at the end of a document (under a "Notes" heading) are linked too, and a number reused on a later page gets a page-qualified key so links never cross. In run 14.
- **Formula round 9 (built this afternoon, in run 13).** Fractions inside superscripts and subscripts are kept with their script; TeX's fixed-size brackets carry their size (the benchmark's checker tells a big bracket from a small one); Latin Modern's maths fonts are recognised like Computer Modern's; a numerator now follows its fraction bar to the right line even when a tall bracket is glued to it; bracketed fractions are no longer mistaken for matrices; two guards stop invalid LaTeX. Spot-check on the first maths sample unchanged at 44 of 52; the second sample is re-run when the machine is free.
- **Run 12 scored 62.9** (run 11: 62.8): headers and footers 95.3 to 96.4 from the running-head rules; every other section within one check of run 11; held-out pages 60.2.
- **Run 13 scored 63.1** (run 12: 62.9): formulas 69.7 to 70.8 (34 more checks pass) from the ninth formula round; every other section unchanged to the check; held-out pages 60.4 (run 12: 60.2), with held-out formulas at 75.4.
- **Run 14 scored 62.9** (run 13: 63.1). Two causes, both found and fixed the same evening: the wider epsilon spelling swap was right for some TeX distributions and wrong for others (the two epsilon shapes now tell themselves apart by width, as do the two phi shapes), and the new footnote links fired on citation numbers ("2-4" pointing at a bibliography) and once on a section heading; a marker with no note anywhere now stays as printed. Held-out 60.1.
- **Run 15 scored 62.9** (level with run 14): baseline 93.4 to 93.8, headers 96.6, formulas and tables unchanged, multi-column down two checks; it still carried run 14's epsilon regression, which run 16 removes. Held-out 60.0.
- **Run 16 scored 63.5, the best so far** (run 13: 63.1). Formulas went from 69.6 to 73.7 (121 more checks pass) once the two epsilon and two phi shapes were told apart by glyph width and the tenth formula round landed; multi-column recovered three checks from the footnote fix. Held-out pages 60.6, also the best so far, so the gain is general.
- **Run 17 scored 63.5** (level with run 16): formulas 73.9 (+5 checks from reverting the bracket-size demotion), multi-column +1, tables 68.6 (-5: the new one-row-box rule fired on captions above ruled tables and on a tall frame around a column; three guards added, and on the seven affected pages 30 checks now pass against run 16's 26; in run 19). Held-out 60.5.
- **Run 18 scored 63.5** (level): the arrow fix won two formula checks and lost nothing; formulas now 74.0. Held-out 60.5.
- **Where the remaining losses sit (census, 4 Sept early morning).** Of the reading-order checks still failing on multi-column and scanned pages, about half are on pages with no text layer at all. Our own OCR reads a third of those pages confidently enough to be accepted, and they still fail on classical-OCR spelling ("Vory truly your", "graduste") and letterhead lines interleaved with the body; the rest it cannot read. That is the vision stage's ground, where the olmOCR 2 experiment already gained 5.6 points. The mechanical tier still has specific rules to find in formulas, tables and digital multi-column pages, and that is where the loops continue.
- **Run 19 scored 63.6, the best so far** (runs 16 to 18: 63.5): the guarded boxed-row rule won nine table checks (tables 68.6 to 69.5) and lost nothing; held-out pages 60.7, also the best.
- **Run 21 scored 63.6** (level; formulas up two checks, nothing lost; held-out 60.8) with the start of formula round 11: a radical's own bar no longer passes for a fraction bar, the "tx" symbol fonts' brackets and radicals are read correctly, and a limit that runs wider than its operator stays with the operator.
- **Run 22 scored 63.6**, identical to run 21 to the check (its one change, a root inside a sum's limit, touched no benchmark check). **Run 23 scored 63.7, the best so far** (formulas 74.0 to 75.0, 32 checks won and 5 lost, everything else identical; held-out 61.0, also the best) with a fix for maths letters that newtx and STIX PDFs deliver with a truncated code (an alpha arriving as a Korean syllable), which had wrecked whole pages of formulas, plus integral signs from two more maths fonts, integrals whose limits and integrand arrive on three separate lines, and "cases" braces that arrive in pieces under Adobe's private-use names. **Run 24 scored 63.8, the best so far** (formulas 75.0 to 75.9, 30 checks won and 3 lost; multi-column down three checks, being traced; held-out 61.2, also the best) with a colon that some fonts deliver as a "ratio" sign, the script alphabet from the rsfs font, operator names glued to their bracket, and a fix for two consecutive lines occasionally merging into one formula. Run 25 launched at 09:12 behind it (score due about 10:50) with the fixes for two of run 23's five lost checks (a tall bracket and a brace piece had been treated as operator signs) and the last brace-piece case, validated the same way (112 tests, gate 97 of 128, samples 44 of 52 and 57 of 64). Run 24's three lost multi-column checks were traced to underlined words being read as fractions (a word on a short rule now needs a word on the rule's other side); the same morning fixed three faults of newspaper display type (a 139 pt headline read as maths, a drop cap left as a heading of its own, the ellipsis character where the references type three dots: 9 checks gained, none lost on run 24's outputs). **Run 25 scored 63.8** (formulas 75.9 to 76.0, four checks won and none lost, everything else identical; held-out 61.2). Run 26 launched at 10:42 with the underline, headline, drop-cap and ellipsis fixes (113 tests, gate 97 of 128, samples 44 of 52 and 57 of 64); it scores itself when the conversion ends, about 12:20. **Run 26 scored 64.1, the best so far** (CI 63.3-65.0): formulas 76.0 to 77.0 (37 won, 9 lost), multi-column 70.5 to 71.8 (12 won, none lost), tables +1; held-out 61.2. The nine formula losses are all a wide hat over a single letter that the accent pass had narrowed to a plain hat (the two render differently); the narrowing now applies to tildes only. **Run 27 scored 64.3, the best so far** (CI 63.4-65.2): formulas 77.0 to 78.1 (37 won, 4 lost), multi-column 71.9 (+1); held-out 61.3, also the best. Two of the four losses were inline matrices broken by folding bracket pieces into lines too early (fixed: only root signs and wide accents are folded early). Run 28 launched at 13:38 with formula round 13 (inline fractions whose denominator starts a new segment, limits shared between neighbouring operators, diagonal dots, cmex angle brackets, wide hats kept wide, roots over script-sized fractions, operator words such as "conv" and "std", arithmetic after a line break, left-margin equation numbers, slanted inequalities written plain, long mapsto arrows). Formula round 14 (for run 29, which launches itself after run 28) mines the symbol tables further: mathabx and newtx codes (partial, lesssim, approx, star, infinity, double bar, blackboard letters, a display product), the square-cup operator, hook arrows, `\cong`, scripts of overlined bases, scripts of scripts on their own baseline, script-sized words merging across segments, `\phi` in Symbol-font maths, single upright capitals as `\mathrm`, glued function names split apart, normal-subgroup triangles, and two halves of a text line merged across a sum sign or a stacked fraction standing between them; each item verified on its page (about 35 checks gained on the traced pages, 2 lost to the wide-hat trade-off). **Run 28 scored 64.4, the best so far** (CI 63.4-65.4): formulas 78.1 to 78.9 (41 won, 17 lost), multi-column one check down; held-out 61.4, also the best. Its losses were understood the same afternoon: five references keep the slanted `\leqslant` (the plain spelling is reverted), two are the wide-hat trade-off, and the rest came from one-line brackets that had started merging into the full-width line above them once the early fold had been limited to root signs; the early fold now takes every symbol whose host's baseline runs through it and leaves matrix-height brackets for the fold after the merge, which repairs those pages while keeping the matrix and sum gains. Run 29 launched at 15:23 with formula round 14 and these repairs. Formula round 15 (for run 30, which launches itself after run 29) found from the checker probes that delimiter sizes never matter to it and spent the afternoon on content instead: tall parentheses around an operator with limits are no longer read as a two-row matrix, blackboard and calligraphic letters from four more font families (bbold, boondox, dsfont, STIX private-use codes) come out as `\mathbb`/`\mathcal`, mathabx's prime and times codes, "(mod p)" written `\pmod{p}`, labelled arrows as `\xrightarrow{...}`, n-ary operators as Unicode, and italic theorem prose inside formulas written as text runs; about 40 checks gained on the traced pages, none lost. **Run 29 scored 64.8, the best so far** (CI 64.0-65.7): formulas 78.9 to 82.6 (123 won, 16 lost), multi-column +1, tiny text -1; held-out 61.8, also the best. Six of the formula losses are the slanted-inequality trade-off (kept faithful to the glyph), five are a "min" label in a subscript read as the operator (fixed for run 31). Run 30 launched at 16:45 with formula round 15.
- **Run 20 scored 63.6** (level with run 19; multi-column up two checks, nothing lost; held-out 60.8, the best yet) with one multi-column fix: on scanned pages with a hidden text layer, a page that opens with a full-width abstract over two columns now finds its column boundary in the lower band instead of nowhere (the two columns of a case report were interleaving line by line).
- **A caution about the benchmark.** Checking the benchmark's own failure messages showed that some expected answers are wrong: on a Croatian interview and a references page the benchmark's phrases contain invented names, so the only way to pass them would be to copy the mistakes. Those checks are noted and left alone.
- The formula rebuild passes about half of the formula checks on two independent samples of maths pages (it started at zero). The rest are mostly multi-line equation blocks, matrices with fractions inside, and formulas whose reference uses a construct that renders differently.
- About a third of the remaining table misses are tables that are pictures (no text in the PDF at all); those wait for the vision-model step.

- **Runs 30 to 37 (4 to 5 September, overnight loop): 64.8 to 65.6.** Formula round 16 (33 items) took the formula section from 82.6 to 86.8: the mathabx symbol font's codes read off a contact sheet of its glyphs, roots and scripts inside limits, italic Times fonts recognised by name, typed "..." told from the LaTeX dots by their spacing, negated relations, text-font terms such as "4k+1" joining their formula. The biggest single step was elsewhere: 89 benchmark pages were coming out empty because the OCR gate rejected confident reads of non-English scans as noise; accepting confident reads whose words look like any Latin-script language filled ten of them and was worth +0.2 on its own (tables 69.6 to 70.3, multi-column 71.9 to 72.7). Four rules were tried and withdrawn after page checks or a run showed losses (symbol-font spaces as negation slashes, fraction rows inside matrices, a respelling of "not in", a fold rule for numerator roots); each is written up in `docs/PROGRESS_LOG.md` so it is not retried blind. Held-out 61.8 to 62.2.
- **6 September: pages lying on their side are turned before reading (run 38).** A landscape scan of a Spanish decree and a table printed up the page were both coming out empty: every line was filed as a rotated stamp. TrueDoc now notices when most of a page's text runs up or down, works out which way from the OCR engine's own angle classifier (or from the text layer's line directions), turns the page in memory and reads it again; the front matter says which pages were turned. A census of all 1,403 benchmark pages found exactly three such pages (one is a picture table with only its title in the text layer, left for the tables job). The bar for accepting confident non-English or numeric OCR moved from 0.85 to 0.80 on the census evidence (the two pages in that band that were rejected stay rejected). On the affected pages: 0 of 8 to 5 of 8, 0 of 5 to 5 of 5 and 0 of 8 to 5 of 8 checks; three ordinary OCR pages unchanged.

## Your insurance library has a score, and it found five things, 13 September

Twenty-five pages of your PDS library - half drawn at random, half chosen because the page draws
many rules - were read as images by a model that never saw our output, and it wrote **229 checks**
about what any honest conversion must say. **TrueDoc passes 198 of them, 86.5%**: present 103/113,
order 50/58, absent 31/31, tables 14/27. The checks are not confirmed yet; you rule on the 38 that
need a person in `bench/out/insurance_set/insurance_dossier.html`, and the 191 that both pass and
read correctly in a second, independent reading of the page are already settled.

Five things came out of building it, and none of them would have shown on the public benchmark:

- **A lossy text layer sails straight through.** One RAA page's own font maps the "ff" and "fi"
  ligatures to a single letter, so the PDF file itself says "ofer", "fnd" and "Certifcate" - we
  checked the file, not the conversion. TrueDoc trusts a text layer whenever there is one, so a page
  that has already lost letters is never read as an image. A cheap detector (impossible words) could
  send such a page to the deeper read.
- **Spaces go missing on that same page.** The file says "If you", "Cooling-of Period", "of 21"; we
  write "Ifyou", "Cooling-ofPeriod", "of21". This one is ours, and it is the sort of thing a reader
  notices immediately.
- **A tick or a cross gets swept into the label beside it.** Our cell reads "X Loss or damage caused
  by lightning." where the page keeps the mark in its own column. Five checks across three insurers.
  The meaning survives for a person reading it; an exact-match test fails, and so would anything
  parsing the table.
- **A table row can vanish while its words survive.** On the Seniors page 25 the page has a limits
  grid with $5,000 and $10,000 in it; our output has "Limits Essential Top Landlords $5,000 $10,000
  Not covered" as flattened text and a two-cell table beside it. The amounts are all there and the
  grid that ties each amount to its cover is not.
- **A cover page's issuer, ABN and registered office are dropped**, and not on purpose, as this page first
  said: the page has a text layer, so no model reads it, and the block goes because the layout model labels
  it a page footer. You ruled that an insurance document keeps them. The fix, a footer label declined for a
  block too big to be a running foot, is measured both ways first, since some benchmark checks want footers
  left out.

### The Key Facts Sheets grade themselves, and the rules that came out of them

A Key Facts Sheet is prescribed by the Australian Government under the Insurance Contracts Act 1984.
Your library holds **202 of them across 34 insurers** - 17% of it. The law fixes the wording; each
insurer sets the type. So a few hundred pages where the right answer is known without anyone writing a
check, laid out 34 different ways. `bench/tools/kfs_grade.py` converts and grades all of them and keeps
a fifth hidden, so no rule can be tuned until everything passes. Your decision (D027): use them to
derive rules, never to special-case - a rule that says "if this is a Key Facts Sheet" fixes 202
documents and no others.

Two rules came out of it on 13 September, and both are **free on the public benchmark**: measured
code against code over the whole table category, 188 pages and 1,022 checks, **843 v 843 with not one
page moved**.

- **A tick or cross at the head of a cell starts a new entry.** Your Allianz policy was publishing
  "✗ Pontoons ✗ Buildings under construction where the value of any alterations... is over $75,000" as
  a single exclusion - two things the policy does not cover, glued into one. About 104 cells across the
  library read like that. Narrowed to ticks and crosses after a broader version shredded sub-lists:
  "✓ Loss or damage caused by impact from: • any motor vehicle, • any animal" is one covered item.
- **A heading that wraps mid-sentence is still the heading.** Two thirds of Key Facts Sheets were
  losing "Event/Cover" and "Yes/No Optional" into the middle of the table, because the heading's own
  third column runs to three lines and the rule that ends a heading stops at the first long cell. On a
  document whose only job is "is this event covered", that loses the labels saying which column holds
  the answer. **Header whole: 34% to 95% on the sheets tuned on, 16% to 97% on the hidden fifth**, with section headings no longer buried inside an exclusion (63 sheets to 0) and the Yes/No answer in its own column for 99.9% of prescribed events tuned on and 100% held out - the
  hidden ones moving with the rest is the evidence the rules are geometry, not a shape fitted to what was
  in front of us.
- **Checked by eye, not only by score (14 September).** The rule that gave the answer its own column moved
  no benchmark score, yet it had changed 16 benchmark pages: 7 for the better and 3 for the worse - a
  court form's address box and claim box built into one table, and phrases cut in two ("Groups at |
  Risk"). Two more rules, both geometry, stop both: a column found on the second look may not be cut only
  to split phrases, and a table only that look can see is not a table. A first, blunter version of the
  phrase rule cost 51 of the Key Facts Sheets' Yes/No answers, and the sheets caught it before it was
  committed. Afterwards not one benchmark score moves
  (tables 844 v 844, multi_column 682 v 682, long_tiny_text 357 v 357), and the markdown differs from the committed code on 11 of 481 pages - 7 better, 3 neutral, and a running head the old code had filed into a table.
- **Two more the same evening.** A sentence printed above a ruled table is no longer taken for its heading row - it
  crosses from column to column on word spaces, where a row of headings crosses on the gaps between its cells -
  which gave 21 more sheets their heading, 4 of them in the hidden fifth. And a label that wraps ("Escape" over
  "of liquid") now continues its row, so its Yes/No stays beside it. No sheet lost anything; on the benchmark
  not one score moves (tables 844 v 844, multi_column 682 v 682, long_tiny_text 357 v 357) and the markdown differs on 6 of 481 pages - 4 better (two captions and a title no longer the first row of their tables, and a TV listing's wrapped lines joined), 1 neutral, and 1 worse: a German index read as a table.
- **A band, and a label in title case (the same evening).** A section heading laid across the table ("Cover for
  valuables, collections and items away from the insured address") no longer keeps "Optional" stuck at the head of
  the exclusions, and a label set in title case ("Malicious" over "Damage") now carries on to its second line, so its
  Yes/No sits beside the whole name. Together they gave 35 more prescribed events their Yes/No beside their name, 3 of them in the hidden fifth, and no sheet lost anything. On the benchmark not one score moves (tables 844 v 844, multi_column 682 v 682, long_tiny_text 357 v 357) and the markdown
  differs on 1 of 481 pages - a milestone table whose two-line row now reads as one ("Substantial Completion of Construction - Operational"), better. Three insurers set the band over only some of the columns, and that is next.
- **A band over only some of the columns (the same night).** On three insurers' contents sheets the section heading
  starts over the answers rather than at the table's edge. It is now told by the white space around it, so
  "Optional" gets its own column on all three sheets and the heading its own row on two. The same change gave the heading its own row on nine landlord sheets from six other insurers, where it had been glued to the end of the exclusions above it; one graded sheet still has it there. The Yes/No sits in its own column for 1,870 of 1,885 prescribed events on the sheets tuned on, from 1,864, and nothing in the hidden fifth moved. On the
  benchmark only tables move (tables 844 -> 848, multi_column 682 v 682, long_tiny_text 357 v 357), and the markdown differs on 2 of 481 pages, read against their images: a band
  the page draws across a table is now one in the output (better), and a Wiley table's sub-heading spans its columns
  (no worse). The four checks gained there are a dollar sign, not the band: the pipe table wrote `\$448` for D024,
  the check wants `$448`, and the table, set as HTML for its band, writes `$448`.
- **A band that starts in the gutter (later that night).** Bank of Queensland sets the section heading after the
  answers end and just before the exclusions begin, so it covered none of the answers' column; a known band now spans
  the column to its left when it starts well clear of its own column's text. Now no graded sheet has its section heading glued into the exclusions, and nothing else moved, on the sheets tuned on or in the hidden fifth. On the benchmark not one score or page moves. A first version, which measured a column's edge from the median start of its lines, had pushed a paragraph of Oracle's BI Publisher guide across its table without moving a score, and reading that one changed page against its image caught it before anything was committed.
- **A two-line answer (the same night).** Where the answer wraps across its slash ("Yes /" over "Optional") beside a
  label that wraps ("Accidental" over "Breakage"), the second line had been left as a row of its own with no event
  named; now it carries the label on. It gave ten sheets tuned on their row and answer, and two sheets in the hidden fifth, never looked at, gained the same way. Every prescribed event on every graded sheet now opens a row of its own, and the Yes/No sits in its own column for 1,880 of 1,885 events tuned on and 373 of 375 in the hidden fifth. On the benchmark not one score or page moves.
- **A label run together with its answer (early the next morning).** CGU's and WFI's contents sheets print the
  answer where every other row's answer starts, but a little way after the label, and the text layer joined the two
  into one line ("Actions of the sea No", "Items away from Yes insured address"). A line is now divided where a word
  starts on the edge the other rows' answers start on, after a gap wider than a word space. CGU's and WFI's two contents sheets each gain their answer, and a sheet in the hidden fifth, never looked at, gains its last two. The Yes/No now sits in its own column for 1,884 of 1,885 events tuned on and all 375 in the hidden fifth; the one left is on Honey's landlord building sheet, where the label is set tight against its answer. On the benchmark no score moves, and the markdown changes on 6 of 481 pages: 4 read better against their images, 1 is a false table on an index page rearranged, and 1 leaves a hyphenated word in two parts. A first version without the two guards had made a table of an address page, cut a census profile's title into pieces and broken a fund table's heading; reading its 12 changed pages caught all three before anything was committed.
- **Two insurance pages the run-together rule broke, and the guard that mends them (the same morning).**
  Re-scored on your insurance set, the rule had cut Bank of Melbourne's "you were living in the" off its bullet into the
  next column and shredded Direct Insurance's covered and not-covered lists row by row: it read a list's hanging indent
  as a column edge. A line's start now counts toward an edge only where something sits to its left. Your insurance set now scores 199 of 229, one more than on 13 September: 23 of its 25 pages convert exactly as they did then, and the two that differ read no worse against their images. On the benchmark no
  score moves, and of the six pages the run-together rule had changed, a soil table now reads as it did before that
  rule, its sub-labels back in the label column. Every table rule is now scored on your insurance set, check by check,
  before it is committed.

The scorer is `bench/tools/insurance_score.py` (it undoes markdown escapes first, or D024's "\$500"
would fail every price check), and the dossier is built by `bench/tools/insurance_dossier.py`.

## Icons, answered on your library, 9 September

You asked how TrueDoc could tell which icons carry meaning and then work out what they mean. Measured
across all 1,176 of your documents rather than guessed: 28% use icons, averaging about seven distinct
symbols each; only **6% carry a legend page**, but an icon sitting beside its own label somewhere is
four times more common - so your own observation (if the words already carry the meaning, the icon is
illustration) is both the filter and the way to learn what a symbol means. All 15,085 icon uses in
the corpus are only **171 distinct shapes**.

You then ruled on 159 of them in a review page, and overrode the machine on 92 of the 119 it had an
opinion about. Most of what it had flagged were parts of pictures - a feature on a floor plan, a
light shade, a car wheel - and most of the "letters" it wanted to discard were words the text layer
already had anyway. **Verdict: not worth building, and no GPU rental needed.** The one document where
icons genuinely carried meaning is the Huddle policy below, already fixed. `docs/ICONS_REVIEW.md`
has the detail. The one thing still open is yours: the directional arrows that tell a reader what to
read next, which is a reading-order question rather than an icon one.

## Fixed on your own documents, 8 September (evening)

Your Huddle Black policy's benefit table used to convert with **every coverage cell empty**: the
row labels were all there, but the ticks and crosses were gone, so "Emergency storage of your
contents" came out blank where the page says covered for Home and not for Contents. That is the
meaning of an insurance table inverted, not a lost detail, and the benchmark never showed it
because no benchmark page is built that way. Two causes, both fixed and tested: the mark reader
accepted marks only between 3 and 30 points, and that page is laid out at 1920 x 1080 rather than
612 x 792, so its 40-point icons were rejected as too big; and those ticks and crosses are white
glyphs knocked out of a solid coloured disc, so what carries the meaning is the hole, not the ink.
The page now converts row for row. No benchmark page changed (134 large pages and all 110 pages
carrying a mark are identical), so this is worth nothing on the exam and a great deal in the
product - which is the reason your library is the test bed.

## Known limits today

- On a few of your Key Facts Sheets a prescribed event's Yes/No still runs into its label or its exclusions; the
  shapes left are named under Next in `docs/PROGRESS_LOG.md`.
- A cover page's issuer, ABN and registered office are dropped when the layout model labels the block a page footer.
- A PDF whose own text layer has lost letters to its ligatures ("ofer", "fnd", "Certifcate") is trusted as it stands.
- The five limits below were written on 6 and 7 September and have not been measured again since.
- Handwritten pages and old maths scans stay empty: the classical OCR engine cannot read them, and TrueDoc leaves such a page empty rather than fill it with nonsense (61 of the 79 benchmark pages that are still empty are handwriting). The optional vision stage reads them when you switch it on, with a rented GPU or an API key.
- A sideways picture of a table on a page whose text layer holds only the table's title is not read: the title makes the page count as readable, so it is never OCR'd (one benchmark page).
- Tables that are pictures, and the 24 benchmark pages whose tables are never detected, still score as missing.
- Multi-column pages lose whole sentences more often than they misorder them; the page-by-page census is in `docs/PROGRESS_LOG.md` (5 September).
- This machine has no NVIDIA GPU, so anything that needs a vision model is slow locally, and nothing calls a model unless you switch it on.
