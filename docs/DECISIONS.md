# Decisions

Short records of choices that shape the project. Newest at the bottom.

## D001 - Fresh start, no reading of earlier attempts (2026-09-02)
The owner asked for a cold start and that no folders outside this repo be read. Everything here is derived from public sources and this repo only.

## D002 - Python 3.13 in a project virtual environment (2026-09-02)
Python 3.13 is used (3.14 is installed but many document-AI libraries do not ship wheels for it yet). A `.venv` inside the repo keeps the project reproducible; the machine's global site-packages are not relied upon.

## D003 - Primary yardstick: olmOCR-bench; secondary: OmniDocBench (2026-09-02)
"Meaning accuracy" is closest to olmOCR-bench's unit-test style ("is this sentence present", "is this cell left of that cell", "does this paragraph come before that one", "is this formula there"), and every tool the owner named has a published score there or on OmniDocBench. OmniDocBench (edit distance, table TEDS, formula CDM) is kept as a second opinion because the vision-model camp reports there. See `docs/BENCHMARKS.md`.

## D004 - Evidence-first architecture (2026-09-02)
Text from the PDF's own text layer is treated as ground truth for characters. Models (layout, table structure, OCR, LLM) are used to decide structure and to read pages without text, and every model output is checked against raw evidence (text layer, geometry) before it is accepted. Rationale: pipeline tools lose on structure, vision models lose on fidelity and cost; the gap between the two camps is exactly where an evidence-first design wins.

