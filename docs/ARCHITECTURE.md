# How TrueDoc converts a page

Read this to understand the code layout before changing anything. Each stage is a module; each keeps what it learned on the `Page`/`Block` objects in `truedoc/model.py`, and every structural decision records its `provenance` (which stage made it) so later stages and humans can audit it.

```
PDF page
  |
  |  1. extract/textlayer.py      characters (with visibility: hidden text is set aside), words, lines (re-joined
  |                               around scripts, never across column gutters), rulings, images, text-layer quality
  |     ocr/rapid.py              (only if the page has no usable text) RapidOCR -> same evidence shapes; a page read sideways is turned and read again
  v
  |  2. tables/ruled.py           tables with visible rulings (PyMuPDF finder; one-row boxes too, kept only when
  |                              pipeline._adopt_ruled_headers finds their column headings just above the box)
  |     tables/aligned.py         unruled tables from whitespace channels; prose is rejected
  v
  |  3. segment/blocks.py         lines -> paragraph blocks (gap, overlap, size, typeface rules)
  |     classify/blocks.py        heuristic kinds: heading, header/footer, page/line numbers, list, caption
  v
  |  4. layout/docling_layout.py  RT-DETR layout model on the rendered page (CPU, ~3 s)
  |     layout/fuse.py            model regions override kinds, split straddling blocks, add figures,
  |                               build tables inside table boxes, veto false tables
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
  |                              _read_regions_with_model); everything marked as inferred (D015)
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

## Where the benchmark harness lives

`truedoc/bench/olmocr.py` converts the benchmark PDFs in parallel and calls the official scorer through `bench/score_olmocr.py`. `bench/inspect_failures.py` summarises failed tests; `bench/math_check.py` scores formulas on a few pages; `bench/quick_check.py` is the regression guard on 13 fixed pages.

## Adding a new stage

1. Give it a single entry point taking a `Page` (and the PyMuPDF page if it needs rendering).
2. Record `provenance` and `confidence` on anything it changes.
3. Add a synthetic unit test under `tests/` (see `test_pipeline_synthetic.py` for building PDFs in a test).
4. Run `bench/quick_check.py`, then the affected benchmark section, then record the numbers in `docs/BENCHMARKS.md` and the story in `docs/PROGRESS_LOG.md`.
