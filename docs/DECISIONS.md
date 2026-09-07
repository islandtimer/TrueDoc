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

## Open: PyMuPDF's licence against D007 (found 2026-09-07, owner's decision pending)

PyMuPDF, which reads every text layer TrueDoc uses, is dual-licensed: GNU AGPL 3.0 or a commercial licence from Artifex (the installed package's metadata says so). D007 excludes AGPL components from the product path. The choices are a commercial licence or moving the text-layer stage to a permissive reader (pypdfium2, pdfplumber). Nothing else in the product path is affected.
