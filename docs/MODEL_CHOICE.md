# The rental decision: what the numbers say (measured on run 88, 12 Sept 2026)

## How much of the benchmark a model reads for us

A page goes to the model when it has no usable digital text layer (D019). In run 88 that was 278 of the
1,403 pages - a fifth of the corpus - and they carry a quarter of the checks.

| category | pages | model-read | checks | on model pages | failing there | our pass rate there |
|---|---|---|---|---|---|---|
| arxiv_math | 522 | 0 | 2,927 | 0 | 0 | - |
| headers_footers | 266 | 38 | 760 | 120 | 6 | 95.0% |
| long_tiny_text | 62 | 46 | 442 | 335 | 45 | 86.6% |
| multi_column | 231 | 38 | 884 | 145 | 36 | 75.2% |
| old_scans | 98 | 98 | 526 | 526 | 280 | 46.8% |
| old_scans_math | 36 | 36 | 458 | 458 | 88 | 80.8% |
| tables | 188 | 22 | 1,022 | 134 | 18 | 86.6% |
| **total** | **1,403** | **278** | **7,019** | **1,718** | **473** | **72.5%** |

**473 of our 1,054 remaining failures - 45 per cent - sit on those 278 pages.** On the 5,301 checks the
model never touches we pass 89.0 per cent; on the 1,718 it does, 72.5.

## What a better model is worth

**This section was twice wrong before it was measured, and both corrections are kept here.** The first
version asked what old scans at 70 per cent would be worth and answered +2.9 points; that target was
invented, and no model published scores above the mid-fifties on the category. The second version took
the published ceiling instead - Chandra 2's 51.1 against our 47.0 - and answered about +0.5. Then the
pages were actually read (see "Measured, 12 September" below) and the answer came back **+9.7 points on
the category, +1.2 overall**, because a frontier model reads degraded handwriting far better than any
published table suggested and the benchmark's own leaders are not measured on that tail.

The lesson is the one the project keeps relearning: a published overall score says little about what a
model does on the pages you actually send it. Measure on your own pages.

For scale, the whole model-read pool is 1,718 of the 7,019 checks and we pass 72.5 per cent of them,
against 89.0 per cent on the 5,301 checks the model never touches. 473 of our 1,054 remaining failures
are there.

## Why no rule of ours can win them

