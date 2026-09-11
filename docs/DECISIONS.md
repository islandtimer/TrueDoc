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

**Partial pages: no. D008 and D009 are unchanged.** Six of the ten thinkers wanted a page the OCR gate rejects to keep its confident printed lines with a visible note. Run 54's 79 blank pages were read again with the gate's measures recorded and each page's own checks run against the shaky reading (`scratchpad/partial_census.py`, 20:08-20:13): 48 pages typed but shaky (322 checks, 20 passing), 27 gibberish (130 checks, 8 passing), 4 unread. Keeping every shaky read would win about 28 text checks and up to 79 baseline checks, at most +1.4, against the model's +4.8 on the same pages. The examples settle it: the floor of the "typed but shaky" bucket is handwriting read as pronounceable nonsense, which the language-likeness measure cannot tell from real words, and the nine pages a reader would genuinely want kept (0.75 and above: a 1920s letterhead, a French page, a manuscript collection header, a Spanish table of vehicles) are pages the model reads anyway under D019. An honest gap still beats a plausible invention.

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

## Open - Literal dollar signs in prose (found 2026-09-12; the owner's to decide)
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
   keep passing, but a viewer that reads `$...$` as maths would still read prices as formulas. Not yet
   measured.
3. Leave both as they are.
The xy-pic arrow tip behind 2503.05329's stray dollar sign is fixed separately - it was never a dollar
sign. The choice between 1, 2 and 3 trades benchmark checks against how the output reads in a viewer.
