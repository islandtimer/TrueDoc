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

**Correction (15:40, after the model research).** An earlier version of this section asked what old scans
at 70 per cent would be worth and answered +2.9 points. That target was invented. **No model published,
open or closed, scores above the mid-fifties on olmOCR-bench's old-scans category.** The published ranking
is: Datalab's hosted API 54.6, Unsiloed 52.9 (closed), Chandra 2 51.1, Chandra 1 50.4, Nanonets OCR-3 49.6
(weights never released), dots.mocr 48.2, olmOCR-2 47.7 (what we run), then everything else below 43 down
to GOT-OCR2 at 22.1. Our own harness reads 47.0 on that category, within a point of olmOCR-2's published
figure, which is what you would expect since every old-scan page is model-read.

So the realistic arithmetic, using the best open weights available rather than a wish:

| category | checks | ours now | best published open weights | checks won | overall |
|---|---|---|---|---|---|
| old_scans | 526 | 47.0 | 51.1 (Chandra 2) | +22 | +0.5 |
| old_scans_math | 458 | 80.8 | not published per-category by any leader | ? | ? |
| long_tiny_text | 442 | 88.7 | not published per-category by any leader | ? | ? |

**A model swap is worth about half a point on old scans, not three points.** The upside on the other two
model-read categories is unknown because the leaders do not publish a per-category breakdown - Chandra 2
is the only model above 83 that does. The whole model-read pool is 1,718 of the 7,019 checks and we pass
72.5 per cent of them, against 89.0 per cent on the 5,301 checks the model never touches; but the
published ceilings say most of that gap is the difficulty of the pages, not the model we chose.

Two further cautions on the numbers:

- **Every published score above 82.5 is self-reported by the model's authors.** The only figures AllenAI
  measured itself are olmOCR's own, DeepSeek-OCR 75.7, Marker 76.1, Nanonets-OCR2 69.5 and Mistral's API.
- **Our harness and theirs are not on the same scale.** We score 84.1 where olmOCR-2 alone publishes 82.4,
  because we read the 1,125 digital pages from their own text layer and only send the rest to the model.
  A model's published overall therefore says little about what it would do inside our pipeline; only its
  old-scans and other model-read categories bear on us at all.

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

## The cheapest way to settle it

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

1. **The rental is worth doing, but not for the reason I gave earlier today.** I said a better model was
   worth about 4.6 points; that was wrong, and the correction is above. The published ceiling on old scans
   is the mid-fifties for anyone, so the realistic prize is half a point there, plus an unknown on
   old-scan maths and tiny text that nobody publishes.
2. **The cheap experiment answers the unknown.** One rental, the 98 old-scan pages, three candidates
   (dots.mocr, Infinity-Parser2-Flash, and olmOCR-2 again as the control), scored against the old-scan
   checks alone. That is an hour and a few dollars, and it turns two unknowns into numbers. Adding the 36
   old-scan maths pages and the 46 tiny-text pages makes it 180 pages and still one sitting.
3. **Run the control.** Re-reading the same pages with olmOCR-2 tells us how much of the gap is the model
   at all: if the control comes back at 47 and the others at 48, the model is not the lever and we should
   stop looking there.
4. **Chandra 2 is worth measuring even though we cannot ship it,** because it is the best published on our
   category. If it reads the old scans markedly better than the clean models, that says the gap is real
   and worth chasing another way; if it does not, the question is closed.
5. **What I would not do**: rent a large general vision-language model on spec. Qwen3-VL and InternVL3.5
   publish no olmOCR-bench score at all, the only general VLMs AllenAI measured scored 31.5 and 65.5, and
   the 30B checkpoints need 48 GB.

## Open questions for the owner

- Whether to spend the rental on a **stronger general model** (more parameters) or a **specialist** whose
  published olmOCR-bench score is higher than olmOCR-2's 82.4.
- Whether handwriting matters: a large part of the old-scans pool is handwritten letters, and no page-to
  -markdown model reads those well.
- Whether to re-read only the 98 old-scan pages first (the cheapest, most concentrated test) or all 278.
