# How TrueDoc converts a page

Read this to understand the code layout before changing anything. Each stage is a module; each keeps what it learned on the `Page`/`Block` objects in `truedoc/model.py`, and every structural decision records its `provenance` (which stage made it) so later stages and humans can audit it.

```
PDF page
  |
  |  1. extract/textlayer.py      characters (with visibility: hidden text is set aside), words, lines (re-joined
  |                               around scripts, never across column gutters), rulings, images, text-layer quality
  |     ocr/rapid.py              (only if the page has no usable text) RapidOCR -> same evidence shapes; a page read sideways is turned and read again
  v
  |  2. tables/ruled.py           tables with visible rulings, found from the page's drawn rules by tables/ruled_pdfium.py;
  |                               one-row boxes too, kept only when pipeline._adopt_ruled_headers finds their column
  |                               headings just above the box - never a sentence, which crosses from one column to the
  |                               next on a word space (tables/cells.runs_across_columns)
  |     tables/aligned.py         unruled tables from whitespace channels and voted column cuts; prose is rejected.
  |                               A second look (_refine_segments) adds a cut judged only by the rows with words on both
  |                               sides of it, refused when every segment it would divide crosses on a word space; it
  |                               sharpens a table the first look found and never makes one of its own
  |                               (find_aligned_tables). A band laid across a table (_band_segments, _is_band) neither
  |                               votes on a cut nor is divided, and spans the grid. _merge_wrapped_rows folds a wrapped
  |                               cell into its row, and _label_carries_on carries a label on to its second line when
  |                               the short value beside it is left empty (a capitalised second line only when the
  |                               row's other cells carry on too; never one holding a digit unless it starts in lower
  |                               case), and an entry wrapped with its value on its last line becomes one row when the
  |                               row after it starts an entry of its own (counted as its lines when the table is judged)
  v
  |  3. segment/blocks.py         lines -> paragraph blocks (gap, overlap, size, typeface rules)
  |     classify/blocks.py        heuristic kinds: heading, header/footer, page/line numbers, list, caption
  v
  |  4. layout/docling_layout.py  RT-DETR layout model on the rendered page (CPU, ~3 s)
  |     layout/fuse.py            model regions override kinds, split straddling blocks, add figures,
  |                               build tables inside table boxes (a header row the box missed is taken from
  |                               just above it, never a sentence crossing the columns on word spaces), veto false tables
  |     tables/rule_grid.py       a confident table box whose text builds no table - its columns hold only drawn marks -
  |                               is read from its own rules: rows between them, columns where their pieces meet at the
  |                               same x on at least three rules, each word in the cell its centre falls in
  |     tables/fill_grid.py       after the layout model: a table the text built across the cells its page draws
  |                               (tiled fills and the rules among them) is read again from the drawing, spans and
  |                               header included - only where words of one text cell lie on both sides of a drawn
  |                               edge (redraw_tables)
  |     classify/page_numbers.py  after the layout model and the margin clean-up: a margin line taken for the page's
  |                               number is text again when the pages beside it number themselves at a distance it does
  |                               not fit and none prints the same line at the same place (release_pointers)
  v
  |  5. math/extract.py           display formulas per equation line, inline maths runs
  |     math/reconstruct.py       glyphs + rules -> LaTeX (fractions, scripts, radicals, matrices, accents)
  v
  |  6. segment/order.py          reading order: column split when a full-height gap exists, else peel
  |                               the topmost spanning block, else horizontal cut
  v
  |  6b. marks.py                 ticks, crosses and bullets drawn as shapes or tiny images are
  |                              rendered, matched to templates and written into the cell or line
  |  6c. vision/ (optional)     pages with no usable text are read from their image by a served
  |                              model (olmOCR 2 behind an OpenAI-style endpoint) or Anthropic's API
  |                              (`anthropic[:model]`, key from ANTHROPIC_API_KEY); then icon-only table
  |                              cells and figures are asked about (vision/regions.py, pipeline
  |                              _read_regions_with_model); everything marked as inferred (D015),
  |                              and the mark names the reader that read the page, not the stage
  |  6c'. the deep reader        a page with no text layer whose own OCR comes back with nothing
  |      (optional, D025)        word-like goes to a second, paid reader instead (--vision-deep;
  |                              pipeline._needs_a_deeper_read). Measured: on pages the ordinary
  |                              reader handles the two are level to the check, and on the hardest
  |                              third of the scanned pages the deep one roughly doubles the score.
  |                              A model's maths arrives between dollar signs and is translated into
  |                              the document's own delimiters first (vision/mathdelims.py), or D024
  |                              escapes it into literal text - which cost 77 checks in run 90.
  |     (maths notes, 3 Sept pm: `is_extension_font` names every cmex-layout font (CM, Latin Modern, tx/px, MathTime, Euler); fixed-size
  |      delimiters map to \big/\Big/\bigg/\Bigg by glyph code; script-sized fraction stacks are assigned to a script by their
  |      position against the baseline; numerators join the line below their bar; bars between rows veto a matrix)
  |  6d. footnotes (pipeline._mark_footnotes): raised markers become [^n], matching notes become [^n]: text;
  |      pipeline._link_endnotes (whole document, after all pages): notes on later pages, keys unique across pages;
  |      a marker whose note is nowhere in the document goes back to the printed digits
  |     (maths notes, 3 Sept evening: the two epsilons and the two phis are told apart by glyph width, not Unicode
  |      (symbols.epsilon_by_width / phi_by_width, thresholds per design size); bars from extender pieces are sized
  |      by the piece count; mapsto is rebuilt from mapstochar + arrow (reconstruct._merge_mapsto); Unicode
  |      mathematical-alphanumeric letters become plain letters with their style (symbols._math_alphanumeric).
  |      Tried and reverted: writing sized brackets plain around line-high content (run 15: +2 checks, -6))
  |  7. render/okf.py             markdown body (hyphenation repair, cross-column joins, tables,
  |                               empty output for unreadable pages) + YAML front matter
  v
OKF markdown
```

