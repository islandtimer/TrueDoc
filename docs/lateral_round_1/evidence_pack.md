# Evidence pack for the lateral-thinking round (7 September 2026)

You are one of several thinkers looking, independently, for ways around the problems below. Read this file first, then `docs/ARCHITECTURE.md`, `docs/STATUS.md` and `docs/DECISIONS.md` in the repository. Do NOT read `docs/M14_MARKER_MINERU.md`: the owner wants this round to think laterally, not to follow what other tools do.

## What TrueDoc is

TrueDoc turns any PDF into markdown with YAML front matter (the Open Knowledge Format) on an ordinary CPU, with no large vision-language model. It wins or loses on meaning accuracy: every word, number and relation on the page in the right place, nothing invented. The public yardstick is olmOCR-bench, 7,010 checks over 1,403 single PDF pages in eight sections. The best published tool scores 83.1 overall; TrueDoc's latest run (run 48) scores 66.7.

Pipeline in one breath: the PDF's own text layer (characters with boxes, fonts, sizes) is read with PyMuPDF; when a page has no usable layer it is rendered and read by RapidOCR (an English recognition model, a small CPU network); a layout model (RT-DETR, CPU, about three seconds a page) labels regions (text, title, table, figure, caption, header, footer, formula, list); heuristics build words, lines, blocks, headings, lists, tables (ruled tables from drawn lines, unruled tables from aligned whitespace), footnotes and reading order; formulas are rebuilt as LaTeX from the text layer's maths fonts; markdown is rendered. Every page is one page: the benchmark gives single pages, so nothing can be learned from a document's other pages.

## Hard constraints

