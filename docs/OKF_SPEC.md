# OKF output format

TrueDoc writes **Open Knowledge Format (OKF)** documents: plain markdown files with a YAML front matter block, as defined at https://github.com/GoogleCloudPlatform/open-knowledge-format (specification version 0.2, read on 3 September 2026). OKF is vendor-neutral: it is not tied to any agent, framework, model provider or serving system. The project owner confirmed this is the OKF meant by the brief (decision D005, confirmed 3 September).

## What OKF asks for

From the specification's field list:

| Field | OKF status | TrueDoc fills it with |
| --- | --- | --- |
| `type` | required | `Document` by default; `truedoc convert --type Reference` overrides it |
| `title` | recommended | the PDF's title metadata when present |
| `description` | recommended | the first sentence of the first ordinary paragraph (a preview line) |
| `resource` | recommended | the source PDF as a URI (`file:///...` for a local file, or the URL it was fetched from) |
| `tags` | recommended | omitted unless supplied (nothing is invented) |
| `generated` | production record | `{by: truedoc/<version>, at: <UTC time>}` (the actor form `<producer>/<version>` is OKF's convention) |
| `status` | lifecycle | `draft`: a conversion nobody has reviewed. A person who checks the file should set `stable` and add a `verified` entry |
| `sources` | provenance | one entry for the PDF: `resource`, `title` (file name) and `last_modified` (the file's modification time) |
| `verified`, `stale_after`, `usage_window` | optional | left for humans and downstream tools |

OKF allows any extra keys, so everything specific to TrueDoc sits under one key, `truedoc`, and never collides with the standard fields:

| `truedoc.` field | Meaning |
| --- | --- |
| `version` | the TrueDoc version that wrote the file |
| `sha256`, `pages` | checksum of the PDF bytes and the number of pages converted |
| `completion` | how the conversion ended (D037): `complete` - everything asked for ran and every page was read; `degraded` - every page has content, but a stage that was asked for did not run or a lesser reader stood in; `incomplete` - content is known to be missing (a page nothing could read, a model's reply cut off at its length limit). The worst issue decides |
| `confidence` | 0..1, **a label for where the text came from, not a measure of how right it is**: the mean over pages of 0.9 for a page with a text layer, 0.6 for one read by OCR, 0.5 for one read by a vision model, 0 for one nothing could read. A page read perfectly and a page that lost a line score the same. (Until 21 September 2026 this row called it "an estimate of meaning fidelity", which it never was; D040 builds a real one from checks and confirmed outcomes.) |
| `language` | best-effort, when known |
| `pages_with_ocr` | page numbers whose text came from image OCR (no usable text layer) |
| `turned_pages` | pages that lay on their side (a landscape scan of a portrait page, a table printed sideways) and were turned upright before reading: `page` and `turn` in degrees clockwise; omitted when there are none |
| `hidden_text` | text a reader cannot see, kept out of the body (page, reason, text); omitted when there is none |
| `imprint` | a line at a page's edge that no page beside prints there - an issuer and licence, a copyright line, a preparation date - kept out of the body and recorded here (D029): `page`, `text`, `provenance`; `checked: false` when there was no page beside to compare with (a one-page document, or neighbours that are scanned), so it is kept rather than lost (D040); omitted when there is none |
| `running` | a running head or foot - the same line on the pages beside - kept out of the body and recorded **once** for the document with the `pages` it ran on (D040), so nothing a page prints is thrown away without trace; omitted when there is none |
| `warnings` | human-readable notes about anything uncertain |
| `build` | what made the conversion, so one made before a change can be told from one made after: `code` (`package` version, `python`, `commit` - from the installation's own record when installed from a git address, else from git in the folder the package was imported from, with `modified: true` when the package's files differ from it; `null` when neither is there), `options` (every conversion option in force), `readers` (`pdf`: the PDFium build; `layout`: the model, its revision and the library versions that ran it, and whether it `ran`; `ocr`: the engine, its version, the recognition model and whether it `ran`; `vision` and `deep`: the model and where it ran - an address without its credentials, "the Anthropic API", or "readings replayed from disk"), `seconds` (reading the document, models loaded included). The same record is in `convert_with_status(...).build` and in the `--status` file |
| `issues` | the same notes for software, one entry each: `code` (stable: `unreadable-pages`, `reply-cut-off`, `stage-unavailable`, `reader-fallback`, `reading-implausible`, `hidden-text`, `pages-turned`, `low-support`, `witness-failed`, `blank-pages` - pages with a few words at most and nothing else to read, a note and not a loss (D042) -, `edge-unchecked` - a line at a page's edge left out of the body with no page beside to show it runs, kept under `imprint` - or `warning` for a sentence nobody classified), `severity` (`note` / `degraded` / `incomplete`), `pages`, `message`; omitted when there are none |

## File shape

```
---
type: Document
title: Quarterly Report                 # from the PDF metadata, when present
description: Revenue grew 12% in the quarter on strong demand in Asia.
resource: file:///C:/reports/quarterly.pdf
generated:
  by: truedoc/0.0.1
  at: '2026-09-03T11:30:00+00:00'
status: draft
sources:
- resource: file:///C:/reports/quarterly.pdf
  title: quarterly.pdf
  last_modified: '2026-08-30T09:12:44+00:00'
truedoc:
  version: 0.0.1
  sha256: <hash of the PDF bytes>
  pages: 12
  completion: complete            # or degraded / incomplete, with the reasons under `issues`
  confidence: 0.94
  pages_with_ocr: []
  hidden_text:                          # only when there is some
  - {page: 3, reason: same-colour, text: white-on-white keywords ...}
  warnings: []
---

# Quarterly Report

Body text in reading order ...
```

The version marker `okf_version: "0.2"` belongs, per the specification, in the `index.md` at the root of a *bundle* (a folder of OKF files), not in each document. Single-file conversions therefore carry no version marker; a batch mode that writes a bundle with `index.md` and `log.md` is on the roadmap (M8).

## Body rules

The specification leaves the body as ordinary markdown. TrueDoc's rules for it:

- **Headings** use `#`..`######`, with levels reflecting the document's real hierarchy (not font size alone).
- **Paragraphs** are joined across line breaks and across page breaks. Hyphenation at line ends is repaired ("conver-" + "sion" becomes "conversion") only when the joined word is a real word or the hyphen was a soft hyphen.
- **Lists** use `-` for bullets and `1.` for numbered lists, nested by indentation.
- **Tables** are GitHub-flavoured markdown tables when the table is regular. Column headings printed unruled just above a ruled box of rows (a form-style table) are the header row. Tables with merged cells or stacked headings (a group heading over its sub-headings, a heading with a units line under it) are emitted as HTML `<table>` with `<th>` header rows and `rowspan`/`colspan`, so no information is lost. A cell holds what its box holds (D028): a list inside a cell is written as a list, and a table inside a cell as a table inside the `<td>` (D038), with its own `<th>` row when it has a heading of its own; either makes the table an HTML one.
- **Figures** are emitted as `![caption](figure)` placeholders with the caption text kept; charts get a `> Figure:` block with any readable text inside them.
- **Formulas** use LaTeX: inline `\(...\)`, display `\[...\]`, one display block per equation line. Equation numbers follow the block as plain text, e.g. `\[E = mc^2\] (3)`. Dollar signs do not delimit anything (D024): a literal one, a price among them, is written `\$` so that no viewer can read the stretch between two prices as a formula. The LaTeX is rebuilt from the PDF's own glyphs and positions and aims to render the same symbols in the same arrangement; it is not the author's source.
- **Footnotes** use `[^n]` markers and `[^n]: text` definitions (decision D017). A small raised digit or symbol (*, †, ‡, §) glued to a word in running text becomes `[^n]`; a line at the foot of the page, or in small type, that starts with the same number becomes the note `[^n]: text`, kept where the page puts it. A marker whose note is not on its own page is looked for on later pages (a "Notes" section, or a run of numbered notes), so endnotes link the same way. Keys are unique across the document: when page 12 reuses a number already used on an earlier page, its marker and note become `[^1-p12]` (markdown viewers number footnotes by order of reference, so the key is only an identifier).
- **Page headers, footers and page numbers** are removed from the body.
- **Page breaks** are not marked in the body by default (`--page-markers` adds `<!-- page: N -->` comments).
- **Reading order** follows how a human would read: column by column, with captions next to their figures and footnotes after their section.
- **Nothing is invented.** If a page cannot be read (no text layer and no confident OCR), it contributes nothing to the body and a warning names the page in the front matter; `truedoc.pages_with_ocr` lists pages whose text came from OCR rather than the PDF's own text layer.
- **Only what a reader sees is in the body.** Text a reader cannot see (white-on-white, under a shape, in a zero-size font, drawn invisibly) is left out of the body and listed under `truedoc.hidden_text` with the page and the reason, so nothing is lost silently. The one exception is a scanned page whose invisible text layer is its only text: that layer is the reading of the page (decision D011).
- **Marks that carry meaning** (a tick or cross drawn as a shape or a tiny picture in a table cell, a bullet drawn in front of a line, a mark set in a symbol font such as Wingdings) become the character a reader would say they mean: ✓, ✗, ●, ○, ■, □. A mark inside a table cell joins that cell; a mark at the head of a line starts that line. A mark in a cell that cannot be read is kept as `[icon]` rather than dropped (decision D013).
- **Links** inside a bundle should be absolute bundle-relative paths (`/topic/file.md`), per the specification; single-file conversions contain no links.
- **Ellipsis.** The ellipsis character (U+2026) is written as three dots ("..."): that is how readers type it when they search or quote a passage, and the meaning is the same. Drop caps (a paragraph's first letter set two to four lines tall) are joined back onto their word, so "L" beside "e gouvernement" reads "Le gouvernement".

## Provenance marks (decision D015, agreed by the owner on 3 September 2026; whole pages implemented, icons and charts pending)

TrueDoc will soon be able to hand a model what the mechanical reading could not process: a scanned page with no text layer, an icon, a chart, handwriting, a font with no character mapping, a formula it cannot assemble. Whatever a model produces is *inferred*, not read from the document's own characters, and a person opening the file must be able to see that at a glance without the file becoming unreadable. The proposal:

Status on 3 September (evening): all five items are built and tested against stand-in models. Item 1 covers icons in table cells (an icon-only cell becomes `Covered[^inferred]`) and figures (the description becomes the image's alt text: `![A bar chart of premiums by year ...](figure)[^inferred]`); item 2 whole pages; item 3 the `truedoc.inferred` list with `{page, kind (page | icon | figure), text, model, bbox}`; item 4 is the rule that shape-recognised marks carry no tag; item 5 is the `--vision-endpoint` switch, with `--vision-pages-only` to leave icons and figures alone. A page asks the model about at most twelve regions. The first real run needs a served model or the `ANTHROPIC_API_KEY` set by the owner.

1. **Inline: a footnote tag.** The inferred text reads naturally and carries one small tag: `covered under contents[^inferred]`. A single definition per document sits at the end of the body:

   `[^inferred]: Marked text was read from the page image or inferred by a model (olmOCR 2, Claude), not taken from the document's own text. See truedoc.inferred in the front matter.`

   Markdown viewers render it as a superscript link; plain-text readers see the tag; programs find every instance by searching for it.
2. **Whole pages: one note, not a tag per line.** A page the vision model read gets a short note at the top of its text: `> This page was read from its image by a model; the PDF holds no text for it.` and its page number goes into `truedoc.pages_with_model`.
3. **Front matter: the audit list.** `truedoc.inferred` lists every inferred item: `{page, kind (icon | chart | page | formula | handwriting), text, model}`. A reviewer can check or strip them; `status: draft` already says the file is unreviewed.
4. **What is never marked.** Characters taken from the PDF's text layer, and marks recognised by shape rules (a drawn tick becomes ✓ without a tag: it is a reading of ink, like OCR, and listed under `truedoc.marks` instead if the owner wants that visible too).
5. **Off by default.** No model is called unless the conversion asks for it; without it, the unreadable item is left out with a warning, as today.

Resolved (owner, 3 September, evening): one tag, `[^inferred]`, for every model source. The model's name lives in the tag's definition and in each `truedoc.inferred` entry, not in the body, so the text stays readable and a program still finds every inferred item by one search.

## The location map (a file beside the text)

Asked for (`--map <file>` on the command line, `ConvertOptions(location_map=True)` and `ConvertResult.location_map`
from Python), a conversion also writes one JSON file saying where every passage of its text came from; the markdown is
character for character the same with it or without it. Offsets count characters (Unicode code points) of the
markdown as written, lines ending in `\n`, front matter included; `markdown.sha256` is the checksum of that text in
UTF-8, so a map is never read against another version of it.

| field | holds |
| --- | --- |
| `markdown` | `characters`, `body_start` (where the body begins after the front matter), `sha256`, `newline`, and `all_found_in_place` - true when every range was placed exactly (the parts joined and the renderer's last cleanups replayed gave the body character for character); false would mean parts were found by searching, and any not found have `range: null` |
| `document` | the PDF's `sha256` and the number of pages converted |
| `build` | the same record as `truedoc.build` |
| `pages` | per page: `page` (its number in the file), `size` (points), `read` (`text layer`, `ocr` or `model`), `state` (`read`, `empty` - nothing of it in the body - or `unreadable`), `range` (the stretch of text it wrote), `printed` (the numbers it prints, each with where it `applies` - the `page`, or the `left half` / `right half` of a spread - and the box of the line it stands in) |
| `blocks` | per paragraph, heading, list item, table, figure or note as written: `id`, `kind`, `range`, `boxes` (the page and box of every piece of the page that went into it - two for a paragraph joined over a page or column break, which also has `pieces`, each with its own range) |
| `cells` | per table cell: `id`, `table` (its block's id), `row`, `col`, `rowspan`, `colspan`, `header`, `page`, `box`, `range` (`null` for a cell with nothing written in it, marked `empty`) |
| `emphasis` | `bold` and `italic`, each a list of `[start, end]` ranges, always written, empty when there are none |

Boxes are in the page's points with the origin at the top left, clipped to the page.

## Reading the file back

Any YAML parser reads the front matter; any markdown renderer shows the body. To know whether the conversion can be relied on as a whole, read `truedoc.completion` first, and `truedoc.issues` for the pages and reasons; a document nothing could be read from still has a front matter block, with an empty body under it. A caller that asks for no front matter gets the same from `truedoc.pipeline.convert_with_status` or the command line's `--status <file>`, and `--strict` turns anything short of `complete` into exit code 3. To find what TrueDoc was unsure about, look at `truedoc.warnings`, `truedoc.pages_with_ocr`, `truedoc.ocr_regions` (pictures on digital pages read with OCR, with `--ocr-pictures`) and `truedoc.hidden_text`. To mark a file as reviewed, change `status` to `stable` and add:

```
verified:
- by: human:your-name
  at: '2026-09-04T10:00:00+00:00'
```