## Principles the code follows

- **Evidence first.** Characters come from the PDF's own text layer whenever one exists. Models decide *what kind of thing* an area is; they never replace characters that the PDF already provides.
- **Structure with provenance.** `Block.provenance` says whether a kind came from a text rule, the layout model, a table finder or the maths rebuild. When two stages disagree, the more specific and more confident source wins (`layout/fuse.py`).
- **Nothing invented.** Unreadable pages produce nothing; low-confidence OCR is rejected; formulas are rebuilt only from glyphs that are actually there.
- **Cheap where easy, careful where hard.** The layout model and OCR are optional stages (`--no-layout`, `--no-ocr`); the text-layer path alone runs at about a page per second.

## Things the text layer gets wrong, and how stage 1 corrects them

- **Maths-extension fonts (cmex and kin).** Big brackets, big operators, wide hats and radicals hang below their origin, and MuPDF reports a box taken from the font's ascender and descender, not from the glyph. Stage 1 makes a second extraction pass with MuPDF's accurate-box and raw-code flags and stores the measured outline on `Char.ink`; where MuPDF cannot measure a glyph, `math/reconstruct.py` rebuilds the box from the font's design metrics (`CMEX_EXTENT` in `math/symbols.py`). Several cmex codes are whitespace characters (a size-4 "(" is 0x20, "}" is a tab); they are carried on private-use characters so that blank filters keep them. MuPDF also inserts a synthetic space wherever it sees a gap, and that space takes the font of the span it lands in, so a blank in an extension-font span counts as a glyph only when the text trace (which lists drawn glyphs) has one at that position.
- **Glyph names that lie.** Characters arrive through the Adobe glyph list: TeX's `\phi` glyph (named "phi") comes back as the character KaTeX draws for `\varphi`; cmsy's `\setminus` is named "backslash"; the text fonts' "Omega" and "Delta" are the ohm and increment signs. `math/symbols.py` maps them back by font.
- **Pages lying on their side (6 Sept).** A landscape scan of a portrait page, or a table printed sideways, arrives with its text running up or down the page. `extract_page` counts the characters in vertical lines by direction; `ocr/rapid.py` asks the engine's angle classifier which way the tall boxes read. Either way `pipeline._turn_page` puts the quarter turn onto the in-memory PyMuPDF page (`set_rotation`) and extracts it again, so every later stage sees the page upright; the front matter lists it under `truedoc.turned_pages`.
- **OCR-layer columns (4 Sept).** On a scanned page with a hidden text layer, `_reassemble_ocr_layer` finds column boundaries as channels that many rows' word gaps vote for. A channel carries the vertical range of the rows that voted, so the vote count and the "no word straddles it" test are judged within that band and only lines in the band are split by it: a page that opens with a full-width abstract over two columns gets its boundary in the lower band instead of nowhere.
- **Shattered lines.** A line with superscripts often arrives as several segments whose spans interleave, plus separate segments for each bracket piece; `_reassemble_lines` re-joins segments on one baseline (sized by their *main* text, not their scripts), folds bracket-only fragments into the line they touch, and lets script-sized fragments (numerators, denominators, stray subscripts) join the line with the nearest baseline.
- **Widths that answer for another glyph (15 Sept).** The PDFium reader boxes a level character from its origin to its origin plus the advance `FPDFFont_GetGlyphWidth` gives for its Unicode value, and a font that maps its ligatures to letters answers for the ligature: on RAA's landlord PDS every f was given its ff ligature's 7.34pt where the f advances 2.54, the box ran over the space after it, and "If you" read "Ifyou". `extract/pdftext_rawdict._geometry` takes an advance that runs more than a quarter of the size past the next character's origin back to that origin - only to a character the file holds, at least 0.15 of the size along, since a line break or a space PDFium makes up stands a fraction of a point after the glyph's own origin; and only to a character set beside the glyph - their ink sharing at least a tenth of the smaller one's height, or one of them having no ink, as a space has none (`_beside`) - since an accent or a limit set over or under a glyph, whatever character its font maps it to, says nothing of where the glyph ends.
- **Unicode maps that spoil ligatures (15 Sept).** A font's ToUnicode map can send its ff, fi and fl glyphs to a single "f", so the file's own text reads "ofer", "fnd" and "Cooling-of". The encoding still names each glyph ("f_f", "fi"), so `extract/glyph_names.lossy_ligature_letters` reads the page's content stream with pypdf, aligns its text with PDFium's characters by sequence (PDFium reports no codes, and its characters come in another order and number than the codes drawn), and gives each character drawn with such a glyph the letters its name spells; no word list is consulted. Not reached yet: fonts with two-byte codes, and text inside form XObjects.

