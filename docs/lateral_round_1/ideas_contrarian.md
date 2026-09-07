# Contrarian round: black hat with a product lens, then green hat

7 September 2026. Read: the evidence pack, ARCHITECTURE, STATUS, DECISIONS (plus OKF_SPEC, ROADMAP, BENCHMARKS, `model.py`, the confidence and warning code in `pipeline.py`). Not read: M14. Nothing under `truedoc/` or `docs/` was touched; no conversions were run. What I did run, read-only: a census that asks, for every failing text-bearing check of run 48, whether the wanted text exists in the PDF's own raw text layer (PyMuPDF, no TrueDoc) and whether it exists in our output. The script is saved as `bench/out/swarm/ceiling_census.py` (three minutes to run) and its per-check results as `bench/out/swarm/ceiling_results.json`. Every number below marked [verified] comes from that census or from files in this repository; hours are my estimates [assumed].

**Verdict in two sentences.** A *perfect* classical run, one that wins every failing check whose wanted text already exists in evidence we hold, would score about 72.5 on this benchmark: below Marker (76.1) and 10.6 points short of Chandra (83.1). About 27.5 of the remaining 33.3 points sit behind pixels that only a stronger pixel reader can turn into characters, and half of all remaining failures are on scanned pages of a kind the owner's library does not contain.

---

## Part one. Black hat: the classical path is finished on this benchmark

### 1. The census

Run 48 leaves 1,896 failing checks [verified: `failed_tests.jsonl`]. For the present, order and table checks (766 of them) I sorted each into one of five buckets, using the checker's own normalisation and matching:

| Section (check type) | failing | A: our output is empty | B: in the raw layer, not in our output | C: in our output, check still fails | D: page has a layer, wanted text in neither | E: no text layer, our OCR did not get it |
|---|---|---|---|---|---|---|
| Long tiny text (present) | 90 | 0 | 8 | 0 | 29 | 53 |
| Multi-column (order) | 233 | 4 | 37 | 17 | 149 | 26 |
| Old scans (present + order) | 417 | 290 | 0 | 0 | 0 | 127 |
| Tables (table) | 226 | 5 | 17 | 143 | 54 | 7 |

[verified] Buckets B and C are the mechanical pool: the characters are already ours and a rule could, in principle, place them. Buckets A, D and E need pixels read better than today, or are unwinnable (some references contain typos; the pack already notes two such pages).

The other sections: formulas 387 failing, all on born-digital pages (mechanical in principle); headers and footers 27; baseline 76, every one of them an empty output file (61 old scans, 10 old-scan maths, 3 headers and footers, 1 multi-column, 1 tables) [verified: census of the output files]; old-scan maths 439, of which 10 pages are empty, and 15 of the 36 failing pages do carry a hidden OCR text layer, which cannot yield LaTeX [verified].

### 2. The arithmetic of the ceiling