## D005 - OKF is the Open Knowledge Format (2026-09-02, confirmed by the owner 2026-09-03)
First taken to mean "markdown with a YAML front matter block" [assumed]. On 3 September the owner confirmed OKF is the Open Knowledge Format (https://github.com/GoogleCloudPlatform/open-knowledge-format): vendor-neutral markdown files with YAML front matter, not tied to any agent, framework, model provider or serving system. `docs/OKF_SPEC.md` now follows that specification (v0.2); see D012 for how the fields are filled.

## D006 - Use the official olmOCR-bench scorer, not a re-implementation (2026-09-02)
The `olmocr` package's core dependencies are light (no GPU libraries), so the official scorer is installed into the venv and used as the source of truth. Its test code (Apache-2.0) is also copied into `bench/olmocr_ref/` for reading. Formula tests need KaTeX rendering in a headless Chromium, installed via Playwright.

## D008 - Unreadable pages produce empty output, never filler (2026-09-03)
A page with no usable text and no confident OCR result yields an empty file (and a warning in the front matter), not a newline or a placeholder sentence. Reason: a benchmark scorer's fuzzy matcher counted a one-character file as matching any phrase, which inflated a section score by 45 points; more importantly, invented or noise text is worse for a reader than an honest gap.

## D009 - Classical OCR is accepted only when it is confident and word-like (2026-09-03)
RapidOCR (Apache-2.0) runs on pages without a text layer, but its output is used only when the mean line confidence is at least 0.75 and at least 60% of tokens look like words or numbers. Typewritten scans pass; handwriting is rejected and left empty. Reading handwriting needs a vision model on a GPU, which is a separate, owner-approved step.

_Amendment (2026-09-03): a confident read (mean confidence at least 0.85) whose tokens are at least 30% numbers, percentages or ranges is accepted even when few tokens are dictionary words, because tables of figures and metric names are exactly what OCR is asked to read; the same rule gates the OCR of a table drawn as a picture on an otherwise digital page._

## D010 - Hidden OCR layers are trusted for characters but not for layout (2026-09-03)
Scanned books from archive.org and similar carry an invisible text layer with meaningless font sizes and one text object per phrase. Their characters are kept (they are usually right), but lines, columns and body size are rebuilt from geometry, and size-based heading rules are switched off for such pages.

## D007 - No AGPL components in the product path (2026-09-02)
PyMuPDF's own layout add-on (`pymupdf-layout`) and DocLayout-YOLO are AGPL or commercial-licensed. TrueDoc only uses permissively licensed models and libraries (Apache-2.0, MIT, BSD) in the conversion path, so it can be used commercially without a licence purchase. AGPL tools may still be run as *competitors* in benchmarks.

**Evidence, 12 September 2026 (run 85).** With stage E of M18 the product path no longer imports PyMuPDF at
all: `tests/test_no_pymupdf.py` converts a three-page document - prose with a ruled box, a page filed on
its side, and a page carrying a hidden OCR layer - in an interpreter where `import pymupdf` raises. The
package left the core dependencies for two extras (`mupdf`, for `TRUEDOC_READER=mupdf` and the other old
readers, and `bench`, for the measurement tools). Every package the product path does import, with the
licence its installed metadata states:

| Package | What it does on the product path | Licence |
|---|---|---|
| `pypdfium2` | reads and draws every page (PDFium) | BSD-3-Clause and Apache-2.0 |
| `pdftext` | the text layer over PDFium | Apache-2.0 |
| `pdfplumber` | the ruled-table geometry | MIT |
| `pypdf` | glyph names PDFium cannot map | BSD-3-Clause |
| `fonttools` | the Adobe Glyph List and font tables | MIT |
| `torch`, `transformers` | the layout model | Apache-2.0 (with BSD and MIT parts in torch) |
| `huggingface_hub` | fetches the models on first use | Apache-2.0 |
| `rapidocr_onnxruntime`, `onnxruntime` | OCR for pages with no text layer | Apache-2.0, MIT |
| `numpy`, `pillow`, `opencv-python-headless` | images and arrays | BSD-3-Clause, MIT-CMU, Apache-2.0 |
| `pyyaml`, `pydantic`, `lxml`, `rich`, `typer`, `rapidfuzz` | front matter, models, output, CLI | MIT and BSD-3-Clause |
| `wordninja` | splits glued words in OCR layers | MIT by its repository; the installed metadata states none |

**Not yet checked, and the owner's to settle before a product ships:** the licences of the two sets of
model *weights* the pipeline downloads at run time - `ds4sd/docling-layout-heron` for layout and
`SWHL/RapidOCR` for the English recogniser. Those are data, not packages, and their terms are not in any
installed metadata.

## D011 - Text a reader cannot see stays out of the body, and is recorded in the front matter (2026-09-03, owner's decision)

**Context.** The goal is fidelity to what a document means when a human reads it. PDFs can carry text that no reader sees: white or background-coloured text, zero-size fonts, text painted under an image or a filled shape, text clipped away by a clipping path, text beyond the page edge. Keyword-stuffed CVs and papers with hidden instructions aimed at automated reviewers are the everyday examples.

**Decision.** Such text is excluded from the markdown body. The front matter records what was removed (where, how much, and the text itself under a `hidden_text` key) so nothing is lost silently. The one exception is the invisible text layer of a scanned page (D010): there the hidden text *is* the visible words, and it is used as the reading of the page.

**Alternatives considered.** Keep hidden text and mark it inline; keep it unmarked (the behaviour before this decision). Both were rejected for the default because the reader-facing meaning is the yardstick. If a forensic or search use case appears, "keep and mark" would be the better default; it can be a rendering option.

**Consequences.** Stage 1 must decide visibility per character: colour against the local background, font size, coverage by later-drawn images or fills, clipping, page bounds. Text outside the page bounds is already dropped at extraction; the rest is to be built after run 7.

## D012 - Front matter follows OKF v0.2; TrueDoc's own details live under one `truedoc` key (2026-09-03)
The required `type` defaults to `Document` (`--type` overrides it). `generated` records `truedoc/<version>` and the time; `sources` names the PDF
(path, file name, modification time); `resource` repeats the path; `description` is the first sentence of the first ordinary paragraph;
`status` is always `draft` because nobody has reviewed the conversion (a human sets `stable` and adds `verified`). Everything that is
TrueDoc's own (checksum, page count, confidence, OCR pages, hidden text, warnings) sits under `truedoc:` so it can never collide with a
standard field, and `tags` is omitted rather than guessed. No `okf_version` in single files: the specification puts it in a bundle's `index.md`.

## D013 - Drawn marks that carry meaning become characters (2026-09-03)
Ticks, crosses and bullets drawn as vector shapes or tiny images (an insurance table saying which cover a line applies to) are found by
rendering each small drawing and matching its ink against a few templates, with its colour as a tie-breaker. A recognised mark becomes ✓, ✗,
●, ○, ■ or □ in the table cell it sits in, or at the head of the line it precedes. A mark inside a cell that cannot be read is kept as
`[icon]`; an unreadable shape next to running text is treated as decoration and left out. Marks set in symbol fonts (Wingdings, Webdings)
are mapped from their font codes. Why: the meaning of such a table lives in the marks, and a text-only reading silently loses it.

## D014 - An optional vision stage joins the product (2026-09-03, owner's decision)
Off by default; one switch; one provider interface with an open model on a GPU endpoint (transcription of pages with no usable text) and a frontier model API (understanding). Evidence: run 9 plus olmOCR 2 on the 94 empty pages scored 67.8 against 62.2. The text layer stays the ground truth; a model only reads pages TrueDoc cannot.

Evidence, 7 September: run 54 (67.4) scores 72.2 with olmOCR 2's readings saved on 3 September dropped onto its 78 blank pages (held-out 65.0 to 66.6), and 72.6 when the model also replaces the 28 typed pages our own OCR reads at 0.80-0.85 confidence. The second number asks whether 'a model only reads pages TrueDoc cannot' should become 'a model reads every page without a text layer'; the owner's decision is pending, with the GPU hour for the proper run (the switch on inside the converter).
Evidence, 7 September, 21:36 (GPU session 2, 85 cents): with olmOCR 2 reading all 281 pages that have no digital text layer, run 54's output scores 82.7 (CI 81.8-83.7; held-out 79.4) against 67.4 without and 72.2 with the model on blank pages only; the hidden OCR layers alone are worth 4.6 points, the pages with no layer 9.7, the suspect layers 1.0. Rule change: D019 below.

## D015 - Model output is marked as inferred, in the body and the front matter (2026-09-03, owner's decision)
Anything a model read from pixels or inferred (an icon's meaning, a chart, a scanned page) is visibly marked for a human reader and listed in the front matter for audit. Marker design (footnote tag `[^inferred]`, page note for whole pages) to be reviewed by the owner before building. Applies to every escalation, not only icons. **Confirmed by the owner on 3 September (evening):** the proposal in `docs/OKF_SPEC.md` stands as written, with one tag for every model source and the model named in the definition and the front matter, not in the tag.

## D016 - The owner's insurance library is the independent test bed; a fifth of the benchmark is held out (2026-09-03, owner's decision)
New rules are checked on the library (never scored) and the held-out slice is never tuned on and is reported separately, to keep the benchmark score honest about overfitting. The owner's Max plan covers my own looking at pages during development; a product call to a frontier model needs an API key with its own billing (two different things).

## D017 - Footnotes are kept and linked as markdown footnotes (2026-09-03)
A small raised digit or symbol glued to a word in running text is a footnote marker and is written as `[^n]`; the note it points to (a
line starting with the same number, in small type or at the foot of the page) is written as `[^n]: text`, so a reader or a program can
follow the link instead of meeting "face.8" and a stray paragraph. Notes stay in the body (they carry meaning; the benchmark's
headers-and-footers checks that want some of them gone are accepted as lost). Endnotes (notes on a later page, under a "Notes"
heading or in a run of numbered notes) are linked by a document-level pass; a number reused on a later page gets a page-qualified
key (`[^1-p12]`) so keys stay unique. Markers inside formulas are not linked (a raised digit there is an exponent).

## D018 - The no-model target is 70, the ceiling 72.5, and the census pool is the stopping rule (2026-09-07, owner's decision)

The lateral round's census (`bench/tools/ceiling_census.py`) found that a perfect classical run, winning every failing check whose text already exists in evidence we hold, would score about 72.5 on olmOCR-bench; the other 27.5 points sit behind pixels that only a better reader of images can turn into letters. The owner set the no-model target at 70 (by the end of the week of 7 September) and treats 72.5 as the wall to measure against, not the goal. The stopping rule for classical work: run the census after each benchmark run; when the mechanical pool stops shrinking while runs keep landing, the classical path is done and the remaining points belong to the model tiers (D014). The three-wave plan is in `docs/LATERAL_ROUND_1.md`.

## D019 - A model reads every page without a digital text layer (2026-09-07, owner's decision)

A hidden OCR layer is another reader's guess at the words, not the document's text: it cannot carry a formula, and it loses to a vision model on every page class measured (session 2 of 7 September: hidden-layer pages +4.6 points, pages with no layer +9.7, suspect layers +1.0; all together 82.7 against 67.4, held-out 79.4 against 65.0). Rule (agreed by the owner at 21:50 the same evening): when the vision stage is on, every page whose text layer is not digital (kinds none, ocr, suspect) is read by the model; the layer's text is kept only as the fallback when no model is available (D010 narrows to that case) and as a witness for the invented-text check (D008). Digital pages never go to the model. Model pages are marked inferred as D015 says, and the header and furniture rules run over the model's text. The top tools behave this way already (olmOCR: image only; Marker: the embedded text per page, hidden layers stripped only with a flag).

## D020 - Partial pages stay closed and small task models stay out (measured 2026-09-07, recorded 2026-09-08 at the owner's request)

Two of wave 3's four questions (`docs/LATERAL_ROUND_1.md`) were measured and settled on the evening of 7 September but never written down here, so the status file went on listing them as open. Both verdicts stand.

**Partial pages: no. D008 and D009 are unchanged.** Six of the ten thinkers wanted a page the OCR gate rejects to keep its confident printed lines with a visible note. Run 54's 79 blank pages were read again with the gate's measures recorded and each page's own checks run against the shaky reading (`bench/probes/partial_census.py`, 20:08-20:13): 48 pages typed but shaky (322 checks, 20 passing), 27 gibberish (130 checks, 8 passing), 4 unread. Keeping every shaky read would win about 28 text checks and up to 79 baseline checks, at most +1.4, against the model's +4.8 on the same pages. The examples settle it: the floor of the "typed but shaky" bucket is handwriting read as pronounceable nonsense, which the language-likeness measure cannot tell from real words, and the nine pages a reader would genuinely want kept (0.75 and above: a 1920s letterhead, a French page, a manuscript collection header, a Spanish table of vehicles) are pages the model reads anyway under D019. An honest gap still beats a plausible invention.

**Small task models: no.** A formula-image reader (pix2tex, MIT) and a second OCR engine (Tesseract, Apache-2.0) were proposed as models that are not vision-language models. Both were set aside: the vision tier covers the same pages better, and the two-witnesses test had already answered the second-engine question (across the 48 confident pages the text layer beat our own engine 181 checks to 72). D019 has since taken away what territory was left, because every page without a digital text layer now goes to a model; arXiv maths stands at 87.4 and old-scan maths at 80.8 (run 63), so there is no formula-reading gap for a small model to fill.

**What remains, and it is a product question rather than a score one:** in the free tier there is no model, so a page our own OCR read confidently but which failed the word-likeness gate is still emitted empty (about six pages on the benchmark). Whether those deserve a visible partial-page note in the no-model configuration is open, and the recommendation is to leave it until the owner's library run shows how often it happens on real documents.

## D021 - The invented-text check reports and never acts (2026-09-09)

D008 says nothing is invented, and on every page a model reads for us (D019) nothing verified it: the
promise was a policy we stated rather than one we measured. `truedoc/vision/corroborate.py` now checks
each model-read page against what we can read of it ourselves - the hidden text layer, or our own
engine's rejected lines, already kept in `page.meta["witness_lines"]` - and puts a verdict per page in
the front matter under `truedoc.corroboration`.

Four verdicts, because a two-state check would imply a pass where none was earned: **unchecked** (no
witness at all - a bare scan our OCR could not read), **unverified** (a witness exists but is in a
different script from the model's text, so its encoding is broken and it can witness nothing),
**corroborated** (the witness backs at least 55% of the model's words), **low support** (a comparable
witness backs fewer - worth an eye, nothing more). Over the 281 model-read benchmark pages: 181, 91, 7
and 2 respectively.

**It never drops or alters the model's text, and that is a measured decision rather than caution.**
Every low-support page in the corpus had a broken witness rather than an inventing model: a Persian
page whose text layer is mojibake (`ƶŝ Ĩŝ ƾĭŵźƀƟř`) against the model's correct Persian, and a formula
our own rebuild mangled. Acting on low support would have destroyed both correct readings. The check
found no inventions at all, so it is insurance and a disclosure to the reader, not a bug-hunt - and it
is what would show a future model starting to invent.

Hand-audited before this was recorded (M6's stated condition): every flagged page is a broken
witness. `7b9b73157809_pg19` - ours `GlOW Tack J and Sponse¢ | Salau'_`, the model "TABLE B-3.
DETAILED COST BREAKDOWN"; `old_scans/74` - ours `+]The [merican [ssnciatim of the Je Gross.`, the
model "The American Association of the Red Cross."; `00d8a44d` - ours `7 PDA 7uq dZ 7z] H[oE`, the
model correct Korean. Zero inventions. Known limit found in the same audit: the script test compares
the dominant script, so a bilingual page (a Korean paper with an English title) has Latin on both
sides and its mojibake layer lands in "low support" rather than "unverified" - still flagged, still
never acted on, but the reason given is wrong.

## Closed by D023: PyMuPDF's licence against D007 (found 2026-09-07; closed 2026-09-11)

PyMuPDF, which reads every text layer TrueDoc uses, is dual-licensed: GNU AGPL 3.0 or a commercial licence from Artifex (the installed package's metadata says so; Artifex's licensing page, read 7 September: a server-based application or service cannot be deployed without disclosing the application's full source under the AGPL; prices on request, per copy with a quarterly minimum). D007 excludes AGPL components from the product path. The choices are a commercial licence or moving the text-layer stage to a permissive reader. Evidence, 8 September: no leaderboard tool uses PyMuPDF; olmOCR, Marker, Docling and MinerU all read PDFs through PDFium (pypdfium2, pdftext, docling-parse), and MinerU moved off PyMuPDF. Agreed with the owner: decide after a measured census (PyMuPDF against PDFium on every benchmark page, the formula stage's special cases first) and, if the census is clean, a trial run with a PDFium extractor; both after GPU session 3. **Census done 8 September (`bench/tools/engine_census.py`): the characters agree on all but 16 pages once the binding's UTF-16 halves are combined; PDFium reads whole columns PyMuPDF silently drops on a handful of pages; PyMuPDF decodes Type 3 fonts PDFium does not (16 pages) and reports raw codes for unmapped glyphs where PDFium gives U+FFFD; PDFium is 2.4 times faster. Verdict: a PDFium extractor is viable with two bounded gaps; step 2 (the extractor, a full run) is the next decision for the owner.** **Step 2 sized 8 September (discussed with the owner that afternoon):** the swap is worth at most +0.30 points (53 pages where PDFium reads text PyMuPDF drops; 16 of them fail checks today, 28 checks in all, and most of that "extra text" is the binding reporting two-part characters as two rather than text genuinely dropped) against at most -0.38 (the 48 checks that pass today on the 16 Type 3 pages), plus an unmeasured risk to the maths glyph outlines. It is a licence job, not a score job, so the recommended order is after GPU session 4 (worth about 3 points), unless the rental is more than a couple of days away, in which case step 2 is the best use of the wait because it needs no rental. The work itself: characters and boxes, page rendering, and the vector drawings rebuilt from raw path segments through pypdfium2's low-level bindings (every symbol needed is present in 5.13), both readers behind one switch. Buying Artifex's commercial licence removes the need for it entirely. Nothing else in the product path is affected.

## D022 - Every stage moved off PyMuPDF is proved against a quantity that must be identical, not against the score (2026-09-10)

The reader swap of M18 (D007, getting AGPL out of the product path) has a failure mode the benchmark is
poor at catching: **it fails silently**. Nothing crashes, no exception is logged, and the page still
converts - it simply converts wrongly, in a way that looks like a layout bug rather than a reading bug.
Two live examples, both found by hand rather than by any score:

* PDFium reports a font's *nominal* size, and a PDF may then scale it by its text matrix. On one
  multi-column page every character came back as size 1.0 where the text is 8pt; on a small-print page
  the sizes came back around 35pt for 5.9pt text. Nothing failed. The page merely lost every paragraph,
  because a stage that cannot tell a heading from body text groups nothing.
* pdftext rotates its coordinates into display space and PyMuPDF does not, so a page that had already
  been rotated was rotated twice and every box landed a median 210pt away - on the 15 rotated pages of
  the benchmark, and invisibly on the other 1,388.

So the rule for the rest of the swap: **before a stage is moved, name a quantity the two readers must
agree on because it describes the same physical page, and measure it.** Character origins and boxes for
the text reader (now agreeing to a median of 0.000pt, unrotated and rotated); the rendered image itself,
pixel by pixel, for page rendering; path geometry for the vector drawings. Where such a quantity is
compared, quote the median *and* the tail - the 0.21 baseline estimate this replaced had a perfectly
respectable median and was 25.8pt wrong on exactly the glyphs it existed to serve.

**The score is the second check, never the first, and on its own it misleads twice over.** It cannot
localise a fault (a page reading 0/14 says nothing about which of four stages broke it), and tuning
against it while a bug is live fits the bug: the 1.5 line-gap threshold was chosen while font sizes were
wrong, and part of what it was doing was compensating for them.

_Corollary, learned the same day: before recording a component as the hard part of the swap, check who
wrote it. PyMuPDF's `find_tables` is a port of pdfplumber's, MIT-licensed, and pdfplumber was already
installed here. The item flagged as the blocker was the one with a permissive original sitting in the
virtual environment._

## D023 - The PDFium readers are the default; PyMuPDF leaves the product path (2026-09-11)

The four stages that read a page - text, rendering, drawings and images, ruled tables - go through
PDFium (pypdfium2, Apache-2.0/BSD) and pdftext (Apache-2.0) by default from run 71 on. MuPDF stays
reachable for measurement only: `TRUEDOC_READER=mupdf`, `TRUEDOC_RENDERER=mupdf`,
`TRUEDOC_OBJECTS=mupdf`.

_Correction (12 Sept): the rendering stage was not in effect from 10 Sept 10:43 until run 83. Commit 905f456 renamed the renderer's document function and left the one call in `_render_pdfium` on the old name, so every PDFium render raised a NameError, the fallback caught it without a word, and MuPDF drew every page image in runs 66 to 81. The text and object readers were in effect throughout. See the progress log, 12 Sept._

**Why now.** The condition set when the swap began was a run holding about 84.0 with the held-out
fifth level. Run 71, every switch on: 84.0 (CI 83.2-84.9), held-out 81.1 against the MuPDF run's 80.9,
tuned-on 81.9 against 81.9; nine checks up over the 1,403 pages of run 65 (53 won, 44 lost: arXiv +6,
tables +3, tiny text +1, multi-column level, headers -1). Without a model, scored category by category
against the MuPDF path on the same code: tables 850 against 848 of 1,022, multi-column 678 against 678
of 884, tiny text 364 against 361 of 442, the arXiv pages that ever differed 627 against 622 of 738.

**How it got there, and the rule that made it work (D022).** Every difference was traced to a
quantity both libraries describe and measured before a line was written: character boxes (origins to
0.000pt; the font's ascent and descent; the origin as the left edge on 99.7% of 316,152 characters;
the size as the root of the text matrix's determinant on 73,333 non-uniformly scaled characters), the
segments a stroked path draws (PDFium's bounds inflate them by the line width), what PyMuPDF's strict
table strategy counts (stroked segments and thin fills, never a wide fill), and the PDF's own tables
where PDFium has none to give (glyph names and widths from /Differences and /Widths, Type 3 widths
through the font matrix). Every rule written without such a quantity - a rule where two fills meet, a
frame around every cluster of rules, an advance from a font with no name - invented tables or lost
words somewhere in the population, and was found only by scoring whole categories.

**What is still PyMuPDF's.** The document handle and `Page` objects, `pymupdf.Rect`/`Matrix` used as
plain geometry types (about 27 sites), `set_rotation` (2 sites), and the MuPDF path itself, kept for
measurement. Removing the dependency altogether is the remaining M18 work; the product path no longer
reads a page through it.

**Known losses against the MuPDF path, all small and all traced** (`docs/PROGRESS_LOG.md`, 11 Sept):
a Type 3 page with unnamed fonts that PDFium cannot map (it falls back to OCR, one check); a 44pt drop
cap whose column line our line join welds to the next column (one check); three table singles; three
arXiv pages (matrices in brackets, a cases brace read as three pieces, tilde accents) worth seven
checks the MuPDF path also loses in part.

## D024 - Formulas in `\( \)`, literal dollar signs escaped (2026-09-12, the owner's decision)

TrueDoc writes formulas as `\(...\)` inline and `\[...\]` as a block, and writes a literal dollar sign in
markdown text as `\$`. The old convention - `$...$`, `$$...$$`, prose dollar signs bare - is gone.

**Why.** The owner will read the output rendered as well as have machines read it, and the standing
objective is that meaning survives for the reader. While formulas are marked by dollar signs, a price in
the same paragraph swallows the formula, and a stray dollar sign flips every formula after it - that cost
2503.05329 page 4 its check. While prose dollar signs are bare, a viewer that pairs any two of them turns
"The excess is $100 and the benefit limit is $2,000" into a formula. One change covers each, and neither
leans on the reader's software being careful.

**Cost, measured.** Re-delimiting costs nothing: on run 82's markdown, all 7,019 checks over all 1,403
pages read exactly the same with every formula re-delimited (`bracket_sim.py`, 12 Sept). Escaping costs
the benchmark, because its expected text holds bare dollar signs and its scorer does not undo a markdown
escape: sixteen checks of the 98 on the fifteen pages that carry one, fourteen of them in tables, about a
fifth of a point overall (`dollar_escape_sim.py`). That is a cost in the benchmark's bookkeeping, not in
meaning - the page still reads "$448" to anyone looking at it.

**Where escaping applies.** Markdown text: paragraphs, headings, list items and pipe-table cells. Not
inside a formula, and not inside an HTML table, where markdown escapes do not apply and a backslash would
show as a backslash.

**Measured on a run:** run 84 scored 84.0 (against run 83's 84.2): 0 won, 13 lost, every one a check whose expected text holds a bare dollar sign, on six pages; held-out unmoved at 81.1. Thirteen rather than sixteen because a price inside an HTML table is left bare.

## Decided - Literal dollar signs in prose (found 2026-09-12, decided the same day: D024)
TrueDoc writes formulas as `$...$` and `$$...$$` (`docs/OKF_SPEC.md`) and writes a dollar sign in prose
as it stands: a hand-built page reading "The excess is $100 and the benefit limit is $2,000 per claim"
comes out exactly so. A maths-aware markdown viewer - GitHub's among them - then reads "100 and the
benefit limit is " as a formula, and so does the benchmark's own parser: on 2503.05329 one stray dollar
sign paired with every later one and cost the page its check. The owner's insurance documents are full
of prices. Three ways out, measured where they can be:
1. Escape every prose dollar sign as `\$` - what the format implies, and safe in every viewer. It costs
   the benchmark: on the 15 pages that carry a check with a dollar sign in it, run 80's markdown with its
   prose dollars escaped passes 57 of their 98 checks against 73 as written - sixteen checks lost,
   fourteen on tables - because the benchmark's expected text holds bare dollar signs and its scorer
   does not undo markdown escapes.
2. Leave prose dollar signs bare and write formulas as `\(...\)` and `\[...\]`, which the benchmark's
   maths checks also accept: a stray dollar sign could then never break a formula and the dollar checks
   keep passing, but a viewer that reads `$...$` as maths would still read prices as formulas. Measured
   on 12 Sept, on run 82's own markdown with every formula re-delimited: not one check changes,
   7,019 of them over all 1,403 pages, every category identical. So option 2 costs nothing on the
   benchmark where option 1 costs sixteen checks.
3. Leave both as they are.
The xy-pic arrow tip behind 2503.05329's stray dollar sign is fixed separately - it was never a dollar
sign. The choice between 1, 2 and 3 trades benchmark checks against how the output reads in a viewer.

_Decided 12 Sept, the owner: options 1 and 2 together - formulas in brackets, prose dollar signs escaped. The output is to be read rendered as well as by machine, and meaning for the reader decides. See D024._

## D025 - A second, paid reader for the pages the first one cannot manage, and two scores kept apart (2026-09-13, owner's decision)

**Context.** D014 put a vision stage in the product and D019 sends every page without a digital text
layer to it. Those pages are a fifth of the benchmark and carry a quarter of its checks, and we pass far
fewer of them than of the rest. The question the owner put on 12 September was which model to rent for
that stage.

**What the measurement found** (`docs/MODEL_CHOICE.md`, and the log for 12 and 13 September).
The published tables could not answer it, so the 98 old-scan pages were read again and scored. A
frontier model reads the hard tail far better than olmOCR 2 - on the hardest third of those pages it
roughly doubles the score - and on pages olmOCR reads well the two are level to the check, 117 each. So
the answer is not a better model for every page; it is a second reader for the pages the first cannot
manage.

**The decision.** A page goes to the deep reader when it has no digital text layer *and* our own OCR of
it comes back with nothing word-like (`pipeline._needs_a_deeper_read`; the threshold is
`vision_deep_wordlike`, 0.6 by default). Everything else keeps the ordinary reader. The deep reader is
off unless an endpoint is given (`--vision-deep anthropic`), so an ordinary conversion and an ordinary
benchmark run are unchanged. 103 of the benchmark's 1,403 pages qualify.

**And two scores, kept apart.** The owner asked for this explicitly. An open-weight score - the machine's
own reading plus a model whose weights anyone can download - stays the default and the number we quote.
A hosted score, with a paid service in the loop, is reported in its own row and never mixed with the
others, which is how olmOCR-bench's own published tables treat hosted services. On 13 September those
numbers are **84.1 open weights (run 89)** and **85.4 hosted (run 91)**.

**What the user sees.** Pages leaving the machine needs their consent, so the deep reader is something a
user opts into rather than something that happens to them; but they opt into a policy, not a sorting
job, because the converter decides which pages qualify. Everything a model wrote is still marked as
inferred and the mark names the model that wrote it (D015), which run 90 got wrong and which is now
tested.

_Decided 13 Sept, the owner: proceed with the deep read, with the open-weight score kept as its own
column._

## D026 - OmniDocBench investigated and declined as a measure of TrueDoc (2026-09-13, owner's decision)

**Context.** M7 asked for a score above every published tool on *both* public benchmarks. olmOCR-bench
has been run ninety-one times. OmniDocBench had never been run once, and the milestone had sat at "half
met" since the beginning on that account. Before running it, the benchmark was taken apart.

**What it turned out to be.** Every page in OmniDocBench is a picture. The current release ships page
images and no PDFs at all; the older v1.0 branch ships PDFs, and six of those, sampled across six
document families, contain **zero characters of text**. So the stage TrueDoc is built around - reading
the document's own text exactly - never runs, and neither does the formula rebuilder (it works from
glyph positions) nor either table builder (they work from text-layer lines). When the vision stage
reads a page it replaces the page's blocks entirely. Measured on one page: **27 of the 35 output lines
were the model's words verbatim**, the rest being our note, our footnote and some formatting.

A score there would therefore be a score for whichever model we plug in, wearing TrueDoc's coat. That is
worth knowing about the model and says almost nothing about the converter.

**And the metric measures a different thing from the goal.** The headline is
`((1 - text edit distance) x 100 + table TEDS + formula CDM) / 3` - how close our string is to theirs.
That is transcription fidelity. olmOCR-bench at least asks questions shaped like meaning: is this text
present, is it in the right order, is this text *absent*, does this cell sit beside that one. Neither is
the same as "retains meaning for the reader", but one is nearer.

**The decision.** OmniDocBench is not run as a headline measure. M7 is closed on the strength of
olmOCR-bench, with this investigation recorded rather than the milestone left quietly half-done. The
cost avoided: 1,651 model calls, a Docker image for the formula metric, and a number that mostly belongs
to someone else's model.

**What was kept.** The evaluation toolkit is cloned and works (`bench/omnidocbench/`, Apache-2.0, runs on
our Python once the dependency pins are dropped; the demo scores end to end). If the question ever
becomes "how does a candidate reader handle Chinese, Japanese, newspapers or exam papers", none of which
we test anywhere, a 200-page sample is half an hour's work from here. The formula metric needs TeX Live,
ImageMagick and Ghostscript, so it needs the Docker image; without them CDM returns 0.0 for every
formula, which was confirmed on their own demo.

**Where the effort goes instead**, in the owner's order: the insurance documents, which have never been
scored and which have already found a meaning-inverting defect no benchmark showed; then the model for
the hard tail; then the remaining grind on the benchmark we do use.

_Decided 13 Sept, the owner: close the milestone, then the insurance docs, then the hard tail, then the
remaining grind._

## D027 - The Key Facts Sheets are an oracle, and every rule drawn from them must be generic (2026-09-13, owner's decision)

**What we found.** A Key Facts Sheet is prescribed by the Australian Government under the Insurance
Contracts Act 1984: the same three columns, the same header wording, the same list of insured events.
The owner's library holds **202 of them across 34 insurers** - 17% of the whole library. What the law
prescribes is the *content*; the typesetting is each insurer's own, because the sheets only have to
look the same to a reader.

That combination is the rarest thing a converter can be handed: a few hundred pages where **the right
answer is known without anyone writing a check**, laid out 34 different ways. Nothing else in the
project has this. The olmOCR benchmark needed a thousand checks written by hand; the insurance set
needed a model to read 25 pages and the owner to rule on 38 of them. The Key Facts Sheets grade
themselves, for nothing, for ever.

**The decision, and it is the owner's.** The sheets are used as an oracle to *derive* rules, never as
a document class to special-case. A rule that reads "if this is a Key Facts Sheet" fixes 202 documents
and no others. The faults these sheets expose - a header that wraps onto three lines, a full-width band
inside a table, a label parted from its answer - are faults on any document. So a rule earns its place
three ways:

1. **Written in geometry and typography**, with nothing in it that knows what an insurance document is.
   The first rule drawn this way is "a heading that wraps mid-sentence is still the heading": the
   prescribed header's third column is a long sentence, and `_header_row_count` ended the heading at the
   first cell of more than six words, so two thirds of the header became body rows.
2. **Verified on the sheets**, because there the answer is known - and on a fifth of them held back and
   never tuned on, chosen by a hash of the filename (`bench/tools/kfs_grade.py`), the same guard
   `bench/holdout.txt` gives the benchmark under D016. Two hundred examples of *one table* is a lot of
   examples of very little, and a rule tuned until all of them pass is a rule shaped to that table.
3. **Measured on olmOCR-bench**, which holds none of this material. The oracle says whether a rule
   fixes; only the benchmark says whether it harms. This is the run-90 lesson written into a method:
   a change measured where it helps and shipped everywhere else is how 77 checks were lost in an hour.

**What it is worth.** Graded over one sheet from each of fourteen insurers before any fix: the
prescribed events land in their own rows almost everywhere (13 of 14 sheets at 10 of 10), so the body
is sound; **9 of the 14 lose the header**, which on a document whose whole purpose is "is this event
covered - yes or no" means losing which column holds the answer.

## D028 - A table cell holds what its box holds, and a list inside a cell is written as a list (2026-09-15, owner's decision)

**The question.** Eight checks on the owner's insurance set failed for one reason. Where a page draws a box around
several things, TrueDoc's table cell held everything in the box, and the check - written from the page image - wanted
less: the tick or cross at the head of an item left off (five checks, on POL1418DIR page 13, Kogan's POL1439FI page 29
and BOM's home PDS page 22); one item of a whole ticked list drawn in one box, as a cell of its own (two, on Kogan's
page 29); and the "Go to page 32." line at the foot of BOM's "Contents cover" box left out (one). The owner ruled card
by card on a dossier of the eight, each card showing its page (`bench/out/insurance_set/cell_box_ruling.json`).

**The decision.**
1. **A tick or cross stays at the head of its item, in the cell.** For the reader both readings keep the meaning: the
   column heading ("What's covered?") establishes it and the mark confirms it. Keeping the mark never loses meaning;
   dropping it would, wherever no heading says the same.
2. **A "Go to page" line stays in the cell whose box holds it.** It tells the reader where that cover is set out in
   full.
3. **A list set in one box - or beside another list with no boxes drawn - is written as a list inside its cell:** each
   item a list element with its tick or cross, a sub-list nested under the item it belongs to, and a note that is not
   an item (BOM page 22's "An additional excess of $250 ... applies to each earthquake") kept in the cell after the
   list. Asked first whether one row per item would serve a machine comparing two insurance products better, and not
   knowing how such a machine will read tables, the owner chose to future-proof. One row per item invents pairings: two
   lists set side by side share rows only by their order, and a tool that reads each row as a record would pair a cover
   with an exclusion the page never pairs. Line breaks inside a cell are flattened by TrueDoc's own markdown tables and
   by many tools, which would run the items together as today's cells already do. A list element is separated by any
   HTML reader, converter or language model, and pairs only what the page pairs. It needs an HTML table, which TrueDoc
   already writes wherever a cell spans.

**What follows.** The six checks the first two points settle were rewritten on 15 September to quote the cell with its
mark or line; the files as they stood are in `bench/out/insurance_set/checks_a_before_cell_box_ruling/`. At fb091fb the
set scores 222 of 229 on them, where it scored 216. The two list checks are rewritten when lists are written as lists,
to look for each item inside its cell's list. The owner also named the fault behind the first point as the one that
matters for meaning: POL1418DIR page 13 draws no boxes, and its table is cut at text lines, so "or commercial building"
stands in a row of its own and the strata-title condition on residential flats lands beside "Recreational structures".
Reading an item as the page sets it - a tick or cross, then lines at the item's own indent - is the same work as writing
the list, and the two are built together.

**Built** (15 September, night). A list inside a table cell is written as a list (`truedoc/tables/cell_lists.py`), and
lists set side by side are read column by column (`truedoc/tables/list_columns.py`). The two list checks, and three on
POL1418DIR page 13 whose items are now list elements (two of them among the six above), were rewritten as `list_item`
checks - the item with its mark among a table cell's list elements, under its column heading; the files as they stood
are in `bench/out/insurance_set/checks_a_before_list_checks/`.
With the wrapped-entry rule in the tree the set scores 226 of 229 on them.

## D029 - A line at a page's edge that no page beside prints is the document's imprint (2026-09-16, owner's decision)

**The question.** A running head or foot runs: the same words, at the same height, page after page. At the edge of a
first page nothing runs, and what stands there is the document's imprint - a copyright line, a journal's "Downloaded
from ... by guest" stamp, a standard's issuing body, an insurance cover's issuer, ABN and licence ("AAI Limited ABN 48
005 297 807 AFSL 230859 trading as AAMI"). TrueDoc dropped all of it as furniture. Four ways of telling the meaningful
lines from the worthless were tried on the library's census and all four failed - repetition, position on the page,
type size, and length. The fourth was an overfit the owner caught: counted by copies, every stamp stopped at ten words
and every issuer block started at twelve, but counted by distinct wording the two overlap at ten, and 23 of the 41
"issuer blocks" were one AAMI template.

**Why it does not divide.** The division is not in the document, it is in the reader. olmOCR-bench's 753 header and
footer checks want every such line absent - "Copyright 1975 American Mathematical Society", "FI-02180 Espoo, Finland",
"Please cite this article as: ..." - and a reader comparing two insurance products needs to know who underwrites them.
Both are right for their reader. The owner's own insurance set holds both positions: two of its 31 absent checks are a
document's own stamps ("PDS preparation date 25/11/2020" on GIO page 2, "NRMAHOMPDS REV2 09/2023" on NRMA's cover), so
publishing imprint into the body would contradict checks he ruled fair.

**The decision.** Neither the body nor the bin. A line at a page's edge that no page beside prints there stays out of
the body, exactly as before, and is kept in the front matter under `truedoc.imprint` with the page it came from.
Nothing the document says is thrown away, no block changes kind, and the body of every document is byte for byte what
it was - so the three measures, which all convert with `frontmatter=False`, cannot move. A page number is left out: a
folio counts the artifact's pages, not the document's matter. No threshold is involved, so nothing is fitted to a
corpus.

**Built** (16 September, midday). `_record_imprint` in `truedoc/pipeline.py` asks `_repeated_beside` of every block
already filed as a header or footer, after every furniture decision is final; `load_document` gathers the entries as
it gathers hidden text (D011); `truedoc/render/okf.py` writes them under the `truedoc` key. Tests in
`tests/test_imprint.py` (6).

**Measured** (against 9c39679). Every page of the insurance set, all 190 Key Facts Sheets and all 266 pages of
the benchmark's headers-and-footers pool are byte for byte what they were, and the suite is 642. Over 200 documents
of the library's census sample 60 keep an imprint - 67 lines, 51 distinct, none of them a page number. It costs
nothing that can be measured: 20 pages convert in 6.99s before and 6.84s after, best of five with the layout model
off.

## D030 - A never-tuned-on slice of the insurance library, sealed before it is looked at (2026-09-16, owner's decision)

**The question.** The insurance set scores 229 of 229, but its 25 pages have been in front of me for every rule
written this fortnight, so the score says TrueDoc handles the pages I have been looking at - not that it handles a
document it has never seen. The benchmark has held a fifth back since the beginning (`bench/holdout.txt`) and the Key
Facts Sheets hold a fifth back by a hash of the file name (D027); the owner's own library had no such guard. He asked
whether running more of the library through TrueDoc first would gain anything. It does - one page read against its
image this afternoon found three defects, at no cost but machine time - but exploring first and carving a held-out
slice out afterwards would destroy the guarantee, because a page that has been read is a page that has been tuned on.

**The decision.** Seal the slice first, blind, and explore everything else afterwards. Membership is
`int(sha1(file name)[:8], 16) % 50 == 0`, a pure function of the name, so it never moves as the library grows and no
judgement of mine can reach it. Excluded before the rule was applied: the insurance set's own pages, every Key Facts
Sheet (the table oracle), and every document whose pages have been converted and read while building rules - 712 of
the library's 1,176 PDFs were eligible, and **19 are sealed, from 10 insurers**. The one-in-fifty census sample is
not excluded, and that is a judgement worth knowing: it looked only at what a page's margins hold, never at a
document's body, so two sealed documents have each had one margin line of theirs appear in a list I read.

**What happens to them.** They are never opened, converted or read while a rule is being built. They are scored once,
at a milestone, by the method the first 25 pages were scored by - a hosted model writes checks from the page images
without seeing TrueDoc's output, and the owner rules on the doubtful ones - and the score is reported separately from
the tuned-on set, as the benchmark's held-out fifth is. The list is `bench/insurance_holdout.txt`, which carries the
rule and the warning in its own header; `scratchpad/seal_holdout.py` regenerates it.