## Reading the page without PyMuPDF (M18, D007, D022) - read this before touching geometry

PyMuPDF is AGPL or a paid Artifex licence, and D007 keeps AGPL out of the product path, so each
stage that reads a PDF goes through PDFium. **Since run 71 the PDFium readers are the default
(D023)**; MuPDF stays reachable by name for measurement. Each stage was proved against a quantity
the two libraries must agree on before it was wired, which is what D022 asks for; the score is the
second check - run 71 with every switch on reads 84.0, level with the MuPDF run and above it on the
held-out fifth (81.1 against 80.9).

| switch (default first) | what it moves | module | measured, no model, whole category |
|---|---|---|---|
| `TRUEDOC_READER=pdftext` / `mupdf` | characters, boxes, fonts, colours | `extract/pdftext_rawdict.py`, `extract/glyph_names.py` | quick gate 100/128 either way; tiny text 364 against MuPDF's 361 of 442 |
| `TRUEDOC_RENDERER=pdfium` / `mupdf` | every page rendering | `extract/render.py` | 100/128, and identical marks on 82 rotated pages - measured at commit 3fb9e5b; from 905f456 (10 Sept 10:43) until run 83 a call left on a renamed function made every PDFium render fail and MuPDF drew every page, unnoticed because the fallback is silent |
| `TRUEDOC_OBJECTS=pdfium` / `mupdf` | drawings, images, ruled tables | `extract/pdfium_objects.py`, `tables/ruled_pdfium.py` | tables 850 against 848 of 1,022; multi-column 678 against 678 of 884 |

What the swap removed, a stage at a time (12 Sept): **A** - `truedoc/geometry.py`, TrueDoc's own `Rect`,
`Matrix` and `transform_point`, PyMuPDF's arithmetic to the bit (MuPDF computes in 32-bit floats, and so
does this). **B** - the page-quality check's invisible-text count taken from the reader's own characters
instead of a second `get_texttrace`. **C** - `truedoc/extract/handle.py`, PDFium document and page handles
carrying what the product asks of a page: its file, its index, its size as drawn, its rotation, the matrix
that turns unrotated coordinates into drawn ones, and `set_rotation`, which turns a page in memory only.
**D** - the renderer repaired (see below) and the vision stage's crops taken through the same handle. **E**
- PyMuPDF imported only when the old reader asks for it, and an empty picture handed back for a crop with
nothing of the page inside it, which PDFium refuses to draw. Proved run by run: run 82's markdown was run
81's byte for byte on all 1,403 pages, run 83 put PDFium in charge of drawing at a cost of four checks,
run 84 carried the owner's dollar-sign decision (D024), and run 85 gave run 84's markdown byte for byte
with three calls reaching PyMuPDF in the whole run - all three from the test suite, none from the
conversion of any page.

