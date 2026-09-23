# How TrueDoc converts a page

Read this to understand the code layout before changing anything. Each stage is a module; each keeps what it learned on the `Page`/`Block` objects in `truedoc/model.py`, and every structural decision records its `provenance` (which stage made it) so later stages and humans can audit it.

```
PDF page
  |
  |  1. extract/textlayer.py      characters (with visibility: hidden text is set aside), words, lines (re-joined
  |                               around scripts, never across column gutters), rulings, images, text-layer quality
  |                               - a character whose code cannot mean what it draws is read by its drawing: a
  |                                 private-use one, and a Latin letter in a dingbat font (Wingdings' "n" is a square)
  |                               - a mark alone on a line, drawn or named by the text layer, joins the words beside it
  |                               - hidden text (D011): a character is covered when a later opaque fill covers its
  |                                 *ink*, not its taller font box; the render may overturn that only on the evidence
  |                                 of characters no visible character is printed over; paint order is matched by
  |                                 position and character, so an earlier wording under a row's shading stays out
  |                                 ; text inside a form drawn at zero opacity is hidden whatever it says of itself
  |                                 (pdfium_objects carries each form's alpha down to its text objects)
  |                               - an underscore TeX drew as a rule (0.3 em long, on the baseline, hard against the
  |                                 word after) is a character of the word it sits in: "Japanese_spaniel"
  |                                 (_read_drawn_underscores), and leaves the page's drawings
  |                               - an arrow set in Wingdings is named from its code, as its tick and cross are
  |                                 (_WINGDINGS_ARROWS, each code drawn from the font and looked at; not Wingdings 2/3)
  |                               - Webdings' triangles likewise (_WEBDINGS_TRIANGLES): its right-pointing one, a list
  |                                 bullet the glyph reader takes for an arrow head, is written as the triangular bullet
  |                                 "‣" that every list rule knows; a mark read from a symbol font (bullet, box, tick,
  |                                 cross) shares no word with its neighbour however close its box - an arrow may
  |                               - a gap beside a numeral set at twice its words' size or more is judged in the words'
  |                                 type, not the numeral's: a Key Facts Sheet's 48-point step number, 3.3 points from
  |                                 "STEP" and from its heading, is a word of its own, and a capital after it starts one
  |                                 however close the boxes (_big_numeral, _numeral_then_capital; in _chars_to_words and
  |                                 in _fuse_touching_words, which would otherwise re-join them); a letter or digit in a
  |                                 dingbat font shares no word with the text beside it
  |     ocr/rapid.py              (only if the page has no usable text) RapidOCR -> same evidence shapes; a page read sideways is turned and read again
  v
  |  2. tables/ruled.py           tables with visible rulings, found from the page's drawn rules by tables/ruled_pdfium.py;
  |                               a cell covers every column whose centre its rectangle holds, a column running from
  |                               its own left edge to the next one's (column_spans) - so staggered rules make no
  |                               empty cells;
  |                               a cell's lines are joined by the one joiner every table builder uses
  |                               (aligned._join_lines: a broken word closes up, a compound keeps its hyphen);
  |                               one-row boxes too, kept only when pipeline._adopt_ruled_headers finds their column
  |                               headings just above the box - never a sentence, which crosses from one column to the
  |                               next on a word space (tables/cells.runs_across_columns)
  |     tables/aligned.py         unruled tables from whitespace channels and voted column cuts; prose is rejected.
  |                               A second look (_refine_segments) adds a cut judged only by the rows with words on both
  |                               sides of it, refused when every segment it would divide crosses on a word space; it
  |                               sharpens a table the first look found and never makes one of its own
  |                               (find_aligned_tables). A cut is placed just before the words that close its range,
  |                               else mid-range, else at its left end; when a word stands on all three, in the widest
  |                               stretch no word of any row stands in - unless that divides a line on its own word
  |                               space (the gap must be over three times the line's ordinary space, or no cut is made).
  |                               A band laid across a table (_band_segments, _is_band) neither
  |                               votes on a cut nor is divided, and spans the grid. _merge_wrapped_rows folds a wrapped
  |                               cell into its row, and _label_carries_on carries a label on to its second line when
  |                               the short value beside it is left empty (a capitalised second line only when the
  |                               row's other cells carry on too; never one holding a digit unless it starts in lower
  |                               case), and an entry wrapped with its value on its last line becomes one row when the
  |                               row after it starts an entry of its own (counted as its lines when the table is judged)
  |                               - a line with no label, flush with the lines of the cell above and one leading
  |                                 below the last of them, is that cell's next line whatever it says
  |                                 (_next_line_of_the_cell_above; a band is centred, and stays a row); under a
  |                                 cell of ONE line the leading is the table's own wrap pitch, learnt on a first
  |                                 reading (_merge_rows_once), and the line's first word must not have fitted
  |                                 above. Either fold is recorded as the lines the page sets, so the judgement
  |                                 "is this a table" never moves with it
  |                               - a line with no label under the line that opens an entry, one of whose cells
  |                                 carries running text on while the others hold a word or two ("No" under "Yes"),
  |                                 is that entry's next line: no cell of a new row opens mid-sentence
  |                               - a heading line carried on under an empty cell joins the heading (_heading_wraps_on),
  |                                 whether it carries on in lower case or with a bracket opened on running words
  |                               - a row under the first that has a label and the shape of a labelled row further
  |                                 down (same cells filled, same cells opening with a number) is body, not
  |                                 heading, however the heading's end was guessed (_header_row_count)
  |                               - a row is re-read in order (_headings_in_order) only when it is short headings,
  |                                 four words a segment at most: never the lines of a table nested in a column
  v
  |  3. segment/blocks.py         lines -> paragraph blocks (gap, overlap, size, typeface rules)
  |     classify/blocks.py        heuristic kinds: heading, header/footer, page/line numbers, list, caption
  |                               - a line at a page's head is a running head only if a page beside it prints it there
  |                               - a line at its foot is a running foot unless it is a sentence (eight words, hardly
  |                               a digit) that no page beside prints there
  v
  |  4. layout/docling_layout.py  RT-DETR layout model on the rendered page (CPU, ~3 s)
  |     layout/fuse.py            model regions override kinds, split straddling blocks, add figures,
  |                               build tables inside table boxes (a header row the box missed is taken from
  |                               just above it, never a sentence crossing the columns on word spaces), veto false tables
  |                               - a page header, or a long page footer, that no page beside it prints at the same
  |                               height is the page's own (_repeated_beside, two pages each way; the same line, its
  |                               words in the same order, not the same bag of words), and so is a line the clean-up
  |                               files as furniture for repeating a running head's words, asked at the height the
  |                               line stands (pipeline._margin_cleanup)
  |     tables/rule_grid.py       a confident table box whose text builds no table - its columns hold only drawn marks -
  |                               is read from its own rules: rows between them, columns where their pieces meet at the
  |                               same x on at least three rules, each word in the cell its centre falls in
  |                               - pieces a word space apart meet, and a filled band across the table edges a row
  |     tables/fill_grid.py       after the layout model: a table the text built across the cells its page draws
  |                               (tiled fills and the rules among them) is read again from the drawing, spans and
  |                               header included - only where words of one text cell lie on both sides of a drawn
  |                               edge (redraw_tables)
  |     tables/boxed_cells.py     then: rows of a text-built table that one box the page strokes holds as one run of text
  |                               - a cover's name on two lines in a card - are one row; never a list, a sentence and the
  |                               next, stacked values or a key's entries, and never where the box holds every row
  |                               (join_boxed_rows)
  |     classify/page_numbers.py  after the layout model and the margin clean-up: a margin line taken for the page's
  |                               number is text again when the pages beside it number themselves at a distance it does
  |                               not fit and none prints the same line at the same place (release_pointers)
  v
  |  5. math/extract.py           display formulas per equation line, inline maths runs
  |                               - never a mark the page draws, which marks.py sets into a line as a word of its own
  |     math/reconstruct.py       glyphs + rules -> LaTeX (fractions, scripts, radicals, matrices, accents)
  v
  |  6. segment/order.py          reading order: column split when a full-height gap exists, else peel
  |                               the topmost spanning block, else horizontal cut; then each side label (a few
  |                               words in a narrow column, level with the first line beside it) is read
  |                               immediately before the block it heads
  |     pipeline._list_levels     then, in reading order: a list item set further in than the item above opens a
  |                               sub-list, read from where the markers start (D028's rule for a cell, in the body);
  |                               a list carrying on in the next column starts again there
  v
  |  6b. marks.py                 ticks, crosses and bullets drawn as shapes or tiny images are
  |                              rendered, matched to templates and written into the cell or line
  |                              - a shafted arrow, drawn or cut out of a square, before a chevron (_shafted_arrow):
  |                                its head meeting on the shaft's line, never from what erasing a ring leaves
  |                              - a glyph's mark (glyph=True): alone in its box, a dot the same upside down
  |     pipeline._icons_are_not_pictures  after the figures are gathered: a picture a mark's size (marks.mark_sized)
  |                               in a table or at the head of a line is an icon, not a figure (D013) - never a
  |                               placeholder; each recorded with the page's decisions
  |     tables/list_columns.py    then, the marks in place: lists set side by side with no boxes, cut at their lines by a
  |                               text-built table, are read column by column and rebuilt as one row of list cells under
  |                               their headings (rebuild_side_by_side_lists)
  |     tables/cell_lists.py      a list inside a table cell - entries opened by a tick, cross or bullet at a hanging
  |                               indent, sub-lists, a note - is kept as a list and written as <ul><li> (list_cells; D028)
  |     tables/cell_tables.py     a table inside a table cell - three lines or more, every one broken at a gap no word
  |                               space makes, the pieces after it starting at one place - is built from the cell's own
  |                               lines, kept only if it says what the cell said, and written as a <table> inside the
  |                               <td>; its first row is a heading only if it names and the rows beneath count
  |                               (table_cells; D038)
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
  |                               - furniture no page beside prints is the document's imprint: kept under
  |                               `truedoc.imprint` with its page, never in the body (D029); furniture with no page
  |                               beside to ask (a one-page file) is kept there too, `checked: false`, never dropped,
  |                               and a running head or foot is kept once under `truedoc.running` with its pages (D040)
  |                               - every line at a page's edge left out of the body is a recorded decision - what,
  |                               why, whether it could be checked - in `ConvertResult.decisions` (D040), which
  |                               bench/tools/word_check.py uses to tell a deliberate removal from a loss
  |     build.py                  what made the conversion - package, commit, options, readers and where they
  |                               ran, seconds - into `truedoc.build`, `ConvertResult.build` and `--status`
  |                               - a drawn mark no cell, line or picture takes is kept under
  |                               `truedoc.marks_not_placed` with its page and box, and published nowhere
  |                               - a stage asked for that could not run is named under `truedoc.warnings`
  |                               ("the layout model was asked for and could not run..."), so no one reads a
  |                               conversion made without it as the converter's own answer
  |                               - how the conversion ended travels apart from the body (D037): every warning is
  |                               also a typed issue (`Document.add_issue`: code, severity, pages), the worst of
  |                               them decides `truedoc.completion` (complete / degraded / incomplete), the front
  |                               matter is written even over an empty body, and `pipeline.convert_with_status`
  |                               hands the same to a caller who asked for no front matter. A page selection the
  |                               document cannot meet is an error (`PageSelectionError`), not a state; a model's
  |                               reply cut off at its length limit is kept and its page named `reply-cut-off`
  |                               - a transcription cannot hold more print than its region (`vision/capacity.py`):
  |                               a page's or a picture's reading that claims more characters than fit at four-point
  |                               type - a loop, a table invented at length - is set aside and named
  |                               `reading-implausible`. Measured before it was written: real transcriptions reach
  |                               0.32 of a picture's capacity and 0.66 of a page's; the two that prompted it, 2.2
  v
OKF markdown
```

**Beside the pipeline: two issues of one document, page by page** (`truedoc/versions.py`, D040). `page_prints` reads
what each page prints with PDFium - not TrueDoc's conversion, so a match stands however TrueDoc comes to read the page -
splitting its running lines (a line at the head or foot that a page beside prints too, numbers aside: D029's
definition) from its body. `match` pairs each page of a new issue with the page of the old one it reprints, keeping
both orders: `same`, `restamped` (the body word for word; the running lines differ in numbers and month names only),
`changed` (passages that differ listed, those with a figure apart), `new`, `dropped`. Only a same or restamped page
keeps what a person confirmed about it; `bench/probes/version_census.py` measures what carries over in the library.

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