The overall score is the mean of eight section pass rates, so one check in a section with N checks is worth 100/(8N) overall points [derived from the pack's scoring description].

Mechanical pool, generous (every B and C check, every formula and header check, and all 54 of the multi-column D checks that lie within three edits of the layer):

- formulas 387 × 100/(8×2927) = 1.65
- headers and footers 27 × 100/(8×760) = 0.44
- tiny text 8 × 100/(8×442) = 0.23
- multi-column (37+17+54) = 108 × 100/(8×884) = 1.53
- tables (17+143) = 160 × 100/(8×1022) = 1.96
- **total 5.8 points** (strict, without the ambiguous 54: 5.0) [derived]

Pixel-bound: old scans 417 × 100/(8×526) = 9.91; old-scan maths 439 × 100/(8×458) = 11.98; tiny text 82 → 2.32; multi-column 125 → 1.77; tables 66 → 0.81; baseline 76 → 0.68; **total 27.5 points** [derived]. Check: 66.7 + 5.8 + 27.5 = 100.0.

So the best classical run possible is about 72.5, and that assumes winning *every* reachable check, which no run has ever done: the best table run (48) won 17 of a pool then near 180.

### 3. Which failure groups cannot move without a better pixel reader, and why

**Old scans, 417 text checks and the 439 old-scan maths checks (the two lowest sections, 20.5 and 4.1).** Not one failing old-scans page has a text layer [verified]. 290 checks sit on the 61 pages we leave empty because RapidOCR's read fails the confidence gate (handwriting, old type). The other 127 are pages we do read, wrongly: of the 71 failing present checks on read pages, 22 miss by one or two letters, 9 by three to five, 9 by six to ten, 31 by more than ten [verified, edit distance to the nearest match in our output]. And 203 of the 251 failing old-scan present checks allow zero edits [verified]: the read must be letter-perfect over a sixty-character snippet of nineteenth-century type. A sample of our own read of an image-only page (tiny text, `17_pg17`): "ncarlya quarter", "itemthe abkaree", "Janlnah". No rule on words, lines or blocks changes a letter; only a reader of pixels does. The 3 September experiment is the proof by construction: a vision model on the 94 empty pages alone was worth +5.6 [verified: BENCHMARKS, 62.2 → 67.8].

**Long tiny text, 82 of 90.** 53 failing checks are on 16 pages that have *no text layer at all* (PyMuPDF returns zero characters and one image) [verified]; our RapidOCR read them, imperfectly. 29 more are on pages whose hidden layer is wrong and our own OCR is no better (the pack: 13 of 66 strings against the layer's 9).

**Multi-column, 125 to 179 of 233.** 95 of the 149 bucket-D checks are four or more edits from anything in the layer: the hidden OCR layer simply does not contain the sentence [verified]. 26 are on pages with no layer, 4 on empty pages. The remaining 54 are within three edits of the layer, and a sample of eight shows what they are: three are the layer's own line-end hyphenation ("ex- hibit", "concentra- tions"), two are typos in the *reference* ("betweentwo", "U.S.source": to pass them we would have to copy the mistake), three are one-letter differences that only pixels can adjudicate ("2007" against "2005"; "Heinsch, F., Vernaux" against "Heinesch, B., Yernaux") [verified]. Even counting all 54 as mechanical, the section's ceiling rises by 1.5 points, not 15.

**Tables, 66 of 226.** Pictures of tables, vector-drawn text, no-layer pages, empty pages: nothing to place.

**Baseline, 76.** Empty pages. Every one of them is an old-scan or image-only page.

### 4. The mechanical pool is a long tail, and the rate says so

- Tables (the biggest pool, 160): the 143 C-bucket cells sit in 90 pages: 34 pages with one failing check, 21 with two, 13 with three, 8 with four, 14 with five or more [verified]. 116 of the 143 are inside a table we *did* emit (101 markdown, 15 HTML) with the wrong neighbour or heading; 27 are in prose [verified]. Each rule of runs 41 to 48 won 2 to 17 checks and lost 0 to 9 [verified: BENCHMARKS]. Runs 37 to 48, about two days of work, moved the overall score from 65.6 to 66.7, of which tables gave 0.9 [verified].
- Formulas (387): 216 pages, 125 of them with a single failing check [verified]; STATUS records the rate as about a tenth of a point per hour.
- Multi-column: the 52 mid-sentence block breaks have "no single pattern" (the pack); the 37 bucket-B sentences are real (example: `0208fbb5…` page 1, the abstract's "Findings thus supported the desirability of applying wood residue…" is in the layer and absent from our output [verified]), each on its own page.
- The one large mechanical shortcut nobody has named, a tagged PDF's structure tree (reading order, table cells, headings declared by the producer), is closed: 0 of the 239 failing multi-column, tables and headers pages carry a StructTreeRoot, and neither do the owner's four PDFs [verified].

Put together: at the recent rate (+1.1 in two days, with the easiest table rules already taken) capturing even half of the 5.8 would take a week or two and land near 69.5, still under Marker; the remaining 27.5 do not move at all. The GPU experiment took 55 minutes and under a dollar for +5.6.

### 5. The product lens on part one

947 of the 1,896 remaining failures (old scans 418, old-scan maths 439, tiny text 90) are on scanned pages [verified]. The owner's four sample documents are born-digital with exact text layers: 40 to 117 pages each, 0 to 4 images (POL1085 has 157, all icons), no scans [verified]. Every hour spent on the benchmark's scanned half buys the product nothing, and the benchmark's single pages cannot even *ask* the questions a policy reader asks (part two). The classical path is finished here in both senses: it cannot reach the published leaders, and the remaining points are the wrong points.

### 6. What would falsify this

- **F1. Bucket D is mostly ours.** If a full read of the 54 near-miss multi-column checks shows 40 or more are our own artefacts (hyphenation, spacing, column joins), the multi-column ceiling rises by about 0.6. Not enough alone.
- **F2. "Pixel-bound" does not mean "large-model-bound".** RapidOCR is one small CPU model; the argument assumes its family is exhausted. If a different small, permissively licensed CPU reader (Tesseract with its historical-print models, PP-OCRv5 server models, kraken's historical models) finds 30% or more of the 127 old-scan strings we misread, a classical route worth two to four points exists. This is the real hole, and the cheapest to test.
- **F3. The tables pool is patterns, not a tail.** A single engineering day on bucket C that wins 60 or more net checks with the held-out fifth rising in step would show the pool is a few patterns. Runs 41 to 48 averaged about 8 net per rule.
- **F4. The page teaches its own font.** On pages whose hidden layer is *mostly* right (tiny text D, multi-column D), cluster the glyph images, label each cluster by majority vote of the layer's characters, and re-read the minority. A page-local nearest-neighbour reader is a classical pixel reader. If it corrects a third of the 124 layer-wrong checks, that is +0.9 without a model in the usual sense. The fact that would kill it: most layer errors are between look-alike glyphs (e/c, quotes), which a nearest-neighbour reader confuses too.

### 7. The cheapest experiment that settles it

Two parts, together under two hours of engineer time, no run needed:

1. **The census is the instrument.** Run `bench/out/swarm/ceiling_census.py` after each run. When B+C for tables and multi-column stop shrinking while runs keep landing, the tail has been reached; that is the stopping rule. It also prints, for bucket D, how far each snippet is from the layer, which settles F1 by reading the 54.
2. **Settle F2 in one hour.** On the 37 non-empty old-scan pages (127 checks), run Tesseract (Apache-2.0, CPU) with `eng` plus its historical-print training data, and count wanted strings found within each check's edit allowance, against RapidOCR's count today. Under 20: the small-OCR family is exhausted and only a vision model remains, which is the decision already taken (D014). Over 40: there is a classical route worth taking before any GPU.

---

## Part two. Green hat: what a meaning-first product optimises

What the benchmark tests: a sentence is present; A comes before B; a cell has the right neighbour; a formula matches; a header is gone. What a reader of a product disclosure statement needs and the benchmark can never test, because its unit is one page and its questions are about text, not meaning:

- **Polarity.** The same bullet means opposite things under "You are covered for:" and "You are not covered for:". ALDI's PDS has 43 pages with the first line and 48 with the second; POL1085 sets "What's covered?" and "What's not covered?" side by side on eight pages; HCPDSA has "What is insured / What is NOT insured" as a repeated two-column header on ten pages [verified].
- **Scope.** "Included for: Home ✓ Contents ✓" (31 pages in ALDI); "Buildings and/or contents" (POL1085); the benefit applies to one cover or both.
- **Numbers with their referents.** "Up to $2,000 per item and $6,000 in total" means nothing without the row label "Watches, jewellery…". RACQ's PDS carries 209 dollar amounts and 214 mentions of "sum insured"; ALDI 62 and 106 [verified].
- **Definitions.** "Flood", "storm", "actions of the sea" have policy-specific meanings; POL1085's definitions table holds 51 terms, 41 of which are used earlier in the body [verified].
- **Cross-references.** "see page 46", "pages 23 and 28 respectively": 26 in POL1085, 22 in ALDI, 51 in RACQ [verified]; every one is a claim about the document's own structure.
- **Continuity across pages.** Tables and clause lists continue over page breaks with repeated headers; 11 (ALDI), 16 (POL1085), 5 (RACQ) and 8 (HCPDSA) pages open by repeating a short line of the previous page, and HCPDSA says "continued" near the top of 20 pages [verified].
- **Furniture that only repetition reveals.** ALDI prints the same seven navigation tabs on 99 of 117 pages and "Household Insurance Policy | Page N" on 98 [verified]; the pack itself notes running heads cannot be confirmed on one page.
- **Completeness and doubt.** Today the document confidence is a constant by page kind (0.9 digital, 0.6 OCR layer, 0.5 vision, 0 unreadable) [verified: `pipeline._estimate_confidence`]; it says nothing about *this* page's difficulty, and the body has no mark for mechanical doubt, only `[^inferred]` for models.

The ideas, in the order I would build them. Each: the need, the mechanism, cost, a one-hour test, the strongest objection.

### Idea 1. The document teaches itself: a cross-page evidence pass

**Need.** Strip furniture that single-page rules cannot prove, map printed page numbers to PDF pages, and stitch tables and lists that continue across pages, so a limits row is never separated from its header.

**Mechanism.** Before rendering, hash every line as (text with digits masked, y position rounded to 3 pt). A key that recurs on three or more pages at the same position is furniture: removed from the body, listed once under `truedoc.furniture` with its page count. From the furniture, read the printed page number pattern ("Page 32") and build `printed page → PDF page`, stored under `truedoc.page_map`. Then, for each page break: if the last block of page N is a table and the first block of page N+1 is a table whose header row repeats it, or whose column edges match within 2 pt, merge them and drop the repeated header; if page N ends mid-sentence and page N+1 opens with body text at the same size, join (the OKF spec already promises this for paragraphs; tables and lists are the gap). Everything merged is listed under `truedoc.joins` so a reviewer can undo one.

**Cost.** 6 to 10 hours [assumed]. **One-hour test.** The census I ran is the test: on the four sample PDFs, the repetition rule finds ALDI's seven tabs and page footer (99 and 98 pages), POL1085's "What's covered? / What's not covered?" header pairs (8 pages), HCPDSA's "Product Disclosure Statement" (38 pages) [verified]. The remaining hour: list every key caught at the threshold of three pages and count the false positives by eye (legal boilerplate repeated on purpose, benefit template lines that recur at varying positions).

**Strongest objection.** Template lines ("Limit:", "You are covered for:") recur on dozens of pages; position must stay in the key or the rule strips meaning, and even then a template line that happens to land at the same height three times will be lost. Guard: never strip a line that is the first line of a block with more than one line, and cap furniture at two lines of text.

### Idea 2. Benefit records: polarity and scope from the document's own template

**Need.** A bullet's meaning is (benefit, polarity, scope). Markdown flattens the two-column "covered / not covered" layout into one list, and a downstream reader (human or LLM) cannot tell which side a bullet came from once a column cut goes wrong.

**Mechanism.** Learn the template from the document, not from a hard-coded insurer: short lines that recur on many pages at varying positions (from idea 1's leftovers) and are followed by lists are the template fields ("You are covered for:", "You are not covered for:", "Limit:", "Included for:", "Optional for:"). Each benefit heading then becomes a record rendered in a fixed order: heading; each field as a bold label with its bullets kept under the field whose region contains them by geometry; "Included for: Home ✓ Contents ✓" as a one-row table; example sentences ("For example, we cover you if a gecko…") kept, labelled as examples with a blockquote so they are not read as the rule. Self-check: every record has the same field set as the majority; a missing field, or a bullet that straddles the gutter between the two columns, is written to `truedoc.review` with page and snippet.

**Cost.** 12 to 16 hours [assumed]. **One-hour test.** With PyMuPDF only: ALDI has 54 pages with template lines and 27 with all four fields [verified]; for those 54, measure the x-gap between the "covered" and "not covered" columns on side-by-side pages (POL1085, HCPDSA) and count bullets whose box crosses the gap. Zero crossings means geometry alone assigns polarity; each crossing is a page to look at.

**Strongest objection.** Four insurers, four templates; the learning rule will meet a document whose fields are not short lines at all (HCPDSA's "We will not cover (continued)"). Then the record falls back to plain headings and nothing is lost, but nothing is gained either. The check on the field set is what keeps this honest: a document where the template is not found simply gets no records.

### Idea 3. Cross-references resolved, as a check on our own structure

**Need.** "see page 46" is meaningless in a markdown file, and it is also a free assertion about the document that we can test: page 46 must contain the benefit named.

**Mechanism.** Parse "see page N", "pages 23 and 28", "section X", and quoted benefit names before them ("under the included benefit 'Broken glass – home' see page 46"). Using idea 1's page map, find the heading on printed page N that best matches the quoted name; write `see 'Broken glass – home' (page 46)` as a link to that heading's anchor, keeping the original words so nothing is invented. Unresolved references (no page map, no heading within one page of N, quoted name not found) go to `truedoc.review` as "cross-reference unresolved": a signal that either our headings or our page map are wrong.

**Cost.** 4 to 6 hours [assumed]. **One-hour test.** Already run in outline: ALDI's printed numbers were found on 98 of 117 pages, and all 10 quoted references resolved to the named printed page [verified]. The hour: extend to unquoted references ("see page 100" for the excess) and to the other three documents, and count the unresolved.

**Strongest objection.** Printed page numbers are not PDF indices (front matter, roman numerals, two-up scans), and a benefit name can appear on the target page in running text without being the heading. Resolve only to headings, keep the printed number visible, never rewrite the sentence.

### Idea 4. Defined terms as a glossary and a check

**Need.** A reader must know that "flood" in this policy is the defined "flood", and a downstream program needs the glossary as data.

**Mechanism.** Detect the definitions section by its shape: a two-column region where the left column holds short lines (one to four words) and the right holds sentences, often under "When we say / We mean" or "means". Emit it as a table (already done) *and* as `truedoc.defined_terms: [{term, page}]`. Do not mark uses in the body (noise, and lexical matching of "we", "you", "home" would fire everywhere); instead run two checks and write the results to the front matter: a defined term never used in the body (a hint that a sentence was dropped or the term is split across a line), and a bold short phrase in the body that is not in the glossary (a heading, or a term the definitions missed).

**Cost.** 5 to 8 hours [assumed]. **One-hour test.** My geometric read of POL1085 pages 74 to 82 found 51 candidate terms, 41 used earlier in the body; the 10 unused are junk the heuristic swept up ("Preparation Date: 13/09/2022", "SPDS455DIR 09/22") [verified], which is itself the point: the unused list is where the mistakes show. A bold-face heuristic found nothing there (the terms are not bold), so the detector must be geometric. The hour: run it on ALDI's and RACQ's definitions and count junk.

**Strongest objection.** "We, our or us" and "You, your" are defined and appear on every page; plurals and possessives defeat exact matching; a glossary of 51 terms with a dozen false entries is worse than none. Keep it as front matter, never inline, and require a term to be a noun phrase of one to four words.

### Idea 5. A typed ledger: every amount, percentage and period, with its label

**Need.** The numbers decide claims. A dropped "$1,263" or a limit separated from its row label is the worst error a converter can make, and the benchmark's cell checks are the only thing that approximates it.

**Mechanism.** From the text layer (exact on digital pages), extract every money amount, percentage and period ("72 hours", "21 days") with its nearest label: the row's first cell in a table, else the nearest preceding heading or bold line. Write `truedoc.amounts: [{page, text, label}]`. Two checks: conservation (every amount in the layer appears verbatim in the body: a miss goes to `truedoc.review` with the page and the amount) and consistency (an amount that appears in a summary table must recur in the benefit's own section, and vice versa; a mismatch is reported, never edited, because summaries legitimately round).

**Cost.** 4 to 6 hours [assumed]. **One-hour test.** On run 48's table pages, a crude number ledger (numeric tokens in the layer absent from our output) flagged 7 of the 10 pages where the census says we dropped a cell, against 33 of 69 other failing pages [verified]: a weak but real signal. Honest negative result: three cheap general ledgers (bag of words, longest run of absent words, layer lines or line pairs not found contiguously in the output) did *not* single out the multi-column pages where run 48 dropped a sentence (31% of them flagged against 26% of the rest) [verified]. Two reasons: those benchmark pages carry noisy scanned layers, so every page looks lossy, and the tears sit at block boundaries. The owner's documents are born-digital with exact layers, so the hour should be: run the ledger over the four samples with our current outputs and read every alarm on two documents.

**Strongest objection.** Labels by proximity are wrong in multi-column layouts and in tables with stacked headings; a ledger that reports 50 false alarms per document is ignored. Gate it to digital pages, subtract furniture (idea 1) and known-dropped kinds, and rank alarms by amount size.

### Idea 6. Two routes, one page: mechanical disagreement as doubt

**Need.** Show the reader what is uncertain without any model. The project's own principle is "check every model's answer against raw evidence"; the mechanical stages deserve the same.

**Mechanism.** Both routes already exist: the text-layer-only path (`--no-layout`, about a page a second) and the layout-model path. Run both on every page, align the two bodies at block level (word-sequence alignment, then group by block), and record each disagreement by kind: a block that is a table on one route and prose on the other, a different column order, a different heading level, a table with a different column count. The fused output stays as it is; each disagreeing block gets the tag `[^check]` (a mechanical cousin of `[^inferred]`, one definition per document) and a `truedoc.review` entry. Per-block confidence, which the roadmap notes does not exist yet, falls out as "the routes agree".

**Cost.** 8 to 12 hours [assumed]; the aligner is the work. **One-hour test.** Convert the four samples both ways (the engineer may run conversions; I did not), diff the two bodies with a word-level differ, and count disagreeing blocks per document; then open ten disagreements and record how many coincide with a real error in the fused output. If fewer than three of ten do, the signal is too weak to show a reader.

**Strongest objection.** The two routes share the text layer, the line builder and the word-gap rules, so they share their blind spots (glued words, dropped lines, hyphenation): agreement is not proof. This catches structural doubt only, and it makes conversion about a third slower.

### Idea 7. Doubt shown to the reader: one tag, one ranked list, an honest confidence

**Need.** A reviewer of a 117-page PDS cannot read it all; they need the ten places to look, ranked by what is at stake, and a confidence figure that means something.

**Mechanism.** Compose a per-block doubt score from signals that already exist or come from ideas 1 to 6: provenance (`layout-table-ocr`, `ruled-rebuilt`, `textlayer-aligned` carry more doubt than `textlayer`), the table finder's confidence, a column cut voted by a thin majority, a hyphenation repair that did not make a dictionary word, OCR line confidence, a ledger miss, a route disagreement, a template record with a missing field, an unresolved cross-reference. Stakes: a block that contains an amount, a percentage, a period, or a polarity field ("not covered") weighs more. Body: blocks above a threshold get `[^check]`. Front matter: `truedoc.review`, sorted by doubt × stakes, each entry with page, kind, snippet and the reason in plain words ("column cut chosen by 4 votes to 3; two bullets may belong to the other column"). Document confidence becomes 1 minus the stakes-weighted share of doubtful blocks, replacing today's constant by page kind.

**Cost.** 6 to 10 hours for the plumbing [assumed]; calibration is ongoing. **One-hour test.** No conversion needed: the benchmark's failing list is a free labelled set. Take the 188 table pages of run 48; compute a two-signal doubt score per page (share of numeric cells, variance of column count across rows) from our outputs alone, and check whether the 90 failing pages rank above the 98 passing ones. Any separation at all justifies the plumbing.

**Strongest objection.** Alarm fatigue: a tag that fires on every fifth block is ignored and makes the file ugly; the ranking is only as good as the stakes rule, which is insurer-agnostic only if "amount" and "polarity" are detected from the text, not from a template. Start with a hard cap (at most one review entry per page, at most twenty per document) and raise it only when reviewers ask.

### Idea 8. Schedules and certificates as key-value records, checked against the wording

**Need.** The owner named schedules. A schedule or certificate of insurance is a form: policy number, period of insurance, insured, address, sums insured, excesses, endorsements. Its meaning is a set of pairs, and half its values must agree with the policy wording it goes with.

**Mechanism.** Detect label-value layout: a short label (bold, or left column, or followed by a colon) with a value on the same line or the line below, repeated down the page; emit as a two-column table and as `truedoc.fields: [{label, value, type}]` where type is date, money, address, text, parsed only when the parse is exact. Checks: dates parse and the period's end is after its start; every money value appears in the wording's excess or limit options when the wording is converted in the same bundle (OKF bundles are on the roadmap, M8); an endorsement named in the schedule appears as a heading in the wording.

**Cost.** 6 to 8 hours [assumed]. **One-hour test.** No schedule is in `samples/` [verified: four PDFs, all PDS or policy wordings], so the hour starts by asking the owner for two schedules and two certificates and ends with a PyMuPDF listing of label-value pairs per page and a count of how many parse cleanly.

**Strongest objection.** Untested on real material, so this is the idea most likely to be wrong in shape; schedules are often generated by policy-administration systems as text-heavy letters rather than forms, in which case the pairs are in prose and the detector finds nothing. Cheap to find out, which is why the test is "ask for two".

---

## Single best bet

**Idea 1, the cross-page evidence pass**, with idea 3 riding on its page map. It is cheap (a day), certain (the census already shows what it will find on all four of the owner's documents: 99-page tab strips, repeated table headers, 11 to 16 continuation pages per document), impossible on the benchmark by construction, and it is the foundation the meaning ideas stand on: polarity records need the template lines separated from furniture, cross-references need the page map, the ledger needs furniture subtracted before it can be quiet. The biggest *prize* is idea 2 (polarity and scope), but it is the most insurer-specific and should be second.

**The fact that would flip it:** if the owner's library is mostly one- to three-page documents (schedules, certificates, key facts sheets), cross-page evidence has nothing to work with, and the best bet becomes idea 5 (the typed ledger) with idea 7 (the ranked doubt list). A count of pages per document in the library settles it in a minute.

## Claims in the evidence pack I doubt, with what I found

1. **"Long tiny text: 54 snippets are not in the hidden OCR layer at all."** 53 of the 90 failing checks are on 16 pages that have *no text layer at all* (zero characters, one image); those pages were read by our RapidOCR, not by a hidden layer [verified]. Only 29 are "layer present, layer wrong"; 8 are in the layer and dropped by us (the pack says 4).
2. **"Multi-column: 148 near misses are the hidden OCR layer's own character errors."** 95 of the 149 are far from anything in the layer (four or more edits), consistent with the claim; but the 54 near ones are a mix of the layer's hyphenation (which a rule can handle), typos in the references (which nobody can), and one-letter differences [verified on a sample of eight]. The "layer's own errors" framing is right in bulk and wrong in detail, and the detail is where the only mechanical multi-column headroom is.
3. **"Baseline 74 failing, 71 of them empty pages."** The failed-tests file holds 76 baseline failures and there are 76 empty output files [verified]. Minor, but the two numbers should agree.
4. **"Tables: 70 present but not structured as a table, 75 relation errors."** Of the 143 checks whose cell text is in our output, 116 sit inside a table we emitted and 27 in prose [verified]. The pool is dominated by tables we found and built wrongly, not by tables we missed; that changes which rules are worth writing.
5. **The implicit claim that old-scan maths pages have nothing to read.** 15 of the 36 failing pages carry a hidden OCR layer [verified]. It cannot yield LaTeX, so the conclusion stands, but the text checks on those pages (the 10 baseline ones aside) deserve the same census before they are written off.

## What I ran (read-only)

- `bench/out/swarm/ceiling_census.py`: the bucket census; results in `bench/out/swarm/ceiling_results.json`.
- PyMuPDF inspections of the four sample PDFs (page counts, images, tags, keyword counts, repeated lines, printed page numbers, cross-references, template lines, definitions, continuations) and of individual benchmark pages; scripts in my session scratchpad, all under forty lines, all reproducible from the numbers quoted.
- No conversions, no benchmark runs, no page checks, nothing installed, nothing edited under `truedoc/` or `docs/`.