Of 216 old-scan near misses (the check's text is in our markdown but not character for character),
**171 allow no edits at all**, and the differences are the model's transcription against the page's: a
comma it drops, a space before a semicolon it closes up, a dash it reads as a full stop, a capital it
lowers. The words come from the model. The tiny-text pool reads the same way - letters misread on a
photographed page. Tool: `scratchpad/nearmiss_edits.py`.

## What the old-scan pages actually are

Rendered and looked at: the pages carrying the most failures are **nineteenth and early twentieth century handwritten letters** in cursive. old_scans/43 is a Civil War era letter in two columns of dense script with the reverse side showing through; old_scans/21 is a patent enquiry on ruled paper. 280 failures sit on 80 of the 98 old-scan pages.

The model's reading of them is close but not exact, which is exactly what the benchmark punishes: on old_scans/21 it wrote 'This device is now' for 'this device is new' and dropped 'I would' before 'sure like to have part of your business'. That is a **handwriting recognition** problem, not a document-layout one. It matters for the choice: the specialists that top olmOCR-bench (olmOCR, dots.ocr, MinerU, PaddleOCR-VL) are trained mostly on printed pages, while cursive is a capability of the large general vision-language models. A model that reads tables and formulas better will not move this pool at all.

Twelve of the 98 old-scan pages taken at random and looked at as a contact sheet: **seven are handwritten cursive** (a 1914 letter to Theodore Roosevelt, two dense manuscript pages, a two-column letter, a patent enquiry, a receipt letter), **three are typewritten** (one faint enough to be hard), and **two are printed** (a newspaper clipping and a 1928 Education Bulletin). So the pool is roughly three-fifths handwriting, a quarter typescript and the rest print. That shape should decide the model, not the olmOCR-bench headline number.

## Are the references winnable?

Checked, because a benchmark whose own reference text is wrong cannot be won by any reader. The tiny-text checks want careful human transcriptions of old encyclopaedia and dictionary pages, phonetic notation and all: "tenant /'tenənt/ noun [C] a person who pays money", and a line that preserves the page's own odd double comma. The words that no English word list knows are proper nouns transcribed correctly - Sungei Ujong, Negri Sembilan, Godavery, Ambon. So they are winnable by a better reader. (A note from 7 September said 17 tiny-text checks carried the hidden layer's own OCR errors; that was measured against run 54 and does not describe today's failures.)

## What we run today

- **Model**: `allenai/olmOCR-2-7B-1025`, FP8 by default (bf16 variant for a 3090), through the `olmocr`
  pipeline (`bench/gpu/run_olmocr2.sh`).
- **Hardware**: one on-demand RTX 4090 (24 GB) on vast.ai, about US$0.335/hour.
- **Time**: 281 pages read in 21 minutes plus about six minutes to install; the whole session cost 85
  cents on 7 September. A model reload between categories is most of the overhead.
- **How it reaches the converter**: the readings are saved as a candidate folder and replayed from disk,
  `--vision-endpoint file:<olmocr2b>+<olmocr2c>`. Nothing is served live.
- **What the model is asked**: the whole page image to markdown; separately, picture crops to transcribe
  (`PICTURE_TEXT_PROMPT` in `truedoc/vision/regions.py`) and figures to describe.

## What a candidate must satisfy

1. Reads a full page image and emits markdown, with tables (markdown or HTML, the scorer reads both) and
   maths as LaTeX.
2. A licence the owner is willing to ship under - D007 keeps the product path Apache-2.0, BSD or MIT, and
   the model weights are the one place still open.
3. Fits a GPU that can actually be rented on demand: 24 GB is cheap and plentiful, 48 GB and 80 GB cost
   more and queue longer.
4. Can be driven over a folder of page images in one batch job, since we replay from disk rather than
   serving.

## The candidates (researched 12 Sept 2026; every score self-reported unless marked)

Only the old-scans column bears on us directly, because that is the category our model reads end to end.
The overall column is what the model scores reading the whole benchmark on its own, which is not what we
ask of it.

| model | overall | old scans | size | fits 24 GB | licence | served |
|---|---|---|---|---|---|---|
| Infinity-Parser2-Pro (infly) | 87.6 | not published | 35.1B MoE | no, wants two cards | Apache-2.0 | vLLM, SGLang, folder batch |
| Infinity-Parser2-Flash (infly) | 86.0 | not published | 2.2B | yes | Apache-2.0 | same |
| **Chandra 2 (datalab)** | 85.8 | **51.1, the best open weights** | 5.3B, 10.6 GB | yes | modified OpenRAIL-M: forbidden above US$2M revenue or funding, and forbidden for anything competing with Datalab's own product | vLLM, transformers, folder batch |
| **dots.mocr (rednote)** | 83.9 | 48.2 | 3.0B | yes | **MIT**, with a companion agreement granting commercial and SaaS use | vLLM 0.11+ |
| Chandra 1 (datalab) | 83.1 | 50.4 | 9B | yes | OpenRAIL-M | vLLM, SGLang |
| Infinity-Parser-7B (infly) | 82.5 | 47.9 | 8.3B | yes | Apache-2.0 | vLLM, SGLang |
| **olmOCR-2-7B-1025 (what we run)** | 82.4 (AllenAI's own measurement) | 47.7 | 8B | yes, 12 GB is enough | Apache-2.0 | the olmocr pipeline |
| PaddleOCR-VL | 80.0 | 37.8 | 0.9B | yes | Apache-2.0 | vLLM, SGLang |
| DeepSeek-OCR-2 | 76.3 | not published | 3B | yes | Apache-2.0 | vLLM, SGLang |
| MinerU 2.5 | 75.2 | 33.7 | 1.2B | yes, 8 GB | weights Apache-2.0, toolkit under its own licence | its own CLI |

Not open weights, for the ceiling only: Unsiloed 88.0, Nanonets OCR-3 87.4, Datalab's hosted API 86.7
(old scans 54.6, the highest figure published by anyone), Mistral OCR 4 85.2.

Three things to weigh:

- **Chandra 2 is the one to beat on our category** (51.1 against our 47.7) **and the only model above 83
  that publishes a per-category breakdown at all.** Its licence is the problem: a US$2M revenue-or-funding
  cap and a clause forbidding use in anything that competes with Datalab's own PDF-to-markdown service,
  which is exactly what TrueDoc is. That is the owner's call, and it sits squarely against D007's intent.
- **dots.mocr is the clean one**: MIT weights, 3B, fits anything, +0.5 on old scans over what we run. Note
  its *inference code* pulls in AGPL PyMuPDF, which we have just spent M18 removing from our own path;
  that affects how we run it, not the weights.
- **Infinity-Parser2 tops the table but is the least verifiable**: neither model card, repo nor paper
  publishes a per-category breakdown, so its old-scans figure is unknown, and it is not even documented
  whether its "overall" covers all eight categories. Pro needs two cards.

There is no audited leaderboard: AllenAI's own table is stale at October 2025 and its Hugging Face space
returns an authentication error, so the 17 entries on the dataset page are self-declared.

## The handwriting question, and a claim that does not survive checking

A third-party review states that olmOCR-bench's old-scans set is Library of Congress letters and
typewritten documents, deliberately excluding handwriting. **That is not what the files hold.** Twelve
old-scan PDFs rendered at random: seven are handwritten cursive. And the benchmark tests them - old_scans
43.pdf, a two-column Civil War letter in dense script, carries seven checks quoting the cursive exactly,
down to the ampersands in "lock & key". So handwriting is squarely inside the category we are trying to
move.

What is published about handwriting is thin and contradictory: an independent test on a different
benchmark puts olmOCR-2 at 94 per cent on handwriting, second only to a frontier commercial model, and
Ai2 say they added 20,000 pages of difficult handwritten and typewritten documents to its training mix.
PaddleOCR-VL claims to excel at handwriting and historical documents yet scores 37.8 on old scans.
CHURRO, a 3B model purpose-built for degraded historical text, publishes no olmOCR-bench score and does
not write markdown with tables and formulas, so it cannot replace the page reader - though it could, in
principle, be a second opinion on the old-scan pages alone.

## Measured, 12 September: a frontier model reading the old scans

The open question in every published table was what a better model would actually do on *our* pages.
Rather than infer it from model cards, the 98 old-scan pages were read again from their images by a
frontier model (me, Opus 5, under the owner's Max plan, which their own note of 3 September says covers
development looking; an API key is a separate product and a separate bill). Fifteen subagents transcribed
them **blind** - each saw the page image and olmOCR's own instruction, never the benchmark's expected
text - and the readings were scored against the same 526 checks, paired page by page.

**The result over 97 pages and 517 checks** (page 64 is excluded, see below):

| reading | present | order | absent | total |
|---|---|---|---|---|
| olmOCR-2, as we run it today | 120 | 53 | 66 | 239 (46.2%) |
| frontier, first prompt | 160 | 66 | 31 | 257 (49.7%) |
| frontier, with the furniture instruction | 157 | 66 | 66 | **289 (55.9%)** |

Counting only the checks the two read differently, which is the statistic that carries the verdict: the
corrected frontier read wins 70 and loses 20, **net +50 over 90 disagreements**, where sampling noise at
that size is about 9. On `present` it is +37, on `order` +13, and on `absent` the two are level with not
one check between them.

**That is +9.7 points on the old-scans category, or +1.2 on the overall score** - 84.1 to about 85.3. The
three rule changes of the same day, each proved by its own full run, bought 0.05 between them.

### The first prompt cost 35 checks, and the lesson generalises

The first read looked like a tie (257 against 239) because it failed 35 of the 68 `absent` checks. Asked
what text each said must not appear, every single one was page furniture: 'Copy.', '2590', "Mch 20/'62",
'20 Blue anchor', 'FORM 1864', 'ack 5/27/14', 'CABLE ADDRESS, BUVALE', '74 EDUCATION BULLETIN',
'JANUARY 1920 75', 'new york State FOUNDED 1814.' Archivists' annotations, docket dates, catalogue
numbers, letterhead and running heads. olmOCR-2 is trained to drop them; the transcription prompt had
said what to keep and never what to leave out. One added paragraph took that row from 31 to 66, level
with olmOCR-2, and cost nothing in reading accuracy.

**So the rental experiment needs the same control.** dots.mocr, Infinity-Parser2 and Chandra may or may
not share olmOCR's convention, and a model that keeps the furniture will score worse than it reads.
Without holding that constant the comparison measures habits, not capability.

Checked and clean, because it would otherwise have wrecked the comparison: the converter strips running
heads from a model's reading using the page's own text as a witness, and on a scanned page there is no
witness - **zero of the 98 pages had anything stripped**, so olmOCR's discipline is its own, not ours.

### Where the gain sits: entirely in the hard tail

Splitting the pages by how well olmOCR-2 does on them, as a proxy for how legible they are:

| page difficulty | pages | checks | olmOCR-2 | frontier | delta |
|---|---|---|---|---|---|
| olmOCR passes 70% or more | 24 | 128 | 117 (91.4%) | 117 (91.4%) | 0 |
| 30 to 70% | 28 | 151 | 73 (48.3%) | 85 (56.3%) | +12 |
| under 30% | 33 | 172 | 25 (14.5%) | 54 (31.4%) | +29 |

**On legible pages the two readers are level to the check.** The whole advantage is the degraded
handwritten tail, where the frontier read more than doubles the score. For a customer whose documents are
clean and printed this buys nothing at all - those pages have a text layer and never reach a model.

### TrueDoc can already tell which pages those are

The converter runs a classical OCR over any page with no text layer and records how word-like the result
is (`ocr_wordlike` in `page.meta`); the function's own docstring says real text scores 0.6 to 0.9 and
handwriting noise under 0.3. Measured on eight pages from each group:

| group | wordlike median | range | OCR lines |
|---|---|---|---|
| olmOCR reads well | 0.84 | 0.11 to 0.91 | 20 to 37 |
| olmOCR struggles | 0.36 | 0.00 to 0.58 | 0 to 13 |

A threshold at 0.6 catches every hard page in the sample and misroutes three easy ones, which is the cheap
direction: on legible pages the deep reader is merely equal, so a misroute wastes a fraction of a cent.
**The routing needs no declaration from the user** - the converter can say "this page has no text layer
and our own reader gets nothing word-like from it, so it goes to the deep reader". The user still opts in,
because those pages leave the machine, but they opt in to a policy rather than sorting their own archive.

### What the number is not

Every one of these favours the frontier read, and they are why this is a ceiling rather than a production
figure:

- It is Opus 5, not the cheaper model an API call would use.
- The agents could zoom into a region; one API call cannot.
- They were given transcription guidance where olmOCR gets its terse prompt.
- The page was rendered at 2,200 px against olmOCR's 1,288, which is olmOCR's training size, not a limit.

### One page was refused to an agent, but not to the API - a correction

While the pages were being hand-read, old_scans/64 was stopped twice by a content filter, on output,
once inside a batch and once alone. I recorded that as an operational difference: that a frontier API
would refuse some historical material where an open model on our own hardware would not.

**The production run contradicts it.** The same page, read through the product's own path with one
ordinary API call, came back with 922 words and no complaint, and all 98 pages read without a single
failure. So the refusal was a property of the agent harness that was doing the hand-reading, not of the
Messages API as the converter uses it. The claim as I first made it was wrong and is withdrawn.

What survives is narrower and still worth knowing: an assistant product wrapped around a model can
refuse material that the raw interface reads happily, so anyone building on a chat-shaped frontier
service should test with their own worst documents rather than assume.

## Measured, 12 September, second pass: what one ordinary API call delivers

The hand read could only put a ceiling on this, because it was Opus 5 able to look twice at a hard
patch. The production question is what a shipped TrueDoc would get from one call a page. Run through
the converter's own frontier path (`--vision-endpoint anthropic`, which defaults to Sonnet 5), four
processes, 98 pages, no failures, about fifteen minutes:

| reading | present | order | absent | total |
|---|---|---|---|---|
| olmOCR-2, what we run today | 124 | 55 | 68 | 247 (47.0%) |
| **Sonnet 5, one API call a page** | 145 | 62 | 67 | **274 (52.1%)** |
| Opus 5 by hand, able to zoom | 157 | 66 | 66 | 289 (54.9%, and short 9 checks) |

Counting only the checks the API and olmOCR-2 read differently: **+21 on present, +7 on order, -1 on
absent, net +27 over 71 disagreements** where noise is about 8.

**So one ordinary call is worth +5.1 points on the old-scans category and +0.64 on the overall score**,
84.1 to about 84.7. The hand read's ceiling was +8.9. A single cheap call therefore recovers around
three fifths of what careful reading with a zoom can get, which says the remaining gap is method -
cropping a hard page and asking again - rather than model class.

**The furniture instruction held in production**: the absent row is 67 against olmOCR's 68, level, where
the first hand read without that paragraph had scored 31 of 68. The prompt change carried straight over.

Two defects the run itself turned up, both fixed and tested:

- **olmOCR's prompt asks for a front matter block.** olmOCR 2 answers with `---` delimiters, which the
  parser strips; a general model answers with a fenced yaml block, which it did not, so five lines of
  `primary_language: en` reached the reader's document on the first page tried. A general model is no
  longer asked for those fields (nothing reads them) and the parser now strips a fence too.
- **The converter is not thread-safe.** Four readers through PDFium, the layout model and the OCR
  engine in threads crashed the interpreter outright. It runs in processes now.

## The ladder: five readings of the same pages, one thing changed at a time

The production call is +5.1, the hand read was +9.7. To find out what the difference is made of - a
bigger model, a better prompt, more pixels, a second look - each was changed on its own and scored on
the 517 checks every reading covers (page 64 left out of all of them, since the hand read never got it).

| reading | checks | rate | against olmOCR-2 |
|---|---|---|---|
| olmOCR-2, what we run today | 239 | 46.2% | - |
| Sonnet 5, one API call a page | 267 | 51.6% | +5.4 on the category, +0.68 overall |
| **Sonnet 5 plus the faithful-transcription paragraph** | **273** | **52.8%** | **+6.6, +0.82** |
| Opus 5, one API call, no paragraph | 271 | 52.4% | +6.2, +0.77 |
| the hand read: Opus, able to zoom, 2,200 px | 289 | 55.9% | +9.7, +1.21 |

**A paragraph beat a bigger model.** Telling a general model to keep the writer's spelling,
capitalisation and punctuation and not to tidy anything is worth 6 checks and costs nothing. Moving to
Opus is worth 4 over Sonnet, inside the noise at this size, at several times the price a page. The
paragraph ships (`_FAITHFUL` in `truedoc/vision/anthropic_api.py`); Opus does not.

**What is left is 16 checks and it is not model class.** Opus at the same resolution with one look does
not get them, so the residue is the two things only the hand read had: the page at 2,200 px where the
API path sends 1,568, and a second look at a hard patch. Both are plumbing rather than purchase, and
reading a page as two overlapping halves tests them together - each half arrives at full resolution and
gets its own pass. 16 checks is about +3 on the category and +0.4 overall, several times what a good
rule run buys.

**A note on prices.** Sonnet reads a page in about 20 seconds and 98 pages cost a few dollars; Opus is
several times that per page for four checks. The deep read is only ever meant for the hard tail anyway -
a third of the scanned pages, which are themselves a fifth of the corpus - so the bill is small either
way, and the argument for Sonnet is that it is better value, not that Opus is unaffordable.

## The cheapest way to settle it## The cheapest way to settle it

One rental, several models, one small page set. The 98 old-scan pages are the concentrated pool: 526 checks, 280 of our failures, and the category score is exactly the pass rate on them, so a candidate can be judged in minutes without a full conversion run. Shape of the experiment:

1. Ship the 98 page PDFs (they are already in `bench/gpu/pdfs/`, and `fetch_pages.py` can pull    them on the rented machine instead of over the owner's uplink).
2. Run each candidate over the same 98 pages, saving one markdown file per page.
3. Bring the readings back, place each as its own candidate folder, and score each with the    official scorer against the old-scan checks alone. That is a number per model in one sitting.
4. Whichever wins, re-read all 278 model pages with it and take a full run.

For scale: the 7 September session read 281 pages in 21 minutes on a 24 GB RTX 4090 and cost 85 cents all in. Even a model needing an 80 GB card for an hour or two is a few dollars.

## The licence crux

D007 keeps the product path permissive, and the open item under it is already the *weights* the pipeline
downloads - the layout model and the OCR recogniser. A page-reading model makes that sharper, because
under D019 it reads every page without a digital text layer, so its weights ship with the product.

- **olmOCR-2, what we run: Apache-2.0.** Clean.
- **dots.mocr: MIT**, with a companion agreement that explicitly grants commercial and SaaS use. Clean.
- **Infinity-Parser2 (Pro and Flash): Apache-2.0.** Clean.
- **Chandra 2: not clean for us.** Its modified OpenRAIL-M forbids use above US$2M of revenue or funding,
  and forbids use in a product competing with Datalab's own - and Datalab sells a hosted PDF-to-markdown
  service. It is the best open model on our category and the one we cannot ship.

So the licence-clean models scoring above what we run are **dots.mocr** (old scans 48.2 against our 47.7,
MIT, 3B) and **Infinity-Parser2-Flash** (overall 86.0, old scans not published, Apache-2.0, 2.2B).

## My view, for the conversation

1. **The deep read is worth having, and it is worth more than the published tables implied.** Measured on
   our own pages: +9.7 on the old-scans category, +1.2 overall, with the paired count 70 to 20 over 90
   disagreements. That is not a rounding error and no amount of rule work reaches it.
2. **It is worth having only for the hard tail.** On pages a model already reads well the two are level
   to the check. This is not "swap the model", it is "add a second tier for the pages that need one".
3. **The converter can route to that tier by itself**, from a number it already computes, and the user
   opts in to a policy rather than sorting their documents.
4. **The measurement is a ceiling, not a production figure.** It is Opus 5 with the ability to zoom, a
   fuller prompt and a larger page image. The next measurement worth making is the production call:
   `--vision-endpoint anthropic` on the same 98 pages with the furniture instruction, which needs an API
   key with its own billing and costs a few dollars. That number, not this one, is what a shipped product
   would deliver.
5. **The rental is now the second question, not the first.** If the hard tail goes to a frontier API, the
   open model's job is the pages where everything scores about 91 per cent, and the choice between
   olmOCR-2, dots.mocr and Infinity-Parser2 barely matters. Rent only to confirm that.
6. **Two things sit outside the score and should weigh on the decision**: a frontier API refused one of
   98 archival pages outright, and every page sent to it leaves the machine. An open model on the owner's
   own hardware does neither. For an archive customer that may matter more than a point of benchmark.

## Open questions for the owner

- Whether to spend the rental on a **stronger general model** (more parameters) or a **specialist** whose
  published olmOCR-bench score is higher than olmOCR-2's 82.4.
- Whether handwriting matters: a large part of the old-scans pool is handwritten letters, and no page-to
  -markdown model reads those well.
- Whether to re-read only the 98 old-scan pages first (the cheapest, most concentrated test) or all 278.