- CPU only in the free tier. No large vision-language model there. Small task models are allowed if their licence permits a commercial service.
- No AGPL code. No model weights whose licence bars competitors or commercial use.
- Nothing invented: a page that cannot be read produces an empty file rather than guessed text (the owner's decision). Hidden text (invisible or white text in the PDF) is kept out of the body.
- Plain-English, example-driven communication with the owner.
- Ideas, not code: this round proposes; the engineer tests and builds.

## The score by section (run 48) and how each section is checked

| Section | Score | Checks | What the checks are |
|---|---|---|---|
| ArXiv maths | 86.8 | 2927 | a formula must appear as LaTeX matching the reference after normalisation |
| Old-scan maths | 4.1 | 458 | old printed maths, scanned: text and formulas must be present |
| Tables | 77.8 | 1022 | a cell with a value must exist, and its neighbour above/below/left/right or its column/row heading must match |
| Old scans | 20.5 | 526 | old scanned pages, mostly handwriting and old print: text must be present |
| Headers and footers | 96.3 | 760 | a running head, foot or page number must be ABSENT from the output |
| Multi-column | 73.6 | 884 | text A must appear before text B (reading order) |
| Long tiny text | 79.6 | 442 | a sentence of tiny type (dictionary pages, newspapers, book scans with a hidden OCR layer) must be present |
| Baseline | 94.7 | 1394 | the output must contain alphanumerics, no runaway repetition, no forbidden characters |

The checker's text matching: whitespace runs collapse to one space, curly quotes and dashes map to plain ones, bold and italic markers are stripped, but `#` and `$` are not; a text check allows an edit distance of 0 to 2 characters (given per check) over the whole snippet, so one wrong character in a 60-character snippet fails it. A table cell must match with a small edit allowance, and headings are matched against each heading cell separately (stacked headings must be joined into one cell). Markdown tables are read with the first row as heading and the first column as row heading; HTML tables honour `th`, `colspan` and `rowspan`.

## Where the failing checks are, counted from the outputs

**Tables, 227 failing.** 152 are a cell not found or no table at all: 46 are text that exists only as a picture (figures, screenshots), 21 are pages with no text layer whose OCR read was rejected or wrong, 70 are text that is present in our output but not structured as a table (a census printout in fixed-width type with `|` and `:` separators; a Polish form; a botanical key; an attendance list with tick marks; rows whose cells are three staggered lines each; two-line cells the reference splits into rows), 15 are text we dropped (a lake diagram's label stacks inside a figure region; a table printed sideways on a landscape page, whose rotated lines the table finder skips; a page number the reference counts as a cell). The other 75 are relation errors: the cell exists but its neighbour or heading is wrong (stacked headings not joined, headings glued across columns by narrow spacing, group labels not spanning their rows, a label column offset from its numbers).

**Multi-column, 233 failing, all reading-order checks.** 148 are not order at all but near misses in the text: the hidden OCR layer's own character errors on scanned pages (e to c, quotes, dropped letters), small-caps names (now fixed), glued words, and 11 where inline maths in prose is written as `$k=2$` while the reference wants `k = 2`. About 16 are true ordering mistakes (sidebars, pull quotes, captions between columns) and about 52 are sentences broken at a block boundary (footnotes, captions and forms interleaved), each a page of its own.

**Long tiny text, 90 failing.** 54 snippets are not in the hidden OCR layer at all (the layer, made by some other OCR years ago, has the words wrong); 32 are near misses of one to three characters; 4 are in the layer but dropped by us. Our own OCR read of those pages is not better than the hidden layer (tried: 13 of 66 strings found against the layer's 9).

**Old scans, 418 failing; old-scan maths, 439 failing.** 71 of these pages produce an empty file because the OCR read is rejected (handwriting reads as noise; confidence under 0.75) or the page is unreadable. The rest are pages we do read, with many wrong characters. RapidOCR's English model cannot read old typefaces, handwriting, or non-Latin scripts (a Japanese table's headings). An experiment on 3 September replaced the 94 empty pages with a vision model's reading and gained 5.6 points overall.

**Headers and footers, 28 failing.** Titles that repeat the running head's words (cannot be dropped without dropping the title); footnotes the benchmark counts as footers (we keep footnotes by decision, 5 checks); page numbers and journal marks that survive on single pages (running heads cannot be confirmed by repetition when there is one page); a letterhead.

**Formulas, 387 failing.** Diminishing returns: radicals inside numerators, script-script exponents, hats versus wide hats, matrices with mixed delimiters, formulas the reference writes in a different but equivalent way.

**Baseline, 74 failing.** 71 are the empty pages (the check wants alphanumerics on every page).

## What has been tried and set aside, with the evidence

- Re-reading poor hidden OCR layers with our OCR engine (page level): worse than the layer.
- OCR of pictures on digital pages (`--ocr-pictures`): one page gained 4 checks, everything else nothing; off by default.
- Lowering the OCR confidence bar below 0.75: every handwriting page sits under it; the 0.75 to 0.80 band was censused and only one real table was found there (now accepted by a numeric-share rule).
- The 52 mid-sentence block breaks: footnotes, captions and forms interleaved, no single pattern.
- Vector-outline text (text drawn as paths) and sidebar pictures: nothing to read.

## Assets you may read (read-only; do not run conversions, do not edit code)

- `docs/` — architecture, status, decisions, the progress log (`docs/PROGRESS_LOG.md`, long), the OKF spec.
- `truedoc/` — the code: `extract/textlayer.py` (characters to words and lines), `segment/blocks.py`, `tables/aligned.py`, `tables/ruled.py`, `layout/fuse.py`, `ocr/rapid.py`, `pipeline.py`, `render/okf.py`, `math/`.
- `bench/runs/truedoc47-20260907-090140/failed_tests.jsonl` — every failing check of run 48 (pdf, cell or text, relation).
- `bench/data/olmocr-bench/bench_data/pdfs/<section>/` — the benchmark PDFs; `bench/data/olmocr-bench/bench_data/truedoc47/<section>/` — our outputs for run 48 (`<stem>_pg1_repeat1.md`).
- `bench/out/page_check/` — recent single-page outputs.
- The benchmark's own checker: the installed package `olmocr.bench.tests` in `.venv`.

## What we want from you

Ideas that standard step-by-step engineering would not reach. Use the lateral-thinking technique named in your brief and show your working: the provocation or challenge or random entry, the movement from it, the concept extracted, then the concrete mechanism. Do not judge ideas as you go; harvest first, then note the strongest objection to each. Prefer ideas that (a) need no large model, (b) invent nothing, (c) can be falsified in an hour with the assets above. Say which failure group each idea addresses and roughly how many checks it could touch. Wild ideas are welcome if they come with a cheap test.