**Coordinate conventions are where this goes wrong, every time.** Four different spaces are in play
and mixing them fails silently - nothing crashes, the document just comes out wrong.

- **MuPDF reports text, drawings and images in the page's *unrotated* space.** `textlayer._rect`
  turns them once, into the rendered page's space, and that is where `Page.chars`, `Block.bbox` and
  the layout model's boxes live.
- **A clip rectangle is not text.** `get_pixmap` clips in the *rendered* space. Three call sites
  used to turn a box back before clipping and so photographed the wrong patch of a rotated page;
  see `tests/test_rotated_page_clip.py`.
- **PDFium measures up from the bottom left.** Every box is flipped about the crop box on the way
  in (`_flip` in `pdftext_rawdict.py`, `flip` in `pdfium_objects.py`).
- **pdftext rotates its own coordinates into display space and PyMuPDF does not**, so the page
  rotation is taken back out in `pdftext_rawdict._line_dir`.
- **PDFium object bounds are already through the object's own matrix; its path *segments* are not**,
  and neither is either through a parent form's matrix. `pdfium_objects._walk` carries the form
  matrix down and composes the object's own for segments. Missing the first put one page's rules
  178.5pt out; missing the second put its rectangles at y = -32,000 while the bounding boxes looked
  perfect.

**Two rules the swap taught.** *Never hand TrueDoc's geometry to a PyMuPDF object.* PyMuPDF's conversions
take only its own types, tuples and lists, and read anything else as the identity or an empty rectangle:
`pymupdf.Point(p) * M` with TrueDoc's `M` leaves the point exactly where it was, without a word. That was
stage C's first fault, caught two minutes into its proof run, and `transform_point` replaced it. Convert at
the hand-off - `pymupdf.Rect(*r)`, `tuple(r)`. *PyMuPDF builds the rotation matrix from the /CropBox as
written,* not from the drawn page, which is the crop box cut to the media box, and keeps that size in
32-bit floats; on a page whose crop box reaches past its media box the two differ, and the handle copies
PyMuPDF, quirk included.

**Silent fallbacks hide faults.** The renderer falls back to MuPDF whenever PDFium declines, and from
10 Sept 10:43 (905f456) to run 82 one call left on a renamed function made every PDFium render fail: MuPDF
drew every page image while the switch read PDFium, and nothing said so. `tests/test_render_pdfium.py`
fails now if an upright page, or one turned in memory, reaches the fallback. Two more differences surfaced
the moment PDFium really drew. A clip must be handed over as the pixel box MuPDF would have drawn, half a
pixel inside each edge, because PDFium rounds each inset up and a crop came out a pixel short. And a mark
must be read from a crop drawn four times larger than the classifier's grid and shrunk here, a cell
counting as ink when a quarter of its pixels are: at the grid's own size PDFium keeps a stroke a pixel wide
where MuPDF thins it, and the same tick covered 0.146 of the crop under one and 0.177 under the other -
a tick drawn one way and an arrow drawn the other.

**Still on PyMuPDF:** the old readers themselves (`TRUEDOC_READER=mupdf`, `TRUEDOC_RENDERER=mupdf`,
`TRUEDOC_OBJECTS=mupdf`) and the measurement tools, which import the package for themselves. The product
path does not: `tests/test_no_pymupdf.py` converts a document in an interpreter where importing PyMuPDF
raises, and `pyproject.toml` carries the package under the `mupdf` and `bench` extras rather than among the
dependencies. D007 holds the licence table for everything the product path does import.

## Where the benchmark harness lives

`truedoc/bench/olmocr.py` converts the benchmark PDFs in parallel and calls the official scorer through `bench/score_olmocr.py`. `bench/inspect_failures.py` summarises failed tests; `bench/math_check.py` scores formulas on a few pages; `bench/quick_check.py` is the regression guard on 13 fixed pages.

## Adding a new stage

1. Give it a single entry point taking a `Page` (and the PyMuPDF page if it needs rendering).
2. Record `provenance` and `confidence` on anything it changes.
3. Add a synthetic unit test under `tests/` (see `test_pipeline_synthetic.py` for building PDFs in a test).
4. Run `bench/quick_check.py`, then the affected benchmark section, then record the numbers in `docs/BENCHMARKS.md` and the story in `docs/PROGRESS_LOG.md`.
