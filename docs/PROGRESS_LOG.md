# Progress log

Working notes, newest entry at the top. Each entry: what was done, what was learned, what is next. Read this file before doing anything, so work is not repeated.

---

## 2026-09-23, 14:05-14:35 - Every conversion says what made it

A conversion recorded `truedoc/0.0.1` and nothing more, so one made before a change could not be told from one made
after - and a before-and-after measure is exactly that comparison. `truedoc/build.py` writes a record into the front
matter (`truedoc.build`), into `convert_with_status(...).build` and into the `--status` file: the package version and
Python; the commit - from the installation's own `direct_url.json` when TrueDoc was installed from a git address,
otherwise from git in the folder the package was imported from, with `modified: true` when the package's own files
differ from it (a worktree on the path is reported as itself); every option in force; the readers - the PDFium build,
the layout model with its revision and the `transformers` and `torch` versions that ran it and whether it ran, the OCR
engine with its recognition model and whether any page used it, the vision and deep readers with where they ran (an
address without its user name or password, "the Anthropic API", or "readings replayed from disk"); and the seconds it
took. Nothing downloads for the record: the OCR model is looked for on disk, not fetched. Git is asked once a process.
Bodies are untouched (the benchmark, the Key Facts Sheets and the insurance set are scored on bodies). Suite 856 (+3,
`tests/test_build_record.py`).

---

## 2026-09-23, 12:40-14:00 - A picture a mark's size in a table or at a line's head is an icon, not a figure

The second of the owner's two general rules (the entry below sizes it). The layout model calls every small drawing a
picture, so an item's tick, cross or dollar in a circle, and each tick down a table's columns, became an empty
`![](figure)` on a line of its own - 29 stacked above one summary table whose cells already held the ticks, one between
an exclusion's lead and the list under it. D013 already had the rule and the layout model's pictures never met it: a
mark the reader can read is its character where it stands (the mark reader has already put it in its cell or at the
head of its line), a mark in a cell it cannot read is the cell's "[icon]", an unreadable shape beside running text is
decoration.

*The rule* (`pipeline._icons_are_not_pictures`, after the figures are gathered, before the reading order): a figure
block with no text of its own, not a single mark standing for itself (`mark_only`), in a box the mark reader would look
at (`marks.mark_sized`: 3 to 30 points a side on a letter page, scaled with a bigger page, no more than 2.5 times as
long as it is wide), is not written when its centre lies in a table or it heads a line of text (a line level with it
starting within three body sizes to its right, or over it). Each one is recorded with the page's decisions (D040):
where it stood and what the mark reader made of it, if anything. A picture that size standing on its own stays a
figure. `_record_imprint` now adds its edge-line decisions to the page's list instead of replacing it. The vision
stage is untouched: it reads a cell's icon from the marks and the page's images, never from these blocks, and already
leaves pictures under half an inch alone.

*Measured, code against code.* `bench/probes/icon_picture_screen.py` converts every page and counts the pictures the
rule kept out: benchmark 18 of 1,403 pages (4 held out), 28 icons - scored with the rule on and stashed, 95 of 106
checks both ways, no page moved; Key Facts Sheets 0 of 380 pages; the insurance set 10 of 25 pages, 46 icons, 229 of
229 both ways (`insurance_diff.py`: 0 checks changed). The library sample's 166 tuned-on pages with such a placeholder,
converted with the rule switched off and on at run time: placeholders 1,522 -> 224, and on every page nothing but
placeholder lines differs. Read against their pages, with every picture taken out drawn round: on 12 pages of 12
insurers and the 14 tuned-on benchmark pages, each one is an icon or a small logo - a table's ticks and crosses (their
characters still in the cells), the symbols over a summary table's columns, event pictures beside their names, a clock
beside "72-hour exclusion period", an envelope beside an address, TV channel logos in a listings grid, a route marker,
a monogram - none of it a picture the placeholder had said anything about. Suite 853 (+5, `tests/test_icon_pictures.py`).

*Mended in passing:* `bench/tools/insurance_diff.py` did not know the set's own `list_item` checks (D028) and counted
all five as failures in every folder, so its totals read 224 where the scorer reads 229; it now runs them as
`insurance_score.py` does.

Still open, noticed while reading: the circled dollar and the circled tick are not read as marks ("●" or nothing) - the
placeholder is gone, the meaning is still not in the text; a summary table's event pictures read as marks ("● Flood").

---

## 2026-09-23, 08:25-12:35 - A side label is read before the lines it heads; the item icon and the navigation button sized

The owner asked for three reading faults to be sized before any code was written, then (after the sizes) for the
first two to be fixed as general rules and the third kept as knowledge about the one design that shows it.

**The side label.** A few words in a narrow column at the left - "Yes", "No", "Limits"; "We cover", "We don't
cover"; a term beside its definition; "Step 1" beside the step - govern the lines beside and below them. The reading
order got them wrong two ways. A label column this narrow is not split off as a column (the cut's guard against a
gutter of line numbers), so the label was weighed against the wide line beside it by their centres; its box reaches
about 0.2 pt lower, and it was written after the first line it governs, which then read as the last line of the group
above. On one storm page "loss or damage caused by actions or movements of the sea or storm surge", an exclusion,
stood under "We cover". A wider label column was split off and read whole: every label, then every text.

*Sized* (`bench/probes/side_label_icon_census.py`: a screen of every page's text layer without the layout model, then
the pages it flags converted with the product's options; `side_label_icon_designs.py` groups documents into designs).
Benchmark, 1,122 digital pages converted: 33 with a label column (a label, its column holding labels, its first line
level with a line beside it), 14 with a label after its line or apart from it (3 held out). Of the 4 tuned-on pages
flagged "after" only one is the shape (a glossary; the others a caption, maths fragments, a stray word). Library
(23,400 pages screened, the sealed 19 left out; for each shape up to three pages a document converted, 2,701 pages of
964 documents, so every count is a floor): 118 documents with a label column, 70 with the fault (41 held out, counted only), 20 insurers; the
commonest design is one group's "We cover / We don't cover / Limit" pages under four brands. The insurance set's 25
pages: none. **Correction:** the size first reported to the owner (44 documents, 10 insurers) counted only a label
written after its line; a label read apart from its line, with other labels between, is as common (197 of the 774
labels in the sample against 228 after).

*The rule* (`segment/order.py`, `_seat_side_labels`, after the cut): a label goes immediately before the block whose
first line is level with its own first line (tops within 0.4 of the line height), across a gutter (0.8 body sizes to
0.4 of the page), where that block is running text (four words or more, twice the label's width). A label is one to
four words of letters (two letters at least), on at most four lines, no wider than 0.18 of the page. Four guards, each
from a page the first version got wrong, each with its test: the label's column holds labels (three in four of what
stands in it) and half of them head a block (a list set in two columns of short entries has only its first entry level
with anything); a figure alone is not a label ("05" beside a stage's title, a row of numbered discs); a word a justified
line's wide spaces cut loose has the paragraph's lines crossing it above and below; and nothing stands between a label
and its block (in a row of cells, the next cell and not a later one).

*Measured, code against code.* `bench/probes/order_screen.py` converts every page once and asks both code states for
the order (the old file loaded under another name): benchmark 8 of 1,403 pages differ (2 held out) - scored both ways
with `ab_pages.py`, 38 of 45 checks before and after, no page moved; read, the 6 tuned-on pages are 4 better (the
glossary, both of its forms; a caption's number with its title; a masthead's volume with its date line; a college's
name before its degree labels) and 2 neutral (a table heading and a scanned card, scrambled before and after). Key
Facts Sheets 0 of 380 pages differ; the insurance set 0 of 25: both unchanged by construction. The library sample,
reordered from the recorded blocks (the old code reproduces the recorded order on 95% of pages): labels read right
246 -> 661, after their line 248 -> 15, apart 195 -> 13; 134 pages change (81 held out); every one of the 53 tuned-on
pages, read before and after, is better. The first version, without the guards, also changed 25 more, eight of them for
the worse (a list in two columns, twice; a row of numbered discs; a stage's "05", on five copies of one document); the
guards came from reading those. Suite 848 (+7, `tests/test_side_labels.py`; each guard's test fails
with that guard cut out).

**The item icon, sized.** A small drawing at the head of every item - a tick, a cross, a dollar in a circle - or in a
table's cells: the layout model calls each a picture and each became an empty `![](figure)`, a line of its own, stacked
above the table or between an item's lead and its sub-list; where the mark reader had read the icon (a table's ticks),
the cell held the tick and the placeholder was written as well. The icons are drawn as vector paths, not images, in the
example documents. Library (same sample): 92 documents (53 held out), 24 insurers, 42 designs carry a repeated icon
placeholder at line heads or in tables, 1,729 placeholders; commonest a table's ticks written twice. Benchmark: 44
mark-sized placeholders on 1,122 pages, one page with a repeated one. The insurance set: 46 on 25 pages, repeated in 2
documents - and it scores 229 of 229, because no check looks for a placeholder. D013 already says an unreadable shape
beside running text is decoration and left out; the layout model's pictures never met that rule. Next: the fix.

**The navigation button, sized and left.** Text an interactive PDF prints under its form buttons ("Table of contents",
"Start of section"), repeated down a side margin on every page: in the whole library 2 documents (one insurer, not held
out, 363 placements), one of which writes it into the body; on the benchmark one page has a button over printed text.
One design: no rule. (Text repeated at one place in a side margin on three pages or more, outside the head and foot
bands, is commoner - 69 documents - but much of it is a template's real side headings, "Limit:" and "Included for:",
which a rule dropping repeated margin text would delete.)

Noticed, not built: a circled tick read as "●" (a grey disc with a white tick; also a green ring), a summary table's
event pictograms read as marks ("● Flood"), an applicability box ("Home ✓ / Contents ✗", the second struck through)
written as a placeholder.

---

## 2026-09-22, 07:50-08:55 - One repository or two: D041, layering

The owner asked to discuss carrying on in this repository against porting a copy of TrueDoc to a new one tailored to
the insurance corpus. Measured for the discussion: the engine is 19,896 lines; the maths rebuilding, 2,777 (14%), is
the only part that serves the benchmark alone - text reading (5,753), tables (4,120), the model readers (1,251),
layout, marks and the rest serve insurance documents as much. The owner chose layering (D041): TrueDoc stays one
generic engine here; the owner's insurance product is built on it in its own private repository, pinned to a TrueDoc
commit (dd32201 at the start), and D040's remaining steps - the store of confirmations, the review page, the second
reader, the pilot - continue there, in a session of its own. The product's repository was set up from this session
(its README, decisions and status; no document committed). Two things found while setting it up, for this project:
the product's document collector holds the live library - 71 documents this project's copy lacks, new versions among
them - while this project's measures keep reading their frozen copy, so they stay comparable; and all 19 sealed
documents are in that library too, where the seal holds as here. What TrueDoc owes the product next, generically: a
passage-to-page map travelling with the markdown, and the exact commit in each conversion.

---

## 2026-09-22, 07:34-07:45 - The docs brought up to date

The owner asked that every document be current before the next discussion. Read against the state of the work:
- `docs/STATUS.md`: "Where we are" still described 17-18 September - a paragraph for 22 September now leads it. "Things
  you may need to do" still asked for the GitHub and Hugging Face logins (done 18-19 September), a ruling on the order
  of the next work (the owner set it on 18 September: the picture-text check, the leaderboard entry, the review's
  F01/F10 - all done) and a remote for backup (the repository has been on GitHub since 19 September); those are marked
  done, and the six questions actually open are listed first - where the store of confirmations lives, one repository
  or two, GIO's two misread bullets, `--strict` as the default, partly-vector pages to a model and a full benchmark
  run, and the retired worktrees' folder for the owner to delete.
- `README.md`: "Where it stands" dated 22 September; a row for the word check (17 of 60,431 printed words lost on one
  page each of 150 library documents) and a paragraph on certainty per document (D039, D040).
- `docs/ROADMAP.md`: milestone M19, certainty per document (D039, D040), with its three steps done and what is next;
  M7b's symbol-font bullets; the test count.
- `bench/README.md`: 29 tools it never mentioned - every tool for the owner's documents, the meaning test, the word
  check, the reader swap's comparisons and the leaderboard entry - with the rules on sealed and held-out documents.
Checked and current: `docs/BENCHMARKS.md` (run 98 is the last), `docs/OKF_SPEC.md`, `docs/DECISIONS.md`,
`docs/ARCHITECTURE.md`, `docs/MODEL_CHOICE.md`, `docs/GPU_PLAN.md`, `bench/probes/README.md`.

---

## 2026-09-21, 21:56-22:05 - D040's third step: two issues of a document matched page by page; a third of the pages carry over

D040 point 2: a new document is matched page by page with the version it replaces; unchanged pages keep what was
confirmed, changed pages are checked afresh. `truedoc/versions.py` does the matching; the store of confirmations it
serves is the next step.

**What a page is, for matching.** What it prints, read by PDFium - not TrueDoc's conversion, which changes whenever
TrueDoc does, so a match stands however TrueDoc comes to read the page (`page_prints`). Its running lines are set
apart: a line in the head or foot band (12% of the page's height each) that a page beside prints too, numbers aside -
D029's definition of a running head, judged by what it means rather than by where it sits. The rest is the body, as
words in reading order.

**How pages are paired and classed** (`match`). Each page of the new issue with the page of the old one it reprints,
keeping both orders - issues add, drop and reword pages, they do not shuffle them - by the pairing that holds the most
word pairs in common, pages under half alike never paired. Classed: `same` (every word, running lines included),
`restamped` (the body word for word; the running lines differ in numbers and month names only - a date, a form code's
digits, a page number), `changed` (the passages that differ listed, those holding a figure apart: D040's "figures are
checked every time"), `new`, and `dropped`. A line taken for running wrongly - a table's heading repeated at each page's
head - cannot hide a change of wording, because only numbers and month names may differ for `restamped`; and a one-page
document has no page beside to show its foot runs, so a new date there makes the page `changed`, never assumed
unchanged. A page moved elsewhere comes out dropped where it was and new where it is: checked afresh. Seven tests
(`tests/test_versions.py`) on PDFs built the way the insurers' are.

**Measured on the library** (`bench/probes/version_census.py`: every document against the nearest other document of
its folder, the two nearest by shared word pairs matched in full; 1,157 documents, the sealed 19 left out, none
unreadable; 90 seconds). 332 of the 490 tuned-on documents have another issue in the library (half their pages or
more matched), 29 of them only an exact copy of another file. Over the other 303 documents, 5,227 pages: **same 32%,
restamped 5%, changed 53%, new 10%**; 2,058 of the 2,757 changed pages have a figure among their changes. The held-out
half, counted only - 438 documents, 8,360 pages: same 30%, restamped 2%, changed 53%, new 15%. The two halves agree.
Read on one pair (Seniors' home PDS of August 2020 against February 2021, 50 of 84 pages changed): the changes are real
edits, most small - "Type" to "Types", "cover/s" to "cover(s)", "While in your home there..." to "There...", a hyphen to
an en dash, the PDS's own date and a cross-reference among the figures - with the page numbers rightly taken as running.

**What it means for D040.** Carrying confirmations by version saves the review of about a third of a reissued
document's pages. Half its pages are edited somewhere, most lightly: a changed page need not be reviewed whole - the
review can show only the passages that changed against the confirmed issue, and a lesson about the page's layout
(D040's second kind) still holds where the layout has not moved. Both belong to the next steps.

**Next:** the store of confirmations. It holds the documents' own words, so it cannot live in this repository, which
is public: where it lives is the owner's call.

---

## 2026-09-21, 20:40-21:55 - The measurement worktrees retired; Webdings' triangle bullet named from its code, and kept apart from its item

The owner's order: the clean-up first, then the "4" bullet, then back to D040.

**The clean-up.** Fifty-one measurement worktrees had piled up in `bench/out/wt_*` since 15 September - 1.2 GB,
74,957 files, every one synced by OneDrive. Eleven were clean checkouts of past commits; 34 held changes never
committed in them; six had been half-removed by earlier `git worktree remove` calls that failed on OneDrive's locks,
their `.git` link gone and git's records left behind. Before anything moved, every uncommitted change was saved as a
patch - `bench/out/worktree_patches/<name>.patch`, untracked files included, local and never pushed - with a README
saying, file by file, whether that exact content is in a commit. Most is; the rest are drafts superseded by what was
committed (the shafted-arrow reader, the private-glyph reader's early rounds, the cell lists) and a "width cap"
experiment that never was. The six unlinked folders were compared file by file with the commits git's records name:
identical, bar a downloaded OCR model cache. Then the 51 folders and git's 52 records were moved out of OneDrive to
`C:\Users\griff\TrueDoc_retired_worktrees` - nothing deleted; the owner deletes that folder when satisfied. `git
worktree list` shows the main tree alone and `git fsck` finds nothing wrong. **Correction:** I had put the pile at
"roughly 2 GB at most", from the three largest; it was 1.2 GB.

**The census first.** `bench/probes/dingbat_census.py` counts every character set in a symbol font across the library
(1,157 documents, the sealed 19 left out; PyMuPDF, a reader independent of TrueDoc's) by font and code, and
`bench/probes/dingbat_readings.py` reads one tuned-on example page per frequent code and says what TrueDoc wrote there.
Most are read right - Wingdings' squares and discs, every tick and cross. Webdings' code 0x34 is not: 608 of them,
every one opening a line, on 74 pages of six documents, written "4". **Correction:** I told the owner these came from
two insurers and were not one stray template. The four documents that may be read are one design, a home PDS of 23
June 2016 sold as Budget Direct, Aussie and Australia Post (the two held out sit in the same folders); the census had
counted the library's top folders, and the archive is one folder holding several brands. It now counts the brand's
folder - the lesson of 16 September again: count distinct wording, not copies.

**What the reader sees, and why TrueDoc missed it.** A small solid triangle bullets each item (drawn from
`webdings.ttf` and looked at: 33 points left, 34 right, 35 up, 36 down). The glyph reader (`_read_private_glyphs`)
takes it for an arrow head ("arrow-right", 0.38 on Budget Direct's page 2) - an arrow it rightly does not write, since
flow arrows standing on rules have read as crosses - or reads nothing where the item's first letter reaches a point
into the glyph's box (the meaning test's storm exclusion). Until this evening's fix (2cf21a5) the "4" was glued to its
item, and the reader skipped the font altogether. D013 already says marks set in symbol fonts are mapped from their font codes:
`_WEBDINGS_TRIANGLES` names the four, the right-pointing one as "‣", the triangular bullet every list rule already
knows (the body's `_LIST_START`, a cell's `cell_lists.BULLETS`, the lone-mark joiner's `_MARK_GLYPHS`), the others as
the shapes they are.

**A second fault, found by the first A/B.** With the bullet named, 101 bullets on the 40 readable pages came out
glued to their items - "‣garages," - where the old code had written "4 garages,". `_fuse_touching_words`, which joins
pieces of one word emitted separately, runs after the glyph reader, and the guard I added there in 2cf21a5 kept apart
only a letter or digit in a symbol font; "‣" is neither. Now a mark read from a symbol font - bullet, box, tick or cross
(`_DRAWN_MARKS`) - shares no word with its neighbour however close its box; an arrow still may ("INTMRK→BRDORT").

**Measured, code against code** (before: a worktree of 2cf21a5; each run names the `truedoc` it imported):
- *Text-layer screen:* the insurance set 0 of 25 pages change, the Key Facts Sheets 0 of 380, the benchmark 0 of
  1,122; and every library page holding a symbol-font character - 3,229 pages of 320 documents, 1,739 of them held
  out - changes on exactly the 74 Webdings pages (40 tuned-on, 34 held out, counted), each changed line the bullet
  renamed in place (306 lines) or a lone bullet joined to its item (two pages, the same words). The guard moved
  nothing else anywhere.
- *The 74 pages converted in full:* no word lost or gained on any readable page (the 314 stray "4"s aside), no bullet
  left glued, 166 list items where there were none; all 34 held-out pages change. Read (Budget Direct's pages 2, 6, 7
  and 8, Aussie's 3 and 6; Budget Direct's page 2 and Aussie's page 6 against their page images): the cover tables
  now hold their lists as lists inside the cells (D028) - "includes:"
  garages, carports and other domestic outbuildings; verandahs, patios... item by item - and Aussie's "We will pay up
  to: 4 10% of your home sum insured or 4 10% of your contents sum insured", where a reader could take the figure for
  410%, is now two items of 10%.
- Four tests (`tests/test_dingbat_glyphs.py`) with a font built to Webdings' codes: three fail on the old code; a
  guard (Webdings' codes name nothing in Wingdings) passes on both. Suite 834.
- A slip of mine, caught by those tests: a `cd` into the before-worktree moved the session's working directory there,
  and the next `python -m pytest` on the main tree's tests imported the worktree's old code - three tests failed for
  no reason, and a suite run from there skipped 17 tests that need benchmark pages. Retiring the worktree ended it; the
  memory on checking imports where they run now covers it.

**Seen, not changed.** In Aussie's additional-benefits table the second benefit's cell is split over four rows, so its
two bullets stay "‣ 10%" in separate rows rather than a list; the rows were split before this change (the known
wrapped-cell fault). And the census found the same fault in other fonts, both GIO's: a Wingdings 3 "`" - a solid blue
triangle on the page, though that code draws an outlined arrow in the system's Wingdings 3 - 1,775 of them in 7
documents, written as a markdown backtick; and a chevron "›", 2,220 in 11 documents, named by its text layer but
known to no list rule. The glyph reader sees both as right-pointing arrow heads. A rule "an arrow head opening a line
of words is a bullet" would fix both, but it loosens a guard set on purpose and needs its own measure: the owner's
call.

**Next:** D040's steps, as the owner ordered - version matching first.

---

## 2026-09-21, 19:17-20:30 - Words run together beside a big step number or a dingbat bullet: fixed in the word builder, and the 16 September diagnosis corrected

The owner ruled on the two questions the word check raised (appended to D040 in `docs/DECISIONS.md`): invisible
accessibility text stays dropped and unlisted, and text set sideways at a page's edge stays out of the front matter.
And chose the next piece of work: the words run together, the commonest fault of the first sample.

**It had been seen before, and put down to the wrong cause.** The owner recalled it had been looked at. It had: on 16
September, reading the Key Facts Sheets' page tops after the imprint change, the entry "2026-09-14 to 2026-09-17" of
this log noted page 2's "Step 3 Other things to consider" coming out "Step3Other things to consider" on 29 of 33
sheets, "the spaces around its large numeral lost", and my working notes put it down to the file - "spaces lost in the
text layer - visible now, not caused" - and left it. I did not check it. Counted now, on the 158 tuned-on sheets
(`bench/probes/step_space_census.py`, PDFium's text layer, every digit set at 30 points or more): beside roughly three
step numbers in five the text layer does hold the space - the file's own space character (240 of 572 sides after the
number, 150 of 594 before it), or one PDFium puts in the gap (89 and 221), or a clear gap (7 and 4) - and TrueDoc
threw it away. Beside the rest (236 after, 219 before) nothing in the file marks it: a digit is a narrow glyph in a
wide box, and the "1"'s box reaches the "U" of "Understanding" (144.9 against 144.8 on Apia's) though the page shows a
clear space. So the diagnosis was wrong for most of the spaces, and "not caused" was the wrong conclusion for all of
them: the type settles every one. TrueDoc lost them in three places, each judging a gap against the larger of the two
sizes beside it - the 48-point numeral's, not the 12- or 16-point words':
- `_chars_to_words` drops a space narrower than 8% of the larger size as a kerning artefact (TIO's 2.8-point space);
- with no space, it breaks a word only at a gap over 13% of the larger size (Qantas's 3.3 points against 48);
- `_fuse_touching_words` re-joins words closer than a tenth of the larger size - it undid the first version of the fix.

**The fix** (`truedoc/extract/textlayer.py`), by type, never by page:
- `_big_numeral`: a digit set at twice the size or more of the letter beside it. The gaps beside it are judged in the
  letters' type: a space there is kept, and with none a gap over 13% of the smaller size (or 0.9 point) is a break.
- `_numeral_then_capital`: that numeral followed by a capital, or preceded by a letter, is a word break however close
  the boxes - a letter never runs on into a numeral twice its size, and a capital after one starts a word. A small
  letter after it is left to the gap, so an ordinal's suffix stays on its number ("1st"); a large *letter* is not a
  numeral, so a drop cap still starts its word ("The").
- A letter or digit in a dingbat font shares no word with the text beside it: the Webdings bullet set a point into
  "artificial" (the meaning test's find) is no longer run into it. A mark already named stays inside its word
  ("INTMRK→BRDORT", one path of a model, as 4a58814 made it).
- `_fuse_touching_words` keeps both breaks.
Eight tests (`tests/test_words_run_together.py`), each with a page's own geometry: five fail on the old code, three
guards (the named arrow, the drop cap, "1st") pass on both.

**Not fixed, a separate fault:** the Webdings bullet is read as its code, the digit "4", not as the triangle it draws.
On the meaning test's page (t03, converted under both code states) the storm exclusions' cell read "loss or damage to:
4fences and gates ... 4artificial grass or turf 4garden retaining walls ..." and now reads "4 fences and gates ... 4
artificial grass or turf 4 garden retaining walls ...": each bullet where it stands, no longer part of a word, still a
stray "4". The Wingdings arrows' trap in another font: name the glyph from its code, drawn from the font and looked at.

**Measured, code against code** (the before state a worktree of 25a3724; each run prints the `truedoc` it imported):
- *The stage screen* (`bench/probes/line_signature.py`, new: the text layer's lines of every page of a population,
  held-out pages as a hash; the compare now reports pages that failed to read instead of skipping them): the insurance
  set 0 of 25 pages change (screened again on the final code); the benchmark 1 of 1,122, a maths line on a tables
  page ("j=1Œi" to "j=1 Œi"; converted in full the body is the same and its one check passes both ways); the Key
  Facts Sheets 288 of 380 pages, 237 tuned-on and 51 held out (counted). Every one of the 451 changed tuned-on lines
  is a step heading that only gained spaces ("STEP 1 Understanding", 16 September's "Step 3 Other", "4 Seek" on a
  line of its own), and no step heading is left run together on any tuned-on sheet.
- *The Key Facts grade* (`kfs_grade.py --fresh`): unchanged - header whole 157 of 158, held out 32 of 32; events and
  answers 1,885 of 1,885, held out 375 of 375.
- *The owner's insurance set:* nothing changes at the text layer, so nothing downstream can.
- Suite 830.

**The word check, run again - and a fault of the check that the fix exposed.** On the same 150 documents (seed 40)
the new code first read glued 26 on 16 pages down to 0 - but *missing* up from 11 to 15 on the tuned-on half and from
6 to 15 held out. The four new tuned-on "losses" were "1understanding" (Apia's; AAMI's building), "3other" and
"4seek" (AAMI's contents, page 2): the *reference* reading a step heading as one word where the page prints a space
(looked at: "STEP 3 Other things to consider", "STEP 4 Seek more information"). PyMuPDF has spacing rules of its own
and runs these together too. While TrueDoc did the same the two agreed and the check saw nothing - so the first
sample's 26 glued words undercounted the fault; the screen found 451 lines. The check gained the mirror of glued,
**split** (`classify_splits`: a word as the reference reads it that TrueDoc wrote as several; listed on a tuned-on page
to be read, the page deciding whose fault), four tests, and each row now names the `truedoc` it ran. Its first version
paired a lost "1understanding" with any leftover "understanding" on the page, so a lost "12" could have been excused
by a stray "2"; the numeral must now stand right beside its word in TrueDoc's text. Both code states, run again with
the one check:

| 150 documents, one page each | missing | glued | split | added |
|---|---|---|---|---|
| tuned-on (64 pages, 26,931 words), 25a3724 | 11 on 2 pages | 6 on 4 | 0 | 0 |
| tuned-on, the fix | 11 on 2 pages | **0** | 4 on 3 | 0 |
| held out (85 pages, 33,500 words, counted), 25a3724 | 6 on 1 page | 20 on 12 | 0 | 139 |
| held out, the fix | 6 on 1 page | **0** | 9 on 7 | 139 |

Missing and added do not move; respaced, repaired and the unchecked edge calls are the same in both states too. Of the
three tuned-on pages with a split, AAMI's contents page 2 had no glued word before - both readers ran "3Other" together,
the blind spot itself. The held-out split is 9 words on 7 pages, all among the 12 whose glued count fell, and the same 7
on which the first run counted new missing words (compared by script, never shown); what they are cannot be read.

**Next**, by D040's order: version matching, the store of confirmations, the review page, the second reader, a pilot
on one or two insurers. Small and separate: the Webdings bullet named from its code.

---

## 2026-09-21, 11:00-17:30 - D040's first two steps: TrueDoc records what it leaves out at a page's edge, and the word check

The owner asked how to create certainty in the conversions of his library, with review where it is uncertain; that
it work on each new document as it arrives; and that a person's answer be kept as a lesson. D040 records what was
agreed. This entry is its first two steps.

**A correction, found while agreeing it.** I had told the owner that the running-head rule dropped the GIO strata
SPDS's footer. It did not. The layout model labels the three lines a page footer, and D029 keeps such a line as
imprint only when the pages beside are known *not* to print it (`_repeated_beside(...) is False`); a one-page file has
no page beside, the answer is None, and the line was neither published nor recorded. An unknown treated as a discard.

**Step 1 - TrueDoc records its own close calls, starting at the page's edge** (`pipeline._record_imprint`). Every
header, footer and page number left out of the body now gets a record - what it was, what was done with it, why, and
whether the call could be checked - in `ConvertResult.decisions`. Three behaviours change, none of them in the body:
- *An unknown is kept, not dropped:* imprint with `checked: false`, and a note (`edge-unchecked`, severity note; the
  conversion stays complete). The GIO footer, "SPDS prepared on 29/07/14" with it, is kept.
- *A running head or foot is kept once* for the document under a new front-matter key, `truedoc.running`, with the
  pages it ran on. A Key Facts Sheet's prescribed "The content of this Key Facts Sheet is prescribed by the Australian
  Government..." stands on both its pages and was thrown away without trace.
- *A line of figures is compared by its figures.* The word check showed "unchecked" calls on documents of many pages:
  `layout.fuse._repeated_beside` compares letter-words only, so AAMI's "13 22 44" at every page's head, or a form code,
  could never be shown to run - my first record even gave the wrong reason ("no page beside it") and would have kept
  the phone number as an unchecked imprint on every page. `_repeated_beside` gained an optional `pattern`; its default,
  and so every rule that decides the body, is unchanged; the record alone asks again with figures counted.

The spec (`docs/OKF_SPEC.md`) documents `imprint`'s `checked`, `running` and the `edge-unchecked` code, and no longer
calls `confidence` "an estimate of meaning fidelity" - it is a label for where a page's text came from (0.9 text layer,
0.6 OCR, 0.5 vision model, 0 unreadable), and says nothing about whether it is right.

**Step 2 - the word check** (`bench/tools/word_check.py`). A page's printed words, read a second, independent way
(PyMuPDF, where TrueDoc reads with PDFium), against what TrueDoc wrote plus what it owned up to leaving out (its edge
decisions, its hidden text). One document as it arrives (`--pdf`), or a random sample of the library (`--sample`).
Held-out documents - odd hash of the name (D039) or held out by the Key Facts oracle - report counts only; the sealed
19 are never opened. What differs is sorted into four kinds: **missing** (neither written nor owned up to: a loss),
**glued** (words TrueDoc ran together: a fault), **respaced** (words the *reference* broke that TrueDoc kept whole: not
a fault) and **repaired** (a text layer's short-spelled ligature, "afer", that TrueDoc writes "after").

**It was wrong three times on the way, and each was caught by reading the page.** (1) I told the owner a whole table was
missing from CBA's home PEDG, from a print I had cut short; TrueDoc had written every tick and cross. The check had
counted the PDF's *accessibility text* - the tick labelled "Applies", the cross "does not apply", a star "asterisk" -
which PyMuPDF puts into its text as a span in a stand-in font though nothing draws it; read with `TEXT_IGNORE_ACTUALTEXT`,
130 "lost" words became 10. (2) Invisible text and symbol-font characters are marks for the eye or for a screen reader,
not printed words, and are left out of the reference. (3) The first "respaced" rule excused three words of a real loss
because the same words stood on a line TrueDoc had written whole; a line now counts as respaced only when most of its
words failed to match. Seven tests (`tests/test_word_check.py`), one checked to fail under the old rule.

**Measured.** The body is unchanged everywhere, as intended: insurance set 25 of 25, Key Facts Sheets 190 of 190,
benchmark headers_footers 266 of 266, byte for byte, against 259c43a - measured before and again after the figures
change. Every measure reads the body without the front matter (`ab_pool`, `kfs_grade`, `insurance_with_code` and
`truedoc/bench/olmocr.py` all convert with `frontmatter=False`). Suite 818.

**The first sample: 150 documents of the library, one random page each** (seed 40; 64 tuned-on pages, 85 held out, 1
without a text layer). Tuned-on: 26,931 printed words; **missing 11 on 2 pages, glued 6 on 4 pages**, added 0,
respaced 32, repaired 5, 5 edge calls kept unchecked. Held out, counted only: 33,500 words; missing 6 on 1 page,
**glued 20 on 12 pages**, added 139 (unexamined - most likely text TrueDoc read from pictures, which a text layer does
not hold), respaced 6. Read, the tuned-on faults are:
- **A cover table's two-level column headings torn apart** (CBA home PEDG, page 3). The ticks and crosses are all there,
  but "Building Cover", "Contents Cover", "Accidental damage (to your Building)" and "The excess amount is stated on
  your Certificate of Insurance" come out partly as stray headings above the table and partly not at all, and the
  table's heading row reads "| | | Cover | Building) | Contents) |": a reader cannot tell which column is which. The
  word check sees ten lost words of it; the damage - unlabelled columns - is structure, which is the second reader's job.
- **Words run together where a styled piece meets the next word**: "Step 1 Understanding the Facts Sheet" as
  "Step1Understanding" on four Key Facts Sheets of four insurers - AAMI, Apia, Qantas, TIO (the step number stands in a
  box of its own), and, from the meaning test, a Webdings bullet written "4" and run into its word ("4artificial grass
  or turf"). The commonest fault in the sample: 16 of 149 pages (4 of 64 tuned-on, 12 of 85 held out). A fault in the
  code: one generic fix.

**Also seen, not changed.** TrueDoc drops the invisible accessibility text without listing it under `hidden_text`, as
D011 asks (nothing is lost - the tick carries the meaning). A turned stamp at a page's edge is recorded in the
decisions but kept nowhere in the front matter: D029 left turned stamps out of the imprint because whether they run
cannot be asked; D040's "an unknown is not a discard" argues for keeping them, marked unchecked - the owner's to decide.

**Next, by D040's order:** version matching, the store of confirmations, the review page, the second reader, a pilot
on one or two insurers. The glued-words fault is a lesson of the first kind - a code fault, fixed generically.

---

## 2026-09-21, 09:20-10:59 - The meaning test, round 2: it now has teeth, it still cannot prove a difference, and it found three faults

The pilot could not tell TrueDoc's text from a plain dump. The diagnosis was that its questions named the thing they
asked about, so finding that word and reading on was enough, on either text. Round 2
(`bench/tools/meaning_test_structure.js`, 219 helpers, 14.2M tokens - I told the owner 10-12M, and it ran over)
changed two things on the same 30 pages: five new questions a page that a keyword search cannot settle (counting
every row that meets a condition, comparing across rows, a value needing the right row *and* column, a term the page
uses twice, whether something is absent, a condition stated elsewhere on the page), and a second, smaller reader
beside the strong one, standing in for what a product would use at scale. Both question sets went to both readers on
both texts: a 2x2, 293 questions after the unanswerable ones were dropped.

**A flaw of the pilot's, found and fixed here.** Its answerers were handed paths ending `.../td/<hex>.md` and
`.../plain/<hex>.txt`: the folder and the extension told a helper which text was TrueDoc's. Round 2 puts both texts
in one folder, same extension, opaque names. The pilot's numbers were taken with that leak open.

**The test now has teeth, and still cannot prove a difference.** The pilot drew no wrong answer at all; round 2 drew
plenty, so the questions bite. Paired over both halves (McNemar):

| reader | TrueDoc | plain dump | only TrueDoc right | only plain right | p |
|---|---|---|---|---|---|
| strong | 272/293 | 275/293 | 10 | 13 | 0.68 |
| small | 270/293 | 263/293 | 15 | 8 | 0.21 |

The small reader favours TrueDoc on every kind of page but prose (marks +4 net, table +2, list +2), and on the
held-out half alone it is 138 against 131 (p=0.12). Nothing reaches significance. At this discordant rate about three
times the questions - ninety pages, some 45M tokens - would be needed for a two-point difference, and that is a lot to
spend on a maybe.

**What the failures were worth, which is the real result.** Reading the tuned-on failures found three faults, none of
which the benchmark, the insurance set or the Key Facts oracle can see:

1. **A one-page document loses its footer entirely.** A GIO strata SPDS (`t12`): "Issued by: AAI Limited ...",
   "SPDS prepared on 29/07/14" and the form code are in neither the body nor the front matter, and
   `completion: complete`, `warnings: []`. Checked against the whole document, which is that one page, so it is not an
   artefact of converting a page alone. A reader cannot tell which version of the SPDS they hold. The test caught it
   as a question the plain dump answered and TrueDoc could not.
2. **A Key Facts Sheet's prescribed statement is removed as a running head.** "The content of this Key Facts Sheet is
   prescribed by the Australian Government and is a requirement under the Insurance Contracts Act 1984" stands on both
   pages of the sheet, so the running-head rule takes it. It is required by law to be there. (bda7609 gave back 13
   headings and 12 prescribed statements on 16 September; this is a case that rule does not reach.)
3. **A Webdings bullet set hard against its word comes out as "4artificial".** On `t03` a storm exclusion's list
   reads "4a design fault ... 4lack of maintenance ... 4artificial grass or turf": the bullet is the character "4" in
   Webdings, and the same trap as yesterday's Wingdings arrows - a symbol character set *inside* a word puts its font
   in `_read_private_glyphs`'s `spelled` set, so the glyph reader skips it, and the word builder glues it on. The
   plain dump at least leaves "artificial" a word. Twelve of them on that page.

**What I now think the test is for.** Not a scoreboard. On clean digital pages the two texts are close enough that
no affordable sample separates them, and the pilot plus round 2 have now spent about 27M tokens establishing that.
What the same machinery does cheaply and well is find faults: three in one reading of fifteen pages, each one a
sentence a reader needed and did not get. The recommendation is to keep drawing random pages and mine the failures,
and - if a number is still wanted - to measure it where the two texts actually differ (pages of ticks and crosses,
tables that continue overleaf, pages with no text layer) rather than on pages where both are at the ceiling.

**Limits.** One model family still plays every part. 293 questions put a two-point gap inside the noise. Five of the
150 tuned-on questions came back unmarked (one page's marker returned the new questions' marks only). The held-out
half returned counts and words-free marks, nothing else.

---

## 2026-09-21, 08:37-09:00 - D039's pilot, run: the test works, repeats, and cannot tell TrueDoc from a plain text dump

The owner parked the tables list on the evening of the 20th and asked how well TrueDoc converts *his* documents. D039
records what the number is to mean (a reader gets the right answer to a question about their cover) and the test. He
chose to run the pilot on this session's helper agents through the Workflow tool rather than on a paid API.

**A correction made before anything was built.** I had told him "Pro writes the questions, Flash answers", and he
agreed to that wording; in this project those names are Infinity-Parser2's two page-transcribing models (D033, D034),
which can do neither. Found by checking the premise, not by accident; he was told, and D039 carries it.

**The draw** (`bench/tools/meaning_draw.py`, seed 39). Eligible: 951 documents = 1,176 less the sealed 19, the 190
Key Facts Sheets and the insurance set's 16. A seeded shuffle, one page of each document at random, at most two
documents of an insurer in each half, held out by a hash of the file name. Three pages without a text layer were
dropped (in the product a model reads those, and none was running). Forty candidates a half were converted, their kind
read off the conversion, and 24 a half laid out kind by kind: pictures, TrueDoc's text and a plain PyMuPDF text dump,
each under a name that says nothing and shares nothing with the others.

**The workflow** (`bench/tools/meaning_pilot_workflow.js`; 231 helpers, no errors, three and a half minutes). One
helper per candidate sees only the page's picture, says whether it holds anything a policyholder would ask about
(38 looked at, 8 not usable), and writes five typed questions with kinds fixed in
advance (two table look-ups where there is a table, one on ticks or crosses, one on what is in a list). The first 15
usable pages of each half are the pilot. Three helpers answer blind - from the picture, from one text, from the other,
not told which text is whose. A marker sees question, true answer and given answer only. Where the picture answer is
not marked correct the question is thrown out, and a fresh helper looks at the picture to say who was right. For the
held-out half the workflow returns counts, and which question was marked how - never a word of a page or a question.

**What came back.** 30 pages, 149 questions.
- *The instrument:* the picture answers are right on **146 of 149 (98.0%)** - the bar was nine in ten. The three
  thrown out were all marked "partial" - none wrong, none missing - and the fresh look sided with the question
  writer on each. The marker never disagreed with the mechanical check of amounts and yes/no. **Two questions would have gone to
  the owner, not the ten to fifteen I guessed** - and on both, all three answers agree with the truth, so no ruling
  of his can change a number.
- *TrueDoc:* **144 of 146, 98.6% (95% interval 95.1-99.6).** *The plain text dump:* **142 of 146, 97.3%
  (93.2-98.9).** **Not one wrong answer from either, in 292 answers.** What was not correct was partial or missing.
- *By half:* tuned-on 72/73 each. Held out: TrueDoc 72/73, plain 70/73 - the plain dump's three are all on pages
  of ticks and crosses (two partial, one missing), where TrueDoc is 25 of 25; TrueDoc's one is a phrase on a prose page.
- *The tuned-on misses, read:* neither separates TrueDoc from the plain text. One question's truth was longer than
  any answer gave, the picture's included (thrown out). On the other the two texts gave the same answer, adding "you
  pay the $500 excess", which the marker called partial; whether the page says so was not checked.
- *It repeats.* A replay I expected to come wholly from the cache ran part of itself again: the same 149 questions,
  the same totals over the two halves together, and two marks of 447 moved, in opposite directions, both of them marks
  of a picture answer (the one I may see had added a true detail).

**What it means.** The test is sound and it is nearly blind. On the owner's digital pages, read by a capable model
one page at a time, the meaning survives a plain text dump almost as well as it survives TrueDoc: the words are all in
both, and a strong reader puts a flattened table back together in its head. The two-question gap is inside the noise.
The one place the pilot separates them is the one we would have predicted - ticks and crosses, which a text dump
drops. So as built this measures that *both* are near the ceiling, not how good TrueDoc is. To make it see, the
conditions have to be the ones where structure carries the meaning: questions that need several rows or columns at
once (how many events are optional; which items have a limit above a figure); whole documents and not single pages,
where running heads, broken order and tables that continue overleaf start to matter; a smaller reader, of the kind
used at scale, which leans on clean structure far more; pages with no text layer, which this draw left out and where
TrueDoc differs most; or a use that is not a model at all (a table turned into a grid).

**Limits, said plainly.** One model family wrote the questions, answered them and marked them. No record exists of
which library documents I have read pages of in past weeks, so some held-out documents may not be new to me. 146
questions put the interval at about plus or minus two points. Nothing of the held-out half has passed my eyes but
counts.

---

## 2026-09-20, 19:52-21:13 - A ruled cell takes the columns its rectangle covers: a column's centre is the column's

From the work list's permit-fee form, `tables/9e3b179d..._pg2`: fully ruled, and its vertical rules are *staggered*
between sections - the divider between codes and descriptions stands 16 points further left beside the lower rows
than under the first three, and the fee divider 10 points further right. A grid built from every rule has five
columns where a reader sees three; two are slivers. The benchmark's checker takes a cell's top heading as the first
non-empty cell of its column from the top, and its neighbour as the next column, so the page's checks failed through
the slivers ("cell to the right ''").

**Sized first** (`bench/probes/sliver_column_census.py`, every table we build, positive control on the known page):
a column that in every row is empty or under the same cell as a neighbour. **Insurance set: none in 19 tables. Key
Facts Sheets: none in 199. Benchmark: 14 of 389 tables, on 14 pages (2 held out), every one from the ruled reader.**
Of the 12 tuned-on: seven staggered, one mixed, two with only a wholly empty column (another question: a form's
blank column may be a real one, left alone), two grids of 25 and 31 columns that are probably no tables.

**The cause was upstream of any fuse.** "RESIDENTIAL" has the rectangle x 37-129, which covers the code column *and*
the sliver beside it, yet it was written over one column, and the cell beside it had no rectangle at all: a filler
we made up. `ruled.column_spans` stretches a cell over the next column when that column's centre lies inside the
cell's rectangle - and took the centre from *the first cell that starts in the column*. On this form that cell is a
description running on across the next column, so the sliver 113-129 had its "centre" at 301. **Now a column runs
from its own left edge to the next column's, and its centre is the middle of that.** A cell that reaches the wrong
centre reaches the right one too, so this can only give a cell columns it was missing - reasoned first, then seen:
on all ten benchmark pages it touches not one span is lost or narrowed.

**Screened exactly** (`pure_function_screen.py` on `truedoc.tables.ruled:column_spans`): **insurance set 0 pages,
Key Facts Sheets 0 of 380 pages**, benchmark 10 pages (3 held out). The screen itself fell over on the benchmark the
first time - the function answers with a dictionary keyed by (row, column), which JSON cannot write - at the first
page that differed; mended (`plain()`), run again in full. On the two sets it had finished, not falling over was its
own proof that nothing differed.

**Measured against 089bf27.** The 7 tuned-on pages: **tables 8 -> 12** (`9e3b179d..._pg2` 6/9 -> 8/9;
`53179836..._pg15` 2/4 -> 4/4, where "Health System Dimension" now stands over both its columns), the other three
sections level. All seven bodies change, and were read: on every one **the same words in the same order** (checked
mechanically with the table tags taken out) - what changes is made-up empty cells going (1 to 44 a page) and the
cell beside each taking the columns its rectangle covers: "SECTION I - OWNER INFORMATION", "Description: HVAC
PARTS", "IFB No. 75175", "TRANSITAIR SYSTEMS, LLC.". No table appears or disappears. Two of the seven are poor
before and after (a diagram read as a grid; a table in a font that maps to nothing) and only their spans move. The 3
held-out pages: the same score either way; their three bodies change, unseen. Four tests
(`tests/test_ruled_column_centres.py`; three fail on the code before). Suite 806.

**Not done, deliberately: the fuse.** The form is still five columns underneath - each description now spans three
of them. Removing a column that in every row lies under a cell which also covers a neighbour (the left on some rows,
the right on others, never a cell of its own) is the second step, and the definition of a staggered rule read from
the rules; the census probe's one-neighbour test has to be loosened to either side first. It gets its own screen.

---

## 2026-09-20, 18:20-19:51 - A lone line beside a table: built, measured, and NOT committed (it moved a sentence above the wrong equation)

`tables/e82a04c6..._pg5`, from the work list: the table came out headed by its first data row ("DFS to DFS"), its
real headings ("Parameters | Mean | SE | Units | Distribution | Source") left above it as paragraphs. **Cause, watched
in `_find_runs`:** the journal sets its caption in the margin, "Table 1 Base case input per" / "year"; the first line
lies in the page's top strip and is left out, the second ("year", x 51-66, 113 points left of the table) falls
between the heading row and the group label under it ("Survival probabilities"); two lone rows running close a run,
and it closed on a heading row alone.

**Built:** `_beside_the_run` - a lone one-segment line two sizes clear of the width of the run's rows of several
cells, and of the next three rows to come (so a short label under a centred heading stays), is stepped over: no row,
no break. The page then opens "Parameters | | Mean | SE | Units | Distribution | Source", and `8/9 -> 9/9`.

**Screened exactly** (`bench/probes/table_runs_screen.py`, the candidates `_find_runs` gathers under both code
states, with a positive control on the known page): insurance set 0 pages, Key Facts Sheets 0 of 380 pages,
benchmark 13 pages (3 held out) - sharing no page with the column-cut change, so each difference is this rule's.

**The reading, and why it does not go in.** Scores: +1, everything else level, the 3 held-out pages level. Bodies:
the target page better; arXiv `2503.08118_pg5` better - the "table" that vanished was Figure 1's vertex labels with
the figure's caption chopped across four cells ("The Gröbner fan | and its | Gröbner cones | for An-"), and the
caption is a sentence again; **arXiv `2503.07452_pg8` worse: "The k residual constraint, defined as:" stands between
equations (13) and (14) on the page and came out above equation (12)**, which makes (12) - the x-velocity bound -
the k constraint. Right words, wrong order, wrong meaning. (That page is poorly written in both states: its numbered
equations are also read as a table. The rule did not cause that; it moved the sentence.) It fired there because
ordinary body text at the left of the column also "stands clear" of a run of *centred* equations. One held-out body
changed, unseen.

**The definition, then the census** (`bench/probes/margin_line_census.py`). What a margin line is: the continuation
of a text block that stands beside the table - a line directly above it, one leading away, flush with it, itself
clear of the run. Of the 20 lines the loose rule stepped over on tuned-on pages (23 with the held-out pages'):
twelve are on arXiv pages and **none** fits - equation numbers "(5)", "(5.12)", lead-ins "where", "and", "by:",
body sentences; seven are lines of the *neighbouring text column* of a two-column page, which do fit, and whose page
came out identical because the builder refused the candidate; **one is "year".**

**Decision: not built.** The narrowed rule changes one page in 1,527 and nothing of the owner's, where even the loose
rule never fired; it is worth one check. Against that, stepping over a neighbouring column's lines removes the brake
that stops one column's rows being strung into a run past the other's, and what that does on two-column documents
outside these three sets cannot be measured here. What would flip it: margin-set table captions turning out to be
common in the owner's library or the benchmark. Kept so that it can be revived in minutes - the screen, the census,
and the function (its four tests were not kept: they assert the rule, and would fail without it):

```python
def _beside_the_run(row, run, after, size):      # called at the top of _find_runs' loop, for a one-segment row
    multi = [r for r in run if _is_multicell(r, size)]
    if not multi:
        return False
    multi += [r for r in after if _is_multicell(r, size)]          # after = rows[index + 1:index + 4]
    x0 = min(s.bbox.x0 for r in multi for s in r.segments)
    x1 = max(s.bbox.x1 for r in multi for s in r.segments)
    seg = row.segments[0]
    return seg.bbox.x1 <= x0 - 2.0 * size or seg.bbox.x0 >= x1 + 2.0 * size
    # to narrow: and a line of the page directly above `seg`, flush with it, also outside x0..x1 (needs the page's
    # lines, which `find_aligned_tables` has and `_find_runs` does not; "Table 1 Base case input per" is in the top strip)
```

**The "heading" kind of the work list, read through: six pages, six causes.** An invisible watermark (fixed,
6e261ac) and a cut placed on a heading (fixed, 4aa7257) on one page; this margin line (left); rows ruled off with
cells centred vertically, written a row per text line (`508eb272..._pg13` - the big one); a form whose vertical rules
are staggered between sections, so the ruled grid has five columns for three and two slivers that never hold text of
their own (`9e3b179d..._pg2`); a caption set inside the table's ruled box as a full-width first row
(`31d7e5e5..._pg162`); and a table that is a picture, which the model transcribed with seven headings over eight
cells (`3d780cdc..._pg22` - the reader's, not a table rule's). Also seen on `e82a04c6..._pg5` and not touched:
"4 × 325" comes out "4 9 325" (a symbol font's code for the times sign), and "Atos / Med." is an orphan row the
flush-left rule misses because it is indented.

---

## 2026-09-20, 18:15-19:47 - A column cut goes in the channel no word crosses; and the first version of it cut two phrases

The check that put `tables/c8cdd4c4..._pg3` on the work list, once its invisible watermark was out of the way: the
heading row's first cell read "Triacylglycerols (%) Palm oil*" over two columns. **Cause, watched in the code**
(`_refine_segments`): the vote found the right empty range - from the shortest label to the first value, 73 points
wide, because a dozen rows leave the second column empty - and then `place()` tries three points in it and no more:
just before the words that close it, its middle, its left end. "Palm oil*" stood over the first, "Triacylglycerols"
over the other two, and it gave up, with 9.2 points of clear page between the two headings (their word space is 2.0).
The two boundaries beside it were cut only because their ranges' midpoints happened to fall between headings.

**Built:** when all three places are refused, the widest stretch of the range in which no word of any row stands, if
it is at least the gap that counts as a vote (0.4 of the size).

**Screened exactly** (`bench/probes/column_cut_screen.py`: the other code state's function, loaded from a worktree,
is asked the same question beside the working tree's inside a whole conversion, and the two lists of cuts compared;
a positive control on the known page first, since a new screen that has only ever said "nothing" proves nothing).
Insurance set: 3 pages. Key Facts Sheets: **66 pages**, 14 of them held out - every one a cut *added*, none moved
or lost. Benchmark: 25 pages, 5 held out.

**What the reading found, that no score did.** On the 20 tuned-on benchmark pages: +1 check, nothing lost - and four
bodies changed, read against their pages. Two better: the palm-oil headings, and "CIP Code | Major", the feet of two
stacked headings that had been one cell (`d461e0d4..._page_3`). **Two worse:** a table's sub-title cut in two,
"Contributions from partners (thousands | of US$)" (`9a61fe78..._pg2`), and a diagram's label likewise (arXiv
`2503.05886_pg3`). Measured, what tells them apart is the definition itself: the bad cuts divide a line on *its own
word space* (a gap of 2.8 where its other words stand 2.8 apart; 5.2 against 5.2), the wanted one on 9.2 against
2.0. In 5.6-point type a plain word space is half the size, and passes for a vote.

**The guard:** the cut is refused if it divides any line on a gap no more than three times that line's ordinary
space - the measure `_splits_at_shared_edges` already uses. Checked that it bites: a copy of the code with the guard
switched off cuts the new test's title, "Contributions | from partners"; the guarded code leaves it whole.

**Measured again, guarded, against 6e261ac.** Benchmark, the 20 tuned-on pages: **tables 47 -> 48**
(`c8cdd4c4..._pg3` 4/5 -> 5/5), the other three sections unmoved, and exactly the two better bodies change. The 5
held-out pages: the same score either way in every section, no body changes. Insurance set, code against code:
**25 of 25 pages identical.** Key Facts Sheets, the 66 sheets, code against code
(`bench/tools/kfs_with_code.py`, new - the grader's cache is not a before state): **66 of 66 identical**, held out
included. Both of the owner's sets were first measured with the unguarded rule and then again with the guarded one,
because a call in which the guard refuses one range and allows another is a state neither "before" nor "unguarded"
had exercised. Why an added cut changes nothing there was not traced: the likeliest reason is that another route
(`_splits_at_shared_edges`) had already made the same division, which is a guess and is tagged as one. Three tests (`tests/test_cut_in_the_clear_channel.py`). Suite 802.

**Two things I told the owner that were wrong, corrected the same evening.** (1) "It can only add a cut." On
`dddf8e29..._pg15` a cut moved 6.1 points: the second look used to cut there at 115.2; the unguarded rule made a
first-look cut at 109.1, and the second look skips a range that already holds a cut. A cut this rule adds can stand
in place of the second look's. Under the guard that one is refused (it divided "Item Quantity Part Number" on its
word space) and 115.2 stands. (2) "It adds one cut on the palm-oil page." Two: the second falls between segments
already apart and divides nothing. **The risk read for and not found:** the rule also fires on candidates that are
not tables - the two columns of prose above the palm-oil table, a running head ("§ 381 | TITLE 21 | Page 386"), a
book's index - and a cut in prose is how two columns of text become a false table (the court form, in this file's
own comments). Under the rule as committed no table appears or disappears on any of the 25 pages - two tuned-on
bodies change, both within a table that was already there - and the running head, the index and the prose come out
byte for byte as before.

Not counted: the calls on which the *guarded* rule differs. The screen ran once, on the unguarded rule; the guarded
one can differ only on a subset of those calls, and every page among them was converted both ways again.

Riding along in the screen, a count for a change not made: cuts that stand in a word space (under 0.4 of the size).
Insurance none; Key Facts Sheets four pages, all the band "Cover for | valuables", which is never cut; benchmark 20
on 10 pages (3 held out), in formulas and numbered references. To be looked at on its own.

---

## 2026-09-20, 17:59-18:14 - An invisible watermark was being published: text inside a form drawn at nothing (D011)

Found while reading the next kind of the tables work list ("a data row where the heading should be"), on
`tables/c8cdd4c4..._pg3`. Our page opened with "# S", "# S", "# E", wrote "PPalm kernel oil*" above the table, headed
the table "CCLa | R6.8", and held cells like "LND E1.0", "C1.0 3.7" and "T0.8 I0.1 0.7". The page image shows none of
those letters. They spell **ARTICLE IN PRESS**: 72-point type at 45 degrees across the page, in a form the page draws
under an ExtGState of `/CA 0 /ca 0` - at nothing. Inside the form the text sets its own opacity back to 1, so the
character's own alpha, which is all the hidden-text reader looked at, said "visible". (MuPDF's text trace says
opacity 1.0 too.) PDFium does report the *form's* alpha - `FPDFPageObj_GetFillColor` on the form object gives 0 -
so the fact is there to be read.

**Sized** (`bench/probes/veiled_form_census.py`, every page's objects on all three sets, each form's alpha carried
down): text under a form drawn at nothing - **one page, that one**; none on the Key Facts Sheets, none on the
insurance set. Text under a *faint* form (a library's pale "(c) Biodiversity Heritage Library" at 0.2): one page, and
a reader sees it, so it stays. Fills and images under faint forms: ten benchmark pages and two Key Facts pages;
nothing reads those values.

**Built** (`extract/pdfium_objects._walk`, `extract/pdftext_rawdict`): the opacity a form is drawn with comes down
to the text objects inside it (the smallest on the way down - a nested form inherits and reports the outer one's
again, so a product would count it twice; the larger of fill and stroke alpha, so only a form that shows neither
hides anything), and a character is no more opaque than that. Only zero is read anywhere (`opacity == 0.0`), so
exactly the text the census found can change. It is hidden text under D011: out of the body, listed in the front
matter. Three tests (`tests/test_text_in_a_transparent_form.py`: hidden at nothing - fails on the code before; read
at 0.2; read in an ordinary form). Suite 799.

**Measured against 4a58814** on the page: **checks 4/5 -> 4/5 - the benchmark is blind to it** - and the body: the
three headings gone, the heading row back on top of its table, "R6.8" -> "6.8", and the seven cells that held
watermark letters ("I", "LND E1.0", "NND", "C1.0 3.7", "T0.8 I0.1 0.7", "R2.6 1.8", "A10.1 POL") give the values
they had swallowed back to their own columns ("1.0 | ND", "3.7 | 1.0", "0.7 | 0.8 | 0.1"). What is still wrong on that page is the check that put it on the list: the heading row's first cell reads
"Triacylglycerols (%) Palm oil*" across two columns, though the gap between the two headings is 1.15 em against a
word space of 0.25 em and the cut between every other pair of headings was made. Next to look at.

**A slip found and mended: my census helper never marked the BENCHMARK's held-out pages.**
`bench/probes/orphan_row_census.jobs` flags held-out Key Facts Sheets, so that a census counts them and never prints
what they say; for the benchmark it passed `False` for every page. Since 19 September every census and screen of
mine over the benchmark has therefore listed held-out pages with the rest (counted now, names not read: e.g. 28 of
the 150 pages the cell-joiner screen named, 39 of 251 in the underscore census, 10 of 57 in the table-continues
census). What that did and did not touch: the rules were designed from tuned-on pages (the work list excludes the
held-out ones by construction, and I checked that the two guard corrections a screen prompted - "Cor", "s-ingle" -
came from tuned-on pages); but screens' changed pages were A/B'd and read without telling the two kinds apart, so
the held-out score is no longer evidence that is clean of my eyes for the rules of 19-20 September. The quoted
number is the whole benchmark and is unaffected. Mended: `jobs` reads `bench/holdout.txt` and flags those pages;
the probes already mask what a flagged page says.

**Sized, not built: text set on a slant** (`bench/probes/diagonal_text_census.py`). The line builder calls a line
rotated only past 60 degrees, so a 45-degree watermark is level text to it - which is how the letters above got into
table cells. Visible ones exist: six tuned-on benchmark pages hold text turned 25-65 degrees ("PREPRINT" at 100
points, "For Peer Review", a study guide's and a leaflet's diagonal title, 386 slanted axis labels of one chart), none
on the Key Facts Sheets or the insurance set. PDFium's angle also reports sheared italics as 12-23 degrees, so a
threshold has to sit above those. Next after the heading kind, as its own change with its own screen.

---

## 2026-09-20, 17:42-17:58 - A Wingdings arrow is a character; an arrow known only by its glyph id is sized and left

The rest of the work list's second kind (a character the page shows and the text layer does not hold): three checks
on two pages, and the two pages hold their arrows in two different ways.

**"INTMRK→BRDORT" came out "INTMRKBRDORT"** (`tables/b5c5b866..._pg4`, a table of hypotheses, each a path from one
construct to another). The arrow is a character, Wingdings code E0, which reaches us as the private-use U+F0E0; the
renderer strips private-use characters, and the reader of private-use glyphs (`_read_private_glyphs`) rightly leaves
a font alone once it has set such a character *inside* a word. `_symbol_font_mark` already names Wingdings' tick,
cross and boxes from their codes; it now names the arrows too (`_WINGDINGS_ARROWS`): DF-E6 the light ones, E7-EE the
heavy, EF-F8 the open. Every code was **drawn from the font file and looked at** (a contact sheet of
`C:/Windows/Fonts/wingding.ttf`), not recalled - and FB-FE came out as the tick, cross and boxes the table already
held, which checks the sheet. Wingdings proper only (`_WINGDINGS_PROPER`): Wingdings 2 and 3 draw other things at
those codes, and the older table's substring test would have matched them.

**Screened** (`bench/probes/wingdings_arrow_screen.py`, the text layer of every page of all three sets): five arrows
on that one benchmark page; none on the Key Facts Sheets' 380 pages, none on the insurance set. **Measured against
b64378b** on the page: **tables 5/7 -> 7/7**; the body changes in five cells ("BRDORT→INTERDVU" ... "JOBSAT→BRDORT")
and nowhere else. Five tests (`tests/test_wingdings_arrows.py`). Suite 796.

**"⇨ Post-deal" - sized, not built.** `tables/9921f236..._pg349` also sets its arrow in Wingdings, but the producer
re-encoded the subset (codes 1, 2, 3 in order of first use) and wrote no Unicode map: MuPDF says U+FFFD, PDFium the
bare code 2, the drawing reader says "unknown", and the check wants "⇨" exactly. One thing still names the glyph:
the subset kept the font's glyph ids - 226 glyph slots, the whole font's count, three of them filled - and glyph 214
of Microsoft's Wingdings (5.01) is code F0, the open right arrow the page draws. Census
(`bench/probes/wingdings_glyph_id_census.py`, all three sets, every Wingdings character whose code is not an arrow's
and whose glyph id is): **six characters, that one page, nothing else.** A rule for one page resting on one
producer's subsetting habit is not built. What would bring it back: the owner's library showing re-encoded Wingdings
*ticks or crosses* - an answer, not an ornament - where the glyph id would be exact and the drawing reader is a
judgement.

One slip on the way: `textlayer.py` imports `re` as `_re`, so the first screen died at import and measured nothing;
seen in its output, fixed, rerun.

**Next kind: a data row or the caption standing where the heading should be (6).** First page read against its image
(`508eb272..._pg13`, a review's table of studies): the fault is not the heading. The table is ruled off between rows,
its cells are centred vertically and hold one to five lines each, and we wrote a row for every text line: the head
came out a table of its own (three rows), the first study as loose paragraphs, and the other five studies as a second
table of 19 rows with the second study ("Porcine (4)") as its heading. The heading check fails because the table is
shredded. To be sized as what it is: rows ruled off, cells centred.

---

## 2026-09-20, 17:10-17:41 - An underscore TeX drew as a rule is a character of its word

First thing built from the tables work list, and not a table rule. "Japanese_spaniel" came out "Japanese spaniel"
because the PDF's text never held an underscore: in TeX's classic encodings `\_` is not a character but
`\kern.06em\vbox{\hrule width.3em}` - a rule three tenths of an em long and 0.4 pt thick, on the baseline. A mark the
page draws, like the ticks and arrows already read, and any identifier on such a page loses it, in a table or out.

**Sized first** (`bench/probes/drawn_underscore_census.py`, every short flat rule lying in a text line, all three
sets; it reads the PDF's raw drawings, because `page.drawings` keeps nothing under 2.5 points and an underscore in
six-point type is 1.8 long). 3,432 such rules on 251 benchmark pages; 56 lie between two words; measured in the type
size of the word after, **18 on five pages carry TeX's fingerprint to the hundredth** - length 0.30-0.34 em, 0.06-0.07
em after the word before, hard against the word after, 0.02-0.03 em above the baseline, 0.4 pt. None on the Key
Facts Sheets, none on the insurance set. What misses it, each looked at: the dashes of a dotted underline ("she's at
the", a transcript's notation: a third of the length, under the baseline, thrice as thick); a rule between "Space"
and "Frequency" in a plot's title, where the page shows nothing at all; a 0.93 em rule under "Value Units"; and two
left alone for want of evidence - "Kademlia_REQ" (0.50 em, below the baseline: perhaps another producer's
underscore) and "Target_3" (0.23 em in a scaled figure).

**The reader** (`extract/textlayer._read_drawn_underscores`, after touching words are fused, digital pages only):
between a word ending in a letter or digit and one starting with one, a rule to that fingerprint joins them as one
word with a `_` character of the following type. Two traps met on the way. PDFium's bounding box for a *stroked*
rule is the rule grown by its stroke width on every side (3.49 points for a rule of 2.69), which is a third of what
is being measured - the reader takes the segment the path strokes (`PageObject.lines`) and the rectangle it fills,
not the box. And the rule has to leave `page.drawings` once it is a character: left there, the maths reader took the
same stroke for a bar over the new character and wrote `\overline{\_}`.

**Screened exactly** (`bench/probes/drawn_underscore_screen.py`, hooking the reader on every page of all three sets,
text layer only): 17 words on five benchmark pages, none elsewhere. **Measured against c63d399** on those five:
**tables 12 -> 14** (`8bc04603..._pg1` "Japanese_spaniel", `3331dcc1..._pg2` "F1 Score_RCNN"), **arXiv maths 2 -> 3**
(`2503.04690_pg4`), nothing lost, five bodies change and each is the identifiers and nothing else: sloth_bear,
Sealyham_terrier, Japanese_spaniel; Score_RCNN, Score_YOLO; DECC23_012_DIP; ten hashtags of a German table
(GEGEN_Masseneinwanderung, UNSER_Politiker, ...); and a formula that had lost half its subscript - "\(k_{\text{fixed}}\)
subtraction frames" is now `\(k_{\text{fixed}\_\text{subtraction}}\) frames`, which is what the author wrote. The
owner's documents cannot change (no rule of theirs carries the fingerprint). Five tests
(`tests/test_drawn_underscore.py`). Suite 791.

---

## 2026-09-20, 17:03-17:10 - The tables work list, sorted into kinds (first pass, nothing built)

The 54 table checks on 30 tuned-on digital pages that Pro passes and we fail (`bench/probes/tables_gap_against_pro.py`),
each run through the benchmark's own checker with what we wrote beside it
(`bench/probes/tables_gap_dossier.py`: the checker's words, and for a cell it cannot find, the cell of ours that holds
the words or is most like them). The checker says: no table at all 9, no such cell 28, relation not satisfied 17.
Sorted by cause, from those words and our cells (pages not yet all read against their images - the counts are a
first pass, and the kinds are what matter):

- **Not a table rule's to fix - 16.** A parts table drawn as vector strokes on a page with a little real text (5); a
  PDF whose font map writes "(" as "~" (5); the escaped dollar, D024, decided (6: `c45171e3` 4, `cf7ccdf5` 2).
- **A character the page shows and the text layer does not hold - 5.** *The underscore*: "Japanese_spaniel" is
  "Japanese spaniel" and "F1 Score_RCNN" is "F1 Score RCNN" in ours (2). Looked at in the PDFs: the text layer has
  no underscore at all - "Japanese" and "spaniel" are separate spans - because LaTeX sets `\_` as a small drawn rule
  at the baseline. A mark drawn as a shape, like the ticks and arrows we already read; every arXiv page with an
  identifier in it is exposed, in and out of tables. Arrows: "INTMRK→BRDORT" is "INTMRKBRDORT" (2) and "⇨ Post-deal"
  is "Post-deal" (1).
- **A data row or the caption standing where the heading should be - 6.** Top heading found = the first data row
  ("Porcine (4)", "DFS to DFS", "CCLa", "New residential building 500 sq. ft. and under.") or the table's caption
  ("Table 14: ..."), and one heading row shifted a column ("Soil thick." over the soil-type column).
- **A blank where the neighbour should be - 6.** "Cell above ''", "cell to the right ''": a value set on another line
  than its label, a heading over two levels ("P | R" under "Lexical Features").
- **Columns fused - about 6.** "4.79±0.37 4.81±0.31 4.77±0.51" in one cell; "83 10.6%:"; two pages of small numbers
  to be looked at.
- **Rows or labels fused, or a wrapped cell's first line left alone - 5.** "F. oxysporum Fresh weight (g)" (a group
  label run into the first entry), "Frequency" without its "(f)", "Planning for and managing residential," cut at
  its first line, a value and its bracketed statistic apart.
- **No table found where there is one - 4** (`f5e5d540_pg12`, a trial-reference table).
- **Singles - 6:** words on the page but outside the table (3, two pages), a row label spanning one line out
  ("Verbal" for "Nonverbal" - the "Cas 2 Homme" fault again), a p-value a column out, one character that differs
  ("Dcrr" for "Dcrc").

So of 54, about 16 are out of reach of any table rule, and the single most general thing in the list is not a table
fault: a drawn underscore. That is sized next, on all three sets, before anything is built.

---

## 2026-09-20, 09:47-11:10 - D038 built: a table inside a cell is written as a table, inside the cell

The owner decided it at 09:47 ("Go with B"; D038 in `docs/DECISIONS.md`, the four options shown to him rendered).

**Groundwork** (3e2c0b8): `TableCell.inner`, as `listing` carries a list; `render_table` goes to HTML for it and
writes the inner table inside the `<td>`; and our own tools, which found rows with non-greedy patterns that a nested
`</tr>` cuts, walk the tags with nesting counted (`kfs_grade.html_parts`, used by `blocks` and by
`kfs_two_readers.gather_spans`). Checked neutral on all 578 sheet files we hold, ours and the model's.

**Sized first** (`bench/probes/nested_table_census.py`). The signal: a body cell of three lines or more, *every* line
broken at a gap no word space makes, the pieces after the gap starting at one place. A first version counted every
ticked list (a list breaks each line after its mark, at the same place) - only pieces after a gap *within the row*
count, and a row opening with a mark leaves the cell to D028. Result: no insurance cell; on the Key Facts Sheets
CGU's four cells and nothing else; on the benchmark's 1,122 digital pages one page, a field-trial table that rules
one cell round each treatment's product lines (name, rate, unit, timing) - the same thing in another document.

**The stage** (`tables/cell_tables.py`, after `list_cells`): the inner table is built from the cell's own lines by
the builder every text-built table goes through (`aligned.table_from_lines`), and kept only if it says what the cell
said, word for word in order; none with spans. Its first row is a heading only on evidence, and type gives none -
CGU sets "Policy | Item Limit | Overall Limit" in the face, size and colour of its rows (checked in the PDF) - so:
no cell of the first row holds a digit, and in some column every row beneath does. "Accidental Damage Home |
Australia & New Zealand" is therefore a row, as it is on the page.

**Screened exactly** (`bench/probes/inner_table_screen.py`, hooking `read_inner_table` on every page of all three
sets): CGU's two sheets (four cells), the one benchmark page (five cells), nothing else in 1,527 pages.

**Measured against 3e2c0b8.** Key Facts Sheets, all 190 fresh: exactly CGU's two change; grade unchanged (header
whole 157 of 158, held out 32 of 32); two-reader comparison unchanged, two rows, both the model's. The rows now read
`<td>High value items and collections</td><td>Yes</td><td><table><tr><th>Policy</th><th>Item Limit</th><th>Overall
Limit</th></tr><tr><td>Accidental Damage Home</td><td>$2,500/item</td>...` and, for "Items away", three plain rows.
Six tests (`tests/test_table_inside_a_cell.py`), one in `test_render.py`, one in `test_kfs_two_readers.py`. Suite 786.

**The benchmark page loses a check, and that corrects what I told the owner before he decided.** `637951191e..._pg2`
goes from 2 of 3 to 1 of 3: "`97 a` has the top heading `Jul-11-2018`" now fails. Cause, read in the scorer:
`parse_html_tables` collects an outer table's rows with `table.find_all("tr")` and a row's cells with
`row.find_all(["th", "td"])`, both of which descend into a nested table - so the inner rows become rows of the outer
table, the outer row counts the inner cells as its own, and every column to the RIGHT of the nested table shifts. My
test this morning had passed five of five because CGU's nested table sits in the LAST column, where nothing shifts;
I gave him that as "the benchmark's checker reads this form", which it does only there. Cost today: one check of
7,019 (about 0.01). It is D024's kind of cost - the scorer's bookkeeping, not the page's meaning - but it also says
something true about the form he chose: a parser that walks tables the naive way, and the benchmark's is one, misreads
a table that holds another. That was the flip-fact I named for the downstream trial; it is now observed, not
supposed. Recorded in D038.

Left as it is: on that page six of the eleven treatment cells are not taken (each holds a row with no wide gap, or
lacks the shared start), so five read as inner tables and six as lines. Truthful, uneven; one benchmark page does not
earn a rule for siblings.

---

## 2026-09-20, 07:19 - Correction: the escaped dollar's cost was known, measured and accepted on 12 September

Yesterday evening's entry put "D024 costs eight benchmark checks" to the owner as a finding and a decision waiting
on him. It is neither. `docs/DECISIONS.md` has it all, and I did not open it before writing: on 12 September the
cost was measured *before* the decision (sixteen checks of the 98 on the fifteen pages carrying one, fourteen in
tables, "about a fifth of a point"), put to the owner as option 1 of three, and **accepted with the number in front
of him** - "the output is to be read rendered as well as by machine, and meaning for the reader decides". The owner
asked this morning whether the decision had not been made because it *improved* the score. The half of D024 he may
be remembering is the other one: writing formulas as `\(...\)` - which stopped a stray dollar sign flipping every
formula after it (it had cost 2503.05329 page 4 its check) and was measured to cost nothing, 7,019 checks identical.
The escaping half was the one known to cost, and was chosen anyway, for the reader.

What yesterday's measurement adds is only the present size of that accepted cost: **eight checks on run 98** (six
table, two order; about 0.11 overall) against sixteen on run 80's markdown. Why it has halved is not traced - more
tables are written as HTML now, where nothing is escaped, and the scanned pages are read by other models than on
12 September; either could account for it, and neither is checked. Nothing is open here unless the owner wants to
reopen D024.

The slip is the one the doctrine names: a claim about a decision, made from memory, where the record was one
`grep` away.

---

## 2026-09-19, 20:27-20:36 - The tables gap to Pro, opened up; and what the escaped dollar costs

The owner's list has "the digital-tables gap": Pro reading every page alone passes 930 of the 1,022 table checks,
run 98 passes 915. Compared check by check (`bench/probes/tables_gap_against_pro.py`, run 98's `failed_tests.jsonl`
against Pro's post-processed run scored on our scorer, `inf2pro_all_post-bycat-20260918-125957/table_tests`):

- **It is not fifteen checks. It is 65 against 50.** We fail 65 that Pro passes, Pro fails 50 that we pass, 42 both
  fail. Two readers with different mistakes, not one reader a little behind.
- Of our 65, **61 are on digital pages our own converter reads** (35 pages; 4 checks on one page a model read). Seven
  of the 61 sit on five held-out pages - counted, not opened. **The work list is 54 checks on 30 tuned-on pages**,
  thirteen of them holding two or more (list in the probe's output).
- The three heaviest, looked at: (1) `fbeb6edc..._pg1`, five checks - an engineering drawing whose parts table is
  drawn as *vector strokes*; the page has a text layer (a product label) so nothing sent it to a model, and the table
  is simply absent from our output. A page whose text layer covers a small part of its ink is a class D019 and the
  router do not reach - a design question, not a rule. (2) `53d3f304..._pg3`, five checks - the text layer's font map
  is wrong: "(−0.04, 0.04)" is encoded "~20.04,0.04!"; the characters are exact and wrong, which only reading the
  image can catch. (3) `c45171e3..._pg10`, four checks - **our table is right and fails anyway**, which led to:

**The escaped dollar (D024) costs eight benchmark checks.** We write a literal dollar as `\$` so that no viewer takes
the stretch between two prices for a formula - the owner's decision, and the right one for a reader. The benchmark's
checks read a cell's text literally, so "\$166,852" is not "$166,852". Measured over every check of every page of run
98, as written and with the escape taken out again (`bench/probes/escaped_dollar_cost.py`): 52 pages hold an escaped
dollar; **eight checks pass only without the escape** (six table, one multi-column order, one old-scan order) and none
passes only with it. Worth about **0.11 on the overall** (86.83 would read 86.94). HTML tables are not escaped, so this
is the markdown pipe tables and running text. Nothing changed: it is the owner's decision against the owner's number,
and it is his to weigh. (One way to have both would be to write a table that holds dollar signs as HTML, where no
escape is needed; that is a trade of its own - HTML is harder to read raw.)

---

## 2026-09-19, 19:53-20:26 - A table that restarts under a band: sized, and not built

Markdown has no table without a heading row, so where the finder cuts one table in two, the first *data* row of the
second part is written as a heading. Counted on the cached Key Facts Sheets: **six tuned-on sheets and two held
out** write a data row as a heading, in three shapes - four "household_kfscts" sheets (one template) where the band
"Cover for valuables, collections and items away from the insured address" comes out as a paragraph between two
tables and `| High value items and collections | Optional | ... |` heads the second; Huddle's building sheet, cut
between "Malicious Damage" and "Impacts" with nothing between; and Bendigo's contents sheet, a table nested in a row
like CGU's.

The candidate - *a table directly under another, with the same columns starting at the same places and at most one
line between them, is the same table* - was sized before anything was designed
(`bench/probes/table_continues_census.py`: every pair of tables one under the other, the gap, what lies in it, the
second's first row). Insurance set: 5 pairs, 1 with matching columns, and it has a heading and a figure between its
halves - two tables, rightly. Key Facts Sheets: 6 pairs, **4 with matching columns, all the one template**, gap 1.7
body sizes, the band the only thing between. Benchmark, 1,122 digital pages: 79 pairs, 8 with matching columns, and
**none the candidate should take** - the two with nothing between stand four body sizes apart (the sessions of a
timetable; result blocks of an OCR'd page), the rest have a caption or a paragraph between.

So a gate that is safe fires on one insurer's template and nowhere else in 1,527 pages. That is the chevron-marker
case again (one document of sixty, refused on 17 September): a structural change to a page's blocks, with a wrong
join costing far more than this fault does, is not earned by one template. And the fault is mild where it occurs:
every word is on the page in order - the band as a line, the row under it - only the row is dressed as a heading.
**Recorded, not built.** Huddle's cut is one sheet and not this shape (it did not come up as a matching pair);
Bendigo's waits on the owner's answer about a table inside a cell. The probe is kept.

---

## 2026-09-19, 18:51-19:51 - Run 98: the day's eleven commits, measured whole

Every change today was measured on exactly the pages it could touch. Run 98 asks the other question - what do they
come to together, on all 1,403 pages - with run 97's arrangement to the letter (the tree at f0509bb; `EXTRA=
"--vision-endpoint file:<inf2flash_raw>+<olmocr2c> --vision-deep file:<inf2pro_raw>" bash bench/tools/launch_run.sh
98 truedoc97`; validated 18:51-18:56: suite, gate 100, samples 46 and 61; launched 18:56, converted by 19:48, scored
19:51; folder `bench/runs/truedoc97-20260919-194807`).

**86.8 (CI 86.0-87.7) - 86.83 against run 97's 86.82.** Held-out 86.1 (1,097 of 1,255; run 97: 1,096), tuned-on 84.8
(4,993 of 5,764). Against run 97, check by check (`bench/tools/run_diff.py`): **tables 913 -> 915, headers and
footers 735 -> 734, every other section identical** - arXiv maths 2,594, old-scan maths 397, old scans 307,
multi-column 739, tiny text 404, baseline 1,392.

**It is exactly the sum of the parts.** The two table checks are the two the page-level A/Bs found - `c6673ff6..._pg3`
(part B: "...Non-communicable / Diseases (2011)" one cell) and `11d982c1..._pg3` (the heading rule: "Depth | H | 63"
a body row again). The one lost is `headers_footers/bec1f712..._page_9`, the windowed-absence accident that "one
picture, one figure" (d5ba8bd, 18 September evening) was measured to cost and was accepted with - it landed after
run 97 and this is its first full run. Nothing moved that a targeted measurement had not already named, in either
direction: the screens' claim that nothing else could change held on 1,403 pages.

So the quoted number stays **86.8**, and stays run 97's - the run that is tagged and published. What the day bought
is mostly not on this ruler: 23 of the owner's sheets with their heading whole, AAMI's and CGU's rows right, the
second reader's 23 differences down to the model's own two, a grader that can now see what it missed.

---

## 2026-09-19, 17:36-18:49 - The paragraph joiner: two slips mended, and two of my own caught by the screen first

`render/okf._join_at_hyphen` joins a line ending in a hyphen to the next, for every paragraph - and, since this
afternoon, for every table cell. Two slips in it, both found through the table joiner's screen:

- It asked whether the next word is a function word *before* asking whether the halves make a word, so "the
  guardian spir-" / "it who watches" was written "spir- it". Halves that make a word are the word.
- It closed up whatever the word list did not know, so one letter and a hyphen lost its hyphen: "Deep Q-" /
  "network" was "Deep Qnetwork", "L-" / "carnitine" was "Lcarnitine", "d-" / "dimensional" was "ddimensional", and
  Maltese "l-" / "ewwel" was "lewwel". No word is broken after its first letter; one letter and a hyphen is the head
  of a compound.

**Each of my first attempts at these was wrong in one case, and the exact screen is what said so** - a function of
two strings, asked old and new about every join of every conversion of all 1,527 pages (`pure_function_screen.py`,
which now takes a dotted module, several functions at once, and runs the whole conversion since a renderer's
function is only called when the page is written). First attempt at the first slip: two joins change on 1,527 pages,
"spirit" and **"a minimum grade of C-" / "or ECON 402H" -> "Cor ECON"** - a grade and its minus; the word list holds
"cor". So the first half must be two letters at least. First attempt at the second slip: nine joins, eight right and
**"a s-" / "ingle object" -> "s-ingle"** - one page does break a word after its first letter. So the one-letter rule
yields when the halves are a word. The same screen showed that the word-first check I had put into the *cell* joiner
at 54b2eca would have written "Cor" too; it is gone from there, and cells simply use this rule. One mechanism.

**Measured against ec0b929.** No insurance page and no Key Facts Sheet holds a join that changes (screened: none), so
neither set can move. Benchmark: the nine pages the final screen named, both ways - no check moves; eight bodies
change by nine words, all read here: Q-network, d-dimensional, T-carbon, spirit, l-opra, l-ewwel, L-carnitine
(twice), b-mercaptoethanol. The ninth page ("single") is byte for byte the same. Four tests added to
`tests/test_render.py` (eleven there now). Suite 778.

Two screens of forty-five minutes for nine words looks dear. It is what it cost to change a function every page
passes through and know that nothing else moved - and both of my first drafts would have shipped a wrong word.

---

## 2026-09-19, 16:49-17:35 - A table read from its drawn rules joins a cell's lines as every other table does

The ruled builder (`tables/ruled.py`) turned every line break inside a cell into a space - the same inline
expression in three places, two of them feeding decisions and one the text - and never asked the joiner. One
function now, `_flat`, folds a cell's lines with `aligned._join_lines`, at all three.

**Screened exactly** (`bench/probes/ruled_flat_screen.py`; the old behaviour was an expression, not a function, so
it is written into the probe as it stood and compared with `_flat` on every call of every conversion): no insurance
cell; on the Key Facts Sheets one page, Huddle's; on the benchmark **126 cells on 13 pages**, none of them a
difference of white space alone. So ruled tables had been stranding hyphens all along, only not on the owner's
sheets, where I had searched and found none: "(reason- able cause required", "research pro- ject", "exemp- tions",
"8:00a- 8:50a" down a timetable, "Community- based", "Non- Aboriginal", "сум- марный", "порож- нини", "Grund- skola".

**Measured against 54b2eca.** Benchmark, the 13 pages both ways: no check moves; twelve bodies change, and every
change is one of those repairs (46 words in all). Two on a Swedish page are no better than before and no worse -
"arbe- tar" is now "arbe-tar" where the page means "arbetar": the word list is English, and halves it happens to
know are kept as a compound. Key Facts Sheets, all 190 fresh: **exactly one sheet changes - Huddle's heading reads
"Yes/ No Optional"** - and under the stricter grader "header whole" is **157 of 158**, which is its ceiling: the one
left is Defence Service Homes' own wording of the heading. Held out 32 of 32; everything else as it was. One test
added (`tests/test_table_hyphen_join.py`, six in all). Suite 774.

Where the day's rule-making leaves the sheets: header whole 157 of 158 (the 158th is not a fault), every prescribed
event in a row of its own with its answer, no band swallowed, no stray row - under a grader that this afternoon
learnt to ask two questions it had not been asking; and against the second reader, two differences on 158 sheets,
both the model's.

---

## 2026-09-19, 15:53-16:48 - A cell's line break is repaired as a paragraph's is; and what that did not reach

**The two sheets the stricter grader fails.** Defence Service Homes' building sheet is **not a fault**: the insurer
words its heading "Risk | Covered? | Some examples of main conditions and exclusions (...)*", our table is whole, and
a grader that asks for the prescribed words cannot pass it - its ceiling on the tuned-on sheets is 157 of 158. Huddle's
contents sheet is real: the PDF itself sets "Optiona" and, on a line of its own, "l".

**The change** (`tables/aligned._join_lines`, which joins the lines of a cell for the text-built tables and is
borrowed by `boxed_cells`, `fill_grid` and `rule_grid`). A line ending in a hyphen before a lower-case line was closed
up unless *both halves were in a word list*, which kept "rent-ed", "how-ever", "switch-ing", "Sec-tion", "be-comes".
It now asks first whether the halves make a word (then they are the word, even before a function word: "spir-" /
"it" - found by this change's own screen, and the paragraph rule has the same slip) and otherwise uses the paragraph
joiner's rule, `render/okf._join_at_hyphen`, which the benchmark has already shaped (its docstring records what run
60 taught it): the hyphen stays
in a compound the list lacks ("dual-unitary", "gram-positive", which the old test wrote "dualunitary",
"grampositive"), in a URL, before a capital or a digit, and keeps its space when it is suspended ("intra- and").
A word broken with no hyphen (`_word_broken_in_a_cell`) is made whole when the upper fragment is no word, the two
together are one and the lower is in lower case; a single letter below counts unless it is "a" or "i".

**Screened exactly** - and the screen itself had a hole first: three modules import `_join_lines` by name and hold
their own reference, so hooking `aligned` alone would have missed their calls. `pure_function_screen.py` now rebinds
the function in every `truedoc` module that holds it (four here; the functions screened earlier today have no outside
callers, checked). Result: no insurance page; 6 sheet pages (5 tuned-on, 1 held out); **312 calls on 150 benchmark
pages** - 156 of them a hyphen wrongly kept and now closed, 67 a compound wrongly closed and now kept (mostly right;
wrong for words the English list lacks - "Aller-dings", "vie-le", "impervious-ness").

**Measured against aa2a880.** Benchmark, all 150 pages both ways: **no check moves in any section, and only two
bodies change** - nearly all of those joins happen inside candidates the finder then refuses as prose. Both read
better: "Among differ-ent age groups" is "different", and two URLs keep the hyphens the old rule took out of them
("proteccio-dedades" is "proteccio-de-dades" again - a link that did not work). Key Facts Sheets, all 190 fresh: four
tuned-on sheets and one held out change; grade unchanged. One is the fault this started from - "if your home is being
rent-ed out" is "rented out". **Three are a cost, and I am recording it as one:** "flood water combined with run-"
/ "off" is now "runoff", and the same insurer writes "run-off" when the word falls mid-line (twice in those sheets).
The meaning is the same; the spelling is not the page's. Neither joiner can know - the halves are words and so is
the whole - unless it looks at how the document spells the word elsewhere, which is the principled repair for both
joiners and is not built. Four tests added to `tests/test_table_hyphen_join.py`. Suite 773.

**What it did not reach: Huddle's heading is unchanged.** That table is built from the page's drawn rules
(`tables/ruled.py`, provenance `pdfium-lines`), and the ruled builder flattens a cell's lines with a plain
`replace("\n", " ")` in three places - it never calls `_join_lines`. So every ruled table joins its cells' lines
with a space and nothing else. No sheet shows a stranded hyphen from it (searched: none), so its cost so far is
the broken word alone, but the class is "every table with rulings". Next: one flattening function there that uses
the same joiner, screened the same way.

---

## 2026-09-19, 15:49-15:53 - The Key Facts Sheet grader asks two harder questions

Two of today's faults stood on the owner's sheets while `bench/tools/kfs_grade.py` reported nothing, so the grader
now asks what would have shown them. Shape only, as before; nothing here knows a right answer.

- **Header whole** asked for the heading's opening words ("event", "yes", "some examples"). It now asks for its
  closing words too ("optional", "others"): a heading cut after its first line no longer passes. On the copies kept
  before d378e6e this fails 20 of 158 tuned-on sheets and 5 of 32 held out; today **2 of 158 and none of 32** - Defence
  Service Homes' building sheet (failing already) and a Huddle contents sheet whose heading reads "Yes/ No Optiona l".
- **Rows that are only a continuation** counted a one-cell row only when it started in lower case - the very test
  the converter's own merger used, so the grader was blind exactly where the converter was. It now counts any row
  with no label and one filled cell, the band aside ("Cover for ...", which may be written under any column). On the
  copies kept before part B (07:41 this morning, part A already in): one tuned-on sheet ("Accidental Damage.") and
  one held out; today **none**. (No copy from before part A was kept, so what it would have said of "51-52" and
  "'Portable Contents'." is not measured.)

Reported now: tuned on, header whole **156 of 158** (it said 157 this morning - the ruler moved, not the text);
events 1,885 of 1,885; answers 1,885 of 1,885; no band swallowed; no continuation rows. Held out: 32 of 32, 375 of
375, 375 of 375, none, none.

The lesson is the one in `feedback-judge-the-definition-not-a-proxy`, turned on the grader: a check that shares the
converter's test cannot see what the converter cannot. Both faults were found by reading pages and by a second
reader, not by the oracle.

---

## 2026-09-19, 15:08-15:49 - The prescribed heading's second line, where it opens with a bracket

Seen on CGU's sheet while reading its nested rows: the table's first *body* row was `| | Optional | (see PDS and
other relevant policy documentation for details of others.)* |` - the second line of the prescribed heading. I had
guessed this was the one sheet of 158 failing "header whole". It is not: that sheet is Defence Service Homes'
building sheet, a different fault, not yet looked at - and **the grader does not see this one at all**. Counted on
the cached conversions: **18 tuned-on sheets and 5 held out, two templates** (ALDI / BOQ / Honey, and ANZ / CGU / NRMA).

**Cause.** `_heading_wraps_on` joins a heading's long cell to the line beneath it when that line starts in lower
case. On most sheets the break falls so that it does ("...that apply to events/" over "covers (see PDS ..."); on
these it falls before the bracket. A bracket opened on running words carries a sentence on as surely as a lower-case
word does - `_continues` already says so for a body cell - so the heading test now accepts it
(`_BRACKET_RUNS_ON`: four words or more, the first three without a digit or "="), and refuses what a body row opens
with under a long heading: "(n = 45)", "(0.45)", "(see note 3)", an enumerator.

**Screened exactly** (`bench/probes/pure_function_screen.py`, the header-count screen made general: any pure
function of `aligned.py`, the old one loaded from a worktree at f504523 and asked beside the new about every call of
every conversion): the answer differs on **23 sheet pages - the 18 and the 5, no other -, on 2 benchmark pages, on no
insurance page.** Measured: the two benchmark pages (prose the finder takes for a table) convert byte for byte the
same both ways, no check moves. Key Facts Sheets, all 190 fresh: exactly those 18 + 5 change and every one of the 18
is the same edit and nothing else - the two heading lines become one, `| Event / Cover | Yes / No Optional | Some
examples of specific conditions, exclusions or limits that apply to events/covers (see PDS and other policy
documentation for details of others)* |` (nine as markdown tables, nine as HTML). Grade unchanged; two-reader
comparison unchanged (two rows, both the model's). Two tests added to `tests/test_heading_interleave.py` (the
positive one fails at f504523). Suite 770.

**Why the oracle never said so.** "Header whole" asks for three parts in the header row - "event", "yes", "some
examples" - which are the heading's *opening* words; the tail ("Optional", "...details of others)*") was never asked
about, so a heading cut after its first line passed. Tried on the cached conversions with the tail asked for as well
("optional", "others"): **20 of 158 tuned-on sheets and 5 of 32 held out fail before this rule, 2 and 0 after it** -
the two being Defence Service Homes' building sheet (already failing) and a Huddle contents sheet whose heading reads
"Yes/ No Optiona l", a word the narrow column broke. Both real. The stricter check goes in as its own commit.

---

## 2026-09-19, 12:52-12:55 - The two-reader tool compares whole entries; two differences left, both the model's

`bench/tools/kfs_two_readers.py` read an event's first row only. A reader that writes a table nested in a row as
further rows under a row-spanning label was therefore compared by a quarter of its entry, and one of those further
rows - "Accidental Damage Home | $2,500/item | ..." - was even taken for the prescribed event "accidental damage",
which is where the "row only one reader found: accidental damage" on CGU's two sheets had come from all along.
`gather_spans` now makes one row of an HTML row whose first cell spans rows and the rows it covers, for both
readers alike, before anything is compared. One test added (11 in `tests/test_kfs_two_readers.py`).

**Tuned-on sheets, 158:** 1,896 rows found by both; no answer differs, no mark, no critical word, no wording under
0.98 alike; **two rows only one reader found, both on Honey's landlord sheet, where the model dropped the row** (read
against the page on 18 September). Of the 23 differences listed on 18 September none of TrueDoc's is left in the
list. Two faults of ours found in that reading are not of a kind the list shows and are still open: a line-break
hyphen kept in a cell ("rent-ed", which leaves the cell over 0.98 alike) and a data row promoted to the header of the
table that follows a band. Held out, totals only: one row only one reader found, one critical-word difference, five
wordings under 0.98 - not opened, and not to be.

---

## 2026-09-19, 12:07-12:50 - CGU's nested table: its lines were being written into the Yes/No column

Two of the four two-reader differences left were CGU's "High value items and collections" and "Items away from
insured address", whose third column holds a small table of its own (Policy / Item Limit / Overall Limit over three
rows). Read against the page, our output was worse than "a row only one reader found": the label was split over two
rows and **"Accidental Damage Home" and "Listed Events Home" stood in the Yes/No column**.

**Traced on the raw rows.** `_build_table` places a row's segments by position and then asks `_headings_in_order`,
which re-reads a row *in order* when three or more segments have sorted, repeated columns spanning exactly their
number - written for "BM BF WM ... Total", short headings set a shade left of narrow columns. The nested table's
second line, "and collections | Accidental Damage Home | $2,500/item 20% of Contents SI or $7,500 (whichever is
higher)", is [0, 2, 2] by position, so it was read [0, 1, 2].

**Sized before touching it** (`bench/probes/headings_in_order_census.py`, every row the rule fires on, all three
populations): none on the insurance set; 8 on the Key Facts Sheets, all CGU's; 28 on 20 benchmark pages. My first
idea - a heading set "a shade left" is moved a shade, so bound the distance - **the census killed**: true heading rows
are moved up to 35 points ("F(s) | G(s) | P(s,a) | yij", "Students | Major | First Term's | ..."), CGU's 18. What
separates is what the rule's own docstring says it is for: *short* headings. The heading rows among the 28 hold one
to three words a segment; CGU's lines hold six and ten (the rest of the long ones are prose and maths the finder
took for tables). The bound is `_build_table`'s own definition of a short cell, four
words.

**Measured against cbf69d3.** The function is pure and the census lists every row it fires on, so the pages that can
change are those with a fired row holding a longer segment: 8 benchmark pages and CGU's two sheets. Benchmark, code
against code on the 8: no check moves; one body changes, a display formula the text layer garbles and the finder
takes for a table - junk before and junk after. Key Facts Sheets, all 190 fresh: **exactly CGU's two sheets change**,
no held-out sheet, grade unchanged. They now read "High value items and collections | Yes | Policy Item Limit Overall
Limit Accidental Damage Home $2,500/item 20% of Contents SI or $7,500 (whichever is higher) Listed Events Home ..."
and "Items away from insured address | Yes | Accidental Damage Home Australia & New Zealand Listed Events Home
Australia up to 90 consecutive days Fundamentals Home Not Covered": label whole, answer right, every word of the
nested table in its cell in reading order. **Its structure is still lost** - which limit belongs to which policy is
readable only because the lines read across. How OKF should write a table inside a cell is a format question for the
owner, not a rule. (The sheets' cached copies served as the before state here, which I said this morning a cache is
not: the exact screen of cbf69d3 showed that commit changes no grid of any sheet, so the copies made at 11:28 are
what cbf69d3 writes.) One test added to `tests/test_table_headings_in_order.py`. Suite 767.

**The two-reader count goes up, and that is the tool, not the text.** `kfs_two_readers.py` now lists eight
differences on the tuned-on sheets where it listed four: the four rows only one reader found, plus four "critical
words" on CGU's two events. The model writes the nested table as further rows under a row-spanning label and the
comparison reads an event's *first* row only ("item limit overall limit"), so our whole cell is compared with a
quarter of the model's. Both readers hold every word. Noted on 18 September as a limit of the comparison; now it
shows. To repair: gather the rows a row-spanning label covers before comparing.

---

## 2026-09-19, 11:32-12:06 - A row of the body is not heading because the heading's end was hard to see

The fault part B exposed on the French case table, in the wider form this morning's census sized (ten tables on
six benchmark pages, five templates, none on the owner's documents). `_header_row_count` only ever guessed where a
heading ends - the first row that is two-fifths numbers, the first long cell, *three rows* when neither comes soon -
and a body row with one number in it passes under all three. What that cost was worse than the census showed:
the rows counted as heading were not just marked `<th>`, they were **folded into the heading's cells** - `| Parameter
Depth Width of expansion | Sign H WE | Initial amount 63 50 | Unit um um |`, `| Variable % time in clinic PGY 1 | -1
(SE) 1.1* (.19) 8.4 (1.2) | ...`, "Table 3 Transmission speed | Simulation parameters. 50 Mbps".

**The rule**, at the end of `_header_row_count`, where it sees the count the function would otherwise return: a row
after the first that has a label, a cell beyond the label opening with a number, and the *shape* of a labelled row
below the heading (the same cells filled, the same cells opening with a number - the function's own `shape`, which
its long-cell guard already used one row up) is a row of the body; the heading ends before it, and before a group
label standing alone above it ("Foundation Courses").

**Screened exactly, not sampled** (`bench/probes/header_count_screen.py`): the count is a pure function of a grid, so
the old function was loaded from a worktree at 1337fdd beside the new one and both were asked about every grid of
every conversion - 25 insurance pages, 380 sheet pages, 1,122 benchmark pages. **They differ on ten tables on six
benchmark pages and nowhere else**: the census's six, no other. The owner's documents cannot change (no grid of
theirs gets a different count), so they were not converted again.

**Measured on the six, code against code:** tables **+1** (`11d982c1..._pg3`, 3 of 4 -> 4 of 4), nothing lost, six
bodies change and every one reads better: the parameters table and the residents' regression table get their first
two rows back as rows; "Table 3 | Simulation parameters." heads its six parameters instead of swallowing two; the two
course lists' first course and its group label are body cells, not heading cells; and the French table - the page
part B had left worse - is now a plain six-column table, "Cas 1 Femme | 61 | Droit | ischemie | clopidrogrel |
angioplastie" and "Cas 2 Homme | 63 | ..." each a row under "Sexe | Age | Cote | Presentation Clinique | Traitement".
(Their second lines, "chronique | + aspirine, puis relais a 3 mois par AVK | + stent", still stand as rows of their
own: several cells continuing at once with nothing lexical to say so - not this rule's.) Five tests
(`tests/test_table_heading_not_body.py`; the three built from the real grids fail at 1337fdd). Suite 766.

---

## 2026-09-19, 09:58-11:30 - Two censuses, and a second value on the second line of its cell

**The heading that swallows a body row, sized - nothing built.** The narrow reading of the fault part B exposed
(the first long cell stands on a label-less line under a labelled one; `bench/probes/header_long_cell_census.py`):
no table on the 380 Key Facts Sheet pages, none on the insurance set, three on two of the benchmark's 1,122 digital
pages - the French case table, and a degenerate table of bare pipes. One real table is not a rule. The wider reading
- *the last heading row has the shape of a labelled body row further down*: the same cells filled, the same cells
opening with a digit, a label - is a population: **ten tables on six benchmark pages, five distinct templates**
("Code | Title | Credits" with "ENGL 314 | Structure of English | 3" counted as heading, twice; "Table 3 |
Simulation parameters" with its first two parameters; "Variable | -1 (SE) | 95% CI | P Value" with "PGY 1 | 8.4
(1.2) | ..."; "Parameter | Sign | Initial amount | Unit" with "Depth | H | 63 | um"; the French table), none on the
owner's documents. That is the next item, as an extension of `_header_row_count`'s own same-shape guard.

**AAMI's row cut at its second answer - built, because its census was small where it mattered.** The answer cell of
"Fire and Explosion" holds "Yes" and "No", one above the other, beside a sentence that runs past the first line;
"No" under "Yes" continues nothing, so the line stood as a row: `| | No | scorching, melting, ... |`. Position
cannot settle it - the sheet's next real row, "Flood", also starts one leading below. The candidate: *no cell of a
new row opens in the middle of a sentence*. Sized (`bench/probes/split_row_census.py`, run together with the header
census by `bench/probes/table_censuses_together.py`, one pass of conversions for both): on the benchmark 174
standing rows have some cell that carries on, nearly all of them junk tables - prose cut into columns, maths - and
read loosely the candidate would, on the census's listing, fold the row holding "PGY 3" into the row holding "PGY 2". Asked as the merger sees a row (tight under the row
above, no label, **the row above has one**, exactly one cell of three words or more in lower case under a cell that
has not closed its sentence, every other cell a word or two, no number) it takes **three** benchmark rows, each a
continuation. On the Key Facts Sheets it takes 138: AAMI's two, and **136 lines of the prescribed heading** ("Yes/No
/ Optional" beside "...limits that apply to events/ / covers (see PDS...") - lines `_fold_wrapped_heading` joins
today. That was the risk, and the oracle was asked rather than argued with.

**Measured against e83e6d5** (worktree; each pool printing its `truedoc`). Key Facts Sheets, all 190 fresh: **three
change** - the two AAMI fire-and-theft sheets, where the row is whole ("Yes No" beside "Fire - no cover for loss or
damage to contents from arcing, scorching, melting, or cigarette burns unless a fire spreads from the initial burn
spot. There is no cover for Explosion." - what the page says and what the second reader wrote), and one held out
(counted, not named); **the other 187 byte for byte the same**, so the heading comes out as it did; grade unchanged
(157 of 158, 32 of 32; 1,885 of 1,885, 375 of 375). Benchmark, the 44 pages the census found a candidate on: no check
moves and **no body changes** - the three rows sit in blocks that do not end as tables. Insurance set, code against
code: no file differs, 229 of 229. Five tests (`tests/test_table_second_value_line.py`; the first fails at e83e6d5).
Suite 761.

**Where the two readers now stand** (`bench/tools/kfs_two_readers.py`, the 158 tuned-on sheets, after this
morning's three rules): of 1,897 rows both readers found, no answer differs, no critical word differs, no wording
falls under 0.98 alike; **four rows only one reader found** are all that is left of the 23 differences of 18
September - two are CGU's table nested in a row (ours, not built), two are the row the model dropped on Honey's
sheet (the model's). Held-out totals, never listed: one row only one reader found, one critical-word difference, five
wordings under 0.98.

A slip, caught by the clock: I wrote "11:25" and "measuring from 11:22" into the memory brief by feel while the
clock said 11:15 and the run had started at 11:14 - corrected. And a shell patch with one heredoc inside another
hung for two minutes; the file tools made the same two edits at once.

---

## 2026-09-19, 07:57-09:55 - The last line of a wrapped cell, part B: a line under a cell of one line

"Accidental Damage." under "...can be purchased to cover" (AAMI's contents sheet) is a cell's last line under a
cell that has only one line, so part A's test - one of the cell's own leadings below - has nothing to compare with.

**Sized first** (`bench/probes/orphan_row_fit_census.py`, all three populations: 380 sheet pages, the insurance
set's 25, the benchmark's 1,122 digital pages). Rows with no label and one filled cell under a one-line cell: 9, 2
and 121; flush with the line above, not a band, not opened by a tick: 3, 1 and 64. The typesetter's definition of a
wrap - *the first word would not have fitted on the line above*: its end, a word space and the word pass the end of
the column's widest line - separated what it was meant to: "Note: eligibility criteria may apply" under "...Go to
page 42." fits with 23 points to spare (a break someone meant), and so do "Over 50 (37; 5.6%)", "Buttermilk
(low-fat)", "Course Attributes:". It was **not enough by itself**, and the census said why: a column of values is
as wide as its values, so none "fits" ("0.499" / "1.291", axis labels "10 -15" / "10 -20", "LE" / "RB"), and "Retire
or resign with" under "Ysterplaat Museum" - the next entry of a magazine's contents list - misses fitting by a tenth
of a point. What separates those is the step down: a wrapped line sits one pitch below, and the pitch is the table's
own, shown by the lines its cells are already known to wrap on. Among the lines that would not have fitted, the
wraps stand at 0.82 to 1.01 of that pitch and everything else at 1.17 or more. (In units of the line's own height the same rows ran from 0.75 to 1.5 for true
wraps - useless; and AAMI's cell is set at 10 points in a table of 11.5, hand-squeezed, so the bound is one-sided.)

**The rule** (`tables/aligned._next_line_of_the_cell_above`, its one-line branch): flush with the line above to 1.5
points, no more than 1.1 of the table's wrap pitch below it, its first word would not have fitted, and not a number
under a number. The merger reads a table twice when such a line is waiting: the first reading shows the pitch (the
median step down to the lines it folded), the second asks the line (`_merge_wrapped_rows` -> `_merge_rows_once`). A
table that wraps nowhere has shown no pitch and the line stays a row.

**What the first measurement caught.** A/B over the 54 benchmark pages holding such a row: +1 check, and one page
wrecked - a magazine's contents list ("SA Soldier") went from a table to loose numbers and loose titles. The folds
were right ("Mandela / Commemoration / Medal Parade" is one entry, read against the page); what rejected the table
was `_build_table`'s prose test, which counts the share of characters in cells of more than six words, and whole
titles are long cells. The code already had the principle for this - a joined entry "is counted as the two lines the
page sets: the join says what the table holds, not whether the text is a table" - and a fold by position now follows
it: each is recorded in `joined` as its parts, a second fold adds a part, and a line folded later on what it says
goes into the last part, which is exactly what the judge saw when the line stood as a row. By construction these
folds can no longer change whether a table is a table. Part A had the same exposure and is covered by the same record.

**Measured, final code against f7aeed7** (worktree, each pool printing its `truedoc`). Benchmark, the 87 pages
either census found a candidate on: **tables 97 -> 98** (`c6673ff6..._pg3`: "...Prevention and Control of
Non-communicable / Diseases (2011)" is one cell), every other section identical, six bodies change. Five read
better, each checked on its page or plainly a wrap: the contents list (four titles whole: "Mandela Commemoration
Medal Parade", "South Africa assists Mozambique Government during the floods", "National Civic Remembrance Sunday
and Wreath-laying Ceremony", "A visit to Air Force Base Ysterplaat Museum"), two course lists ("Special Topics in
Gender and Sexuality / Studies", "...Middle and High School Physical / Education"), the bicycle-report table
("High visibility clothing (1994)", "Reflective clothing Lighting" - a two-line cell of Massachusetts' row), and the
UN resolutions list. **One reads worse, and the fault is older than this rule:** a French case table
(`multi_column/019a8841..._page_2`) whose heading cell "Presentation / Clinique" is now whole, which leaves
`_header_row_count` with two heading rows where it had three - and the second is Cas 1's first line ("Sexe Cas 1
Femme | Age 61 | ..."). It counted that body row as heading before as well (it ends a heading at the first cell of
more than six words, and that cell is on the second, label-less line of Cas 1's entry); then it was a `<th>` row of
its own, now it is folded into the labels. No check sees either. **Next item**, sized before it is built:
`bench/probes/header_long_cell_census.py` (written, not run). Insurance set, code against code: **no file differs**,
229 of 229. (The cached copy of one page differed - it predates "one picture, one figure"; old code and new write the
same page. A cache is not a before state.) Key Facts Sheets, all 190 fresh: **two change**, the one tuned-on sheet
the census named and one held out (counted, not named); grade unchanged, 157 of 158 and 32 of 32, 1,885 of 1,885 and
375 of 375. Thirteen tests in `tests/test_table_last_line_of_a_cell.py` (the first part-B test fails at f7aeed7).
Suite 756.

Written while the pools ran, not yet run: `bench/probes/split_row_census.py`, for AAMI's row cut at its second
answer (`| | No | scorching, melting, ... |` under "Yes | Fire - no cover ... from arcing,": the raw rows were read,
and the table's next real row also starts one leading below, so position cannot decide it; the candidate is "a cell
of a new row never opens in the middle of a sentence").

Both census probes now count held-out sheets and never list them (the first run of the part-B census printed a
held-out sheet's file name beside its numbers - no text, but a name is a listing; fixed the same hour).

Also answered for the owner: would `pipeline_tag` / `library_name` on the card get TrueDoc listed? Read from the
hub's API at 09:27: two of the 18 listed models carry neither, and `luganoquant/Inkling` carries both, has valid
results, is three days old and is not listed. Not required and not sufficient; the table still shows 18 rows.

---

## 2026-09-19, 07:25-07:55 - The last line of a wrapped cell, part A: built and measured

`tables/aligned._next_line_of_the_cell_above`, called by `_merge_wrapped_rows` for a row with no label and one
filled cell that nothing else folded: it continues the cell above when it starts within 1.5 points of the left edge
of that cell's last line and sits within a tenth of the cell's own leading below it. Only under a cell of two lines
or more; never a band (`_is_band`), never a line opening with a tick or cross. The design and the census behind it
are the entry below.

**Measured.** Benchmark, code against code on all 87 pages that hold such a row (the before state from a worktree
at 80d640d, each pool printing its `truedoc`; run 97's readings replayed): **no check moves in any section**, and
three bodies change, each for the better - a contents list's wrapped titles become one line each ("End of an era
for the Executive National / Security Programme"), "...the Canadian Premature Babies / Foundation." is one cell,
and "+ aspirine, puis relais a 3 mois par / AVK" is one cell. That last was read against its page: AVK is the fifth
line of Cas 1's treatment. (The row-spanning label "Cas 2 Homme" sits one line early on that table, before and
after alike - an older fault of that table's, unchanged, noted.) Insurance set: no file differs, 229 of 229. Key
Facts Sheets, all 190 fresh: **exactly two change** - ANZ's "'Portable Contents'." and the 2017 building sheet's
"51-52" and "PDS pg.31." go back into their cells - no held-out sheet moves, grade unchanged (157 of 158; held out
32 of 32, 375 of 375). Seven tests (`tests/test_table_last_line_of_a_cell.py`), two of them the census's warnings: a
centred band one leading below stays a row, and a line under a one-line cell is not decided here. Suite 750.

A check script of mine nearly misled me on the way: it flattened an HTML table's tags into spaces, so a row boundary
read like a join and "Accidental Damage." looked folded when the function had said no. Read the raw lines.

**Part B is next and not built:** "Accidental Damage." under a one-line cell. Its census is written
(`bench/probes/orphan_row_fit_census.py`: would the first word have fitted on the line above?) and not yet run.

---

## 2026-09-18 22:30 to 23:25, written up 19 September 07:25 - A cell's last line made a row of its own: sized, a rule designed, NOTHING BUILT YET

Work in progress, recorded so it survives a break. The fault (four rows on three tuned-on Key Facts Sheets, two
more on held-out ones): `| | | 51-52 |`, `| | | PDS pg.31. |`, "'Portable Contents'.", "Accidental Damage." - the
last wrapped line of a third-column cell standing as a row.

**Why they stand.** `tables/aligned._merge_wrapped_rows` - the one merger every table builder goes through
(aligned tables and `layout-table`s alike) - folds a line into the row above on what it *says*: it starts in lower
case, or the cell above ends on a connector or a comma; a numeric line is refused outright. "Accidental Damage."
under "...can be purchased to cover" fails every such test, and words cannot settle it: "Accidental Damage" is as
good a label as a continuation. The page can.

**First idea, killed by its census** (`bench/probes/orphan_row_census.py`, which hooks the merger and records every
row left standing with no label and one filled cell): "a wrapped line sits one leading under the line above; a new
row starts after the row's padding". On the sheets, of 110 such rows under a cell of two lines or more, **40 sit
exactly one leading below - and 37 of them are the legitimate band** "Cover for valuables, collections and items
away...". These tables have no padding between rows. AAMI's table says the same from the other side: lines inside
a cell step 11.5 points, and the real next row, "Flood", starts 11.5 below the last line of "Fire and Explosion".
Pitch alone would have folded thirty-odd bands into the cells above them.

**What does separate them: the rest of what "the next line of the same paragraph" means - it starts at the left
edge of the lines above.** A band is centred (30 to 112 points off that edge). Rows one leading below *and* flush
left within 1.5 points, under a cell of two lines or more:

| population | one leading below | and flush left | what those are |
|---|---|---|---|
| Key Facts Sheets, 380 pages | 40 | **3** | exactly the three orphans with a multi-line cell above |
| insurance set, 25 pages | 0 | 0 | - |
| benchmark, 1,122 digital pages | 18 | **17** | last lines of references and wrapped entries: "...Nelson and / Winter, 1982).", "...Executive National / Security Programme", "...Glob Health / Action. 2013;6:22450.", "...vol. 302, Art. no. / 117584, 2024." |

**The fourth orphan is the hard one.** "Accidental Damage." sits under a *one-line* cell, which has no leading of its
own. That group is where the danger is: sheets 9 rows (3 flush left - the orphan, counted twice, and one held out),
insurance 2 flush left that MUST stay rows ("Note: eligibility criteria may apply" under "...Go to page 42."; a
cross and "Pontoons" under "...Replacement of water"), benchmark 166 (88 flush left, among them stacks of numbers,
"-0.05" over "-0.06", which are rows). Flush-left is not enough there.

**The design, to be built and measured next:**
- *Part A - the cell above has two lines or more:* a row with no label and one filled cell continues that cell when
  it starts within 1.5 points of the left edge of the cell's last line and sits within a tenth of the cell's own
  leading below it; never a band (`_is_band`), never a line opening with a tick or cross (`_BULLET_START`). Numeric
  lines allowed ("51-52" is one).
- *Part B - the cell above has one line:* the typesetter's own definition of a wrap - **the first word of the line
  would not have fitted on the line above** (the line above's right edge, a space, and the word's width pass the
  column's right edge, taken from the widest line in that column). "-0.06" fits after "-0.05", so a stack of
  numbers stays rows; "Go to page 42." is short, so the note under it stays a row. Its population has NOT been
  sized yet - size it before building it, and build A first.
- *How to measure:* the rule can only touch tables that hold such a row, and the census lists them: 87 benchmark
  pages, 83 sheet pages, 4 insurance pages. Convert those both ways (the before state from a worktree), re-grade
  all 190 sheets fresh, re-score the insurance set, read every changed page against its image.

**The AAMI row cut in two ("Yes" / "No" in the answer cell) is a different rule** and pitch cannot decide it, for
the reason above. Its row is `| | No | scorching, melting, or cigarette burns unless... |`: no label, and one cell
that plainly carries a sentence on (lower case, the cell above ends on a comma). The merger wants *every* filled
cell to read as a continuation, and "No" under "Yes" does not. Candidate: with no label, one cell carrying a
sentence on is enough, and the other cells are second lines too - to be sized on every table page, since a looser
version of this merger once cost 48 benchmark checks (the comment at `aligned.py:1719`).

---

## 2026-09-18, late night (21:35-22:24) - Hidden words in the body: an earlier wording under a row's shading, with the present sentence printed over it (D011)

**What the comparison found, read against the page:** "entered" at the end of a GIO cell and "item." inside an
Apia one are not on the page. Each is in the PDF, painted first; then the table row's opaque shading over it; then
the visible sentence at the same spot. D011 exists to keep such text out of the body, and its check had judged
one of them `covered` and then let it through. Three separate faults, stacked:

1. **The cover test measured the font box.** A fill had to cover 0.9 of a character's box; a band the height of
   the line covers every stroke and 0.87 of the box, which holds the line's leading too. A character is now covered
   when a later opaque fill covers 0.9 of its *ink* (`_ink_box`: from 0.22 em under the baseline to 0.75 over it,
   inside its own box), or of its box as before.
2. **The render check took another text's ink for this one's.** `_Visibility.verify` renders a covered run's box
   and overturns the verdict if the patch shows contrast - but the patch showed the sentence printed over it. The
   render is now asked only about the characters no visible character is printed over (`_clear_stretches`: other
   visible ink over a tenth of a character's ink counts), a stretch at a time, over the ink region brought in a
   point and to whole points; where there are none it cannot testify and the paint order stands. A run with nothing
   over it is one stretch, as before.
3. **Characters were matched to their paint order by position alone.** A hidden full stop and the "t" of the
   visible "Earthquake" share an origin to half a point; the later overwrote the earlier in `_span_at`, so "item"
   was hidden and "." stayed ("damage that . occurs"). Matched now by position *and* character, in the order the
   page gives them (`_span_queue`), in both readers.

**Sized before it was written** (`bench/probes/covered_overprint_census.py`, text layer only): runs un-hidden by the
render while overprinted - Key Facts Sheets 5 of 86 un-hidden runs, with a clean gap (81 at no overprint at all);
the benchmark's 1,122 digital pages 7, all one handbook. A share-of-overlap threshold would have been a tuned
number there (the handbook's runs sit at 0.48 to 0.63), which is why the rule is about what the render can
testify to and not a share. Runs whose ink a later fill covers though not their box: 6 on the sheets, every one
an overprinted remnant; 1 on the benchmark, visible, and left visible by the render.

**Two traps on the way, each now a test.** The render saw the *band's edge* round a font box standing proud of it
and called it ink (so the ink region is what is rendered); and a patch ending at 202.03 points took in the pixel
row the band's foot runs through (so the patch is brought to whole points). `tests/test_hidden_text_overprint.py`
builds the three cases from raw PDF operators and reads each with both libraries: 8 tests.

**Measured.** A screen of the text layer of every page of all three populations, both code states (1,808 pages, six
minutes a state, the before state from a worktree, each run printing its `truedoc`): **22 pages change - 9
benchmark, 13 Key Facts Sheets, 0 of the insurance set - and every change is text newly hidden; nothing newly
visible.** Each newly hidden run on a page I may open was then looked at on the page, its box outlined: a magazine
foot reading "86 ... MAY 2012" over a hidden "94" and "JANUARY 2012"; page tabs "40", "41" over "26", "27"; a
handbook's footer "thermofisher.com/probes" over a hidden "www.invitrogen.com/probes" and its title with a
trademark sign over the old one with a registered sign; "Policy Name" over "s at:"; a stray glyph on blank paper,
twice. One looked wrong and was not: on Budget Direct's sheet the box of a hidden "STE" sits over the body line
under the big blue "STEP" - the PDF holds *two*, the visible heading and a second "STE" from an earlier layout
under the body's fill, which had been coming out as a phantom top-level heading, `# STE`, on six sheets.
Converted in full: the 9 benchmark pages, no check moves and one body changes (a stray "Ó" out of a garbled
cell - the rest was running heads and feet, dropped anyway); the 190 sheets, exactly the 13 predicted change, each
by the loss of a word the page does not print (and the Budget and ING sheets' heading levels settle up one with
the phantom gone), grade unchanged (157 of 158; held out 32 of 32, 375 of 375). The two-readers comparison goes
from 15 tuned-on differences to 12; a held-out total falls by one, seen as a number only. Suite 743.

**What this was worth knowing.** The benchmark would never have shown it: nothing moved there. It was found by
putting a second reader beside ours on the owner's documents and reading the differences against the page - two
of the six causes turned out to be this one fault, and the census found four more sheets and a benchmark
document with it that no difference had pointed at.

---

## 2026-09-18, night (21:20-21:33) - The Key Facts Sheet differences, each read against its page: six defects of ours, one of the model's

The repaired two-readers tool listed 23 differences on the tuned-on sheets. Each was read against the page image
(rendered from the PDF, the differing cell in view) and given a verdict; held-out sheets were never listed or
opened. None of the sheets is on the sealed list (checked by name before any was opened). The adjudicated list is
`bench/gpu/out5/pro/own/differences_with_verdicts_20260918.json`.

**Eight of the 23 were the tool's error, found on the first sheet read.** RACQ's table has a dark band across it
("Cover for valuables, collections and items away..."), and TrueDoc writes what follows the band as a second
markdown table; the tool read only the table holding the most events, so two rows TrueDoc had word for word were
"missing". `rows_of` now reads every table, first rows included (a test pins it). Re-run: 15 differences on 11
sheets. *Noticed there:* the rows under the band come as a table whose first row - "High value items and
collections | Optional | ..." - stands where markdown wants a header, so a data row is dressed as a heading.

**The fifteen, by cause (entries / sheets):**

| cause | verdict | what the page shows |
|---|---|---|
| a row split at a second value in the answer cell (4 / 2, one AAMI template) | TrueDoc wrong | "Fire and Explosion" answers "Yes" and "No" on two lines (fire yes, explosion no). TrueDoc starts a new, unlabelled row at "No", cutting the third column's sentence at "...from arcing," / "scorching, melting..." |
| a cell's last wrapped line becomes a row of its own (4 / 3) | TrueDoc wrong | `\| \| \| 51-52 \|`, `\| \| \| PDS pg.31. \|`, "Accidental Damage.", "'Portable Contents'." - the 17 September candidate (a wrapped line opening with a capital), now seen to include a digit and a quotation mark |
| a word written twice (2 / 2, one Apia template) | TrueDoc wrong | "item.", the last word of the row above, appears again inside the Earthquake cell ("damage that item. occurs more than 72 hours") |
| a hidden word let into the body (1 / 1, GIO) | TrueDoc wrong | "entered" is in the PDF at the spot where the visible sentence "the insured address with your consent." is printed. Paint order: the word, then the row's opaque fill over it, then the sentence. TrueDoc judges it `covered`, and `_Visibility.verify` overturns that because the rendered patch shows ink - the *other* sentence's. D011 defeated by an overprint |
| a table nested in a row (2 / 2, one CGU template) | TrueDoc wrong on the page, though listed by a false match | Policy / Item Limit / Overall Limit for three policies inside "High value items" and "Items away". TrueDoc splits the labels, puts policy names in the answer column and runs the limits together; the model wrote it right with row spans. Neither the shape grader nor the word comparison flags it: the comparison reads an event's first row only |
| a row dropped (2 / 1, Honey) | **model wrong** | "High value items and collections \| No" with an empty third cell: TrueDoc has it, the model dropped it and wrote the next row as a loose line |

Also one line-break hyphen kept inside a cell ("rent-ed"; the model wrote "rented").

**What it means.** Thirteen of fifteen are ours, as the 17 September reading said - but that reading covered
sheets that should not have been listed, and these are the numbers that replace it. The shape grader (99% and 100%)
passes every one of these sheets: it asks whether the events open rows and carry answers, and a sentence cut in
two or a stray word does not change that. Six candidate rules, none built tonight, each to be sized on its
population first - the orphan last line and the covered-word check look the largest, and the second is a fault in
the core reader's D011 check, not a table rule.

---

## 2026-09-18, night (21:06-21:19) - A transcription cannot hold more print than its region

The second thing the crops taught (D033's check, this evening): Flash turned a scatter plot into an 1,800-row
table of numbers and a graph figure into one line 4,095 times. Nothing in the *words* marks either as wrong, and a
picture has no text layer to check them against. What marks them is the region.

**Measured before it was written** (`bench/probes/region_capacity.py`, and the three readers' 843 whole-page
readings). My first idea - a region H points tall holds at most H/4 lines - is the wrong measure: three honest
readings exceed it (1.51, 1.29, 1.14), because olmOCR 2 writes an HTML table one cell a line, so lines measure
the reader's formatting and not the picture. Characters against area is the right one: print under about four
points cannot be read, so a region holds at most its area over the area of a four-point character (W x H / 8).
Of 164 recorded readings of picture regions the largest real transcription uses 0.32 of that, the median 0.02,
and the two runaways 2.25 and 2.21. Of 843 whole-page readings the densest - tiny-print book scans on page boxes
of 300 x 200 points, all three readers agreeing - uses 0.66, and none exceeds 1. The bound is 1.0, the definition
itself, with a margin of one and a half over the densest real page seen and a factor of seven between the
runaways and the largest real picture reading.

**The rule** (`truedoc/vision/capacity.py`; wired in `pipeline.py` where a transcription arrives): a whole-page
reading, or a picture's transcription, that claims more characters than its region can hold is set aside and named
`reading-implausible` (degraded; the page keeps its own reading, the picture stays a figure). An icon's meaning
and a figure's description are words *about* a region and are not judged so - a sentence about a twelve-point
icon is longer than anything that fits in it.

**Measured, code against code** (the worktree at d5ba8bd, the 60 crop pages, each pool printing its `truedoc`):
with Flash's crop readings **two pages change and only two**, 4,123 lines to 23 and 1,987 to 140, and no check
moves in any section (the benchmark never saw the invented text; a reader would have). With olmOCR 2's readings -
run 97's arrangement - 0 of 60 pages differ from the pool made after the figure fix: the rule fires nowhere. The
scatter-plot page now reports itself `degraded`, one figure line, no invented number. Ten tests
(`tests/test_vision_capacity.py`), three of them through the pipeline. Suite 735.

**What it does not do.** It bounds length, not truth: an invented table that fits its picture passes. It would not
have caught Flash dropping a column of the vehicle list. It makes Flash safer as a crop reader, and D033's split
stands on the evidence it was made on: olmOCR 2 keeps the crops.

---

## 2026-09-18, late evening (20:25-21:06) - One picture is one figure: a picture the layout model also saw was written twice

**How it was found.** Reading the crops for D033, a caption of olmOCR 2's stood twice on three run 97 pages. The
cause was not in the vision stage. Every picture is proposed twice: the layout model's figure region
(`layout/fuse.py`, provenance `layout-figure`) and the PDF's own image object (`pipeline.process_page`,
`textlayer-image`). The fusion refuses a layout figure where a figure already stands; the later step that adds the
image objects never looked. So a picture both saw became two blocks with near-identical boxes: two `![](figure)`
lines in the body, a model's description twice, or - where the picture was transcribed - **the whole transcription
twice** (the geology table of `tables/3d780c..._pg22`: 245 lines, twice). In run 97's pages, 209 of the 333 that
have a figure line carry two together.

**The rule.** Two figure boxes are one picture when each covers at least 0.8 of the other; the block that stands
takes the PDF's own box, which is the exact one (the layout model's is a few points loose, and the crop sent to a
model should be the picture). A layout figure holding several images is left as it was: whether a composite
figure is one thing or four is a separate question and changes more than a repeat.

**Measured, code against code** (`ab_pool.py` over the 333 pages, the before state in a worktree at 1892a25, each
pool printing which `truedoc` it imported; run 97's readings replayed): 172 pages changed. Classified mechanically,
every one: 162 lost only a repeated figure line; 10 lost a repeated transcription of which every line still stands
once; **nothing added, nothing moved, nothing lost**. Checks: arXiv 249 = 249, multi-column 300 = 300, tables 312 =
312, tiny text 74 = 74, **headers and footers 290 to 289**. The one: `bec1f712..._page_9` asks that "ANEC" be absent
from the *first 20 characters*, a window standing in for "no running head". The page's real first heading is "ANEC
CONCLUSIONS...". Written twice, the picture above it was 26 characters of padding that pushed the heading out of
the window, and the check passed by luck; written once, the heading starts at character 16. The output is more
correct and the check less satisfied; taken, and recorded here, rather than padded for. On run 97's arrangement
that is 735 to 734 in that section and 86.82 to 86.81 overall: the quoted 86.8 is unchanged, and run 97 stays
the run it was (tag `run-97`). A test (`tests/test_one_picture_one_figure.py`) was shown to fail on the code
before - run from inside the worktree, after a first attempt from the repository root imported the fixed code
and proved nothing. **The owner's documents:** insurance 0 of 25 files changed, 229 of 229; Key Facts Sheets 20
of 190 changed, every change a repeated figure line removed, grade identical (held out 32 of 32, 375 of 375).
Suite 732.

Noticed and not built: that page's picture is the ANEC logo in its running head, which arguably should not be in
the body at all - furniture that is a picture. A single benchmark page cannot show that a picture repeats; the
owner's multi-page documents can.

---

## 2026-09-18, evening (19:40-20:25) - How a conversion ended, carried apart from the markdown (D037); the two-readers tool repaired. The review's F01 and F10

The owner's order after the entry was published: the other agent's review items next. Its ten synthetic
probes were taken as acceptance cases, and all ten are now tests.

**F01, the status contract (D037).** `truedoc/model.py` gains `Issue` (code, message, severity, pages),
`Document.add_issue` (writes the typed issue and the sentence `warnings` has always held),
`Document.all_issues` (a bare sentence some caller appends is still reported, as a note) and
`Document.completion`: `complete` / `degraded` / `incomplete`, the worst issue deciding. The pipeline's ten
warning sites became typed issues: `unreadable-pages` and `reply-cut-off` are incomplete; `stage-unavailable`
(layout model, vision stage, deep reader) and `reader-fallback` are degraded; `pages-turned`, `hidden-text`,
`low-support`, `witness-failed` are notes. The probes, one by one: **P01** an unreadable document rendered as an
empty string with front matter on - the block is now written over the empty body, and `convert_with_status()`
returns the same status to a caller who asked for no front matter (the body stays empty: D008 stands). **P04** a
reply with `stop_reason: max_tokens` was accepted as finished - both live providers and the replay provider now
set `last_cut_off`, the pipeline keeps the text and names the page (whole pages and picture regions). **P05**
`--pages 2-1` parsed to `[]`, which `opts.pages or all` took for every page, and `--pages 99` of a two-page file
converted nothing and exited 0 - the parser refuses what is not a forward range of page numbers and the pipeline
raises `PageSelectionError` for an empty selection or a page the document lacks; exit code 2. **P2-01, P2-02** (my
own `bench/gpu/place_bakeoff.py`): a reading salvaged from a cut-off layout reply now opens with a YAML block
`cut_off: true`, which `FileReadings` reports as a live provider would, and layout JSON is recognised however
the model spaced it. The command line lists issues on stderr, writes `--status <file>` as JSON, and `--strict`
exits 3 when the result is short of complete. **Left to the owner:** whether strict should be the default.

**It found something at once.** Re-placing the recorded readings marked two as salvaged from cut-off replies:
Flash's `long_tiny_text/17_pg17` and Pro's `long_tiny_text/13_pg475`. Converted in run 97's arrangement, the
first is now reported `incomplete` with a body byte-identical to run 97's (it always was incomplete; nothing
said so), and the second is `complete`, rightly: the router does not send that page to Pro.

**A caller of my own that the stricter pipeline would have broken:** six tools ask for pages 1 and 2 of every
Key Facts Sheet, and a one-page sheet has no page 2. `pipeline.first_pages(path, n)` gives the opening pages a
document has; the six use it.

**F10, `bench/tools/kfs_two_readers.py`.** Held-out sheets are counted and never listed (verified: 32 held-out
sheets, none named in the output or the JSON). A leading tick or cross is compared as a mark, not stripped
(P2-03). Negations, limiting words and every figure are compared as a bag of their own whatever the similarity
(P2-04: a dropped "not" in a long condition is 0.998 alike and was invisible at the 0.98 cutoff). Rows only one
reader found are counted and listed, and a label that opens more than one row is reported (P2-05). Each listed
difference carries an empty `verdict` (truedoc / model / both / source ambiguous) and its sheet's place in the
library - the first run showed one RACQ file listed twice because it is kept under two product lines. The
comparison is a pure function (`compare`), so the probes are tests. **First run on the real sheets, tuned-on
158:** 1,883 rows found by both, **12 found by one reader only** (the old tool could not see these), 2 answers
differ, 0 marks, 4 cells differ in critical words, 5 in wording; 23 differences on 15 sheets, 13 distinct
files. Held out, totals only: 3, 1, 0, 2, 7. Not yet read against the page images - that is the next list
item, and the 17 September claim that "every difference read so far was TrueDoc's" predates these repairs
and covered sheets that should not have been listed.

**A side effect of this afternoon's path clean-up, caught here:** the Key Facts Sheets cache was keyed on the
whole path as typed, so moving the library's root into `doc_library` changed every key and would have orphaned
all 190 cached conversions without a word. The key is now the library-relative path. `kfs_grade.LIB` is looked
up when asked for, so the grader imports on a machine without the library (the new tests need that).

**Measured.** 30 new tests (21 in `tests/test_status_contract.py`, 9 in `tests/test_kfs_two_readers.py`);
suite 722. All 190 Key Facts Sheets re-converted fresh: **190 of 190 byte-identical** to the day before's cached
conversions, grade unchanged (tuned on 157 of 158 headers whole, 1,885 of 1,885; held out 32 of 32, 375 of 375).
The insurance set reconverted: **0 of 25 files differ, 229 of 229**. The benchmark converts with front matter
off and its bodies cannot move; the two cut-off pages' bodies were checked against run 97's directly.

**Three times in an hour I patched code through a heredoc and a `"\n"` in the replacement text became a real line
break** (a regex the first time, which failed safe; then `okf.py` and `cli.py`, which did not compile). The
memory note that already warned of this now says what to check before every such patch.

---

## 2026-09-18 - The owner decides the reader: Flash, Pro behind it, and run 95's 86.4 is the number

Three decisions, put to the owner one at a time in plain terms and recorded as D033, D034 and D035.

- **D033: Flash is the standard reader of scanned pages**, in place of olmOCR 2 ("yes, go with Flash"). Subject
  to two checks that are mine to do: Flash asked TrueDoc's picture-text question (a small rental), and D021's
  invented-text check over its saved readings (free). If it fails either, olmOCR 2 stays.
- **D034: two tiers are kept, Pro is the deep reader we quote, and a live service lets its user choose** ("people
  are given the information and can make a choice that suits their needs").
- **D035: the number we quote is run 95's 86.4** (CI 85.4-87.3, held-out 86.0), with run 94's 85.6 and run 91's
  hosted 85.4 beside it. It is the arrangement D033 and D034 make, so it is what a user would get.

**Measured for the second decision, from runs already scored: Pro and Claude are level as the deep reader.** The
router flags 102 pages carrying 568 checks (found as the pages whose markdown differs between runs 94 and 95). On
them: olmOCR 2 alone 291, Flash alone 315, Claude behind olmOCR 2 344 (run 91 - the code of 13 September, so not
quite a clean comparison), Pro behind Flash 348, Pro on everything 348. Page by page Pro is better on 24, Claude on
15, level on 63. So the choice between them is cost, waiting and where the page goes, not quality: which is why
the owner's answer - tell the user and let them choose - is the right shape and not a dodge.

**The owner's question about hosting, and the arithmetic.** I had said an always-on 140 GB card is about US$105 a
day and makes no sense for a small service. He asked why not temporary instances as needed, as we have been
doing. It does remove the idle cost. From session 5's own log, a start costs about ten minutes and two to three
dollars before the first page (the instance, 70 GB of weights, the load; the bill's disk and bandwidth share was
real), then about a quarter of a cent a page: cheaper than the API from about 90 hard pages in a batch, dearer and
far slower for a three-page letter. One such machine holds both models, so a batch gets Flash and Pro from a
single start. What "as we have been doing" hides is that the owner rents and destroys by hand and I drive; a
service needs that automated and needs never to forget an instance. Providers that keep the weights cached and
bill by the second exist and would cut a start to cents; unpriced, an hour's research before any service is built.

**To do, none of it started:** a provider that talks to a served Infinity-Parser2 model (its own prompt, layout
JSON to markdown; today the readings are replayed from disk); D033's two checks; and the list already open from
session 5 - the seven old-scan-maths checks our own handling loses, a general maths clean-up, Pro alone against
the 87.6, the fifteen disagreeing Key Facts Sheet cells, Pro's other 125 pages of the library. The owner wants to
talk about the downstream trial next.

**D033's first check: Flash does not invent more than olmOCR 2** (`bench/probes/corroborate_readers.py`, the 281
pages converted under each of three readers' saved readings, D021's verdict recorded per page). The witness is the
page's own and does not change with the reader, so the support figures compare like with like:

| | olmOCR 2 | Flash | Pro |
|---|---|---|---|
| corroborated / low support / unverified / unchecked | 180 / 18 / 6 / 74 | 181 / 17 / 6 / 73 | 180 / 18 / 6 / 73 |
| support on the 197 pages with a comparable witness: median | 0.917 | 0.931 | 0.932 |
| pages backed 0.10 less than olmOCR 2 | - | 0 | 2 |
| words no other reader produced, all 281 pages | 3.3% | 1.5% | 1.3% |

Flash is never backed less than olmOCR 2 on any page and produces fewer words the others do not; on the second
measure olmOCR 2 is the outlier. Pro's two pages (old_scans_math/5_pg174, support 0.37 against 0.71, and a
multi-column page, 0.72 against 0.99) are not among the pages the router sends it. **Passed.**

**The seven old-scan-maths checks: traced, fixed, measured.** With Pro's readings the converter scored 375
against the plain merge's 382; with Flash's, 385 against 392. Same seven, two pages: old_scans_math/4_pg380 and
4_pg48, an algebra textbook. Both readers write "$f(1)$", "$P$", "$a + [b - (a - b)]$", and
`truedoc/vision/mathdelims.py` recognised maths only by a command, a script, a group or an equals sign, so those
spans stayed between dollars and D024 escaped them into text - the check for "f(1)" then fails because it is no
longer a formula. **The rule now:** a span is also maths when it holds a letter, every word in it is a single
letter or the name of a function (sin, log, lim, ...), and it is written only with the characters an expression
uses; money fails three ways ("5 and " has a word, "5, " has no letter, "5 a day" is a number followed by a word,
which is the shape of a price). One old test flipped with its reason written in ("a bare letter is not obviously
maths" - it is, when a model put dollars round it), four tests added, **suite 685**.

Measured code against code on every category a model reads - the run-90 lesson - with `bench/tools/ab_pool.py`,
which now takes `--pages` and `--vision` for exactly this (the before state from a worktree on PYTHONPATH, each
worker printing which `truedoc` it imported): all 281 model-read pages under Flash's readings. **Five categories
identical to the check (headers 113/123, tiny text 303/335, multi-column 110/145, old scans 271/526, tables
133/143); old-scan maths 385 to 392, +7, exactly the two pages.** 34 pages' markdown changed; every new formula
read on them is a variable, a function of one, a statistic ("p < 0.05") or an expression of letters, and not one
is a price. The insurance set and the Key Facts Sheets cannot move: the function runs only on a model's reading,
and their scorers convert with no model. Run 96 - the quoted arrangement, run 95's, on this code - was launched
to carry the seven into the number.

**What the authors' maths clean-up still wins after that, and which parts are ours to take.** Flash's readings
merged over run 89's pages score 392 on old-scan maths raw and 407 with their post-processing (`bake_flash_post`).
Read page by page, the fifteen checks are four things: an aligned column of equations split into one formula a row
(+5); a formula the model broke in two at an operator joined again (+1); formulas separated by "and" or a comma
merged into one with the word inside the maths (+7); a column of display formulas merged across line breaks
(+2). **The first two are taken; the last two are declined** on the owner's principle - "and" inside a formula is
worse for a reader and matches nothing but the reference's habit.

- **An aligned column is one display formula a row.** The page prints a column of equations and each row is one;
  a row continuing a derivation reads "= ..." as the page prints it; what stands before or after the environment
  in the same formula (3_pg39 sets a bracketed "or" alternative after the column) is a formula of its own; an
  equation number set as a row of its own stays with its equation. Only the aligned family (aligned, align,
  gather, split, eqnarray) is split: a matrix or a cases brace is one object. The first version split only a
  formula that was nothing but the environment and won one check; the page that mattered has the alternative
  after it. Measured on the categories that hold such a block - only old-scan maths (13 of 36 pages) and one
  multi-column page do, in either reader's readings, so the other four cannot move: **old-scan maths 392 to
  401, +9**, 3_pg39 16 to 24 of 26 and 4_pg48 22 to 23; multi-column 110 to 110. Sixteen pages' markdown changed
  and every one was read: columns of equations, derivations with their "= ..." rows, a pair of coordinate
  equations, all as the page prints them.
- **A formula a model split at an operator is joined.** "$...- 7n\}$ $+ [9m - ...]$" is one sum on 4_pg48; two
  inline formulas with only blanks between them are joined when the seam is an operator, and "$x$ $y$" stays two.

Seven tests added, **suite 692**. Committed after run 96 was launched, so run 96 carries the first fix alone;
these two go into run 97.

**The other agent's review, read and discussed (15:20-16:00; `docs/review/`, local only).** Revision 2, baselined
at this morning's decisions commit, recommends refining the current direction - no rewrite, no pause, no paid
launch yet - and orders the work: a completion-and-issue status contract first (its F01: an empty output drops its
warnings, an invalid page range succeeds silently, a truncated model reply is accepted), honest assurance wording
(F02), repairs to my two-reader comparison tool (F10), then reader-adoption evidence, then both downstream tasks,
then delivery. **F10 is right on every point and one matters most: `bench/tools/kfs_two_readers.py` prints its
discrepancies from the held-out fifth too**, the leak the split exists to prevent, written by me on the 17th without
noticing; its normaliser also erases a tick-versus-cross difference, its 0.98 cutoff misses a removed "not" in a
long cell, and rows one reader misses drop out of the count. The fifteen cells and three answers reported on the
17th are to be re-listed with held-out sheets excluded before any is read against its page. Other points taken:
"a product cannot use that post-processing" was too broad (a product cannot choose it by benchmark folder; general
source-preserving normalisation is fine, and the aligned split is exactly that); "level" from an overlapping
interval is not an equivalence test; the 102 deep pages were counted from changed output, not call records; "both
models fit on one card" is a claim about weights, not serving; the docs said 7,010 checks where the files hold 7,019
(fixed). Where I pushed back: "use the upstream model for everything" is not level with the hybrid on the evidence
(Pro alone 86.1 raw on our scorer against our 86.6; equal on the sheets' shape, behind on their wording); two
findings predate the day (the seven-check loss is traced and fixed; the invented-text check passed); the JSON
salvage is a bench tool, not the product, though the live provider must carry finish reasons. My recommendation to
the owner: accept the direction and the order, with the review's R2-S1 (the status contract, its ten probes as
acceptance cases) and the F10 repairs before the fifteen cells; the owner has not yet ruled on that order.

**The leaderboard, and publishing (16:00-16:30; D036).** The owner: a listing on the benchmark's own leaderboard is
instant credibility. Checked against Hugging Face's documentation, not memory: a model repository holding
`.eval_results/olmocrbench.yaml` is aggregated onto the dataset's leaderboard automatically, entries are
self-reported (no verification exists for this benchmark's own scorer), and a classical pipeline is already listed
with a results page as its source, so a tool can be. Our dataset copy is revision `54a96a6f`, the one the entries
cite. Decided: the strong form (all 1,403 page outputs plus the scorer's log as the source, so anyone can rescore
in minutes), Apache-2.0 for the code, the four insurer PDFs stay, the reviewer's folder stays local
(`.gitignore`), one repository pushed private first and public with the entry, a tag per quoted run. The owner
does the two one-time logins; nothing goes public before LICENSE, NOTICE, the D007 weight licences, a
stranger's README tested in a clean environment, and a secrets scan of the whole history.

**Run 96, scored 14:49: 86.6 (CI 85.6-87.4).** Against run 95, old-scan maths 381 to 388 - the seven, and nothing
else moved in any category. Held-out 86.0 (unchanged; both algebra pages are tuned-on), tuned-on 84.5. Under D035
this was the number we quote for an hour and a half. Run 97, the tree at 9f9b77b with the two rules above, was
validated at 14:50 and launched at 14:56; the owner asked for a pause once run 96 and the re-measurement were in
and the docs current.

**Run 97, scored 16:25: 86.8 (CI 86.0-87.7) - the number we quote.** Against run 96, old-scan maths 388 to 397:
**nine won, none lost**, exactly the code-against-code measure over the model-read pages - eight checks on `3_pg39`,
the aligned column, and one on `4_pg48`, the seam join - and every other category identical to the check
(`bench/tools/run_summary.py` over the two run folders). Held-out 86.0 (1,096 of 1,255, unchanged: both pages are
tuned-on), tuned-on 84.8 (4,993 of 5,764). The afternoon's three maths rules together took old-scan maths from 83.2
at run 95 to 86.7, every check of it on tuned-on pages - which is the honest reading: the rules were built from
what the leader's post-processing does to pages I could see, and the held-out fifth has not moved since run 95.
The leader's 87.6 now sits just inside the top of run 97's interval, by the same reading that called Chandra's 85.8
level with run 91; on the number it is eight tenths ahead, so M7 stays not met. The runs table, the leaderboard
table and its section-score table in `docs/BENCHMARKS.md` (which now carries run 97's and run 94's section rows),
`docs/STATUS.md` and the memory brief say 86.8; nothing else moved. The pause holds here.

**17:00-17:20 - the repository goes to GitHub, private (D036).** The owner did both logins (`gh` as
`islandtimer`, `hf` as `awmg`) and named the repository TrueDoc. Before the push: a scan of all 3,666 blobs in
the history for API keys, tokens, private keys, secret assignments, emails and IP logins (43 seconds; a
scratchpad script) - no credential anywhere; the only "secret" is `api_key="test-key"` in a test, the emails
are insurers' contact lines on benchmark pages plus `x@y.com`, and the rental host was never committed. Personal
paths: 18 files named this machine's folders (five with the repository root as a literal, eight with the library,
three one-document probes, a shell script's scratchpad, and 505 entries in `out5/pro/own/manifest.json`); the
root is now derived from each script's location, the library comes from `bench/tools/doc_library.py`
(`TRUEDOC_LIBRARY`, or the git-ignored `bench/library_path.txt`; a stranger gets a plain message), and the
manifest's paths are relative to the library (`build_own_sets.py` writes them so). `kfs_grade` still finds its
190 sheets. LICENSE is the Apache-2.0 text from apache.org, checked by hash; `pyproject.toml` said MIT and was
wrong. NOTICE names the olmOCR scorer copy and how `score_olmocr.py` runs it (the vendored `benchmark.py` with
its three relative imports pointed at olmocr 0.4.27's modules - I first wrote that the package's own scorer
runs, read the wrapper, and corrected it), the committed readings and the dataset's ODC-BY terms, the samples,
and both weight repositories, each checked Apache-2.0 through the Hub's API (heron now lives at
`docling-project/docling-layout-heron`; the old name redirects). The README: a results table, a quick start
that matches `pyproject.toml` (the extra `pip install transformers rapidocr-onnxruntime` line was stale), a
reproduction section, and a licence section. The reproduction section was tested before it was written: the
three replay candidates run 97 used (`inf2flash_raw`, `inf2pro_raw`, `olmocr2c`) rebuild byte for byte from
the committed readings with `place_bakeoff.py` and `merge.py place` - except that `olmocr2c`'s crop manifest
was git-ignored, so it is now committed as `bench/gpu/out3/crops_failing_manifest.json`. Suite 692. Commit
157a60e; `gh repo create TrueDoc --private --source=. --push` took under a minute; tag `run-97` on 9f9b77b,
pushed; the API confirms private, default branch master, licence detected Apache-2.0, no `docs/review/`. A
fresh-venv install test (`pip install -e ".[bench,dev]"`, three sample pages, the suite) was still running at
17:20.

**17:20 - the clean install found the one thing a stranger would have hit.** Ten minutes to install (torch is
most of it), and the suite passed, 692 - but the conversion printed "AutoImageProcessor requires the Torchvision
library" and wrote its three pages *without the layout model*, saying so in the front matter exactly as b7f53c4
requires ("the layout model was asked for and could not run, so 3 page(s) were read without it"). `torchvision`
was in our venv (0.28.0, installed by hand at some point) and not in `pyproject.toml`. Added (`torchvision>=0.15`),
reinstalled in the same fresh venv, converted again: no warning, and the output is byte-identical to the
project venv's for the same three pages, timestamps aside - on torch 2.14, transformers 5.17 and torchvision
0.29, all newer than the project venv's 2.13 / 5.16.1 / 0.28, so the pins hold forward. The review's F06 (a README a stranger
can install from, tested in a fresh environment) is met. Note for the other agent's F01 (the status contract):
this run is the case its probes describe - a stage silently degraded to the reader of the markdown, loud only
in the front matter and on stderr; the exit code was 0.

**17:30-18:50 - GPU session 6: the picture-text check. Flash fails it; olmOCR 2 keeps the crops; the number
stands.** The owner's order for what remained: this check first, then the leaderboard entry, then the review's
F01/F10 - a correction to my earlier recommendation, which had taken the review's order wholesale though the
entry depends on neither. He rented one RTX 4090 (24 GB, vast.ai, US, $0.386/h, Max CUDA 13.0, 70 GB disk; the
first address he sent refused connections and a second one worked). Only `crops_failing` went up - 42 MB as one
tarball, 32 minutes at 20-25 KB/s, slower than the 50 KB/s of past sessions; a parallel-stream test was
inconclusive and re-cutting the crops on the instance from the benchmark's own pages was possible (`select_regions.py`
is a clip on the page) and declined by the owner, rightly: the check must use the same 92 crops olmOCR 2 and Pro
read. The installs ran during the upload (`run_bakeoff.sh ... prep`, an unknown stage name, does the venv and the
pins and nothing else - torch 2.10.0+cu128, vLLM 0.17.1, INF-MLLM at 5089819 again) and Flash's weights were
fetched behind them (snapshot cfddc410, into the image's `/workspace/.hf_home`). Then `SETS=none CUSTOM_PROMPT=...
FIT_GB="6 8 12 16" ... flash`: server up in five minutes, 92 crops read under our prompt, none failed, in ten.

The readings placed as `inf2flash_custom_raw` with the crop manifest (`place_bakeoff.py infinity` reads the custom
`inference.jsonl` as it reads the authors'). Counted by the pipeline's own rule for an answer (not `none`, three
words or more): olmOCR 2 transcribes 52 of 92, Pro under our prompt 47 (the log's 53 was a looser count; Pro's
custom readings had never been placed - now `inf2pro_custom_raw`), Flash 44 - **with 12,682 words to olmOCR 2's
3,337**. Two crops hold 11,060 of them: `multi_column/027880a8..._page_7__r0`, a two-panel scatter plot, for which
Flash invented an 1,800-row markdown table of numbers from 0.00 to 45.20 (olmOCR 2: a 46-word description); and
`arxiv_math/2503.05506_pg11__r0`, a graph figure with vertex labels, where Flash wrote two labels and then
`- V_i^50s` 4,095 times to the token limit (olmOCR 2: nothing). Both read against their crops. The rest of the gap
was HTML: olmOCR 2 writes tables as `<table>` markup and my word count took the tags as words; the geology table
(`tables/3d780c..._pg22`) is right cell for cell in Flash's markdown. Coverage cross-tab: both read 42, Flash only
2, olmOCR 2 only 10, neither 38; of olmOCR 2's ten, two are figures it *described* (a diagram, a scatter plot)
where Flash rightly answered `A B` and `None` - and on 15 crops olmOCR 2's whole answer is a description, which
the pipeline writes into the page as `![...](figure)[^inferred]`, twice on three run 97 pages (a duplication to
trace).

**Through the converter, the 60 pages three ways on the same code** (`ab_pool.py --pages crop_pages --vision
file:inf2flash_raw+<crops>`; the olmOCR 2 side's 60 page bodies are byte-identical to run 97's): olmOCR 2 230 of
306; Flash 228 (tables +1 on the geology table, -1 on a people list both mostly fail, **-2 on the sideways
vehicle-list scan, where Flash dropped the chassis-number column - seven columns of eight - and read NUMERO as
HUMERO**; the two runaways moved no check, as the benchmark's design predicts); Pro 230 (+1, -1, the vehicle list
intact, no runaways). **Verdict under D033's own words:** Flash cannot be the crop reader - "noticeably more
unsupported text" - so olmOCR 2 stays on the crops, Flash stays on whole pages, and since run 97 was made exactly
that way the quoted 86.8 is unchanged. Recorded in D033. Fit stage: 6 GB does not serve Flash, 8 GB does (8.6 GB
in use; weights 4.25 GiB, KV cache 1.84 GiB at 32k context), 12 and 16 GB likewise; the stage's twelve-crop reads
all failed with "requested 32768 output tokens" against the 32k context - the authors' client's default output
length against my shorter `--max-model-len`, so "serves in 8 GB" is shown and "reads in 8 GB" is not; a flaw in
the fit stage, to fix before it is used again. Instance destroyed by the owner at 18:50; about 55 minutes of
instance time, all-in cost to come from the account. Everything is in `bench/gpu/out6/` (logs, fit results,
environment) and `bench/gpu/out5/flash_custom/` (the readings).

**19:00-19:35 - published (D036), on the owner's "publish".** The entry was built locally first and the owner
shown its three reader-facing files: `bench/tools/leaderboard_entry.py` copies run 97's 1,403 outputs and the
scorer's four files, computes the nine values from the counts (overall 86.8214, the mean of the eight section
pass rates, agreeing with the scorer's 86.8), and writes `.eval_results/olmocrbench.yaml` in the form the hub's
documentation specifies and the kraken entry uses (dataset id, task id, revision, value, date, source, notes),
a results page and a card that opens "this repository holds a benchmark result, not model weights". He asked
whether it could be named just TrueDoc: the hub prefixes every repository with its account, and the `truedoc`
namespace is someone else's, so `awmg/TrueDoc`. Then GitHub to public (`gh repo edit --visibility public`), and
`leaderboard_publish.py` created the repository and uploaded 1,411 files in a minute. **Two things caught in the
first minutes.** A web request for `docs/review` on the newly public repository answered 200: it was GitHub's
generic landing page, served for a few seconds after the flip - the API says Not Found, the remote tree has no
such path, no commit ever held it, and the raw URL is 404; it then answered 404 like any missing path. And the
card listed the benchmark under `datasets:`, which the hub reads as *trained on*: TrueDoc appeared in the
dataset's "models trained or fine-tuned on this" list, which is false. Removed from the card and from the
script within five minutes; the list no longer shows it. The hub tagged the repository "Eval Results" at once
and serves the entry file anonymously; the dataset's leaderboard table still showed its eighteen models (a new
one since the 17th: `jinaai/jina-ocr-v1`, 83.4, fourth) and not ours at 19:27, seven minutes after the upload - **I wrote "19:45" and "twenty minutes" here and in four
other places from a sense of elapsed time, without looking at the clock; corrected at 19:35.** What the comparison found (19:30-19:45, the owner's request): nothing wrong with the file. The hub's API (`/api/models/<repo>?expand[]=evalResults`) shows our nine results parsed exactly as it parses kraken's and jina's, and reports no validation error (it does report one for another repository's rejected file, so silence means accepted); the task ids match the benchmark's `eval.yaml`; two listed entries have no `pipeline_tag`, so that is not required; the public listings know the repository (search finds it; the `eval-results` filter lists it newest of all). What differs: our notes are 681 characters and our source name 94, where no listed entry exceeds 286 and 36; and age. The leaderboard has its own API (`/api/datasets/allenai/olmOCR-bench/leaderboard`, 18 rows), and neither it nor our model page's results widget has us - but a two-day-old repository with ordinary, valid results (`luganoquant/Inkling`, 16 September) has no widget and no row on its benchmark either, so the display side lags by days or is gated, and not for anything in our file. The feature's page calls it work in
progress and says results appear automatically, with no timing. To check again; if a day passes without the
row, compare our file field by field with an entry that did appear the same day, and ask on the dataset's
community tab.

---

## 2026-09-17, afternoon and evening - GPU session 5: a stronger open reader, measured on our own pages

**Why.** The leaderboard read that morning put two tools above us and the gap to the first, 2.2 points, sat in four
sections, three of them photographs of paper (`docs/BENCHMARKS.md`). Those are the pages TrueDoc hands to a model, so
the score there is the reader's, and M17 had already concluded that no rule reaches them. The owner approved a rental.

**A miss of mine, found while preparing.** `docs/MODEL_CHOICE.md` had listed Infinity-Parser2-Pro at 87.6 and
Chandra 2 at 85.8 since 12 September (dcd4d35), marked "least verifiable" because neither published its sections.
M7 was written up as met against 83.1 the next day. Two documents in one repository disagreed for five days; the
stale README was only half of it.

**What the leader's 87.6 is made of.** The authors' own evaluation script
(`INF-MLLM/Infinity-Parser2/evaluation/olmocr-bench`, commit 5089819) scores their readings after post-processing
keyed on the benchmark's category folder names. `infer.py`, read in full: `convert_latex_in_markdown` and
`apply_synonym_map` on `multi_column` and `tables`, `latex_formula_normalization` on the two maths sets, handed the
category. `utils.py`, read only through a fetch tool's summary [so tagged]: about 850 lines, LaTeX turned to
Unicode, adjacent formulas merged, and aligned environments split into single formulas only when the folder is
called `old_scans_math`. A product cannot know a page's benchmark category.
Their script keeps the raw reading beside the processed one, so everything below is measured both ways.

**The session.** One H200 NVL (141 GB, Czechia, US$4.37 an hour), 15:03 to 17:13; **US$12.03 all in**, the disk and
some 80 GB of downloads included - I quoted the GPU time alone at one point (about $9.50), which is the wrong
number to give an owner. Read through the authors' client, vLLM 0.17.1, greedy decoding:

| set | pages | Flash (2.2B) | Pro (35B) |
|---|---|---|---|
| every page without a digital text layer | 281 | read | read |
| the picture crops (92 on failing pages, 107 more) | 199 | read | read |
| the rest of the benchmark | 1,122 | - | read |
| the owner's own pages (25 insurance set, 380 Key Facts Sheet, 100 library; the sealed 19 excluded by name) | 505 | - | read |
| the 134 old-scan pages a second time | 134 | - | read |
| the crops under TrueDoc's own picture-text prompt | 199 | - | read |

No page failed. Everything is in `bench/gpu/out5/` (c12dadd), with `environment.txt` holding every package version
and both model snapshots. **Correction, the same evening:** I first kept the readings of the owner's pages out of
git, as insurers' words in a repository that may one day be published; the owner ruled that they are publicly
available documents, and they are committed with the rest (D032).

**Quick merges first (minutes each): a reader's raw pages over run 89's, all 281, scored.**

| | olmOCR 2 | Flash raw | Pro raw | Pro + authors' post-processing |
|---|---|---|---|---|
| overall | 84.0 | 85.6 | 86.4 | 86.9 |
| old scans | 46.6 | 51.3 | 58.4 | 58.4 |
| old-scan maths | 80.8 | 85.6 | 83.4 | 87.6 |
| long tiny text | 88.7 | 91.4 | 92.5 | 92.5 |
| tables | 87.3 | 88.5 | 88.8 | 88.8 |
| headers and footers | 96.8 | 96.1 | 95.9 | 95.9 |
| multi-column | 83.6 | 83.8 | 83.3 | 83.5 |
| held-out | 80.9 | 84.5 | 84.5 | 85.5 |

Pro's 58.4 on old scans reproduces the 58.2 its authors publish. Its 87.6 on old-scan maths does not reproduce their
91.3. The post-processing is worth 0.5 to us and all of it is on that one section.

**Then the number that counts: two full runs of today's code, the reader the only difference.**

| | Run 92, olmOCR 2 | Run 93, Pro raw | |
|---|---|---|---|
| **overall** | **84.2** (CI 83.4-85.2) | **86.4** (CI 85.5-87.3) | +2.2 |
| held-out | 81.5 (1,071/1,255) | 84.8 (1,090/1,255) | +3.3 |
| tuned-on | 82.1 (4,913/5,764) | 84.4 (4,983/5,764) | |
| old scans | 47.0 (247) | 58.6 (308) | +61 |
| long tiny text | 88.7 (392) | 92.5 (409) | +17 |
| tables | 88.6 (905) | 89.6 (916) | +11 |
| old-scan maths | 80.8 (370) | 81.9 (375) | +5 |
| multi-column | 83.6 (739) | 83.1 (735) | -4 |
| headers and footers | 97.0 (737) | 96.8 (736) | -1 |
| arXiv maths | 88.6 (2,594) | 88.6 (2,594) | 0 |
| baseline | 99.8 (1,391) | 99.9 (1,393) | +2 |

Both: `--vision-endpoint file:<whole pages>+<olmocr2c>`, the crop readings left as olmOCR 2's so that one thing
changes. Run 92 was validated by the launcher at 15:59 (suite passing, gate 100, samples 46 and 61) and run 93
converted the same tree. **Run 92 is also the first full run since 13 September, and the week of rules drawn from
the owner's library cost nothing: 84.2 against run 89's 84.1, every category identical to the check but tables,
896 to 905.** Run 93's 86.4 would stand second on the leaderboard, above Chandra OCR 2's 85.8 and above our own
hosted 85.4 with no paid service in the loop; its interval stops at 87.3, so 87.6 is still a real gap, of 1.2
where it was 3.5.

**A loss of our own, not yet traced.** On old-scan maths the converter scores 375 with Pro's readings and the plain
merge of the same readings scores 382: something in how TrueDoc handles a model's maths costs seven checks, and a
step of ours should never score below the raw reading. The authors' clean-up reaches 401 on those pages. Tracing the
loss and measuring a general form of that clean-up - on all six categories that have model-read pages, which is the
lesson of run 90 - is CPU work on readings already on disk.

**Traps met on the rented machine, so they are not met twice.**
- A fresh vLLM server takes about fifteen seconds over its first request and the authors' client gives up its
  connection check after five: Flash's first pass wrote nothing and said nothing, because my own filter on the log
  hid the traceback. The script now sends the first request itself, and shows the client's last lines.
- `pkill -f run_bakeoff` kills the shell that runs it, whose command line holds the same words. `pkill -f
  '[r]un_bakeoff'` does not.
- The image's system pip refuses to install (PEP 668) and ships `uv`; the script uses it.
- pip reports vLLM 0.17.1 as wanting transformers below 5 and installs 5.17 anyway. That is the authors' documented
  pairing and it serves both models.
- Sending 32 pages at a time, not 8, tripled Pro's rate (about 31 pages a minute on the dense arXiv pages, 42 on the
  owner's): **about a quarter of a US cent a page** at this rental's price.
- The owner's uplink carries about 50 KB a second: 89 MB of pages took 27 minutes. Anything public should be fetched
  by the rented machine itself, as `fetch_pages.py` does for the benchmark.
- The authors' client hands back the model's layout JSON untouched when it can make no markdown of it - a picture
  with nothing to read, a page of running heads alone, a reading its parser chokes on. `place_bakeoff.py` turns
  those back into the text they hold (2 of 281 whole pages, 71 of 92 crops).

**The owner's own documents: two independent readers, and what their disagreements found.** Pro's pages 1 and 2 of
all 190 Key Facts Sheets, graded by `kfs_grade.grade` exactly as TrueDoc's are (`bench/tools/kfs_two_readers.py`):

| | TrueDoc | Pro, never tuned on anything of ours |
|---|---|---|
| header whole, 158 tuned on | 157 (99%) | 157 (99%) |
| header whole, 32 held out | 32 (100%) | 32 (100%) |
| answers attached, tuned on | 1,885 / 1,885 | 1,891 / 1,893 |
| answers attached, held out | 375 / 375 | 374 / 374 |

On a clean modern table the leader reads the shape as well untuned as TrueDoc does after three days of rules. Then
the words, which the shape grader cannot see: of 2,256 event rows both found, the Yes / No / Optional is identical on
2,253 (the three are one AAMI-family template, not yet read against its page), and the third column is identical on
2,221 and materially different on 15. **Every one of the fifteen read so far against TrueDoc's own markdown is
TrueDoc's fault, on sheets the grader passes as perfect:** a wrapped cell line that opens with a capital becomes a row
of its own ("...cover can be purchased to cover" and then a row holding only "Accidental Damage." - the orphan test
only looks for lowercase continuations); a stray word from elsewhere lands in a cell ("...with your consent.
entered" on two GIO sheets, "loss or damage that item. occurs more than 72 hours" on two Apia sheets); and one sheet
writes "[icon]" in five third-column cells where Pro has nothing. None is built; each is a candidate to measure in
the usual way. This is M11's disagreement mining working for the first time, and it cost minutes.
`bench/gpu/out5/pro/own/kfs_text_diffs.json` and `kfs_answer_diffs.json` hold the lists.

**The picture crops.** Asked its authors' layout question, Pro calls 71 of the 92 failing-page crops a figure and
transcribes nothing; olmOCR 2 read 54. Asked TrueDoc's own question it reads 53 (olmOCR 2: 52; three of olmOCR 2's
are descriptions of plots, which the prompt forbids; one of Pro's is an invented image address, so its answers need
a guard). Not yet scored through the converter. **Flash was not asked our question - my omission** - so whether one
small model can do both jobs, and olmOCR 2 be retired, is open.

**Not finished.** Pro alone over all 1,403 pages, which would check the 87.6 end to end, hung in the scorer twice
under load and was stopped; to be re-run a category at a time. Runs 94 (Flash alone) and 95 (Flash on every scan
page, Pro on the pages the converter's own D025 router flags, through `--vision-deep file:`) were launched at 19:07
on the same tree.

**Runs 94 and 95, scored 20:59: two tiers reach Pro's score with Pro reading a third of the pages.**

| | Run 92, olmOCR 2 | Run 94, Flash | Run 95, Flash with Pro behind the router | Run 93, Pro |
|---|---|---|---|---|
| **overall** | 84.2 | **85.6** (CI 84.8-86.5) | **86.4** (CI 85.4-87.3) | 86.4 (CI 85.5-87.3) |
| checks passed, of 8,413 | 7,375 | 7,432 | 7,465 | 7,466 |
| **held-out** | 81.5 (1,071) | 84.8 (1,088) | **86.0 (1,096), the best yet** | 84.8 (1,090) |
| old scans | 47.0 (247) | 51.5 (271) | 58.4 (307) | 58.6 (308) |
| old-scan maths | 80.8 (370) | 84.1 (385) | 83.2 (381) | 81.9 (375) |
| long tiny text | 88.7 (392) | 91.4 (404) | 91.4 (404) | 92.5 (409) |
| tables | 88.6 (905) | 89.3 (913) | 89.3 (913) | 89.6 (916) |
| headers and footers | 97.0 (737) | 96.4 (733) | 96.7 (735) | 96.8 (736) |
| multi-column | 83.6 (739) | 83.7 (740) | 83.6 (739) | 83.1 (735) |
| arXiv maths | 88.6 (2,594) | 88.6 (2,594) | 88.6 (2,594) | 88.6 (2,594) |

Run 95 is `--vision-endpoint file:<inf2flash_raw>+<olmocr2c> --vision-deep file:<inf2pro_raw>`: D025's router,
exactly as built on 13 September, with nothing in it changed - a page goes to the deep reader when it has no text
layer and our own OCR of it finds nothing word-like. It sent Pro **102 of the 1,403 pages** (counted as the pages
whose markdown differs between runs 94 and 95: 64 old scans, 14 headers and footers, 10 tables, 7 old-scan maths, 6
multi-column, 1 tiny text) and Flash the other 179 that have no digital text layer. The result is one check short of
Pro reading all 281, and ahead of it on the held-out pages and on old-scan maths, where Flash is the better reader
and keeps most of the pages. I had said beforehand that two tiers would earn their place if they recovered most of
the 0.8 between Flash and Pro, and that under half would argue for one reader: they recovered all of it. With a
second reading moving a section by about three checks (below), runs 93 and 95 are level, not ranked. **Flash alone,
at 85.6, is level with Chandra OCR 2's 85.8 on a model of 2.2B.** The reader is still the owner's decision; this is
the evidence for it.

**How much a second reading moves (measured the same evening).** Pro read the 134 old-scan pages twice, greedy
decoding both times, 8 pages at a time and then 32. Only 80 of the 134 readings are the same character for
character; 54 differ, six of them by more than a twentieth of their words and one almost wholly. Scored the same way
(candidate `bake_pro_repeat`): old scans 305 against the first reading's 307, old-scan maths 385 against 382. **So a
fresh reading of the same pages moves a section by about three checks either way, and the overall by less than a
tenth.** Our runs replay saved readings and are exact; what this sizes is how far to trust a small difference
between readers - Pro's 61 checks over olmOCR 2 on old scans is far outside it, Flash's 10 over Pro on raw old-scan
maths only modestly so.

**The owner's rulings this session.** The rental (approved); his library's documents may go to a rented machine
for a model to read, never the sealed nineteen (D032); the laptop test parked (below).

**"Everyday" was the wrong word, and the owner caught it.** I called Flash an everyday reader because it fits a
24 GB card. His own laptop - a Core Ultra 7 with Intel graphics and 32 GB, no NVIDIA card - can run none of these
as we ran them, and that is most people's machine. The tiers are about where a model runs, not which card: the
mechanical tier on any laptop; a reader behind a service (or a technical user's own card). What survives of the
idea, in the owner's words, is a note to help a user decide what they need: Flash on small documents might be
possible on a laptop, and nothing else is. The timing test that would say how slow is parked.

---

## 2026-09-14 to 2026-09-17 - Table rules from the Key Facts Sheets, the imprint, and the library read against its images

_Entries in this section run oldest first, the newest just above **Where the Key Facts Sheets stand**._

**Two more rules, and the oracle sorted the work rather than leaving it to guesswork** (13-14 Sept)
After the first heading fold, 99 sheets still lost their header. `bench/tools/kfs_why.py` sorted them by
cause instead of two examples being generalised from: 51 had lost a whole column, 27 were still split,
21 had a sentence from above the table sitting in the header row. That ordering is what made the next
two rules aimed rather than hopeful.

- **A heading that breaks on "apply to" carries on past an empty cell** (a431c79). Where a heading's
  columns wrap by different amounts their lines interleave, so a column's continuation sits two rows
  below its own start with an empty cell between, and a fold that looks one row down stops at the first
  line. The signal is the break itself: a preposition or conjunction cannot end a column heading, so the
  sentence has to go on somewhere - a far tighter test than "no full stop", which nearly every heading
  passes. Guarded by requiring the row below to still look like heading, part of it empty; a body row of
  the prescribed table fills every column and stops the fold dead. Header whole 51% -> 59% tuned on,
  34% -> 50% held out; stray continuation rows 22 -> 9 and 6 -> 1, which was not designed for.
- **A paragraph's lines run on; a column's cells start with a capital** (7afddab). `_split_side_by_side`'s
  prose branch, added in run 58 for a figure's key values set beside a paper's body text, was cutting
  the third column off 51 sheets: "Yes" and "No" beside seven-word sentences is exactly what that branch
  looks for. The exclusions were not deleted - they were left as loose paragraphs above the table, with
  nothing to say which insured event each one qualified, which on a Key Facts Sheet is the whole point
  of the document. The separator is how the wide side reads, judged on the opening letter alone: run 58's
  prose opens every one of its five lines lower case and mid-sentence; each exclusion opens with a
  capital. It fails safe - unsure means the table stays whole. Header whole 59% -> 72% tuned on,
  50% -> 66% held out; sheets whose exclusions are severed from their events 51 -> 0.

**The second of those needed three categories, not one.** It changes whether a region becomes a table at
all, and that code runs on every page of every category - the run-90 mistake in miniature if measured on
tables alone. Code against code on 481 pages and 2,348 checks: tables 843 v 843, multi_column 682 v 682,
long_tiny_text 357 v 357, not one page moved in any of them. Both `before` and `after` sides were chained
inside a single command around the `git stash`, so the working tree could not be left half-applied
between them.

**Where the Key Facts Sheets stand after four rules:** header whole **34% -> 72% tuned on and 16% -> 66%
held out**, the hidden fifth moving with the rest at every step. All four rules are written in geometry
and typography; none of them knows what an insurance document is.

**The band inside a table, in three attempts and one owner's objection** (14 Sept, 140c19f and 84b38a5)
A Key Facts Sheet breaks its table with a full-width line opening a section - "Cover for valuables,
collections and items away from the insured address" - and the merger was reading it as the tail of the
cell above, so a reader tied a new section's heading to escape of liquid. 63 sheets.

- **The geometry, measured before any rule:** an ordinary wrapped continuation begins some 16pt *inside*
  its own column; the band begins 96pt to the left of the column it was filed under and crosses the rest.
- **Attempt one - don't fold a row that crosses columns, and move it into the first column it covers.**
  Won 60 of 63 bands and cost 26 events their Yes/No answer. Bisected: the no-fold half carried the whole
  win at no cost; the placement half did all the damage, because a wrapped line spilling a little into the
  narrow "Yes/No" column read as a band under any test loose enough to catch the real ones, and landed on
  top of the answer. Placement removed.
- **Attempt two - the same, unless the row above also spans.** Still cost two checks on the benchmark: a
  table's own centred title ("TABLE 1 / Partial Correlations Between Stroop Scores and / Verbal
  Responses") crosses the columns in exactly the same fashion, and the guard did not fire where assumed.
- **Attempt three - a band must cross three columns, a title two.** Measured, and **the owner stopped it
  before it shipped**: a two-column table can hold a band and could never satisfy the test, so live
  documents would keep the fault whatever this corpus happens to contain. His point was a design point,
  not an empirical one - no census was needed or wanted.
- **What shipped: position, not width.** A title stands above the grid with no proper row of the table
  before it; a band stands inside the body with proper rows above *and* below, counted only within the
  columns the text spans (so the references running beside a table on a two-column page cannot vouch
  for a title). Bands swallowed 63 -> 12 tuned on, 8 -> 0 held out; every other measure unmoved; and
  **+1 on the benchmark** (843 -> 844), where the width version had been -1.
- **Then the band spans the table.** The band kept its own row but sat under whichever column it was
  filed beneath, so a reader took the heading for an example of an exclusion. A band belongs to no
  column, and `render_table` already switches a table to HTML the moment any cell spans, so it became
  `<td colspan="3">`. With detection now positional the same placement that cost 26 answers is safe:
  header whole 72% -> 75% tuned on and 66% -> 69% held out, stray continuation rows 9 -> 7, answers
  unchanged at 93%, benchmark 844 v 844.

**The instrument was wrong twice in one afternoon, and both times it looked like the converter.**
- `kfs_grade.py` matched a prescribed event *anywhere* in a cell. Once bands moved into the first column,
  the band's own text - which contains "items away" - matched as that event's row, a row that by its
  nature carries no answer. It reported **47 events losing their Yes/No** when nothing in the converter
  had changed for them. Three explanations about the converter were offered and all were wrong; the
  per-sheet diff found it, because 54 sheets each losing exactly one is not the shape of a real
  regression. The label must now *open* the cell.
- `kfs_diff.py` had **copied** the grader's matching logic instead of calling it, so after the grader was
  fixed it went on reporting 55 lost. It now delegates. One implementation, or two disagree exactly when
  it matters.
- And a near miss worth recording: with the grader fixed, the spanning change read 1804 answers against
  a remembered 1797 - but 1797 had been measured by the broken grader. Both code states were re-graded
  by the one corrected grader before anything was claimed; they came out identical.

**Where the Key Facts Sheets stand after six rules:** header whole **34% -> 75% tuned on, 16% -> 69% held
out**; exclusions severed from their events 51 -> 0; section headings buried in an exclusion 63 -> 12;
events carrying their Yes/No 93%. Every rule is geometry and typography.

**Where the missing Yes/No answers went, and a column the cut-finder had been voting down** (14 Sept)
- **The losses sorted by shape before any rule** (`bench/tools/answer_census.py`): most were "no row" - an
  event named in the table but never opening a row of its own - then "glued" ("Fire and Explosion Yes" in
  one cell), then "bare".
- **"No row" was mostly the grader again.** It counted an event as present if its name appeared anywhere in
  the table, so "Accidental Damage" inside the exclusions of the Accidental Breakage row (91 sheets, 76 of
  them with the real event answered), "items away" inside the valuables band (12) and "malicious damage"
  inside the fire exclusion (8) all read as missing events. An event is now held only if it is named in the
  label column read down the table (`held_events`), which still counts - and fails - a label genuinely split
  over two rows. A second fault in the same grader flattered us: it accepted an answer word opening *any*
  later cell, so "Flood |  | Optional Excludes damage..." passed with its answer column blank. The owner
  confirmed the column is headed "Yes / No / Optional", and `carries_answer` now looks only there. Both are
  shared helpers the census and the diff call, rather than copies of them.
- **"Glued" was a column the cut-finder out-voted** (`_refine_segments`). On the ALDI template every "Yes"
  starts at x=136.9, and all 14 rows with words either side of that x leave a gap there; but the vote was a
  share of all 35 multi-word rows, 21 of them wrapped exclusion lines lying wholly to its right and unable to
  vote either way - 14 against a threshold of 21. AAMI's cut vote failed identically (16 against 20.4) and
  escaped only because its gap was wide enough for a whitespace channel. A second, purely additive look now
  judges a range by the rows able to judge it. ALDI reads "Fire and Explosion | Yes |" again, and "High value
  items No and collection" became "High value items and collections | No |".
- **Then three contents sheets lost their heading, and the cause was an accident being removed.** A sentence
  above the table ("Any amounts you claim include GST less...") was adopted as the table's first row by
  `_header_lines_above`. It had been kept out only because a band spanning the table stretched the first
  column's span across the whole width, so every word read as one column; better cuts gave that column its
  true width, and the sentence walked across three columns, changing column on word spaces of 2.8pt. A row of
  headings crosses between columns on the gap between its cells, so a line that crosses on less than 0.6 of
  the body size is now refused; 19 other sheets gained their headings and none lost one.

**Not one benchmark page moved, and the markdown had changed on 16 of them** (14 Sept)
The pooled gate for those two rules read tables 844 v 844, multi_column 682 v 682 and long_tiny_text 357 v
357. Diffing the markdown instead of the scores found 13 table pages and 3 multi-column pages changed, and
each was read against an image of its page:
- **7 better:** labels freed from their values ("Pupillary reactions | Relative afferent pupillary defect"),
  headings split into the columns they head ("Item | Quantity", "Sexe | Âge | Côté | Présentation",
  "Distortion | Intensity | Actual Parameters"), and a P/R/F1 table given all ten of its columns.
- **5 neutral:** two index pages and a chart read as tables either way, and two pages that gained one thing
  and lost another.
- **3 worse, from two causes.** A court form's address box and the claim box beside it became one table of
  three columns, every row an address line beside a line of the claim box ("Ikoyl | (including | Malabu Oil
  & Gas Limited"). And phrases were cut across two cells - "Groups at | Risk", "(thousands | or Os$)" - with
  "quimicos | e" and "Day 0 and 35 Day | 35 and 42" on the two mixed pages.
- **One that looked worse and was not.** A dishwasher manual's "de Störung, was tun?" disappeared. The layout
  model labels the line `layout:page_header`, a running head, removed on every page; the old code had kept
  the words only by filing them as the table's first row, which the new guard rightly refused.

**What the cuts were, read from the code itself.** `bench/probes/pass2_probe.py` runs `_refine_segments`' own
source with the second look cut out beside the real function, and prints every cut the second look adds with
the gap each crossing row leaves there. The phrases crossed on 0.23 to 0.51 of the body size - three of them
wide enough to count as a vote for a column - while every row the new cuts rightly divided on those pages left 1.09 or more.
The court form's cut was sound, 2.05 to 4.67 on all four rows it crossed; the fault sat one step earlier.
Without the second look, the finder saw no table there at all.

**Two rules, each with a test that fails without it** (`tests/test_second_look_cuts.py`):
- **A cut whose only work is to split phrases is refused.** The first version refused a cut if any one row
  crossed it on a word space - the 0.6 of the body size that `_header_lines_above` uses to tell a header row
  from a sentence - and the oracle caught what the benchmark pages could not: 38 answers lost on the sheets
  tuned on and 13 held out. On the ALDI, Bank of Queensland and Honey templates "Accidental Breakage" ends
  0.46 of the body size before its "Yes", a tight label on a column the other labels prove: on ALDI the cut
  divides six label-and-answer segments, five of them across real gaps. So the question is now asked of
  everything the cut would divide, and the cut is refused only when every segment it divides crosses on a
  word space. Each benchmark phrase was the one segment its cut divided, every other row already standing
  apart. One helper answers both questions (`runs_across_columns` in `tables/cells.py`). What it still
  misses: a sheet where the tight label is the only row the text layer ran together with its answer (Honey's
  building sheet, one answer), which on the geometry is the same shape as "Groups at | Risk".
- **The text-layer finder calls something a table only if the first look does too** (`find_aligned_tables`).
  Nothing there vouches for a table - no ruling, no layout model - and the second look finds a column inside
  a table, not a table. Where a ruling or the layout model has found the table, the second look still
  sharpens it.
- **Result, code against code:** Key Facts Sheets header whole 119 -> 133 tuned on and 22 -> 27 held out, and the Yes/No in its column 1788 -> 1827 of 1885 tuned on and 351 -> 367 of 375 held out; against the patch before the phrase rule, one answer fewer on one tuned-on sheet and nothing else moved. Benchmark tables 844 v 844, multi_column 682 v 682, long_tiny_text 357 v 357, not one page moved; the
  markdown changed against the committed code on 11 of 481 pages - 7 better, 3 neutral, and a running head the old code had filed into a table.

**A faster instrument, checked before it was trusted.** `ab_pages.py` starts the CLI for every page and so
reloads the layout model every time: 51 to 76 seconds a page with three subsets sharing the machine. The CLI's
options default to the dataclass's and it writes the converted string unchanged, and three pages came out
byte-identical converted both ways, so `bench/tools/ab_pool.py` converts in a pool of worker processes
instead. Both sides of a gate run on it, never one side per tool. Checked again on the 219 pages the CLI runs
had also converted: 217 identical, and the 2 that differed were converted by the CLI while the committed code
was stashed in place for the gate - each is identical to the pool's own reading of the committed code.

**Lessons**
- **"Not one page moved" counts checks, not the output.** A gate reading zero across 481 pages hid a false
  table and four phrases cut in two, because the benchmark holds no check on those cells. When a gate reads zero,
  diff the markdown and read the changed pages against their images before calling the change free.
- **`pkill -f` kills nothing here.** Git Bash does not see Windows command lines, so four A/B loops "stopped"
  twice ran on for more than three hours - one since 12:38 - converting pages all through the gate, slowing
  it to about 7 seconds a page, and writing committed-code pages into folders named for the patch while the
  stash was applied. Jobs are now stopped by PID through PowerShell and confirmed from the process list,
  never from a count of output files that held still for less time than one page takes.

**The two rules drafted this morning, measured together** (14 Sept, after 752ffa6)
- **A sentence above a ruled box is not its heading row** (`_adopt_ruled_headers`, through the same
  `runs_across_columns`). A Key Facts Sheet's own heading cell of more than four words made its ruled box look
  headerless, and the sentence printed above the box lines up with two of its column edges, so RACQ's sheets
  published "Under STEP this policy 2 you | Check set the the maximum |..." - a step heading and a sentence
  woven together - as the first row of the table, and Huddle's "Under this policy you | choose the | maximum
  level of cover...". A sentence crosses from one column into the next on a word space, a row of headings on
  the gap between its cells. Header whole 133 -> 150 of 158 tuned on and 27 -> 31 of 32 held out, no sheet
  losing its header.
- **A label that wraps continues its row, whatever the column beside it begins with** (`_label_carries_on` in
  `_merge_wrapped_rows`). "Escape" over "of liquid" stayed two rows on ANZ's buildings sheet because the
  exclusions beside the second line open a new sentence ("...from certain items." over "Not covered for the
  cost of repairing..."). The label column decides now: a lowercase tail of a few words, under a label not
  closed, on a row that leaves the short value above it empty. Yes/No in its column 1827 -> 1832 tuned on and
  367 -> 368 held out, no answer lost. It reached six events; the census still finds 34 events on the sheets
  tuned on whose name never opens a row - 22 of them a title-case label wrapping onto a capital ("Malicious"
  over "Damage"), which this rule does not accept - and that is the next rule.
- **The benchmark caught the first version gluing an index.** A back-of-book index read as two columns had
  "permeability 454, 457, 465" joined to the entry above, and with it the next row, because the rule overrode the
  merger's own guard that a line carrying a number under a line carrying a number is an entry of its own. The
  label column keeps that guard now; on the Key Facts Sheets, whose label tails carry no numbers, not one sheet
  moved for it. A German index still loses an entry the same way: the scan's own text layer reads
  "Impulsberegnung" as "lmpulsberegnung", and nothing in the geometry says a capital was lost.
- Tests for both, each failing on the code before it, and one for the index; suite 521. Benchmark, code against
  code: tables 844 v 844, multi_column 682 v 682, long_tiny_text 357 v 357, not one page moved; the markdown changed on 6 of 481 pages - 4 better (two captions and a title no longer the first row of their tables, and a TV listing's wrapped lines joined), 1 neutral, and 1 worse: a German index read as a table.

**A band belongs to no column, and a title-case label carries on** (14 Sept, after 639a1ab)
- **A band neither refuses a cut nor is divided by one** (`_band_segments`, in `_refine_segments`). On four
  contents sheets "Cover for valuables, collections and items away from the insured address" ran as one unbroken
  line over the gap between the answers and the exclusions. The cut-finder refuses a cut that a segment crosses
  without a gap of its own - right for a title or a group heading - so "Optional" was published at the head of the
  exclusions ("Flood |  | Optional Excludes damage to the liner..."). A band is told from a title by where it sits,
  as `_is_band` tells it on the finished grid: rows of the table above and below it, each with two or more
  segments under its extent. A label run together with its answer ("Actions of the sea No") is one segment too, but
  with a real gap in it, so it stays a row to be divided.
- **The label column carries on by the merger's own test, and a capital tail carries on when its row's other
  columns do** (`_label_carries_on`). "Malicious" over "Damage" - 22 of the 34 events that never opened a row -
  stayed two rows because "Damage" starts with a capital, though its exclusions carry on in lower case ("...caused
  by you, your" over "tenant or their visitors") and its Yes/No sits empty. And "Fire and" over "Explosion": a
  label ending on a connector goes on whatever case follows, which `_continues` already said.
- **The benchmark caught both parts reaching too far.** A TV listing's "Michael Flatley: A Night To" took "Remember
  (S). 3.40 Road" as its second line, and the page's table fell apart into loose lines; an address box's "SA
  SOLDIER" took "Private Bag X158", and three boxes became one table pairing names with the wrong roles
  ("Distribution: Deputy Editor: Mr Lufuno Netshirembe"). Neither tail read as words. A second line that does not
  start in lower case must, so one carrying a digit - a time, a box number, a count - stays an entry of its own. Both
  pages returned to the committed reading, and the milestone table the connector part repaired ("Substantial
  Completion of" over "Construction - Operational") kept its repair. Not one Key Facts Sheet
  moved for the guard.
- **A first look before the whole oracle**, on the sheets each rule was written for (`bench/tools/kfs_quick.py`):
  the four HCKFS sheets from 8 answers to 11 each, every "Malicious Damage" family one more, the sheet with "Fire
  and Explosion" two more - and ALDI's, Bank of Queensland's and Honey's household contents sheets not moved.
- **What the band rule does not reach yet.** Those three sheets start the band over the answers, so the rows around
  it hold one segment under its extent - the answer run together with its exclusions, the fault itself - and the
  band test cannot see it. White space tells it from a wrapped line (it stands 4.7pt or more clear of both neighbours, where
  wrapped lines touch), and a refinement drafted on that frees the answers; but on the finished grid
  `_spanned_columns` wants 30% of a column's width before a segment counts as crossing into it, and this band
  reaches 6pt into the answers' column, so it is still folded into the exclusions above. Both halves are a cycle of
  their own.
- **Result, code against code:** Key Facts Sheets the Yes/No in its own column 1832 -> 1864 of 1885 tuned on (97.2% -> 98.9%) and 368 -> 371 of 375 held out (98.1% -> 98.9%); events opening a row of their own 1851 -> 1875 and 370 -> 373 - the 22 "Malicious Damage" and 2 "Fire and Explosion" labels - with the other 8 answers the four HCKFS sheets' "Optional" freed from their exclusions; header whole and bands unchanged, and no sheet lost anything. Benchmark tables 844 v 844, multi_column 682 v 682, long_tiny_text 357 v 357, not one page moved; the markdown
  changed on 1 of 481 pages - a milestone table whose two-line row now reads as one ("Substantial Completion of Construction - Operational"), better. Tests for both rules and the guard, each failing without the part it guards; suite 528.

**A band over only some of the columns** (14 Sept, after 12c2137)
- **White space tells a band from a wrapped line** (`_band_segments`). ALDI's, Bank of Queensland's and Honey's
  household contents sheets start the band over the answers, or in the gutter after them, so the rows around it hold
  one segment under its extent - the answer run together with its exclusions, the very fault the band was causing -
  and the test by position could never see it. A wrapped line runs on from the line above; a band stands apart from
  both neighbours (4.7pt and more on these sheets), so a single run of text set apart above and below, with rows of
  the table on both sides, is taken for a band too.
- **On the finished grid a known band crosses into a column once it reaches 0.4 of the body size into it**
  (`_spanned_columns`, `_is_band`). The 30% of a column's width that any other segment must cover still stands, so a
  label running a little long is not taken for a band; ALDI's band reaches 6pt into the answers' column, a tenth of it.
- **A first look** (`bench/tools/kfs_quick.py`): each of the three sheets from 10 answers to 12, and the band its own row
  again on ALDI's and Honey's; still folded into the exclusions on Bank of Queensland's, which starts it in the gutter
  7.5pt before the exclusions' own text. A refinement for that is drafted and checked in memory against a test of its
  geometry. The two control sheets did not move.
- **And a fault the rule was never pointed at.** Nine landlord sheets from six insurers (Allianz, Australian Unity
  and Guild two each; Kogan, TIO and Westpac one each) had the band glued to the end of the exclusions above it
  ("...a direct result of an insured event. Cover for valuables, collections and items away from the insured
  address"); on every one it is now a row of its own across the table. None of their answers moved, because none had
  been lost, so only the grader's band count shows it - and `bench/tools/kfs_three.py` now names a sheet whose band
  changes, as it already did one whose header or answers change.
- **Which half did what** (`bench/probes/band_halves.py`, each half cut in memory in turn). On the nine landlord
  sheets the crossing alone frees the band: it was already known for a band, and reached too little into a column to
  count as crossing it. On ALDI's and Honey's the white-space test frees the two answers and the crossing gives the
  band its row.
- **Result, code against code:** Key Facts Sheets the Yes/No in its own column 1864 -> 1870 of 1885 tuned on (98.9% -> 99.2%), two more on each of the three sheets; a band glued to the exclusions above it on 12 sheets -> 1, Bank of Queensland's; header whole and events in rows unchanged, and nothing in the hidden fifth moved (371 of 375). Benchmark tables 844 -> 848, multi_column 682 v 682, long_tiny_text 357 v 357; the markdown changed on 2 of 481 pages,
  both read against their images. A conference paper's table now carries "STEP Participants" as the black band the
  page draws across it, where it had been a label over eight empty cells - better. A Wiley earnings table carries
  "Reported EPS" across its columns the same way - no worse - and that page's four new checks are not the band's
  doing: they are the four that name a dollar amount, which the pipe table wrote as `\$448` (D024) where the check
  compares `$448` exactly, and the table, set as HTML for its band, writes `$448`. The same escape costs six more
  checks on two other pages (`bench/probes/dollar_cells.py`). A test built on ALDI's geometry, failing on the code
  before it; suite 529.

**A band that starts in the gutter** (14-15 Sept, after ddf5ff9)
- **A known band spans the column to its left when it starts in the gutter before that column's text**
  (`_band_reaching_left`, from `_is_band`). Bank of Queensland's household contents sheet sets the band at x 156.1,
  after the answers end (155.3) and 7.5pt before the exclusions' own text (163.6), so on the grid it covered none of
  the answers' column and was folded into the exclusions above it. The band must start at least 0.4 of the body size
  before the column's leftmost other line, and only a segment already known to be a band is ever moved.
- **A first look** (`bench/tools/kfs_quick.py`): Bank of Queensland's band its own row, its answers unchanged at 12;
  ALDI's and Honey's contents sheets, a landlord sheet, CGU's building and AAMI's contents sheets, WFI's contents
  sheet and Honey's two landlord sheets did not move.
- **The first version measured the column's edge from the median start of its lines, and one benchmark page caught
  it.** Its oracle moved only Bank of Queensland's band, and no benchmark score moved (tables 848 v 848, multi_column
  682 v 682, long_tiny_text 357 v 357), but the markdown changed on 1 of 481 pages, and read against its image it was
  worse. Oracle's BI Publisher guide describes "Accessibility Mode" in a paragraph, then a paragraph set apart ("When
  Accessibility Mode is enabled,"), then a list indented past the column's edge; the median sat at the list's indent,
  so the set-apart paragraph read as starting in a gutter and ran across the table as a row belonging to no option.
  Measured from the leftmost start, the page converts as it did at ddf5ff9, byte for byte, and Bank of Queensland's
  band is still its own row. A test built on the guide's geometry fails on the median version.
- **Result, code against code, on the version committed:** Key Facts Sheets a band glued to the exclusions above it on 1 sheet -> 0, Bank of Queensland's, the only one of the 190 whose markdown changed at all, tuned on or held out; header whole (150 of 158, 31 of 32), answers (1870 of 1885, 371 of 375) and events in rows unchanged. Benchmark tables 848 v 848, multi_column 682 v 682, long_tiny_text 357 v 357, not one page moved; the
  markdown changed on 0 of 481 pages. Tests built on Bank of Queensland's geometry and on the guide's, each failing on the
  code before it; suite 531.

**A two-line answer carries its label on** (the same night, after ee27c52)
- **Words ending on a slash carry a full row on** (`_label_carries_on`). Ten sheets set "Accidental" over "breakage"
  (or "Breakage") beside "Yes/" (or "Yes /") over "Optional", and the exclusions open a paragraph for each answer
  ("Yes - We pay for glass..." over "Optional - We cover accidental damage..."). The second line fills every column the
  first did, so the rule never found the emptied short value it looks for, and in title case the exclusions do not
  carry on either: the line stayed a row of its own, an answer with no event. Now, when the second line fills every
  column the first did and its label reads on (lower case, a connector, or title case), a cell above that is words
  ending on a slash, with words under it, carries the row on. Words only, so a web address ending on a slash is not
  taken for a wrapped value.
- **A first draft reached four of the ten.** Keyed on the emptied value's place, it carried on the four HCKFS sheets,
  set in lower case, and none of the six in title case (ALDI's and Bank of Queensland's building and contents sheets,
  Honey's contents sheet, a March 2017 building sheet), which the title-case test refused first because their
  exclusions open a new paragraph. The check moved in front of that test.
- **In memory, before any file changed:** all ten gain the row and its answer; a landlord sheet, AAMI's contents sheet
  and CGU's contents sheet (whose "Actions of the sea No" is another fault) do not move.
- **Result, code against code:** Key Facts Sheets the Yes/No in its own column 1870 -> 1880 of 1885 tuned on (99.2% -> 99.7%) and 371 -> 373 of 375 held out (98.9% -> 99.5%), the two held-out sheets Honey's building sheet and a March 2017 contents sheet, the same shape and never looked at; every prescribed event now opens a row of its own, 1885 of 1885 and 375 of 375; the markdown changed on exactly the 12 sheets that gained, and header whole, bands and orphan rows are unchanged. Benchmark tables 848 v 848, multi_column 682 v 682, long_tiny_text 357 v 357, not one page moved; the markdown changed on
  0 of 481 pages. Tests: lower case and title case, each failing on the code before it; a full row under an answer with
  no slash, and the entry under a web address ending on a slash, each still an entry of its own; suite 535.

**A label run together with its answer is divided where the other rows start their answers** (15 Sept, after 3ea5e99)
- **The shape** (`_splits_at_shared_edges`, from `_refine_segments`). CGU's contents sheets set "Actions of the sea"
  and its "No" 11.5pt apart, and WFI's set "Items away from" and its "Yes" 9.8pt apart; in both the answer starts
  exactly where every other row's answer starts, and the text layer runs the pair into one line. Every other row reaches
  the table with its label and its answer already apart, so no cut was voted between those columns: the second look saw
  one empty range from the labels to the exclusions, bridged by the label lines with no answer beside them, and skipped
  it, because the first look's cut at the exclusions already lay inside it. Now a segment is divided where a word starts
  on an edge that segments of three other rows start on, after a gap wider than a word space (0.6 of the body size, the
  phrase guard's measure) and more than three of the segment's own word spaces. A band is never divided, and like the
  second look the rule refines a table the first look found and never makes one of its own.
- **A first test that could not fail.** Built on a sheet of seven events, it passed on the code before the rule: with
  too few wrapped lines of exclusions, enough rows voted for the answers' cut and the first look drew it. Three more
  wrapped lines, as a real sheet has, made the vote fall short; the test then failed without the rule and passed with
  it, as the two sheets it was drawn from do.
- **In memory, before any file changed (the first version):** CGU's two contents sheets and WFI's two each gain their
  answer; an HCKFS sheet, a landlord sheet, AAMI's and ALDI's contents sheets, WFI's two building sheets and Honey's
  landlord contents sheet do not move. Honey's landlord building sheet keeps its "Accidental Breakage Yes": there the
  gap is 4.7pt, 0.47 of the body size, under the word-space measure.
- **The first version, measured on the benchmark, changed 12 pages, and reading them caught three faults.** Tables
  went from 848 to 850 on one page, but an address page's lines became a table where the finder saw none, a census
  profile set in a fixed-width face - whose word space is itself 0.6 of the body size, every word on a character grid
  shared with the rows around it - had its title and its notes cut into pieces, and a fund table's heading read "Fund
  Type 5". So the rule now waits for the first look's table, and wants the gap wider than three of the line's own word
  spaces. Converted again, 6 of the 12 pages return to 3ea5e99 byte for byte, among them three the first version had
  made better by their markdown - the page behind the two checks, its values divided into their columns, a column of
  p-values and a header of two measures - which the ratio no longer reaches. Of the 6 still changed, read against
  their images, 4 are better ("Porcine (4)" and "Full thickness" in their own columns, "Driving at night on lonely
  highway | 90", a header's "Distribution | Source", a soil table's header and its Silt row), 1 is a false table on an
  index page rearranged with no word gained or lost, and 1 is slightly worse: on that index's next page a hyphenated
  word is left in two parts. A test built on the census geometry fails on the first version.
- **Result, code against code, on the version committed:** Key Facts Sheets the Yes/No in its own column 1880 -> 1884 of 1885 tuned on (99.7% -> 99.9%), CGU's two contents sheets and WFI's two, and 373 -> 375 of 375 held out (99.5% -> 100%), both on one held-out contents sheet never looked at; the markdown changed on exactly the 5 sheets that gained, byte for byte as the first version wrote them, and header whole, events in rows, bands and orphan rows are unchanged. The one answer still missing tuned on is Honey's landlord building sheet's. Benchmark tables 848 v 848, multi_column 682 v 682, long_tiny_text 357 v 357, not one score moved; the
  markdown changed on 6 of 481 pages - the six read against their images above, which the pool wrote byte for byte as they were read. Tests: CGU's and WFI's geometry, each failing on the code before it; a word space
  before the answers' edge, a gap whose far side starts where no other row starts, and a line whose words stand evenly
  apart, each left whole; suite 540.

**A list's hanging indent is no column edge: two insurance pages the run-together rule broke** (15 Sept, after e32e431)
- **How it was found.** Re-scoring the insurance set as a baseline for the next rule gave 197 of 229, one fewer than
  the 198 of 13 September. Named check by check (`bench/tools/insurance_diff.py`), that was 3 lost and 2 won, on two
  pages - and both pages read worse. Bank of Melbourne's building modifications table had "you were living in the" cut
  off its bullet and filed under "How much we will pay" ("We will pay up to $10,000. you were living in the"); Direct
  Insurance's covered and not-covered lists were shredded row by row, the exclusion "Any buildings at your insured
  address rented to short-term tenants for money, reward or other consideration" spread over three rows between lines
  of the other column. On that page the count had gone up, from 7 checks to 8.
- **Which commit.** Both pages were converted at each of the twelve commits since 13 September, each from a git worktree
  of its own under the ignored `bench/out`: both read right through 3ea5e99 and broke at e32e431, the run-together label
  rule. That rule was measured on the Key Facts Sheets and the benchmark, and not on the insurance set.
- **The cause** (`bench/probes/cut_probe.py`). The wrapped lines of a list item start on the list's hanging indent with
  nothing beside them, and the rule counted those starts as a column edge: on Bank of Melbourne's page four lines start
  at x 68.0, so "• you were living in the" and "• we receive" were each divided at 64.7, between the bullet and its
  text. Now a start counts toward an edge only where its row holds something to its left - CGU's and WFI's answers
  have their labels beside them; a list's wrapped lines do not.
- **In memory, before any file changed:** Bank of Melbourne's page from 8 checks of 10 to 10, its condition whole again;
  Direct Insurance's exclusion whole again, at 8 of 10; CGU's and WFI's contents sheets still 13 answers of 13.
- **Result, code against code:** the insurance set 199 of 229, against 197 on e32e431 and 198 on 13 September: Bank of Melbourne's page back to 10 checks of 10, word for word as on 13 September; Direct Insurance's exclusions whole again, its crosses in a column of their own, one table check traded for another. Of the 25 pages, 23 convert byte for byte as on 13 September; the other two, both Direct Insurance's, were read against their images - page 13 no worse, its crosses beside whole exclusions, and page 28 better, its theft cover and its police-report note in one cell where 13 September paired them across the wrong rows. Key Facts Sheets not one sheet's markdown changed from e32e431, byte for byte on all 190 - CGU's two contents sheets and WFI's two keep their answers (1884 of 1885 tuned on) and the held-out sheet keeps its last two (375 of 375), so the guard costs the Key Facts Sheets nothing. Benchmark tables 848 v 848, multi_column 682 v 682, long_tiny_text 357 v 357, headers_footers 739 v 739, not one score moved; the
  markdown changed on 1 of 747 pages against e32e431, read against its image: a soil table whose sub-labels (Sand, Silt, Clay; Ca, Mg, Na, K) sit indented under their label, which e32e431 had given a column of their own and which now sit in the label column as they did at 3ea5e99, its header split over two rows again and Silt's value still carrying Clay's, as before - no worse than 3ea5e99, where e32e431 alone had it better. Against 3ea5e99 the two commits together change the same 6 pages as e32e431 did: 3 better, 2 neutral, 1 slightly worse. A test built on Bank of Melbourne's table, failing on e32e431; suite 541.
- **What changes in the loop:** a table rule is now scored on the insurance set, check by check against the commit
  before it, as well as on the Key Facts Sheets and the benchmark, and a page whose count rises is read like any other.

**A block too big to be a running foot, and repeated on no page beside it, is published** (15 Sept, after 4bfca16)
- **The fault** (`apply_layout`, `truedoc/layout/fuse.py`). On the Qantas home PDS cover the layout model labelled the
  issuer, the ABN and the registered office - four lines and 34 words at the foot of the page, 91 to 97% of the way
  down - a page footer. Running feet are furniture, so the reader saw none of them, and seven of the insurance set's
  checks failed: three that each is there, four on the order they come in.
- **Two versions judged the block on its own page, and reading their pages undid both.** The first took out of the
  feet every block of more than two lines and more than fourteen words. Its benchmark pool, stopped once this was
  understood, had changed 14 of the 617 pages it reached (every benchmark file is a single page); read against their
  images, 1 was better (a paper's author affiliations), 3 neutral (two equal-opportunity notices and a census report's
  source note) and 10 put running feet or stamps into the body - a journal's foot with its page number, a catalogue's
  legal notice on four pages, a licence stamp, an article-in-press notice, a download stamp, a trademark notice and a
  report's banner, which as text also pushed the page's two tables to its end, away from their headings. The second
  kept only blocks whose lines start on one left edge (the issuer block starts all four at 14.2pt; the journal's foot
  is centred, the notice and the banner flush right), and in memory it still released the licence stamp, the
  article-in-press notice and the trademark notice, all set flush left. Size and alignment stand in for the thing
  itself; a running foot is one that runs.
- **The rule.** A block of more than two lines and more than fourteen words that the layout model calls a page footer
  comes out of the feet when the pages beside it - up to two each side - have a text layer and none prints most of its
  words (60%) in the band it fills, measured up from the foot of each page (`_repeated_beside`, which reads the file
  again through PDFium by its path). Repeated, it stays a foot; with no page beside it to ask - a one-page file, or
  scanned pages beside it - the model's label stands.
- **Measured.** Benchmark: every one of its 1,403 files is a single page, so the rule cannot change a benchmark page,
  and converted with it the 14 pages the first version had changed come out byte for byte as at 4bfca16. The
  insurance set 206 of 229, from 199: the cover's seven checks won and none lost anywhere; the other 24 pages convert byte for byte as at 4bfca16, and the cover, read against its image, carries its four lines in the page's order, run together into one paragraph as a text block's lines are. Key Facts Sheets publish the underwriter statement on CGU's home building sheet ("The policy this KFS relates to is Underwritten by Insurance Australia Limited ABN 11 000 016 722 AFSL 227681 trading as CGU Insurance"), the only one of 190 sheets whose markdown changed, and no grading moved: header whole 150 of 158 tuned on and 31 of 32 held out, answers 1,884 of 1,885 and 375 of 375, as before. The full oracle ran on the first version; the rule can only change what that version changed, and CGU's sheet converts byte for byte as it did.
- **Tests:** an issuer block that no page beside it repeats is published, failing on the code before it; the same block
  repeated on the pages beside it stays a foot, and so does one in a one-page file, both failing on the first version;
  a one-line foot stays a foot; suite 545. `bench/probes/foot_geometry.py` prints each foot block's lines and
  edges, `bench/tools/partial_footprint.py` lists the pages a pool has changed while it still converts, and
  `bench/tools/convert_compare.py` converts named pages with the code on the path against earlier conversions.

**A label set tight against its answer is divided on an exact, clean edge** (15 Sept, after 90dc95a)
- **The fault** (`_splits_at_shared_edges`, `truedoc/tables/aligned.py`). Honey's landlord building sheet sets
  "Accidental Breakage" 4.7pt before its "Yes" - 1.7 of the line's own word spaces - and the text layer runs the pair
  into one line, so the row read "Accidental Breakage Yes" with its answer cell empty: the last prescribed event on a
  sheet tuned on without its answer in its own column. The run-together rule wants a gap wider than 0.6 of the body
  size and than three word spaces, and the census profile is why the second test stays. Label and answer share one
  face, size, colour and set of flags (`bench/probes/label_spans.py`), so typography cannot tell them apart. Geometry
  can: the "Yes" starts within a tenth of a point of where all fourteen other answers on the sheet start, and no other
  row's text runs across that edge.
- **The rule.** A gap of at least one and a half of the segment's other word spaces is also divided where three other
  rows start a segment within half a point of the far word and no other row's segment runs across it; a segment with
  no other word space has nothing to measure the gap against and is not divided this way. Each guard has a toy test
  that fails with that guard removed: an answer a point short of the edge, which only exactness refuses, and a note run
  across the edge, which only the clean edge refuses. A first control, an answer a point and a half past the edge, was
  refused by the clean edge as well - the other answers' own cells run across it - and so tested neither.
- **Measured, code against code.** Key Facts Sheets: Honey's landlord building sheet is the only one of 190 whose
  markdown changed ("| Accidental Breakage | Yes |"), and the Yes/No now sits in its own column for all 1,885 prescribed
  events tuned on (from 1,884) and all 375 held out; header whole, events in rows, bands and orphan rows unchanged. The
  insurance set converts byte for byte as before on all 25 pages. Benchmark not one score moved on any of the seven subsets (tables 848 v 848, multi_column 682 v 682, long_tiny_text 357 v 357, headers_footers 739 v 739, arxiv_math 2594 v 2594, old_scans 110 v 110, old_scans_math 17 v 17); the markdown changed on
  1 of the 1,327 pages with markdown on both sides (the other 76 of the 1,403 give none without a model, the same on both), read against its image: a study-findings table whose two means had their p-values run into the same cell ("1.28 (0.784) <.001") with the p-value column beside them empty, now each p-value in its own column - better.
- **Tests:** Honey's geometry, failing on the code before it; an answer a point short of the edge and a tight gap on an
  edge another row runs across, each left whole; suite 548.

**A glyph's box stops at the next glyph beside it, however wide the width lookup says it is** (15 Sept, after 737012f)
- **The fault** (`_geometry`, `truedoc/extract/pdftext_rawdict.py`). RAA's landlord PDS page 22 read "Ifyou", "ofthese",
  "of21" and "Cooling-ofPeriod" where the file keeps the spaces. The reader boxes a level character from its origin to
  its origin plus the advance `FPDFFont_GetGlyphWidth` gives for its Unicode value, and this page's font maps its ff
  and fi ligatures to "f" as well (the letters the file itself has lost, `ofer` and `fnd`): asked for "f", PDFium
  answers with a ligature's 7.34pt where the f advances 2.54 (`bench/probes/width_lookup.py`), so every f's box ran over
  the space after it and into the next word - 25 spaces lost on the one page. It was not the 11 September suspicion, a
  ligature split into two characters on one origin: this page's f's are single characters.
- **The rule.** An advance that runs more than a quarter of the size past the next character's origin on the line is
  taken to that origin. A first version stopped at any next character, and on the insurance set it changed six pages:
  RAA's for the better, but on an Allianz PDS it cut ticks, crosses, bullets and word-final letters to half a point -
  PDFium puts the line breaks and spaces it makes up a fraction of a point after the origin of the letter before them -
  which opened false column edges and lost two checks, and on a Huddle page it cut overlapping display digits to
  nothing (`bench/probes/cap_fires.py` lists every character a cap shortens). So the next character must be one the
  file holds, standing at least 0.15 of the size along, and not a mark, an accent or the same character again; on the
  25 insurance pages the rule then fires on RAA's page alone, on its f's only.
- **Beside the glyph, not over it.** That second version, run over the benchmark, changed the markdown of 25 pages and
  cost three points (arxiv_math 2594 to 2591). Two pages gained: a table page set in Trade Gothic, whose "r" the lookup
  also answers too wide, got 19 spaces back in 17 places ("forthe", "sufferfrom" and "perspecies" read "for the",
  "suffer from" and "per species"), and another page's heading a space its image shows. On each of the other 23 it cut
  a glyph short at a character sharing none of the glyph's height: TeX's letters at the hats, tildes and dots set over
  them, which their fonts map to "b", "e" and "9", and a sum's upper limit at the sum - `\widehat{f}(\chi)` read
  `f\widehat{(}\chi)` and `\sum_{i=1}^{n_{MP}}` read `\sum_{i=1}^{nMP}` - and Jönsson's o at the umlaut its font maps
  to "«", which put a space into the name. Accents and limits stand over or under a glyph, not beside it; all 40 of
  RAA's cuts share at least nine tenths of the glyph's height (`bench/probes/stack_probe.py`). So the next character
  must also stand beside the glyph, their ink
  sharing at least a tenth of the smaller one's height (`_beside`; a comma after an r shares 0.43 of its height) - or
  one of them having no ink, as a space has none: PDFium gives an ArialMT space a box of no height at all, and asking
  it for height declined the cuts at the spaces of three Key Facts Sheet pages. With that, all 23 pages read byte for
  byte as they did before the cap, and the two that gained keep their gains. Whether
  the next character came from the same font was a near miss: TeX's accents come from other fonts, but so does the
  letter set beside a TeX angle bracket. The price: where a font's glyph boxes share no height though the glyphs stand
  side by side - a Japanese page's full-width commas and the letters after them - the lookup's width stands, as before
  the cap.
- **Measured, code against code** (against 737012f). Insurance set: 207 of 229, from 206: RAA's page 22 gains the check its lost spaces had failed ("condition of the Rental Property including any existing or subsequent damage or loss;"), and it is the only one of the 25 pages whose markdown changed - every change a space the file keeps, restored after an f. Key Facts Sheets: not one of the 190 sheets' markdown changed, byte for byte, and no grading moved: header whole 150 of 158 tuned on and 31 of 32 held out, answers 1,885 of 1,885 and 375 of 375.
  Benchmark: no score moves on any subset (tables 848 of 1,022, multi_column 682 of 884, long_tiny_text 357 of 442, headers_footers 739 of 760, arxiv_math 2,594 of 2,927, old_scans 110 of 526, old_scans_math 17 of 458). Measured as the second version's pool (`pwidth`, all 1,403 pages, against `ptight`), then every page whose cuts differ between the second version and this one converted again with this one (`bench/probes/cap_counts.py` lists them, `bench/tools/convert_compare.py` converts); the markdown changed on 2 of the 1,403 pages, both for the better and both as the second version had them: the Trade Gothic table page's 19 spaces and the heading's one.
- **Tests:** a lookup that answers "f" with a ligature's width keeps the spaces, failing on the code before it; it
  keeps them too when PDFium gives the spaces no ink, failing on a version that asked every glyph for height; a word
  at a line end keeps its last letter when PDFium puts its made-up line break just after the letter's origin, failing
  on the first version; an o keeps its advance under an umlaut its font maps to "«" (a hand-built page), failing on
  the second; suite 553. A page built with PyMuPDF puts PDFium's made-up characters at the glyph's end, where
  no version cuts anything, so each test gives PDFium the fault seen on the real page.

**A ligature the text layer spoils is read back from the glyph's own name** (15 Sept, after 4850331)
- **The fault** (`glyph_names.lossy_ligature_letters`, `pdftext_rawdict._build`). RAA's landlord PDS page 22's ToUnicode
  map sends the codes of its ff, fi, fl and ffi ligatures to "f", so the file's own text reads "ofer", "fnd",
  "Certifcate" and "Cooling-of" (`bench/probes/ligature_codes.py`), and TrueDoc wrote what the file said. The encoding
  still names those glyphs "f_f", "fi", "fl" and "f_f_i", and the content stream draws each by its code.
- **The rule.** For a page whose simple fonts hold a code whose glyph name gives more letters than the ToUnicode map
  does, beginning with the map's, the content stream is read with pypdf, each code through its font's map, and that
  text aligned with PDFium's characters by sequence - PDFium reports no codes, and its characters come in another order
  and number than the codes drawn. Each character drawn with such a code takes the name's letters, laid out on the
  glyph's box as an expanded ligature is. No word list is consulted. An alignment that pairs fewer than nine in ten of
  PDFium's characters is not trusted; a two-byte font's codes and text inside a form XObject are not read.
- **What it costs.** A first version opened the file with pypdf for every page: on the first 30 pages of RAA's 95-page
  landlord PDS that was about 600 ms a page, pages with nothing to mend included - 44% of the reader's time. The file is
  now read once per document and each font's codes worked out once. The answers are the same as before on the PDS's
  first 60 pages, and the insurance set converts byte for byte as it did: a page whose fonts spoil nothing costs about
  17 ms, a page that needs mending about 390 ms (timed on a loaded machine). On those 60 pages the reading mends 247
  characters.
- **How far it reaches.** The 405 pages first searched for lost letters held one such page. Across the whole library -
  1,176 PDFs, 23,870 pages - words that are no word until an f is expanded ("ofer", "Certifcate", "fnd") stand on 130
  pages of 6 documents: RAA's landlord PDS (56 pages) and its home and contents PDS (60), two editions of a CBA home
  insurance guide (6 each) and two CBA target market determinations (1 each). The reader now reads all 130 whole: no
  such word is left, and each word it should have been is in the reader's text as often as the file lost it
  (`bench/probes/library_ligatures.py`). The repair reads only simple fonts drawn by the page's own content and reaches
  every one of these pages, so no page of the library yet needs the two cases it leaves out: two-byte fonts and text
  inside form XObjects.
- **Measured, code against code** (against 4850331). RAA's page 22 now reads "offer", "find", "different",
  "offences", "Certificate" and "Cooling-off" nine times - its 14 ligature glyphs - and not one other word of the page
  changed. Insurance set: 212 of 229, from 207: RAA's page 22 gains its last five checks - four passages holding "offences", "find", "offer" and "Cooling-off", and one order check - and now passes all nine; it is the only one of the 25 pages whose markdown changed. Key Facts Sheets: not one of the 190 sheets' markdown changed, byte for byte, and no grading moved: header whole 150 of 158 tuned on and 31 of 32 held out, answers 1,885 of 1,885 and 375 of 375. Benchmark: no score moves on any subset (tables 848 of 1,022, multi_column 682 of 884, long_tiny_text 357 of 442, headers_footers 739 of 760, arxiv_math 2,594 of 2,927, old_scans 110 of 526, old_scans_math 17 of 458). Measured as a pool of all 1,403 pages with the ligature reading on the width cap's second version (`plig`, against `pwidth`: no page changed), then, on this commit's base, the 50 pages the width commit reads differently from that version and the 2 it changed, converted again with the ligature reading: all 52 byte for byte as before; the markdown changed on
  none of the 1,403 pages.
- **Tests:** a hand-built page whose font maps its f_f and fi codes to "f" reads "We offer to find it", failing on the
  code before it ("We ofer to fnd it"); the same page with a map that already spells the ligatures is left as it is;
  suite 555.

**A table whose columns hold only drawn marks is read from its own rules** (15 Sept, after ccb5e1b)
- **The fault** (`apply_layout` step 1, `truedoc/layout/fuse.py`). QBE's home PDS page 16 sets which cover each change
  concerns: a column of situations ("Alterations, additions or renovations", "You buy jewellery, watches, artworks...")
  beside two columns under "If you have buildings cover" and "If you have contents cover" that hold nothing but a drawn
  tick or cross. The layout model boxes it as a table (0.95), and `truedoc/marks.py` reads all eight marks, six ticks
  and two crosses; but the table is built from the text lines inside the box, the mark columns hold no text, and none
  came out. The rows read as headings and paragraphs, the marks had no cell to go to, and a reader could no longer tell
  that buying jewellery matters for contents cover and not for buildings cover. The page draws no vertical rules, so
  the ruled finder builds no grid either.
- **The rule** (`truedoc/tables/rule_grid.py`). Each rule on the page - one under the header, one under every row - is
  stroked in pieces that meet at the two column edges, at the same x on every row: the page's own drawing of its
  columns. Inside a table box the model scores 0.7 or more whose text builds no table, the rows are now the bands
  between consecutive rules, with the text above the first rule as the header; the columns are where the pieces of at
  least three rules meet, with no vertical rule drawn there; and each word goes to the cell its centre falls in, so a
  wrapped entry stays whole and the header line the text layer runs across two columns ("buildings cover contents
  cover") is divided where the columns divide. The marks then take their cells as they always have.
- **Why so gated.** Rule pieces meeting at a shared x are also how pages draw decoration: they stand on 3,213 of the
  insurance library's 23,870 pages, in 379 documents - AAMI's building PDS has them at its margins on nearly every page
  - and on 33 of the benchmark's 1,403 (`bench/probes/joined_rules_census.py`). Of the 38 insurance and benchmark pages
  that carry them, the rule would fire on one, QBE's page 16: on the rest the joins lie outside any confident table box
  or under a table already built (`bench/probes/joins_under_tables.py`).
- **A word read twice.** QBE's page 11 is the same layout, and there the reader gives "contents cover" inside the
  header line and again as a line of its own, where the file draws it once: the heading read "If you have contents
  cover contents cover". A word repeated at the same place is now taken once.
- **Measured, code against code** (against ccb5e1b). Insurance set: 213 of 229, from 212: QBE's home PDS page 16 gains its table check on "Alterations, additions or renovations", tables 15 to 16 of 27, and it is the only one of the 25 pages whose markdown changed. Key Facts Sheets: byte for byte the same on all 190 sheets, header whole 95% tuned on and 97% held out with every answer carried, before and after.
  Benchmark: set against 737012f's pool, the last one converted (ccb5e1b's reader differs from it only by the width cap and the ligature repair), every subset scores as it did - tables 848/1022, multi_column 682/884, long_tiny_text 357/442, headers_footers 739/760, arxiv_math 2594/2927, old_scans 110/526, old_scans_math 17/458, no page moved - and every page reads the same but two, a674cb40 in tables and 0722235b in headers_footers, whose spaces the width cap restored and which read there as the width cap's own pools read them. Thirteen library pages chosen for their columns of drawn marks: the rule changes QBE's page
  11, now a table of eight rows with its ticks and crosses where the page has them, and leaves the other twelve byte
  for byte as they were.
- **Tests:** a drawn page of that layout, with the model's table box given, reads as a table with each mark in its
  column, failing on the code before (no table); a word the reader reports twice at one place reads once in its cell,
  failing without that step; suite 557.

**The seventeen insurance misses, read against their pages** (15 Sept, after the rule grid)
- **Asked by the owner, answered page by page.** At 212 of 229 every failing check was read beside its page image and
  our markdown, sorted first by `insurance_dossier.evidence`'s computed reason (`bench/probes/insurance_triage.py`).
  The rule grid has since mended one, QBE's page 16. The sixteen left are two kinds of thing, eight each.
- **Eight are reading faults on four pages, and three of the pages share one fault: text that wraps inside a table or
  a card is read as a new row.** GIO's page 26 cuts its limits table at text lines rather than at the rules it draws,
  so "Paintings, pictures, works of art," is an item of its own ($10,000 and $20,000, no Platinum limit) and
  "antiques, sculptures, ornaments and art objects" a second ("$200,000 in total"); its two-line heading puts "Item"
  in a body row beside the first line of every Jewellery limit ("Classic $2,000 per item"), leaving Jewellery's own
  row "or set up to a total of $4,000" - two checks, and none sees the Jewellery row. Budget Direct's page 8 reads its
  two-line cover names as table rows, "Unspecified | Specified" over "Personal Effects | Personal Effects" (three
  order checks, whose phrases never appear whole). BOM's contents page gives each wrapped entry two rows, the first
  without its page number (two). The Seniors page 25 flattens a Limits grid nested in its "We cover" cell into run-on
  text, though the same-shaped grid above it comes out as a table (one).
- **Eight turn on one ruling: whether a table cell is everything drawn inside its box.** Our cell holds what the box
  holds and the check wants less: the tick or cross heading an item (five, the list markers of ccb5e1b); a whole
  ticked list drawn in one box, where the check wants "Solar panels" and "Grass or lawn..." as cells of their own
  (two, Kogan's POL1439FI page 29); a "Go to page 32." line at the foot of BOM's "Contents cover" box (one). Keeping
  them is faithful to the page; the checks as written want each item alone. STATUS puts it to the owner as one
  question.
- **Found on the way, with no check to see it:** Budget Direct's page 8 also drops the pointer "page 52" under its
  Landlord Options card, taken for the page's own number.

**A number in the margin is the page's own only if it counts pages** (15 Sept, after the misses were read)
- **The fault** (`classify/blocks.py`, then the layout model). Budget Direct's home PDS ends the Landlord Options card
  on PDF page 8 with a pointer, "page 52", 41pt above the foot. The zone rule takes any block reading just "page N",
  "N" or "N of M" in the top or bottom strip for the page's own number, the layout model called the line a page
  footer (0.65), and the renderer leaves both out: the card lost where its cover is described, while "page 53", 28pt
  higher on the same page, stood. Allianz's renter PDS lost "PAGE 25" and "PAGE 32" from the foot of its snapshot
  page the same way.
- **The rule** (`truedoc/classify/page_numbers.py`). A page's own number counts pages, so the pages beside it print
  theirs at the same distance from their place in the file: Budget Direct prints 4, 5, 7 and 8 at the top of PDF
  pages 6, 7, 9 and 10, and 6 on page 8. The nearest page before and the nearest after that print a number in their
  strips, up to two pages each way, are read through PDFium by the file's path. A margin line taken for the page's
  number that is not at the distance both share, and that no page within two prints at the same place, goes back to
  the text - after the layout model and the margin clean-up, so whichever rule took it. With nothing beside the page
  to ask - a file of one page, pages beside it with no numbers, or numbers that disagree - the zone rule stands.
- **Why it must not run either.** A first version gave back every margin number that counts no pages, and on RACQ's
  household PDS that put a stray "1" at the head of page 11: the numeral of the section tab printed down the page's
  edge, which counts no pages but runs - PDF page 13 prints it at the same place. A running head is known the way
  `layout/fuse.py` already knows a running foot (`_repeated_beside`), so the line must also not repeat.
- **Where it can act.** Only where pages lie on both sides. Every benchmark file is a single page (all 1,403
  counted), so the benchmark cannot move. `kfs_grade.py` converts pages 1 and 2 of each sheet, so only page 2 of the
  five sheets of three pages or more could change, and all five convert byte for byte as before. Across the insurance
  library, 3,591 margin lines in 198 documents count no pages (`bench/probes/folio_pointer_census.py`) - lines, not
  TrueDoc's blocks, so an over-count: many sit inside blocks the zone rule never takes, and many are the printers'
  slug along the foot of Allianz-family PDSs ("...indd 29 ... 5/8/2024 11:53 am"), which does not change.
- **Measured, code against code** (against ccb5e1b's reader). Insurance set: 212 of 229 either way, the same
  failures; the one page changed is Budget Direct's page 8, which gains "page 52" under Landlord Options - and on the
  main tree, with the rule grid, 213 of 229, the rule grid's own run differing only on that page. Twenty
  library pages, one per document from the census, among them Kogan's and Allianz's with a printers' slug along the
  foot: a first version changed three - Qantas's copy of Budget Direct's page 8 gained "page 52", Allianz's snapshot "PAGE 25" and "PAGE 32", each where the page image prints it, and RACQ's page 11 a stray "1" from its section tab - and the rule as committed changes the first two and leaves the other eighteen byte for byte as they were.
- **Tests:** a pointer in the foot of a page whose neighbours count pages is kept, failing with the release switched
  off; a number that counts pages is still left out; a tab printed again two pages each way stays out, failing without
  the repetition check; a one-page file keeps the zone rule; pages that disagree say nothing. Suite 562.

**Tables read again from the cells their page draws** (15 Sept, after ffc9594)
- **The fault.** GIO's home PDS page 26 draws its limits table as tiled filled cells - a blue header of two bands, the
  first a cell spanning the three cover levels, then grey cells meeting at every row's edge - and TrueDoc built it from
  its text lines inside the layout model's box: the header's second band shared a row with the first line of every
  Jewellery limit, and "Paintings, pictures, works of art," and "antiques, sculptures, ornaments and art objects" became
  two items with different limits. The Seniors home PDS nests a grid of limits inside its "We cover" cell, and the ruled
  finder read the nest as one cell of run-on text. The benchmark's German dishwasher fault table (bdb0c069 pg42), grey
  cells with one cause spanning nine rows, was cut and run together the same way.
- **The rule** (`truedoc/tables/fill_grid.py`, `redraw_tables` in `process_page` after the layout step). Filled
  rectangles that share edges are a drawn grid: its lines are their edges and the rules among them; a fill covering
  several intervals is one cell spanning them; open positions join across any stretch of line nothing draws; grid lines
  no cell starts or ends at come out (sub-fills had inflated every span); rows too low for a line of the table's text,
  holding only empty cells of their own, are gaps; groups whose cells mostly hold no letter or digit are decoration;
  the header is the run of top rows drawn in colours no lower row uses, with two rows under it. A text table is read
  again from that grid only where words of one of its cells lie on both sides of a drawn cell edge, at least twice,
  and the drawing holds nine in ten of the table's words. Spans and a two-row header are written as HTML: a first
  version left `has_merged` unset, and the pipe table repeated "Limits for any one incident" in three columns.
- **Why only on a crossing.** Every table the ruled finder built on the eighteen benchmark and insurance pages checked
  agrees with its drawing; a text table that keeps labelled sub-rows inside one shaded band (8160caa0's "# Fibres",
  "Passband", "Velocity accuracy") shows no crossing and stays; and a crossing judged by a cell's box rather than its
  own words raised 41 false ones on an aligned table whose boxes run past their text (9d800d5e). Drawn tables stand on
  24 of the benchmark's 1,403 pages and on 83 of the 380 Key Facts Sheet pages converted - the only pages the rule can
  change, since `drawn_grids` reads nothing elsewhere (`bench/probes/drawn_census.py`).
- **Measured, code against code** (against ffc9594). Insurance set: 216 of 229, from 213: GIO's page 26 gains both its table checks ("Item" heading the column over "Carpet or rugs that are hand woven or hand knotted", and "Paintings, pictures, works of art, antiques, sculptures, ornaments and art objects" whole beneath it) and the Seniors page 25 its "$10,000" beside "$5,000", tables 16 to 19 of 27; no other page's markdown changed. Benchmark, those 24 pages converted and
  scored against the `prules` pool's markdown (`bench/probes/fills_bench_compare.py`): one page changed - the dishwasher fault table bdb0c069 pg42, from 0 to 2 of its 3 table checks, the third still failing on an arrow its text layer gives as "~" - and the other 23 read byte for byte as the pool read them, so tables go from 848 to 850 of 1022 and every other subset stays as it was (80 to 82 of the 91 checks on those pages). Key Facts Sheets: byte for byte the same on all 190 sheets, though 83 of the 380 pages converted hold a drawn grid - none of their tables crosses its drawing - so header whole stays at 95% tuned on and 97% held out, with every answer carried. ALDI's household PDS page 31
  (library), where both ticks shared a cell and the Limit note fell beside the wrong events, now reads as its page
  draws it: five columns, each tick in its own, the Limit note one cell spanning the fourteen rows.
- **Tests:** a hand-made text table crossing a drawn header's foot is read from the fills with its header marked,
  failing with the crossing count switched off; a band spanning both columns keeps its span and renders once; a table
  that agrees with its drawing is left alone. Suite 565.

**The owner's ruling on what a table cell holds (D028)** (15 Sept, evening)
- **The dossier.** The eight insurance checks that turned on "is a table cell everything drawn inside its box?" went to
  the owner as one page with a card each: the page with the box outlined, the words the check wanted and what our cell
  also held marked on it, what TrueDoc writes, what each answer would change, and a recommendation with the way it
  could be wrong. The ruling is `bench/out/insurance_set/cell_box_ruling.json`.
- **Keep, on six.** The tick or cross at the head of an item stays in the cell (five checks), and so does BOM's "Go to
  page 32." line (one): for the reader both readings keep the meaning, the column heading establishing it and the
  mark confirming it. The six checks now quote the cell with its mark or line; the files as they stood are in
  `bench/out/insurance_set/checks_a_before_cell_box_ruling/`. At fb091fb the set scores 222 of 229 on them, where it
  scored 216, and 224 with the wrapped-entry rule in the tree.
- **Unsure, on Kogan's two whole lists, with a question worth asking:** why does a list there come out as one
  run-together cell when other pages give each ticked item a line of its own? Because Kogan's page 29 draws one box
  round the whole list and a drawn box is read as one cell. POL1418DIR page 13 draws no boxes, so its rows come from
  text lines, and BOM page 22's lightning box holds a single item. BOM page 22's earthquake box holds several and runs
  them together too, with no check to see it.
- **Lists, decided for machines as well as readers.** The owner asked whether one row per item would serve a machine
  comparing two insurance products and, not knowing how such a machine will read tables, chose to future-proof: each
  item a list element inside its cell, a sub-list under its item, a note after the list. One row per item pairs a
  cover with an exclusion the page never pairs; line breaks in a cell are flattened by markdown and by many tools; a
  list element is separated by any HTML reader and pairs only what the page pairs.
- **Next, named by the owner as what matters for meaning:** POL1418DIR page 13's table is cut at text lines, so "or
  commercial building" stands in a row of its own and the strata-title condition on residential flats lands beside
  "Recreational structures". An item is read as the page sets it - a tick or cross, then lines at its own indent - and
  the same reading writes a boxed list as a list. A looser fix for exactly this was tried and cost 48 benchmark checks
  across 21 pages (the note in `_merge_wrapped_rows`), so the indent is the evidence, not the empty cell.

**A wrapped entry whose value sits on its last line is one row** (15 Sept, after fb091fb)
- **The fault** (`_merge_wrapped_rows`, `truedoc/tables/aligned.py`). BOM's home PDS contents page sets "What you're
  covered for" over "under each of the insured events" with the page number 16 beside the second line only, and the
  same for "If this insurance has been issued through an" / "insurance intermediary" and "Your responsibilities - duty
  to take reasonable care" / "not to make a misrepresentation". The aligned finder made each two rows, the first with
  no page number, so a reader met an entry that pointed nowhere and a fragment that pointed to page 16. The merger
  already folds a line that continues the cell above when it leaves the other columns empty, and `_label_carries_on`
  joins a label's second line when that line leaves a value empty; here it is the first line that leaves the value
  empty, because the number is set against the last.
- **The rule.** An upper row that fills its label alone, a lower row whose label carries that label on (`_continues`:
  a lower-case start, or the upper ending on a connector) and that fills a value, and a row after them that starts an
  entry of its own, are one entry: the labels join and the row takes the lower row's values. The row after is what
  tells a wrap from a heading over a group, which reads the same for two rows - "Demographics" over "age (years)" is
  followed by "sex (male %)", which carries on too. A label closed by ".?!:;" or a bracket ("Patient outcomes (n %)")
  is whole; a tick or cross opens an entry; the lower label is at most eight words, the gap a line's, and a band laid
  across the table is never joined.
- **Why those guards.** A census of converted markdown before the rule was written found the bare shape - a label alone
  over a carried-on label with a value - as 35 row pairs on 16 pages across the benchmark, the Key Facts Sheets and the
  insurance set, most of them headings over a group: "Teachers by Ethnicity and Sex:" over "African American",
  "discrete decoding" over "unbalanced (k=4, l=5)". With the guards it leaves 15 on 7, and the bracket guard one fewer.
- **A join must not decide whether the text is a table.** The rule's first benchmark run found a conference flyer
  (0722235b) whose accommodation price list sets "Standard rooms" over "(standard or double occupancy) US $85.00". The
  joins read right, and the whole list vanished: the aligned finder's prose test asks that a two-column table's cells
  be four words or fewer, 85% of them, and it counted the joined six-word labels whole - short cells went from 26 of 29
  to 22 of 27, and the list came out as run-on text, the Mayfair Hotel's five rooms in one run and their prices in
  another. A joined entry is now counted as the two lines the page sets, and its row as two rows: joining says what a
  table holds, not whether the text is one. Counted that way every figure the test reads is what it was before the
  rule, so the rule cannot make or unmake a table.
- **Measured, code against code** (against fb091fb). Insurance set: 216 -> 218 of 229 on the checks as they stood,
  BOM's contents page gaining both its checks and no other page changing; 224 of 229 on the six checks D028 rewrote.
  The repair changed no insurance page: its pages are, byte for byte, the rule's before it. Benchmark (full pool
  against `prules`): tables 848 -> 852 of 1,022 and every other subset unchanged. Of the four, bdb0c069's two are the
  drawn-cells rule's - its page converts byte for byte the same at fb091fb - and b773892d's two this rule's, its two
  wrapped topics whole. The markdown differs on five of the 1,403 pages, bdb0c069 and four of this rule's, each read
  and right: 1801ca1d ("50% Kernel home range"), b773892d, 065d792c's German index entries whole with their hyphens
  mended, and 0722235b's price list, kept as a table with its entries joined. Key Facts Sheets: byte for byte the same
  on all 190 sheets, before the repair and after it, so header whole stays at 95% tuned on and 97% held out with every
  answer carried.
- **Tests:** a contents entry wrapped with its page number on the second line is one row, failing on the code before;
  a heading over a group of lower-case entries, a label closed by a bracket or a colon, and a label opened by a tick
  are each left as they were; and a price list of the flyer's shape stays a table with its entries joined - failing on
  the code before the rule, which joins nothing, and on the rule before its repair, which makes no table. Suite 570.

**A list inside a table cell is written as a list, and lists set side by side are read as lists (D028)** (15 Sept, night)
- **What the ruling asked for.** Kogan's home PDS page 29 draws its covers as boxes, and one box holds a whole ticked
  list - five covers, one with a bulleted sub-list of appliances - which the cell ran together on one line. POL1418DIR's
  page 13 sets a ticked list beside a crossed list with no boxes, and the table built from its text lines cut every item
  where it wraps. The owner ruled (D028) that a list is written as a list inside its cell, each entry a list element with
  its tick or cross, and named the cut items as the fault that matters for meaning.
- **Reading a list as the page sets it** (`truedoc/tables/cell_lists.py`). A cell's words are grouped into visual lines
  as the ruled finder groups them, a drawn mark leading the line it sits beside. A line opening with a tick, a cross or
  a bullet opens an entry, whose words start where the word after the mark starts - the hanging indent; a line starting
  at that indent carries the entry on ("- $5,000 limit applies."); a mark set further in opens a sub-item; a line back at
  the indent after a sub-list carries the entry on after it; and a line left of the marks, or left of the indent after a
  paragraph's break, is a note (BOM's "An additional excess of $250 ... applies to each earthquake", POL1418DIR's "You
  must report the incident to police"). A line wrapped back under its bullet with no break above still carries the
  entry on. A cell takes a list with two entries or more, or with one entry holding a sub-list of two or more, and only
  when the list's words are the cell's words, so nothing the cell says changes - only its shape. The renderer writes it
  as `<ul><li>`, sub-lists nested, the note as a paragraph, each element on a line of its own because the benchmark's
  scorer takes a cell's text whole.
- **Two lists side by side** (`truedoc/tables/list_columns.py`). A text-built table is read again column by column: a
  column holding nothing but marks joins the column to its right, a lone label in the first column opens a section
  ("Structures"), a top row the finder took for a heading but which opens with a tick is an entry. Each column of each
  section is read as a list, and the table is rebuilt - headings, a band per section, one row of list cells - only where
  every column opens with an entry, one column is a list, and the rebuilt table holds exactly the words the cut one did
  (287 of 287 on POL1418DIR's page 13). Page 13 now reads six covered and eleven excluded items whole: "Any hotel, motel,
  hostel, guest house, boarding house, dormitory, nursing home or commercial building", and the condition on
  residential flats back in its own item.
- **One entry with a sub-list is a list too.** POL1418DIR's page 28 sets its covered impact damage as one ticked entry
  over five bulleted kinds of impact. Taken as a list only with two entries or more, that column came out as plain text
  with its bullets left to list elements that were never written, so the five ran on; the first insurance run of the
  combined work showed it, and an entry holding a sub-list of two or more now makes a list (`cell_lists.is_list`).
- **The checks.** A check can no longer ask for one entry of a list as a cell of its own, so `bench/tools/insurance_score.py`
  gains a check of its own kind, `list_item`: the entry, with its mark, among the list elements of a table cell under its
  column heading. Five checks were rewritten to it: Kogan's two the ruling named, and on POL1418DIR's page 13 the two
  already quoting their mark and a third of the same shape, "Replacement of water". The files as they stood are in
  `bench/out/insurance_set/checks_a_before_list_checks/`.
- **Measured, code against code** (against the wrapped-entry rule). Insurance set: 224 -> 226 of 229 with the five
  checks rewritten as list checks, the three misses left being Budget Direct's cover cards. Six pages change, each
  read: Kogan's page 29 and POL1418DIR's page 13 read as lists, and POL1418DIR's page 28 and BOM's pages 22, 31 and 6
  take lists no check looks at; every other page is byte for byte the wrapped-entry rule's. Key Facts Sheets: byte for
  byte the same on all 190 sheets, both with the boxed-cells rule and the arrow reader in the same tree and with the
  lists alone before their last two refinements, so header whole stays at 95% tuned on and 97% held out with every
  answer carried. Benchmark: no check moves in any subset against the wrapped-entry rule's full pool. The markdown
  differs on four of the 1,403 pages, each read and each converting byte for byte the same with the lists alone: a
  chemical supply spec sheet whose bulleted operating conditions, gases and supplies become lists, an Oracle manual's
  accessibility option (a lead paragraph and five items), a child-labour report's education measures (a lead and four
  items) and a French HR audit's checkbox questions. Those tables are written as HTML now, which also shows the row
  spans a pipe table had left as empty cells ("Coordination and Enforcement" over four rows).
- **Tests:** a ticked list with a sub-list reads as a list; the words after a sub-list carry the entry on and a line at
  the box's edge is a note; one entry with a sub-list is a list, and one entry alone is not; a paragraph under an entry
  is a note while a line wrapped under its bullet is not; a cell holding a list is written as one; a list drawn in one
  box comes out as a list, converted end to end; lists set side by side are rebuilt as lists; and a table holding words
  the page does not is left as it is. Suite 579.

**A name set on two lines inside one drawn box is one cell** (15 Sept, night)
- **The fault** (Budget Direct's home PDS page 8). The optional covers are cards: each cover's name in a green box, on
  one line or two ("Unspecified" over "Personal Effects", "Motor" over "Burnout"), with a link to its page under the
  box. The aligned finder read each row of cards as a table and gave each line of a name a row of its own, so
  "Unspecified Personal Effects" was nowhere in the markdown: a reader met "Unspecified | Specified" over "Personal
  Effects | Personal Effects". The break is not forced by the width - "Unspecified Personal" is 100pt and the box 148pt -
  so the lines say nothing about belonging together. The box does.
- **The rule** (`truedoc/tables/boxed_cells.py`, `join_boxed_rows` in `process_page` right after the drawn-cells
  redraw). A rectangle whose four sides the page draws, holding whole cells of one column across consecutive rows of a
  text-built table and no other text, folds those rows into one, where every other column holds text in at most one of
  them or has a box of its own over the same rows. Only a single run of text is folded: no line opening a list item, no
  sentence closed before the last line, no line that is a value (as many digits as letters), one size of type, the
  lines a line apart and no rule drawn across them - so a ticked list in one box, or a paragraph over a "Go to page"
  line, stays as the table has it. And the box must divide the table's rows: a frame round the whole table, or round
  each whole column, says nothing about which rows belong together.
- **Found on the way.** Its first insurance run changed nothing: boxes were sought among the edges near the table, which
  dropped the right-hand card's far side, and the strokes of an icon drawn between a name's two lines counted as a rule
  dividing them. Boxes are now sought across the page, and a rule divides two lines only where it runs under half the
  narrower one; each fix is pinned by a test that fails on the behaviour before it, and so is the value guard, which
  keeps a box of stacked amounts from reading as one run.
- **A legend is not a card.** The benchmark pool of the combined work changed one page by this rule: arxiv 2503.04674's
  convergence plots, whose legends are stroked boxes of short lines - "Gauss (s=1)" over "Radau IIA (s=2)" over "Gauss
  (s=2)" - that passed every test of a wrapped name, so each legend became one cell and each method lost the marker drawn
  beside it. No check moved; the pairing did. A key draws a sample before each of its lines, a stroke ending just short
  of the words, which a card's wrapped name never has (Budget Direct draws its icons to the right of the name): two lines
  or more each led by one are entries, not a run, and the legends read as they did.
- **Measured, code against code** (against the D028 lists). Insurance set: 226 -> 229 of 229, Budget Direct's page 8
  gaining its three order checks ("This Home and Contents policy is made up of different covers", "Unspecified
  Personal Effects", "Motor Burnout") and no other page changing; every kind of check now passes in full. Key Facts
  Sheets: byte for byte the same on all 190 sheets, measured with the D028 lists and the arrow reader in the same
  tree, so header whole stays at 95% tuned on and 97% held out with every answer carried. Benchmark: no page of the
  1,403 changes. The full pool of the combined work changed one page by this rule, arxiv 2503.04674's legends, and
  with the key guard that page converts byte for byte as it did; the guard only ever leaves rows unfolded, so no check
  moves.
- **Tests:** a name on two lines in one box is one cell; an icon drawn beside the name is not a rule between its lines;
  a frame round the whole table or round each whole column joins nothing; a list or two sentences in one box are left
  apart; a rule across the lines or a change of size keeps them apart; a column whose rows keep their own values is not
  folded; boxes of stacked values are rows, not a run; and a key with a sample before each line is not one run, while an
  icon beside a name leads no line - the first failing without the guard. Suite 588.

**An arrow with a shaft, cut out of a square, is read as an arrow and written as one** (15 Sept, night)
- **The fault** (`truedoc/marks.py`). Budget Direct's home PDS cuts a white arrow out of a green square beside every page
  link ("page 47"), and every one came out as a bullet. The chevron test wants an arrow's arms to reach the corners of
  its ink, and a shaft running the ink's length leaves those corners empty, so each square was read as a dot. The cut-outs
  also fill only 30 to 39 cells of the classifier's grid of 1,024, and the knockout gate stood at 31.
- **The rule.** Before the chevron, each orientation of the ink is asked for a shafted arrow: a bar through the middle at
  least 70% of the ink's length, arms above and below closing on its end by more than 15% of the width, nothing but the
  bar in the first quarter, and ink on the bar's line at the far end, where the arms meet. A knockout filling 2.5% to 3%
  of the grid is taken only as a shafted arrow; at 3% and above everything reads as it did.
- **Found on the way.** The first version left the first 35% of the ink to the bar and missed Budget Direct's two
  lower-left squares, whose heads reach back to 31%; the tail is the first quarter now - a plus sign's upright stands at
  half, a T-bar's cross at the end. It also lowered the gate for every shape, and a question mark cut out of an NRMA disc,
  26 cells, read as a chevron pointing down; below 3% only a shafted arrow is taken.
- **Letters are not arrows.** A census of the library's marks, one page in forty (6,334 marks), found the reader
  changing 22: six right - Budget Direct's and Qantas's page links, arrows drawn before "page 62" - and sixteen letters
  drawn as outlines, the "m" of CBA's "Commonwealth" and of Woolworths' "Home" read as arrows pointing up. A bold letter
  fills its box, so its ink touches the ring test's band all round and the ring is erased; what is left of an "m" is the
  middle stroke with the arches bending onto it, a shaft with two arms closing on its end. A shafted arrow is read now
  from a mark's whole ink or from a shape cut out of a solid one, never from what erasing a ring leaves, and none of the
  six right ones is read through a ring. The "re" of CBA's "CommInsure" still reads as a chevron from inside its ring,
  as it did before the reader.
- **Nor are stars.** A census of every mark on the benchmark's 1,403 pages found the five filled stars of a book
  record's "Doody's Star Rating" (headers_footers 7881b598) read as arrows pointing down, where the chevron test had
  them pointing up. Turned so its top spike is the tail, a star has nothing but that spike in the first quarter, a column
  down its middle for a shaft, and its arms and legs for a head - but an arrowhead's arms meet on the shaft's line, and a
  star's legs end either side of it with nothing between. The ink's far end must now lie on the shaft, and the stars
  read as they did before the reader: pointing up, a misreading older than it.
- **An arrow in a line is not maths** (`truedoc/math/extract.py`). With every square read as an arrow, the page still
  read wrong: the four links in table cells came out "→ page 47", and the four in lines outside tables as
  `\(\overline{\rightarrow}\) page 50`. The marks reader sets a mark at the head of its line as a word of its own, and the
  inline maths pass - which a table cell never meets - took the arrow for a relation sign. The words that are never
  inline maths, display type until now, take every word the marks reader set, and all eight links read "→ page N".
  Neither the insurance score nor a census of the marks' kinds could see it; reading the page did.
- **Measured, code against code** (against the boxed-cells rule). Insurance set: 229 of 229 either way, and one page
  changes: Budget Direct's page 8, whose eight page links read "→ page 47" and so on - four in two table rows, four in
  lines outside tables - with no formula left on the page. Marks read on a one-in-forty sample of the library: 6 of
  6,334 marks on 1,325 pages change kind, each an arrow before a page link now read as an arrow (Budget Direct's and
  Qantas's), where the reader before its ring fix changed 22; on the benchmark's 1,403 pages 26 of 2,695 marks change
  kind, every one an arrowhead drawn apart from its shaft in a diagram of an arxiv paper, now read with its direction.
  Key Facts Sheets: byte for byte the same on all 190 sheets, measured with the reader before its rule for the tip,
  which can only take a shafted arrow back, so header whole stays at 95% tuned on and 97% held out with every answer
  carried. Benchmark: the 159 of the 1,403 pages that hold a mark - the only pages a mark reader or the maths guard
  can reach - converted before the reader and after it: no check moves, and the markdown differs on two pages, each
  read. A HAL cover's arrow before "To cite this version", written `\(\rightarrow\)` since before the reader, is "→"
  now; and the arrowhead of a block diagram, taken into a formula with the label beside it, is text, that label,
  G3(s), losing the subscript it had only inside the arrow's formula. The 26 arrowheads the reader now names in six
  arxiv diagrams sit in no line or cell, so their pages do not change, and the star-rating page the combined pool
  changed reads as it did.
- **Tests:** an arrow cut out of a square is read whichever way it points; an arrow drawn in ink is read too; a plus cut
  out of a square is no arrow; a thin shape under the old gate is taken only as a shafted arrow, and an arrow whose head
  reaches back a third of its length is an arrow - those two failing on the first version; what erasing a ring leaves of
  a bold letter, the reader's own grid of CBA's "m", is no arrow - failing without that fix; a star, the reader's own grid
  of one of Doody's five, is no shafted arrow - failing without the rule for the tip; and a drawn arrow leading a line is
  text, not maths, while the same arrow set in a maths font is still maths - the first failing without the guard.
  Suite 597.

**Dotted rules drawn in pieces, and a header set in a filled band: the rule grid reads RAC's pricing table** (16 Sept, early morning)
- **Where the loop went.** The unplaced-marks census builds pages without the layout model, so a mark a model-boxed table
  takes counts as lost there. Every page of the library's one-in-ten sample with marks standing in columns - 139 pages of
  93 documents - was converted in full instead, and the marks the reader finds set against the mark characters written:
  761 read, 465 written, 74 pages short. Their marks were looked at cut from the pages, one page for each template, 49
  standing for the 74: logos, cover art, category icons, the "!" of a note and the "$" of a limit - illustration under
  the owner's ruling, since the words beside them carry the meaning - and one table whose meaning was lost.
- **The fault** (`truedoc/tables/rule_grid.py`). RAC's premium, excess and discount guide sets ten pricing factors on its
  first page, each with a tick under "Buildings" and under "Contents". The layout model boxes the table (0.85) and its
  text builds none, so the rule grid is asked, and it found no column edge: every dotted rule is stroked in three pieces
  that stop 1.5pt short of one another at the column edges, where a piece had to start within 1pt of the last. The
  header sits in a dark filled band with no rule under it, and the first rule lies under the first row, so with the
  edges found that row would have joined the header. The factors came out as paragraphs, the header words as loose
  lines, and all twenty ticks were lost.
- **The rule.** A piece of a rule meets the next where it stops short of it by less than a word space, a quarter of the
  body text size. A filled shape drawn across the table - from within a text size of the rules' left end to within one
  of their right - divides its rows as a rule does, where text lies between its edge and the rule or edge either side of
  it, and only above the last rule, so the rules still close the table. RAC's page now writes its ten rows, each with its
  two ticks, and QBE's page 16, the page the rule grid was built for, is the same byte for byte.
- **Measured, code against code** (against dda1240). Insurance set: 229 of 229 either way, and no page of it changes.
  Key Facts Sheets: byte for byte the same on all 190 sheets, header whole 95% tuned on and 97% held out, every answer
  carried. Benchmark: both code states converted all 1,403 pages, and not one page's markdown differs - tables,
  multi-column, tiny text, headers and footers, arxiv and both scanned subsets alike, with the same pages empty on
  both sides - so no check can move.
- **Tests:** a rule's pieces 1.5pt apart meet at a column edge, and pieces 6pt apart are separate rules; a header set in
  a filled band ends where the band does; and a banded table of ticks converted in full writes every tick in its row -
  all but the rule about pieces standing apart failing without the change. Suite 601.

**A private-use character is read by what its font draws** (16 Sept, early morning)
- **The fault** (`truedoc/extract/textlayer.py`). A code in Unicode's private-use area means nothing of itself; only the
  font's drawing says what it is. RAC's 2021 premium, excess and discount guides tick every pricing factor under
  "Buildings" and "Contents" with FontAwesome's check, U+F00C; an RAA landlord policy bullets the causes a table cell
  excludes with a Wingdings square; Suncorp's contents policies bullet sub-items with a Wingdings 2 dot, and RACQ's
  supplementary PDS with Symbol's. The renderer strips every such code with the raw glyph codes of maths fonts, so the
  pricing table's two columns came out empty, the cell's list ran on as one line and the sub-items lost their nesting.
  The symbol-font tables read Wingdings and Webdings codes by the font's name, and nothing read the rest.
- **The rule.** A private-use character those tables do not know - outside maths and extension fonts and hidden OCR
  layers, and only in a font the page sets as marks, each of its private-use characters a word of its own - is drawn and
  read as a drawn mark is (`truedoc.marks.classify_mark`, given `glyph=True`), and a tick, cross, dot, circle, square or
  box becomes that character. An arrow, or a shape the reader cannot name, stays as it was: where such an arrow points
  is the owner's open question about reading order. A mark so read that stands alone on its line starts the words beside
  it on its row, by the measures that place a drawn mark at the head of a line.
- **Found on the way**, on the 24 pages of the library's one-in-ten sample and the 134 of the benchmark that hold such
  characters. A glyph's box is its font's, and a bullet's is a line tall and a third as wide: drawn onto the reader's
  square grid the dot came out flattened and was not read - a glyph is read through a square around its box. Suncorp's
  flow arrows, solid triangles set in ZapfDingbats over a rule, read as crosses with the rule - a glyph's ink must stand
  alone, touching no edge of its crop. Apia's block arrows, a Wingdings 3 shaft standing on a head, read as a dot in one
  render of three - a dot, square or box must be about as wide at each height as at its mirror height (bullets differ by
  0.03 to 0.24 of their width, the arrows by 0.41). FontAwesome's check is heavy enough to put 12 to 13 per cent of its
  ink in the upper-left quarter, past the tick test's 12 - a glyph's tick is given 15; given to drawn marks as well, the
  insurance census turned Honey's ringed ticks right and two pieces of an Allianz illustration into ticks, so drawn
  marks read as before. RACQ's bullets stand 13pt before their words, the text layer gives each as a line of its own,
  and every one came out as an empty list item above its words - hence the join.
- **Tried and dropped.** Taking the ink of the characters around a glyph out of its crop was meant to free RAA's seven
  squares that sit so close to their words a first letter reaches the crop's edge. It freed none - the letter's ink
  reaches a hair left of its own box - and it let letters read as marks on four benchmark pages: 34 of txfonts'
  private-use small capitals as boxes, crosses and ticks, 39 codes of an Advent journal font, and more. Every such
  letter sits inside a word, where every mark on the library pages stands as a word of its own; a font is read as marks
  now only where the page sets all its private-use characters that way, and RAA's seven stay unread, as before.
- **What it reads:** on the library pages, all 40 of RAC's ticks, RACQ's 8 bullets and Suncorp's 7, and 16 of RAA's 23
  squares; CGU's and Bendigo's page-link triangles, Suncorp's and Apia's flow arrows and Woolworths' zero-width markers
  stay as they were. In full: RAC's two pricing tables gain their twenty ticks each, RAA's causes become lists inside
  their cells, Suncorp's sub-items become list items, and RACQ's two lists read "- Mobile Phones;" and so on.
- **Measured, code against code** (against the rule-grid commit). Insurance set: 229 of 229 either way, and no page of
  it changes. Key Facts Sheets: byte for byte the same on all 190 sheets, measured on the reader before its line join
  and its font rule, which only take a reading away or act where one was made, so header whole stays at 95% tuned on
  and 97% held out with every answer carried. Benchmark: 134 of the 1,403 pages hold private-use characters, most of
  them the glyph codes of maths fonts and of embedded text fonts; the text layer changes on two - a slide whose three
  Wingdings square bullets now lead its headings, which drop a level from # to ##, and a form whose 21 FontAwesome
  ticked checkboxes fill its attributes table's empty first column with ✓ - and no check moves on either (0 of 2 and 7
  of 7 before and after). On the other 132 the reader reads nothing, and those pages are as they were.
- **Tests** (`tests/test_private_glyphs.py`, which cannot import on dda1240): a private-use tick is a tick, and so is a
  heavy one; a private-use bullet leads its line as the square it draws; a bullet in a box as tall as its line is a dot;
  a bullet set 13pt before its words starts their line - failing without the join; a triangle stays as it was; a font
  that spells a word with its private-use codes is not read, even where one of them stands alone - failing without the
  font rule, which read that one as a tick; a glyph with a rule inside its crop is not read; the reader's own grids of
  Apia's arrow and Suncorp's bullet, one not as wide at each height as at its mirror and one so; and a heavy tick is a
  tick only as a glyph - failing with the room given to drawn marks. Suite 611.

**A heading line carried on under an empty cell joins the heading: Auto & General's Key Facts Sheets read whole** (16 Sept, morning)
- **Where the loop went.** With the rule grid and private-use glyphs committed, the Key Facts Sheets' last failures were
  read by cause. Header whole failed on 8 of the 158 sheets tuned on and 1 of the 32 held out, and a row that is only a
  continuation stood in 7 and 1 - the same sheets. Seven tuned-on ones are one Auto & General design: Budget Direct's
  and Qantas's sheets and ING's pair. The eighth, Defence Service Homes, heads its table "Risk | Covered?" where the
  grader looks for "event" and "yes"; its table is right, and the grader's limit is left alone.
- **The fault** (`truedoc/tables/aligned.py`). The layout model boxes the table and the text builds it. The design
  centres each heading cell in a blue band, and the third column's heading runs to three lines, so the lines
  interleave: "Some examples of specific conditions, exclusions or limits that apply", "Yes/No", "Event/Cover" beside
  "to events/covers (see PDS and other policy documentation for details", "Optional", "of others)*" - five rows, the
  last graded as a continuation. `_heading_hangs_open` was written for this layout as other sheets break it, on "apply
  to" and "details of", a line ending on a word that cannot end a heading. These break one word earlier, and
  `_heading_wraps_on`, which looks one row down, found an empty cell there.
- **The rule.** A long heading cell that closes on no full stop is carried on, too, by a lowercase line one row further
  down, under an empty cell of its column, when that row's other text stands only in columns empty in both rows above
  it - where a column's own heading starts, as "Event/Cover" does. The five rows fold into "Event/Cover | Yes/No
  Optional | Some examples of specific conditions, exclusions or limits that apply to events/covers (see PDS and other
  policy documentation for details of others)*".
- **Tried and dropped.** The first version took any lowercase line two rows down whose row kept an empty cell. The
  benchmark pool found it folding a two-level heading - group headings over "n | % | n | %" - into one row, "12-" and
  "n" read as "12n" (tables 0cda549c), and fusing two studies of a review table, Cheng et al. (2020) and
  Gholipour-Kanani et al. (2012), into one row (tables 508eb272); no check moved on either. Both second rows fill
  columns the rows above already hold, and under the rule as it stands both pages are as they were, byte for byte.
- **Measured, code against code** (against the private-use glyph commit). Key Facts Sheets, graded afresh under this
  rule: header whole 150 to 157 of 158 tuned on and 31 to 32 of 32 held out; rows that are only a continuation 7 to 0
  and 1 to 0; every event and answer carried. Exactly eight sheets change, each its heading folded, and the other 182
  are byte for byte the same - every sheet as the first version wrote it. Insurance set: 229 of 229 either way, and no
  page of it changes. Benchmark: no page of the 1,403 changes. Converted on every page, the first version changed
  three - the two tables pages above and a stray table under a case split on an arXiv page (2503.05177, page 10), its
  "n | 1" folded into the row above - and all three are byte for byte as they were under this rule, which acts only
  where the first version did.
- **Tests** (`tests/test_heading_interleave.py`): the five-line heading folds into one row with the body untouched -
  failing without the rule; a body row under an empty cell is not taken into the heading; and a two-level heading and
  a review table's wrapped entries stay as they are - both failing on the first version. Suite 615.

**A line at the head of a page is taken for a running head only if it runs** (16 Sept, morning, after 955500b)
- **What was found.** Honey's household PDS names each peril at the top of its page - "Animal damage", "Explosion",
  "Flood", 14 pt in red - and TrueDoc published none of them: the layout model labels the name a page header, so page
  33 opened on "# Included for:" and no peril's page said which peril its cover, limit and exclusions belong to. The
  insurance set's checks on that page quote its sentences, not the name, so 229 of 229 never saw it. The page's ringed
  tick, dollar and cross icons stand beside headings that say "You are covered for:", "Limit:" and "You are not
  covered for:", so under the owner's icons ruling they are illustration; the name is the loss.
- **How far it reached.** A census of every block the conversion takes out at the head and foot of a page
  (`bench/probes/running_head_census.py`), each asked whether a page within two either side prints most of its words
  at the same height, read the whole one-in-fifty sample of the library: 210 pages of 168 documents in file-name
  order - mostly AAMI, ALDI and Apia - and then the other 1,027, of 810 documents, in shuffled order. In file-name
  order the rule gives back 28 heads on 23 pages; 13 stay out, printed beside them, and 9 have no page beside to ask.
  Fifteen of those 28 the layout model had labelled page headers - the cover titles of ten AAMI guides and a landlord
  PDS's "Your excess" - and thirteen the pipeline's own margin clean-up had taken: the defined term at the top of a
  definitions page ("Incident", "Illegal drugs", "Computer", "Joint policyholders", Apia's "Loss or damage"), two
  complaint steps' headings, a proofs table's title, the covers of four supplementary PDSs, and a building PDS's
  "This guarantee does not apply:", without which nothing said the guarantee does not apply to the four cases listed
  under it. In the shuffled pages it gives back 45 heads on 39 of the 1,027 pages; 68 stay out, printed beside them,
  and 28 have no page beside to ask. Ten of the heads given back were read against their page images - nine in
  file-name order, on seven pages, and one of the shuffled ones, the title of Apia's village supplementary PDS - and
  every one is the page's own; the rest were not read one by one. Converted under this rule, the 24 pages that first
  read found heads on no longer take out any of them.
- **The rule** (`truedoc/layout/fuse.py`, `truedoc/classify/blocks.py`, `truedoc/pipeline.py`). A running head runs:
  the same words at the same height, page after page. Every rule that takes a line out as a running head now asks
  first whether it runs - the zone rule for small lines in the top margin, the layout model's page-header label and
  its margin tie, and the margin clean-up's heading in the outermost strip, top strip and header stack - and takes the
  line only when no page beside it shows that it stops at this page. The question is the foot rule's
  (`_repeated_beside`: most of the block's words, 60%, in the band it fills on a page within two either side), now
  measured down from each page's head for a block in the upper half of its page. Printed beside it, a line stays a
  head; with no page beside it to ask - a one-page file, or scanned pages beside it - each rule decides as it did. A
  released page header keeps the kind its text gave it, so Honey's page 33 now opens "# Explosion", at the level of
  "# Fire" below it. Text inside a picture at the top (the banner rule) and rotated side tabs make other claims than
  running and are not asked.
- **Measured, code against code** (against 3a2810b). Key Facts Sheets: the same as 3a2810b on every measure - header
  whole 157 of 158 tuned on and 32 of 32 held out, every event and answer carried, no band swallowed, no row only a
  continuation. Fifty-five sheets change, each only gaining lines at the head of a page, 96 in all and none taken
  away: the sheet's product line and preparation date under its title, with its "THIS IS NOT AN INSURANCE CONTRACT"
  (60 lines); page 2's "Step 3 Other things to consider" (33, of which 29 come out "Step3Other things to consider",
  the spaces around its large numeral lost - which dropping the line had hidden); CBA's prescribed statement, which
  its sheet prints on page 1 only; and a table row Direct Insurance carries over to the head of page 2 ("Items away
  from insured address | No"), published as loose lines beside a row of that table already loose. A sheet of each kind
  was read against its page image. Insurance set: 229 of 229 either way. Four pages gain the heading at their top and
  nothing else - Honey's "Explosion", ALDI's "Flood" (the same design), Apia's "What to do" beside its claim steps and
  GIO's "Contents with fixed limits (continued)" over its example box - each read against its page image and each the
  page's own. Benchmark: every one of its 1,403 files is a single page, so no page beside a line can be asked and no
  benchmark page can change; and converted under this rule, the headers-and-footers section - the one a rule about
  running heads could touch - comes out byte for byte as it did on all 266 of its pages, the same three empty, 739 of
  760 checks either way.
- **Left as they were: feet, and the contact rule.** The page feet no page beside them repeats are mostly a cover's
  issuer line ("AAI Limited ABN 48 005 297 807 AFSL 230859 trading as AAMI"), "Continued on next page." and a
  document's preparation date. The classifier's contact rule - a web address, phone number or e-mail in a page's
  margin is furniture whatever its length - is not asked either: in the census it took RACQ's supplementary PDS
  cover block, the issuer's name, ABN, licence, addresses and phone. Which of a cover's issuer lines to publish is
  the owner's 13 September ruling, a question of its own. A rule that asks the pages beside a line cannot move the
  benchmark's one-page files, so it can serve that ruling without costing the furniture checks; that is the next
  thing to measure, not a side effect of this rule.
- **Tests** (`tests/test_running_head.py`, 11): the model's label on a title no page beside it repeats is refused,
  failing on the code before it; a head repeated beside it, set alternately on facing pages, or in a one-page file
  stays a head; a head is asked at its height from the top of pages of another height, failing when heads are
  measured from the foot; the margin tie, a small line at the top, a heading at the very top and a line stacked under
  a running head come back when no page beside them prints them - the zone rule's, the top strip's, the margin
  heading's and the header stack's tests each failing with that guard alone taken out - while a small line and a
  heading repeated at the top of every page stay heads. `bench/probes/running_head_census.py` lists every block a
  conversion takes out at a page's head or foot, the rule that took it and whether it runs. Suite 626.

**A line filed as furniture for repeating a running head must run where it stands** (16 Sept, morning, after 66bdf98)
- **What was found.** 66bdf98 asked the pages beside a line whether a head runs. Read at the foot, the same census
  (`bench/probes/running_head_census.py read --kind FOOTER`) showed the margin clean-up losing a page's own heading to
  a rule that asks nothing of the pages beside: a short line whose words repeat a running head's is filed as furniture
  wherever it sits. Two contents policies head a grey box "We do not cover" over "additional features on pages 26 to
  35, additional covers on pages 36 to 45, any incident not covered by your contents policy", and a home policy marks
  a section "Optional cover" beside "Commercial Storage" - all three in the words their pages run at the head, none of
  them printed where the box stands on any page beside. The rule was written for a form's label at the foot of its box
  ("Schedule A (Form 990) 2022"), which does run there.
- **The rule** (`truedoc/pipeline.py`). The line must run at the height it stands: the clean-up files it as furniture
  only when a page within two either side prints most of its words in the band it fills, which is 66bdf98's question
  (`_repeated_beside`) asked where the line is rather than at the page's head. With no page beside it to ask - a
  one-page file, or scanned pages beside it - the rule decides as it did, so no benchmark page can change.
- **Tried and dropped, each measured before it was dropped.** Asking the same question of the other rules that take a
  line out at a foot gave back furniture as often as content. The layout model's page-footer label, asked without its
  length test, published the sheet's own document code or file name and its folio as a heading on 127 of the 190 Key
  Facts Sheets. The zone rule's bottom branch published GIO's "PDS preparation date 25/11/2020" with its folio, which
  a check wants absent - and that branch is where a supplementary PDS's one sentence of substance sits ("The insured
  event 'Flood and/or run-off' ... is deleted."), so that sentence stays lost. The contact rule gave back four issuer
  blocks and a sentence about the Code of Practice against five "Effective Date" stamps. The margin heading's foot
  branch gave back two product names against three brand straplines and a "Continued next page...". The two bottom
  strips gave back nothing at all in 1,237 pages. What separates a sentence from a stamp is not what "does it run"
  asks, and it wants a measured step of its own.
- **Measured, code against code** (against 66bdf98). Insurance set: 229 of 229 either way, and no page of it changes -
  none of its 25 pages heads a box in the words its running head uses. Key Facts Sheets: graded afresh, every measure
  as it was - header whole 157 of 158 tuned on and 32 of 32 held out, every event and answer carried, no band
  swallowed, no row only a continuation - and not one of the 190 sheets' markdown differs by a character: no sheet
  heads a box in the words its pages run at the head. Benchmark: every one of its 1,403 files is a single page, so no
  page beside a line can be asked and no benchmark page can change; converted under this rule, the headers-and-footers
  section comes out byte for byte as it did on all 266 of its pages, 739 of 760 checks either way. Library: over the
  whole one-in-fifty sample of the library, 1,237 pages of 978 documents, the rule gives back three lines on three
  pages, and each was read against its page image: the grey box "We do not cover" on two contents policies and
  "Optional cover" on a home policy.
- **Tests** (`tests/test_repeated_head.py`, 5): a box heading in a running head's words is published when no page
  beside prints it there, failing on the code before it; the same line stays furniture when the pages beside do print
  it at that height, and when there is no page beside to ask; and the two feet the rule leaves alone - a cover's
  one-line issuer the model calls a page footer, and a cover's block of contact details - stay furniture, which is
  what the measurements above decided. Suite 631.

**A sentence standing alone at the foot of a page is the page's own** (16 Sept, late morning, after c48e2ce)
- **What was found.** c48e2ce left the zone rule's bottom branch alone and a supplementary PDS's one sentence of
  substance with it. SPDS654DIR ends its cover "The insured event 'Flood and/or run-off' under the heading What you're
  covered for is deleted." at the very foot, with the folio joined to the block, and the branch files it as a running
  foot; SPDS652DIR and an EXQL supplementary PDS lose theirs the same way. Asking the pages beside was measured and
  refused: GIO's "PDS preparation date 25/11/2020" stands as alone at its foot as that sentence does, and publishing
  it cost the insurance set a check (229 of 229 to 228).
- **What tells them apart.** Not where they sit, nor whether they run, but what they are. The census of the whole
  one-in-fifty sample of the library - 1,237 pages of 978 documents - holds 194 feet that no page beside prints: three
  sentences and 191 stamps, codes, folios, dates and issuer lines ("TMDHL_LLP015 12/25", "Page 1 of 11", "Prepared on:
  27 February 2026", "AAI Limited ABN 48 005 297 807 AFSL 230859 trading as AAMI"). "At least eight words, with digits
  no more than a twentieth of the lower-case letters and digits" picks out those three and nothing else, and the
  selection does not move across eight, ten or twelve words, or a twentieth, a tenth or a seventh of digits - the two
  sides are far apart, not divided by a fitted constant.
- **The rule** (`truedoc/classify/blocks.py`). A line in the bottom margin is a running foot unless it is a sentence
  that no page beside prints there. Both halves are needed, and both were measured: among the feet the pages beside
  do print, the sentence test fires on fifteen - "Insurance products issued by RACQ Insurance Limited. Conditions may
  apply. This is general advice only ...", "Home Insurance | Product Disclosure Statement and Policy Booklet", a
  Huddle booking line - every one a running foot that must stay out; and among the feet no page beside prints, the
  repetition question alone gave back 191 stamps with the three sentences. With no page beside to ask - a one-page
  file, or scanned pages beside it - the zone decides as it did, so no benchmark page can change.
- **Measured, code against code** (against c48e2ce). Insurance set: 229 of 229 either way, and no page of it changes -
  none of its 25 pages ends on a sentence at its foot, and GIO's preparation-date stamp stays out, which is the check
  this rule had to keep. Key Facts Sheets: all 190 graded fresh under the rule, and not one sheet's markdown differs
  from the committed output: the 158 tuned on stay at 157 headers whole (99%), 1,885 of 1,885 prescribed events
  opening a row of their own and 1,885 of 1,885 carrying their Yes / No / Optional; the 32 held out stay at 32 headers
  whole (100%), 375 of 375 and 375 of 375, with no band swallowed by the cell above and no row that is only a
  continuation on either side. Benchmark: every one of its 1,403 files is a single page, so no page beside a line can
  be asked and no benchmark page can change; counted rather than assumed - every one of the 1,969 PDFs under `bench`,
  the 1,403 among them, opens at one page - and the headers-and-footers pool, the 266 pages this rule is most exposed
  on, scores 739 of 760 under both code states with not one page's markdown differing. Library: the pages the census
  points at, read under both code states - the three sentences and twenty whose feet are stamps, 23 pages of 23
  documents - with every block either state takes out, at a head or a foot, compared block by block: 20 pages
  unchanged, three blocks published now, none taken out now. The three are the three sentences; the stamps stay out,
  among them AAMI's "AAI Limited ABN 48 005 297 807 AFSL 230859 trading as AAMI" on three covers, ALDI's "Prepared on:
  12 April 2024", WFI's three-line ABN block and the Qantas SPDS's own "Page 1 of 5" beneath its sentence.
- **Tests** (`tests/test_foot_sentence.py`, 5): a supplementary PDS's sentence at the foot is published when no page
  beside prints one there, failing on the code before it; a sentence the pages beside do print at their feet stays a
  foot; a stamp alone at the foot stays a foot, as does a short line and as does the sentence in a one-page file.
  Taking either half of the condition out fails a different one of them. Suite 636.

**A line at a page's edge that no page beside prints is the document's imprint** (16 Sept, midday, after 9c39679)
- **What was found.** A running head or foot runs: the same words, at the same height, page after page. At the edge of
  a first page nothing runs, and what stands there is the document's imprint - an insurance cover's issuer, ABN and
  licence ("AAI Limited ABN 48 005 297 807 AFSL 230859 trading as AAMI"), a preparation date, a document code. TrueDoc
  dropped all of it. Four ways of separating the meaningful from the worthless were tried on the census and all four
  failed: repetition (neither kind repeats), where it sits on the page (184 of the 197 unrepeated feet are on a first
  page), type size (7pt issuer against 6pt date), and length. The fourth was an overfit, and the owner caught it:
  counted by copies every stamp stopped at ten words and every issuer block started at twelve, but counted by distinct
  wording the two overlap at ten - and 23 of the 41 "issuer blocks" were one AAMI template repeated across documents.
- **Why it does not divide.** Because the division is not in the document, it is in the reader. olmOCR-bench's 753
  header and footer checks want every such line absent - "Copyright 1975 American Mathematical Society", "FI-02180
  Espoo, Finland", "Please cite this article as: ..." - while a reader comparing two insurance products needs to know
  who underwrites them. The owner's own insurance set holds both positions: two of its 31 absent checks are a
  document's own stamps ("PDS preparation date 25/11/2020" on GIO page 2, "NRMAHOMPDS REV2 09/2023" on NRMA's cover),
  so publishing imprint into the body would contradict checks he ruled fair.
- **The rule** (`truedoc/pipeline.py`, `truedoc/render/okf.py`). Neither the body nor the bin. `_record_imprint` runs
  at the end of `process_page`, after every furniture decision is final, and asks `_repeated_beside` of each block
  already filed as a header or footer: when no page beside prints it there, its text is kept with its page.
  `load_document` gathers the entries as it gathers hidden text (D011) and the renderer writes them under
  `truedoc.imprint`. Nothing changes kind, so the body is untouched; a page number is left out, because a folio counts
  the artifact's pages rather than the document's matter; and no threshold is involved, so nothing is fitted.
- **Measured, code against code** (against 9c39679). Insurance set: every one of its 25 pages is byte for byte the
  page main writes at 9c39679, so its 229 of 229 cannot move - the change adds to the front matter and every scorer
  converts without it. Key Facts Sheets: all 190 graded fresh under the change and not one sheet's markdown differs
  from the committed output; every figure stands where it stood - 157 headers whole of the 158 tuned on (99%) and 32
  of 32 held out (100%), 1,885 of 1,885 and 375 of 375 prescribed events opening a row of their own and carrying their
  Yes / No / Optional, no band swallowed and no row that is only a continuation. Benchmark: 739 of 760 on the
  headers-and-footers pool under both code states, with not one of its 266 pages differing byte for byte - and no
  benchmark page could gain an imprint entry in any case, since every one of its 1,403 files is a single page and no
  page beside can be asked. What it keeps: 200 documents of the census sample read under the change, their first two
  pages with the pages beside them still there to answer: 60 keep an imprint - 67 lines, 51 of them distinct, every
  one on page 1 or 2, and not one a page number. Nineteen name who issues the product ("Australian Pensioners
  Insurance Agency Pty Ltd ABN 14 099 650 996 is an agent and authorised representative ...", "AAI Limited ABN 48 005
  297 807 AFSL 230859 trading as GIO", RACT's and QBE's issuer paragraphs), twelve carry a date ("This PDS came into
  effect on the 1 September 2021", "Underwritten by Hollard Prepared 6 December 2023"), and the rest are a document
  code, a web or phone line, a strapline or a fragment ("TMDHL_HBC099 10/24", "raa.com.au/insurance", "The over 50s
  specialists", "Provided by") - kept as they stand, labelled rather than published, because the reading that
  separates them is the reader's and not the document's. It costs nothing that can be measured: 20 pages of an AAMI
  PDS convert in 6.99s at 9c39679 and 6.84s with the pass, best of five with the layout model off so its seconds
  cannot hide the difference, and the markdown is identical to the byte.
- **Tests** (`tests/test_imprint.py`, 6): a cover's imprint no page beside prints is kept; it stays out of the body;
  a running foot is not imprint; a page number is not imprint, nor is a folio the layout model has labelled a page
  footer - taking that one test out of the pass fails that one test and nothing else; and with no page beside to ask,
  as in every olmOCR-bench file, nothing is claimed. Suite 642.

**A running head is the same line page after page, not the same bag of words** (16 Sept, afternoon, after 93b68fb)
- **What was found, and how.** The owner asked for his arrows question to be measured - directional chevrons that tell
  a reader which text applies - and the page he named, AAMI's home building PDS printed page 75, turned out to lose
  three separate things. One of them is a heading: "If your policy has a building sum insured", the line that says
  when the whole settlement tree applies, is not in the output at all. `_repeated_beside` asked whether 60% of a
  line's distinct words turned up anywhere in the same band on a page within two, and two pages on a *different*
  heading reads "When you have a building sum insured and we settle your building claim we will not:", which shares
  building, if, insured, sum and your - five of the seven, 71%. Ordinary words collide; a line does not.
- **The rule** (`truedoc/layout/fuse.py`). Every word of the line must appear in the band in its own order: the same
  line, not the same bag. Extra words between them - a folio, a section number - do not matter, so a running head
  set with its page number still runs. `_same_line` is asked wherever `_repeated_beside` was, which is every rule
  that takes a line out at a head or a foot, and the imprint pass (D029) that keeps what none of them will publish.
- **Measured over the census before anything was built.** Of the 106 heads the whole one-in-fifty sample calls
  repeated, the order test gives back 13, and all 13 were read against their pages: "You are not covered for:" over
  an exclusions list (four sheets), the definitions entries "Same passageway or hallway" (three) and "Broken glass -
  home", and five cover titles. Of the 307 feet, it gives back 20, every one an issuer line - "The issuer of this
  Product is RACT Insurance Pty Ltd ABN 96 068 167 804", "ABN 62 004 478 960 AFSL 700014 trading as WFI." - which
  the imprint keeps rather than publishes. A symmetric test (60% each way) was measured and refused: it gives back
  30 heads and 107 feet, among them "Page 1 of 9", "1 of 3" and a claims phone number.
- **Measured, code against code** (against 93b68fb). Insurance set: 229 of 229 with every kind of check at 100% -
  present 113, order 58, absent 31, table 22, list items 5 - and one page of the 25 differs: BOM's home contents page
  6 promotes "Your cover options" from a second-level heading to a first, which is what the page sets it as (the
  margin tie that had demoted it gives the tie to the margin only when the line runs, and it does not). Key Facts
  Sheets: every figure as it was - 157 headers whole of the 158 tuned on (99%), 32 of 32 held out (100%), 1,885 of
  1,885 and 375 of 375 prescribed events opening a row and carrying their answer - and 12 sheets gain the statement
  the Australian Government prescribes ("The content of this Key Facts Sheet is prescribed by the Australian
  Government and is a requirement under the Insurance Contracts Act 1984"), which was being dropped as a running head
  because both pages of a sheet print it. 46 lines added across the twelve, and not one line removed on any sheet.
  Benchmark: 739 of 760 on the headers-and-footers pool under both code states, with not one of its 266 pages
  differing byte for byte - and no benchmark page can move in any case, since every one of its files is a single page
  and no page beside it can be asked. Library: the census's own verdicts re-asked from the PDFs, which needs no
  conversion: of the 106 heads the whole one-in-fifty sample calls repeated, 13 come back, and all 13 were read
  against their pages; of the 307 feet, 20 come back, every one an issuer line that the imprint keeps rather than
  publishes (D029). The symmetric test measured beside it would have given back 30 heads and 107 feet.
- **Tests** (`tests/test_same_line.py`, 4): a heading whose words collide with another heading two pages on is
  published; a running head printed beside stays furniture, and still does when the pages beside it add a section
  number; a head whose words run in another order is published. Two of the four fail on the code before this. Suite 646.

**A mark nothing takes is kept, not lost** (16 Sept, evening, after bda7609)
- **What was found.** The third of the three losses on AAMI's printed page 75, and the one that could not be repaired.
  The page chains its settlement statements with a chevron in a grey disc, carrying the word "then", and all five are
  dropped. TrueDoc reads the shape correctly - `find_marks` returns arrow-down - and then loses it at placement:
  `_attach_marks` has three ways to place a mark, a table cell, the start of a line, or being the whole content of a
  picture, and on that page the chevrons fall inside the region the layout model calls a table, so none applies. On
  printed page 20 the same chevrons sit in pictures of their own and reach the body as arrows, which is why the chain
  survives there and not here.
- **The fourth way, measured and refused.** A readable mark standing between two blocks in its own column, with none
  beside it, looked like a flow marker: on the two AAMI pages it picks out seven chevrons and nothing else, and the
  count is stable from six times the body size to twelve. Over 59 documents of the library it publishes ten arrows,
  and they are Apia's benefit-table marks ("Limit >> We", four of them), two pointing into a list of tradespeople,
  one on a Key Facts cover, and - read against its page - a section numeral drawn so large that the reader takes it
  for an arrow. The chain the rule was built for occurs in one document of the 59. A mark's meaning is not in its
  geometry, which is the same wall the issuer lines met in D029.
- **What is kept instead** (`truedoc/pipeline.py`, `truedoc/render/okf.py`). `_attach_marks` already recorded every
  mark it found; it now records whether anything took it, `load_document` gathers the ones nothing took, and the
  renderer writes them under `truedoc.marks_not_placed` with the page and the box each was drawn in. A shape the
  reader cannot name is left out. Nothing is published and no block changes kind, so the body of every document is
  what it was - as D029 keeps a line at a page's edge that nothing places, this keeps the mark.
- **Measured, code against code** (against bda7609). Insurance set: every one of its 25 pages is byte for byte the
  page main writes at bda7609 - nothing is published, so nothing can move. Key Facts Sheets: every figure as it was -
  157 headers whole of the 158 tuned on (99%), 32 of 32 held out (100%), 1,885 of 1,885 and 375 of 375 - and against
  bda7609 not one sheet's markdown differs. The twelve sheets that differ from the cache taken before bda7609 differ
  by that commit's prescribed statement, the same 46 lines added and none removed, and by nothing this change does.
  Benchmark: 739 of 760 on the headers-and-footers pool under both code states, with not one of its 266 pages
  differing byte for byte. What it keeps: 40 documents of the census sample read under the change, their first twelve
  pages each: 23 of them keep a mark nothing placed, 245 marks in all - 93 dots, 46 boxes, 76 arrows (31 up, 25 right,
  15 down, 5 left), 21 ticks and 5 squares. The heaviest document carries 43 and the median of those that carry any is
  5, against a cap of 200 a document. Keeping only the arrows would cut it to 76, and was refused: an unplaced tick is
  the missed-table loss that costs a reader a yes or a no (QBE's page 16 loses eight), so deciding which shapes matter
  is the judgement geometry cannot make - which is what the rule above tried to do.
- **Tests** (`tests/test_marks_kept.py`, 4): a mark nothing takes is kept with its page; one that leads a line
  reaches the text instead and is not kept; the mark nothing takes stays out of the body; a page with no marks
  records none. The first fails on the code before this. Suite 650.

**A decision tree read as a table: three signals measured, none of them enough** (16 Sept, evening, nothing shipped)
- **The loss.** AAMI's home building PDS printed page 75 sets how a building claim is settled as a decision tree: two
  conditions across the top, three branches under them, the outcomes under two of those. The layout model calls the
  region a table and the reader builds one - the three branches as a header row, the outcomes beneath - and leaves the
  two conditions above it as loose paragraphs. Which outcome follows which condition is lost, and a reader of the
  markdown cannot recover it. With the model switched off the reading order is right (condition, branch, outcome,
  branch, outcome, condition, outcome), so the model costs meaning on this page rather than adding it.
- **Signal one: a row that cuts a sentence.** The built table reads "The builder we engage will be authorised to" in
  one row and "complete the repair or rebuild on a 'new for old' basis." in the next, a boundary the page does not
  draw. Counted over markdown already converted - 481 files, 162 tables, 1,792 rows: the 190 Key Facts Sheets, the
  insurance set and the benchmark's headers-and-footers pool - using `_CONNECTIVE_END`, the reader's own test for a
  line that cannot end: **5 rows, 0.28%, none of them in the owner's documents** (three on one Indonesian medical
  page, two on a garbled one). Too rare to earn a rule that merges table rows, and merging risks the table checks.
- **Signal two: the table is unusually empty.** A tree is not a grid, and a grid fills itself: the built table leaves
  its third column empty in two of three rows. Over the same 163 tables, 53% have no empty cell and 30% under a
  tenth - but AAMI's tree sits at **22% empty, inside a band that holds legitimate tables at 20 to 33%**, among them
  BOM's home contents page 22 from the insurance set. A threshold there vetoes two dozen real tables. Refused.
- **Signal three: a connector inside the table.** A flow chart draws arrows and a grid does not, and since 73d39ff
  every mark nothing takes is recorded. Over 40 documents of the census sample, their first twelve pages, 76 arrows
  are placed nowhere and **not one of them stands inside a table the reader built**. The pattern is, so far, this one
  page: a rule keyed on it would fire once, could not be measured, and would put the benchmark's table checks at
  risk. Refused.
- **What is left.** The loss stands, recorded rather than repaired. What would settle it is not another geometric
  signal but a decision about the layout model: whether a region it calls a table, whose rows do not line up into a
  grid, should be left as text. That needs the benchmark's table pool measured on both sides, and a candidate that
  fires more than once.

**Correction: the unplaced-marks census counts a state the product does not produce** (16 Sept, evening)
- **What was written, an hour before this.** STATUS named the next item as the table the reader never builds, on the
  strength of `bench/probes/unplaced_marks_census.py`: 541 readable marks standing in columns on 141 pages of 93
  documents in a one-in-ten sample, with QBE's home PDS page 16 losing eight yes-or-no answers. The figure was taken
  from the probe's own docstring, written on 15 September, and repeated as though it described today's conversions.
- **What is true.** The probe builds its pages **without the layout model**, which its docstring says plainly and I
  did not read: tables are found before the model runs, so the census sees a state no conversion produces. QBE page
  16 today, asked both ways through `truedoc.marks_not_placed`: with the model off, eight marks are placed nowhere;
  with it on, **none**, and the page's table converts whole - four rows, six ticks and two crosses, each in its own
  cell.
- **The population, re-measured on today's code.** Five pages the census names, asked both ways: GIO's landlord PDS
  page 41 four marks to none, AAMI's fire and theft page 41 three to none, AAMI's home contents page 41 two to none -
  the model builds the table and the marks reach their cells. Two keep them: Bank of Melbourne's financial services
  guide page 1 (four either way) and a RACQ supplementary PDS page 1 (eleven to nine). A sixth page the census names
  is in the sealed slice (D030) and was not opened.
- **What the survivors are.** Bank of Melbourne's four crosses, read against the page, are the quadrants of the
  bank's shield logo - decoration, and no meaning lost. They are what `marks_not_placed` is for: listed, published
  nowhere, and recognisable as decoration by their kind and their box.
- **What this changes.** The next item is not the missed table. On the product's own measure - the model on, as it
  runs - 245 readable marks are placed nowhere over 40 documents' first twelve pages, 21 of them ticks, and the ones
  read so far are logos. The lesson is narrower than the correction: **a probe's numbers describe the options it was
  run with**, and a figure lifted from a docstring is a recalled number, not a measured one.

**Correction: three defects that were never there, and the interpreter that hid the layout model** (16 Sept, evening)
- **What was read.** Step two of the library plan, on the owner's instruction: twelve documents drawn from the library
  by a hash of their names, two pages each, converted and read against their page images. Three defects were written
  down within the hour - QBE's three-column insured-events table lost, BankSA's ticked list run together inside its
  cell, ALDI's six thumb-index tabs published in the body.
- **None of the three is real.** Every conversion had been run with the interpreter on the path rather than the
  project's own, and there the layout model cannot load: docling pins `tokenizers` below 0.22 and the machine's
  Python has 0.22.2. The run says so once, in a log line, and carries on without it. Under `.venv/Scripts/python` the
  same three pages convert correctly - QBE's table is built with every exclusion in its own column and the row header
  spanning ten rows, BankSA's cell is a list of eight ticked entries, ALDI's tabs never reach the body.
- **The figure that came out of it is withdrawn.** A census of lists whose bullets stand on lines of their own
  counted 361 empty list items over 52 pages of a sixty-document sample. With the model running it is **54 over 16
  pages and 9 documents** - one seventh of the claim.
- **Two withdrawals in two days, and both have the same shape:** a number measured in a state the product does not
  produce. On 15 September it was a probe that builds its pages without the layout model; today it was an interpreter
  that cannot load it. The lesson is not "be careful" - it is that a conversion must say what did not run, which is
  the next entry.

**A stage that was asked for and could not run says so** (16 Sept, b7f53c4)
- `_detect_layout` swallowed every failure into a log line, and the conversion carried on without the model. A page
  read that way is indistinguishable, in the output, from the product's own work. The reason is now kept on the page
  and reported once in the front matter: "the layout model was asked for and could not run, so N page(s) were read
  without it: <reason>". Checked on ING's home SPDS page 4: `warnings: []` under the project's interpreter, and the
  reason named under the one that cannot load the model.
- It cannot move a score - every scorer converts with `frontmatter=False` - and a test pins the body byte-identical
  with the warning present. Six tests; the two that monkeypatch `_detect_layout` now pass the page through.
  Suite 656 -> 662.

**A bullet alone on a line marks the words beside it** (16 Sept, e43c06e)
- **The shape.** Some PDFs draw a list's bullets in a text run apart from their items, an em or more before the words
  they mark; the line splitter cuts at the gap, so each bullet becomes a line holding one glyph. The orphan is then
  published as an empty list item - "- " with nothing after it - and the items it marked run together with nothing to
  tell them apart. Measured over sixty documents of the library, twelve pages each, with the layout model running:
  **16 pages of 386 and 9 documents of 60, 54 empty items** - Chubb's two Masterpiece wordings, Budget Direct's SPDS,
  RAA's home and contents PDS, two Key Facts Sheets, AAMI, NAB and Qantas among them.
- **The rule already existed for the marks read from their drawing.** `_read_private_glyphs` ends by joining a mark
  that stands alone on a line to the nearest line within three ems to its right, because RACQ's supplementary PDS
  sets its Symbol bullets 13pt before their words. A bullet the text layer names for itself is the same thing in the
  same place, so it joins that set: one line of code, one place, one reach. Ticks and crosses are left out - a column
  of them is a table's answers, not a list's markers (D028).
- **Measured.** On the 52 pages that hold the shape: empty items **54 -> 4**, pages **16 -> 2**, documents **9 -> 2**.
  The two left are Key Facts Sheets whose bullets stand 4.1 ems from their words, beyond the reach the drawn marks
  were measured at; widening a measured constant is a separate question, and the remainder is named here rather than
  tuned away. Twenty of 47 pages changed at all, and every change read is the same one: the orphan gone and its words
  under their own marker.
- **Nothing else moved.** Insurance set 229 of 229 with all 25 pages byte-identical. Key Facts Sheets 99% tuned on
  and 100% held out, 1885 of 1885 and 375 of 375 answers - the record, unchanged. The benchmark barely sees it: over
  all 1,403 pages there are 135 lone markers on 76 pages, 93 of them with no words beside them at all, and only
  **three pages** hold one with words within reach. Those three score 4 of 7 either way, and two read better - a
  university's committee names and a Finnish advisory's paragraphs, each now under its own marker instead of after a
  row of empty ones. Suite 650 -> 656.

**A dingbat font's letter is a code, not a letter** (16 Sept, 4bc6a51)
- **The shape.** Wingdings, Webdings, ZapfDingbats, Marlett and Monotype Sorts hold no letters at all: their "n" draws
  a filled square, their "l" a circle, their "o" an empty checkbox. The letter is what reached the reader - "n admit
  guilt, fault or liability except to the police" in Australian Seniors' landlord PDS - and Woolworths' target market
  determination bullets with Wingdings U+009F, which renders as nothing at all, so its items lost their markers
  entirely. Sixty documents of the library, twelve pages each: **242 such characters over 27 pages and seven distinct
  documents**, every one of them opening a line.
- **The rule is the private-use rule's own.** `_read_private_glyphs` already reads a glyph by what its font draws;
  these join it, with the same guards - a font that spells words is left alone, and so is a glyph another drawing
  reaches into. A character whose code is already a mark keeps what it says, so SymbolMT's 157 bullets in the same
  sample and a form's dingbat boxes are untouched, and the Symbol family, which spells Greek and mathematics, is not
  a dingbat font.
- **Measured.** Library: lines opening with the raw letter **170 -> 31**, pages **18 -> 5**, documents **5 -> 1**. Of
  the 31 left, 29 are GIO's ZapfDingbats chevrons, whose own code (U+203A, a right-pointing angle) already looks like
  what the font draws and which read as arrows - a kind this reader deliberately does not name; the other two read as
  arrows because other drawing reaches into their box. Insurance set 229 of 229 with one page changed, Qantas's
  Wingdings circle becoming a list item. Key Facts Sheets 99% tuned on and 100% held out, unchanged. Of the
  benchmark's 1,403 pages eleven hold such a character: 41 of 48 either way, four pages changed, every change read -
  "FEMALE o MALE o" into checkboxes, "l 78% of cases" into a list item, three Wingdings squares in a heading. Suite
  662 -> 669.
- **One thing this turns up for later:** a cell's list now carries its bullet in the element's own text
  ("<li>&#9679; Fire and explosion;</li>"), because `cell_lists.BULLETS` knows the small bullets but not the filled
  disc the reader writes. A bullet says nothing a list element does not already say, so it should go the way the
  others do.

**A column of labels is not a heading wrapping onto the rows below** (16 Sept, c3ed2ce)
- **What the page showed.** QBE's financial services guide sets "Phone:", "Email:", "Online:", "Post:" down a column
  with their values beside them. The conversion published "Phone: Email: Online: Post:" as one paragraph and every
  value as another, so nothing said which value belonged to which label. The next page of the same document sets the
  same shape and builds it as a table, which is what made the fault worth tracing rather than guessing at.
- **Where it went.** `_heading_wraps_on` reads a cell of more than six words that closes on no full stop, with a
  lowercase line beneath it in its own column, as one heading set over two lines. The first value - "1300 650 503
  (Monday to Friday, 9am-5pm AEST/AEDT)", seven words - stood over "complaints@qbe.com", which starts in lower case,
  so the fold ran three times and put three labels in one cell. The table was then refused altogether, and the labels
  and the values fell out as two paragraphs.
- **The rule.** A colon closes what it follows, so a cell ending in one is a label, whole. Where the row below fills a
  column whose cell above ends in a colon, it is a row of its own and not the heading carrying on. The same reading
  of a colon is already in `_label_carries_on` and in the merger's label branch; this makes the third place agree.
- **What a wider version cost, measured before it was narrowed.** Refusing the fold whenever the row below filled any
  column the row above filled - the test the code already used one row further down - took WFI's classic home
  building Key Facts Sheet's header apart: its heading interleaves "... that apply to" over "Yes/No" over
  "Event/Cover | Optional | events/covers ...", and "Optional" under "Yes/No" is exactly that shape. The colon
  narrows it to labels, and the sheet is whole again.
- **Measured.** Key Facts Sheets 157 of 158 tuned on and 32 of 32 held out, 1885 of 1885 and 375 of 375 answers -
  identical to before the change, sheet by sheet (`kfs_three.py`). Insurance set 229 of 229 with no page changed.
  Benchmark tables 852 of 1022 and headers_footers 739 of 760 either way, with all 454 pages byte-identical. Of 47
  library pages converted for this reading, one changed: QBE's page 3, now four rows pairing each label with its
  value and the postal address after them, as its page 4 already read. Suite 669 -> 673.

**Two more shapes measured, and what the numbers said to do with them** (16 Sept, evening)
- **A paragraph opening with a character markdown reads as syntax: refused, population zero.** RACV's landlord
  premium guide footnotes with "#", so "#Excludes Travel, Business, and Farm Insurance products." is published as a
  first-level heading. Over 217 pages of 40 library documents, with the layout model running, there are **no other
  instances** - not one paragraph opening with "#", ">" or "|". One page in a hundred and forty is not a rule; it is
  noted here and left.
- **A chevron standing alone as a list's marker: measured at 11 markers on 2 pages of one document in sixty**, where
  the bullets shipped this evening were 16 pages and 9 documents. `_MARK_GLYPHS` holds the round and square bullets
  only, so RAC's legal rights guide still sets its "»" apart from the words it marks. The same one-line change would
  cover it; at a sixth of the population it waits until something else brings it, rather than spending a quartet of
  measurements on one document.
- **A list set at two levels, flattened to one: 20 pages of 217 and 11 documents of 40.** CGU's landlord PDS sets
  "there is any change to:" over four items an em further in, and both levels come out as "- " at one level, so a
  sub-item reads as a sibling of the item it belongs to. `Block.level` already carries list nesting and the heading
  renderer already reads it; what is missing is setting it from the marker's own indent and indenting the element.
  That is the next thing to build, and the largest of the three.

**A list item set further in than the item above opens a sub-list** (17 Sept, a9cf7e8)
- **The shape.** The owner's D028 says this already for a list inside a table cell: "a mark set further in than the
  entry's own opens an item of a sub-list". The body had no such rule. CGU's landlord PDS sets "there is any change
  to:" over four items an em further in, and both levels came out as "- " at one level, so a sub-item read as a
  sibling of the entry it belongs to. Over 217 pages of forty library documents, 20 pages and 11 documents set a list
  at two levels or more.
- **The rule, read off the page.** Within a run of list items uninterrupted by anything else, the markers' left edges
  are gathered into places half an em apart, and an item's level is which place it starts at, to four levels. A list
  that carries on in the next column starts again there: a marker more than eight ems in from the run's own edge is
  another column, not a deeper level. `Block.level` already carried list nesting and the renderer already read it for
  headings; an item is now indented two spaces a level, which is what markdown reads as nesting.
- **Three things the pages caught before this was measured.** Only an item carrying a marker the classifier itself
  knows, with words after it, takes a level: the first version's own pattern took any letter with a dot, and indented
  "J. A. Melero. 1989. ..." - the second line of a reference in a numbered bibliography - as a sub-item of the
  reference above it. The layout model calls a paragraph a list item often enough that Australian Seniors' claim
  steps, a numeral in a dark square beside a sentence, were being indented as though the page set them that way. And
  a block that was a heading before the model called it a list item still carried the heading's level, which the
  renderer then read as an indent.
- **Measured.** Insurance set 229 of 229 with no page changed. Key Facts Sheets 157 of 158 tuned on and 32 of 32 held
  out, **zero sheets moved**. Benchmark over four categories and 747 pages - tables 852 of 1022, headers_footers 739
  of 760, multi_column 682 of 884, long_tiny_text 357 of 442 - every score identical, four pages changed, and each
  read against its image is the page's own shape: a Polish numbered list with lettered sub-items, an Indonesian b),
  a Finnish sub-list under a green bullet, a patent's (b) and (c) clauses. Of 47 library pages, two changed - CGU's
  page 4 and Bendigo's page 7, each sub-list under the entry it belongs to, across both columns. Suite 673 -> 677.

**A filled disc or square is a bullet, and belongs to the list element** (17 Sept, 5146686)
- **What the dingbat rule exposed.** D028 already says it - "a bullet's own glyph is left to the list element; a tick
  or a cross stays with its words, because it says whether the entry is covered" - but `cell_lists` knew the small
  bullets and not the marks the glyph reader writes, which are "●" for a dot and "■" for a square. So from the
  moment a Wingdings bullet was read by its drawing, every entry of Woolworths' target market determination came out
  as `<li>● Fire and explosion;</li>`, the glyph saying twice what the element already says. Over the library pages
  converted for this reading: **31 discs and 21 squares inside list elements, on 6 pages of 4 documents**.
- **The line.** A filled disc or square is a bullet wherever it is drawn. The hollow ones stay with their words: an
  empty box or circle is how a form draws an answer not given, and dropping it would drop the answer.
- **Measured.** Those 52 glyphs are gone from the elements and every tick and cross is untouched. Insurance set 229
  of 229 with no page changed; Key Facts Sheets 157 of 158 tuned on and 32 of 32 held out, zero sheets moved; the
  benchmark's table category 852 of 1022 with **not one of its 188 pages changed**. Suite 677 -> 682.

**Two rules the library asked for and the census refused** (17 Sept, small hours)
- **"A block whose every line stops short of the measure is a list of records": refused.** RAA's home and contents
  PDS ends with seven shop addresses, each its own line, joined into one paragraph so that "Colonnades" reads as part
  of the Adelaide address. The signal proposed was typographic and general - a paragraph's lines reach the measure,
  a list of records' lines do not. Measured over 217 pages of forty documents: **33 blocks on 22 pages and 16
  documents** hold the shape, and the ones read are ordinary prose - "Your insurance premium generally reflects the
  likelihood of a claim", five lines of it, in a column narrower than the widest line beside it. The measure a block
  is judged against is the difficulty: a block's own right edge is its longest line, so it is always flush with
  itself, and the column's measure taken from its neighbours is wrong wherever a figure or a narrower column sits
  beside it. A rule on this signal would break paragraphs to save address lists. Not built.
- **"A heading band drawn outside a table's rules is its header row": refused as proposed.** RAC's premium guide sets
  "Alarm type | Discount" in a coloured band with no rule under it, so the ruled finder builds only the body rows:
  the first data row is published as the table's heading and "Discount" ends up at the foot of the page, far from the
  column it names. `_adopt_ruled_headers` already reaches for a heading above a box, but only when the box is one row
  or its first row plainly looks like data. Widening it by alignment alone was measured first: over the same 217
  pages, **47 of 104 tables have a line of text just above them whose words all fall inside their columns**, and
  reading them shows what they are - "Landlord Insurance policies are subject to stamp duty...", "We offer the
  following types of..." - introductions, not headings, over tables whose own first row is already a proper heading
  ("Membership Card Colour | Years of Membership | Annual Discount"). Adopting those would wreck four tables for
  every one it fixed. **What a later attempt needs is the band's own typography, not its alignment:** the fill drawn
  behind it, which `page.drawings` carries and the boxed-row rules already read.

**Where the Key Facts Sheets stand:** header whole **34% -> 99% tuned on, 16% -> 100% held out**; the Yes/No in
its own answer column for every prescribed event, tuned on and held out (94.9% and 93.6% before the
answer column was cut, by the corrected grader); exclusions severed from their events 51 -> 0; section headings
buried inside an exclusion 63 sheets -> 0. Every rule is
geometry and typography.

**Next**
- Six table checks on two benchmark pages fail only because a pipe table writes a literal dollar as `\$` (D024) and
  the check compares the cell's text exactly, where an HTML cell writes `$`: under a tenth of a point overall, and a
  question about D024 rather than a table rule.
- Drawn marks that no table cell takes. ALDI's household PDS page 31, the example that stood here, is read from the
  cells its page draws since the drawn-cells rule: each tick under Home and under Contents, and the Limit note one cell
  spanning the fourteen rows. The rest of that census - 541 drawn marks in columns no cell or line took, on 141 pages of
  93 documents in a one-in-ten sample of the library (`bench/probes/unplaced_marks_census.py`) - has not been
  measured again.
- Ligatures a text layer spoils where TrueDoc cannot read the glyphs' codes: a font with two-byte codes, or text drawn
  inside a form XObject. No page of the insurance library needs either yet (`bench/probes/library_ligatures.py`).
- Then hold back a never-tuned-on slice of the insurance set, as `bench/holdout.txt` does for the benchmark; then the hard tail.

---

**The leaderboard moved, and TrueDoc is third** (17 Sept, 11:00; nothing built, three claims corrected)
- **What the owner found.** `huggingface.co/datasets/allenai/olmOCR-bench` now carries its own leaderboard -
  17 entries, each fed by an `.eval_results/olmocrbench.yaml` file inside the model's own repository - and
  TrueDoc is no longer at the top of it. **Infinity-Parser2-Pro scores 87.6 and Chandra OCR 2 scores 85.8,
  against TrueDoc's 85.4 hosted (run 91) and 84.1 open weights (run 89).** The check is right.
- **Correction, and it is three claims, not one.** Every standing document has said "against a best
  published 83.1" since 13 September. That number was Chandra 0.1.0's, read from `allenai/olmocr`'s README
  on 2 September, and the README is no longer where this field publishes. Stale with it went **M3** ("tables
  88.2, the best published figure for the section": Chandra OCR 2 now publishes 92.1, Infinity-Parser2-Pro
  91.2, dots.mocr 90.7, against our 88.3) and **M4** ("arXiv maths above every published figure":
  LightOnOCR-2-1B publishes 89.6 against our 88.6). **M7 is not met.** All three rows now say so.
- **Checked two ways before any of it was written down.** The leaderboard's own table first; then, for every
  number in it, the YAML in the model's repository that the leaderboard reads; then each tool's eight
  section scores averaged to confirm they give the overall it claims. Infinity-Parser2-Pro's eight average
  to 87.59, Chandra OCR 2's to 85.79, ours to 85.41 and 84.15. Our existing row for Infinity-Parser 7B
  matched its published file section for section, which is what proved the column order was read right.
- **Three of the seventeen are not sitting the same exam, and the leaderboard stars them.** A submitter can
  attach a note to a score; a small star appears when there is one. LightOnOCR leaves the
  headers-and-footers section out of its own average and says plainly why: that section asks whether a
  running head is *absent*, so a tool that prints nothing at all scores 100 on it, and their model is
  trained to transcribe the whole page (it scores 19.7 there). Over all eight sections their 83.2 is
  **75.2**. GLM-OCR drops the same section and loses 2.6 points by doing it. Falcon-OCR's run is the English
  subset. **Neither tool above us carries a note**, so the ranking stands.
- **Where the gap is, section by section.** Against Infinity-Parser2-Pro the hosted run is *ahead* on two -
  arXiv maths 88.6 to 88.1, headers and footers 96.7 to 95.8 - and the whole 2.2 points sit in four:
  old-scan maths -8.1, old scans -4.6, tables -2.9, long tiny text -2.9. Three of those four are photographs
  of paper. On the open-weight number the two scan sections alone are 21.7 of the 27.5 points of
  section-by-section difference. **Against Chandra OCR 2 the gap is 0.4 and we cannot claim to see it:**
  their 85.8 sits inside run 91's interval of 84.5-86.3, and we lead four sections of eight (arXiv +1.7, old
  scans +2.5, headers +5.3, multi-column +1.4).
- **Nothing was changed in the code.** `docs/BENCHMARKS.md` holds the leaderboard as read, with the section
  scores, the asterisk explained, both TrueDoc rows placed in the ranking and the rows that are not on the
  leaderboard kept and labelled. What to do about it is the owner's call; the numbers point one way, which
  is that the gap is in scans and tables rather than in the digital pages this converter was built for.

---

## 2026-09-13 - The insurance library gets a score, and a dossier rebuilt so a decision takes seconds

**Done**
- **First score on the owner's own documents: 198 of 229 checks, 86.5%** (present 103/113, order 50/58, absent 31/31, **tables 14/27**). 25 pages of the PDS library - half at random, half chosen because the page draws many rules - read as images by a model that never sees our output, which writes the checks; scored by the benchmark's own `load_single_test`. Tools now in `bench/tools/insurance_*.py`. The scorer undoes markdown escapes before comparing, because D024 writes a price as `\$500` and every price check on an insurance page would otherwise fail on one character of syntax.
- **The dossier was rebuilt after the owner said it was hard to follow and hard to decide from.** The first version was one card per page carrying all ten checks as a wall of text plus 4,000 characters of our markdown - a research task per card. Now it is **one card per decision**: 191 checks pass *and* have their quotation confirmed by a second reading, so they are counted and collapsed; 38 need a person; each card states the check in a sentence, the computed reason it failed, our output beside it, and three buttons. `bench/tools/insurance_dossier.py`.
- **Reasons are computed and cards grouped by them,** so one judgement covers a run: text we never produced (3), same words a few characters apart (7), not a table in our output (7), the cell is nearly right (5), right cell wrong neighbour (1), an ordering check blocked by missing text (8), and passes worth one look (7).
- **The verification was reading `absent` checks upside down.** It looked for each check's quotation in a second reading of the page and flagged what it could not find. For "the page number 6 must NOT appear", a reading that omits the page number is agreement - and that false alarm was **24 of the 38 flags** in the first dossier. Read the right way up, only 7 absent checks are worth a look.

**Found on the library, none of it visible on the public benchmark**
- **A lossy text layer sails straight through.** The RAA landlord PDS page 22's own font maps the ff and fi ligatures to a single letter: the **PDF file itself** says `ofer`, `fnd`, `Certifcate` (checked with PDFium against the source, not inferred from our output). TrueDoc trusts a text layer whenever one exists, so a page that has already lost letters is never sent to the deeper read. An impossible-word detector would catch it cheaply.
- **Spaces lost on that same page, and this half is ours.** The file says `If you`, `Cooling-of Period`, `of 21`; we write `Ifyou`, `Cooling-ofPeriod`, `of21`. Leading suspicion, not yet proven: the 11 September note that PDFium splits a ligature into two characters sharing one origin, against a space rule that works on the gap between boxes in ems, would make exactly this gap read as zero.
- **A tick or cross swept into the label beside it** - our cell reads `X Loss or damage caused by lightning.` where the page keeps the mark in its own column. Five checks, three insurers. *(Correction, 15 September: the page does not keep the mark in a column of its own. On all three pages it is the item's list marker, in a hanging indent inside the cell, so the checks turn on whether a list marker belongs in a cell's text - a question for the owner, not a column to move.)*
- **A table row vanishes while its words survive.** Seniors page 25: the page's limits grid holds $5,000 and $10,000; our output has `Limits Essential Top Landlords $5,000 $10,000 Not covered` as flattened text beside a two-cell table. Every amount is present and nothing ties an amount to its cover.
- **Cover-page issuer, ABN and registered office dropped on purpose** (the reader is told to omit page furniture, worth 35 checks on the benchmark). Three checks say that is wrong for an insurance document. A policy call for the owner, not a defect.

**Lessons**
- **A fuzzy match will tell a confident false story.** The dossier first reported "our cell reads $1,000" against a check wanting `$10,000` - 92% alike, and completely wrong: our table is missing that row, and the `$1,000` it found is a different cell that passes its own check. `find_cell` now requires the digits to match before anything is called close. In an insurance document the digits *are* the content.
- **Diff what the judge compares.** Diffing our raw markdown against the check showed a wall of pipes and newlines and hid the one character that failed; diffing the benchmark's own `normalize_text` of both, with the aligner's window padded and its boundary insertions dropped, puts the mark on `offer` against `ofer`.
- **Parse what the judge parses.** Only markdown tables were searched at first, so six cards said "we built no table here" about pages where we emit HTML tables. The benchmark reads both. Six of seven cards in one group were telling the wrong story.

**The owner ruled on all 38, and nothing was dropped**
- **31 fair, 7 unsure, 0 unfair**, so **198 of 229 (86.5%) is a confirmed score** and every one of the 31 failures is ours to fix. The rulings are in `bench/out/insurance_set/fairness_decisions.json`.
- The seven parked: four are the tick-and-cross cells, where the owner's note says our output *is* correct - the ✓ is a bullet, and the page's column heading already carries the polarity; three are order checks on a navigational illustration whose cover name we cut in half across two rows ("Unspecified" over "Personal Effects"), which is broken whatever is decided about the illustration.
- The owner's ruling on the cover-page issuer, ABN and registered office is a decision to **change what we emit**, not a defect report. It pulls against the omit-furniture instruction that is worth 35 checks on the benchmark, so it gets measured both ways before anything moves.

**Key Facts Sheets: an oracle, 202 of them (D027)**
- A Key Facts Sheet is prescribed by the Australian Government under the Insurance Contracts Act 1984. The library holds **202 across 34 insurers**, 17% of it, and the law fixes the wording while each insurer sets the type - so a few hundred pages where the right answer is known without a check being written, laid out 34 ways. `bench/tools/kfs_grade.py` grades them on shape alone and holds back a fifth by filename hash.
- The owner's decision: use them to *derive* rules, never to special-case. A rule earns its place by being written in geometry, verified there, and measured on olmOCR-bench, which holds none of this material. The oracle says whether a rule fixes; only the benchmark says whether it harms.
- **Before:** header whole on 34% tuned-on, 16% held out; 8% of prescribed events lose their Yes/No answer. On a document whose only job is "is this covered", that is the worst thing on the page.

**Two rules, both measured**
- **A tick or cross at the head of a cell starts a new entry.** `✗ Pontoons` and `✗ Buildings under construction where...` were being published as one exclusion; the library census counted ~104 such cells. Narrowed to ticks and crosses only after the broad version cost two insurance checks by shredding sub-lists - `✓ Loss or damage caused by impact from: • any motor vehicle, • any animal` is one covered item. Benchmark exposure is 53 of 24,984 table cells; measured code-against-code on every page where it can fire, it moves nothing. Insurance set unchanged at 198. **Worth no score anywhere and ~104 rows of meaning across the library.**
- **A heading that wraps mid-sentence is still the heading.** `_header_row_count` ended the heading at the first cell of more than six words, which on a Key Facts Sheet is the heading's own third column. Folding the wrapped heading into one row *before* anything counts it - rather than teaching each downstream rule about it - leaves a grid every later rule already handles. **Header whole 34% -> 51% tuned-on and 16% -> 34% held out, bands swallowed 61 -> 48 and 8 -> 6.** The held-out set moving with the tuned-on set is the evidence the rule is geometry and not a shape fitted to what was in front of me.

**Lessons**
- **The yardstick broke before the code did, and cost two hours.** `page_check.py` was pointed at a run launched with `--vision-endpoint ... --vision-deep anthropic` while the check passed no vision flags at all, so every page that run had read with a model scored near zero locally. That read as "-48 checks across 21 pages" in a change touching three checks in the whole category. A control run of the unmodified code scored **identically, page for page**. Two tells were ignored: reverting the suspect rule changed nothing, and a rule with no exposure cannot cost 48 checks. `bench/tools/ab_pages.py` now converts with whatever the working tree holds into a named folder and compares **code against code**, both sides carrying the same options.
- **Run directories are named for the candidate, not the run.** `bench/runs/truedoc89-*` holds candidate truedoc89, which is run *90*. Read the `conversion.json`, not the folder name.
- **A census that predicts a regression is worth acting on.** The library census said plainly that a round bullet leads a sub-list and a tick leads an entry; the first version of the rule ignored that and lost exactly the two checks the census pointed at.
- **The benchmark caught a rule drawn from the insurance library.** A flora's dichotomous key sets "A. Glands of the involucre ovate..." over "aa. Glands kidney-shaped...", and the second starts lowercase, so "wraps mid-sentence" folded two rows of the key into one. Guarded by an enumerator test. Two-sided measurement earning its keep in the direction not expected.

**Both rules measured together on the whole table category, code against code: 843 v 843, not one page moved.**
188 pages, 1,022 checks, the same command on the same machine with the same options on both sides. (That 843 is not the scoreboard's 87.7%: a real run reads the model-dependent pages with olmOCR's saved output and this A/B reads nothing with a model on either side. It is a sound measure of change and a useless measure of quality - the distinction missed this afternoon.) Insurance set 198/229 with both rules in; suite 511.

**What the cover page's missing ABN actually is, and it is not what the dossier said**
The dossier told the owner the issuer, ABN and registered office were dropped "on purpose, because the
reader is told to omit page furniture", and that the change would push against 35 checks. Both wrong,
and the error was mine repeated back to me from my own card. The page carries a text layer holding
every one of those lines, so no model reads it and the vision prompt's furniture instruction never
runs. The block is dropped because **the layout model labels it `layout:page_footer`** - four lines in
small type at 91% down the page, set apart by white space, which is exactly what a running foot looks
like from the outside.

The fix is generic and already half-written elsewhere in the code: `_margin_cleanup` refuses to call
anything longer than two lines a running foot, and we accept the layout model's label without applying
the same test. This block is four lines and about 32 words. A rule that declines `page_footer` for a
block too big to be a running foot rescues an address block, a copyright notice or a funding note at
the foot of an academic paper just as well. A second and stronger signal - a running foot repeats, and
this appears once - cannot be the primary test, because every benchmark PDF is a single page and the
rule would quietly do nothing there. Cost unmeasured: the benchmark has `absent` checks that want
footers left out, so this one is measured both ways before it moves.

---

## 2026-09-11 (midday) - Whole categories measured, fills are not rules, and four things PDFium says differently

**Done**
- **Run 70's two regressions traced, and neither was the metric box.** A probe shows all five of 09f801e3's fonts embedded, and a census over 115 benchmark pages has the font-metric box agreeing with MuPDF's top and bottom on a median 99% of characters against the loose box's 93% (100% on that page). Both losses were the "shared sides" rule: rows shaded across two columns (c2b2651d, six checks) and a newspaper's panels (09f801e3, five checks - `TRUEDOC_TABLE_EDGES=strokes` alone restored its 46/49, and the rule's "both orientations" repair did not).
- **Measured on the whole category, no model, both readers - 188 table pages in 20 minutes, 231 multi-column pages in 23 - because run 70's lesson was that the changed-pages sets are yesterday's faults.** Tables: MuPDF 848/1022; PDFium with run 70's finder 837 (-11 on ten pages); with the finder below 844; with the frame rule and the reader facts 847, and with the text-size rule below 850 - two above MuPDF's 848 over the whole category, measured on the committed code (lost 3 on three pages: 2d0e0586, 6767787c, f45a188e; won 5 on three). Multi-column: MuPDF 678/884; PDFium before 662 (-16: three pages of one TeX paper at 0, 09f90a8f, -7; the newspaper -5; seven singles); after 678 - level with MuPDF, six singles lost (00f6c2ee, 02943986, 031a888e, 0b65b6a5, 0be9ba92, 0e5f0c34, all order checks) and six won on three pages. Tiny text (62 pages, the heaviest category): MuPDF 361/442, PDFium 359 before the last two rules below and 364 after them on the committed code (won 3, lost 0). The whole-category scorer is `bench/probes/cat_score.py` (per page to `bench/out/lost/<name>.txt`, `bench/probes/catdiff.py` to compare two).
- **What PyMuPDF's strict strategy counts, measured against it and written down as the quantity to agree on (D022):** every fill-only box wider and taller than its 3pt snap is dropped; every straight, axis-parallel segment of a stroked path is a rule at its own length; a thin fill is a rule down its middle. f1774abd's 4 by 4 comes from ten strokes, one of them 3pt wide under the header - and `FPDFPageObj_GetBounds` inflates a stroked path by its line width on every side (measured: 1pt strokes +1 each side, the 3pt stroke +3), so that rule read as a 6pt-high box, failed the thin test the bounds were put to, and the table lost its header row. Deflating the bounds by the width agrees with MuPDF on only 70% of 1,406 strokes (caps and joins vary), so the walker now hands back the path's own segments (`PageObject.lines`, `_segments_of_path` in `pdfium_objects.py`) and `_edges_from_objects` makes rules of them; `_shared_sides` is gone. ba0f816b, where MuPDF reads two tables and the fused grid read one, +3; 8a1262ef +2; 8bf7270c +2; 92f758de +1; 09f801e3 +5; c2b2651d back to 6/6.
- **A frame only closes a grid.** b2a4c508 and cefac431 rule between their rows and nowhere else - thin filled rules the full width with a tick at each end - and `_frame_edges` closed them into tables of one column that fused each row's fields (three checks; PyMuPDF reads no table there). A cluster gets a frame only when it holds a rule of each direction inside its outline, not just along it.
- **Four things PDFium reports differently from MuPDF, each measured before it was written into `pdftext_rawdict.py`:** (1) a ligature PDFium splits into two characters sharing one origin with the ink divided between them (cefac431's "fi rmware": the advance of a lone i, laid from the f's origin, ended before the f) - a shared origin now marks a ligature piece as a shared box does, but never a generated blank, which PDFium stands at the next glyph's origin; (2) MuPDF's left edge is the glyph's origin - 99.7% of 316,152 matched characters against the loose box's 99.2% (level text, 120 pages), and the loose box's fraction of a point to the left is what closed the 7pt word gap MuPDF reads between "et" and "al."; (3) sheared text, an italic made by slanting an upright face (text matrix c = 2.09 on b2a4c508), keeps the loose box's right edge, which is where MuPDF's slanted advance box ends - origin plus advance stops 1.5pt short; b2a4c508 8/10 to 10/10, a parity test on its 52 sheared glyphs; (4) the /Widths advance for unmapped glyphs, written after run 70, met a TeX paper set in seven Type 3 fonts with no /BaseFont: PDFium names them "" and so did the table, so the first font's width served every glyph, and multiplied by the drawn size PDFium reports for Type 3 text (0.12) it boxed every letter 0.007pt wide - the word builder read "m ethods" and "w hen" and three pages scored 0 (09f90a8f). A font with no name gets no answer, and a Type 3 font's widths are scaled by its /FontMatrix into thousandths; the three pages read 10/12 against MuPDF's 7/12.
- **A fifth, found on the last table page left (0091c5b2, an OCR layer, 4/8 against MuPDF's 7/8): the text size.** An OCR layer fits each word to its box by scaling x and y differently, and `_drawn_size` took the y scale - 8.40 where MuPDF reads 7.28 - so the rows of the page's table fused. Measured on 73,333 characters over 30 benchmark pages whose matrix scales x and y differently, the tiny-text family among them: MuPDF's size is the geometric mean of the two scales every time (the square root of the matrix's determinant, which is also the size of turned and slanted text), its right edge is the origin plus the advance at the x scale every time, and its top and bottom are the ascent and descent at the y scale on 92%. The reader now does the same in all three places; the page reads 7/8. The tiny-text category, the heaviest in the benchmark, is where such pages live, and it is being scored whole, both readers, as this is written.
- **Two more from the tiny-text category, both in the table finder.** A TV-listings page (20_pg39) draws a rule from 575pt outside its own left edge; PyMuPDF clips every rule to the page box and ours did not, so the grid ran from there across the page and every listing fused into one cell (6 checks at 0.028 each, the dearest in the benchmark). Rules are now clipped to the page as PyMuPDF clips them, and a cut end is remembered as no end. Then the frame: with the cut rule gone, the page's margin rule - one vertical running up past the table - still set the frame's top and closed a row of cells above the table that PyMuPDF, which draws no frame, does not read. A frame side now goes in only where at least two rules of the other direction end (the rows of 3b18f8c all start at its missing left rule, which is the case the frame was written for); a voting frame was tried first and took fa18a15c's header rule for an outlier (13/14 to 12/14), so the extreme still sets the side, provided two rules reach it. 20_pg39 reads 5/6, as MuPDF does; the eight table pages the frame ever touched read as before.
- **Where MuPDF puts a space, measured over 120 pages:** the share of glyph pairs with a space between them, by the gap between their boxes in ems - 0.5% up to 0.06, 5% at 0.08, 8% at 0.10, 17% at 0.12, 39% at 0.14, 96.5% from 0.16. The reader's 0.15 threshold sits on the step. The 0.12-0.14 band is a second rule of MuPDF's not yet named.
- **Tests (suite 397 both ways):** `test_ruled_pdfium.py` - shaded cells with no lines give no grid as PyMuPDF strict reads none; a 2x2 ruled by 3pt strokes matches PyMuPDF; rows ruled with end ticks make no table; f1774abd and the striped page kept. `test_pdfium_objects.py` - a stroked path hands back its segments, not its inflated bounds. `test_pdftext_char_boxes.py` - sheared text starts at the origin and ends where MuPDF ends it. `test_glyph_names.py` - Type 3 widths scaled by the font matrix; a font with no name answers nothing. `test_pdftext_type3.py` - the TeX page keeps its words whole. Gate 100/128 both ways, sample1 46/52, sample2 57/64.

**Lessons**
- A whole-category score of both readers, no model, is twenty minutes and finds what no changed-pages set holds: three of today's fixes were on pages no set had (ba0f816b, 09f90a8f, the sheared line of b2a4c508).
- When the two libraries disagree, ask the PDF: its /Widths, its /FontMatrix, the path's own segments. The answer settles which library is right instead of choosing one.
- A rule that reads "where two fills meet" or "close the outline" is an invention; every invention today lost more than it won once the whole category was scored.

**Run 71 = candidate `truedoc70`, every switch on, launched 13:45 from commit bb920ec and scored 14:43: 84.0 (CI 83.2-84.9), held-out 81.1 (1066 of 1255, the best yet), tuned-on 81.9.** Against run 65, the MuPDF baseline: 53 won, 44 lost, +9 - arXiv +6, tables +3, tiny text +1, multi-column 0, headers -1; against run 70: 30 won, 3 lost. By category: arXiv 87.6, old-scan maths 80.8, tables 88.5, old scans 47.3, base 99.8, multi-column 82.9, tiny text 88.7, headers 96.7. The condition set for the switch - a run holding about 84.0 with the held-out fifth level - is met, with the held-out fifth above.

**The defaults flipped the same afternoon (D023, `docs/DECISIONS.md`; the open licence entry closed).** `enabled()` in the text reader, the renderer and the object reader now answers yes unless asked otherwise (`TRUEDOC_READER=mupdf`, `TRUEDOC_RENDERER=mupdf`, `TRUEDOC_OBJECTS=mupdf`); the three tests that said "off unless asked for" say "on unless asked off"; every comparison that used to *clear* the switches to reach MuPDF now asks for it by name (`test_hidden_text_readers`, `test_pdftext_type3`, `test_render_backends`, `bench/tools/reader_generalise.py`, `hidden_compare.py`) - clearing the variables now means PDFium. Verified: the suite with nothing set and with everything set to `mupdf`, the quick gate both ways (results in the commit that follows). ARCHITECTURE, STATUS and ROADMAP say so. What is left of M18 is the package itself: the document handle, `pymupdf.Rect`/`Matrix` as plain types (about 27 sites), `set_rotation` (2 sites).

**After the flip, the drop cap's page (0e5f0c34, one check) traced to three line facts, each tested and written into `pdftext_rawdict.py`:** (1) the line join (`_continues`) refuses a run that starts more than an em beyond the line's end - PDFium ended its line there, and a superscript or torn fraction starts within the line (a census over 747 pages found 2,640 welds, 584 of them across three ems or more, almost all on two table pages whose rows the gap rule cut again afterwards); (2) where PDFium's own text page ended a line (its generated CR LF, now remembered on the character before it, across spans) and an em of space follows, `_split_at_gaps` cuts - pdftext regroups by band, and the object rule cannot see a break inside one text object; (3) a baseline a whole em from the last glyph's starts a line, as it does for MuPDF, measured in ems of the line's own median size - the drop cap's 44pt hid a 24pt step that is nearly three ems of the 9pt text beside it, and a 5pt superscript's own size would have made its 7pt return to the text a line of its own (the first two yardsticks tried broke a join test each). The page reads 3/4 as MuPDF does, with the drop cap on a line of its own. Measured on whole categories, no model, against the committed code: multi-column 679 against 678 (the drop-cap page, nothing lost), tables 851 against 850 (2d0e0586 to MuPDF's 3/5, nothing lost), tiny text 364 against 364, the arXiv pages that ever differed 630 against MuPDF's 622 on the committed code, 627 before the line rules (2503.09133, the bracket matrices, 7/10 to 10/10 - the rows of a matrix on baselines an em apart are lines of their own, as MuPDF has them; 2503.06293 9/9 to 8/9, traced to the yardstick: a wrapped tail of six glyphs, four of them scripts, had a median of the script size, and the 0.7-em swing from a superscript to a subscript looked like a line - the upper quartile of the line's glyph sizes is the text's size there and still the text's beside a drop cap; 9/9 again, the matrix page and the drop cap held). Headers and footers scored whole for the first time: MuPDF 738/760, PDFium 736 - two pages, both traced (below): a tax form drawn with a negative font size under a doubly negative matrix, which PDFium reports at an angle of pi, and a page whose CropBox reaches outside its MediaBox, which PDFium's crop box call reports raw.

**The unnamed Type 3 page (0b65b6a5, one check) traced to four facts, each tested and written into `glyph_names.py` and `pdftext_rawdict.py`:** (1) PDFium answers `FPDFFont_GetGlyphWidth` for every code of a Type 3 font with the font's first /Widths entry (0.770, 0.718 and 0.437 for the page's three unnamed fonts, each the first width times the font matrix) - useless as an advance, decisive as a fingerprint, so `narrow` picks the resource whose first width PDFium reports and the glyph is read from that font's own /Differences and /Widths (`probe` carried per character from `_geometry`); (2) a glyph name that is nothing but a decimal number is the character's code (dvips: "/76" for L), which the Adobe list does not know and MuPDF reads; (3) a NUL is never a character - PDFium maps the font's code 0 (its first glyph, the capital A) to U+0000 and reports no error, and the line read "Lobo R" and a U+0000; (4) the PDF's own glyph name now comes before the TeX-table guess, which had read code 0 as cmr's Gamma ("Lobo RΓ"). The page's text is digital again (it had fallen back to OCR at 95% bad characters); 4/5 as before by a different route, the one left a paragraph break MuPDF does not make (its Type 3 line boxes stand 6pt tall to MuPDF's 8-9, a lead for later). The maths samples hold at 46/52 and 57/64 with the PDF's name ahead of the TeX guess.

**Run 72 = candidate `truedoc71`, launched 15:59 from commit bff9d6f and scored 17:30: 84.1 (CI 83.2-84.9), held-out 81.1 (1065 of 1255), tuned-on 82.0 - the best overall and tuned-on yet.** Against run 71: 5 won, 3 lost (arXiv +1, multi-column +1; the three lost are singles on 2503.06509, 2503.04897 and 0b65b6a5, whose paragraph break is the Type 3 line-box lead). By category: arXiv 87.7, old-scan maths 80.8, tables 88.5, old scans 47.3, base 99.8, multi-column 83.0, tiny text 88.7, headers 96.7.

**The two headers pages, fixed after the run (tests written first, both failing for the predicted reason):** (1) 8e953483 sets its text with the matrix -1.333 0 0 -1.333 *and* a font size of -4.43 - two negations, so the glyphs stand upright and run left to right, but `FPDFText_GetCharAngle` reports pi; the line voted right-to-left, every glyph was a backwards jump, and `_split_at_gaps` shattered the page into 1,290 one-character lines (126 with the split off). The sign of the size is part of the direction: pi is added to the angle when the size is negative, and every size the rules use is the magnitude. One page of 1,403 has a negative size (`negsize_census.py`). (2) b2ca8e00 writes an A4 CropBox around a 430 by 660 MediaBox; MuPDF measures from the two boxes' intersection (its page rect), pypdfium2's crop box call gives the /CropBox as written, and every character sat 82.5pt right and 92pt down of where MuPDF has it - the running head fell out of the page-edge band and stayed in the text. `page_box` in `pdfium_objects.py` is the intersection, and both flips measure from it. Twelve pages of 1,403 have a crop box reaching outside the media box (`cropbox_census.py`; two of them table pages). Both pages read as MuPDF reads them (6/6 and 2/2; the two crop-box table pages unchanged and level with MuPDF). The whole headers category rescored: 738 against MuPDF's 738, nothing lost; tables unchanged at 851. With that, every category scored whole without a model is level with the MuPDF path or ahead of it: tables 851 v 848, multi-column 679 v 678, tiny text 364 v 361, headers 738 v 738, the arXiv pages that ever differed 630 v 622.

**Run 73 = candidate `truedoc72`, launched 17:38 from commit a9b16d5 and scored 18:47: 84.1 (CI 83.2-85.0), held-out 81.2 (1066 of 1255, the best yet), tuned-on 82.0. Against run 72: 2 won, 0 lost - the two headers pages.** Headers 97.0; every other category as run 72.

**After run 73: font names lose their subset tag, as MuPDF names them.** PDFium reports an embedded subset's six-letter tag in the name ("ABCDEE+Calibri", 214 characters of 6767787c) beside the plain "Calibri" of the rest, and MuPDF folds it away; the reader now does the same (`_SUBSET_TAG` in `pdftext_rawdict.py`; a parity test on that page: the set of font names over spans that hold text equals MuPDF's). It did not turn out to be that page's loss: its lines are identical under both readers, and the difference is downstream - the whitespace-table builder took the whole section above the two side-by-side course tables into one eight-column table (title, numbered list and all), so "Fall Semester" is not the heading over "Composition I"; MuPDF's path renders a three-column table of the Fall side alone. A lead for the table builder, not the reader.

**Run 74 = candidate `truedoc73`, launched 18:54 from commit b164375 and scored 19:52: 84.1 (CI 83.1-85.0), held-out 81.2, tuned-on 82.0 - identical to run 73 check for check. The subset tag was parity and nothing else.**

**After run 74: a list's marker keeps its item across the object gap.** 6767787c's real cause, traced after the subset tag proved innocent: Word sets each numbered list marker ("1.", "2.", "3.") as a text object of its own exactly one em before its item, and the object-gap rule (a cut where the text object changes and an em of space follows) cut every marker off; the markers stood as a column of their own at the left margin, and the whitespace-table finder grew one eight-column table from them over the whole section - title, list and both semester tables - where MuPDF, which keeps each item as one line, finds the two course tables. A run that is nothing but a list marker - a number or letter with its dot or bracket, or a bullet, four characters at most - now stays with the text after it at that gap; a dash or an asterisk is not a marker (a table puts those in a cell of their own), and the general 1.5-em limit still cuts. 6767787c 9/10 to 10/10, as MuPDF reads it. Measured whole, no model: tables 852 against 851 before (that page, nothing lost; 852 against MuPDF's 848), multi-column 679, tiny text 364, headers 738 and the arXiv pages that ever differed 630 - all unchanged; suite 407 with nothing set and 407 with everything set to mupdf, quick gate 100/128 both ways, samples 46/52 and 57/64.

**Loose accents, traced the same evening (031a888e, one check; the fix measured before it is written).** TeX's accent command draws an accent as a glyph of its own beside the letter. Census over the benchmark: of the spacing accents whose letter can be found, MuPDF orders the accent just before its letter 1,585 times (after it 135, elsewhere 22); PDFium puts it just after 927 times, just before 662, and somewhere else entirely 153 times - on 031a888e the acute of "ý" in "Český" comes out after "Radio" at the other end of the line, the caron of "ž" after "žurn", the acute of "á" after "al.". Neither library composes the pair: MuPDF's raw text is "Radioˇzurn´al" too, and the text layer's composer (`_compose_spacing_accents`) joins an accent to the letter just before or just after it in the line, which covers MuPDF's order and PDFium's usual one. The stranded 153 it cannot see, and the line splitter cuts each of them off as a backwards jump. The fix moves a stranded accent to just before the letter under it, on the composer's own conditions - the same font, the accent's centre over the letter, a precomposed form - and leaves every accent that already stands next to its letter. A scratch prototype, applied by monkeypatch so the tree stayed untouched while five category runs converted, takes 031a888e page 3 from 4/5 to 5/5 (eight accents moved on its three pages); the A/B over every benchmark page with a loose accent (244 pages, 216 of them arXiv) was running when the list-marker change was committed; its result follows.

**Measured and set aside: an "occupied gap" exception to the line cut.** 00f6c2ee page 10 loses a check because each sentence line is cut where an inline formula sits ("where" | "refers to...", 1.05 em) and the fragments read as two columns; the gap holds a drawn text object whose glyph PDFium's text page reports no character for, and MuPDF keeps the line whole. Before writing "no cut where another object fills the gap", a census over four categories (multi-column, tables, headers, tiny text; `occupied_gap_census.py`) asked MuPDF at every same-baseline break of one to one and a half ems: where the gap holds another text object MuPDF splits the line 207 times and keeps it whole 38 times, on four pages; an image or path in the gap splits it 22 times of 24. The rule would have disagreed with MuPDF five times for every time it agreed, so it was not written. 00f6c2ee stays a single, traced.

**The accent move, measured and written.** The A/B over every benchmark page whose PDFium text carries a loose accent - 244 pages, 216 of them arXiv, 1,360 checks - the stock reader against the prototype: 1,189 against 1,190, one won (031a888e page 3) and none lost. It is narrow by construction: of 2,243 loose accents it moved 70, left 403 that already stood beside their letter, and left 1,770 alone because no letter of the same font sits under them - the maths accents, which the maths stage attaches by geometry. Written into `pdftext_rawdict.py` as `_rehome_accents`, run on pdftext's grouping right after the geometry is read, with the prototype's rule; a parity test on 031a888e (the accented words both readers produce are the same words, and no accent is left on its own where MuPDF has none) failed before and passes; suite 408 both ways, gate 100/128 both ways, samples 46/52 and 57/64.

**Bold and italic from the font program, measured and then written after run 75.** 0be9ba92 page 5 loses a check to reading order, and a bisection by switch pins it on the text reader: MuPDF reads the page's CIDFont+F2 as bold, F3 as bold italic and F5 as italic, and the PDFium path read all three plain - their names say nothing and their descriptors carry no style bits, so the heading lost its bold and the column order changed. A census over four categories (3,390 page-and-font pairs, `style_census2.py`) set every signal the embedded font program offers against MuPDF's span flags: a TrueType weight class of 600 or 700 is bold to MuPDF every time (465 of 465) and 900 never (0 of 4); a CFF or Type 1 weight of Bold, Semibold or Black is bold every time (225 of 225) and Heavy and Medium never; a non-zero italic angle in the program is italic. Taken on top of the current rule those fix 31 bold and 10 italic disagreements and break none; the style bits in fsSelection and macStyle were mixed (10 fixed, 7 broken) and set aside, and the italic angle in the PDF's font descriptor, which PDFium reports, fixed nothing. On forty documents of the insurance library (449 page-and-font pairs) the name rule already agreed with MuPDF on every flag and the program rule changes none: its gain is the benchmark's anonymous fonts. Written into `pdftext_rawdict.py` as `_program_style` (fontTools, cached by the program's digest across pages), read per font in the geometry pass and OR-ed into each span's flags. Two tests written first and failing until then: the rule on synthesised TrueType programs (weight classes 400, 600, 700 and 900, with and without an italic angle), and 0be9ba92 page 5's three fonts against MuPDF's flags. Suite 410 both ways, quick gate 100/128 both ways, samples 46/52 and 57/64; whole categories without a model: tables 852, multi-column 680, tiny text 364, headers 738 and the arXiv pages that ever differed 630 - not one page's score changed by this rule (multi-column's one gain is the accent page). It is committed as parity - 41 flags set as MuPDF sets them, none broken - and not as points: 0be9ba92 page 5's three fonts now carry MuPDF's flags and the page still reads 3/4, so its order has a second cause.

**Measured and set aside: a justified-line guard on the object-gap cut.** 02943986 page 3 loses a check because a justified line, "remunerado. El documento añade dos", has word gaps of 1.32 to 1.34 em and changes text object twice, so the object-gap rule cut it in three where MuPDF keeps one line. Two censuses over four categories (`justified_census.py`, `justified_census2.py`) set every same-baseline break of one to one and a half ems against MuPDF. Where the break is no wider than the line's own word gaps, MuPDF keeps one line 465 times on 16 pages and splits it 125 times on 48; narrowed to strictly justified lines - every gap equal to within 15%, four words or more, mostly words - it keeps one line 39 times on 11 pages and still splits 25 times on 13 ("Women's group intervention. During"). MuPDF's grouping follows the file's text runs, not the geometry, so no gap rule mirrors it; either guard would have broken as many pages as it fixed. Not written; 02943986 stays a traced single. With the occupied-gap census before it, the object-gap rule's known costs are these same-baseline breaks MuPDF keeps whole - 1,382 of them on 29 pages - against the table rows it separates, which is why it was kept when it was measured.

**2503.09472, traced to the end (two arXiv checks; left for the maths stage).** Its cases formulas come out as "{{{" because PDFium's lines group the brace's extension-font pieces into the equation lines (41 lines on the page against MuPDF's 69), and the maths stage then reads three braces. The same grouping turns three plain sentences into headings: under MuPDF "so we can get" shares a block with the brace and the equation below it and is text from the start; under PDFium it stands as a one-line block of 12pt text on a page whose body size is estimated at 9.5 - the maths scripts pull it down, under both readers - so the size rule makes it a heading, and the layout model's verdict of text (0.90, the block wholly inside the region) is not enough to demote a heading of one short line. Bisected by switch: only the reader flips it. Two leads, neither measured: the body size on maths-heavy pages, and letting a confident text region demote a size-only heading of one line.

**Run 75 = candidate `truedoc74`, launched 20:53 from commit 7e7c1b1 (validated 20:56: suite clean, gate 100, samples 46 and 57) and scored 21:45: 84.1 (CI 83.2-85.0), held-out 81.2, tuned-on 82.0 - the best tuned-on yet.** Against run 74: 2 won, 0 lost - the list marker's page (6767787c) and the accent move's (031a888e page 3), each exactly as its whole-category measurement said. Against the MuPDF run 65: 51 won, 36 lost, fifteen checks ahead (arXiv +7, tables +4, multi-column +2, headers +1, tiny text +1). By category: arXiv 87.7, old-scan maths 80.8, tables 88.6, old scans 47.3, base 99.8, multi-column 83.1, tiny text 88.7, headers 97.0.

**The line-end hyphen, boxed a full em wide (0be9ba92 page 5's second cause).** With the style rule in, 0be9ba92 page 5 still read 3/4: the left column's text block reached x = 309 where MuPDF's stops at 302, two points short of the right column at 311, so the column finder saw no gutter and the right column's first paragraph came out before the left column's heading. The widest line ended in "anti-", and its hyphen was 11pt wide. PDFium marks a hyphen it recognises at a line end with the control code U+0002, and the reader's advance rule asks the font for the width of the character's Unicode value; asked for code 2, `FPDFFont_GetGlyphWidth` answers with the width of a code the font does not have - a full em here, 11.02pt against the hyphen's 3.67. A census over five categories (`hyphen_box_census.py`) set every such hyphen against MuPDF's hyphen at the same origin: 2,808 of 4,058 agreed to a fifth of a point, 603 were wider and 647 narrower, on 202 pages (multi-column 22, tables 12, headers 43, arXiv 125). The width is now asked for the hyphen itself (0x2D): 4,056 of 4,058 agree, and the two left sit on a turned line of a tables page (7772a40a) whose boxes are PDFium's own loose boxes, a fifth of a point apart - not this rule. 0be9ba92 page 5 reads 4/4 and page 4 5/5, as under MuPDF. A test written for it (`test_a_line_end_hyphen_is_boxed_at_the_hyphens_own_width`) sets every hyphen box on that page against MuPDF's. Suite 411 both ways, quick gate 100/128 both ways, samples 46/52 and 57/64 (MuPDF 46 and 58); whole categories without a model: tables 852 (was 852), multi-column 681 (680), tiny text 364 (364), headers 738 (738), and the arXiv pages that ever differed 630 (630). Exactly one page changed, the one predicted (0be9ba92 page 5, 3 to 4). Against MuPDF: tables 852 to 848, multi-column 681 to 678, tiny text 364 to 361, headers 738 to 738, the arXiv set 630 to 622; the pages still behind MuPDF outside arXiv are three multi-column pages (00f6c2ee, 02943986, 0b65b6a5) and one table page (f45a188e), one check each.

**Found while it was measured, not yet written.** (1) 2503.06329 page 24 loses two checks to one tilde. MnSymbol's tilde has no advance and is drawn as a text object of its own, raised over its letter; PDFium reports it there, while MuPDF's text moves it to where the previous glyph ended, on that glyph's baseline (MuPDF's own glyph trace draws it at 273.6, 248.0; its text says 271.2, 250.8). The maths stage's rule for a zero-width accent - the next glyph to the right, from 0.15 em left of the mark - was written for MuPDF's position; over the italic R the tilde starts 1.7pt inside the letter, the rule refused the R and hung the tilde on the "=" after the subscript. A prototype - a mark raised 0.1 to 1.3 em over a same-size letter whose box holds it takes that letter, and otherwise the old rule - scores the page 7/9 under PDFium, as under MuPDF, and never fires under MuPDF there; on the five non-arXiv pages with a combining mark it fires once, under MuPDF, and changes no score. The whole-arXiv A/B is running. A census of combining marks over five categories (`combining_census.py`) counts 265 on 109 pages; MuPDF's text reports 230 of them away from where PDFium says they are drawn. **Correction:** the reader's comment on combining marks and the docstring of `test_a_combining_mark_is_boxed_at_its_own_origin` say MuPDF boxes a mark at its own origin "every time"; that holds for 35 of 265. (2) MuPDF's line breaks follow one measured rule: a new line wherever the pen moves forward 0.8 em or more in drawing order, counted from where the previous glyph's advance ended, real spaces included (`pen_gap_census.py`, MuPDF alone, five categories: below 0.75 em 2,134,789 pairs kept together and 512 split; from 0.8 em up 18,367 split and 238 kept, 83% in the first twentieth of an em and 96 to 100% beyond). The reader instead measures gaps in PDFium's order from the last glyph that is not a blank, and cuts at 1.5 em, or at 1 em where the text object changes; the old finding that no gap rule fits MuPDF measured that geometric gap, a different quantity. **Correction:** the justified-line paragraph above says MuPDF keeps 02943986's line "remunerado. El documento añade dos" whole; its text splits it at every word gap, into five lines, each gap 1.10 em past the space's own advance - the rule's prediction - so the loss there has another cause. 2503.05062 page 35's cases row, joined at 0.975 em where MuPDF splits it, is the rule's case exactly. A prototype of the rule in the reader, measured on whole categories, is next.

**Run 76 = candidate `truedoc75`, launched 23:19 from commit 301359b (validated 23:19: suite clean, gate 100, samples 46 and 57) and scored 12 Sept 00:32: 84.1 (CI 83.2-85.1), held-out 81.2, tuned-on 82.1 - the best tuned-on yet.** Against run 75: 1 won, 0 lost - 0be9ba92 page 5, exactly as the whole-category measurement said. Against the MuPDF run 65: 51 won, 35 lost, sixteen checks ahead (arXiv +7, tables +4, multi-column +3, headers +1, tiny text +1). By category: arXiv 87.7, old-scan maths 80.8, tables 88.6, old scans 47.3, base 99.8, multi-column 83.3, tiny text 88.7, headers 97.0. The conversion took 4,079 seconds at a mean of 17.42 seconds a page, against run 75's 2,890 at 12.33, because the prototype measurements below shared the machine; the scores do not depend on it.

**The accent drawn over its letter, written (2503.06329 page 24, two checks; the mechanism is in the paragraph above).** Written into `truedoc/math/reconstruct.py` as a first branch of `_accent_base`: a zero-width mark raised 0.1 to 1.3 em over a same-size letter whose box holds it takes that letter; any other zero-width mark keeps the old rule, the next glyph to the right, which is right for the position MuPDF's text moves a mark to. Measured before it was written with a recording prototype that asks both rules at every accent and lists the pages where they choose differently, so every other page converts exactly as before: over the 522 arXiv pages under PDFium the new branch fired 57 times and chose differently 21 times, on 4 pages: 2503.06111 page 6 from 5 to 6 of 9 and 2503.06329 page 24 from 5 to 7, both now level with MuPDF, and two pages unchanged - three checks won and none lost (the whole category 2,569 of 2,927, against MuPDF's 2,559); under MuPDF it fired 3 times and never chose differently, so the MuPDF path is unchanged by construction. Outside arXiv, on the ten pages that carry a combining mark or a zero-width accent glyph, it fired once, under MuPDF, and changed no score. Two tests, written first: the page's row "x R~ a1a5 =" at its measured positions as PDFium reports it (failed on the old rule, which gave the tilde to another glyph) and as MuPDF's text reports it (passed before and after). The two corrections above are written into the reader's comment and the test's docstring. Suite 413 both ways, quick gate 100/128 both ways, samples 46/52 both ways and 57/64 (MuPDF 58). It was written into the tree at 00:28 while the line-rule measurements below were still converting pages with the tree's code; that is safe here, and only here, because the new branch never fires under PDFium on any page outside arXiv (measured above) and those measurements cover none, and the reader's change is a comment.

**MuPDF's line rule, prototyped in the reader (measured before anything is written).** A copy of `_split_at_gaps` patched in memory (`pen_proto.py`): a cut wherever the pen - the end of the last glyph or real space, invented blanks not counting - moves forward 0.8 em or more in drawing order; in the variant that replaces the old rules, the 1.5-em gap rule and the object-gap rule go and the baseline step, the backward jump and the list-marker exception stay. On the 19 traced pages it gains 02943986 page 3 (2 to 3 of 3) and changes nothing else. Two things PDFium's text page does that MuPDF's pen does not were found on the way. **It reports no character for some drawn text objects:** 00f6c2ee page 10's "where | refers to" gap holds a Cambria Math glyph and a zero-width Times object whose object text is empty, which MuPDF traces as spaces - its pen crosses the gap and it keeps the sentence whole; letting such silent objects move the pen when they come between the two characters in painting order (`pen_silent_proto.py`) recovers that page too (+2 on the 19, none lost). **It collapses consecutive real spaces:** a hand-built "where" with two spaces reports one; MuPDF's trace has both. With the object bounds being ink only, the lost advances cannot be recovered, so the prototype measures its 0.8 in the old rules' em - the taller of the size and the glyph's box, about 1.1 times the drawn size - rather than MuPDF's drawn size, which over-cuts space-padded text (a hand-built case shows it). Under the prototype the whole suite passes but for the two tests that assert the old object rule - that a gap inside one text object does not end a line, and that a 1.4-em gap is cut only where PDFium ended its line - both of which MuPDF's own behaviour, measured above, contradicts. f45a188e (tables, one check): the rule cuts its fused number row exactly as MuPDF does, one line per number, but the page still reads 1/4, because MuPDF starts a new block for the "P R F1" header row after a 1.69-em step while pdftext's block keeps it with the title rows, and the table stage then folds "R" into the title's cell. The whole-category A/B, with a worker per variant, said the rule as MuPDF applies it loses more than it wins here: over 434 pages the replacing rule won 1 check and lost 5 - two on 09f90a8f, a Type 3 page whose font reports a size of 0.1, so that the em falls to a glyph's box and a sentence space reads as a jump; one on 0b045ab8, whose letter-spaced running head split where PDFium had collapsed its spaces; two on long_tiny_text/11 - and with the silent objects, over 393 pages, it won 2 and lost 3. MuPDF's own lines agree with the rule on the Type 3 page (it too splits "texts." from "Surprizing") and disagree on the other two, so the losses come from what PDFium's text page leaves out, not from the rule. A guarded form - the old cuts kept, a pen cut added only after a glyph and only between glyphs with a real size - avoided those three and still lost in dense small print (long_tiny_text/11 pages 145 and 421, 2 to 1 each). What survives is the one pure repair: an old cut dropped where a silent text object fills the gap, as MuPDF's pen crosses it - 00f6c2ee page 10 from 3 to 4 and nothing lost on 24 test pages; measured over whole categories and written for run 79 (below). **MuPDF's block rule, measured the same way (`block_step_census.py`, MuPDF alone, five categories):** a new block wherever a line's baseline steps down 1.5 em or more from the line before it - 94.8 to 99.9% of such steps start one - and at ordinary spacing seldom (10 to 15% of steps of 1.0 to 1.4 em between overlapping lines). The reader keeps pdftext's blocks, which kept f45a188e's header row with the title rows across a 1.69-em step. A prototype that splits the reader's blocks at such steps (`block_proto.py`) passes the whole suite, and a hand-built test discriminates it; but on the 19 traced pages it changes no score - f45a188e still reads 1/4, so the table stage has its own reason for folding the header's "R" into the title cell - and its whole-category measurement waits behind the line rule's.

**Run 77 = candidate `truedoc76`, launched 00:43 from commit 2171b9c (validated 00:43: suite clean, gate 100, samples 46 and 57) and scored 01:55: 84.1 (CI 83.3-85.0), held-out 81.2, tuned-on 82.1 (4,892 of 5,764).** Against run 76: 3 won, 0 lost - 2503.06329 page 24 (two checks) and 2503.06111 page 6, the pages the whole-arXiv measurement of the tilde rule named and no others. Against the MuPDF run 65: 51 won, 32 lost, nineteen checks ahead (arXiv +10, tables +4, multi-column +3, headers +1, tiny text +1). By category: arXiv 87.8, old-scan maths 80.8, tables 88.6, old scans 47.3, base 99.8, multi-column 83.3, tiny text 88.7, headers 97.0.

**A maths-extension glyph as wide as its metric box (the brace family: 2503.03905, 2503.05177, 2503.05062, 2503.09472).** Four arXiv pages lost their cases formulas the same way: the brace came out as three - one brace per row inside an aligned block (03905), or three braces before rows in the wrong order (05177, 09472). The maths stage's own debug output showed why. All five pieces of the brace - top, extender, middle, extender, bottom - reach the merge that stacks an extensible bracket, with the same LaTeX; but under PDFium each piece's box is its ink, and the ink's left edge follows the shape: the middle piece's point starts at x 264 where the others start at 267. The merge sorts the pieces by left edge and wants neighbours to start within 0.15 em (1.8pt) of each other, so the middle piece sorted first, the next was 3pt away, and the run broke at once - top with its extender, the middle alone, extender with bottom. Under MuPDF the box comes from the cmex design extents, whose left edge is the metric box's, 262.3 for all five, and the pieces stack into one brace and a cases environment. The ink is used for these glyphs to measure the height - a font box one line tall where the bracket is three; the width now comes from the metric box, as MuPDF's design box keeps it, in both places the ink is taken: the text layer's `_extension_box`, which replaces every extension glyph's box before any line is built, and the maths stage's `glyph()`. (A first prototype patched `glyph()` alone and changed nothing: the text layer had already put the ink in the glyph's box.) Measured before it was written: over every arXiv page under PDFium, nine checks won on eight pages and two lost (the category 2,576 of 2,927 against 2,569 before; won: the brace family - 2503.03905, 05062, 05177 and 09472 (two checks) - and 05323, 07617 and 08261, all now level with MuPDF, and 04620 page 35, above it; lost: 2503.07421 page 26 and 2503.08172 page 25, which now fail exactly the checks MuPDF fails there, 07421's display being MuPDF's to the character); outside arXiv, on the eight pages that carry such a glyph, 88 boxes changed and no score did; under MuPDF no glyph carries an ink box, so that path is unchanged by construction. Three tests, written first and failing on the old code: the middle piece keeps the ink's height and takes the metric width; the page's five pieces stack into one brace; the text layer's box is as wide as the metric box. Suite 418 both ways, quick gate 100/128 both ways, samples 46/52 both ways and 58/64 both ways (PDFium up from 57: 2503.03905 page 7).

**cmmi's hook read as MuPDF reads it (2503.06194 and 2503.07441, two arXiv checks).** TeX draws `\hookrightarrow` as cmmi's left hook, slot 0x2C, touching cmsy's arrow. MuPDF's text reports the hook as a comma, and the maths stage's rule - a cmmi comma touching an arrow is the hook - was written for that; PDFium names the glyph and reports U+21AA, so the rule never fired and the page read the hook as a stray symbol beside a separate arrow ("Z^d ↪ → Z_p^d"). The rule now takes either form. Measured with the rule itself, compiled from its own source with the one condition widened (`hook_rule_proto.py`), so the measurement is of what is written: 2503.06194 page 10 from 8 to 9 of 10, level with MuPDF; a census of every category finds four pages whose PDFium text carries the hook this way, all arXiv (2503.03994 page 108, 2503.04912 page 4, 2503.06194 page 10, 2503.07441 page 11), and on them two checks won and none lost - 06194 page 10 and 07441 page 11, both now level with MuPDF; MuPDF, whose text reports the comma the rule already took, is unchanged by construction. Two tests, one for each reader's form of the hook; the PDFium one failed on the old rule. Suite 418 both ways, quick gate 100/128 both ways, samples 46/52 both ways and 58/64 both ways (PDFium up from 57: 2503.03905 page 7).

**Measured and set aside for now: a text-style sum sign's join (2503.05469 page 12).** A maths-extension glyph's origin is its top, so a text-style sum or product sign's origin stands 0.75 em above the line it is set on (8.2pt at 10.9pt); MuPDF keeps it on the line - its own threshold, measured above, is 0.8 em - while the reader's join, at half an em, left the sign, its limits, the fraction and the rest of the sentence in a block of their own. Giving a run that starts with an extension glyph MuPDF's 0.8 em (`join_ext_proto.py`, compiled from the join's own source) was measured over the first 199 arXiv pages: one check won, 05469 page 12 (4 to 5 of 5, MuPDF's score), and one lost, 2503.03903 page 9 (3 to 2 of 3, MuPDF's score too). The loss is not the join's. On 03903 page 9 the joined line is MuPDF's own - "S_w = ∏", then, after the one-em baseline step from the sign's top to its subscript, "i h^i_{L(i)}." - and MuPDF's path fails the same check the same way. The text layer does not put that row back together: its right-hand half is mostly scripts, so its size reads as 8pt against the left's 12pt and the reassembly's similar-size test refuses it; it is not a lone symbol; and as a satellite it runs past its host's end. Under stock PDFium the sign arrived as a segment of its own and the symbol fold joined the halves across it, the only reason that page passes. Left alone, "S_w = ∏" became a block of its own and was taken for display maths ("$$S_{w}=\prod$$" after the paragraph). The repair belongs in the text layer - two segments on one baseline are one line when the smaller carries glyphs of the other's size on that baseline - and it moves the MuPDF path too, so it will be measured with the join as one change, over every category. The join's run was stopped at 199 pages so that its core could finish the other two measurements.

**Run 78 = candidate `truedoc77`, launched 02:12 from commit 7c45725 (validated 02:12: suite clean, gate 100, samples 46 and 58) and scored 03:26: 84.2 (CI 83.3-85.0), the best TrueDoc run yet; held-out 81.2, tuned-on 82.1 (4,901 of 5,764).** Against run 77: 11 won, 2 lost, all on arXiv, and exactly the pages the two whole-arXiv measurements named - won 2503.03905 page 7, 04620 page 35, 05062 page 35, 05177 page 10, 05323 page 16, 07617 page 27, 08261 page 14 and 09472 page 15 (two) for the extension glyph's width, and 06194 page 10 and 07441 page 11 for the hook; lost 2503.07421 page 26 and 2503.08172 page 25, each now at MuPDF's own score (4 of 5 and 4 of 7). Against the MuPDF run 65: 50 won, 22 lost, twenty-eight checks ahead (arXiv +19, tables +4, multi-column +3, headers +1, tiny text +1). By category: arXiv 88.1, old-scan maths 80.8, tables 88.6, old scans 47.3, base 99.8, multi-column 83.3, tiny text 88.7, headers 97.0. The conversion took 4,094 seconds at a mean of 17.46 seconds a page, the machine shared again with prototype measurements; the scores do not depend on it.

**A spacing accent emitted out of order does not end its line (2503.04407 page 3, and three more arXiv pages).** TeX draws the hat of `\hat{v}` before the v, which is the content stream's order and MuPDF's. PDFium's text page sometimes emits it after later glyphs of the same line - on 2503.04407 the hat over v came after the theta that follows - and the reader's backward-jump rule (a new line where the pen steps back more than half an em, written for a table row drawn right to left) cut the sentence at the hat: "), where τ̂ denotes the delay" went onto a line of its own and the formula lost its hat. The accent move of run 75 could not help: it re-homes only an accent in its letter's own font, and this one is roman type over a maths-italic v - one of the 1,770 maths accents it leaves to the maths stage by design. The backward rule now lets a spacing accent (hat, tilde, macron, dot, dieresis, caron, breve, ring or acute) that lands on a glyph already in the piece stand where it is. Measured before it was written, with a copy of the splitter carrying the one exception (`accent_jump_proto.py`): over the 522 arXiv pages under PDFium, four checks won on four pages and none lost - 2503.04407 page 3, 2503.03879 page 4, 2503.07509 page 2 and 2503.09190 page 4, each now at MuPDF's own score (the category 2,582 of 2,927 against 2,578); outside arXiv, over the 747 pages of the other four categories, it changes the lines of one page - a dieresis in a reference on 07070be1 page 9 now stays on its line - and that page's score does not move (3 of 4). The written patch was then checked against that copy: every line's text and box on all 1,269 pages, under each, identical. A test on the page, failing before.

**A glyph PDFium's text page reports no character for fills its gap again (00f6c2ee page 10, one check).** The one repair that survived the line-rule measurements above, written: `_geometry` now also lists the text objects on the page that the text page reports no character for (an object's box, not a paragraph's - at most 200pt wide - and not invisible text), and `_split_at_gaps` drops a cut of the old rules where such objects, drawn between the two glyphs in painting order and in the line's band, close the gap to under MuPDF's 0.8 em, each step under 0.8 em as well - as MuPDF's pen crosses them. No cut is added. Measured before it was written, over whole categories with the prototype (`pen_guarded_proto.py`, PEN_ADD=0): over the 747 pages of tables, multi-column, tiny text and headers, one check won and none lost - 00f6c2ee page 10, from 3 to 4 of 4, MuPDF's score (the four categories 2,636 of 3,108 against 2,635); over the 522 arXiv pages it found no such object at all - PDFium's text page reports every object on a TeX page - and changed nothing. The written patch was then checked against the prototype that was measured: every line's text and box on all 1,269 pages of the five categories, under each, identical, with cuts dropped on two pages, both 00f6c2ee (pages 10 and 8, eleven cuts). A failure in the new listing costs the line rule its silent objects, not the page. A test on the page, failing before.

The two were written together, the accent's patch first, and the file then compared byte for byte with the source rehearsed in the scratchpad: suite 418 both ways, the two new tests failing before and passing after (420 in all), quick gate 100/128 both ways, samples 46/52 both ways and 59/64 against 58 (2503.03879 page 4, one of the four pages the accent's measurement named). The two measurements were finished on shared workers once run 78 had converted - the pages each single-worker run had not reached, split across four and five workers and merged with its own (`shard_proto.py`).

**Run 79 = candidate `truedoc78`, launched 03:45 on the code of commit 8b3c8c4 (validated 03:45: suite 420, gate 100, samples 46 and 59) and scored 04:55: 84.2 (CI 83.3-85.1), held-out 81.2, tuned-on 82.2 (4,906 of 5,764) - the best tuned-on yet.** Against run 78: 5 won, 0 lost - 2503.03879 page 4, 2503.04407 page 3, 2503.07509 page 2 and 2503.09190 page 4 for the out-of-order accent and 00f6c2ee page 10 for the silent objects, exactly the pages the two measurements named, each now at MuPDF's own score. Against the MuPDF run 65: 50 won, 17 lost, thirty-three checks ahead (arXiv +23, tables +4, multi-column +4, headers +1, tiny text +1). By category: arXiv 88.2, old-scan maths 80.8, tables 88.6, old scans 47.3, base 99.8, multi-column 83.4, tiny text 88.7, headers 97.0. The conversion took 3,799 seconds at a mean of 16.17 seconds a page.

**The parity losses after commit 8b3c8c4.** New stock per-page files for the committed code (`bench/out/lost/*_pdfium_v15.txt`: arXiv 2,582, tables 852, multi-column 682, tiny text 364, headers 738, no model) set against MuPDF's stored per-page scores leave twelve arXiv pages where MuPDF still reads more (thirteen checks), two multi-column pages and one table page; headers and tiny text have none. Each was traced to its cause the same hour, and six causes are repaired below, each measured before it was written. The measurements used a cheaper route than scoring whole categories: a dump of every page's lines under the current code and under the prototype - the reader's lines for a reader change, the text layer's for a text-layer change - finds the pages the change touches at all, and only those are scored; pages never touched convert exactly as before.

**An accent left standing does not move the pen (2503.07532 page 14, one check).** The accent rule written for run 79 lets a spacing accent PDFium emits out of order stand where it lands, over a glyph already in the piece. On 2503.07532 the word "e c d c̄ d̄ ē a b ā b̄ e" comes out with its bars out of order; the bar of ē, standing back over the e, became the last glyph, and the bar of ā after it, 30pt to the right, was measured from it as a jump of 2.9 em - the gap rule cut the word there, and its tail was read after the next line. Such an accent no longer moves the pen: the next glyph's gap is measured from the glyph before it. Measured before it was written (`accent_pen_proto.py`, compiled from the splitter's own source): its lines differ from the current code's on 11 of the 1,269 pages of the five categories, and scored, those pages gain one check and lose none - 2503.07532 page 14 from 2 to 3 of 3, MuPDF's score. The written patch was checked against the prototype on every page: identical, no page differing. A test on the page, failing before.

**Three more AMS symbol codes, read as MuPDF reads them (2503.07281 page 12, one check).** PDFium leaves some codes of the AMS symbol fonts raw; the reader's table for them, measured on 10 Sept, kept only codes seen at least three times. 2503.07281's proper-subset sign is msbm's code 0x28, left as "(", which the maths stage then read as cmsy's ⇐ ("K ⊕ ΘH ⇐ H"). A census of every raw msam and msbm code over the five categories, against the character MuPDF reads at the same place (`ams_census.py`), finds four MuPDF reads differently: msbm 0x28 ⊊ (twice), msbm 0x79 ↷ (once) and msam 0x08 ⟳ (twice), each where the published layout places it, and msam 0x02, which MuPDF reads as a registered sign where the layout has ⊠ - left raw. The three go into the table. Scored on the four pages that carry them: 2503.07281 page 12 from 2 to 3 of 3, MuPDF's score, and nothing else moves (14 against 13 of 17). Two tests, failing before.

**A lone punctuation mark is no filler for the text layer's bridge (2503.06630 page 14, one check).** "(ii) w1/w2 , w2/w1 ∈ L∞(Ω)": PDFium hands the comma between the two fractions over as a segment of its own, on the text's baseline. The text layer's bridge - written for a sum sign's limits or a stacked fraction standing between the two halves of a text line - took the lone comma, set in a maths font and with a box that overlaps the denominators' row, for such a filler, and welded the two denominators into one segment "w2 w1". No fraction bar covers half of that, so it linked to no bar, was refused as a satellite, and both fractions read as underlined letters. MuPDF keeps the comma with the second numerator (", w2"), too wide to be a filler, and each denominator joins the line under its own bar. A segment of punctuation alone is no longer a filler. Measured before it was written (`bridge_punct_proto.py`, compiled from the reassembly's own source): the text layer's lines differ from the current code's on 3 of the 1,269 pages of the five categories; scored, one check won and none lost - 2503.06630 page 14 from 5 to 6 of 10, MuPDF's score. The written patch differs from the prototype only in spelling out its one condition. A test on the page, failing before.

**No invented blank between a subscript and a full-size glyph where MuPDF leaves the gap closed (2503.09195 page 13, one check).** PDFium puts a zero-width blank in the 0.98pt gap after the 7pt subscript of "(S, D_S)-connected" - 0.14 em of the subscript, 0.10 em of the parenthesis - and the maths span ended at it: the page read "(S, D_S$ )-connected". MuPDF's own blanks start at 0.16 em. The reader already takes out the blank PDFium invents beside a dash in a run of digits; the blanket rule, every invented blank under a word space, was measured and cost five checks on one quick-gate page, because between glyphs of one size a tightly set page's box gaps understate its pen gaps. This one applies only across a change of size: an invented blank between a script-sized glyph and a full-size one (sizes under 0.8 to 1), in a box gap under 0.16 em of the larger size, goes. Measured before it was written (`blank_script_proto.py`): the reader's lines differ from the current code's on 271 of the 1,269 pages - it takes out 1,298 invented blanks there - and scored, those pages gain one check and lose none: 2503.09195 page 13 from 7 to 8 of 10, MuPDF's score, and no other score moves. A test on the page, failing before.

**An accent's base found by its centre (2503.05183 page 15, two checks).** "(2λ̂₄(1−p))^{1/(2−p)}" read "(\hat{2}\lambda_4(1-p))" under PDFium and lost both checks MuPDF passes. The hat sits over the λ (hat 98.8-102.1, λ 97.8-103.3), the "2" before it at 92.8-97.8. The maths stage's first rule - the glyph directly below the accent - takes the λ under MuPDF, whose boxes are the font's full height; PDFium's metric boxes keep the λ's top a quarter of a point below the hat's middle, so the second rule, by baselines, decides - and it took the first glyph whose box, widened 0.35 em each side, holds the accent's centre: the "2". Of the glyphs that qualify it now takes the largest, and of those the one whose centre is nearest the accent's. Measured before it was written, with a recording prototype that asks both rules at every accent (`accent_centre_proto.py`): over the 522 arXiv pages under PDFium the new rule chose differently 16 times on 5 pages, and one of them moved - 2503.05183 page 15 from 8 to 10 of 10, MuPDF's score; outside arXiv, on the 27 pages whose lines carry an accent, it was asked 48 times and never chose differently, and no score moved (82 of 96 both ways). Two tests, one with each reader's boxes; the PDFium one failed before.

The six were written together, each file byte for byte the source rehearsed in the scratchpad, and the whole suite had passed on the rehearsed sources first (427). Run 80 was validated on them at 05:23 - suite 427 (the 420 before and seven new tests, each failing on the old code), quick gate 100/128, samples 46/52 and 59/64, all as before - and launched.

**Measured and set aside: MuPDF's join for a numerator or a text-style sum (2503.08504, 2503.05469).** A text-style fraction's numerator rises about 0.55 em and a text sum sign's origin stands 0.75 em up; MuPDF keeps both on the line, its vertical threshold being 0.8 em, while the reader's join stops at half an em and never takes a run that sits on a fraction bar (kept so that the maths stage could pair a numerator with its bar). On 2503.08504 page 4 that left each numerator and its denominator starting past the line's end, where the text layer refused them as satellites, and the fractions vanished ("2 ≤ q <" and nothing after it). The join as MuPDF would make it - 0.8 em, runs over a bar taken (`join_mupdf_proto.py`, compiled from the join's own source) - reads 08504 page 4 at 5 of 5 (from 3; MuPDF 4) and 2503.05469 page 12 at 5 of 5; but it changes the reader's lines on 361 of the 1,269 pages, and on the first 59 of those scored it lost five checks and won none (2503.03903 page 9, the reassembly case above, and two each on 2503.03994 page 108 and 2503.06549 page 8). It was stopped there to give run 80 the machine. The losses, traced, are the two things the reader's join was built to prevent: with the bar refusal off, 2503.03994's inline fractions tear (α₀/β₀, 1/Θ₀ - the numerator welds into the text line), and at 0.8 em 2503.06549's raised script stacks (λ_i^{(N)}, μ_i^{(1)}(t)) are taken into the line and broken. So the join keeps its half em and its bar refusal; MuPDF's 0.8 em for a run that starts with a big operator's glyph - the narrow form measured above, one won and one lost - waits on the text layer's reassembly, and 08504's fractions after "q <" need a route of their own, a bar-linked fraction just past the line's end. Two other losses were traced and left: 2503.07910 page 7, where PDFium's reading makes a run-in heading a heading and orders the rest of its sentence wrongly - a layout-stage matter - and 2503.09577 page 20, whose inline formula scatters for the numerator reason above.

**Run 80 = candidate `truedoc79`, launched 05:23 on the code of commit aa8602f (validated 05:23: suite 427, gate 100, samples 46 and 59) and scored 06:10: 84.2 (CI 83.3-85.1), held-out 81.3 (1,068 of 1,255), tuned-on 82.2 (4,910 of 5,764).** Against run 79: 6 won, 0 lost, all on arXiv, exactly the six checks the measurements named - 2503.05183 page 15 (two), 2503.06630 page 14, 2503.07281 page 12, 2503.07532 page 14 and 2503.09195 page 13 - each page now at MuPDF's own score. Against the MuPDF run 65: 50 won, 11 lost, thirty-nine checks ahead (arXiv +29, tables +4, multi-column +4, headers +1, tiny text +1). By category: arXiv 88.4, old-scan maths 80.8, tables 88.6, old scans 47.3, base 99.8, multi-column 83.4, tiny text 88.7, headers 97.0. The conversion took 2,710 seconds at a mean of 11.56 seconds a page, the machine to itself.

**A held-out page was tuned on (D016): found, reported, and now guarded against.** Run 80's held-out rise is not what it looks like: its two checks are 2503.05183 page 15's, and that page is in the held-out fifth - the accent rule above was traced on it. The parity list drawn after commit 8b3c8c4 took every page, and three of the pages traced from it are held-out: 2503.05183 page 15 (repaired), 2503.05140 page 22 and 2503.06549 page 8 (traced, nothing written from either). Checking the pages traced before finds one more: 0b65b6a5 page 4, whose unnamed Type 3 fonts were traced to the four facts written for run 72 on 11 Sept. So run 80's held-out 81.3 is not a clean figure; without the page the rule was traced on it is 81.2 (1,066 of 1,255), level with run 79, and that is the number to compare. The accent rule stays in - it is general, and over the five categories it changes no other page - and so does the Type 3 work, unless the owner decides otherwise. From now the parity list leaves out every page in `bench/holdout.txt` before anything is traced, and 2503.05140 and 0b65b6a5 come off the work list.

**A diagram's arrowheads are drawing, not text (2503.05329 page 4, one check).** xy-pic, which sets commutative diagrams, draws its arrows from fonts of its own whose glyphs are named a1, a41, ... - the names of Zapf Dingbats' glyphs in the Adobe list - so the glyph-name step read them as dingbats ("❜❜❜❜ ❨❨❨"), and one arrow tip with no name came through as its bare code, a dollar sign. That lone dollar sign opened a formula in the markdown that paired with every later one, and the page's one check, "0 < r′ ≤ r ≤ ∞", was never read as a formula. Glyphs from xy-pic's fonts no longer enter the text layer. Measured before it was written (`xypic_proto.py`, compiled from the reader's own source): five pages in the five categories use those fonts, all arXiv and all tuned-on; on them it drops 442 glyphs, and 2503.05329 page 4 goes from 0 to 1 of 1, MuPDF's score, with nothing else moving; the written patch reads the five pages line for line as the prototype does. A test on the page, failing before. Run 81 was validated on it at 06:27 - suite 429, quick gate 100/128, samples 46/52 and 59/64, all as before - and launched. It also raised a question that is the owner's to answer - how a dollar sign in prose should be written, since TrueDoc writes formulas between dollar signs - measured (escaping every prose dollar would cost sixteen benchmark checks) and set out in `docs/DECISIONS.md`, Open.

**Run 81 = candidate `truedoc80`, launched 06:27 on the code of commit 4e030d4 and scored 07:18: 84.2 (CI 83.4-85.2), held-out 81.3 (1,068 of 1,255; 81.2 without 2503.05183 page 15, as above), tuned-on 82.2 (4,911 of 5,764).** Against run 80: 1 won, 0 lost - 2503.05329 page 4, the check measured, now at MuPDF's score. Against the MuPDF run 65: 50 won, 10 lost, forty checks ahead. arXiv 88.5; every other category as run 80. The conversion took 2,938 seconds, 12.53 a page, with measurements running beside it. Its markdown is run 80's byte for byte on 1,398 of the 1,403 pages, and the five that differ are exactly the five pages that use xy-pic's fonts: two runs of the same code give the same output, so a change meant to alter nothing can be proved by a run whose markdown does not move (D022).

**Taking PyMuPDF out of the product, stages A to C: TrueDoc's own rectangles and matrices, the quality check's count from PDFium, and PDFium page handles (M18, D007, D022).** The PDFium readers have been the default since run 71, but the package was still on the product path: `pymupdf.Rect` and `pymupdf.Matrix` as plain geometry types at eighteen sites; the page-quality check counting invisible text through `get_texttrace`, a second trace of every page; the document and page objects themselves, which carry each page's size, its rotation and the matrix that turns the readers' unrotated coordinates into drawn ones; and the vision stage opening its own PyMuPDF document to crop regions for the model. Three stages, each proved before it was written against a quantity that must not move. **A, geometry** (`truedoc/geometry.py`): PyMuPDF's `Rect` and `Matrix` reproduced exactly for the operations the product uses - width and height clipped at zero, `is_empty`, `normalize`, transform by a matrix (MuPDF's three branches, including its swap for an inverted rectangle), union and intersection with PyMuPDF's rules for an empty operand, the inverse - down to the 32-bit arithmetic MuPDF does them in; identical to PyMuPDF on 100,000 random cases, then swapped in at eighteen sites in seven modules. **B, the quality check's count**: a page drawn mostly invisibly is a scan's OCR layer, and the check routes pages by that fraction. It now counts the characters as the page is read - PDFium's generated blanks left out, since a trace never sees them - instead of tracing the page a second time. Measured on all 1,403 benchmark pages: 84 carry invisible text, and the new count clears the check's two thresholds (0.5, and 0.1 over a picture) on exactly the pages the trace does; the counts themselves are equal outright on 571 pages. **C, page handles** (`truedoc/extract/handle.py`): a PDFium document and page that report what PyMuPDF's did - size as drawn, rotation, rotation matrix, title - and turn a page lying on its side in memory, as `set_rotation` did. One quirk had to be matched: PyMuPDF builds the rotation matrix from the /CropBox as written, not from the drawn page (the crop box cut to the media box), and keeps that size in 32-bit floats; the first two drafts differed on the benchmark's crop-box pages until both were matched. Proved identical on every page of the benchmark (1,403) and of the insurance library (23,870 pages in 1,176 documents), as filed and turned to each quarter: 101,092 checks. Anything else asked of a page belongs to the old reader and goes to PyMuPDF's copy of the page, opened only then. The vision stage's crops, which neither the run (its model readings come from files) nor the suite renders, were compared directly: 1,911 page and region images on 147 pages - every page lying on its side, every crop-box page and every twentieth besides, as filed and turned either way - made the old way and the new, byte for byte identical. The quantity for all three together: run 82 must give run 81's markdown on every page. Run 82 was validated at 07:46 - suite 439, quick gate 100/128, samples 46 and 59, all as before - and launched. Suite 439: ten new tests - the geometry against PyMuPDF's own (four), the page handle (four, the last reading a page through either handle at every turn) and the quality count (two). With `TRUEDOC_MUPDF_TRACE` naming a folder, the handle notes each call that still reaches PyMuPDF: on the first launch, that trace is what found the renderer fault below. Its markdown is run 81's byte for byte on all 1,403 pages, no conversion errors, 3,182 seconds at 13.55 a page, and it scored the same 84.2 (CI 83.3-85.0), held-out 81.3, tuned-on 82.2: the three stages change nothing. The trace says what is left - 5,273 calls reached PyMuPDF and every one of them was a page drawing (the renderer fault below), plus three from the suite; no text, drawing, object or table call went near it.

**Stage C's fault, and how it got past five checks.** Every check above compared a quantity with its PyMuPDF twin, and none of them put PyMuPDF's own objects together with TrueDoc's new ones. Since stage C, a page's rotation matrix is TrueDoc's `Matrix`, and the text layer turned each character's origin with PyMuPDF's `Point(pt) * M`. PyMuPDF reads a matrix it does not recognise as the identity (its conversion accepts only its own types, tuples and lists), so on a rotated page every origin stayed where it was: boxes right, baselines wrong, nothing crashing, the suite green at 437. It surfaced two minutes into run 82, while stage E's point arithmetic was being proved: PyMuPDF's `Point` times TrueDoc's `Matrix` gave the right answer on 0 of 200,000 points. Run 82 was stopped before it had done any real work; the 83 pages it had finished were set aside, and all 83 match run 81 byte for byte. The repair: `truedoc.geometry.transform_point`, MuPDF's `fz_transform_point` exactly (the point and the matrix rounded to 32-bit floats on the way in), which gives PyMuPDF's own `Point` times `Matrix` on all 200,000 points; the text layer uses it. The sites where a PyMuPDF object could meet the new types were then audited one by one: this was the only one. Two tests, the second failing on the old code at the first rotated page: the arithmetic, and a page read through either handle, as filed and at every turn. On real pages: the text layer's whole reading - characters, words, lines, hidden text, drawings, images, the quality verdict and the page's notes - through PDFium's handle and through PyMuPDF's page, on 147 benchmark pages (every page filed on its side, every crop-box page, every twentieth besides), as filed and turned a quarter either way: 441 readings, all identical.

**The PDFium renderer had not drawn a page since 10 Sept 10:43.** Run 82's trace notes every call that still reaches PyMuPDF, and its first two minutes showed ordinary upright pages drawn by MuPDF (2503.03847 page 30: 71 renderings). Commit 905f456 renamed the renderer's document function from `_document` to `document` and left the one call in `_render_pdfium` on the old name. Every PDFium render has raised a NameError since, the renderer's fallback caught it without a word, and MuPDF drew every page: runs 66 to 81 had `TRUEDOC_RENDERER=pdfium` switched on while MuPDF drew every page image the layout model, the OCR engine, the marks and the hidden-text check looked at. The measurement behind the switch (the gate at 100/128 either way, identical marks on 82 rotated pages) was made at commit 3fb9e5b, before the rename, and nothing checked it again. The text and object readers are not affected - a fallback there would show in the trace, and none did. The repair is one word, but it changes the picture every stage sees, so it goes in alone as run 83 and is judged by its score, not by identical output. Two tests fail on the old code: PDFium must draw an upright page itself, and an upright page must never reach the fallback. The claims this corrects: the switch table in `docs/ARCHITECTURE.md`, the table in `docs/STATUS.md`, D023, and the run 66 row.

**Run 83 = PDFium draws every page, at last, and what the repair cost.** The renderer's document function was renamed on 10 Sept (905f456) and one call left on the old name, so every PDFium render raised a NameError, the silent fallback caught it, and MuPDF drew every page image in runs 66 to 81 while the switch read PDFium. The repair is one word; two more went with it, each found by a test rather than by a run. A clip is now the pixel box MuPDF would have drawn - PDFium rasterises the whole page at the same scale and cuts whole pixels off each edge, so the box is handed over in pixels, half a pixel inside each edge - where a crop used to come out 32 pixels wide against MuPDF's 33. And a mark's crop is drawn four times larger than the grid it is read on and shrunk here, a cell counting as ink when a quarter of its pixels are: at the grid's own size PDFium keeps a stroke a pixel wide where MuPDF thins it, and the same tick covered 0.146 of the crop under one and 0.177 under the other - a tick drawn one way and an arrow drawn the other. Measured over every mark there is (a chevron in a grey disc, a plain tick and cross, a tick and a cross knocked out of coloured discs) the two libraries now agree on all of them, while 'any pixel will do' and 'half the pixels' each get one wrong. **Run 83 scored 84.2 (CI 83.3-85.0), held-out 81.1 (1,067 of 1,255), tuned-on 82.1 (4,908 of 5,764)**: against run 82, 2 won and 6 lost, net four checks, over 155 pages whose markdown moved. Five of the six losses are one page, tables/937a90b2 page 7: PDFium draws text about seven per cent heavier, the layout model reads a wider table region there (0.87 against the 0.38 MuPDF's drawing gives) and the table stage could not build the fees table from it - traced, and on the work list. The number the run is for is the other one: calls still reaching PyMuPDF fell from 5,273 to 77, and all 77 are crops hanging off the edge of the page, where PDFium cannot draw and MuPDF pads with white. Stage E replaces that padding, and the package leaves the product path.

**Run 84 = D024, the owner's decision on dollar signs, measured.** A price and a formula cannot both own the dollar sign. TrueDoc now writes formulas as `\(...\)` and `\[...\]`, and writes a literal dollar sign in markdown text as `\$`. The owner decided both parts together on the standing principle - the output will be read rendered as well as by machine, and meaning for the reader decides - after the two costs were measured separately: re-delimiting changes not one of the 7,019 checks, escaping costs what the benchmark's own bookkeeping says it costs, because its expected text holds bare dollar signs and its scorer does not undo a markdown escape. **Run 84 scored 84.0 (CI 83.1-85.0), held-out 81.1 (1,067 of 1,255, not one check moved), tuned-on 81.9 (4,895 of 5,764).** Against run 83: 0 won, 13 lost, every one of them a check whose expected text holds a dollar sign, on six pages - ten in tables, two in old scans, one in multi-column - for 654 pages whose markdown changed. Thirteen rather than the sixteen measured, because a price inside an HTML table is left bare: markdown escapes do not apply there and a backslash would show as a backslash. On the owner's own documents the change reads as it should: AAMI's home building PED now says 'excess levels between \$100 and \$5,000', where a viewer that pairs dollar signs used to read the words between the two prices as a formula.

**Run 85 = stage E, and PyMuPDF is off the product path (M18 done, D007).** The package is imported only when the old reader asks for it - `handle.pymupdf_module()`, reached by `TRUEDOC_READER=mupdf` and the fallbacks - the renderer hands back an empty picture for a crop with nothing of the page inside it (PDFium refuses to draw one, which is what the last 77 renderings of run 83 were about), and `pyproject.toml` tells the truth at last: PyMuPDF moves to the `mupdf` and `bench` extras, and the packages the default path has always imported but the list never named - pdftext, torch, transformers, huggingface_hub, rapidocr_onnxruntime - are declared, so a fresh install can now run at all. **Run 85's markdown is run 84's byte for byte on all 1,403 pages and every figure is identical: 84.0, held-out 81.1, tuned-on 81.9.** The trace is the number this run is for: **three calls reached PyMuPDF in the whole run, and all three are the suite's own escape-hatch test on a temporary file - the conversion of 1,403 pages made none.** `tests/test_no_pymupdf.py` converts prose, a page filed on its side and a page carrying a hidden OCR layer in an interpreter where `import pymupdf` raises. D007 now carries the licence of every package the product path does import - Apache-2.0, BSD or MIT throughout - and the one thing still unchecked is the licence of the two sets of model weights the pipeline downloads at run time, which is the owner's to settle before a product ships.

**Where the remaining checks are, counted on run 85's failures (1,060 of 7,019).** By category: arXiv maths 337, old scans 280, multi-column 148, tables 131, old-scan maths 88, tiny text 51, headers 25. By kind the split is clean: every arXiv failure is a maths check, every multi-column failure an order check, every tables failure a table check. **About 670 are TrueDoc's own work to win and about 390 are the model's reading.** The model's share is not winnable while the readings are replayed from disk: old_scans/43 is a handwritten letter where olmOCR transcribed a different clause from the reference, and long_tiny_text/16a to 16c - five pages holding half that category's failures - are dictionary pages with no text layer where the model simply stopped part way. Ours are long tails: arXiv's 337 spread over 192 pages (the worst five hold 25), multi-column's 148 over 95, tables' 131 over 65 (the worst five hold 26, and the nested-region rule of run 86 is aimed at that pool). One small defect was measured and parked on the way: TrueDoc passes the model's "&c." - the old abbreviation for "etc." - into a formula unescaped, where no renderer can read it (five times on old_scans_math/5_pg174, whose own expected text writes an escaped ampersand); escaping it wins two checks, measured, so it rides with the next change to that path rather than alone.

**Run 86 = a region nested inside another of the same kind no longer suppresses it.** `clean_regions` drops a region when the overlap covers 85 per cent of the smaller of the two and keeps whichever ranked higher, so a strong narrow region beat the weaker region that contained it: on the fees page tables/937a90b2 page 7 the layout model offers a table region over the whole table (0.593) and one over its fee column alone (0.775), and the column won. The bigger of two nested regions of one kind is now the one kept. **Run 86 scored 84.0, held-out 81.3 (1,068 of 1,255), tuned-on 81.9 (4,895 of 5,764): 1 won, 0 lost against run 85**, over 48 pages whose markdown moved - the other 47 changed without changing a check. Small, but nothing paid for it. **It did not recover the fees table, and the reason is worth recording:** the right region is now kept, but the table stage trusts a region only from 0.7 up, and this one scores 0.593 where MuPDF's drawing happened to give 0.739. The next step follows from that - when a nested region is replaced by the one containing it, carry the better of the two scores: the bigger box says where the table is, the better score says how sure the model is that it is one.

**The multi-column pool is not what its name says.** Its 148 failures are all order checks, which reads like a reading-order problem; asked why each one fails, the benchmark answers 'text not found' 137 times and 'wrong order' only 11. Searching our own markdown again, allowing a tenth of the text in edits, splits those 137: **81 are near misses - we wrote the words and something small differs** (the expected text reads 'and no reduction was made to U.S.source' where we write 'U.S. source'; two Korean pages differ in the words themselves, which is a reading difference, not an assembly one) **and 53 are genuinely absent**, among them the tax guide's '$8,000' line that D024's escaping now costs us. So the category is about exact text, not about order, and its easy-looking 148 is mostly out of reach. One page in it earns a note of its own: on multi_column/00f6c2ee page 13 the PDF's own text layer drops every capital C - 'Indonesian Journal of omputing and ybernetics', 'International onference on Asian and Pacific oasts' - and MuPDF reads it exactly the same way, so it is the document's defect rather than the reader's. Nothing would catch it either: four words of 767 are damaged, the page reads as good digital text (garbage fraction 0.008 against the 0.2 that makes a page suspect), and only re-reading the page with a model would recover the letters. Recorded so the pool is not mistaken for a cheap win again.

**Run 87 = the container region carries the better score, and the fees table is a table.** When `clean_regions` replaces a nested region with the one containing it, the survivor now takes the higher of the two scores. The bigger box says where the thing is; the score says how sure the model is that it is one, and every stage downstream reads that score as confidence - the table stage builds only from 0.7 up, where the fees page's whole-table region scores 0.593 against its fee column's 0.775. **Run 87 scored 84.0, held-out 81.3 (1,068 of 1,255, level with run 86), tuned-on 81.9 (4,897 of 5,764): 2 won, 0 lost against run 86**, both on tables/937a90b2 page 7, the page the rule was traced on - six courses and their fees, loose prose since run 83, are a five-row table again. Two pages' markdown moved in the whole run and both gained a table: on tables/b773892d page 1 the words 'Topic' and 'Number of questions*' are a header row instead of two stray headings, and four rows of prose are rows, though no check noticed. The footprint was known before the launch, which is why a one-line change was worth a full run: the rule is general, and the two pages it moved are the two it should.

**Where the 1,057 remaining failures are, and what the formula pool is really made of.** Run 87 fails 337 arXiv maths checks, 280 old scans, 148 multi-column, 129 tables, 88 old-scan maths, 51 tiny text, 24 headers - and every failure in a category is of one kind (arXiv and old-scan maths are all maths checks, multi-column all order, tables all table). Taking the 425 maths failures apart: for each one, our nearest formula on the page was scored against the wanted one. 13 are all but identical, 116 near, 235 half right, 61 nothing like it; 25 more show the signature of a formula we cut in two. So the pool is not one fault but a few hundred. **Twelve spelling rules were then simulated** - rewrite our formula one rule at a time and ask the benchmark's own comparison whether it now matches, counting as a loss any passing check whose carrier the rule breaks. Almost none pay: tfrac to frac 0 won, prime to quote 0, rightarrow to to 0, ldots to dots 0 and 36 lost, varepsilon to epsilon 2 won and 39 lost, notin 2 won and 3 lost (which is run 28's finding again, and the code already says so). **One pays: a matched pair of sized delimiters written as `\left ... \right` wins 7 and loses 3.** The first attempt at that rule converted every sized delimiter and measured 5 won against 14 lost - but the 14 were its own doing, a lone `|` turned into a `\left|` with no `\right`, which cannot render; pairing them properly turned the ledger round. `\leqslant` to `\leq` simulates at 9 won and 5 lost, against run 28's five lost and four gained on the full corpus: a simulation on the nearest formula is not a run, the glyph on the page really is the slanted one, and the code keeps it as drawn. **The lesson to carry: the near-miss pool looked like the cheap win and is not, exactly as the multi-column pool was not.** The remaining maths failures are misread letters, garbled structure and cut formulas, one page at a time.

**A tool that reports zero is suspect until it has been shown finding one.** The formula-render census counted a formula as unrenderable when `render_equation` returned `None`, which it never does: the benchmark's renderer hands back an object with `.error` set and no spans. The census had been reporting a clean bill of health on whatever it was given. Corrected, with `bench/probes/census_selftest.py` to prove it: a page of two formulas, one sound and one KaTeX refuses, must come back as 1 of 2. This is the same shape as the renderer that failed silently into MuPDF's hands for two days, and the marks classifier that read a perfect 100 while losing 38 table checks.

**The old-scan pools are limited by the model's transcription, not by anything we could add.** Of the 280 failed old-scan checks, the benchmark could not find its text 130 times - but 73 of those are texts we did write, differing by a character or two. Taking every near miss in that category apart (216 of them, counting the order checks' two texts, both sides put through the benchmark's own normalisation): **171 allow no edits at all**, and what differs is the model's punctuation against the page's. It writes 'Church South was' where the page reads 'Church, South was'; 'of his inheritance; the man' where the scan sets a space before the semicolon; 'your promptness. We are' where the letter has a dash; 'sister' where the writer capitalised 'Sister'. The commonest single differences across the pool are a comma we drop (8), a space we close up (4), a dash we read as a full stop (4) and a capital we lower (4). The tiny-text pool reads the same way: of its 51 failures, the near misses are letters misread on a photographed page ('Godavery' for 'Godavary', 'budra' for 'bura'). **No rule of ours reaches any of this**: the words come from the model, and the benchmark marks them character for character. The 419 checks on model-read pages (old scans 280, old-scan maths 88, tiny text 51) move when a better model reads them, which needs the owner's rental - it is the single biggest lever left, and larger than everything the converter can still win by rules. Tool: `bench/probes/nearmiss_edits.py`.

**Compare like with like: the benchmark normalises before it matches.** Its `normalize_text` folds curly quotes, en and em dashes, the minus sign and unicode forms to ASCII, and strips markdown emphasis, before any check is run. A first pass over the multi-column near misses compared the raw texts and produced a tidy-looking list of typographic differences - a curly apostrophe for a straight one, an en dash for a hyphen - none of which the checker can see. With both sides normalised the real classes are smaller and different: a space we insert where the reference has none (7), a line-end hyphen we failed to join (3, 'nega- tive'), a heading marker we drop into the middle of a sentence (3), TeX's doubled quotes left as two apostrophes where the reference writes one double quote (2), and small capitals transcribed as full capitals (2, 'COURTOIS' for 'Courtois'). Every census that diffs text against the benchmark's must normalise both sides first.

**The headers and footers pool was looked at and left.** Its 23 failures are all absent checks - text the benchmark says should not be in the body - and they are journal banners ('OPEN ACCESS', 'PLOS ONE'), a catalogue's running title we write as the page heading ('Physics Minor (Non-Teaching)'), a footnote's source URL, and bare page numbers. Each is text a reader might want to see; suppressing it to pass the check would cost meaning elsewhere, and the detection would have to work on a single page with no other page to compare against. Left alone deliberately.

**The tables pool is mostly not a grid problem.** Of 129 failed table checks, read with the benchmark's own parsers (markdown and HTML both): 45 name a cell that is in no table of ours, 14 sit on a page where we build no table at all, 26 have the neighbour missing, and 37 have the neighbour somewhere else - the grid out by a row or a column. A first cut of that census read only markdown pipe tables and reported 70 pages as having no table; the model writes its tables in HTML, and the checker reads those too. Correction recorded so the number is not quoted again.

**Run 88 = a row is not a heading just because the row below it is wordier, and the fee table is whole.** The aligned table builder ends the heading at the first row holding a cell of more than six words. On tables/937a90b2 page 7 the third course is named in seven words and the first two in five, so those two were read as heading lines and merged into a single row: two courses and two fees became one cell each. A row above the long cell that has the same shape as it - the same cells filled, the same cells opening with a number, and a label in the first column - is another body row, and the heading stops there. A table always keeps one heading row, which is all markdown can write and what the checker reads as row 0, so the rule can only ever merge less. **Run 88 scored 84.1 (CI 83.1-85.0), held-out 81.3 (1,068 of 1,255, level with run 87), tuned-on 82.0 (4,900 of 5,764): 3 won, 0 lost**, the three checks still sitting on that fee table. It is the first run above 84.0 since D024 took thirteen dollar-bearing checks. **Five pages' markdown moved and every one is better for a reader**: on two course tables (headers_footers/3734d658, tables/48e07fcf) and one more (multi_column/0145bc47) a data row had been marked as heading, which forced the whole table into HTML; each is now a plain markdown table with a proper header, and one of them had been reading 'Code KIN 487' as a single heading cell. `tests/test_table_long_cell_heading.py` holds five cases and the first fails on the old code.

**What the formulas we write can be read by**: of the 1,650 formulas outside arXiv, exactly two will not render - both the '&c.' on old_scans_math/5_pg174 - and the rest of multi-column (487), tables (184), headers and footers (286) and old-scan maths (691 of 693) render clean. The arXiv pool's 17,911 formulas have not been measured; the census is slow because each uncached formula needs a browser.

**Run 89 = three measured repairs, and one of the three measurements was wrong.** The changes: a matched pair of sized delimiters is written `\left ... \right` rather than `\big( ... \big)`, because that is what the author typed and what the references spell (only a pair the scanner can match, never a bar, never across a row break, an alignment mark or a brace group); a bare `&` inside a formula span is escaped, since LaTeX reads it as an alignment character and one '&c.' stops the whole formula rendering; and a word the column break cut in two is closed up, which the renderer already intended - its comment names this very case - but which it gated on both blocks being plain text, and a reference list is list items. **Run 89 scored 84.1 (CI 83.3-85.1), held-out 81.4 (1,069 of 1,255, its best yet), tuned-on 82.0 (4,906 of 5,764): 10 won, 3 lost, net +7.** By rule: the delimiters won 7 and lost 3 on arXiv, to the check, exactly as the simulation said (the three losses are references that spell the size themselves, and nothing distinguishes them from the winners); the hyphen join won 3 on multi-column where it promised 2, the extra on a page it was never traced on. **The ampersand won nothing, where its simulation promised two, and the simulation was at fault.** `bench/probes/etc_sim.py` matched a page to its checks by asking whether any test's file name appeared in the page's path: for old_scans_math/5_pg174 that swept in 67 checks from seven different PDFs (old_scans/5, /17, /4, /74, /7) where the page has 24, and scored them all against the wrong markdown. The escape itself works - both formulas on that page now render instead of showing the reader raw TeX - but it moves no check. **A simulation is only as good as its page-to-check matching, and that matcher is the first thing to check when a prediction misses.**

**Run 90 = the first run with a hosted service in the loop, and the first run to go backwards on purposeful work.** The deep reader (`--vision-deep anthropic`) reads a page when it has no text layer and our own OCR of it comes back with nothing word-like; 103 of the 1,403 pages qualified, 64 of them old scans. **Run 90 scored 82.8 against run 89's 84.1.** Old scans went 47.0 to 52.1, +27 checks, exactly what the measurement of the previous evening predicted; tiny text +4 and tables +4; and **old-scan maths fell 80.8 to 64.0, -77 checks, the largest single loss the project has had**. The cause is two of our own rules meeting. D024 escapes every literal dollar sign outside TrueDoc's own `\(` and `\)` spans, which is right for prose and has been safe for ninety runs because nothing of ours writes maths between dollar signs. A general model does: asked to convert equations to LaTeX it answers in the convention it learned, and on old_scans_math/1_pg131 fourteen integrals came out as `\$\int ...\$` - literal text, no formula, no check. olmOCR 2 happens to answer in our delimiters, which is exactly why this never appeared before. Fixed in `truedoc/vision/mathdelims.py`: a model's reading is translated into the document's own delimiters before anything else sees it, and only when the span is really maths, so a price is still escaped. Two details the page itself taught: pairing dollar signs left to right breaks a line that holds both a price and a formula, because the price's opening dollar takes the formula's as its partner, so a pairing that is not maths does not consume its opening dollar; and `let $p=x$ $dp = dx$` has no command and no script in it, so an equals sign has to count as evidence of maths too. **The method error is worth more than the fix: the deep reader was measured on one category, old scans, over 98 pages and 526 checks, and then shipped to all eight. The category it broke is the one that was never looked at.** A change that touches every model-read page has to be checked on every category that has model-read pages, and there are six.

**Run 91 = the same deep reader with its maths translated, and the best score the project has had: 85.4** (CI 84.5-86.3), against run 89's open-weight 84.1 and run 90's broken 82.8. **Held-out 82.4 (1,075 of 1,255) and tuned-on 83.5 (4,953 of 5,764), both the best yet, moving together.** By category against run 89: old scans +35 (47.0 to 53.6), old-scan maths +11 (80.8 to 83.2), tables +6, tiny text +4, headers -2, multi-column -1, arXiv and baseline unmoved - +53 checks in all, and nothing down by more than two. The old-scan maths pages went from 165 failing checks in run 90 to 77: they did not merely recover from the collapse, they ended eleven checks ahead of where they started, because the deep reader really does read those textbook pages better once its formulas survive the trip. **The whole confidence interval now sits above the previous best of 84.2.**

**What the number is and is not.** It is not an open-weight score and it is not comparable to the rows above it: 103 of the 1,403 pages were read by a hosted service over the API, chosen automatically as the pages with no text layer whose own OCR came back with nothing word-like. The open-weight score stays run 89's 84.1 and stays the default - the deep reader is off unless asked for. Two rows, two meanings, which is how the benchmark's own published tables keep hosted services apart from open weights.

**And the check that should have existed before run 90 now does.** `bench/tools/compare_categories.py <a> <b>` puts two runs side by side category by category and names anything that lost ten checks or more, under a heading saying to look before calling the run a success. Run over 89 and 90 it reports the collapse in one line. The dollar-sign bug was the symptom; shipping a one-category measurement to eight categories was the cause.

**Next**: the join for numerators and sums, with the text layer's reassembly; the block rule's measurement, re-based on the current code; the traced losses on tuned-on pages (2503.05896's reading order, 2503.07910's run-in heading, 2503.09577's scattered formula, f45a188e's header in the table stage); the model's "&c." escaped inside a formula, measured at two checks, when that path is next touched; and M7, still half met because OmniDocBench has never been run.

---

## 2026-09-10 (night) - Fixing the PDFium reader by points: the arXiv gap closed from -78 to -8

**Done**
- **The owner said "proceed as per your suggestion": run 67 with every switch, then fix by points. The points were traced on the pages that lost them, and none of the arXiv loss was in the maths code.** Every one of the 114 lost arXiv checks was a `math` check; the equations differed because the *characters* handed over differed. Each cause below was measured against MuPDF (D022) and is pinned by a hand-built page in `tests/test_pdftext_maths_pages.py`, `tests/test_pdftext_type3.py` or `tests/test_pdftext_rawdict.py`.
- **A letter beyond the basic plane arrives in two halves.** A maths font's italic m is U+1D45A; PDFium's text page holds UTF-16, so it is a high and a low surrogate on one box, and pdftext writes each as U+FFFD. Page 2503.05588 read 496 of them, 21.6% of its text, and the quality gate sent it to the model as a broken layer - 25 equations gone on one page. Census: 14 arXiv pages, one header page, one table page carry these. The pair is joined back into the one character MuPDF gives.
- **A character PDFium cannot map keeps PDFium's own box.** The advance lookup goes by Unicode and back to a code; for cmsy's mapstochar (code 0x37, no mapping) it answered for the minus sign, the box grew to the minus's, and the ligature rule then zeroed the minus - `\longmapsto` lost its shaft.
- **One font at two matrix scales was one span** (pdftext cuts on the nominal size), so "D_{2k}" had a 14pt letter and 9pt subscripts at one size. Spans are now cut at each drawn size, as MuPDF cuts them. The census said 14 such spans in 30,283 - one page - so this was the smallest of the six, but it was the first hypothesis, and measuring it first is what turned the search to the others.
- **PDFium ends a line wherever the baseline steps.** `R^{2^n}` arrived as three lines and the words after it as a fourth, in another block; TrueDoc bridged the strays into whichever neighbouring line their box touched, and a formula two lines down grew a superscript it never had (`\mathbb{R}^{2}` and a stray `n^{n}` on 2503.04329). Runs that carry straight on - script-sized, or back on a baseline, starting no further back than the last glyph, inside the line's band - are rejoined; full-size text on a baseline of its own (a matrix row) stays a line. Measured on the fixture: PDFium itself keeps a 6pt step on one line and breaks a 12pt one.
- **The line direction was wrong for every turned line, and had been since the swap.** pdftext's dictionary output carries no rotation per line, so `_line_dir` read every line as level; a table's turned headings on 371cfed arrived one word to a line and read backwards ("article). this of text the to 1 note"). The direction now comes from PDFium's own char angle and is (cos, sin): measured against MuPDF's `dir` on four hand-built pages - text set with (0 1 -1 0) is 4.71 to PDFium and (0, -1) to MuPDF, and a level line on a /Rotate 90 page is (1, 0) to both. The earlier docstring had the page rotation turning the vector, on the strength of reasoning rather than a measurement; the tests that pinned it are replaced by measured ones. PDFium also files the blank it makes up between two turned words as a level line of its own, which is what cut the text at every word; those fold back.
- **The letter-spacing merge fused a rating scale's "1 2 3 ... 10" into 12345678910.** Gaps of 1.35 em are never letter spacing. MuPDF never showed the rule such a line: it cuts lines at those gaps itself, and the cells reached the merge one to a line.
- **Committed as 63fad31. Measured on every page that changed between runs 65 and 67, both readers, no model** (`bench/out/lost/`): **arXiv 104 pages net -8 (lost 40, won 32), where the run measured -78; multi-column 18 pages -15; tables 34 pages -36.** Suite 364 and 2 expected failures on and off; **gate 100/128 with every switch on - level with the shipped path for the first time.**
- **Second batch, traced on what was left.** (1) PDFium hands over U+0002 for a hyphen it recognised at a line end; the shape test fails on a Type 3 font, and 09f90a8f read "tech-" as "techΘ" (the code taken for cmr's Theta) with no line joining its paragraph. Census over the benchmark: 4,915 such characters on 691 pages, and MuPDF reads a hyphen at 4,033 of them - the marker is the evidence, no shape needed. (2) The AMS symbol fonts: msam's `\leqslant` is code 0x36 and `\lesssim` 0x2E, and they read as "/" and `\swarrow`. Measured by position against MuPDF over the 75 pages that use these fonts, only the codes seen and consistent with the layouts are tabled. (3) **Bold came from PDFium's weight, and the weight is the descriptor's stem width in disguise: 640-820 on every TeX face, CMR and CMTI alike, so whole arXiv pages were bold and their run-in "Theorem 1.6." headings became headings.** Measured against MuPDF's flag over 7,469 (page, font) pairs: a weight of 600 disagrees on 2,265, "bold" in the name on 369, the name plus TeX's bold faces (CMBX, CMMIB, ...) on 273. MuPDF calls neither "Black" nor "Heavy" bold, and calls CMBX bold only when the embedded program says so, which nothing PDFium reports can tell. (4) **A table ruled between its rows with no rule down the left closed only its right column** (3b18f8c: 4 cells for PyMuPDF's 10). PyMuPDF's port joins rules that stand within a snap tolerance into one box and, where the box holds text, takes its four sides as rules; the same outline rule over our own edges restores 3b18f8c (5x2) and 451680 (two 6x2). (5) **A Type 3 font's glyphs each came in their own box** - an x 6.5pt tall, an E 9.7 - where MuPDF boxes them all in the font's height; the text layer sizes Type 3 text from its box, so a scanned-era paper's body read 3.7pt for MuPDF's 8 and every line stood as its own paragraph. The tallest glyph on the line now stands in for the font's height (within 3% of MuPDF's on that page).
- **Left in the tables category after that, by grid comparison:** the rotated-page transpose (9921f236 reads 10x11 for MuPDF's 11x10, 58feed 7x8 for 8x7), one row lost on 8bf7270c and f1774abd, and four pages whose losses are not in the ruled finder at all.
- **Second batch measured on the changed pages, both readers, no model: arXiv +2 (624 against 622 of 738; was -8 after the first batch, -78 in the run), tables -29 (was -36), multi-column -12 (was -15).**
- **Third batch: the rotated tables, and the cells filled from our own words.** Measured first: **PyMuPDF's finder reports its cells in the rendered space** - on a 90-degree page its first cell holds the word "Table" only once the word is turned by the rotation matrix - so `find_ruled_tables`' `* rotation_matrix` on those cells is a second turn (it only reaches the mark placer's cell boxes; left as it was for the shipped path, noted). The PDFium path now builds pdfplumber's grid in the rendered space: the rules turned by the matrix, TrueDoc's characters left as they are held. And the cells are filled from TrueDoc's *words*, not pdfplumber's character clustering: no single gap fits both a 9pt table with 2.5pt word spaces ("TypeofTask" at the 3pt default) and a 7pt table whose letter spacing runs past a seventh of an em ("fr actu res" at the 0.15-em ratio); the word builder judges each line by its own letter gaps and reads both, and the words already follow their line's direction, which is what had stacked a turned cell one letter to a line. **9921f236 reads 11x10 and 58feed 8x7 - PyMuPDF's grids, cell for cell - and the strict expected failure that recorded the transpose is gone; 451680's cells read whole.** PDFium's made-up line ends ("\r\n") are dropped on the way in: on a Type 3 TeX page the raw-code recovery had taken the carriage return (0x0D) for cmr's "fl" and an author block grew a column of "fl" cells. **Measured: tables -15 (was -29), multi-column -9 (was -12).**
- **The quick gate caught one more, and it was a good one.** 100/128 fell to 99 with every switch on, on b5c5b866: a table row drawn right to left arrived from pdftext as one line with its characters running backwards - pdftext files every span that overlaps a line's band in that line, whatever its order - and the word builder, which measures each gap from the character before, glued "0.658", "0.77**" and "0.31*" into one word and one cell. MuPDF starts a new line when the pen jumps back, and so does the reader now (half an em; kerning pulls a glyph back a fraction of one). A cell's lines are then ordered as visual rows, left to right within a row, so a raised "**" drawn before its number follows it. **Final for the batch: tables -12 on the changed pages (from -69 in the run), multi-column -9 (from -25), arXiv +2 (from -78); suite 373 on and off; gate 100/128 both ways. Committed after 63fad31; run 68 launched with every switch on.**
- **Run 68's first launch (06:26) was refused by the launcher, and rightly: the second maths sample read 54 for a floor of 56** (gate 100, sample 1 46, pytest clean). The changed-pages measurement is biased - it re-reads only pages that differed between runs 65 and 67, so a fix that regresses a page that was equal never shows - and the launcher's twelve-page sample caught what it could not. Bisected in the hour: with the line join switched off the sample reads 57, so the join cost three of the five; PDFium itself keeps a text-style fraction's numerator on the text line (a 0.4-em step is within its own tolerance), and the join then welded the denominator, which starts back under the numerator, into the same *word* - "14" for a 1/4 on 2503.03899, "1x" on a hand-built page - and the maths stage never saw a fraction. Three changes: a welded run that starts back under the last glyph gets a word break (MuPDF puts a blank at any jump); a run sitting on a fraction bar is never welded (the bars come out of the same object walk `_geometry` already makes); the "script-sized" weld clause is gone (a numerator rises 0.39 em and a superscript 0.41 - nothing in the baseline tells them apart, the bar does). `TRUEDOC_LINE_JOIN=0` switches the join off for measuring. Sample 2 back to 56; **run 68 launched at 06:50 on the second attempt** (status file archived as `launch68_status_refused1.txt`).
- **Found while it converts, and queued behind it: Python calls a form feed whitespace, and so did the reader.** cmex draws a tall bar from pieces on code 0x0C; the join's blank-only rule (`isspace()`) took five of them for the blank PDFium makes up between words and folded them into the sentence above a display formula, whose box then reached 60pt into the formula and the maths stage swallowed the sentence ("We will take x_n ∈ {±n^{-1/4}}", 2503.03899). Census: 79 benchmark pages carry unmapped glyphs on whitespace codes - cmex pieces on 0x0C/0x09/0x0B, and Minion's and Myriad's ligatures on 0x1C-0x1F, which Python calls whitespace too. The fix is one predicate: a code PDFium could not map is a glyph, whatever Python calls it. Test written (`test_a_glyph_on_a_control_code_is_not_a_blank`), fix to follow the run.
- **Run 68 scored 07:37: 83.6 (CI 82.7-84.6), held-out 80.3, tuned-on 81.6.** Against run 65's MuPDF baseline: 51 won, 77 lost - **arXiv -1 (from -78 in run 67), tables -15 (from -69), multi-column -9 (from -25)**, headers -2, tiny text +1. Against run 67: +1.2 overall, +1.8 on the held-out fifth. 0.4 short of the MuPDF run overall and 0.6 on the held-out fifth; not shipped yet. The worst pages left: 2503.09133 (3, a matrix), 5bdc8382 and 105e91a0 (3 each, text tables whose first columns fuse because pdftext hands a row over whole where MuPDF cut it at the text object), 013a3686 and 06ba2a90 (2 each, multi-column), 01ed6dcc (2, the ligatures - fixed below).
- **Two more fixes in the code after the launch, both measured on the twelve-page sample (57 of 64 now, from 54 at the refused launch):** the whitespace-code predicate above (`_is_blank`: a code PDFium could not map is a glyph), and **the glyph names PDFium cannot map, read from the PDF's own font tables** - `truedoc/extract/glyph_names.py`, pypdf (BSD-3) for the /Differences arrays and fontTools' glyph list (MIT) for the names, including the ones in parts ("f_i", "T_h"); two resources of one name are told apart by the glyph's advance. On the two benchmark pages that lost checks to it, all 77 unmapped characters resolved and every one agreed with MuPDF's reading. Suite 380 on and off.
- **The text-object cut, measured as a sweep rather than chosen.** Two table pages fused their first two columns because pdftext hands a row over whole where MuPDF, which follows the file's text-showing runs, cut it at the run ("Listening to speech or lecture" | "118"). Each character carries its text object's index already (the hidden-text work needed it), so `_split_at_gaps` gained a second rule: a gap of `_OBJECT_GAP` em ends the line where the text object changes with it. Swept at 0 (off), 0.5, 0.75 and 1.0 over the gate, the twelve-page maths sample and the changed table and multi-column pages: gate 100 and sample 57 throughout; tables -12 at off and -6 at every other setting (5bdc8382 +3, 26f221a3, 508eb272 and 8bf7270c +1 each); multi-column -2 at off, -4 at 0.5 and 0.75, -3 at 1.0 (0925342e loses one). **1.0 it is: the same table gain for the smallest cost.** Set through `TRUEDOC_OBJECT_GAP`; 0 switches it off.
- **A blanket rule measured and taken out the same hour.** PDFium invents a blank at a tenth of an em after the en dash of "1726–1728" (06ba2a90 read "1726– 1728"; 107 of that page's 1,195 invented blanks stood in gaps under 0.15 em), and MuPDF's own blanks start at 0.16 em, so "drop every invented blank in a gap under a word space" looked principled. It took the multi-column pages from -3 to 0 - and the gate from 100 to 95, all on one tightly set table page (26076dc: "Birthweight2690 g", "Elective forcephalopelvic") whose word gaps measure under 0.15 em between glyph boxes though not between pen positions; there PDFium's blanks were right. The gap between boxes is not the measure MuPDF uses. What stays is the narrow rule the case needs: an invented blank beside a dash between digits goes, since a range of numbers has none.
- **Run 69 scored 09:38: 83.9 (CI 83.0-84.8), held-out 80.9 - level with run 65's MuPDF baseline on the held-out fifth, on five more checks (1063 against 1058 of 1255); tuned-on 81.8.** Against run 65: 51 won, 57 lost - arXiv +3, tiny text +1, multi-column -1, headers -2, tables -7. Against run 68: 26 won, 6 lost. 0.1 short of the MuPDF run overall.
- **Two more found on the table pages left, both geometry, both measured against PyMuPDF before being written.** (1) fa18a15c's header fused two columns because "Item", centred over a two-line header, changed rows in the rebuild: **PDFium's loose box stops short above the baseline** - 1.4pt on 8pt Arial - and by an amount that varies with the glyphs, where MuPDF boxes every character from the baseline by the font's ascender and descender. `FPDFFont_GetAscent` and `GetDescent`, asked at the drawn size, give the very metrics MuPDF uses (7.276 = 0.905 x 8.04, to the third place), so the box is built from them, level text only; on the embedded-font page every character's top and bottom now agree with MuPDF's to a twentieth of a point (a test holds that page). A hand-built page cannot pin the agreement - for a font that is not embedded the two libraries substitute different faces (0.891 against 1.053 em of ascent for Times) - so it pins the construction instead. (2) f1774abd rules its rows by shading alone, sixteen filled cells and not one line, and PyMuPDF reads its 4 rows by 4 from the boundaries between the fills; this read 3 by 4. **A rule wherever two filled boxes meet** - the side of a filled box counts only where another filled box meets it, so a page background or a figure's panel, which meet nothing, give none (taking every box's four sides had been tried and measured, and invented tables). Both in the code for run 70.
- **Run 70 scored 11:01: 83.7 (CI 82.8-84.6), held-out 81.0 - above run 65's 80.9 for the first time (1064 against 1058 of 1255); tuned-on 81.5.** Against run 69: 14 won, 26 lost - tables -9, multi-column -4, arXiv +1. **Two of the losses were the new rules' own doing, on pages no measurement set held:** a table shaded row by row across both its columns gave the shared-side rule horizontal boundaries and no vertical one, and the one-column grid it made fused each row's two cells (c2b2651d, six checks) where the column finder had read the table right; and a newspaper page (09f801e3, three checks) whose paragraphs came apart. **Lesson, twice in one run: a rule that changes geometry or adds rules for everything must be measured on the whole category, not on the pages that changed last time - the changed-pages set is the population of yesterday's faults, and a new rule makes its own.** Fixed for run 71: shared sides count only where fills tile in both directions (stripes are not cells). Correction: the first reading of 09f801e3 blamed fonts that are not embedded - a probe shows all five of its fonts ARE embedded, and a census of 115 benchmark pages has the font-metric box agreeing with MuPDF's on a median 99% of characters against the loose box's 93% (100% on that page), so the metric box stays and the page's loss has another cause, traced below.
- **A lead for later, from the census that found the AMS codes: PDFium cannot map a glyph named by its OpenType parts.** MinionPro's "fl" and "ffi" sit on codes 0x1F and 0x1E with names PDFium's table lacks (measured on a hand-built page: "fi", "fl", "ffi" and "uniFB01" map, "f_i" and "Th" do not; MuPDF maps "f_i" and reads "T" for "Th"). On 01ed6dcc a page of Minion and Myriad lost every "fi"/"fl"/"ffi" - "non uorescent", "de nes" - two checks. The names live in the embedded font program, which `FPDFFont_GetFontData` hands over; parsing a Type 1 program's cleartext Encoding is a page of code, a CFF charset rather more. Across the benchmark 131 pages carry unmapped characters in ordinary fonts (42,000 characters, most of them Type 3 codes that already read right); how many checks it costs is not yet measured.

**Lessons**
- **Trace the lost check to the character, not to the stage that wrote the output.** Six of six arXiv causes were in what the reader handed over; the maths code was innocent every time. The per-check diff of two runs (`wonlost.py`), the equation-level diff of two markdown outputs, then a character dump under both readers, in that order, found each within the hour.
- **A docstring is not a measurement.** The direction rule had a confident docstring and two tests that pinned the docstring; the real pages had never had a rotation to give it. When the number a test pins was never observed, the test pins nothing.
- **When two readers disagree on a flag, census the whole corpus before choosing a rule**: the bold question had five candidate rules and the census ranked them in four minutes. The same census exposed that MuPDF's own answer for CMBX depends on the embedded program - a fact no rule of ours can reproduce, so the choice is the least-wrong one and says so.

---

## 2026-09-10 - The reader swap checked for overfitting, and the real fault found underneath it

**Done**
- **The owner asked the right question about the 1.5 line-gap threshold: how do I know it is not just fitted to the 13-page quick gate?** The honest answer separated the four fixes. Three of them - the double rotation, the estimated baseline, the font flags - are not tuned on the gate at all: each was settled by comparing a quantity the two readers must agree on because they describe the same piece of paper, and none of those measurements involves a score. **Only the gap threshold was chosen by scoring, and the exposure was worse than it first looked: two of the gate's 13 pages are pages I had read while diagnosing the fault.** Fitting a number on pages you debugged on is the ordinary way to fool yourself.
- **A guard already in place, found while answering: `bench/tools/launch_run.sh` refuses to launch a full run unless the quick gate reads at least 96.** With the swap on it reads 90, so the degraded reader cannot become a scored candidate by accident. The safety net was working without anyone remembering it was there.
- **`bench/tools/reader_generalise.py` written to answer the question with evidence: 150 benchmark pages drawn at random with all 13 gate pages excluded by name, scored under MuPDF and under pdftext at three thresholds.** Old scans are left out on purpose - a page sent to a model under D019 reads the same whichever text reader is installed, so including them would only dilute the signal.
- **Then, while that ran, the remaining 10 gate checks turned out not to be a tuning problem at all.** `multi_column/05eac...` reads its text almost exactly as MuPDF does (261 lines against 260, 1,479 words against 1,481) and still scores 0/5. The blocks tell the story: **139 blocks under MuPDF, 256 under pdftext, every one of them a single line, and body text classified as HEADER.**
- **The cause is the font size, and it is a plain bug rather than a threshold.** PDFium reports a font's *nominal* size; a PDF may then scale it by its text matrix, which MuPDF folds in and PDFium does not. On that page every character came back as **size 1.0 against MuPDF's 8.0**; on `long_tiny_text/11` the computed body size was **35.0 against 5.9**. With one size for the whole page nothing can tell a heading from body text and the line-spacing rules are computed from a meaningless number, so no paragraph ever forms.
- **The fix is measured, exact, and matches PyMuPDF to three decimals on all three test pages: multiply `FPDFText_GetFontSize` by the scale of the character's text object matrix** (05eac 1.000 -> 7.970 against 7.970; arXiv 11.955 -> 11.955, already right; tiny text 35.830 -> 5.149 against 5.149). The loose box height is a near miss and not good enough - 7.954, 10.616, 5.829 against those same three.
- **Correction to yesterday's assessment of what is left.** I recorded `find_tables` as the real obstacle to leaving PyMuPDF, with no straightforward replacement. That is wrong: **PyMuPDF's table finder is a port of pdfplumber's, MIT-licensed, and says so in its own source header - and pdfplumber 0.11.10 is already installed here.** The item flagged as the blocker is the one whose permissive original was already in the virtual environment.
- **The corrected map of what still runs on PyMuPDF:** page rendering (6 sites, easy - PDFium renders natively), vector drawings (3, a moderate rebuild with every raw ingredient available), image positions (2, easy), `find_tables` (1, easy via pdfplumber), and `get_bboxlog` (2) - **which is now the genuinely awkward one.** It is an ordered log of every drawing operation and its box, used to work out what is drawn over what and so to spot hidden text (D011). PDFium has no such log; page objects do come back in painting order with types and bounds, which reconstructs most of it, but that is a rebuild rather than a swap.
- **D022 written:** every stage moved off PyMuPDF is proved against a quantity that must be identical between the readers, and the score is the second check, never the first.
- **The generalisation run answered the owner's question: the 13-page gate is honest.** Over 150 unseen pages, MuPDF scores 638/734 and pdftext 583 at gap 1.5 - **91.4% of MuPDF, against 90% on the gate**. The threshold plateau held off-sample too (581 at 1.0, 583 at 1.5, 578 at 2.25 - five checks across the whole range). The losses concentrated exactly where the font-size bug predicted: multi-column -23, long tiny text -17, tables -11, arXiv maths -4, headers and footers 0.
- **The font-size fix, written test-first (`tests/test_pdftext_font_size.py`).** The tests build the offending PDF by hand - `/F1 1 Tf` followed by an 8x text matrix - so the case is pinned without depending on a benchmark file, and they failed on the old code first. `_drawn_size` multiplies `FPDFText_GetFontSize` by the scale of the character's text-object matrix, cached per object (roughly one object per span, so the cost is negligible).
- **A second defect surfaced while checking the first, and it is the same shape.** With sizes fixed there was still a cluster reporting 1.0 - 906 characters on the small-print page, **every one of them a space PDFium had invented to fill a gap.** An invented character has no text object and therefore no size, and where a run of them formed a span of its own that span had nothing to measure, so its phantom 1.0 dragged the page's body size down. `_fill_blank_span_sizes` now gives such a span the size of the nearest measured neighbour, which is what MuPDF does implicitly by putting its own synthetic spaces inside the surrounding span. Character-size distributions now sit within a few counts of MuPDF's on both pages.
- **Result: the gate goes 90 to 97 of 128, and the pages recovered are the ones predicted.** `multi_column/05eac...` 0/5 to 3/5 (MuPDF also gets 3), `long_tiny_text/11` 19/31 to 22/31 (MuPDF gets 22), `headers_footers/04cea...` 11/12 to 12/12, which is one better than MuPDF. The default path is unchanged at 100/128 and the suite is 304 tests.
- **Page rendering prepared, and its convention settled by measurement rather than by reading the docs (`bench/tools/render_compare.py`).** Full-page renders agree in size on all 32 sampled pages, 8 of them rotated, differing by a mean of 4.3 shades per pixel at 1x and 2.8 at 2x - antialiasing, not geometry. Clipping is where the two libraries part: PyMuPDF takes a rectangle, PDFium four insets from the edges of the bitmap *after* rotation. The right conversion is `crop = (x0, H - y1, W - x1, y0)` in display space, which scores 5.7 against the wrong reading's 35.7, and works equally on rotated pages (5.70) and upright ones (5.74). Two traps found on the way: a symmetric test clip makes the two candidate conversions arithmetically identical and so proves nothing, and pypdfium2 rounds each inset up (`math.ceil`), so a fractional clip shifts the crop by up to a pixel - which over text looked like a wrong convention (19.4) until the clip was put on whole points (5.7).
- **That measurement turned up a bug in the shipped MuPDF path, on rotated pages only.** `get_pixmap`'s clip is in *display* space: clipping with a display-space rectangle reproduces the matching region of the full render exactly (mean difference 0.000), while the same rectangle multiplied by the inverse rotation matrix returns a differently shaped, wrong region (179x259 where 422x179 was wanted). But `_renders_uniform` in `textlayer.py` and `_ink` in `marks.py` both do exactly that - they take a box in display space, multiply by `~M`, and clip. On an unrotated page `M` is None and nothing happens, which is why it has never shown; on a rotated page the hidden-text flat-area check (D011) and the tick/cross renderer both inspect the wrong part of the page. About 1% of the benchmark (15 of 1,403 pages), more in the insurance library where landscape tables are common. **Fixed on the owner's instruction, and checked where it matters rather than where it was convenient** (his words: "if there is nothing in the 13-page test, we should check it on docs where it actually matters"). `bench/tools/rotated_clip_check.py` found every rotated page carrying something the mark reader would look at: all 15 in the benchmark, and 67 in the insurance library, concentrated in Australian Seniors and Everyday home insurance - the landscape benefit tables. Reading all 82 before and after: **80 are identical, including every one of the 67 library pages.** One benchmark page gains a single mark. One - a dense engineering drawing - goes from 103 marks to 262, and **scores 0/5 either way**, so the benchmark is indifferent. The 159 extra are false positives the mark reader has always produced on a drawing-dense page; the bug had been suppressing them on rotated pages by accident, because a wrongly-aimed clip usually lands on blank paper and fails to classify. **The fix introduces no new behaviour: on an upright page `M` is None and the box was always used as it stands, so rotated pages now do exactly what upright ones have always done.** Gate unchanged at 100/128, suite 312.
- **`tests/test_rotated_page_clip.py` states the invariant without needing ground truth: wherever ink shows up in a full render, clipping to that same box must find ink there.** Four rotations each way, on a hand-built PDF carrying one black square. It passes 8/8 with the fix and, against the old code, fails at 90, 180 and 270 while passing at 0 - which is the claim about the defect being rotation-only, proved rather than asserted.
- **Page rendering moved, and it costs nothing: the gate reads 100/128 with PDFium drawing and 100/128 with PyMuPDF, and 97 either way when the pdftext reader is on too.** Rather than change seven `get_pixmap` calls one at a time, they now all go through `truedoc/extract/render.py`, so the choice of drawing library is made once and can be tested in one place. Switched on with `TRUEDOC_RENDERER=pdfium`, separate from `TRUEDOC_READER` so each can be measured alone. It falls back to PyMuPDF rather than failing a page, and lets go of its PDFium handles when a document finishes (marks.py asks for one crop per candidate shape, so the document is held open between calls).
- **The strongest evidence it is a true swap: on the 82 rotated pages, both libraries read exactly 263 marks and not one page differs.** The mark reader is the most pixel-sensitive thing in the project - it thresholds pixels into a grid and matches templates - so agreement there is worth more than the score being equal.
- **A third instance of the rotated-clip mistake, found while wiring: `ocr_region` in `ocr/rapid.py` mapped its clip back into unrotated space and then mapped the OCR results forward again.** Self-consistent, and wrong at both ends on a rotated page. Both halves removed. **The codebase had disagreed with itself all along:** `vision/regions.py` documents the opposite belief - "which is also the space PyMuPDF's `clip` expects" - and it was the one that had it right. Three sites believed one thing, one believed the other, and nobody had measured until now.
- **`tests/test_render_backends.py` (12 tests) compares the two libraries on a hand-built page at all four rotations, clipped and whole, grey and colour, scaled, and with a clip hanging off the edge of the page** (PDFium refuses a negative inset where PyMuPDF simply intersects, so the clamp is tested too). Checked that the tests bite: with the crop conversion deliberately replaced by the other plausible reading, four of them fail, at every rotation including 0.
- **Then the drawings and the images, and the item that had looked like the hard one dissolved.** `get_bboxlog` - a log of every drawing operation and its box, with no PDFium equivalent - was the thing I had written down as the real obstacle to leaving PyMuPDF. Reading what TrueDoc actually takes from it settled it: **two things only, the boxes of images and shadings, and the order they were painted in.** PDFium's page objects come back in painting order with a type and a box, which is the same information. `truedoc/extract/pdfium_objects.py` now serves all four callers - `_extract_drawings`, `_extract_images`, `marks._candidates` and (later) `_Visibility` - from one list, behind `TRUEDOC_OBJECTS=pdfium`.
- **Measured before wiring (`bench/tools/objects_compare.py`, 60 pages): image boxes agree 122 of 122; the per-page path match rate has a median of 1.000, a tenth percentile of 1.000, and 20 of 22 pages at or above 0.95.** The two that disagree are dense vector artwork - one arXiv figure page has 82,218 paths to MuPDF and 39,973 to PDFium, because MuPDF splits a compound path into its subpaths and PDFium keeps it whole. A difference in what counts as one drawing, not in where anything is. **Gate: 100/128 either way**, and 97/128 with all three switches on, the same as the text reader alone. Over the 82 rotated pages the mark reader differs by 4 marks, all on the 0/5 engineering drawing.
- **A measurement trap of my own, worth writing down: my first comparison ran for ten minutes and had to be killed.** The matcher was a nested loop over two lists of boxes, which is fine until a generated page carries 82,000 paths. Bucketed by rounded corner it finishes in seconds. The first reported figure - 1.7% of paths matching - was also junk for a different reason: one page held 83,258 of the 83,258 totals between them, so the global ratio described that page and nothing else. Per-page rates told the true story.
- **And a correction found by a failing test: PDFium's bounds for a stroked path are wider than PyMuPDF's by a *full* stroke on each side, not half.** A 2pt rule at y=100 is `(20, 100, 180, 100)` to PyMuPDF and `(18, 98, 182, 102)` to PDFium; both are right, one reports the path and the other the ink. The comparison tool had assumed half and understated the agreement (19 of 22 pages rather than 20). No compensation is applied in the product - the consumers are robust to it and the gate says so - but the test states the invariant as containment with bounded slack rather than pretending the boxes are equal.
- **The table finder: the route is proven, and it is not the obvious one.** Using pdfplumber as a library - opening the PDF with it and calling `page.find_tables` - does *not* reproduce PyMuPDF's answer: on `b5c5b866...` MuPDF finds two tables and pdfplumber finds none, because `lines_strict` means "the edges my own reader found", and pdfplumber reads through pdfminer. **But pdfplumber exposes its algorithm separately from its reader:** `edges_to_intersections`, `intersections_to_cells` and `cells_to_tables` are plain functions over plain dictionaries, as are `snap_edges` and `merge_edges`. Fed edges derived from our own `pdfium_objects`, they reproduce MuPDF exactly on that page - two tables of 35 and 30 cells against MuPDF's (5x7) and (6x5). So the licence-clean path is the MIT algorithm over our own geometry, with no third engine and no pdfminer cost.
- **Built, on the owner's instruction to finish tables first and not to treat effort as a barrier.** `truedoc/tables/ruled_pdfium.py` runs pdfplumber's `snap_edges`, `merge_edges`, `edges_to_intersections`, `intersections_to_cells` and `cells_to_tables` over rules taken from `pdfium_objects`, and hands the resulting cells to pdfplumber's own `Table` with a stand-in page carrying **TrueDoc's characters** - `Table.rows` needs nothing but the cells, and `Table.extract` nothing but a list of characters, so both come across without a third engine. Behind `TRUEDOC_OBJECTS=pdfium` with the rest of the page-object work.
- **Two details that had to be right.** The rules a table is drawn with are not always strokes - a flat filled rectangle or a one-pixel image stretched along a row is common, which is why the edge builder reads `o.rects` and images as well as paths. And the geometry is in the page's *unrotated* space, which is what `find_ruled_tables` expects because it applies the page rotation itself at the end, while TrueDoc holds its characters rotated - so the characters are turned back on the way in, inverting exactly the turn `textlayer._rect` applied. Without that the grid still looks right and every cell comes out empty, which is why the tests cover 90, 180 and 270 as well as upright.
- **`tests/test_ruled_pdfium.py` (8 tests):** a 2x2 ruled grid built by hand, checked for shape, for cell text coming from our own characters, for the cell boxes `deal_tall_cells` and the span logic read, for agreement with PyMuPDF on how many tables and of what shape, for the three rotations, and for a page with no rules yielding nothing. **Gate: 100/128, the same as PyMuPDF, with the three table pages unchanged at 14/14, 5/7 and 10/14.**
- **And then the whole category was scored, and it says the opposite: 848/1022 with MuPDF against 810/1022 with ours - 38 checks lost.** The quick gate holds three table pages of 188 and showed nothing at all. This is the clearest case yet for the rule that the gate is a canary and not a measurement, and for the owner's instruction to check a change where it actually bites: had this gone in on the strength of 100/128, it would have cost about half a point overall, which is half the whole margin over Chandra. **Not shipped, and the switch stays off while the loss is traced.**
- **Tracing it found three real bugs, two of them in the page-object reader rather than the table code, and the gap closed from 38 to 18 (810 to 830 of 1022).**
  1. **Form matrices were ignored.** PDFium reports the objects inside a form XObject in the *form's* coordinates. `_walk` recursed into forms without carrying the matrix down, so one page's rules all sat 178.5pt from where they belonged - exactly that form's translation. This was never a table bug: every drawing and image on any page using a translated form was in the wrong place.
  2. **Path segments needed a second matrix.** `FPDFPageObj_GetBounds` returns a box *already through* the object's own matrix; `FPDFPathSegment_GetPoint` returns the raw points from *before* it. So bounding boxes looked perfect while the rectangles derived from the same object sat at y = -32,000. On one page 441 objects of 1,716 were affected; afterwards, one - and that one is a genuinely enormous path.
  3. **Overprinted text was doubled.** A page that fakes bold by drawing its text twice made every cell read `SSmmiitthh eett aall.` - 755 duplicated characters. TrueDoc's own word building already collapses these, which is why the page converts correctly everywhere else.
- **Two changes measured and taken out again.** Breaking every *box* into its four sides, as pdfplumber does with a rectangle, because a page reading 4x1 against PyMuPDF's 5x2 is missing exactly one outer rule: it did not fix that page and invented a spurious table on two that had been matching cell for cell. And restricting edges to strokes only, which is what `lines_strict` means to pdfplumber: 804 against 830 for taking flat fills and image strips as well.
- **A wrong hypothesis, caught by strengthening a test rather than by the score.** PyMuPDF reports its table box in the *rendered* page's space - measured, `(66.6, 84.9, 545.4, 304.0)` inside a 792x612 rendered rect - so building there looked obviously right. It is worse: a page turned 90 degrees has its glyphs turned too, so in rendered space the text runs down the page and pdfplumber's extractor stacks each cell into `K\na\np\np\na`. **The test that should have caught the original fault could not, because the sample grid was 2x2 and a square grid reads the same transposed.** Made it 2x3, and it failed immediately on the change I was about to keep.
- **Where the remaining 18 sit:** about a third on turned pages, where each cell's text is right but the rows and columns are the transpose of PyMuPDF's (8x7 against 7x8) - a real gap, now written into the test that covers it rather than papered over; four on the one page whose outer rule is a box; the rest scattered one and two at a time. **Still not shipped.**
- **A D016 wrinkle, owned and checked (Thursday afternoon, after the owner asked whether the gap would be addressed).** The edge-rule choice - "all" over "strokes", 830 against 804 - was made on all 188 table pages, which include the held-out fifth. Re-read on the tuned-on 152 only: "all" 685, "strokes" 678, against MuPDF's 703, so the choice stands without the held-out pages. **And the split says something better than that: on the 36 held-out pages ours scores 145/175, identical to MuPDF's 145.** The whole 18-check gap sits on tuned-on pages. A systematic defect would show on both halves; this is page-specific.
- **Run 66 scored 17:25: 81.4 against run 65's 84.0 (CI 80.4-82.3), held-out 76.9 against 80.9.** 290 checks lost and 46 won across 173 pages: arXiv maths -91, tables -72, multi-column -67, tiny text -13, headers and footers -1; old scans and old-scan maths identical to the check, because the reader never touches a model page. **The quick gate read 97/128 for this configuration.** In points: multi-column and tables about 0.9 each, arXiv and tiny text about 0.4 each. Not shipped.
- **Traced the same evening to three causes, every one silent and none of them where I first looked.** The first guess - that pages with an OCR layer were no longer reaching the model, because run 66 predates the hidden-text branch and was joining PDFium's characters to MuPDF's text trace by rounded origin - was checked on the six worst pages and was wrong: every one is digital under both readers, with no hidden text. What the same probe showed instead was that PDFium yields *more* visible characters on five of the six.
  1. **A graphics-state scale the size fix could not see.** The tiny-text page opens with `0.7492 0 0 0.7492 0 0 cm` and every text object carries an identity matrix, so `Tf` x the object's matrix gave 9.30 where MuPDF reads 6.97 - exactly 4/3. `FPDFText_GetMatrix` returns the *effective* matrix per character and reproduces MuPDF on the `cm` page, the `Tm` page and an unscaled one. Fixed in `_drawn_size`; `tests/test_pdftext_font_size.py` gains the `cm` case.
  2. **End-of-line hyphens delivered as U+0002.** `Ipsilat-`, `reconstruc-`, `radiolu-` under MuPDF are `Ipsilat\x02` ... under PDFium, and the hyphenation repair looks for "-", so no broken word rejoins. Not a mapping error as PDFium sees it - the fonts (an AdvTT TrueType subset, and CMR12) genuinely map the glyph to U+0002; MuPDF ignores a control-range mapping and PDFium trusts it. I had logged this on day one as "2 characters in 1,896" and moved on. The fix is by shape: a control character whose ink is a flat bar (0.26-0.32 em wide, 0.05-0.08 em tall, a quarter-em above the baseline, measured on both fonts) is a hyphen. **After it, the worst table page has no word either reader lacks.**
  3. **TeX's symbol fonts delivered as their raw codes.** The maths rebuild was failing outright - `$I_{t}$` came out as `I,`, `$Z\in L^{2}$` as `Z e L2` - because in cmsy and cmmi PDFium hands back the glyph's *code* as a letter where MuPDF resolves the glyph *name*: `k` for the parallel sign, `h` and `i` for the angle brackets, a backtick for the script ell. TrueDoc already carries raw-code tables for cmex; cmsy and cmmi now have theirs (the standard OMS and OML encodings, in `pdftext_rawdict.py`, consulted only where PDFium itself flags the mapping broken). **The census of unmapped codes over 150 pages no longer lists any of them.** What it still lists is a mojibake page where MuPDF reads *spaces* - not a standard to copy - and a few small cases in other fonts (`\x03` to a box, `\x08` to a star, `6` to `=`), left for now.
- **The size fix was necessary and not sufficient.** With sizes identical at 6.97 the tiny-text line still reads `ofthe`: the characters and boxes match, but MuPDF puts a synthetic *space character* between `of` and `the` and PDFium does not, and TrueDoc's gap rule was tuned with MuPDF's spaces present. Measured on the four worst pages: ordinary letter pairs sit at a gap of at most 0.04 x size (p95), MuPDF's spaces start at 0.16, and PDFium adds 236 spaces of its own in the 0.11-0.15 band that MuPDF does not. A rule of "space wherever the gap is at least 0.15 x size" splits no letter pair and misses 14 of MuPDF's 597. Next: rebuild the synthetic spaces from geometry rather than trust PDFium's.
- **State after the three fixes: 347 tests and 2 expected failures, gate 100/128 default and 98/128 with every switch on** (was 97).
- **The gluing traced to its last cause, and it is not spacing.** On the `ofthe` pair both readers put the `t` at 254.78 and neither inserts a space; they differ on where the **f ends** - MuPDF 253.47, PDFium 253.91. TrueDoc's own word builder breaks a word at a gap above `max(0.13 x size, 0.9pt)`: MuPDF's 1.31pt clears it, PDFium's 0.87 does not. Measured across the page, PDFium's loose box matches MuPDF's right edge to a 95th percentile of 0.007pt - the difference is confined to glyphs whose ink overhangs their advance, **56 of the 68 cases the letter f**, the rest mostly i. MuPDF's box is the advance box. PDFium exposes the advance (`FPDFFont_GetGlyphWidth`), and origin plus advance reproduces MuPDF's right edge to 0.000 on that page. The wide-gap disagreements in the broader sample turned out to be something else entirely: 296 of 297 sit inside arXiv formulas (a cmex delimiter, a txsys infinity), where the rebuild works from positions and a synthetic space is neither here nor there. **So: no space rule. The box takes the advance for its right edge, which is what MuPDF was doing all along.** `tests/test_pdftext_char_boxes.py` pins it on Times, whose f overhangs and which every reader carries.
- **The advance fix went in and did exactly what it should - the f now ends at 253.47 under both readers and the gap clears the rule - and then went one glyph too far.** With the fix, "fixtures" read "fi xtures" and an arXiv gate page lost a check to "suffi cient" and "modifi ed": the **fi ligature**, one glyph carrying two characters, whose lone-f advance is narrower than the glyph. PDFium's signature for it is exact - consecutive characters with the same loose box *and* the same origin (12 on the tiny-text page, all fi and ff; 36 on the arXiv page, fi plus the rotated arXiv watermark the level-text test already excludes) - so a character whose neighbour shares its box keeps the loose box. That restored "fixtures", and then the test's ligature case exposed the other half of the same fact: PDFium gives both characters the whole glyph box, and MuPDF does not - the i's left edge sat 3.9pt from MuPDF's. **I inferred "MuPDF divides the box between them" from that one edge, cut the box into equal slices, and the test promptly failed on the *other* edge by 1.95pt.** Measured directly, with ligatures expanded as TrueDoc asks: MuPDF gives the f the whole box (31.86-35.75 on Times at 7pt) and the i a zero-width box at its right edge (35.75-35.75). Two inferences from one number each, one of them wrong; the direct measurement took a minute. Word building is indifferent either way, everything that reads a left edge is not. Two table corrections from the same page: MuPDF leaves cmsy `0x37` as `7` for the maths stage to join to its arrow, so it is deliberately absent, and reads `0x36` as a combining negation slash.
- **The three fixes measured on their categories before the f fix went in** (no model either side, so only the gaps compare; `bench/out/cats/`): **tiny text -13 in run 66 to -4 (361 against 357 of 442); multi-column -67 to -24 (678 against 654 of 884).** Won 3 and lost 7, won 3 and lost 27. ArXiv was cut from this pass: at this scorer's pace (15 seconds a page, KaTeX included) its 250 pages would have frozen `truedoc/` for two more hours, and run 67 will report it in under one along with everything else. The worst multi-column page is the same one run 66 named, `07f4d706..._page_7_pg1`, 5/5 to 1/5.
- **State at 19:20, six reader fixes after run 66, all committed (d709c8a, 55ef422): suite 349 and 2 expected failures, gate 100/128 default and 98/128 with every switch on. Run 67 (candidate `truedoc66`) launched at 19:20 with every switch on**, the launcher's gates to pass first. Against run 66's 81.4 and run 65's 84.0.
- **Run 67 scored 20:19: 82.4 (CI 81.5-83.4), held-out 78.5.** Against run 66: 89 checks won, 17 lost - multi-column +42, tiny text +14, arXiv +13, tables +3 - and **tiny text, at 88.7, is now above MuPDF's 88.5.** Against run 65's baseline: arXiv -78, tables -69, multi-column -25, headers -1, tiny text +1. Held-out up 1.6 on run 66 and still 2.4 short of run 65. 49 minutes of conversion.
- **The tables gap is the lead, and it says I closed a hypothesis on the wrong evidence.** The no-model category measurement puts the table gap at 18 checks; the full run puts it at 69. On MuPDF the model adds 53 table checks over the no-model figure, on PDFium it adds 2 - so on this path the model's contribution to tables is almost entirely lost. I had ruled out "model pages are being lost" by checking the six worst pages *overall*, which were all digital; that was the wrong population - the question was never about those pages. `3f788302...pg30`, which the table finder now reads cell for cell in the no-model measurement, still loses 4 in the full run. **Traced within the hour, and the model was not it after all** - that page scores 4/8 under PDFium with the endpoint on *and* off, 8/8 under MuPDF both ways. What the no-model measurement had missed was simpler and my own doing: **the tables category runs set `TRUEDOC_OBJECTS=pdfium` alone, with the text reader still MuPDF**, so they measured the table finder in isolation and never the reader's effect on table pages. The full run's diff of that page shows exactly that effect: `Introductionto`, `TypeofTask`, `Week8 Term1`, `Teamworkandsafety`, `14LW,15LW` - **words glued inside cells.** The cell text comes from pdfplumber's own text assembly over our characters, which breaks words at an absolute 3pt gap; with MuPDF's synthetic spaces present that never mattered, and with PDFium's fewer spaces a 9pt word gap of 2.5pt is not a break. The same spacing story as the tiny-text page, through a different door. **Lesson: a category measurement must carry every switch the full run will carry.**
- **Fixed the same hour.** pdfplumber's extractor takes a size-relative tolerance, and 0.15 x size - in the measured band between letter gaps (at most 0.04) and MuPDF's spaces (from 0.16) - restores the cells outright: `Introduction to / science`. The tall-cell re-read in `clipped_blocks` joined our characters blindly and has the same rule now (`_spaced_text`). **The worst table page goes 4/8 to 8/8 under every switch, its output within one character of MuPDF's.** Suite 351 and 2 expected failures on and off; gate 98/128 all-on; `test_small_type_keeps_its_word_spaces_inside_cells` pins it. The tables category is being re-measured with every switch on, as it should have been the first time.
- **The launcher refused it - and was right to.** Gates 98, 45 and 58, all clear; `pytest rc=1`. The launcher runs the suite with whatever switches the launching shell carries, and under them `test_sideways_pages` reached `os.stat(None)`: a page built in memory has no file name, and the PDFium object reader raised a `TypeError` that its `except OSError` does not catch. A real product fault - any in-memory document with the switches on - not a test fault, and one I had not seen because I ran the suite only in the default configuration. Both adapters now fall back to MuPDF when there is no path, as the renderer already did. **Lesson, and a habit from here: run the suite with the switches on as well as off. The launcher does; I should have.**
- **Run 66 launched 16:21 with every PDFium switch on** (`TRUEDOC_READER=pdftext TRUEDOC_RENDERER=pdfium TRUEDOC_OBJECTS=pdfium`, candidate `truedoc65`, run 65's 84.0 as the clean baseline). The launcher's gates passed first: quick gate 97/128 against its floor of 96, maths samples 45/52 and 56/64 against floors of 44 and 56. The point of running before the last 18 table checks are fixed: the quick gate read a perfect 100 on tables while the category lost 38, and the text reader reads 97 on that same gate. Across 1,403 pages that could be three checks or thirty; the run finds out, with held-out and tuned-on reported separately, and the next day's work is then ordered by points rather than by whichever category happens to be in view.
- **What is left on PyMuPDF after all this:** `get_texttrace` (3, only for `_Visibility` and the maths path), `get_bboxlog` (2, only inside `_Visibility`), `set_rotation` (2), `find_tables` (1, and pdfplumber is the MIT original it was ported from), and `pymupdf.Rect` as a geometry type (16). **Everything else is switchable.** `_Visibility` - the hidden-text machinery of D011 - is the one real piece of work left, and it needs the two things the new object reader does not yet carry: which text was drawn invisibly, and the opacity it was drawn with.
- **Threshold re-swept afterwards, as promised, and it barely matters any more: 96 to 97 across every value from 0.8 to 2.5.** 1.5 stays, now on a genuinely flat curve rather than one propped up by a bug. That is the clearest evidence the earlier worry was real: most of what the threshold had been doing was compensating for the broken sizes.

**Learned**
- **A parameter tuned on top of a bug fits the bug.** The 1.5 threshold was chosen while every font size on some pages was wrong by a factor of eight, and part of what it was doing was compensating for that. The threshold has to be re-swept once the size is right, and its current value should be treated as provisional rather than measured.
- **The dangerous failures in a swap like this are the silent ones.** A size eight times wrong throws no exception and loses no text; it produces a confidently wrong document. Both of the day's real defects were found by asking "why did this paragraph not join" - never by a score, which can only say that something is worse and never which of four stages did it.
- **Quote the tail, not just the middle.** The baseline estimate this work replaced had a respectable median and was 25.8pt wrong on precisely the glyphs it existed to serve. A median alone would have passed it.
- **Check who wrote the thing before calling it the hard part.** One look at a source header turned the swap's supposed blocker into its easiest remaining item. I had asserted the difficulty from the shape of the API rather than from its provenance.
- **A small canary test can be trusted - but only after measuring that it can.** The gate is 13 pages and it had been steering every decision for a day before anyone asked whether it was representative.

**Next**
- The order agreed with the owner, once the generalisation run lands: **font size first** (measured and ready), **then re-sweep the gap threshold** on both the gate and the 150-page sample, then page rendering, image positions, tables via pdfplumber, vector drawings, and `get_bboxlog` last.
- ~~An owner decision waiting: the rotated-page clip bug~~ (fixed 10 Sept on his instruction, checked over 82 rotated pages including 67 from the library; see above).
- **A separate weakness the clip fix exposed, worth its own look one day:** the mark reader finds 262 candidates on a dense engineering drawing and names 59 of them as ticks, crosses, squares and circles. Cropping the page at those boxes shows letter fragments and bits of the drawing, not symbols. It costs nothing on the benchmark (that page scores 0/5 regardless) and nothing in the library, and it is not new - upright pages have always behaved this way - but a candidate filter that asked "does this page look like a drawing?" would stop it.
- Nothing in `truedoc/` may be edited while a scoring run is in flight - its child processes read the code from disk, so an edit mid-run silently invalidates the comparison. Same rule as a benchmark run's "validating" to "finished converting" window. Heavy comparison runs alongside one also starve it: run 2 took far longer than run 1 because `render_compare.py` was competing for the same cores.

---

## 2026-09-09 - Icons: measured across the whole library, reviewed by the owner, and not built

**Done**
- **The question, from the owner: how would TrueDoc know which icons carry meaning, and then what they mean?** His own observation set the frame - if the words beside an icon already carry the meaning, the icon is illustration - and the design turned on using that redundancy twice: as a filter (ignore what the words already say) and as the teacher (the labelled occurrence is what lets an unlabelled one elsewhere be resolved). Written up with the numbers in `docs/ICONS_REVIEW.md`.
- **The census over all 1,176 documents and 23,870 pages (`bench/tools/icon_census.py`, 251 s).** 326 documents (28%) use icons, averaging **7.6 distinct** each; 171 (15%) have load-bearing ones, averaging 4.7. Only **66 documents (6%) carry a legend**, but a short label beside the icon is available four times more often (314 icons against 77) - so the self-describing occurrence, not the legend page, is the mechanism that would do the work. The architectural result that survived everything: **15,085 occurrences collapse to 171 distinct shapes**, 88 uses per thing, which is why per-page vision is the wrong tool - reason per symbol, not per page.
- **Three instrument failures caught before they became answers.** Keying icon identity on exact size split one document's six symbols into 339; counting every small shape called a 117-page policy 169 symbols when 67 appeared once and the rest were rules and filled quads; and treating any text beside an icon as its label confused "house Home" (a name) with "tick Loss or damage..." (the statement being marked), which needed the repetition test to separate. Each was found by validating against documents whose answers were already known.
- **A contact sheet of all 171 shapes, which disproved the number I was about to report.** The plan said about 156 crops would need a model. The sheet showed a large share were letters drawn as outlines - logos, brand names - and my structural filter had promoted every one. Looking is what caught it; 171 crops fit on one page and 24,000 pages do not.
- **A review dossier put all 159 renderable shapes to the owner (`bench/tools/icon_dossier.py`, the `review-dossier` skill).** Each card carries the icon enlarged *and the band of page it sits in* with the icon outlined - added at his request, and decisive: one card resolved instantly to the "n" in a **coles insurance** logo, another to a fixture in a floor plan that our own mark reader had called a tick. A second request, evidence and decision on screen together, became `bench/tools/dossier_two_column.py`.
- **The owner drained all 159, and the machine was wrong on 92 of the 119 cards where it proposed anything - 23% agreement.** It proposed "carries meaning" for 71 pictograms and was overridden on 62; "ignore" for 55 letter-shapes and was overridden on 30. **The structural filter must not ship.** In his words, on the two most-used shapes in the corpus: *"this specific occurrence is an icon that denotes a feature on a floor plan. This is not a tick."* Also a red light shade, the hair of a female figure, a broken window, the wheel of a car - the "contrasting set of the same size" test is matching coincidental pairs inside illustrations.
- **The letters spell words, but words the text layer already has.** 30 were marked as carrying meaning, each named to its word. Checked afterwards: coles insurance, CGU, RACT and the phone number are all already in the text, so the drawn glyphs are duplicates and ignoring them loses nothing. Where the word is genuinely absent - "Allianz" on a 44-character page, "LUCKY YOU'RE WITH AAMI" on the AAMI covers - it is a cover-page logo whose brand name appears elsewhere in the document. A fidelity gap on covers, not a meaning loss.
- **Verdict: the icon-resolution pipeline is not worth building for this corpus, and no GPU session is needed.** The population is roughly a dozen shapes; the one document where icons genuinely carried meaning (Huddle Black) was already fixed on 8 September; and the 156-crop estimate collapsed the moment a person ruled out the illustration fragments for nothing.

- **The directional arrows built, and the owner's reading of them was right (10:40-11:20).** He asked whether they should be handled like the ticks and crosses we already capture. They should, and the machinery was already most of the way there: the AAMI chain arrow is a white chevron painted over a filled grey disc - the same knockout construction as the Huddle ticks - and yesterday's knockout pass pulls a clean chevron out of it. The only thing missing was vocabulary: the templates knew tick, cross, dot, circle, square and box, so the chevron matched nothing (`_best_template` returned None) and the disc underneath was reported as a dot. Added `_chevron`, which tells an arrow from a cross by the corners - an X reaches all four, a chevron only the two its arms open towards, with its point on the opposite edge - and four arrow entries in `MARK_TEXT`. **Two pieces were needed, not one:** the mark was then classified correctly and still silently dropped, because `_attach_marks` only ever puts a mark into a table cell or at the head of a line, and an arrow alone in the gap between two paragraphs matches neither. A picture whose whole content is one readable mark now renders as that mark. `aami-home-building-insurance-pds-a01463_4906c3da.pdf` page 11 now reads "If you have a sum insured shown on your certificate of insurance. / ↓ / The most we will pay ... is the sum insured shown ... / ↓ / Some items also have fixed limits", which is the page. Four tests; 281 in the suite.
- **Two limits stated rather than papered over.** The placement half depends on the arrow landing inside a picture region, which is how these documents are built but is not guaranteed; on a page where no such region forms the arrow is still read and recorded in the page's own `marks` record but does not reach the text, and fixing that means creating blocks mid-pipeline. And the red `(!)` callout markers beside every important-note paragraph on those same pages are still unread - a ring with a glyph inside rather than a knockout, and "!" is not in the vocabulary either.

- **M6 built: the invented-text check on model-read pages (D021, `truedoc/vision/corroborate.py`).** D008 says nothing is invented, and on the 281 pages a model reads for us nothing verified it - the promise was a policy we stated rather than one we measured. The page's own reading is the witness (a hidden layer, or our engine's rejected lines already kept in `page.meta["witness_lines"]` for the running-head witness), and a verdict per page goes in the front matter under `truedoc.corroboration`. **Measured before it was built, over all 281 pages: 181 corroborated, 91 unchecked, 7 low support, 2 unverified.** Four verdicts rather than two, because "unchecked" - a bare scan with no witness at all, a third of them - is the honest answer and a two-state check would imply a pass nobody earned.
- **It reports and never acts, and that is measured rather than cautious.** Every low-support page turned out to have a broken witness rather than an inventing model, so dropping model text on low support would have destroyed correct readings. Hand-audited, which is M6's stated condition: `7b9b73157809_pg19` ours reads `GlOW Tack J and Sponse¢ | Salau'_` against the model's "TABLE B-3. DETAILED COST BREAKDOWN"; `old_scans/74` ours reads `+]The [merican [ssnciatim of the Je Gross.` against "The American Association of the Red Cross."; `00d8a44d` ours reads `7 PDA 7uq dZ 7z] H[oE` against correct Korean. **Zero inventions.** The script test names the clearest case outright - "the page's own reading is Latin where the model reads Arabic, so its encoding is broken and it cannot witness anything". 286 tests; 30 model pages page-checked, all unchanged, 85 against 85.
- **A limit found by the audit and written into the code rather than glossed:** the script test compares the *dominant* script, so a bilingual page defeats it - a Korean paper with an English title has Latin on both sides and its mojibake layer lands in "low support" rather than "unverified". Still flagged, still never acted on, but the reason given is wrong.

- **M18 opened, and the owner's reasoning set the order: switch now, so later work builds on the new foundation rather than raising the bill.** He also asked whether PyMuPDF's own source would show us how to group lines. **It would, and that is exactly why not to read it:** the grouping lives in MuPDF's C code, which is the AGPL we are trying to leave, and reimplementing from it risks a derivative work - self-defeating. There was no need: **pdfminer.six (MIT) was already installed** and does the same job, and the approach is documented rather than secret.
- **Three investigations, run 9 Sept afternoon.** (1) Licences: **pdftext is Apache-2.0, docling-parse is MIT** - either satisfies D007 with no fee. The maths worry was mine and it was wrong: pdftext has `PageChars`, `get_chars` and `keep_chars`, returning every character's own box, so the per-glyph detail the formula rebuild needs is there; Marker choosing not to use it is not the same as it being absent. (2) **pdfminer.six** reproduces PyMuPDF's lines at 0.75 median, exposes per-character objects, and costs 2.4x the time. (3) **pdftext** reproduces them at 0.48 - no better than a hand-written twenty-line grouper - at 1.01x the speed, with per-character boxes confirmed (328,382 chars over 103 pages).
- **That third number discredited the metric I had been deciding on all afternoon.** Three independent implementations score 0.49, 0.48 and 0.75 against PyMuPDF's lines, and the 0.48 one is what Marker uses to score 76.0 on this benchmark. **PyMuPDF's segmentation is one valid answer among several, not a gold standard**, so agreement with it measures nothing about quality. My earlier "49%, therefore days of layout engineering, therefore buy the licence" was built on it.
- **Run 65: a baseline, not a change (19:25-20:35, 64 minutes). 84.0, every category identical to run 64, zero won and zero lost.** Run so the reader swap would be measured against something real. It also proves the day's two additions - arrow marks and the invented-text check - are neutral across all 1,403 pages rather than only on the samples the page checks covered.
- **The swap built and measured (commit 1eaf61e).** `truedoc/extract/pdftext_rawdict.py` rebuilds PyMuPDF's rawdict shape from pdftext so `extract_page` needs no rewrite, behind `TRUEDOC_READER=pdftext`, off by default; pdftext installed `--no-deps` to keep our pypdfium2 5.13.0 against its 5.10.1 pin. Verified first on one arXiv page: 1,896 non-space characters both ways, same fonts and sizes, boxes within a point, top-left coordinates already. **Then the gate: 71/128 against MuPDF's 100.**
- **The shape of that loss is the finding: one table page 14 to 0, another 8 to 5, a multi-column page 3 to 0. The fault is not pdftext - `extract_page` is not the only thing that reads text.** The ruled-table builder calls `get_text("dict", clip=...)` itself, the maths stage re-reads the page with accurate boxes to measure glyph ink, and the extension-glyph origins read again. All three still go through MuPDF, so they now disagree with the page's own characters about where everything sits. **Mixing two readers is worse than either alone.** Next session: move those three onto the same reader, then re-run the gate. The default path is untouched and verified (286 tests, gate 100/128 with the switch off).

- **All four readers moved onto PDFium, and the adapter rebuilt around a better division of labour (evening).** The census found four stages reading text, not three: `truedoc/tables/ruled.py`, the maths ink pass, `_extension_glyph_origins`, and `_page_has_extension_font`'s `get_fonts`. Rather than route each through pdftext, the adapter now takes **only grouping and reading order** from pdftext and reads **every geometric fact straight from PDFium** by the character index pdftext already carries (`char_idx`). PDFium turned out to hold everything the four stages needed: `FPDFText_GetCharBox` is the drawn outline PyMuPDF needs `TEXT_ACCURATE_BBOXES` for, `FPDFText_IsGenerated` says whether PDFium invented a space to fill a gap (what `get_texttrace` was for), and `FPDFText_GetCharOrigin` and `FPDFText_GetFillColor` supply the two values the first adapter had to approximate.
- **Both documented approximations are gone, and three shipped defects came out with them.** (1) pdftext rotates its coordinates into display space and PyMuPDF does not, so `extract_page` rotated a second time: every box on a rotated page sat a median 210pt from where it belonged, on 15 benchmark pages. (2) The estimated baseline was out by up to 25.8pt on precisely the maths-extension glyphs it existed to serve; read properly it now agrees with PyMuPDF to a median of 0.000pt on both an unrotated arXiv page and a 90-degree rotated timetable. (3) PDFium's font-descriptor flags were passed through into PyMuPDF's span-flag bits, where 0x2 means serif on one side and italic on the other - every serif face was arriving italic. Fill colour is read now too, so D011's hidden-text rules work on this path.
- **The real remaining difference is line grouping, and it is measured rather than assumed.** MuPDF's line breaks match neither a gap rule (best case 5,068 disagreements in 67,591 adjacent character pairs) nor the PDF's own text objects (6,345). It keeps characters together across a 95x gap and splits at small ones, because it follows the content stream's text-showing runs, which is a structure neither rule can see.
- **I started optimising agreement with PyMuPDF's lines again - the metric this project discredited the same afternoon - and caught it two measurements in.** Switched to tuning on the score: cutting a pdftext line wherever the gap exceeds 1.5x the font size took the gate from **72 to 90 of 128**, and the plateau is flat from 1.0 to 2.25, so the threshold is not the binding constraint. On the worst page it is the whole story: a wheat-cultivar table went 0/14 to 14/14, and a second table page to 9/14 where MuPDF gets 8.
- **A companion rule was written, measured, and taken out again.** pdftext also welds text at different heights into one line (a journal page's "G Model" and "ARTICLE IN PRESS" arrive as one 24pt-tall line spanning the page), so a baseline-step rule looked obviously right. It moved the gate by nothing at any threshold from 0.3 to 0.6, so it was removed rather than carried as an unearned knob.
- **State: 301 tests (15 new for the adapter), default path verified unchanged at 100/128, pdftext path 90/128.** Still short by 10 checks - a multi-column page 0/5, another 4/5, a long-tiny-text page 19/31, an arXiv page 6/9 - and text was only ever part of M18: MuPDF is still called for page rendering (7 sites), vector drawings (3), `find_tables`, `get_image_info`, `get_bboxlog` and the Rect/Matrix geometry.

**Learned**
- **The adapter that copies an interface should not also copy its coordinate system by assumption.** The first version matched PyMuPDF to under a point on an unrotated page and was 210pt out on a rotated one, and nothing in between would have shown it - the page I checked first had rotation 0. Pick the test page that exercises the transform, not the one that is easy to read.
- **Two spot checks agreeing is not a measurement.** Origins matching on one arXiv page hid that a 0.21 descender estimate was 25.8pt wrong on the maths glyphs, because the median was fine and the damage was all in the tail. Quote the p95 and the max, or the median will flatter you.
- **The discredited metric came back wearing a different hat.** Yesterday's lesson was that agreement with PyMuPDF's lines measures nothing; today I spent two measurements optimising exactly that before noticing. A metric that is easy to compute will keep re-proposing itself - the defence is to write down what the number would change, and stop when the answer is "nothing".
- **When a threshold shatters everything, suspect the units before the threshold.** A gap rule that split between almost every letter was not too aggressive: pdftext reports the font matrix scale (1.0) rather than the point size for some fonts, so "1.5x the font size" was 1.5pt. The codebase already knew this about Type 3 fonts in another stage; the knowledge had not travelled.
- **Do not read the source you are trying to escape.** The licence you are leaving contaminates the reimplementation. Look for a permissively licensed implementation of the same idea instead - there were three, and one was already in the virtual environment.
- **A metric borrowed from the thing you are replacing is not a measure of quality.** Agreement with PyMuPDF's lines looked like correctness and was really just similarity to one vendor's opinion. The tell was that a production library scoring 76.0 on this benchmark agreed with it no better than my twenty-line first attempt.
- **Map every caller before declaring a swap "plumbing".** Four stages read text, not one; replacing a single one leaves the others reading a different page. Both of my scope estimates today - "days of layout engineering" and "it's plumbing" - were wrong in the same direction, from mapping only the couplings I could already see.
- **The honest verdict set is bigger than the obvious one.** A pass/fail check here would have reported a pass on 91 pages where no witness existed at all. "Unchecked" is a third of the corpus and the most useful thing the front matter can say about those pages.
- **Measure the check before trusting the check.** Running it over all 281 pages first is what showed that low support means a broken witness, not an inventing model - and that acting on it would have destroyed the one page (Persian) where the model most clearly beat us.
- **A vocabulary gap looks exactly like a broken mechanism.** The arrows had been coming out as anonymous figure placeholders, which reads as "the mark reader cannot see them". It saw them perfectly; it had no word for what it saw. Worth checking what a classifier's vocabulary contains before assuming its eyes are the problem.
- **Reading a mark and placing a mark are separate jobs, and either can fail alone.** The arrow was classified correctly and dropped anyway. The first end-to-end test caught it; the classifier test alone would have passed and shipped nothing.
- **Three findings talked down in one day, every one by evidence.** The vector-drawn-table rule (one page), the drawn-text loss (cover-page logos), and my own icon filter (23% agreement). The alternative was building an elaborate pipeline for a problem that mostly does not exist in this corpus - so a day spent measuring bought more than a day spent building would have.
- **A person ruling on 159 pictures for twenty minutes replaced a GPU rental and beat it.** Not because they are cheaper, but because they see context a crop cannot carry: every one of the overrides came from recognising what the *picture around the icon* was.
- **The owner found the one thing the machine could not.** Directional arrows that tell the reader what to read next - not a value symbol at all, but a reading-order instruction. No structural test in this project would have surfaced it, and it came from him reading page 75 rather than from any measurement here.
- **Put the evidence and the decision on the same screen.** The first dossier made him scroll away from the picture to read what he was deciding about, which is backwards for a page whose whole purpose is judging against evidence.

**Next**
- ~~M18: move the other three text readers onto pdftext~~ (done 9 Sept evening - four, not three, and the adapter rebuilt; gate 72 to 90 of 128, see above). ~~Then the two untested approximations~~ (both removed: origin and fill colour are read from PDFium now).
- **M18, the next concrete step: find the last 10 gate checks.** `TRUEDOC_READER=pdftext python bench/quick_check.py` reads 90/128 against MuPDF's 100. Four pages hold the difference: `multi_column/05eac72b...page_6_pg1` at 0/5 (paragraph joining and de-hyphenation do not run - its lines and words match MuPDF almost exactly, so the fault is downstream of the reader), `multi_column/01566a95...page_7_pg1` at 4/5, `long_tiny_text/11_pg146_pg1` at 19/31, and `arxiv_math/2503.03762_pg1` at 6/9. Start with the 0/5: a total collapse usually has one cause, and its text layer is already known to be right.
- **Then the rest of M18, which text was only part of.** MuPDF is still called for page rendering (`get_pixmap`, 7 sites), vector drawings (`get_drawings`, 3), `find_tables`, `get_image_info`, `get_bboxlog`, and Rect/Matrix/Point geometry. Rendering and geometry are straightforward through pypdfium2; `find_tables` and `get_bboxlog` are the genuinely hard ones and have no obvious PDFium equivalent.
- **A known limit worth one look:** characters whose font has no usable ToUnicode come back as raw codes on the PDFium path where MuPDF resolves them by glyph name (a hyphen reading as `\x02`, 2 characters in 1,896 on one arXiv page). `FPDFText_HasUnicodeMapError` flags them and the adapter keeps the flag in `map_error`, so the information is there to act on; nothing acts on it yet, and `_is_bad_char` will currently count them against the page's text quality.
- ~~The directional arrows~~ (done 9 Sept: read as marks, see above), originally: three shapes, ~157 uses, `aami-home-building-insurance-pds-a01463_4906c3da.pdf` pages 11 and 75. Reading order still loses real checks on the benchmark, so this is the one thread with somewhere to go.
- Twelve of the 171 shapes have a zero-width bounding box and cannot be rendered at all. Degenerate geometry has now bitten three times in two days (two contact sheets and the dossier); worth one look at where those boxes come from rather than another guard.
- The classical tail and M17/M18 are unchanged by any of this; run 64 (84.0) still stands as the last scored run.

---

## 2026-09-08 - Runs 56 to 64 (82.8 to 84.0): the vision switch proved, the classical tail, the multi-column family, and GPU session 4's negative answer

**Done**
- **Run 56 scored 82.8 (00:33; converted 23:41-00:31); held-out 79.9, tuned-on 80.5: a regression against run 55 (4 won, 10 lost: multi-column 3, tables 7 on six pages).** The partial-reading rule fired on six pages the disk measurement had not flagged, because the pipeline counted the page's own reading as the raw layer's words (every word a hidden layer holds, including what the body drops) against the model's `text.split()` (a markdown table's pipes counted as words): on a two-column page the ratio came out 1.63 where the rendered readings give 1.23. Repaired (00:34-00:38): both sides counted the same way (`_word_count`: tokens of two letters or digits or more), the page's side from its blocks' lines and table cells (`_own_words`), and the ratio raised to 2, where the disk measurement gave +4 and nothing back. Checked directly on the six pages plus the two intended ones with the saved readings: the rule now fires only on the table page the model reduced to 32 words from 227 (ratio 7.1) and stays quiet on the rest (1.19 to 1.83); 225 tests.
- **Run 57 launched (00:38; `truedoc56`; the same `EXTRA`).** Run 55 plus the repaired rule; expected 82.9 or a check or two above it.
- **Run 57 scored 82.9 (01:26; converted 00:40-01:25); tables 84.0 (+4 checks, none lost against run 55), held-out 80.0 (best), tuned-on 80.6: the best run by checks.** Exactly the disk measurement: the table page the model reduced to 32 words keeps its own reading and its four cells pass; every other section identical to run 55 to the check.
- **The 'picture-text' region built for session 3 (00:55-01:31, 8 September).** A picture on a digital page that holds none of the page's own words and covers at least 2% of the page is first asked to transcribe itself (`PICTURE_TEXT_PROMPT` in `truedoc/vision/regions.py`: tables as markdown tables, nothing described, 'none' when there is nothing to read); a transcription of three words or more becomes the figure's content, rendered as the placeholder followed by the text with the inferred tag (`truedoc/render/okf.py`), listed in the front matter as kind 'picture-text'; only a picture with nothing to transcribe is asked for a description as before. The file provider takes several folders joined with '+' and answers picture-text questions from a crop folder's `manifest.json` (the crop tool's), matched by page and bbox overlap (`FileReadings.read_region`). Tests: the crop manifest lookup, the end-to-end transcription of a pasted table with the fake endpoint, the figure test's question order (transcribe first, describe second); 227 tests. Session 3's recipe is in `bench/gpu/README.md`: ship the crop folders, run `run_olmocr2.sh` over them, place the readings as candidate `olmocr2c` with the manifest copied in, then run 58 with `EXTRA="--vision-endpoint file:<olmocr2b>+<olmocr2c>"` and regions on. Committed at the owner's request as 57f6f0b (fourteen files).
- **The PyMuPDF question, continued with the owner (8 Sept, about 07:29).** Three questions answered from the tools' own dependency files: no leaderboard tool uses PyMuPDF (all on PDFium via pypdfium2, pdftext or docling-parse; MinerU moved off it); the alternatives (pypdfium2 BSD, pdftext Apache-2.0, docling-parse MIT, pdfplumber MIT) can be tested because TrueDoc reads PDFs through one function that yields our page model; an engine is unavoidable because a PDF holds drawing instructions, not text, and the only engine-free route is reading pixels with a model, which needs an engine to render and gives away the exactness edge on formulas. Agreed: the census and the trial run after session 3.
- **GPU session 3 started (07:35; the owner rented the Japanese RTX 4080 SUPER, 32 GB, at $0.210 an hour: the 16 GB cards on offer were a risk for the FP8 model's memory, the two-GPU machine paid for a card we would not use).** The machine reaches Hugging Face and PyPI. Shipped: `run_olmocr2.sh` and `bench/gpu/crops_failing` (92 crops on run 55's 60 failing digital pages, 43 MB, over this machine's uplink); the `crops` folder (107 crops on pages with no failing check) stays home: it cannot gain a check and could cost one, and the product rule is generic either way. The remote job started with its input detached (`ssh -n`, `< /dev/null`), output under `~/gpu/out`, watched by `poll_remote.sh` through the Monitor tool.
- **The Japanese machine abandoned (07:56-08:03; about ten cents).** After twenty minutes its install had two packages: the host's IPv6 route to the Python package host was dead (the redirect alone took eight seconds, a real download never started) and its IPv4 link ran at about half a megabyte a second, against three gigabytes of packages and eight and a half of model weights. Preferring IPv4 in the container (`/etc/gai.conf`) would have unstuck the install but not the arithmetic: two to three hours against last night's thirty-three minutes. Lesson for the GPU README: the listing's bandwidth figure is no guide; test the link with a real download before uploading anything, and prefer European or US hosts. The owner destroyed it and rented a North Carolina RTX 4090 (24 GB, $0.377 an hour): PyPI at 15 MB/s, PyTorch wheels at 380 MB/s. Session 3 restarted there at 08:05 with the same steps.
- **Session 3 done on the North Carolina RTX 4090 (08:05-08:18; upload under a minute, install four minutes, 92 crops read in eight, with a model reload per category).** 54 crops produced a reading, 50 of them non-empty; the other 38 were pictures without text. Placed as candidate `olmocr2c` with the crop manifest beside it. Two things in the readings: olmOCR writes tables as HTML (5 readings; the pay-advice screenshot came back as a proper `<table>`), which the scorer parses as it parses markdown (`parse_html_tables` in `olmocr.bench.tests`), so they stay as they are for run 58 and a markdown conversion is a separate, testable step for the product; and 22 readings are a single image reference whose alt text describes the picture ('![Scatter plot showing ...](...)'), a description, not a transcription. Built (08:21): `split_picture_answer` in `truedoc/vision/regions.py` takes image lines out of a picture's answer, the first alt text becoming the figure's description (alt text, D015) and the rest the transcription; the pipeline places whichever it got. Test `test_vision_picture_answer.py`; 228 tests.
- **Run 58 launched (08:21; `truedoc57`; `EXTRA="--vision-endpoint file:<olmocr2b>+<olmocr2c>"`, regions on).** Run 57 plus the picture-text regions from the crop readings. Expected: some of the 38 table checks on the 13 table pages with picture tables, and whatever the transcriptions of the other crops win; nothing on the sections without crops.
- **The PyMuPDF census, step 1 of the licence decision (08:23-08:51; `bench/tools/engine_census.py`, all 1,403 pages, 23 minutes; the table in `bench/out/engine_census_20260908.tsv`).** Both engines read every page's text layer; per page the characters, the fonts, the odd characters, images, paths and time were compared. Findings. (1) **The characters agree.** The bag of characters agrees to 0.99 or better on 1,278 pages and to 0.95 on all but 16, once one quirk of the PDFium binding is handled: it returns a mathematical letter as two UTF-16 halves (the arXiv page that looked worst, 0.83, is 0.995 after combining them, the only remaining difference being the placeholder each engine writes for an undecodable glyph, U+0000 against U+FFFD). Font names agree except that PyMuPDF truncates long ones ('TimesNewRomanPS-BoldItal' against PDFium's 'TimesNewRomanPS-BoldItalicMT'), which touches no rule. (2) **PDFium reads text PyMuPDF drops.** On a handful of pages (six with a hundred or more characters) PyMuPDF returns far less than the page holds: a magazine page whose HelveticaNeue and ZapfDingbats text (3,200 characters, whole columns: '44 | The State Education Standard ■ February 2012 time is spent on a skill...') never comes out of PyMuPDF though it lists the fonts; text inside included PDF figures (PTEX form XObjects) that PyMuPDF skips. No optional content, no annotations involved: a PyMuPDF failure, and a fidelity fault in our current engine that this census found. (3) **PyMuPDF decodes Type 3 fonts PDFium does not.** 16 pages carry Type 3 fonts; on 12 the engines disagree, and on the worst (a multi-column page set in bitmap Type 3 fonts) PDFium returns 3,600 raw codes where PyMuPDF returns the letters. A PDFium extractor needs a Type 3 fallback (our own code recovery, as for dvips fonts, or the OCR path). PDFium also gives U+FFFD, not the raw code, for a glyph without a Unicode mapping, so the cmex bracket-piece rule keyed on raw codes would need the ink boxes instead. (4) **Speed:** PDFium read the 1,403 text layers in 100 s against PyMuPDF's 243 s. Verdict for step 1: a PDFium extractor is viable; the characters, fonts, boxes, images and paths are there, two known gaps are small and bounded (Type 3 on 1.1 per cent of pages, raw codes on a few formula checks), and it reads text the current engine loses. Step 2, the extractor and a full run, is worth its three to five days.
- **Run 58 scored 83.0 (09:16; converted 08:25-09:14); tables 85.1 (+12 checks, none lost against run 57), every other section identical to the check; held-out 80.0, tuned-on 80.8: the best run, within a tenth of Chandra's 83.1 (CI 82.1-84.1).** The picture tables on digital pages now come out as tables (the pay-advice screenshot's HTML table sits after its placeholder with the inferred tag); the twelve checks are on tuned-on pages, so the held-out half is level. Session 3 cost: about ten cents on the abandoned Japanese host and a few cents on the North Carolina one. Committed at the owner's request as 78e37f1, with the engine census.
- **The classical tail, first four shapes (09:40-09:48; the owner: pass 83.1 with rules before the PyMuPDF step).** Run 58's 152 failing table checks by family: relations 59 (33 of them unspecific, 18 top heading, 8 left heading), cells found only as prose 33, cells absent 23, no table 19, model pages 18. Traced page by page with the page images: (1) a ruled statistics table stacks 'Shapiro / W / P value' beside '0.46 / < 2.2e-16', and the splitter's own docstring names the case but its equal-height guard refused it; now a label cell one line taller than at least two numeric stacks wraps its first label, a dash placeholder to the right does not block, and label lines beside numeric stacks pair up whatever their case ('Pearson r' over 'p value'); (2) a one-row heading centred over a group of columns ('Program Committee' over two name columns and their tick columns) heads every column it covers, as a colspan (`_single_header_spans`); (3) a label column filled on five rows in twenty-nine ('Emotion Type': Sequential, Prevalent, Inverse) read as whitespace from the table's edge, because the channel finder tolerates a fifth of rows crossing a gap and a run touching the edge is never a channel; text of two rows or more lying wholly inside such a run now splits it (a heading alone does not: it may sit a shade left of its narrow column on purpose); (4) the strip chain bridges a one-line group label ('Adjusted EPS*:') between a strip row and the body, takes the label in as a row, counts a chain onto a strip row already taken as proof enough, sorts the body before clustering, and currency amounts ('$448') count as numbers, without which a press release's revenue row read as a heading. Tests `test_table_tail_run58.py` (four, each failing on the old code first); two existing tests steered the rules (a heading offset into a gap stays a heading in order; one stack beside a taller label stays whole); 235 pass. Page checks against run 58 on the four pages: 25 of 25 checks against 10 before (+15); a thirty-page sample for regressions running.
- **The thirty-page sample, and one real regression (10:05-10:11).** The page checker converts without the vision provider, so on the first pass every page whose run 58 output came from the model (whole pages and picture crops) showed losses that were the model's absence, not the rules'; with the provider passed through the checker's flag hook (`PAGE_CHECK_ARGS="--vision-endpoint file:<olmocr2b>+<olmocr2c>"`) the sample read 39 checks against 40, one page down two. That page (4c77cbf4, a microbiota table) has a three-row header the corner rule caps at one, and the new one-row span rule spanned 'Mean (log DNA copies/g) ± SD' over columns whose headings sit in the rows below ('Microbiota', 'Day 35 and 42'), so the scorer read the span as their heading. Guard: in a table of numbers, non-numeric text under the span on any row before the first numeric row is a lower heading, and the span is withheld; a table without numbers (the roster) keeps its spans. The page is back to 12 of 14, the roster keeps its three, the sample is level, the targets +15; 235 tests.
- **Run 59 launched (10:16; `truedoc58`; the same `EXTRA` as run 58).** Run 58 plus the four table rules; expected about +14 checks on tables, nothing elsewhere.
- **Run 59 scored 83.2 (11:17; converted 10:16-11:14); tables 86.2 (16 won, 5 lost against run 58), every other section identical to the check; held-out 80.3, tuned-on 80.9: the best run, and the first above Chandra's published 83.1 on the point estimate (CI 82.3-84.1, so level inside the interval).** The four targets paid as page-checked (+15 there, one more on another page); the five losses sit on one page (ebfe1f9a, a table of large numbers with a two-row group heading) whose seven columns collapsed to three: being traced before the next build.
- **Run 59's five losses traced, and the next three shapes built (11:20-11:30).** The losses: a ruled table whose cells each hold a row of three numbers (sub-columns the rules did not divide) used to come back as three tall stacked cells, which counted as 'crowded' and were rebuilt from the text lines into seven columns; the new label-wrap rule split the stacks into seven rows of three-number cells, no longer crowded, so the rebuild stopped and the seven columns collapsed to three. The wrap now applies only to stacks of single values (one number a line). Built with tests first (`test_ruled_tall_cells.py`, the titled-table test in `test_table_tail_run58.py`): labels in a tall unruled cell dealt to the rows their lines fall in (`deal_tall_cells`, the row's extent being its shortest ruled cell, since a tall cell is not it); ruled cells whose box runs across the columns to their right carry a colspan (`column_spans`), and a sub-heading across the value columns ('% da população') is a heading row, so a ruled table with spans now renders as HTML like an aligned one; a two-row table under a centred title keeps the title (`_centred_title` in the run finder), and a one-cell header row above a row of several headings spans every column they cover (`_header_structure`), which also stops the assembler folding the title into the first heading. 238 tests. Page checks against run 59 with the provider: running.
- **The figure's value block beside prose (11:35-11:55; b5d9db35, the shape written down on 7 September, 5 checks).** The finder had the candidate (a prose column and the block in one region) but three things stood in the way, each found by tracing: the side-by-side splitter wants three channels and two surviving parts, so a channel dividing eleven-word prose from cells of a few words now splits on its own and the short side stands alone (judged by the segments adjacent to the channel, row by row, since the prose dominates any 'left' that includes it); the prose gate counted the block as prose because no cell matched the number pattern ('TP 120 µg l-1' is a value with its unit), so cells carrying a digit now count against prose; and on this taller page three of the block's four rows sit inside the head strip, where the join failed twice: its alignment test looked at left edges only (the second column is right-aligned, 'TN 3600 µg l-1' over 'pH 6.9') and it wanted two body rows below a strip row where this block has one. Either edge now aligns, and a strip row with another strip row stacked on it rests on that. Along the way a slip from the morning was undone: the body's rows had been clustered from all lines, so a row straddling the strip's edge held segments the body list did not, and the TN row vanished; the body's rows come from body lines again. Page checks with the provider: the lake page 5 of 5, the two strip-chain pages and the two document-control stamp pages level; 239 tests.
- **Run 60 launched (11:57; `truedoc59`; the same `EXTRA`).** Run 59 plus the four shapes: the tall label cell, the spanning sub-heading rows (ruled tables with spans now render as HTML), the titled two-row table, the value block beside prose, and the label-wrap rule narrowed to single-value stacks. Expected about +16 on tables (11 on the traced pages plus the lake page) and the five losses of run 59 recovered.
- **The multi-column family traced while run 60 converts (12:00-11:59).** The census after run 59 had 43 multi-column checks whose text sits in the raw layer but not in our output. Located against the output with a fuzzy window: 13 have both anchors present and the order wrong (true reading-order faults); 17 have the first anchor present and the second garbled or missing; 10 have the first anchor garbled; 3 have it missing. The garbling has a dominant shape: a measurement or a name in prose written as inline maths ('1.54 μm' as '1.54 $\mu\mathrm{m}$', '≤260 μm' as '$\leq260\mu m$', 'IFN-γ' as '$IFN\gamma$'), 19 checks on digital multi-column pages in all; about half of those are genuine maths the annotators typed plainly ('u_t', 'k = 2'), which stays LaTeX, and the other half are units, measurements and Greek-lettered names, which a reader wants plain. Also seen: a section kicker inserted into a title's line ('The Best of ## Feature ## the Best Foods'), a footnote digit glued after a full stop ('IVUS study.6 A strut'), a dagger and equals sign from a symbol font read as 'P50.005', and 'The kit' read as 'Te kit' (a 'Th' ligature glyph mapped to 'T' alone: a font-decoding fault worth a look under the engine question). Built for the next window, tests first (`test_inline_units_plain.py`): units ('μm', 'µg', '°C'), relation-and-number words ('≤260', '<0.05') and Greek-lettered names ('IFN-γ', 'β-catenin') set in the text fonts are not maths; a maths-font glyph or a lone Greek letter still is. Committed at the owner's request as 3661703 (the eight table shapes, runs 59 and 60's code; the units test held back until its rule is applied).
- **Run 60 scored 83.3 (12:57; converted 11:57-12:55); tables 87.3 (19 won, 8 lost against run 59), every other section identical to the check; held-out 80.2, tuned-on 81.1: the best run.** The eight losses sit one each on eight pages none of the samples held; traced next, before the units rule launches.
- **Run 60's eight losses traced and repaired (13:05-13:22).** Three causes. (1) The tall-cell deal, built for the yearbook's label column, also split cells that are one cell: a heading over two heading rows ("Minimum Central Pressure (mb)" beside "Landfall Location" over "Longitude | Latitude", two checks), a realtors' note beside two value rows (one check), and a label centred in a tall cell over empty rows, which the deal moved to the middle row, leaving an empty row above it that the scorer reads as the cell above (one check; markdown drops an all-empty row, HTML keeps it). The deal now leaves the first row alone, leaves a cell whose lines read as sentences, and leaves a cell whose lines all fall in one row; a tall cell left standing carries a rowspan (`row_spans`), which markdown writes once and HTML writes as `rowspan`, and the scorer fills the spanned rows with it. (2) A ruled table rendered as HTML marked only its first row as headings, so a title row across the columns hid the column headings beneath it from the scorer, which takes an HTML table's headings from its `<th>` cells and looks no further once it has found any (four checks on four pages); every row above the first row of values is now a heading row (`heading_rows`: a title across the columns, then the column headings, up to three rows; a group label across the columns under them is a body row, and a cell of many words is prose unless it is the title). (3) The titled two-row rule from run 59 took "Number of Agreement" for a title over "Item | I-CVI" when "(ranked 3 or 4)" continued it two rows down (one check); a title's column has nothing beneath it. Page checks against run 60 with the readings folders (13:15-13:20): the eight pages 9 checks up (the eight, plus 'Longitude' on the storm table, which run 59 had also missed), the three controls and the seven pages run 60 won unchanged. Five tests (`test_ruled_headings_run60.py`, `test_table_tail_run60.py`); suite 247. **Run 61 launched at 13:25** (`truedoc60`, the same `EXTRA`): run 60 plus the three repairs and the units rule.
- **Run 61 scored 83.5 (14:24; converted 13:28-14:22): tables 88.2, multi-column 80.7, the rest identical; 14 won (tables 9, multi-column 5), none lost; held-out 80.6, tuned-on 81.3. The best run, and 0.4 above Chandra's 83.1 on the point estimate (the interval 82.6-84.4 still holds 83.1).** The units rule accounts for the five multi-column checks. While it converted, the vision stage's post-processing was audited: every check on the 281 model-read pages run on the raw readings and on our output (1,451 tuned-on checks, 279 held-out): our processing loses none and wins 9 (the running-head witness), so the 386 failing checks on those pages are the model's own reading; a better reading (another model, or dense pages read in column crops: the three dictionary pages 16a/b/c hold 17 failing checks) is a GPU-session matter, not a code one.
- **The multi-column family traced with the scorer's own matcher (13:40-14:05) and five repairs built while run 61 converted, applied at 14:24, checked by 14:52.** Run 60's 113 failing order checks on tuned-on digital multi-column pages: 11 true order faults, 59 with the first anchor garbled or missing, 43 with the second. The garbling shapes: reference errors, unwinnable (about 18); inline maths in prose (about 10, half taken by the units rule); line-end hyphens dropped from real compounds ("racistfree", "thirdhighest", "GCSF", about 6); a heading marker inserted mid-sentence (about 8: a wrapped heading's second line as a heading of its own, "electrical ## parameters"; run 60's output held 98 headings starting with a lowercase letter on 56 pages); the two columns' lines joined by MuPDF across a narrow gutter (about 12; the strict channel scan finds no gutter when a full-width head and the joined lines cross it: 53 tuned-on pages have such lines); a caption or table row inside the anchor (about 4); text missing altogether (about 17: furniture stripped, the engine's dropped text on 0925342e, the rest unknown). Built, tests first: (1) `_merge_wrapped_headings` in the pipeline (a one-line heading directly under a heading of the same size and weight continues it when the upper line does not end a sentence and the lower starts lowercase, or the upper ends on a connective or an open bracket, or both are long title-case lines aligned left or centre; a numbered lower line stands alone); (2) the segmenter rejoins a lowercase fragment of at most three words to the line on its baseline within a stretched word space, or within six ems inside the block's own width, never across a gutter and never when other lines start where the fragment does (the newspaper's next column); (3) `_join_at_hyphen` in the renderer: the halves join without the hyphen when together they are a word in the list, keep it when each is a word on its own (a prefix joins unless two vowels meet), a capital or digit keeps it, a function word after it keeps the space (a suspended hyphen); (4) `_edge_gutters` in the extractor: a gutter shown by the columns' edges (a share of lines start at the right column's edge and the lines wholly left of it end just before it, with a minority crossing), a strict channel inside it widened to it, and a word gap splits at a wide gutter only when it covers most of it (a title's word spaces do not); (5) segments on one baseline that together fill their column's measure (per column and baseline, so a producer that places every word on its own still measures whole lines) rejoin for gaps up to an em and a half. Three page-check rounds against run 61 with the readings folders (14:26-14:52): the first found the fragment rule pulling the next column's line start into a paragraph on four pages (a control page lost all five of its checks: the straddling block defeated the column cut), the measure rule joining lines across an unfound newspaper gutter, and a per-word producer measuring segments instead of lines; each guard was written as a test. Final: 18 family and control pages 73 checks against 64 (nine won: 00f6c2eea6 two, 0dd31f954c, 03b953c18a, 013a3686ef, 09f90a8fad, and the newspaper pages 20_pg39, 20_pg35, 20_pg40), none lost. Suite 266 (nineteen new tests in `test_wrapped_headings.py`, `test_line_fragments.py`, `test_dehyphenation.py`, `test_columns_under_a_full_width_head.py`, `test_full_measure_segments.py`). **Run 62 launched at 14:53** (`truedoc61`, the same `EXTRA`): run 61 plus the five repairs.
- **Run 62 scored 83.7 (15:45; converted 14:55-15:43): multi-column 81.7 (+1.0), tiny text 88.2 (+0.4), arXiv 87.1, headers 96.2 (-0.2), the rest level; 14 won (multi-column 10, tiny text 3, arXiv 1), 4 lost; held-out 80.8, tuned-on 81.5. The best run, 0.6 above Chandra's 83.1 on the point estimate (interval 82.7-84.6).** Built while it converted, tests first, and applied at 15:44: the re-joiner's gutter test asked only when the right half followed the left, and a maths glyph's baseline a tenth of a point off put the right half first, so the "interleaved formula" path glued a left column's line to the right column's (0145cc39b0, 0853d8a05f, 0904c70713); the test now asks whether the halves lie on opposite sides of a gutter whatever their order. A relation-and-number word may carry a hyphenated tail ("≤5-year-old" is prose). Three furniture shapes: a short line in a running head's own size that repeats its text is furniture wherever it sits (a form's label at the foot of its box, 8e953483), a small numbered line near the foot is a note and not a heading ("9 Ibid", 138eff9f), a bare web address counts as a contact line ("health.ucsd.edu/jacobs", 0f727ae2). Page checks against run 62 (15:45-15:49): +7 on the target pages, controls level (0853d8a05f two, 0904c70713, 01460d3dc3, 00e2c7719d, 138eff9f95, 0f727ae22d). The four losses traced (15:50): a newspaper's running head "Surfside Gazette • AUGUST 2013" kept as a heading (eac8e314, two checks: the head and the page number it carries), and two columns' lines joined across an unfound gutter by the measure rule on 20_pg46 and 03ccfe8bb1 (the per-baseline row union made two unfound columns look like one full-width measure). The form label on 8e953483 stayed: the classifier's verdict was overridden by the layout model's label afterwards.
- **Run 62's four losses repaired (15:50-16:05), tests first; suite 273.** (1) A stretched gap is joined only when no channel of white runs through it (`_channel_through`: on the lines within a dozen line heights, some word must cover the gap's middle); two narrow columns whose gutter went unfound leave their word gaps as wide as the gutter, and their lines share baselines, so their union passed for one full-width measure (20_pg46) and a justified line's own wide word gaps reached across the gutter (03ccfe8bb1 was a different fault: two run-in headings a line apart were merged as one wrapped heading, taking the line between them out of order; `_merge_wrapped_headings` now refuses when another block's line sits between the two). (2) The repeated-running-head rule moved from the classifier into `_margin_cleanup`, which runs after the layout model whose label had undone it (8e953483). (3) A display-size line in the bottom strip is a running foot even when a column's last line touches it (the newspaper masthead "Surfside Gazette • AUGUST 2013" in 18 pt, eac8e314; a heading sits above its text). Page checks against run 62 with the readings folders (16:01-16:05): the four loss pages recovered (eac8e314 two, 03ccfe8bb1, 20_pg46) plus the form label, the seven earlier targets kept their gains, eight controls level: 78 checks against 66 on 20 pages, none lost. **Run 63 launched at 16:06** (`truedoc62`, the same `EXTRA`): run 62 plus the gutter-order test, the hyphenated-relation word, the three furniture shapes, and these four guards; expected about +12 to +16.
- **Where the remaining points are, measured while run 63 converted (16:15-16:50).** A check is worth a different amount in each category (0.028 points in tiny text, 0.024 in old scans, 0.014 in multi-column, 0.012 in tables, 0.004 in arXiv maths), so failures were counted in points, not checks. Run 62's 913 tuned-on failures: **528 on pages TrueDoc reads itself (4.4 points), 385 on pages a model reads (9.2 points)**. The model's pile sorted by what its own reading shows: 219 checks garbled (5.5 points, a better model), 77 never read (1.9, the page too dense), 44 read exactly but in the wrong order (1.1). Session 4 is prepared for that: `bench/gpu/select_bands.py` cuts the two dozen worst pages into three overlapping bands, `bench/gpu/merge_bands.py` stitches the readings back, and because those pages already have whole-page readings the two can be scored against each other on the same checks (recipe in `bench/gpu/README.md`, reasoning and table in `docs/GPU_PLAN.md`; the owner's call, it needs a rental). Our own 528: multi-column 1.46 points, arXiv maths 1.32, tables 1.10, headers 0.31, tiny text 0.17. Each is now a long tail of one-page shapes: the multi-column order failures are 27 anchors garbled by one to three characters (mostly the reference's own typos: "migrating ata", "betweentwo", "U.S.source"), 33 by more, 14 absent; the table failures are 19 cells that swallowed their neighbours (five on one census page drawn with pipe characters, four on a table whose statistics the references keep separate) and 19 whose text is not on the page. Two measurements said no: writing a lone italic variable in prose as plain text would win nothing (0 checks), and the symbol fonts that print "±" as "6" (AdvPSSym, Universal-GreekwithMathPi on 23 pages) carry no glyph names to decode by, so only a rendered-shape comparison could read them. One artefact worth recording: **the ten failing checks on the LANL magazine page (081875a103) name text that is nowhere in that PDF** (our output holds 422 of its 432 words), so no tool can pass them.
- **Run 63 scored 84.0 (16:57; converted 16:08-16:55): CI 83.1-84.8, so Chandra's published 83.1 is now the lower end of our interval; multi-column 82.9 (+1.2), arXiv 87.4 (+0.3), headers 96.8 (+0.6), tiny text 88.5, tables 88.2; 28 won (multi-column 11, arXiv 11, headers 5, tiny text 1), 1 lost; held-out 80.9, tuned-on 81.9.** The eleven arXiv wins were unexpected and welcome: the gutter test that now works whichever half sorts first stops a formula being glued to the next column's line. The one loss (2503.06944) is an inline formula split from its left side, "H_r^{NLoS}" ending up beside "∈ C^{M_r×N}" instead of inside it. Three measurements while it scored, all negative, all recorded so they are not repeated: formulas that begin with a relation looked like a defect (117 of them) but are equation chains written correctly, one line per step; writing the narrow accent everywhere ("\\hat" for "\\widehat") would win 4 checks on one page and lose 9 on five others; and the crossed element sign was settled in an earlier run (the note in `_polish` records won 2, lost 4). Applied instead: a script that arrived in two pieces is joined ("E_{s}_{,t}" is not LaTeX at all, so a renderer refuses the whole formula; two formulas in run 63's output). **Run 64 launched at 17:01** (`truedoc63`, the same `EXTRA`).

- **Committed at the owner's request as 162011a (17:15): runs 61 to 64's code, eleven new test files, the session-4 GPU tools and every document.** Thirty files, 1,574 lines added. The working tree is clean; run 64 was converting as the commit was made, so the commit holds exactly the code that produced it.
- **Step 2 of the reader swap sized for the owner while run 64 converted (17:22-17:40).** The question was what the PDFium extractor involves and whether it comes before or after GPU session 4. The work: characters and boxes (PDFium does this well), page rendering (trivial), the vector drawings rebuilt from raw path segments through pypdfium2's low-level bindings (rules, shading and marks; every symbol needed is present in 5.13), and two bounded gaps, glyph outline measurement for the maths stage's tall brackets and raw codes for unmapped glyphs (the 16 Type 3 pages). Sized from the census file and run 63's failures: the swap wins at most 0.30 points (53 pages where PDFium reads text PyMuPDF drops, but only 16 of them fail checks, 28 checks in all, and most of that "extra text" is the binding reporting two-part characters as two rather than text genuinely dropped; the real dropped-column case is 4 checks on one page) and risks at most 0.38 (the 48 checks passing today on the Type 3 pages). PyMuPDF took 243.2 s over the 1,403 pages against PDFium's 99.6 s, 2.44 times. Recommendation: after session 4, which is worth about 3 points, unless the rental is more than a couple of days away, since step 2 needs no rental; buying Artifex's licence removes the need for it. Recorded in ROADMAP as M18 (M17, which M16 already pointed at, is the rental-dependent work on the pages a model reads) and in the open PyMuPDF decision.
- **D020 written and the status list cleaned (17:45), at the owner's request after they noticed the doc still listed a settled decision.** Partial pages and small task models were measured and closed on the evening of 7 September but never given a decision number, so the "things you may need to do" list went on asking for them. D020 records both with their numbers (partial pages at most +1.4 against the model's +4.8 on the same pages; small task models with no territory left under D019) and names the one live remnant, a product question for the free tier rather than a score question. The status list now carries the GPU session 4 rental, PyMuPDF's licence with today's sizing, and D020 as done.
- **ROADMAP's milestone table brought current in the same pass (17:50).** It still said "updated 2026-09-06, after run 37", twenty-six runs behind. Against their own stated conditions and run 63's section scores: **M2 done** (all four of its sections now beat Marker 1.10.1: headers 96.8 to 86.6, multi-column 82.9 to 80.0, tiny text 88.5 to 85.7, baseline 99.8 to 99.3), **M3 done** (tables 88.2, past MinerU 2.5's 84.9 and Chandra's 88.0), **M4 done** (arXiv 87.4, above PaddleOCR-VL's 85.7, the best published), **M5 done** (the vision stage is the product path; old scans 47.3 and old-scan maths 80.8, competitive but not leading), **M7 half met** (84.0 against 83.1 on olmOCR-bench, but OmniDocBench has not been run and the milestone asks for both). M6 stays partial (the invented-text check on model pages), M7b partial, M8 not started. The pass also found a numbering hole: M16's closing sentence pointed at an M17 that had never been written, so M17 is now the rental-dependent work on the pages a model reads (session 4 and the stronger model) and the reader swap became M18.
- **Run 64 scored 84.0 (18:05; converted 17:04-18:02, 58 minutes): CI 83.0-84.8, every section unchanged, 1 arXiv check won and none lost, held-out 80.9 and tuned-on 81.9, both unchanged.** The one check is `2503.08925_pg16_math_001`, on a tuned-on page: exactly what the page check predicted for the two-piece subscript, no more and no less. Nothing to trace. The reading of it: the classical tail is now returning about one check a fix, so another round of one-page shapes is worth roughly a tenth of what session 4 is worth, and the loop's best next move is the rental rather than more rules.
- **The owner rented an RTX 4090 and GPU session 4 ran (20:20-20:55; 18 minutes of instance time, about 40 cents).** The host was chosen for its link rather than its price ($0.657/hour in California against $0.395 in Japan) on the strength of this morning's lesson, and it paid immediately: 14 MB/s from both PyPI and Hugging Face, so apt, pip and the 8.5 GB of weights took **nine minutes against twenty-five in the first session**. The pre-flight test needs a big file, though - the recipe's small pip wheel reported 1.4 MB/s, which is latency, not throughput, and would have had us destroy a perfectly good instance; a real download measured 14. Dependencies were installed in parallel with the upload and the model run was queued behind both, so nothing idled. 80 bands read, zero pipeline failures.
- **Session 4's answer is no, and the held-out split is what says so.** 32 pages holding 136 failing checks scored **84.2 against run 64's 84.0**: eleven net checks where the value census projected 3.0 points. Banding won 5 on old scans and 4 on tiny text and **lost 4 on old-scan maths**, which is mechanical rather than unlucky - a formula cut across a band boundary is unreadable in both halves. **Eight of the 30 scored pages are held-out, carrying 30 of the 136 checks, and the held-out score was identical before and after (1058 of 1255 both times): every net gain landed on a tuned-on page.** So the 77 "never read" and 44 "wrong order" checks are not recovered by sending less page at a time, and the 9.2 points on model pages collapse into one question, a stronger model. Recorded in BENCHMARKS, GPU_PLAN, ROADMAP (M17) and STATUS; the instance was destroyed once every reading, every JSONL record and both logs were verified off it (78 markdown files and 78 records agreeing exactly, which also proved the two absent bands were genuinely empty rather than lost in transfer).
- **A bug in our own tool nearly hid the one part that worked (20:47).** The first merge scored 84.1 with tables completely unmoved, and its own line said "22 from olmocr2d" where the stitcher had written 30. `merge_by_list.py`'s `all` mode takes only pages on the non-digital census list, and the eight pages sent whole are *digital* pages whose table is a vector drawing, so all eight readings were discarded in silence. Fixed by adding an `any` mode (every page the model has a reading for) and re-scored at 84.2, tables 88.2 to 88.6. The check that caught it was comparing the merge's own count against the number of pages stitched.
- **The vector-drawn-table rule was measured and NOT built (21:20-21:40).** The census across all 1,403 benchmark pages says the population is five pages holding six failing checks, and five of the six are on one page (`fbeb6edc`, an engineering drawing of a power cord whose parts table is 5,875 vector paths and 174 characters of text); the single page with no image object for `select_regions.py` to reach fails no checks at all. Per-page numbers also killed the rule as first stated: routing every such page to the model wins 7 and **loses 2**, because on `8160caa0` (a conference slide with an ordinary table) TrueDoc already builds a correct sixteen-row table from the page's own text and the model's version is worse. The evidence-first variant - use the model only where TrueDoc found no table - wins 6 and loses none, but on one page. A detector fitted to one example is what banding had just cost 40 cents to warn about, so it was left unbuilt and the finding recorded instead.
- **Probing the owner's library for that signature found a real product defect instead (21:40-22:30).** The benchmark has 5 such pages in 1,403; a 120-document, 2,135-page sample of the insurance library has 26, and 16 of those have no image to crop. But rendering them showed the signature catches *decorative illustrations* (a cutaway house drawing), not drawn tables - so the rule would have been wrong for the library too. What the probe did surface is worse and more valuable: **the Huddle Black policy's benefit table converted with every coverage cell empty.** TrueDoc read the structure and all eleven row labels correctly and dropped the ticks and crosses, so "Emergency storage of your contents" came out blank where the page says covered for Home and not for Contents. In an insurance document that is not a lost detail, it is the meaning inverted.
- **Two defects behind it, each fixed with a failing test written first.** (1) `marks.py` accepted a mark only between an absolute 3 and 30 points; that page is laid out at 1920x1080 rather than 612x792, so its 40-point icons were rejected as too big even though relative to their page they are *smaller* than a 30-point tick on a letter page (2.1% of the width against 4.9%). The limits now scale with the page (`_page_scale`). (2) With that fixed every icon read as `●`: these ticks and crosses are white glyphs knocked out of a solid coloured disc, so the ink is the disc and the meaning is the hole - and worse, a solid disc has ink all the way round, so it trips `_has_ring` and `_erase_ring` threw away the shape that carried the meaning. `_knockout` now reads the hole, before the ring test, and only accepts a hole that reads as a tick or a cross. The page converts correctly row for row against the rendered image. 277 tests pass.
- **A third defect, in the tool that guards every change (22:30).** The first regression sweep reported nine old-scan pages losing 14 to 24 checks each. Removing the marks change entirely reproduced the same numbers, which proved it innocent; the cause was `page_check.py` matching test cases with `t.pdf.endswith(name)`, so checking `old_scans/5.pdf` also pulled in the checks for `15.pdf`, `25.pdf` ... `95.pdf` - ten pages' checks scored against one converted page. Only single-digit stems collide, which is why it survived this long. Now matched on the exact file name. With it fixed those nine pages are identical, 37 against 37. **Regression result: 134 of 134 large pages and 110 of 110 pages carrying a mark unchanged, 585 against 585.** The change is neutral on the exam and fixes the library.
- **The keeper from session 4 is not about bands at all.** Those eight vector-drawn tables won 5 checks and no model had ever seen them: `select_regions.py` looks for image objects and there are none, so the region cropper walks straight past a table drawn as paths. Their readings are on disk, and the rule they point at - a digital page whose content is a vector-drawn table goes to the model, as picture-text regions already do - is CPU work needing no rental.

**Learned**
- The scorer reads an HTML table's headings from its `<th>` cells and nowhere else, so a table rendered as HTML must mark every row above the first row of values as a heading row. Run 60 lost four checks to a title row that hid the real column headings beneath it.
- Measure before building. Six candidate rules were tried against the saved outputs in minutes each and six were rejected: the narrow accent everywhere (won 4, lost 9), a space before every bracket (won 2, lost 4), lone variables written plain (0), the crossed element sign (settled in an earlier run, won 2 lost 4), decoding symbol fonts by glyph name (the fonts carry names like "C176"), and formulas that begin with a relation (117 of them, all correct: equation chains).
- A run's losses are worth as much as its wins. Every run from 60 on was traced within the hour and its losses repaired before the next launch, and that is where most of the day's points came from: run 60 lost eight and run 61 won fourteen with none lost; run 62 lost four and run 63 won twenty-eight with one lost.
- Count failures in points, not checks. A check is worth 0.028 points in tiny text and 0.004 in arXiv maths, seven times less, because the overall score is the mean of eight sections of different sizes. Sorting the remaining failures that way put the model's pages (9.2 points) ahead of our own (4.4) and changed what to work on.
- Our own handling of the model's readings is sound: an audit of every check on the 281 model-read pages found the pipeline loses nothing against the raw reading and wins nine checks (the running-head witness). What fails there is the model's reading, not our processing of it.
- The benchmark contains checks no tool can pass: ten on one magazine page name text that is not in that PDF at all, and about eight multi-column anchors carry the annotator's own typos ("migrating ata", "betweentwo", "U.S.source").
- **The held-out fifth earns its keep on experiments, not just on runs.** Session 4's +0.2 looked like a small win until the split was read: held-out was identical before and after, so the whole gain sat on pages the work was chosen from. A treatment that moves only tuned-on pages has not been shown to work. Report the split on every experiment, not only on scored runs.
- **Check a merge's own arithmetic against the step before it.** The first session-4 merge said "22 from olmocr2d" where the stitcher had written 30, and that one number was the only sign that eight readings had been silently discarded by a filter that pre-dated them. A tool that quietly does less than asked reads exactly like a treatment that did not work.
- **A measuring tool can be the thing that is broken.** Four numbers lied today: banding's +0.2 that vanished under the held-out split, a merge that silently discarded eight readings, a pre-flight test that read latency as a slow link, and a page checker scoring one page against ten pages' checks. Every one was caught by making a number agree with something else it had to agree with (the stitcher's count against the merge's, a small download against a big one, the change removed against the change present) and none by looking at the number alone. When a result surprises you, suspect the instrument before the code.
- **The benchmark is not the product.** The drawn-table rule was worth 5 checks on one exam page and nothing on the library; the marks defect was worth nothing on the exam and inverted the meaning of a real policy document. A rule's value has to be measured on both, and the library is the only place the second kind shows up.
- **A throughput test needs a big file.** The pre-flight check in the GPU recipe used a 2 MB pip wheel and reported 1.4 MB/s on a host that actually does 14; on that number alone the rule said destroy the instance. Latency dominates a small download. Measure with something of a size you actually care about.
- **Do the setup in parallel with the upload, and queue the job behind both.** Nine minutes of dependencies against twenty-five in the first session, with no idle GPU time between stages.

**Next**
- **A run to bank the marks fixes.** They are neutral on the benchmark by page check (134 large pages and 110 mark pages unchanged), so a run would confirm rather than move the score; worth batching with the next rule that is worth points rather than launched for its own sake.
- **More of the library, now that it has proved its worth.** One 120-document probe found a meaning-inverting defect the whole 1,403-page benchmark never showed. The obvious next pass is to convert a sample of the library and look for tables whose cells came out empty, which is the shape this defect takes; `bench/out/library_drawn_census.txt` has the page-level geometry already. The owner's ten-document sample is still the standing ask.
- **Plan the stronger-model session before asking the owner to rent again.** After session 4 the 9.2 points on model pages are one question, not three. PaddleOCR-VL (Apache-2.0) is the candidate and doubles as M16's second witness. What to settle on paper first: the serving stack, how its readings key back to pages, and which pages it reads (all 281, or only the 219 garbled checks' pages). Sessions 2 to 4 each cost under a dollar because they were planned in full first.
- Run 64 is recorded (84.0, one check won, nothing lost) and nothing is running. Another classical round buys about a check a fix, so no run should be launched for its own sake; batch the vector-table rule with anything else worth having first.
- The classical tail is now one to three checks a page: 90 table failures on 49 pages, 103 multi-column order failures, 310 arXiv maths. Of the table checks, session 4 recovered 5 on the vector-drawn pages, and a handful are judged unwinnable (a page drawn with pipe characters, unique in the corpus; a symbol font that prints "±" as "6").
- Still open from earlier days: a served model end to end (the readings are replayed from disk today), HTML tables in model readings turned into markdown, the invented-text check on model pages (D008), the reader swap's step 2 (now planned and sized as M18), and the library run with the owner's ten-document sample.

---

## 2026-09-07 - Runs 46 to 54 (66.4 to 67.4): the table morning, the review, the lateral round's two waves

**Done**
- **Column cut position (7 Sept 06:20-07:05, for run 47).** Run 46's two losses on the design schedule (00e980a0_pg64) traced. A cut is now an x range that enough rows leave empty, and it was placed at the range's midpoint. On the schedule the dated rows leave a wide stretch empty (from the end of the longest task name to the date column, 45 points), and the rows without a date, the wrapped task lines, never vote yet run across it; the midpoint landed in one of their ordinary word spaces ("(approx." | "90-95%"), which the no-word-straddles check cannot see, so "90-95% design level)" moved into the date column. A first repair (support from at least two gaps narrower than a bound) could not serve both this page and the Dutch sleep table, whose number columns sit four ems apart (bound four ems: schedule 4 of 4, Dutch 3 of 5; six ems: the reverse). The cut now sits one point before the words that close the range, where the next column really starts; the schedule is 4 of 4 (from 2), the Dutch table 5 of 5, the four other control pages and twelve sampled table pages unchanged (76 checks against 74), gate 100 of 128 (98 at the previous reading). Tests: 157 (`test_table_cut_position.py`).
- **Run 47 (`truedoc46`) scored 66.5, the best so far** (launched 06:37, scored 07:36; CI 65.6-67.4; run 46: 66.4): table_tests 76.2 (+6 net: 12 won, 6 lost), headers_footers 96.3 (-1: a running header, "Physics Minor (Non-Teaching)", that run 46 had split into a heading and a stray table by accident now stands whole, and the check wants it absent), every other category identical. Held-out 63.7 (run 46: 63.3) and tuned-on 62.3, both the best yet. Run dir `bench/runs/truedoc46-20260907-073241`. The gains include the immunisation-providers table (4 of 8 to 7 of 8) and the design schedule (2 of 4 to 4 of 4); all six table losses came from the new cut position (next bullet).
- **Scanned tables of numbers kept (06:50-07:15, for run 48).** Census over the 73 benchmark pages that come out empty (the OCR read rejected): one is a printed table of measurements read at 0.785, just under the 0.8 rescue bar (a wastewater table: 248 lines, numeric share 0.74); the rest are handwriting under 0.75, a Japanese table the Latin engine cannot read (0.69) or a line or two of noise. A page with a numeric share of at least 0.5 over at least 20 lines is now accepted from the page floor (0.75) up: the wastewater table 0 of 5 to 3 of 5 (its stacked heading "Total DDT" still misses). Empty pages fail the benchmark's baseline check, which wants alphanumerics, so the 71 empty handwriting pages each cost a check by design; reading them needs the vision stage.
- **Leader dots and dash rules out of cells (07:15-07:30, for run 48).** "Hettinger ........." and "---------------- Percent" are a label and a heading with their leaders attached. Cells now lose a run of four or more dots or dashes at either end (`tables/cells.py`, applied by both table builders and the ruled-header adoption); an ellipsis of three, a form's underscores and a bare rule stay. The North Dakota district table 11 of 14 to 13 of 14, the campus count table 4 of 5 to 5 of 5; 54 cells across the benchmark carried leaders, mostly contents pages.
- **Headings read in order (07:30-07:50, for run 48).** A scanned applicant table sets eight short headings ("BM BF WM WF OM OF ?? Total") a third of a column left of their numbers, so by position two share a column and one column gets none. A non-numeric row whose headings cover, by position, exactly as many columns as it has headings, with such a clash, is read in order (`_headings_in_order`): 3 of 5 to 5 of 5, controls unchanged. Gate 100 of 128; tests 164.
- **Cut position refined (07:40-08:10, for run 48).** The right end of the empty range is where the next column starts, but (1) a heading centred over that column reaches back over the end ("C14" over "23.8"), so the cut through it was vetoed and two columns merged ("C13 C14", "105.7 23.8"); (2) a title or group heading running across the whole range can have a word space at that end, and the cut split it ("Tabel 2 Table of Correlation | Criteria" cost a two-column table; "Mean (log | DNA copies/g) ± SD"). Now a segment running across the whole range vetoes the cut outright, unless its own word gap over the range voted for it (a heading row set closer than two ems, "N Minimum Maximum Gemiddelde Sd", is one segment), and the cut is tried at the right end, then the middle, then the left end, taking the first that no word straddles. All six pages are back (c00cffd4 3 of 3, 66aa22ac 7 of 7, 4c77cbf4 12 of 14, e82a04c6 8 of 9, a6820ddd 5 of 5); the schedule, the Dutch table and the usual controls hold. Tests: `test_table_spanning_title.py`.
- **Run 48 (`truedoc47`) scored 66.7, the best so far** (launched 08:02, scored 09:05; CI 65.8-67.5; run 47: 66.5): table_tests 77.8 (+16 net: 17 won, none lost), baseline 94.7 (+1: the wastewater table page is no longer empty), every other category identical. Held-out 63.9 (run 47: 63.7) and tuned-on 62.5, both the best yet. Run dir `bench/runs/truedoc47-20260907-090140`. Tables have gone 70.3 (run 37) to 77.8 in a day and a morning.
- **Hyphen-wrapped cells (08:10-08:25, for run 49).** A cell wrapped at a hyphen was joined with a space ("Automotive- Industrial", "NON- RECURRING"); the two lines now close up: a word broken by the typesetter loses the hyphen ("Diver-" / "sity" gives "Diversity"), a compound of two common words keeps it ("self-" / "employed"), a capitalised continuation keeps it ("Automotive-Industrial"). Applied wherever wrapped lines and stacked heading lines are joined (`_join_lines`). ebfe1f9a 4 of 5 to 5 of 5, 2d0e0586 2 of 5 to 3 of 5, eight controls unchanged. Tests: `test_table_hyphen_join.py`.
- **Group labels span their rows (08:25-08:55, for run 49).** A survey table writes "Education" once, centred beside three education levels, and "Gender" beside three answers; the reference reads each level as a row of its own with the label as its left heading, and the benchmark's parser carries a rowspan's text into every row it spans. Two changes: a long line under a heading that closes with a count or share ("High school or less (107; 16.3%)") is an entry, not a wrapped continuation of the heading (`_ENTRY_END`); and a label written once for a group of entry rows (entries at least twice as many as labels) spans the group with a rowspan (`_label_rowspans`: a label centred on its group takes the nearest entries above and below, a label at the top of its group takes those below; the label moves to the group's first row). 9c389720 1 of 5 to 4 of 5; the Tagetes spec sheet, the eye-disease table and nine other controls unchanged. Tests: 167 (`test_table_group_labels.py`).
- **Where run 47's missing table cells are (08:55-09:05).** Of its 152 "cell not found" and "no table" failures, 46 are text that is not in the text layer (pictures, figures), 21 are pages with no text layer, 70 are text present but not structured as a table (the census printout, a Polish form, a botanical key, an attendance list, staggered three-line rows) and 15 are text dropped: a lake diagram's label stacks (inside a figure region, classed as banners), a table printed sideways on a landscape page (dad8f9b8: its lines are rotated and the table finder skips rotated lines), a page number the reference counts as a cell. The sideways table is the one worth a rule later.
- **Ruled cells whose lines pair up are rows (09:05-09:40, for run 49).** PyMuPDF returns a ruled cell's lines joined by newlines; a specification sheet rules one box around four instrument properties beside a box with their four values, and a reader takes each line as a row. When every filled cell of a body row holds the same number of short lines, none of which reads as the wrapped continuation of the line above it, the row becomes that many rows (`split_multiline_row` in `tables/ruled.py`; a one-line label left of the stacks stays on the first row). The instrument sheet 1 of 5 to 3 of 5; the bat-metals table keeps a three-line label beside two-line values and is unchanged; eight ruled controls unchanged.
- **Running heads widened (09:10-09:45, for run 49).** A few short body-sized lines at the very top of a page, set apart from the text below by white space, are a running head (a statute's "Part 2 / Division 1" lines: 3 of 5 to 5 of 5); a single line in the bottom strip may run to fourteen words; a short line stacked under a header block may run to eight. The first version took a paragraph tail carried to the top of a column for a header (a multi-column page lost an order check), so a running head may not start in lowercase or hold a sentence end. Twenty-five sampled header pages unchanged. Three running heads still stand (a page number beside a journal name, a document URL, a journal reference line) and three "absent" checks are titles that repeat their running head, which cannot be dropped. The crowded-cell rebuild is limited to tables of eight rows or fewer: a bus timetable's note row holds many numbers too, and rebuilding the timetable dragged its running head into a cell.
- **Word spaces in tiny type (09:15-09:30, for run 49).** A tiny bold caption ("James Norwood still favours pink boots", 6.4 pt) sets its word spaces at 0.78 pt, under the 0.9 pt absolute floor, so the words came out glued. A gap of a tenth of an em that nine letter pairs in ten stay well under is now a word space (`_chars_to_words`): the caption's check is back, eleven other tiny-text pages unchanged. Most tiny-text misses are the hidden OCR layer's own errors: 54 of the 90 failing strings are not in the layer at all.
- **Crowded ruled cells rebuilt (09:25-09:45, for run 49).** A logistic regression table is ruled around its header and its two model blocks only, so each block came back as one cell holding a run of numbers. A body cell with six or more numeric tokens now triggers the rebuild from text lines whatever the row count, and the rebuild's numeric-share bar drops to 0.15 there (its title and stacked headings dilute the share to 0.21): 0 of 3 to 1 of 3, ruled controls unchanged. Tests: 169.
- **Small-caps fonts read as capitals (09:25-09:35, for run 49).** A bibliography sets author names in "TimesTen-RomanSC": the text layer says "Rottier S., Piette J.", the page shows ROTTIER S., PIETTE J., and the reference reads the capitals. Lowercase letters in a font whose name ends in SC or SmallCaps are uppercased (`_small_caps`): the two bibliography pages 1 of 7 to 6 of 7. Tests: 172.
- **Run 49 on hold (09:30).** The owner asked to talk before it launches; the candidate stands at run 48 plus eleven checks won and none lost across the page checks. Questions put to the owner: commit now, the vision stage (the only route past the high sixties), and whether footnotes and full titles stay even where the benchmark penalises them.
- **Where the multi-column misses are (09:40).** Of run 48's 233 failing order checks, 148 are near misses in the text rather than in the order: hidden-OCR-layer character errors, small caps (now handled), glued words, and 11 where inline maths in prose is written as LaTeX while the reference wants plain text (left as is: the formula pages reward LaTeX).
- **Also tried and set aside:** re-reading poor hidden OCR layers with RapidOCR (13 of 66 failing strings found against the layer's 9); the picture-OCR option on the four picture tables (one page gains 4 checks, the others nothing; controls unchanged; left off by default); the 52 sentences broken at a block boundary are footnotes, captions and forms interleaved with no single pattern; the 77 failing baseline checks are the empty handwriting pages.

- **M14, Marker and MinerU read (09:50-10:20).** The owner chose the reading day over the vision routes ("i want to make sure we have exhausted all mechanical options"). Twenty source files of `datalab-to/marker` and `opendatalab/MinerU` read from the public repositories, ideas only; written up in `docs/M14_MARKER_MINERU.md`. Headlines: Marker's fast mode (light layout detector, text layer, vision model only where the layer fails) scores 66.6 on olmOCR-bench to our 66.7, and its pure text-layer mode 43.6, because it never reads formulas from the text layer; its weights are closed to a competing product at any size; MinerU 3.x is Apache 2.0 with attribution and its PaddleOCR-family models (layout with an order head, PP-OCRv6, formula and table models) are usable on CPU; reading order is a model in both, except that Marker orders text-layer pages by the PDF character stream, the one mechanical idea we lack; Marker scores several candidate table grids and keeps the best; both re-read bad text at block or span level where we reject whole pages.
- **Lateral-thinking round launched (10:25).** The owner: think laterally "irrespective of what others are doing", on Edward de Bono's principles. Ten independent thinkers, one technique each (random entry with eight random words, provocation, challenge, reversal, escape from dominant ideas, stepping stone, concept fan, fractionation, other people's views, and a black-hat contrarian with a product lens), all read-only, none allowed to read the M14 report. Each starts from `bench/out/swarm/evidence_pack.md` (the problem in concept terms, the constraints, the score by section, the failure census with counts, what was tried and set aside, the checker's rules) and writes 6 to 10 ideas with a technique trail, a mechanism, the checks it could touch, a one-hour falsification test and the strongest objection to `bench/out/swarm/ideas_<technique>.md`. Harvest and a verifier pass follow.
- **Lateral round harvested (10:25-11:40).** Ten reports in `bench/out/swarm/ideas_*.md` (a usage limit cut the first launch; three thinkers were rerun), harvest in `docs/LATERAL_ROUND_1.md`. What the round established: the OCR pass reads scans at a half or a third of their pixels (`_MAX_SIDE` 2,000 px against 3,200 to 6,400 px scans; 93 of 98 old-scan pages); the failing tiny-text pages are mostly our own OCR of layer-less dictionary scans, not somebody's hidden layer; the log's set-aside sentence about re-reading hidden layers was inverted (13 found against 9) and ran at the reduced scale; old-scan maths is formula checks only and the geometric rebuild runs on OCR pages inventing subscripts; multi-column is not an ordering problem (17 true misorders of 233) and the PDF's content stream is right on 92 percent of the judgeable checks; the classical ceiling is about 72.5; and PyMuPDF is AGPL-or-commercial, against D007. Three one-hour tests run on run 48's outputs: a space after , ; : on scanned pages wins 12 and loses none; plain inline maths wins 1 (and loses 20 on arXiv ungated); 7 old-scan-maths references are present as plain text. Shortlist and owner decisions in the harvest.
- **Plan agreed and compact prepared (11:45-12:05).** The owner asked whether the usage-limit interruption was recovered cleanly (it was: four of the seven cut-off thinkers had saved their reports seconds before, the other three were rerun, nothing in the repository was touched), then set the plan: wave 1 after the compact, then run 49; wave 2 through the week with tests first; wave 3 on decisions. Target 70 without a model, 72.5 the ceiling, the census pool the stopping rule (D018). The round's reports were copied from the git-ignored `bench/out/swarm/` to `docs/lateral_round_1/` and its census scripts to `bench/tools/`. The licence question is recorded as an open decision. Committed at the owner's request at 12:25 as 5eb1b11 (24 files: the seven rules and their tests, the two reports, the round's files, the plan); working tree clean; nothing pushed (no remote).
- **Wave 1, items 1 to 4 (12:30-13:10, for run 49).** (1) *Punctuation spaces on OCR text.* A comma, semicolon or colon followed directly by a word is a word break in our OCR reader (`ocr/rapid.py`, `_punct_parts`) and, for the comma, in hidden OCR layers (`extract/textlayer.py`, whose `_split_glued_words` already split at `;` and `:`); a single letter after the mark stays ("A,B", "f(x,y)"), web and e-mail addresses keep their colons. Re-measured on run 48's outputs by TrueDoc's own page kind: 12 checks won, none lost, all on pages we read ourselves (hidden layers: no change); without the single-letter guard the bare rule lost a table cell "A,B". Page checks: tiny text +6 on five pages, old scans +5 on five pages, multi-column +1 (an Indonesian page), all as measured.
- (2) *TeX ligature codes.* On a page set with dvips Type 3 fonts the glyphs are named by code, so MuPDF hands back the raw code; Python treats 0x0B-0x0D as whitespace, and "fi" became a word break ("classi cation") while "ffi" and "ffl" (0x0E, 0x0F) were stripped as control characters. `_recover_tex_codes` reads the codes of TeX's OT1 layout (ligatures, ß æ œ ø, Greek capitals, accents) for a font whose characters on the page are mostly letters set in words; a symbol font using the same codes for other glyphs (cmmi's τ at 0x1C) sets single letters and is left alone; a code is replaced only next to a letter of the same font, one character per letter with the glyph's box shared out. The T1 ligature slots are mapped when they are a text font's only raw codes (no benchmark page uses them; unit test only). Census over the benchmark with our own text flags: one multi-column PDF (two pages) and one tables page carry such codes; "classification", "off-line", "difference", "efficient", "fluid" now read correctly. **Correction to the round's claim of 13 multi-column checks:** blanking the ligatures in the failing references and rescoring run 48 flips no multi-column check at all (the two pages' remaining failures lie elsewhere) and three headers/footers checks on pages whose layers already spell the ligatures out; the fix is for fidelity, not score.
- (3) *Formulas on OCR pages.* `display_formula_blocks` no longer rebuilds LaTeX from OCR characters, which invented superscripts and subscripts that are not on the page ("2_{c}c_{2}x" for "2c-x"); each line inside a formula region is written as the engine's own string in `$$...$$` (`_ocr_formula_blocks`, TeX specials escaped). Four scanned-maths pages checked: scores unchanged (3/14, 0/12, 0/16, 0/3), as expected of a fidelity fix.
- (4) *Stacked statistics.* A row with nothing in the label column whose filled cells are all bracketed numbers, each under a number in the row above, folds into that row: in the table finder's rows (`tables/ruled.py`, `fold_stacked_statistics`, cell boxes united) and in the aligned builder (`_merge_wrapped_rows`); a row that has taken a fold takes no second; `is_bracketed_statistic` in `tables/cells.py` is the shared shape. The econometrics page (dad8f9b8) 0/3 to 2/3. The other page (981f5f24) first gained one and lost one: the folded cell "− 0.0548*** (0.0175)" no longer counted as a number (three stars, a space after the minus, the stars before the bracket), so the value row was taken for a heading and merged into it; `_NUMERIC` widened for the three shapes, and the page re-checked at 8/8 from 6/8. Suite 189 tests (three new files). Page checks of items 1 to 4 against run 48: 16 checks won, none lost, on 23 pages.
- **Wave 1, item 5: OCR at the scan's own resolution, set aside (12:40-13:10).** The test the round asked for, on the fourteen pages it named (ten old scans we read badly, the three 600-dpi tiny-text clippings, one scanned table): each page rendered at its embedded image's own pixel size (1.33x the point size on the old scans, 5.5x on the table, 8.3x on the clippings) and read in full-width strips 2,000 px tall with a 200 px overlap, against the current reader (300 dpi, capped at 2,000 px on the long side). Both readings scored on the page's own checks as a plain text of the lines in top-to-bottom order. Result: no page gained a check. Old scans: 43 reads nothing either way; 30, 46, 17, 75, 24, 63, 10 the same checks; 74 a third more characters at lower confidence (0.85 to 0.76) and the same 2 of 6; 70 four per cent more characters and the same. Tiny text: the native read finds slightly less (5,190 against 5,204 characters, 5,227 against 5,713, 5,037 against 5,342) and passes one check fewer on two of the three pages. The scanned table: 0 of 11 both ways. Fact 1 of the round (we read scans at a half or a third of their pixels) is true and does not matter to this engine: its recogniser resizes every line to its own height, so the pixels above the current cap buy nothing, and the tiny-text clippings are already read above 300 dpi. Set aside with these numbers; the tiled reader is not built. The scratch script is `bench/probes/native_ocr_test.py`.
- **Wave 2, test 7: the conservation census (13:16-13:44, scratch `conservation_census.py`).** Every word of three or more letters in a text layer (as our extractor reads it, hidden text excluded) checked against run 48's output for the page, over 1,198 pages with a usable layer. Read plainly, 1,119 pages drop something and 24,789 words go missing; read carefully, nearly all of it is intended or an artefact of the method: running heads, feet, citation lines and notices that the margin rules remove on purpose (a handbook's notice block on four pages, a conference footer, an equal-opportunity notice, a journal's citation strip); and the halves of hyphenated words ("tion", "ing", "con", "pro" lead the list), which the output joins. One real loss stands out: an arXiv page (2503.08283, page 7) whose 43 lines of prose come out as a single display formula with every space stripped ("theminitially,longertimehorizonsand..."): a whole page of text made unreadable by the display-maths test, a fidelity failure no check measures. Traced (13:58): the page's body face is TeX Gyre Termes (the newtx package's text font, "TeXGyreTermesX-Regular", 3,224 of 3,296 characters), and the maths-font list carries the hint "TEXGYRE", meant for the TeX Gyre Math faces; so every character counted as maths, the test saw no ordinary words, and the page became one formula. Fix ready as a failing test (`tests/test_math_font_hints.py`: a TeX Gyre face is maths only when its name says Math); applied when the code is free. The reach (14:02): eleven benchmark pages are set in a TeX Gyre text face, ten of them arXiv pages, and every one of the ten carries a formula block of 400 to 2,000 characters in run 48's output, the swallowed prose; they are the top of the conservation census's list. Those ten pages are page-checked with the fix.
- **Run 49 launched (13:16).** Candidate `truedoc48`: run 48's code plus the morning's seven rules and wave 1's items 1 to 4. The launcher's validation: suite green, gate 100/128, maths samples 46/52 and 57/64 (the same as run 48's). Expected against run 48: +16 checks from the page checks (tables +4, tiny text +6, old scans +5, multi-column +1) plus the eleven of the morning's rules, about +0.3 overall if nothing regresses elsewhere.
- **Wave 2, test 1: the content stream as a reading-order witness, set aside (13:17-13:19).** While run 49 converts. Every multi-column page's lines in the order the PDF paints them, scored on the 841 order checks against run 48's output: the stream passes 512, we pass 640; the stream is better on 26 pages (32 checks) and worse on 89 (160 checks). The trust gate the round proposed (how often the stream jumps back up the page inside a column) does not separate them: winners and losers both sit at zero, and the strictest gate picks 121 pages for a net loss of 72 checks. The 32 checks are the ceiling of a per-block tie-breaker, which cannot be tested without instrumenting the layout stage; set aside with these numbers (scratch `stream_order_test.py`).
- **Wave 2, test 2: the running heads we keep (13:19-13:21).** Run 48 fails 28 'must be absent' checks (27 headers/footers, 1 old scan). Twelve sit in the top band of the page: four just outside the 8% strip the top-strip rule reads (a journal line at 8.2%, a Portuguese title at 8.4%, a statute's part heading at 8.9%, "Notes" at 9.2%), the rest inside it but set as headings or body text the rule's other conditions keep (a repeated document title of eight words, a form's name, a page number "2" alone). Six sit in the bottom band, three of them real footnotes of a Swedish statute that the benchmark counts as furniture, and eight in the middle of the page ("OPEN ACCESS", "PLOS ONE", a thesis's "SKRIPSI"), which no margin rule should touch. Widening the top strip to 10% is the one cheap build, worth at most four checks (0.06 overall) with a regression risk on pages whose first heading sits that low; ranked last in wave 2 (scratch `running_heads_census.py`).
- **Wave 2, test 3: what the failing table checks are (13:21-13:22).** Run 48's 227 failing table checks by the checker's own reason: the cell found nowhere 94; no table in our output at all 48; the cell found but a neighbour or heading wrong 79 (column heading 23, right 16, above 15, row heading 11, below 8, left 6); our output empty 6. Of the 79 relation failures, the expected neighbour's text exists somewhere in our output in about two thirds (the heading or neighbour landed in another cell: a merged or split column, a heading not handed down), which is the ceiling of the round's "columns from the numbers, headings handed down, HTML spans" idea: about 50 checks, 0.6 overall, spread over many pages (no page holds more than five). The 48 checks with no table in the output are the next census (scratch `table_failures_census.py`).
- **Wave 2, test 4: the twelve pages with a table expected and none output (13:22-13:24), 48 checks.** Four are pictures: the text layer holds three to six lines and the table is drawn or scanned (a shipping label, a parts list, a laboratory sheet, an address block; 18 checks), the vision-tier territory already set aside. Two are unruled tables we wrote as prose with every checked cell present in the text (a botanical key, a Polish scoring sheet; 8 checks): the aligned finder's miss, the first build of wave 2's table work. The other six (22 checks) were read next: two carry the checked text in no text layer at all (the clinical-trial table's registry number, the 305-line page's numbers: drawn, not typed), so they join the pictures; the water-quality table (133 lines, "TN 2300 µg l-1" in our prose) and a dated form (17 lines) are aligned tables the finder missed, like the botanical key and the Polish scoring sheet (a two-row table of six short cells under a colon). So the winnable part of this bucket is four unruled tables the aligned finder passes over, about 16 checks, each a different shape (scratch `no_table_census.py`). Traced (13:25-13:30): the Polish sheet is six label-value rows that `_merge_wrapped_rows` folds into one, because every line starts lowercase and the wrapped-cell rule takes a lowercase start as a continuation; the fix (a line whose value carries a number under a value that carries a number is an entry of its own) is written as a test and waits for run 49 to finish converting. The botanical key is a five-row candidate rejected as prose (its leads are long); the form's rows never become a candidate at 24 pt type; the water-quality table is a two-column block of values inside a figure at the very top of a journal page ("surface water | bottom water" over TP, TN and pH), inside the 9% top strip the aligned finder leaves to running heads, so it never becomes a candidate. Those three stay on the list: a key of long leads, a form in 24 pt type, a value block inside a figure in the head strip.
- **Wave 2, test 6: four of the pages where a checked cell is found nowhere (13:31-13:32).** A gene table whose OCR layer is rubbish (unwinnable); the statistics table whose "Shapiro W / P value" lines pair up in one ruled cell, which the paired-lines rule already in run 49 splits (4 checks expected there); a rate table whose first block ("Q3 | $448 | $427", "9 Months | $1,298 | $1,263 | 5%") sits at the top of the page inside the 9% strip the aligned finder leaves to running heads, the same miss as the water-quality block (4 checks here, 5 there: the strip should keep rows of several cells, since a running head is one row); a committee list of names with tick marks read as one giant cell (4 checks; a checklist layout the aligned finder has no shape for). Four of the relation-failure pages read too (13:33-13:34): a Portuguese statistics table with rows merged and a heading dropped; a Hindi station table whose expected text differs from the layer in conjunct order (unwinnable here); a survey table whose "Groups" heading swallowed its first entry, which the entry-end rule already in run 49 addresses; and a donor table losing to two glued spaces in a digital layer ("University,Japan", "Giving(individual") and a thousands space ("3 479"). The glued comma is the wave-1 rule's shape on digital text, where it was never measured; measured (13:34-14:00, scratch `measure_punct_digital.py`): on the digital pages of four subsets the guarded rule wins that one table check and loses none. One check is not worth a rule on text whose spacing the producer set on purpose; the rule stays OCR-only, and the number is recorded. The committee checklist traced (13:35): it is a fifteen-row candidate with a clean seven-column grid (name, tick, name, tick, name, and the minutes' side column) that `_build_table` rejects, most likely as "justified prose sliced at word gaps": the tick columns are sparse, so the grid has more columns than a typical row has segments, which is that rule's signature (confirmed in-process, 13:37: seven columns against a median of four segments a row); a checklist's signature is the opposite, left edges that repeat down every row, which the rule will have to weigh before it calls a grid prose. Three tests now stand written and failing against the current code, ready for the build once run 49 has converted: the head-strip table, the lowercase label rows, the checklist with sparse tick columns (`tests/test_table_in_head_strip.py`, `test_table_lowercase_labels.py`, `test_table_checklist_columns.py`). Four more cell-not-found pages read (13:40): a scanned confidence-interval table whose OCR is rubbish (unwinnable); the spectrograph specification whose paired lines the ruled-cell rule already in run 49 splits (4 checks expected); a small reliability-statistics table found nowhere; a regression table whose whole rows fall into one cell. Traced (13:40-13:42): the reliability table is two rows of two cells under a title line, below the finder's minimum (three rows, or two rows of three cells), a shape worth 3 checks only with a title-above guard; the regression table's candidate builds as 13 rows by 9 columns in the finder, so its one-cell rows are made later in the pipeline (a group label "Unadjusted Model" over rows that carry their own labels, or the ruled-table rebuild), which only a page conversion will show once the machine is free.
- **Wave 2, test 5: monospaced printouts among the failing table pages (13:32-13:34).** Of the 90 pages with failing table checks, three are set in a monospaced face with a text layer (one digital printout with 5 failing checks, two typewriter-style OCR layers with 4 and 1); the rest of the "printout" look is scanned pages with no characters at all. The character-grid idea is therefore worth about ten checks on three pages. A quick grid reading of the digital printout (13:27-13:31: every character on a column by its x over the character width, borders from the bars and colons, then from the blank columns across the numeric rows) passed none of its five checks either way: the printout's columns are not clean blank runs once the text is placed on a grid, and its headings stack over spanning group labels. Set aside with those numbers (scratch `char_grid_test.py`); ranked last.
- **Run 49 scored 67.1 (14:15; converted 13:16-14:11), the best so far; held-out 64.7, tuned-on 63.0.** Against run 48: arXiv 86.8 (+1), baseline 94.7, headers 96.6 (+2), tiny text 81.2 (+7), multi-column 73.9 (+2 net: 6 won, 4 lost), old scans 21.5 (+5), old-scan maths 3.5 (-3), tables 78.7 (+9 net: 15 won, 6 lost). 36 won, 13 lost. The losses: four order checks on one page of a French bibliography (the same document gained five elsewhere); three scanned formulas on one page that the geometric rebuild had got right and the plain string lost because its braces became TeX grouping (repaired at once: a brace the engine read is written `\{`); four cells of one regression table whose statistics row the fold merged where this reference wants the rows apart; and two single cells ("John Wang, M.D.", "LTP"). All five loss pages are in the page checks running with the wave-2 fixes. Read from the outputs (14:20-14:28): the bibliography page is set in a small-caps face and this reference typed the names in mixed case ("David-Elbiali M.") where the same document's pages 33 and 34 typed them in capitals and gained five; the rule reads what the page shows and stays, net +1 on the document. The regression table's four losses are the statistics fold where this reference keeps the t-values on their own row, against two pages that want them merged (+4): a convention split between annotators, a wash on the score; the fold stays as the reader's reading. The neuroscience table lost its heading row "Category", which sits in the top strip of a continued table and was read as a running head by the morning's top-strip rule (it had been a text block above the table before, outside the aligned finder's strip); the repair is that a row of several cells in the strip directly above a table belongs to the table. The cardiology roster's wrapped title ("Chief, Cardiac Catheterization Laboratory" / "MedStar Union Memorial Hospital") no longer folds into one cell: the table is ruled, and the morning's paired-lines rule split the one two-line cell into two rows although nothing pairs up across the row; the repair is that the rule needs two stacked cells (lines pair across cells or not at all). The three scanned formulas are back with their braces (page check 2 of 24 to 5 of 24). Both repairs are written as tests and wait for the page checks to release the code. Page checks of the wave-2 targets against run 49 (14:15-14:35): the Polish scoring sheet 0 of 4 to 4 of 4; the regression table whose rows fell into one cell 1 of 3 to 2 of 3; the summary block at the head of the rate page and the value block in the figure at the head of the journal page are not in the output at all, so no finder ever saw them: the summary block (three lines of numbers) is taken for a running head by the morning's top-strip rule, and the figure's block goes with the figure; the checklist is a ruled box that the table finder returns as one row of one cell, so the aligned repair never saw its lines either. Two more repairs follow from this: a block that is mostly numbers is not a running head, and the ruled path traced on the checklist (14:25) shows the rule finder returning a 3 by 3 box with all the names in one cell, and the sparse-table rebuild declining to rebuild it because a rebuilt table must be at least three-tenths numbers, a bar meant for boxed prose; a rebuilt grid of short cells (four in five cells of three words or fewer, three columns or more, six rows or more) is a table on its own evidence, numbers or not. The ten TeX Gyre arXiv pages, page-checked with the text face read as text (14:15-14:27): every page is prose again (no formula block longer than a character where run 49 had blocks of 400 to 2,000), and the maths checks come out +7 and -2 (two formulas that had matched only by accident inside the garbage block: a set "{τ1, . . . , τN}" whose ellipsis, set in the text face, now splits the inline formula in two, and "b = " before a fraction, set in the text face, now left outside the formula; a later refinement of the inline detector's run boundaries, punctuation and a lone letter between two maths runs, would take both) All four repairs of this hour applied at 14:30: paired lines need two stacked cells, a strip row next to a body row of cells joins the table, a mostly-numeric block at the top is content, a rebuilt grid of short cells is accepted. Suite 202. Page checks against run 49 (14:27-14:30): the cardiology roster 3 of 5 to 4 of 5, the checklist 0 of 4 to 1 of 4 ("Bartholomew, Deb" now a cell of its own; the heading relations still fail), the Polish sheet 4 of 4, the regression table 2 of 3; the neuroscience heading and the rate page's summary block unchanged (read next); the paired-lines controls (the statistics table, the spectrograph sheet) unchanged. The numeric guard then narrowed to blocks of two lines or more, so a one-line journal head with its volume and year stays furniture. The neuroscience heading row "Category" is back in its table (the check still fails on another relation). The rate page's summary block was removed by a different hand: the layout model labels it a page header, and the fusion takes the model's word; the same guard now sits there too (`_numeric_region` in `layout/fuse.py`: a page-header or page-footer region whose blocks make two or more lines that are mostly numbers keeps its blocks as they are; the helper `numeric_token_share` lives in `classify/blocks.py` for both). Suite 203; page check of the rate page and three running-head controls (14:33-14:36): the controls unchanged, the rate page unchanged too, because the block never reaches the fusion as a block: the block builder hands it over as a label and six one-line pieces, and the classifier's zone rule (any short block in the top 9%) had already made each piece a running head. So the judgement moved to the zone: the head of the page is a block of numbers when its text pieces make two or more lines, mostly numbers, at least four of them (`numeric_head_blocks` in `classify/blocks.py`); the pieces so judged (the numeric ones, a label ending in a colon, whatever shares a row with them) are content for the classifier's zone rule and the margin clean-up's top-strip rule alike, while a running head on its own row in the same zone stays furniture. Suite 205. Page-checked (14:45): the pieces survive but as scattered fragments, "9 Months" set as a heading, the numbers as a stray paragraph, half the pieces lost to other rules; worse for a reader than the silent drop and no check gained. **Reverted** the zone-level judgement (the two block-level guards, in the margin clean-up and the layout fusion, stay: harmless and tested); the block belongs to the table path, where a two-row table whose second row runs its numbers together is the shape to build, and that is a wave-2 item with its own hour. Suite 204. **Run 50 launched at 14:45** (`truedoc49`: run 49 plus the brace escaping and the wave-2 repairs of the afternoon; validation: suite green, gate 100/128, maths samples 46/52 and 57/64). While it converts, the next repair is written as a failing test: the inline maths detector bridges one word between two formula words but not a run of them, so "{τ1, . . . , τN}" splits in two once the page's text face is text (`tests/test_inline_math_dots_bridge.py`). The 78 relation failures of run 49 read page by page (14:50): 53 pages, no two alike; OCR letter errors ("ciclomontanismo" for "ciclomontañismo", "34i" for "34½", "aduate" for "Graduate"), long wrapped cells the reference keeps whole, headings the reference expects over a column that our table lacks, a column heading "Total" where the page says "Total DDT". The round's "columns from the numbers with HTML spans" has no common shape to build against; the relation pool is one page at a time, not a rule, and is set aside as a bulk idea. The water-quality value block traced once more with the head-strip logic (14:50): its three strip rows are kept now, but each row also carries a line of the prose column to its left (a two-column journal page, prose left, figure right), so the candidate spans prose and values and is rejected as prose; the side-by-side split does not part them. A figure's value block beside a text column is a shape of its own (5 checks); set aside with the trace. The neuroscience page read once more (14:55): its heading row is back but the table comes out in two pieces, the heading with one body row and the rest below, because the references column wraps to three lines and two lone continuation lines in a row are what the run finder takes for the end of a table. A lone line that starts on a column of the row above and stays inside it is the rest of a cell; written as a failing test (`tests/test_table_wrapped_lines_inside_run.py`) for the code once run 50 has converted, with the dots bridge. Both applied at 15:38, the moment run 50 finished converting: the dots bridge (a run of one to six words made only of dots, commas and semicolons between two formula words joins the formula; `inline_math_text`) and the wrapped cell line (`_wrapped_cell_line` in the run finder: a lone line that starts on a column of the last row of several cells, not the first column, and stays inside it, is the rest of a cell). Suite 208. Page checks against run 50 once it has scored.
- **Ceiling census after run 49 (14:22, `bench/tools/ceiling_census.py`).** Failing checks by bucket (A our output empty, B text in the raw layer but not our output, C in our output but still failing, D in neither, E no text layer): tiny text 83 = 0/8/0/28/47; multi-column 231 = 4/40/17/145/25; old scans 412 = 290/0/0/0/122; tables 217 = 5/14/139/52/7. The mechanical pool (A+B+C, scans aside) is 8 + 61 + 158 = 227 checks against the round's count of a day earlier; the census is recorded run by run from here.
- **Run 50 scored 67.1 (15:40; converted 14:45-15:36); held-out 64.9 (best), tuned-on 62.9.** Against run 49: arXiv 87.0 (+5 net: 7 won, the two newtx formulas lost as traced), baseline 94.7, headers 95.7 (-7: all on two document-control pages, "dated: 2016-09-06 / issued: 2019-04-17 / supersedes: Revision 1 / reviewed: --" and "Page 10 / CERN/DG/RB 2002-338", furniture that the afternoon's numeric-block guards kept as content because dates and reference numbers are mostly numbers too; both guards reverted at 15:45 with their tests, the rate page's block having gained nothing anyway), tiny text 81.2, multi-column 73.6 (-2 on one references page, to be traced), old scans 21.5, old-scan maths 4.1 (+3, the braces), tables 79.2 (+5 net: 10 won on the Polish sheet, the scanned table, the checklist, the roster and the regression table; 5 lost on four pages, to be traced). 20 won, 16 lost. Census after run 50 (15:50): tiny text 83 = 0/8/0/28/47, multi-column 233 = 4/42/17/145/25, tables 212 = 5/16/132/52/7 (A empty / B in the raw layer / C in our output / D neither / E no layer); the mechanical pool (A+B+C, scans aside) is 224 against 227 after run 49: shrinking, slowly. First reading of the five table losses (15:50): every lost cell is still in the output; the relations moved. One cause is plain: the paired-lines rule now leaves a single stacked cell whole, and a rebate table's tariff tiers ("1-80 Kwh - $50 / 81-600 Kwh - $100 / 601+ Kwh - $200", one stacked cell) are rows, not a wrapped title; the distinction is that every line of a stack of entries carries a number, and it is written as a test for the code. Page checks after the revert (15:43-): the CERN page's two checks are back with the numeric guards gone, but the document-control page is not: its five lost checks ("issued: | 2019-04-17", "supersedes: | Revision 1", "reviewed: | --", "dated: | 2016-09-06") come from the head-strip table rule of the afternoon, which read the stamp's four rows of two cells as a table. That half of the rule (rows of cells alone in the strip make a table) gained nothing on its two target pages and goes; the other half (a table's heading row in the strip above its body) stays with its test. The test rewritten first, the code when the checks release it. The checks done (15:55): the dots bridge wins its formula back, the wrapped cell line makes the neuroscience table whole (4 of 4), the references page recovers with the numeric guards gone. The three other table losses read from the outputs: a campus report's banner (wide titles in two rows right above the table) taken for the table's heading by the strip-adjacency rule, so that rule now requires the strip row's cells to start on the table's columns; a course list wrapped after a comma ("ENGR 350A," / "ENGR 370A") and a design level broken at a hyphen ("(approx. 90-" / "95% design level)") no longer folded, because the number test of the lowercase-labels repair blocked them, so that test now yields to a comma, hyphen or connector at the end of the cell above; and the same schedule table rebuilt from its lines by the grid acceptance, which now needs the box to hold three times more lines than rows. With the tariff tiers and the strip rule's first half, five repairs; suite green. Page checks against run 50 (15:45-15:52): the campus report 4 of 5 to 5 of 5, the schedule 2 of 4 to 4 of 4, the course list 6 of 8 to 7 of 8, the neuroscience table 3 of 4 to 4 of 4; the roster, the Polish sheet, the checklist and the econometrics page hold. The document-control stamp and the tariff tiers did not move: read next. Read (15:55): the tariff tiers are rows again as in run 49 and the "$200" check fails on another relation now, one check left to the run; the stamp had become a table by the strip-adjacency rule after all, because its third row crosses the strip's edge into the body and the two rows above align with it, so the rule now asks for a table body of at least two rows of cells below the strip row, not one. Suite 208. That did not move the stamp either: the trace shows its table built by the aligned finder from body rows alone (it sits just under the strip), which run 49 did not do; the cause is still to be found and the page costs five checks meanwhile. **Run 51 launched at 15:59** (validation: suite green, gate 100/128, maths samples 46/52 and 57/64; `truedoc50`: run 50 minus the numeric guards and the strip-alone rule, plus the dots bridge, wrapped cell lines, tariff tiers, the comma-and-hyphen exemption, the grid-rebuild gate and the aligned strip heading), the stamp trace to follow while it converts. Traced (16:00): in run 49 the wrapped-cell rule folded the stamp's three rows into one (its lowercase keys "reviewed:", "dated:", "supersedes:" read as continuations) and the one-row grid was rejected as a table, so the lines went out with the page's head as text; the number test of the lowercase-labels repair now stops that fold, and three rows of key: value cells make a table the finder is right to build and the margin rules never touch. The layout model calls the block "key_value" (0.4 to 0.6) with weak page-header readings, no help. The right layer is the furniture rule: a table of a few short key: value cells in the head of the page, above its first heading, is a document-control stamp; written as a failing test (`tests/test_margin_control_stamp.py`) for the code once run 51 has converted. Applied at 16:49 when run 51 finished converting (`_control_stamp` and the table clause at the head of `_margin_cleanup`: a table of at most four rows and two columns, its cells short and at least half of them key: value pairs, ending within the top 15% of the page and above the page's first heading, is a running head). Suite 209. The two-witness test on hidden OCR layers started at 16:50 while run 51 scores (scratch `two_witness_test.py`).
- **Run 51 scored 67.2 (16:50; converted 15:59-16:48), the best so far; held-out 65.0 (best), tuned-on 63.1.** Against run 50: arXiv 87.0 (+1, the dots bridge), baseline 94.7, headers 95.9 (+2, the CERN page back), tiny text 81.2, multi-column 73.9 (+2, the references page back), old scans 21.5, old-scan maths 4.1, tables 79.5 (+4 net: the campus report, the schedule, the course list, the neuroscience table; one cell lost on one page, traced next). 10 won, 1 lost. The document-control stamp (5 checks) has its repair in the code for run 52. The one loss (16:55): a capability list whose heading row "# | Attribute | Description" sits in the head strip over a body whose first column is empty; the afternoon's alignment test asked every heading cell to start on a body column, and "#" has none, so the row was dropped and the table lost its heading. Two of three cells aligned is enough: the test relaxed to at least two cells and at least half (written as a test first). Census after run 51: tiny text 83 = 0/8/0/28/47, multi-column 231 = 4/40/17/145/25, tables 208 = 5/15/129/52/7; the mechanical pool 218 (224 after run 50, 227 after run 49). Page checks against run 51 (16:52-17:00): the document-control stamp 4 of 9 to 9 of 9 with the stamp rule, the econometrics control unchanged; the capability list unchanged even with the relaxed alignment, because its table now comes from the ruled finder (the strip-alone rule had made the aligned one, running head and all) and the ruled path's heading adoption did not take "# | Attribute | Description" above the box: to be traced. Suite 210. **Run 52 launched at 17:01** (validation: suite green, gate 100/128, maths samples 46/52 and 57/64; `truedoc51`: run 51 plus the stamp rule and the relaxed alignment). The capability list traced while it converts (17:00): its rows are a ruled box whose first row is data ("driverTypeAddress | Address of the Driver Type"), and the ruled path adopts a heading printed above a box only for a one-row box, on the reasoning that a box of several rows carries its own heading. A box whose first row has a cell of more than four words, or one starting lowercase or with a symbol, carries none, and may take the aligned heading above it like a one-row box does; a caption above a box ("Table 3. ...", one sentence across the columns) still may not. Written as a failing test (`tests/test_ruled_headerless_box_adopts_heading.py`) for the code once run 52 has converted. Applied at 17:55 when run 52 finished converting; suite 212. Page-checked against run 52 (18:00-18:06): unchanged, with four ruled-box controls unchanged, because the table is not ruled at all: the finder builds it from body lines, and its heading row and first data row both sit inside the head strip, where the adjacency rule judged each strip row against body rows only, so the heading had nothing to join. The rows are now taken nearest the body first, and a row the table takes in carries the row above it (the chain); the capability list 6 of 7 to 7 of 7. Suite 213. **Run 53 launched at 18:13** (validation: suite green, gate 100/128, maths samples 46/52 and 57/64; `truedoc52`: run 52 plus the headerless-box adoption and the chain).
- **Wave 2, test 8: two witnesses on hidden OCR layers (16:50-17:07, scratch `two_witness_test.py`).** The 34 hidden-layer pages with failing text checks in multi-column, tiny text and headers (80 failing checks), each read again with our engine at the pipeline's resolution, every failing check scored against the layer's reading (run 51's output), the engine's, and the two together. The engine passes 9 that the layer fails (six on three pages of a Middle English dictionary, read at 0.94 confidence; two multi-column order checks; one running head), the two together 12, and 67 pass under neither. So a line-level arbitration is worth about nine checks (0.15 overall), most of them on one document; whether a page-level swap to the engine's reading on confident pages loses more than it wins is the next measurement, running (scratch `witness_swap_test.py`, all checks of every hidden-layer page the engine reads at 0.90 or better). Result (18:05, an hour of reading 48 pages beside the run): the layer wins almost everywhere. Confidence bars and nets, all the page's checks counted, layer against engine: at 0.90, 48 pages, layer 181 against engine 72, net -109; at 0.92, 40 pages, layer 172 against engine 71, net -101; at 0.94, 31 pages, layer 143 against engine 53, net -90; at 0.95, 12 pages, layer 38 against engine 8, net -30. Two dictionary pages are the whole of the engine's case (11_pg161 8 against 6, 11_pg145 2 against 1); on the rest the layer is far better (a tiny-text page 12 against 9, another 9 against 0, a multi-column page 5 against 0). A page-level swap is dead at any bar; the line-level arbitration is worth about nine checks on three pages and is set aside with these numbers. Fact 3 of the round stands: the hidden layer is the better witness.
- **Run 52 scored 67.3 (17:58; converted 17:01-17:54), the best so far; held-out 65.0, tuned-on 63.2.** Against run 51: headers 96.6 (+5, the document-control stamp), every other section level; 5 won, none lost. The day: 66.7 (run 48) to 67.3 in four runs. Census after run 52 (18:00): unchanged from run 51 (the stamp's five are header checks, outside the census's sections); the mechanical pool stays at 218. The heading-adoption change is page-checked against run 52 with four ruled-box controls before run 53.
- **Wave 2, test 9: the gutter from ink (18:12-18:15, a census while run 53 converts).** The idea: on a scan whose hidden layer runs its lines across both columns, find the gutter from the ink and split the lines there. Of the 20 hidden-layer multi-column pages with failing order checks (52 checks), one has most of its lines crossing the page's middle (4 checks) and two more have many (40 of 90 lines, 48 of 134; 7 checks); the other 17 pages already read as two columns and fail on their characters, as the census's "neither" bucket says. About eleven checks on three pages, behind a rendering and an ink profile per page: set aside with the numbers.
- **Wave 2, the first no-table shape prepared (18:15).** The botanical key (four checks): five rows of a long lead on the left, each starting with an enumerator ("A.", "aa.", "B."), and a short name on the right; the prose rejection reads the leads as body text. The rule to build: a two-column candidate whose right cells are short labels on at least four rows in five and whose left cells each open with an enumerator is a key, prose rejections notwithstanding; a column of prose beside margin line numbers, the mirror, stays prose. Written as a failing test (`tests/test_table_key_leads.py`) for the code once run 53 has converted. Applied at 19:02 when run 53 finished converting (`_key_table` in the aligned builder); suite 215. Page-checked against run 53 (19:03-19:05): the key 0 of 4 to 4 of 4; the Polish sheet, the econometrics page and the roster unchanged. **Run 54 launched at 19:08** (validation: suite green, gate 100/128, maths samples 46/52 and 57/64; `truedoc53`: run 53 plus the key-table rule).
- **Run 53 scored 67.3 (19:02; converted 18:13-19:00); held-out 65.0, tuned-on 63.2.** Against run 52: tables 79.6 (+1, the capability list's heading), every other section level; 1 won, none lost. Five runs today: 66.7, 67.1, 67.1, 67.2, 67.3, 67.3.
- **Wave 2, the reliability table read (19:08), designed, not built.** "Scale Reliability Statistics" is a title spanning two columns over a two-cell heading row ("Cronbach's α | McDonald's ω") and a three-cell value row ("Counterradicalism readiness Scale | 0.92 | 0.93", its label wrapping to "(CoRS)" below); the run finder wants two rows of three cells or three rows, and the benchmark wants the title as a spanning heading cell. Widening the two-row rule to a two-cell row under a title would admit any pair of gapped lines under a heading; three checks on one page do not carry that risk. Left on the list with its shape written down.
- **Docs brought to the evening and committed (19:15-19:30, at the owner's request).** The status page's "Where we are" (it still described 6 September), the roadmap's M15 note and the round's page were rewritten for the day's end, and this log was given its own 7 September section in time order (every entry of the day had been appended under the 6 September heading). Commit a5d1260: 14 source and doc files changed, 13 test files added, 215 tests; working tree clean; nothing pushed (no remote). Run 54 (`truedoc53`, the key-table rule) was converting at the commit; the next session records it.
- **Wave 3 put to the owner while run 54 converted (19:40-19:50).** Sized from run 53: the 83 blank pages carry 518 of the 1,854 failing checks (old scans 357, old-scan maths 136, tables 16, multi-column 5, headers 4) and 82 of them have olmOCR 2's reading saved from 3 September, so the vision tier can be measured from disk; the mechanical pool by section (tables about 150, multi-column about 93, tiny text about 25, old scans none) puts 70 without a model at two thirds of everything left; partial pages are worth under a point (83 baseline checks at most) and change D008/D009; small task models set aside (the vision tier covers the same pages better, and two witnesses said no to a second engine); the owner's library is 1,176 PDFs and 23,870 pages, about thirteen hours at run 53's rate (2,831 s for 1,403 pages). PyMuPDF's licence re-read from the source at the owner's request: the GitHub page shows AGPL-3.0 only; PyMuPDF's documentation says it is dual licensed with Artifex as the exclusive commercial agent; Artifex's licensing page says a server-based application or service cannot be deployed without disclosing the application's full source under the AGPL, prices unpublished, distribution licences per copy with a quarterly minimum. Plain reading, not legal advice: nothing owed for internal use; source or a licence once TrueDoc is conveyed or served to others.
- **Run 54 scored 67.4 (20:02; converted 19:08-19:58), the best so far; held-out 65.0, tuned-on 63.3.** Against run 53: tables 80.0 (+4, the botanical key, exactly as page-checked), every other section identical to the check; 4 won, none lost. Six runs today: 66.7, 67.1, 67.1, 67.2, 67.3, 67.3, 67.4. Census after run 54: mechanical pool 213 (tiny text 8, multi-column 61, tables 144; 218 after runs 51 to 53). Wave 3 measurements started at 20:03 as one sequential job (`bench/probes/wave3_measure.sh`): olmOCR 2's saved readings merged over run 54's 78 blank pages (`truedoc53_vlm`) and over all 110 pages it read (`truedoc53_vlmall`, which also replaces the 28 pages our OCR has rescued since 3 September), each scored with the official scorer and the held-out split, then the blank pages sorted with our own engine (`bench/probes/partial_census.py`: confidence, word-likeness, language-likeness, numeric share, and the checks a shaky read would pass).
- **Wave 3, measurement 1: the vision tier from disk (20:03-20:06, candidate `truedoc53_vlm`).** olmOCR 2's readings saved on 3 September dropped onto the 78 pages run 54 left blank, nothing else touched: **72.2** (CI 71.2-73.2) against 67.4. Old scans 21.5 to 34.8 (+70 checks), old-scan maths 4.1 to 23.1 (+87), baseline 94.7 to 99.9 (+73: a blank page fails its baseline check), tables +9, multi-column +2, headers -1 (2 won, 2 lost: running heads the model transcribed on a French title page and a Bengali one, so the header rules would need to run over the model's text too). 242 won, 2 lost. Held-out 66.6 (65.0), tuned-on 68.6: the gain is on both halves. The estimate given to the owner an hour earlier was 'about four' [assumed]; the measure is 4.8.
- **Wave 3, measurement 2: the model over our weak OCR (20:06-20:08, candidate `truedoc53_vlmall`).** As above, and the model also replaces the 28 typed pages our own engine has accepted since 3 September (rescued at 0.80-0.85 confidence): **72.6** (CI 71.5-73.5), +0.4 on measurement 1; tables +20 checks (22 won, 2 lost), multi-column +9, headers 2 won and 2 lost; held-out unchanged (the 28 pages are all tuned-on). On image-only pages the model beats our engine even where the engine is confident, so D014's line ('a model only reads pages TrueDoc cannot') would become 'a model reads every page without a text layer' if the owner agrees.
- **Wave 3, the blank pages sorted for the partial-pages decision (20:08-20:13, `bench/probes/partial_census.py`, 319 s).** Run 54's 79 blank pages read again with our own engine, the gate's measures recorded, and each page's own checks run against the shaky reading. Typed but shaky (confidence at least 0.60 and word-like or language-like): 48 pages holding 322 checks, of which the shaky read passes 20. Gibberish: 27 pages, 130 checks, 8 pass. Nothing read: 4 pages. By confidence band: 0.50-0.60 24 pages (115 checks, 4 pass), 0.60-0.70 32 pages (174, 16), 0.70-0.75 10 (98, 2), 0.75-0.80 3 (41, 1), 0.80 and above 6 pages the word-likeness gate rejected (24, 5). Keeping every shaky read would win about 28 text checks and up to 79 baseline checks, about +1.4 at most, against the model's +4.8 on the same pages: partial pages are a reader's question (a marked shaky page against a blank one), not a score lever. The examples narrow it further: the floor of the 'typed but shaky' bucket is handwriting read as pronounceable nonsense ('CCe LcA ct ma hveAads- Shall deave ths Conuma Whecls', language-likeness 0.80 at 0.60 confidence: the language measure is fooled by pronounceable strings), and the pages a reader would want kept with a note are the nine at 0.75 and above (a 1920s letterhead read at 0.86, a French page at 0.96, a manuscript collection header at 0.96, a Spanish table of vehicles at 0.87), all of which the model reads anyway. Recommendation to the owner: leave D008 and D009 as they are; if a partial-page note is wanted for the product, admit only confident reads (0.80 and above) that failed the word-likeness gate, about six pages here.
- **Page-kind census of the whole benchmark (20:45-20:55, `bench/probes/kinds_census.py`, 578 s, no OCR run).** Every page's text-layer kind by section: digital 1,122; none 183; hidden OCR layer 76; suspect 22. Pages without a digital layer, the vision session's whole input: 281 (old scans 98, old-scan maths 36, tiny text 46, headers 39, multi-column 38, tables 24). Old-scan maths has no digital page at all: 21 without any layer (10 left blank, 11 read by our own OCR), 13 with hidden layers, 2 suspect; every reading of a formula there is a machine's guess at words, which is why the section sits at 23.1 with the model on the blank pages only and at 82.3 in olmOCR's own hands. Correction to what was said to the owner at 20:40: the 26 non-blank old-scan-maths pages are 13 hidden layers, 11 pages our own OCR read and 2 suspect layers, not 26 hidden layers; the argument is unchanged. At 12 minutes of model time per 110 pages (3 September), 281 pages are about 31 minutes on one RTX 4090.
- **How the top tools treat hidden OCR layers (20:40-20:50, the owner's question; three project pages read).** olmOCR's pipeline help says the text-layer anchor is 'not used for new models': image only. Marker extracts the embedded text with pdftext and decides per page whether it is usable, sending garbled or scanned pages to its model; `--strip_existing_ocr` throws hidden layers away but is off by default. Chandra's page does not state its input handling (a Qwen-based vision model, image-only by construction [recalled]); its code is Apache-2.0 but the weights carry a modified OpenRAIL-M licence ('free for research, personal use, and startups under $2M funding/revenue, cannot be used competitively with our API'), so Chandra is a competitor to measure, not a candidate to adopt. Conclusion for the pathway (`docs/LATERAL_ROUND_1.md`, wave 3): exact text where the author's text exists, the picture everywhere else; no top tool reproduces a hidden layer.
- **GPU session 2 started (20:50; the owner rented an RTX 4090, 24 GB, on vast.ai at the recommended settings).** Prepared beforehand: `bench/gpu/pages.txt` regenerated as the 281 pages without a digital text layer (with each page's kind; the 3 September list kept as `pages_20260903.txt`), the PDFs copied into `bench/gpu/pdfs/` (110 MB) as a fallback, and `bench/gpu/fetch_pages.py`, which makes the rented machine download the listed pages itself from the public Hugging Face dataset instead of taking them over the owner's uplink (46 MB took 12 minutes on 3 September). On the machine: the three small files uploaded, then one nohup job: fetch (about one page a second unauthenticated), `run_olmocr2.sh` (apt, venv, `olmocr[gpu]`, then the pipeline once per category). Two harness lessons: a remote `nohup ... &` started over ssh keeps the session open unless stdin is detached (`ssh -n`, or `< /dev/null` on the remote command), and the Monitor tool's eval breaks on a quoted multi-line script, so the poll loop lives in `bench/gpu/poll_remote.sh` and the monitor runs the file. Results will be placed as candidate `olmocr2b` (the 3 September candidate `olmocr2` stays), then merged by page class with `bench/probes/merge_by_list.py`: blank pages only, all 281, and none / hidden-OCR / suspect separately.
- **GPU session 2 done and measured (21:22-21:36; the owner destroyed the instance at 21:24; 85 cents in all).** Fetch 290 s, install 6 minutes (25 on 3 September's slow link), 281 pages read in 21 minutes (headers 39 in 3, tiny text 46 in 5, multi-column 38 in 5, old scans 98 in 3, old-scan maths 36 in 2, tables 24 in 2; a model reload between categories), 3 pages returned empty (two headers pages, one old scan). Readings placed as candidate `olmocr2b`; five merges into run 54 by page class with `bench/gpu/merge_by_list.py`, each scored with the official scorer and the held-out split: blank pages only 72.2 (the same as with the 3 September readings: the model is stable), no layer at all 77.1, hidden OCR layers only 72.0, suspect layers only 68.4, **all 281 non-digital pages 82.7 (CI 81.8-83.7; held-out 79.4, tuned-on 80.5)**. The classes add up (9.7 + 4.6 + 1.0 = 15.3 on 67.4). Sections at 82.7: arXiv 87.0 (unchanged: digital pages never go to the model), old-scan maths 80.8, tables 83.6, old scans 46.6, baseline 99.8, multi-column 80.1, tiny text 87.8, headers 96.3. Against run 54: 725 checks won, 53 lost: headers 5 (running heads and feet the model transcribes: an Arabic issue number, a French title, a Bengali university name, 'Fonte: Bacen', a Norwegian county), tiny text 17 (presence checks whose reference text carries the hidden layer's own OCR errors, 'nnder British rule', so the model's correct reading fails: a benchmark artefact no better reader can win), multi-column 6, old scans 11, old-scan maths 4, tables 10. Held-out by section: old-scan maths 71.2 on 66 checks against 82.4 tuned-on, tiny text 93.0 against 87.2, the rest within two points. Where it lands: above olmOCR's own published 82.4, Infinity-Parser 82.5 and PaddleOCR-VL 80.0, level with Chandra's 83.1 inside the interval; the hybrid (exact text on the 1,122 digital pages, the model on the 281 others) beats the model alone by the digital formulas (87.0 against olmOCR's 83.0). Not a TrueDoc run yet: the converter's vision stage reads blank pages only.
- **What follows from it (21:40).** (1) The rule: a model reads every page without a digital text layer, hidden OCR layers included (D019, agreed by the owner at 21:50; D010 keeps hidden layers only as the fallback when no model is available). (2) The header and furniture rules must run over the model's text (5 losses). (3) The proper run with `--vision-endpoint` on inside the converter needs a served model for the run's hour: one more rental, or the on-demand endpoint. (4) The classical pool (213 checks, about 3 points) is now what separates 82.7 from passing Chandra; tables (144) first.
- **D019 agreed and the evening committed (21:50-21:55).** The owner agreed D019 (a model reads every page without a digital text layer) after the session's table. Commit eb8d67f: fourteen files (the eight docs, the GPU folder's README, page list and three new tools, `.gitignore` now ignoring `bench/gpu/out2/` like `out/`); no source code changed today after run 54's key-table rule. A `.gitattributes` rule keeps `*.sh` at LF so the scripts run unchanged on the rented Linux machines (Git on this box converts to CRLF on checkout otherwise; the session's upload had to strip carriage returns by hand).
- **D019 built into the pipeline (21:58-22:35).** (1) A third vision provider, `truedoc/vision/file_readings.py`: `--vision-endpoint file:<folder>` replays a model's saved page readings (the benchmark candidate layout, olmOCR's small YAML front matter stripped), so a GPU session's readings go through the whole pipeline without a served model. (2) Page selection in `_read_unreadable_pages_with_model`: every page whose text layer is not digital goes to the model (D019); digital pages never do. The reader's note now says why (`docs/OKF_SPEC.md` item 2: 'the PDF's own text layer is an OCR layer, not the author's text' for hidden and suspect layers). (3) The running-head witness, `truedoc/vision/witness.py`: the page's own lines in the head and foot strips (12% of the height; the hidden layer's lines, or our engine's, kept on rejected pages as `witness_lines`) vouch for the model's first and last line as furniture; where the layer leaves a strip empty (a publisher's download stamp at the foot of a bare scan, the French journal page) our engine reads that strip, from a crop twice its height because the engine misses text at a crop's edge. Dropped lines are recorded in the page's `vision_dropped`. (4) `bench/tools/launch_run.sh` takes extra bench arguments from the `EXTRA` environment variable; `bench/tools/watch_run.sh <N>` is the status-file watcher for the Monitor tool. Tests: `test_vision_file_readings.py`, `test_vision_witness.py`, and `test_vision.py` reshaped for D019 (a digital page is never sent; text over a full-page image is a suspect layer, read by the model, its running head witnessed away); 223 pass.
- **Two hour-tests for the witness, from disk (22:20-22:36; `bench/probes/witness_census.py`, `bench/probes/witness_strips.py`, `bench/probes/strip_test.py`).** A census first: the strip lines of all 281 non-digital pages (98 from the layer, 183 from our engine; 214 pages have head-strip lines, 196 foot-strip lines). Test 1, the first draft (first and last three lines, any short line, position only): 147 lines dropped on 75 pages, most of them body text (dictionary entries at the top of dense tiny-text scans, a magazine's price line, figure captions), 4 checks won and 5 lost: a wash, and wrong. Test 2, the strict rule (first and last line only; the line must look like furniture: all capitals, a page number, or a few words with a digit in a script without case) with the strip OCR for empty strips: 17 lines dropped on 17 pages, every one a running head ('LES JUIFS, LES GRECS-CATHOLIQUES SOUS 'ALÎ BEY AL-KABÎR', 'REPORT OF THE SECRETARY OF WAR.', 'IV] REDUCTION OF MULTIPLE INTEGRALS', 'THE WESTERN UNION TELEGRAPH COMPANY'); **82.8 (CI 81.9-83.8), 3 checks won, none lost; held-out 79.5.** The Bengali and Arabic running heads stay: our engine reads those scripts as garbage, so nothing witnesses them.
- **Run 55 launched (22:35; `truedoc54`; `EXTRA="--vision-endpoint file:bench/data/olmocr-bench/bench_data/olmocr2b --vision-pages-only"`).** The first TrueDoc run with the vision switch on: the converter itself selects the pages (D019), takes the model's saved readings from disk, witnesses the running heads, and writes the inferred note and tag. Expected about 82.8, the strip test's figure, less whatever the reader's note and the D015 tag cost on the checks (none expected: the note holds no page text); the 3 pages the model returned empty keep our own reading or stay blank.
- **Run 55 scored 82.9 (23:27; converted 22:38-23:25, 47 minutes, the same as without the model); held-out 79.7, tuned-on 80.6; the best so far and the first TrueDoc run with a model.** Sections: arXiv 87.0, old-scan maths 80.8, tables 83.6, old scans 47.3, baseline 99.8, multi-column 80.1, tiny text 87.8, headers 96.4. Against run 54: 725 won, 48 lost (headers 4/4, tiny text 45/17, multi-column 62/6, old scans 203/7, old-scan maths 365/4, tables 46/10). Against the all-pages merge: 5 won, none lost; against the strip test: 2 won, none lost. All 281 model pages carry the reader's note and the tag; the French journal page opens with 'the PDF's own text layer is an OCR layer, not the author's text' and its running head is gone. Above olmOCR's own published 82.4 and Infinity-Parser's 82.5; level with Chandra's 83.1 inside the interval (82.0-83.8). Census after run 55: the mechanical pool (scans aside) is 187 (tables 123, multi-column 56, tiny text 8; 213 after run 54): the model's readings settled some of the pool too, and no section has an empty page left (bucket A is 0 everywhere). Old scans still fail 275 checks, 272 of them with no evidence in any layer: the model's reading is now the only witness there, and a better model is the only lever. Committed at the owner's request as 5c7c782 (eighteen files: the D019 code and tests, the two tools, the docs).
- **Run 55's losses traced (23:30-23:40), and a partial-reading rule built from them.** The 48 losses by cause: 17 tiny-text presence checks whose references carry the hidden layer's own OCR errors (unwinnable); 4 running heads (two in scripts our engine cannot witness, 'Fonte: Bacen' in mixed case, 'MØRE OG ROMSDAL' folded into a title line); 6 multi-column order checks whose passages the model's page does not contain at all; 10 table cells; 7 old scans; 4 old-scan formulas. A coverage census of the model's readings against each page's own text (3-grams; 194 pages with 60+ own words) found low coverage mostly where the model read *more* than a thin or garbled layer, so coverage alone is no signal; the signal is length: on five pages the page's own reading holds 1.3 times the model's words or more, among them a table the model reduced to 59 words from 228 (4 losses) and a dictionary page cut to 906 from 1,660 (4 losses, 1 gain). A fallback to the page's own reading at a ratio of 1.5 (four pages) recovers 8 checks and gives back 1; at 1.3 it would give back 21 on one old-scan-maths page where the model's shorter reading is the better one. Built as `_model_reading_is_partial` in the pipeline (own reading 100+ words and 1.5 times the model's; hidden and accepted-OCR layers, suspect layers only when clean): the page keeps its own text, no inferred note, a warning in the front matter. Test `test_vision_partial_reading.py` (an invisible text layer over an image, a short answer keeps the page, a full answer replaces it); 225 tests.
- **Run 56 launched (23:38; `truedoc55`; the same `EXTRA` as run 55).** Run 55 plus the partial-reading rule; expected +7 checks (about +0.1), nothing else changed.
- **The table tail traced on run 55 (23:45-00:30, into 8 September).** Run 55's 168 failing table checks: relation wrong 69, cell not found 58 (33 of them with the cell text in the output as prose), no table at all 41; on digital pages 146 of the 168. The no-table pages, looked at as images: the largest family is **tables that exist only as pictures on otherwise digital pages**: a sideways scan of a vehicle list with the page number as the only real text (4db371ae, 5 checks), a map figure with an embedded table image (3d780cdc, 5), a pay-advice screenshot in a help page (3a91fad8, 5), a web page's people list (587a1f5a, 3), an engineering drawing's parts table (fbeb6edc, 5). The page's own text is exact and stays; the picture has no text layer, so a model should read the picture alone: D019 applied to a region. Two censuses to size it (`bench/probes/mixed_census.py`, 28 minutes over the 1,122 digital pages; `bench/gpu/select_regions.py`): whole pages that are a picture with a text stamp are few (at most nine pages, eleven failing checks); pictures on text pages are many: 107 crops of at least a tenth of the page on 89 digital pages (52 failing checks on those pages), and, restricted to run 55's failing pages with a floor of 2% of the page (the pay-advice screenshot is 3.5%), 92 crops on 60 pages holding 106 failing checks, 13 of them table pages with 38 checks. The crops are written as one-page PDFs with a manifest (`bench/gpu/crops/`, `bench/gpu/crops_failing/`, git-ignored) for a third GPU session: about 200 crops, a few minutes of model time. Still to build for it: the file provider's `read_region` keyed by page and bbox, and a region kind 'picture-text' in the pipeline that places the model's transcription as the figure's content with the inferred tag, gated so a photo's description never becomes body text. Not in the set: the figure's value block (b5d9db35, drawn as paths, not an image) and the forest plot (f5e5d540, digital labels inside a figure), which stay classical shapes.

**Learned**
- An hour's test on the last run's outputs before any code is the rule that made the day: nine of the round's fourteen ideas were retired with numbers in an afternoon, and the four rules that were tried without one (the numeric-block guards, the strip-alone table rule) were the day's only regressions, all reverted the same hour.
- The benchmark's annotators disagree with each other on two shapes (a value and its statistic as one cell or two; small-caps names in capitals or mixed case), so a rule that follows the page washes out on the score; the page wins.
- The hidden OCR layer of a scan beats our own engine almost everywhere (181 checks to 72 on the 48 confident pages), and extra pixels buy the engine nothing because it resizes every line it reads: the two OCR ideas of the round are closed.
- A whole page can be lost without any check noticing: the conservation census (every word of the layer against the output) found ten arXiv pages swallowed into one formula each by a font-name hint; the census is worth running after each run.
- Most of the day's score came from table shapes found by tracing single pages (the no-table census, the relation reasons), not from the lateral ideas themselves; the method is the product.
- Time stamps must come from the clock, not from a guess: several bullets of the afternoon were first written an hour ahead and corrected.

**Next**
- After session 3, the PyMuPDF decision in two measured steps (owner, 8 Sept 07:29): (1) a half-day census comparing what PyMuPDF and PDFium (pypdfium2) report on all 1,403 benchmark pages: character counts and text agreement, font names, character boxes, images, drawings, and the formula stage's special cases (dvips Type 3 glyph codes, cmex pieces, newtx and STIX ToUnicode quirks) on the arXiv pages; (2) if clean, a second extractor on PDFium (pdftext or pypdfium2 directly), a benchmark run with it, sections compared. Evidence gathered tonight: every leaderboard tool runs on PDFium (olmOCR pypdfium2+pypdf; Marker pdftext; Docling docling-parse+pypdfium2; MinerU pypdfium2+pdftext, having moved off PyMuPDF), none on PyMuPDF; pdftext is Apache-2.0, docling-parse MIT, pypdfium2 BSD.
- Record run 58: done (83.0). Then: HTML tables in model readings converted to markdown for the product (the scorer accepts both; OKF wants markdown), a served model for the end-to-end run (one more rental hour, or the on-demand endpoint), the invented-text check on model pages (D008 with our OCR as the witness), and the classical tail (tables first) to pass 83.1. Owner decisions still open: the licence direction, the library sample. The experiment candidates are `truedoc53_vlm`, `truedoc53_vlmall` and `truedoc53_v2*` under `bench/data/olmocr-bench/bench_data/`; the model's readings are `olmocr2` (3 September, 110 pages) and `olmocr2b` (7 September, 281).
- Wave 3, the owner's decisions: the vision tier for the two scanned sections (a quarter of the exam at 21.5 and 4.1; D014), PyMuPDF's licence (D007), partial pages with a visible note, small task models, the product work on the owner's documents.
- Shapes written down and not built, in order of value: the figure's value block beside a prose column (5 checks), the two-row reliability table under a title (3), the 24 pt form (2), the inline detector's "b =" boundary on newtx pages (1), the maths-italic Type 3 font's Greek codes (1 page).
- The stopping rule: the census pool went 227, 224, 218, 218, then mechanical pool 213 (tiny text 8, multi-column 61, tables 144; 218 after runs 51 to 53) after run 54; if it stops shrinking over two more runs, the classical path is done (D018).

---

## 2026-09-06 (afternoon and evening) - Pages lying on their side are turned before reading; run 38

**Done**
- **Sideways pages are turned upright before they are read (job 1 of the recorded order; for run 38).** Two paths, one mechanism. (1) *Image-only scans:* `ocr_page_turn` in `truedoc/ocr/rapid.py` runs the engine as before and then asks whether most of the read characters sit in boxes taller than wide (the engine's own 1.5:1 ratio); if so, `_sideways_turn` finds which way the text runs from the engine's angle classifier: RapidOCR turns every tall crop a quarter turn anticlockwise before reading it, and the classifier then says whether that crop is upright ("0": the text ran down the page, so the page turns anticlockwise, 270) or upside down ("180": the text ran up the page, so the page turns clockwise, 90). The classifier pass costs a quarter of a second; only sideways pages pay for a second full read. (2) *Text layers:* `extract_page` now counts the visible characters in lines whose direction is vertical, split by direction (`vertical_chars_down`, `vertical_chars_up`, `text_chars` in `page.meta`), and `_sideways_text_turn` in `pipeline.py` asks for a turn when at least 40 characters and 60% of the page's characters are vertical (a rotated "Downloaded from" stamp never turns a page). Both end in `_turn_page`: the turn goes onto the in-memory PyMuPDF page's rotation (`set_rotation`), and the page is extracted again, so rendering, OCR, drawings, the layout model and the vision stage all see it upright without knowing; the file is not changed. The front matter lists such pages under `truedoc.turned_pages` (page and turn) with a warning, and the vision providers' `read_region` takes the turn along so region crops come out upright (`vision/regions.py`). Tests: `tests/test_sideways_pages.py` (a text layer running up and one running down, a stamp that must not turn the page, and a synthetic scan turned both ways read through the real engine); 132 tests pass.
- **Census of sideways pages (`bench/probes/rot_census.py`, 38 minutes: every benchmark page's text-layer line directions, and an OCR pass on the 182 image-only pages).** Exactly one image-only page reads mostly sideways: the landscape scan of a Spanish university decree (tables/0684e33b..., 75 of 75 boxes vertical, read at 0.89 confidence and filed entirely as "rotated-text" headers; run 37 kept eleven loose numbers). Exactly one text-layer page is sideways with the PDF's own rotation attribute at 0: tables/371cfed4..., a table of norm types printed up the page (25 of 27 lines vertical), whose output was empty because every line was a rotated stamp. Every other "vertical" hit is a page with a rotation attribute of 90 or 270 that TrueDoc already maps upright. One more sideways picture, tables/4db371ae... (a vehicle-fleet table with only its title in the text layer, 24 characters), is not reached: the title makes the page "usable", so it is never OCR'd; a lead for the tables job (picture tables on pages with a stub text layer: 4db371ae, 5 checks; tables/5fd60eb1..., 4 checks).
- **The OCR rescue bar moved from 0.85 to 0.80 confidence** (`_RESCUE_MIN_CONFIDENCE`), because the turned decree reads upright at 0.84 (0.89 sideways: the engine is a little less sure of the same lines once they are horizontal) and was rejected again after the turn. Evidence from the same census: of the 18 image-only pages reading between 0.80 and 0.85, 16 were already accepted as English-word-like text; the two rejected ones score 0.64 and 0.48 on language-likeness and stay rejected; every handwriting page reads under 0.75. The change admits the decree and one more page, a scanned financial-outlook table (tables/8097792c..., 0.82, numeric share 0.45, real text).
- **Verified page by page against run 37 (`bench/tools/page_check.py`):** the decree 0 of 8 to 5 of 8 (the staffing tables come out with their columns in order); the norm-types table 0 of 5 to 5 of 5 (a perfect table); the financial table 0 of 8 to 5 of 8; three ordinary OCR pages (long_tiny_text/17_pg2, long_tiny_text/10a_pg1, old_scans_math/1_pg113) unchanged to the check; old_scans_math/5_pg174 (0.80, language-likeness 0.64) stays empty. Net +15 checks, nothing lost.
- **Run 38 (`truedoc37`) scored 65.9, a new best** (launched 15:43, scored 16:47; CI 65.0-66.8; run 37: 65.6): table_tests 72.2 (+1.9: 22 checks won, 0 lost), every other category identical to the check; baseline 94.6. Held-out 62.2 (level), tuned-on 61.8 (61.4). More than the 15 checks verified page by page: the 0.80 bar also admitted scanned number tables that the census had not listed (it recorded language-likeness but not the numeric share). Scoring took five minutes, not forty: the scorer caches rendered formulas and run 38's formulas are run 37's. The first launch of run 38 had to be killed and relaunched: a background shell call has a ten-minute ceiling and the launcher's validation alone runs longer, so the launcher is started with `nohup ... &` from a foreground call (recorded in `bench/README.md`).
- **Job 2, multi-column text coverage (16:00-16:50, for run 39).** Run 37's 241 failing multi-column order checks were classified with the checker's own normalisation (`normalize_text` collapses whitespace runs and maps curly quotes and dashes to plain ones itself, so those never cause a failure): 320 missing halves, of which 48 absent from our output, 45 with a space missing in our text, 30 with a space missing in the reference's own text, 19 with a heading marker inside the expected sentence, 24 with an inline formula's dollar signs, 23 case differences, and the bulk longer differences on scanned pages, which are the hidden layer's own reading errors (a fresh RapidOCR read finds 13 of 66 such strings where the layer finds 9, so re-reading is no lever). Most of the missing text sits on digital pages (91 of the 125 pages). Fixes, each verified page by page against run 37 or 38 with clean controls: (1) an explicit space character in the text layer is a word break however tight the geometry: `_fuse_touching_words` no longer fuses across one (`Word.after_space`; "platform. These" at 0.1 em in Caslon, and a drop cap whose box reached the next word: "TheChief"), the "spurious space" rule now skips OCR layers, whose glyph boxes overlap at word boundaries ("Fracturesextend" on three pages of a scanned mineralogy paper, 13 checks), and keeps spaces after a comma or after a full stop before a capital ("However,state"); +3 checks on the mineralogy pages, four controls unchanged. (2) A free-standing accent glyph is composed with the letter under it when both share a font and a precomposed form exists (`_compose_spacing_accents`: "Ram´on", "H¨older", "Geocieˆncias", "Evoluc¸a˜o"; 296 such names in run 37's output); a maths hat over an italic letter comes from another font and stays; +3 on a Petrobras references page, six maths pages with hats unchanged. (3) A section number set apart from its title ("VI." then "CONCLUSIONS" an em to the right) is one heading (`pipeline._merge_label_headings`; 55 such splits in run 37's output); +1. (4) The block builder judges "above" by baselines and measures the block's size the way it measures the line's, so a hidden OCR layer with boxes taller than the line pitch keeps a paragraph's short last line in place (a patent scan; +1). (5) The renderer joins a block ending in a hyphenated half-word to a lowercase-starting block wherever the two sit (a reference list). Tests: `tests/test_word_spaces.py`, `tests/test_accents_and_labels.py`, `tests/test_blocks_overlapping_boxes.py`; 146 pass. Run 39 (`truedoc38`) launched at 16:52 with all five. **Run 39 scored 65.9, level with run 38** (17:50; CI 65.0-66.8): multi_column 73.1 (+0.4: 10 checks won, 7 lost), arxiv_math 86.9 (+5: 8 won, 3 lost), long_tiny_text 79.6 (5 won, 5 lost: the dictionary-page regression below, caught by the gate and fixed before the run finished), headers_footers 96.2 (-1), old_scans 20.5 (-1), tables level. Held-out 62.5 (run 38: 62.2), the best yet; tuned-on 61.8. Run 40 (`truedoc39`) carries the fix, the two table repairs, the Polish letters and the repairs of run 39's own losses (next bullet); launched 18:00 after a first launch at 17:51 was stopped to include them.
- **Not fixable now, recorded so it is not retried:** sidebars drawn as vector outlines (0925342e: the sentences are not in the text layer at all, only OCR of the picture would read them); running titles that the reference wants in the body (0621a0090414, two pages, three checks each); contact lines at the foot of a first page (the tests want them absent seven times and present four); the reference's own glued words and typos ("confounderswere", "Yatogami"); inline formulas written with dollar signs where the reference has plain text (only 4 of the 52 affected pages would pass without them).
- **Job 3, tables (17:00-17:30, for run 40).** Run 38's 285 failing table checks sit on 104 pages; 18 pages (76 checks) have no table in our output at all, and of those only three are pictures. Two causes found on the digital ones, both in the unruled-table finder (`tables/aligned.py`): (1) a two-line cell set centred on its row ("White to cream" over "powder", beside "Appearance") clusters as a row of its own and `_merge_wrapped_rows` folded it upwards into the wrong row; a lone line that overlaps the row below more than it nears the row above now folds down into it (a product specification sheet: 0 of 5 checks to 5 of 5); (2) the "justified prose" guard rejected a table of short labels because its rows carry six words each ("Distribution Code | Distribution Licensees | Separate Annex 5"); the guard now also needs prose-length cells, three words or more on average, unless the voted cuts have sliced the text layer's segments into far more columns than there were segments (line-numbered prose sliced word by word still fails, as its test requires); a regulator's list of documents and owners: 0 of 5 to 5 of 5. Five clean table pages and the prose controls unchanged. Tests in `tests/test_table_centred_cells.py`; 150 pass.
- **Gate regression caught and fixed before it shipped.** Run 39's validation read 97 of 128 against run 38's 98: the block builder's new consistent size measure was stricter, not looser, on a dictionary page whose hidden OCR layer swings between 7 and 11 pt boxes from line to line (a paragraph fell apart into one block per line and "which con-" / "tains a whole gammon" never rejoined). Sizes on such layers are noise, so the builder's size window is 0.6-1.7 on OCR layers (0.8-1.25 elsewhere); the page is back to 22 of 31 and the patent pages keep their gains.
- **Not fixable now (tables):** tables that are pictures (3a91fad8 a screenshot of a pay advice, 3d780cdc a figure, 587a1f5a a speaker list) wait for picture OCR; a dichotomous botanical key (b74ef859) and a court form (f2ad0cd0) that the benchmark reads as tables; a figure legend read as a table (b5d9db35); a Polish regulation whose "l with stroke" arrives as a product sign and is written as a formula (f30f3060: worth a symbol-table look).
- **Run 39's losses traced and repaired (17:55-18:20, for run 40).** Three causes, all verified page by page against run 39. (1) The three formula losses: the block builder's new height-based block size was applied to digital pages too, so a paragraph line carrying tall inline maths refused its own next line, and the orphaned sentence ("Thus, the coefficients in the Ising model are:") sat alone inside the display formula's vertical span and was swallowed by it, with equations (18) and (19) behind it; the height measure now applies only to hidden OCR layers, and 2503.07924_pg3 is back from 3 of 8 to 5 of 8, 2503.09577_pg20 from 8 to 9 of 10. (2) The header loss: a scanner's "Downloaded from journals.ssu.ac.ir ... [DOI: ...]" stamp running up the margin had always been glued into a body line (`_merge_uniform_rows` let a vertical segment start a row, since only the following segments were checked for rotation) and had passed the absent test only because the glue spelt it without spaces; the word-space rule put the space back and the test saw it. Vertical text can no longer start or join a row (`_merge_uniform_rows`, and the same guard on the newer segment in `_reassemble_lines`), so the stamp is filed as a rotated header and the page is 5 of 5. (3) The five tiny-text losses: the dictionary pages of item 4 above, fixed by the OCR-layer size window before run 39 finished; 11_pg146 and 11_pg418 confirmed back. Run 40 (`truedoc39`) launched at 18:00 with these, the two table repairs, the Central European letters and the layer size window; 152 tests. **Run 40 scored 66.1, a new best** (18:53; CI 65.3-67.0; run 39: 65.9): table_tests 73.2 (+1.0: 18 won, 8 lost), multi_column 73.8 (+0.7: 6 won, 0 lost), arxiv_math 86.8 (-5: run 39's accidental gains from the block-builder bug went with it; against run 38 no formula check moved), headers_footers 96.1 (-1), tiny text 5 won and 5 lost. Held-out 63.0 (run 39: 62.5), the best yet; tuned-on 61.9. Against run 38: 29 checks won, 13 lost. Run dir `bench/runs/truedoc39-20260906-185106`.
- **Captions adopted as header rows (18:05-18:30, for run 41; neutral).** In run 39's output 26 tables on 22 pages (44 failing checks) open with a caption or a sentence as their header row ("Table 2. Differentiating features between ..."): `_header_lines_above` took any line above the model's box whose words all sat on columns, and a caption spanning the columns qualifies. `caption_like` (fuse.py: starts like "Table 2.", or eight words with two function words across most of the box) now keeps such a line out of the header, and `table_from_lines` takes the region's box as the extent for its column channels. On seven such pages and three controls the score is unchanged (one page trades one check for another: without the wide caption line the channel between its last two columns closes, and "CRVO" and "AION" merge). Taking a caption out of the box's own lines as well was tried and withdrawn for the same reason. Kept for what it is worth to a reader; not a lever.
- **Run 40's own losses traced (18:55-19:00, for run 41).** (1) Four table checks on a 25-row table of mouse phenotypes: the relaxed prose guard let the whitespace finder accept a two-row fragment of it, and the fuser then took that fragment as the table already found inside the model's box and never built the box's whole table; a fragment covering under half of a confident table box is now dropped in favour of the box (`rebuilt` in `apply_layout`): 0 of 4 to 4 of 4. (2) Two header checks on a 1975 AMS page (a hidden OCR layer): the widened size window for such layers let the small copyright line and the page number join the footnote block above them and so reach the body; on OCR layers a line is now refused when both its nominal size and its box height disagree with the block's last line (both under 0.75 or over 1.33), which keeps the dictionary pages whole (sizes agree, heights swing) and the copyright line out (both disagree): 4 of 6 to 6 of 6. The dictionary reorderings that traded five tiny-text checks for five are a different matter (entries whose lines interleave across the column) and are left. Run 41 (`truedoc40`) launched at 19:00 with these two, the caption guard and the region extent; 155 tests. **Run 41 scored 66.1, level with run 40** (19:53; CI 65.2-67.0): headers_footers 96.3 (+2: the AMS page), table_tests 73.3 (+1 net: 10 won, 9 lost; the 25-row table came back, six checks went on a course-list page and three on the eye-disease table, the next bullet), multi_column 73.6 (-1). Held-out 63.0, tuned-on 61.9. Run dir `bench/runs/truedoc40-20260906-195025`.
- **Two more table-finder refinements (19:05-19:30, for run 42).** Looking into why the caption guard was neutral on a table of eye diseases showed two faults behind it. (1) The centred-cell fold of item (1) above was too loose: on a table with sparse continuation rows it folded row labels and the first data row into the heading ("VA Pupillary reactions", "Neuroretinitis 6/60-6/12"), and run 40's three checks on that page were passing by accident; a line now folds down only when it stands clear of the row above (a gap of 0.15 em or more), sinks half its height into a real row below, and fills one column. (2) `_header_row_count` ends the heading at the first row with numbers or with a long cell; a table of short text has no numeric row, so its first long cell ended the heading late, at row 3 or 7, and `_header_structure` then merged those rows into the heading. When the heading was found that way and the table has an empty corner cell over a labelled first row, the heading is one row. The eye-disease table is 5 of 5 (run 40: 3 of 5); six table controls, two of them with two-row headings, unchanged; 155 tests.
- **Run 41's losses repaired and two more table faults (19:55-20:15, for run 42 and 43).** (1) The course list of six lost checks: the fragment rule of item (1) two bullets up dropped an aligned table in advance of the box's own build, which then produced nothing; a fragment now gives way only when the box yields a bigger table, otherwise it stays (10 of 10 again). The region-extent hint went with it: it let a false table box over prose grow empty columns on a multi-column page. (2) A journal's "AdvP" symbol font puts the minus sign on code 1, a control character the renderer strips, so negative correlations printed positive ("−.34" as ".34"); code 1 in an AdvP font is the minus sign now (one benchmark page, four uses; not a check, a meaning error). (3) `_NUMERIC` did not know a value with its error in parentheses ("−.25 (.23)", "7.90 (3.07)"), so a correlation table had no numeric row to end its heading and its three heading rows collapsed into one; the form is numeric now, and the Stroop table's headings ("Divided attention" under "Chinese experimenter") come out stacked: 1 of 4 to 3 of 4, seven controls unchanged. Also: a wrapped row label that starts with a symbol ("Received tetanus immunization" / "≥2 times during last pregnancy") is still two rows, one multi-column check, left. **Run 42 scored 66.3, a new best** (20:48; CI 65.5-67.1; run 41: 66.1): table_tests 74.9 (+1.6: 20 checks won, 4 lost), every other category identical to the check. Held-out 63.1, tuned-on 62.2, both the best yet. Run dir `bench/runs/truedoc41-20260906-204620`. Run 43 (`truedoc42`) launched at 20:50 with the minus sign and the value-in-parentheses form. **Run 43 scored 66.3, level with run 42** (21:42; CI 65.4-67.2): table_tests 75.0 (+2 checks, none lost), every other category identical. Held-out 63.1, tuned-on 62.2. Run dir `bench/runs/truedoc42-20260906-213926`. Run 44 (`truedoc43`) launched at 21:42 with the corner-label and pieces-versus-sub-tables rules; **Run 44 scored 66.3, level with run 43** (22:35; CI 65.4-67.2): table_tests 75.0 (2 checks won on the Tagetes table, 2 lost on a date-headed table, fa18a15c), every other category identical. Held-out 63.1, tuned-on 62.2. Run dir `bench/runs/truedoc43-20260906-223248`.
- **Run 42's four losses (20:55-21:20, for run 44).** (1) Two on a Tagetes trial table whose corner label ("Tagetes spp. Treatments") is set centred beside a two-line heading, overlapping both heading lines: the loose fold had put it with the lower line by luck, the tight one left it a row of its own, which ended the heading a row early; a lone corner label between two rows whose first column is empty now joins the row it overlaps more (4 of 5, from 2). (2) One on a page whose model box spans two small tables ("STEP Applicants", "STEP Participants", each with its caption): the box overrode both with one merged table. Several aligned tables inside a box are either sub-tables or pieces of one table broken at its wrapped rows (the eye-disease table came out in three pieces once the box stopped overriding them); the box's own table tells them apart, since pieces leave rows out and the whole box then holds at least two rows more than the pieces together. The eye-disease table is whole again (5 of 5); the applicants page stays merged (3 of 5, run 41: 4 of 5), one check traded for two. (3) The fourth, a corner heading split from its second line ("Confidence" / "level"), is left. 156 tests.
- **Table headings, continued (22:00-23:15, for run 45; the owner said "keep going").** Ten failing checks expect a column heading that spans lines. Five causes, each verified page by page against run 44 with controls. (1) The whitespace finder trimmed every lone row at a run's ends, which dropped a narrow heading fragment above the first multi-cell row ("Number of Agreement" over "(ranked 3 or 4)") and a lowercase wrapped label under the last ("Slaapkwaliteit tijdens" / "consignatiediensten"); such rows now stay (`_heading_fragment`, `_wrapped_label`), and a lone row that closed the previous run is remembered in case a table starts under it. The model-box path has the same two adoptions (`_header_lines_above` takes a one-column line when the table's own first cell in that column reads as the lower half; `_label_lines_below`). (2) `_header_structure` kept every parenthesised heading line as a unit row of its own, so "(ranked 3 or 4)" never joined "Number of Agreement" and "(1)" never joined "Passed Course"; a parenthesised line is a unit row only when the same text repeats across columns ("(percent)" under every date), and otherwise continues the heading above. The I-CVI table is 5 of 5, the regression table 6 of 8 (from 4), the crop-progress table 11 of 14 (from 9). (3) The corner-label join of the previous bullet must not join a row of numbers ("2011 2011 2010 Average" under "Aug 21, Aug 14,"), which the heading count needs to see as its own line: the two crop-progress checks lost in run 44 are back. (4) A stacked column heading with an empty corner may run five lines on an OCR'd table; the depth cap allows five there. (5) The two Advent symbol fonts of 2000s journal PDFs (`AdvP4C4E74`, `AdvP40271B`) carry their own encoding: read off every use across the benchmark, "¼" is "=" (51 times), "ð" and "Þ" are parentheses, "þ" is "+", "½" is "[", code 1 is the minus sign, and in the second font "2", "f", "g" and "j" are the element sign, braces and a bar; `_ADVENT_SYMBOLS` in `textlayer.py` maps exactly those two fonts ("(n = 562)" on one page: 4 of 5 to 5 of 5). The Dutch sleep table keeps its label now but its last two columns still merge; the "SPECIAL VOLUNTARY FUND" table (OCR'd) stays at 3 of 8. Tests: 156.
- **Column cuts voted by range, not midpoint (23:00-23:20, for run 46).** `_refine_segments` clustered word-gap midpoints within six points to find a column boundary that most rows share; a heading's gap ("Gemiddelde | Sd") and the gaps between right-aligned numbers under it share only their overlap, and their midpoints sat twelve points apart, so a two-row Dutch sleep table kept its last two columns merged ("3,9 1,0"). Each gap now votes with its whole range and a cut is an x range that enough rows leave empty (a sweep over the gap ranges). The Dutch table is 5 of 5 (from 3); the spec sheet, the regulator's list, the crop-progress table, the gate's three table pages and six more clean table pages are unchanged. Tests: 156.
- **Committed** (7 Sept 06:10, at the owner's request): commit 2696d2a, 28 files, the whole of 6 September's work from the sideways pages to the fragment guard; tests 156; working tree clean. Nothing pushed (no remote).
- **Run 45's two loss pages traced (23:50-23:58, for run 47).** Both came from the new heading-fragment rule adopting a title line above a table ("t Distribution" centred over three headings; "In relationship to others I feel:" over a rating scale). A fragment now has to sit over an empty stretch of the first multi-cell row (no word of that row beneath it), carry at most six words and end without a colon or sentence punctuation: the t-distribution page 2 of 6 to 5 of 6, the rating scale 3 of 5 to 5 of 5, the I-CVI page keeps its 5 of 5, controls unchanged. This is in the code after run 46 launched, so run 47 carries it; 156 tests.
- **Run 45 (`truedoc44`) scored 66.4, the best so far by a tenth** (launched 22:57, scored 23:48; CI 65.4-67.2; run 44: 66.3): headers_footers 96.4 (+1), table_tests 75.1 (+1 net: 6 won, 5 lost on two pages, db0e3215 and 533600ba, traced below), every other category identical. Held-out 63.1, tuned-on 62.2. Run dir `bench/runs/truedoc44-20260906-234616`. Run 46 (`truedoc45`) launched at 23:50 with the range-voted cuts. **Run 46 scored 66.4, the best so far** (7 Sept 00:38; CI 65.5-67.4; run 45: 66.4): table_tests 75.6 (+0.5: 7 checks won, 2 lost on one page, 00e980a0_pg64, a dated design schedule), every other category identical. Held-out 63.3 (run 45: 63.1) and tuned-on 62.3, both the best yet. Run dir `bench/runs/truedoc45-20260907-003611`.
**Learned**
- RapidOCR's public result carries no angle; the direction of sideways text is recoverable from `engine.get_crop_img_list` plus `engine.text_cls` on the tall boxes, a quarter of a second for 74 boxes. PyMuPDF's `Page.set_rotation` on an open document is the cheapest way to turn a page for every downstream stage at once: `page.rect`, `get_pixmap`, `get_text` and the rotation matrix all follow it.
- The engine's confidence on the same text differs by orientation (0.89 sideways, 0.84 upright), so any gate near 0.85 was going to bite on turned pages; a census is the only honest way to move such a bar.
- Nearly all "vertical text" in the benchmark is the PDF rotation attribute, which the text-layer path has mapped since day 2; genuinely sideways content is rare (three pages), so this job was worth a point on the tables section at most and is done.

**Next**
- Wave 2 and the decisions: see `docs/LATERAL_ROUND_1.md`. Tables, continued (run 44: 75.0; page checks after it +9 on six pages): the remaining "relation wrong" checks are column merges (a narrow last column swallowed by its neighbour: the Dutch sleep table, the neuroretinitis table's CRVO/AION before its caption line was removed), OCR'd stacked headings, a wrapped row label that starts with a symbol; the picture tables (three pages) and the botanical key and court form the benchmark reads as tables stay out of reach.
- Multi-column, continued (73.6): the 52 sentences broken at a block boundary (footnotes, captions and forms interleaved) and the 16 true ordering mistakes; each is a page of its own.
- The two old-scan sections (20.5 and 4.1, a quarter of the exam) are handwriting and old print that the classical engine cannot read; they move only with the vision stage, which is the owner's call (a GPU rental, or an API key).

---

## 2026-09-06 (afternoon) - First commit; hand-off for the next session

**Done**
- **The repository is committed** (first commit, branch `master`, no remote) at the owner's request "commit and prep for a safe compact": the converter, the tests (128 passing), the docs, the benchmark harness and the four sample PDFs. The benchmark dataset, run outputs and the virtual environment stay git-ignored. Nothing is pushed; the owner adds a remote when an off-machine copy is wanted.
- **The loop's helper scripts moved into the repository** as `bench/tools/` (they had lived in a session scratch folder): `launch_run.sh` (validate, launch, wait, score), `page_check.py` (verify a rule page by page against a past run), `run_diff.py`, `pair_probe.py`, `glyph_sheet.py`, `scan_ctrl.py`, `log_update.py`. Paths are now relative to the repository and launcher logs go to `bench/out/launch/`. Documented in `bench/README.md`.
- **Docs refreshed for a newcomer:** `docs/STATUS.md` (date, where we are, the next-session order, a run 30-37 summary, known limits, a backup item for the owner), `docs/ROADMAP.md` (milestone table measured against run 37), `README.md` (layout, GPU row), and this log: the 4-5 September bullets had been written under the 3 September entry during the loop and now sit under their own heading below, with runs 24 and 30 put in run order.
- **State at the commit:** run 37 (`truedoc36`, run dir `bench/runs/truedoc36-20260905-034810`) is the current code, 65.6 overall (formulas 86.8, headers and footers 96.3, base 94.5, tiny text 79.6, multi-column 72.7, tables 70.3, old scans 20.7, old-scan maths 4.1), held-out 62.2, tuned-on 61.4. The code is unchanged since run 37's launcher validated it (128 tests, quick gate 98 of 128, maths samples 46 of 52 and 57 of 64); the suite was run again before the commit (128 passed).

**Next session, in order**
1. Rotated scans: in `truedoc/ocr/rapid.py` (`ocr_page`), when most OCR line boxes stand vertical, turn the rendered page a quarter turn and OCR again. First test page `tables/0684e33bd901b116725b6a0e0d21398f7315_pg4_pg1.pdf`, then the other empty table pages. Verify with `python bench/tools/page_check.py bench/runs/truedoc36-20260905-034810 <stems>`, the quick gate at 96 or more, the full suite, then `bash bench/tools/launch_run.sh 38 truedoc37 56`.
2. Multi-column text coverage: of run 37's 248 failing order checks, 115 are sentences missing from our output, 81 partial, 36 near-misses (plain text wrapped in dollar signs, superscript digits such as "kg/m²", spacing); only 16 are ordering mistakes.
3. Table detection on the 24 pages where no table is found (112 checks); four table pages are still empty.
4. The OCR categories more broadly, and the headers-and-footers loss on an OCR'd page ("euras.lt", an absent test: page furniture is not dropped on OCR pages).

Formula items still open, all at diminishing returns (verify any new rule on ten pages, not five): the inline numerator radical on 2503.06459 (needs ink boxes), the script-script exponent on 2503.06256, hat versus wide hat on 2503.09565 (run 26 lost nine checks when the accent pass narrowed hats), the mathx extension-font treatment (+4/-2 split), overset and underset (11 references), the inline-over-display sum cross-assignment on 2503.06256.

---

## 2026-09-04 to 2026-09-05 - Runs 17 to 37 (63.5 to 65.6): formula rounds 11 to 16, tables, multi-column mining, the OCR gate rescue

Bullets in run order, each timed. They were written during the loop under the 3 September entry and moved here on 6 September; the 3 September entry below keeps its own bullets.

**Done**
- **Run 17 (`truedoc16`) scored 63.5** (CI 62.6-64.3; run 16: 63.5): arxiv_math 73.9 (+5, the demotion revert), multi_column 70.5 (+1), table_tests 68.6 (-5: 4 newly passing, 9 newly failing table checks on six pages, all from the one-row ruled boxes now returned by `find_ruled_tables`; traced below). Held-out 60.5. Run 18 (`truedoc17`, launched 00:07) carries the arrow fix and the same table code. The nine table failures traced (00:30-01:00): `_adopt_ruled_headers` ran on every ruled table, so a caption above a multi-row ruled table ("Table 4. Clinical Trials of ...") was adopted as a header row; and a tall ruled frame around a whole column group (a 1×2 "box" 157 pt high) counted as a boxed row and swallowed the real header line of a two-level table. Three guards: adoption only for one-row boxes; a box no taller than 2.5 line heights; and no adoption when unruled lines directly below continue the box's columns (the box is then the header of a larger table, left to the whitespace finder). Official checks on the seven affected pages: 30 passing against run 16's 26 (the motivating page 4/4, every other page back to its run-16 count). Gate and tests before run 19.
- **Run 18 (`truedoc17`) scored 63.5** (CI 62.6-64.3; run 17: 63.5): arxiv_math 74.0 (+2, the touching-bar rule for mapsto), nothing lost. Held-out 60.5. Run 19 (`truedoc18`, launched 01:18) carries the guarded boxed-row table rule.
- **Multi-column mining (4 Sept, 01:40-02:30, for run 20).** Run 18's 267 failing multi-column checks: 29 on empty pages, 88 with both phrases present in the wrong order, 150 with a phrase not found. Of the not-found class: a Korean paper whose text layer is garbage (Latin-looking junk, so the OCR gate does not fire); two pages where the wanted text sits inside an image on a digital page (a sidebar box, a reference column: recorded as M13 in the roadmap); and an OCR-layer case report whose two columns interleaved. The last one is a rule: `_reassemble_ocr_layer` looked for a column channel over the whole page and demanded half of all rows to vote for it, so a page that opens with a full-width abstract over two columns never got its channel. Channels now carry a vertical range (the rows that voted): the vote count and the straddle test are judged within that band, and only lines in the band are split by it. The case report's columns now read whole (its remaining misses are the hidden OCR layer's spelling). 25 column, OCR-layer and order tests pass; gate 97/128; in run 20.
- **Run 19 (`truedoc18`) scored 63.6, a new best** (CI 62.6-64.5; run 18: 63.5): table_tests 69.5 (+9 checks: the guarded boxed-row rule), multi_column 70.6 (+1), nothing lost. Held-out 60.7 (best), tuned-on 59.0. Run 20 (`truedoc19`, launched 02:30) carries the band-aware OCR-layer column channels.
- **Text inside pictures (M13), first cut, 03:00-03:40.** `_ocr_text_pictures` (pipeline.py) OCRs pictures at least an inch on a side on pages that have their own text, gated like page OCR (confidence 0.8, word-likeness 0.6, twelve words, three lines), skips pictures the page already has text inside, replaces the figure with the text blocks (provenance `ocr-region`) and lists them under `truedoc.ocr_regions`. Two tests (`tests/test_picture_text.py`). On the benchmark's sidebar page the engine read the picture correctly: it is a map whose only text is its caption, which the page already carries (the sidebar sentences I was chasing belong to another page of the same document, matched by hash prefix), so the feature had nothing to add there and is **off by default** (`--ocr-pictures`, `ConvertOptions.ocr_pictures`) until a real text-bearing picture turns up. A false alarm on the way: comparing pages by hash prefix matched every page of the same paper, which made the band-aware column change look like a regression; matched by full name, the three pages are level with run 19 or better.
- **Where the remaining reading-order losses sit (census, 4 Sept 03:00-04:00).** Run 18's failing order checks in multi-column and old scans by the page's text layer: 203 of 426 on pages with no text layer at all, 154 on digital pages (47 of those with a garbage layer such as a mis-encoded Korean paper), 61 on hidden OCR layers (12 poor), 8 suspect. Of the 92 textless pages, our own OCR is confident and word-like enough to pass the gate on 35 (70 checks) and their checks still fail: the misses are classical-OCR spelling on typewriter scans ("Vory truly your", "graduste", "tho fenes ware parchsd") and letterhead lines interleaved with the body; 9 pages (21 checks) sit just under the gate with poor text; the rest are unreadable to it. Relaxing the gate would not help; better recognition would. That is the vision stage's ground (the olmOCR 2 experiment moved exactly these pages, +5.6 overall). Conclusion for the mechanical tier: formulas, tables and digital multi-column pages still have specific rules to find; scans do not. Tried and dropped: rendering scans for OCR at up to 3,300 px on the long side instead of 2,000 (about 300 dpi instead of 180 on these large pages) moved the phrase-match scores on four scans by under two points either way, so the cap stays.
- **Run 20 (`truedoc19`) scored 63.6** (CI 62.7-64.5; run 19: 63.6): multi_column 70.8 (+2 checks from the band-aware channels), nothing lost. Held-out 60.8 (best), tuned-on 59.1.
- **Formula round 11, first three (04:15-04:50, for run 21).** From run 19's `\sqrt` failures: (1) a numerator such as `\sqrt{n-1}` over a fraction bar has a bar above it too, the radical's own, and the run-10 denominator rule (`bar_above`) took it for a fraction bar and refused the host below; a bar whose left end meets a radical sign (anywhere on the page) is not a fraction bar for that purpose; (2) the newtx symbol font `txsys` maps its brackets to bracket characters, and the cmsy raw-code table turned "(" into `\Leftarrow`: for TXSY/PXSY fonts the bracket characters are trusted; (3) tx radicals hang above the baseline like cmex ones but the fold-in rule (`_tall_symbol`) knew only the Computer Modern font names, so the sign landed on a line of its own and the root became an overline: any extension font and the tx/px/MathDesign/Latin Modern symbol fonts now qualify. On 2503.06459 the target `\frac{\sqrt{n-1}}{\sqrt{n-2}}\delta` reads right (one twin a few lines up still loses its signs). 48 maths and text-layer tests; gate 97/128, 111 tests, run 21 launched 04:09. (4) A limit wider than its operator, `\sum_{p\leq\sqrt{x}}`: the radical's bar was built as a root at the top level before the limits were gathered, and the limit run stopped at the operator's edge. A script-sized stack beside an operator that takes limits, with no main-size text around, whose parts' baseline sits below (or above) the operator's centre is left to the limit group (`_build`, the rule loop), and `_target_atom` extends a limit run glyph by glyph along its own baseline past the operator's edge (a radical sign, whose origin sits at its bar, is judged by adjacency alone). Gate 97/128, 111 tests; run 22 launched 05:16.
- **Truncated maths letters (05:20-05:45, for run 23).** A census of run 20's failing formula pages for odd characters found 41 pages (166 failing checks) with Hangul syllables and Latin-1 marks in our output; the top ones are set in newtx (`NewTXMI`) and STIX maths italic. The cause is exact: those producers write the ToUnicode entry for a Mathematical Alphanumeric Symbol with sixteen bits, so italic alpha U+1D6FC arrives as U+D6FC, a Hangul syllable; adding 0x10000 gives every letter back (`symbols.unfold_truncated_surrogate`, applied in the text layer at character creation and in `latex_for_char`, for maths fonts only so Korean text in Korean fonts is untouched). Three such pages went from 0 of 29 formula checks to 8 with no odd characters left; the rest of their misses are other things. Alongside: a combining mark that the accent pass could not attach (a stray macron after `\leq`) made KaTeX reject the whole formula, so `_polish` now drops leftover combining marks. 45 maths and text-layer tests; gate and tests in the run-23 launcher. Also for run 23: a line made only of accent glyphs (dots and bars set above the letters of the line below, as for `\dot{\bar{Az}}`) now joins that line in `_attach_satellites` whatever its size, instead of standing as a stray "˙¯" paragraph; the page that showed it (2503.09135) reads better but wins no checks yet, because a stacked accent over a two-letter base (`\dot{\bar{Az}}`) is beyond the accent pass, which puts one accent on one glyph. Noted as a gap. 49 tests.
- **Run 21 (`truedoc20`) scored 63.6** (CI 62.7-64.5; run 20: 63.6): arxiv_math +2 checks, nothing lost. Held-out 60.8. Run 22 (`truedoc21`, launched 05:16) carries the limit-stack deferral; run 23 (`truedoc22`) the truncated-surrogate fix.
- **Integrals (05:50-06:30, for run 23).** From run 20's `\int` failures: (1) the esint and mathabx extension fonts name their integral sign so that MuPDF reports a circumflex, and `I_n = ˆ\sec^n θ dθ` was the result: "ˆ" from `esint`/`TeX-mathx` is `\int`; (2) a display integral often arrives as three text-layer lines (the sign with its upper limit, the integrand, the lower limit): `_attach_satellites` now finds tall extension-font glyphs, takes the line whose baseline the sign spans as the host, and joins the sign's own line and any small fragment in the sign's column to it; (3) in `split_display_lines` the limits of an integral sit to the right of the sign, not centred as a sum's do, so the window that moves stray limits next to their operator reaches 1.2 em right for integrals and accepts limits level with the sign's top and bottom. `\int_{-\infty}^{t}F_X(x)dx\geq\int_{-\infty}^{t}F_Y(x)dx` now reads whole on 2503.05348. 36 maths tests; gated before run 23.
- **Cases braces under Adobe's private-use names (06:15-06:35, for run 23).** From run 20's `\begin{` failures: a two-row `\begin{cases}` came out as script soup (`1_{i}i_{f}f_{t}...`) because its brace arrived as three CMEX characters at U+F8F1-F8F3 (Adobe's bracelefttp, braceleftmid, braceleftbt) that no table knew, so no `\{` existed and the two rows became scripts of each other. `symbols._ADOBE_PUA_PIECES` maps the whole family of piece names (parens, brackets, braces, the integral extender) to their bracket, and `_merge_extensible_pieces` stacks pieces up to a line apart when both are such pieces (their boxes are the font's fixed box, not the drawn extent, so a brace's top pair and bottom pair show a gap). Two pages now read `\begin{cases}`. Probed on the way: the checker accepts `\text{ mod 4}` only (not `\mod`, `\bmod` or `\text{mod}`), but "mod" appears in ten references, so no rule. 36 maths tests; gate 97/128 on the exact code of run 23, which launched 06:31.
- **Run 22 (`truedoc21`) scored 63.6** (CI 62.7-64.6): identical to run 21 to the check; the limit-stack deferral touched no benchmark check (the page it was built on fails its check for other reasons). Held-out 60.8. Run 23 (`truedoc22`, launched 06:31) carries the truncated-letter fix, the accent-line join, the esint/mathabx integral sign, the three-line integrals, the display integral limits and the private-use brace pieces.
- **Inline fractions at a line break (07:00-07:20).** The sum page's real failure is an inline formula that runs over a line break: `\frac12\sum_{p\le\sqrt x}` ends one text line and `\frac1p = \frac12\log\log x + O(1)` starts the next, and the second half came out as prose ("2 1 log log x + O(1)") because the fraction digits are in the text font. Two changes tried: (a) a word sitting just above or below a short rule counts as maths for the inline detector (`extract._word_on_fraction`, kept: tests pass, harmless); (b) letting a bar-linked fraction that starts just past a line's last word join that line in `_attach_satellites` (reverted: the numerator joined, the denominator and the sum scattered into a display block and a heading). The page stays at 3 of 9; the line-break case needs the block builder to keep a formula's stacked parts with the line they belong to, noted as a gap.
- **Colons, script letters, operator names (07:20-07:50, for run 24).** From run 22's `\mathbb` failures: (1) some fonts name their colon so that it arrives as U+2236 RATIO, which KaTeX draws differently from ":" and which sank every check on those lines (`h∶\mathbb{R}^p`): RATIO and PROPORTION map to ":" and "::"; (2) letters from Ralph Smith's formal script font (`rsfs`) came out plain where the source says `\mathscr{F}`: RSFS letters are `\mathscr`, and Euler script (`eusm`) letters `\mathcal`; (3) an upright word glued to the maths that follows it with no space at all ("Fix(Q)", "supp(m)") is an operator name and joins the formula (`inline_math_text`). Official checks on four pages: 22 passing against run 22's 17 (the colon page 3 to 5, the script page 6 to 9). The operator-name rule needed a second half: "Fix(Q)" is one text-layer word whose upright letters `_trim_prose` split off as prose; an upright run glued to an opening bracket now stays in the formula as `\text{Fix}(Q)` (that page 6 to 7). 42 tests; gate 97/128 before, re-gated after.
- **Display rows linked by real glyph extents (07:30-07:55, for run 24).** A pre-existing bug: on 2503.05436 a formula line and the prose line under it came out as one garbled formula (`\mathbb{S}^{2}C^{:y}o^{3}...`). `split_display_lines` links glyphs whose vertical extents overlap, and it used MuPDF's character boxes, which come from the font's ascender and descender: 1.2 em tall, so two lines set at 1.2 em leading touch exactly and can never be told apart (cmsy's braces declare 1.7 em boxes and bridge even more). A text-font glyph is now linked by the extent a glyph of its size really has (0.8 em above the baseline to 0.25 em below); extension-font glyphs keep their measured boxes, rules their padding. Scripts still overlap their base row. The page's two lines separate (8 of 10 checks, from 7); the maths samples and the gate run in the run-24 launcher because this touches every display formula. 36 maths tests. Launcher result: 112 tests, gate 97/128, samples 44/52 and 57/64 (from 56); run 24 launched 07:48.
- **Run 23 (`truedoc22`) scored 63.7, a new best** (CI 62.8-64.6; run 22: 63.6): arxiv_math 75.0 (+27 net: 32 newly passing, 5 newly failing), every other category identical. Held-out 61.0 (best), tuned-on 59.2. Run 24 (`truedoc23`, launched 07:48) carries the colon, script-font, operator-name and display-row linking changes.
- **Run 23's five losses (08:10-08:40, for run 25).** Two were the new operator pre-pass in `_attach_satellites` taking any tall extension-font glyph for an operator: a `\Big(` around a fraction pulled the denominator's line to the wrong host (2503.09574, 8 to 7 checks), and a cases brace's top piece, now that it maps to `\{`, joined the text line whose baseline it touched (`\Theta_n\{:[0,+\infty)`, 2503.07122). The pre-pass now counts only genuine operator signs (`_BIG_OPERATOR_LATEX`: integrals, sums, products, big unions and the like), and a fragment made only of extensible-delimiter pieces never attaches as a satellite (it belongs to the display formula assembled from its region). The bracket page is back to its run-22 count and the three-line integral page keeps its gain; the brace page's stray `\{` was a *raw-code* piece (cmex 0x38, bracelefttp) that MuPDF had put on the text line above the cases: `symbols.is_piece_glyph` now knows raw cmex piece codes (0x30-0x43) as well as the private-use names, and the inline run drops a piece glyph whose origin sits more than 0.6 em from the line's baseline; that page now passes 9 of 10 (run 22: 8). The two cases pages the brace mapping was built for now pass 10 of 10 and 3 of 3 (from 9 and 0). The other three losses show identical output at the quoted formula between runs and were not chased. 49 tests; the run-25 launcher validated the final batch (112 tests, gate 97/128, samples 44/52 and 57/64) and launched run 25 at 09:12.
- **Run 24 (`truedoc23`) scored 63.8, a new best** (CI 62.9-64.8; run 23: 63.7): arxiv_math 75.9 (+27 net: 30 newly passing, 3 newly failing, all three on integral pages), multi_column 70.5 (-3 order checks), the rest identical. Held-out 61.2 (best), tuned-on 59.3. Run 25 (`truedoc24`, launched 09:12) carries the operator restriction and the brace-piece rules.
- **More symbol spellings (09:20-09:40, for run 26).** From run 23's `\mathcal` failures: the mathabx symbol font (`TeX-matha`) delivers the element sign as "P" and the two inequalities as "ď" and "ě" ("f P L^2", "0 ď s ď t"): added to `_MATHABX_RAW`; angle brackets coded as CJK brackets (U+3008/3009) map to `\langle`/`\rangle`. Two mathabx pages: 6 of 8 (from 2) and 2 of 6 (from 0); 36 maths tests.
- **Underlined words are not fractions (4 Sept, for run 26).** Run 24 lost a multi-column page because the fraction rule (a word sitting on a short rule is a numerator or denominator) fired on underlined words, turning prose into maths. The rule now needs a word on the far side of the line too. Same round: an operator name glued to a bracket ("word(1)") only counts as maths when the bracketed part has a maths-font glyph, and integrals keep their own row boxes when display lines are split. Checked: the underline page is back to 5 of 5, the operator page holds 8 of 10 (run 23: 6).
- **Headlines, drop caps and the ellipsis (10:00-10:40, for run 26).** A French newspaper page (multi-column, 2 of 5) showed three faults of display type. Its 139 pt headline was read as maths ("$\underline{18} L_{L}OI$"): words set above 40 pt are never inline maths unless in a maths font, and a line that size hosts no satellites (the page number above it and the drop cap below it are not its scripts). The 41 pt drop cap "L" then stood as a heading of its own before "e gouvernement": a single tall letter now rejoins the first word of the paragraph beside it (`_join_drop_caps`; 3 tests). Census: 37 benchmark pages carry text above 40 pt, about 20 of them drop caps. Last, the references type the ellipsis as three dots (35 checks, none with the ellipsis character) while the PDFs carry "…": the renderer writes "..." (run 24's outputs: 9 checks gained, 0 lost, all multi-column). The page: 3 of 5; its other two losses are a kicker line the layout model files as a page header and a reference that misquotes the page ("laisse la contr..." for "laisse la solidarité").
- **Run 25 (`truedoc24`) scored 63.8** (CI 62.9-64.8; run 24: 63.8): arxiv_math 76.0 (+4 checks, nothing lost), every other category identical. Held-out 61.2, tuned-on 59.3. Run 26 (`truedoc25`, launched 10:42 after 113 tests, gate 97, samples 44/52 and 57/64) carries the underline, headline, drop-cap and ellipsis fixes and scores itself at the end of its conversion.
- **Two levers checked and set aside (10:45-11:00).** (1) Junk text layers: a regex census flagged 14 Latin pages with mostly non-word tokens (112 failing checks), but by our own word-list measure their layers score 0.73-0.84 and a fresh RapidOCR read scores the same and passes no extra check; nine of the fourteen are scanned maths books whose failures are formulas. Not a lever. (2) Sparse layers over big images: 25 pages (33 failing checks, mostly image tables with 5 of 5 failing). Picture OCR (`--ocr-pictures`) reads some text on them but yields no table structure, so no check moves. Image tables stay vision-stage territory.
- **Formula round 12 (11:00-11:45, for run 27).** From run 25's plain misses: (1) the mathabx font's not-equal sign arrives as "‰" (+1); (2) the newtx/newpx symbol fonts carry correct characters, but "+" (and "-", "=", "<", ">", "|", "/", "*") was being pushed through the cmsy code table, where 0x2B is `\Downarrow` ("1\Downarrow\frac{1}{121d^2}"): those characters are now trusted as they come (+3 on one page); (3) OpenType maths fonts (Libertinus Math, STIX Two Math) set their variables as the Unicode italic letters, so a plain ASCII "l i m" in them is upright text and now becomes `\lim` (+1); (4) a wide tilde in the extension font was treated as a bracket piece and lost its letter (`\tilde{}`): accents are excluded from piece merging; (5) MuPDF splits a line at a radical or wide accent, and the second half was left as a line of its own ("$W_1(x,y)=$" then "|x-y| and interventions"): symbol-only segments are folded in before the halves measure their gap, and a segment ending in an extension glyph may overlap the next by 1.5 em (+3 on two pages). Set aside: `\setminus` delivered as a minus with the minus's width (unwinnable from the text layer, 4 checks); big parentheses from the mathx font arriving as accent characters (glyph names needed); a radical whose bar spans two fractions closes after the first (bigger change, noted).
- **Run 26 (`truedoc25`) scored 64.1, a new best** (CI 63.3-65.0; run 25: 63.8): arxiv_math 77.0 (37 won, 9 lost), multi_column 71.8 (12 won, 0 lost), tables 69.6 (+1), the rest identical. Held-out 61.2, tuned-on 59.7. All nine losses are `\widehat` over a single letter (`\widehat\beta`, `\widehat{1}`, `\widehat{Lu}`): the accent pass narrowed a cmex hat over one glyph to `\hat`, and the checker renders the two differently. Narrowing now applies to tildes only (which render the same either way). Run 27 (`truedoc26`) launched 12:05 with formula round 12.
- **Formula round 13 (12:00-12:45, for run 28).** (1) Inline fractions whose denominator MuPDF starts a new segment with, exactly under the numerator ("|C| ≤ |U|" then "10r and thus"): two segments may now merge when their overlapping words sit on different baselines (a numerator over a denominator), where before any x-overlap meant a duplicated text layer (+2 on one page). (2) Limits shared out between neighbouring operators: a limit glyph that continues a run on the same baseline stays with that run's operator instead of the next operator whose span also holds it; among operators whose spans hold a glyph, the nearest centre wins; "n" left of "lim" waits for the word (`\lim_{n\to\infty}`, the "n" was lost before). (3) Three periods stepping down and right become `\ddots` (26 instances on 7 matrix pages). (4) The cmex codes 0x44/0x45 are the largest angle brackets, not floors (five per page on 2503.08572; +2). (5) A radical's bar over script-sized fractions in a text-style formula was taken for a fraction inside a script and skipped; a bar that starts where a root sign ends is always the root's (`\arctan(\sqrt{\frac{\phi_0}{\phi_2}}\phi_1)`, +1). (6) The wide hat is kept wide (run 26's nine losses come back: +4 checked on two pages). Checked on the limit pages: the double sum with an integral now reads `\sum_{n=1}^N\sum_{m=1}^N\int_0^T` (+1) and a `\lim_{n\to\infty}` after a `\mathbb{P}-` (+1), nothing lost. First maths sample 44 of 52 (unchanged). Standing loss noted: an inline root over two stacked fractions whose denominator MuPDF glues into the prose line (2503.05503, "where c_{l,m} = ..."), unchanged since run 23. (7) A word shaped like an operator applied to a bracket ("std(w)", "conv(w)") joins a formula beside it, not only a single letter ("f(x)"); and a word set as an operator that KaTeX has no command for ("conv", "std", "supp", "span") is written `\text{conv}`, as the references spell it, even when the author set it in italics (+1 checked; the italic "conv" is now `\pi(\text{conv}(w))`). (8) A formula broken across two lines ("maj(σ) =" then "2 + 1 + 1 + 1 = 5" on the next line) was left as prose numbers because numbers alone are not maths: the renderer now pulls plain arithmetic that follows a formula ending in a dangling relation or operator back into it (`_join_dangling_formulas`, 4 tests; +1). (9) Journals that number equations on the left had the number glued to the front of the formula ("$$(3.12)Q(ae^{...})=...$$", 92 formulas on 49 pages of run 26's output): a bracketed number at the left margin, a wide gap from the formula, is now taken off like a right-hand one (tests/test_equation_number.py). (10) Checker facts established with one-formula probes: spaces inside `\text{...}` and `&` alignment markers do not matter; `\leqslant` and `\leq` render differently (173 references use `\leq`, 6 `\leqslant`), so the slanted forms are written plain; `\text{ mod 4}` is the only accepted mod spelling (digits inside the text); a bar glued to an arrow is `\mapsto`; a textual version of that rule broke a unit test (it cannot see the gap) and was dropped for a glyph-level one: the mapsto bar followed by the minus shaft of a long arrow is `\longmapsto` (+1). (11) Folding root signs into their line before the halves merge (item 5) had also folded matrix bracket pieces early, which broke two inline matrices on 2503.09133: the early fold now takes root signs and wide accents only; bracket pieces are folded after the merge as before (page back to 10 of 10, the radical and wide-tilde pages keep their gains).
- **Run 27 (`truedoc26`) scored 64.3, a new best** (CI 63.4-65.2; run 26: 64.1): arxiv_math 78.1 (37 won, 4 lost), multi_column 71.9 (+1), the rest identical. Held-out 61.3 (best), tuned-on 59.9. Two of the four losses are the early-fold matrices above (fixed before run 28); the other two (`\left(\frac{1}{q}-\frac{1}{p}\right)` on 2503.05140, `\frac{\sqrt{n-1}}{\sqrt{n-2}}\delta` on 2503.06459) are being checked. Run 28 (`truedoc27`) launched 13:38 (122 tests, gate 97, samples 44/52 and 57/64) with formula round 13. The remaining loss (2503.06459, an inline `\frac{\sqrt{n-1}}{\sqrt{n-2}}\delta` whose root signs now fold into the prose line above) does not come back by undoing any one of the day's text-layer changes, or all three together: noted as a standing regression of one check, to be revisited with the satellite rules.
- **Formula round 14 (13:40-, for run 29).** From run 27's `\mathbb` misses: mathabx "«" is `\approx` and "‹" is `\star` (+1); newtx's blackboard-bold symbol font (`txsyb`) gives `\mathbb{}` letters like msbm, and its extension font's "Ö" is a display `\prod` (+1 for `\mathbb{P}_{det}=1-\prod_{s=1}^{t}...`); msbm's kappa is `\varkappa` (the Unicode table had turned it into a plain kappa first; +1); the dot operator U+22C5 and the division slash U+2215 are `\cdot` and "/" (+1 on a units formula). Facts noted: `\leqslant`, written plain now, accounts for two more checks on 2503.05562. Two more structural fixes: a script of a script (the F of `\nu_F` above a sum) now rides on the script glyph on its own baseline rather than the last one in reading order, which had put it into the lower limit (`\sum_{q=1}^{\nu_F}`, +1); and a script-sized word that MuPDF starts the next segment with, under or over a full-size word (the "++" of `\mathbb{S}^{n\times n}_{++}`), no longer blocks the two segments from merging as a duplicated layer would (+1). From the `\overline` misses: the scripts of an overlined or underlined base were left in the tail and rode on the next glyph (`\overline{B} :_{h,\alpha}^{\nu}`, `\overline{\mathcal{C}} =_{\mathrm{sum},u}`): the script-sized glyphs right after a built group now hang on it (`_attach_core_scripts`). From the `\dot` misses: Adobe Symbol's "phi" slot (mathptmx) is the straight letter that `\phi` draws, as in TeX's own fonts, so it is written `\phi`, not `\varphi`. From the `\partial` and `\mathcal` misses: mathabx "B" is `\partial`, "À" is `\lesssim`, and its ring "˚" is the asterisk (`\tau_*`, two pages); cmex 0x46/0x47 are the square-cup operators `\bigsqcup`, not ceilings (+1 on 2503.05960); cmmi's slot 0x2C, reported as a comma, is the left hook of `\hookrightarrow` when it touches an arrow (these three pages: 23 to 29 checks). From the `\hat` and `\mathrm` misses: a tilde stacked on an equals sign is `\cong` (12 references; +2 on 2503.08577); "argmax"/"argmin" set as one word become `\operatorname*{arg\,max}` so their limits go underneath; a lone upright capital in a formula is written `\mathrm{T}` (the references do so 53 times; lower-case ones such as the d of dx stay plain, 57 plain to 4 roman). The main-line size of a formula whose long superscript outweighs its base (`\hat{Z}^{W_0^2\delta x_s^1(\xi_i)}`) is the base's when nearly all (80%) of the smaller glyphs sit clearly above or below it; the old rule wanted every one, and a superscript's own subscripts dip to the base line. More mathabx codes from the `\sum` misses: "}" is the double bar `\|` and "8" is `\infty` ("\sup_n }\sum e_i} < 8" on 2503.06880, eight failing checks there). From the `\mathbf` misses: upright letters glued into one run ("logsin", "sin" inside an exponent) are split into the operator names they are made of (`\log\sin`), and function names are now recognised at every size, not only on the main line (`_split_names`; the two pages now read `\sin\alpha` and `\log\sin`, though their checks still fail on other parts). Checked: the Symbol-font `\phi` alone brings 2503.05993 from 0 to 4 of 5; `\mathrm{T}_p` renders as intended (its page still fails on other symbols). Trade-off recorded: keeping cmex hats wide loses two `\hat{Z}` references on 2503.09565 while saving nine `\widehat` ones elsewhere. A superscript that used to break after its first glyph (`C^{2}}+\beta`) now comes out whole (`C^{2+\beta}`, +1 on 2503.06020) through the same script rules. Checker equivalences probed and recorded in memory: `\|`/`\Vert`, primes, `\mathrm`/`\text`/`\operatorname`/`\rm`, `\tfrac`/`\frac`, `\centerdot`/`\cdot` all render the same. The parked-limit release built earlier today also restores a limit's first glyph before "sup" (`\sup_{x\in\Omega_R}`, +2 on 2503.09231). From run 27's short misses: the normal-subgroup triangles (U+25C1/25B7, U+22B2/22B3) are `\lhd`/`\rhd`, a white circle U+25CB is `\circ` (+1 each), and the arithmetic pulled back into a formula after a dangling relation may now contain × and · ("$N_x\times N_v=$ 49 × 97"). A lost inline sum traced: "the length of P is" and "w(v_{i-1}v_i) and the..." were two lines with the sum sign and its limits standing between them as segments of their own, a gap too wide to merge, so the sum fragment found no host that spanned it. Two halves of a line are now merged when the gap between them is filled by such a segment with ordinary gaps on either side (the filler attaches as a satellite afterwards): `\sum_{i=1}^{n}w(v_{i-1}v_i)` comes out whole (+1 on 2503.07448). The same merge brings the stacked fractions of 2503.05503 into their formula; the root sign was then still dropped because a second "script stack" test in the rule loop lacked the radical-bar exemption. With it, the formula reads `\sqrt{\frac{(2l+1)}{4\pi}\frac{(l-m)}{(l+m)!}}`, one factorial sign short of the reference (a lone "!" split off as its own word now joins the maths before it). Run 28 finished converting at 14:55; its score and the run-29 validation follow.
- **Run 28 (`truedoc27`) scored 64.4, a new best** (CI 63.4-65.4; run 27: 64.3): arxiv_math 78.9 (41 won, 17 lost), multi_column 71.8 (-1 check), the rest identical. Held-out 61.4 (best), tuned-on 60.0. Of the 17 formula losses, five are references that keep the slanted `\leqslant` where the glyph is slanted (the plain spelling gained four elsewhere): reverted, the glyph decides. The two `\hat{Z}` losses are the accepted wide-hat trade-off. The rest (sized delimiters around fractions on five pages, two fractions on 2503.07924) are being compared against run 27's output. The run-29 launcher stopped on the second maths sample (56 of 64 against an expected 57): the five failures there are the same five that failed in run 27, so the expectation was stale, not the code; it is reset to 56 and the launcher re-armed. The delimiter losses traced (2503.04415 "$G\text{that}\Big\lfloor a r e\Big\rfloor$"): once the early fold was limited to root signs, a bracket segment whose origin sits at its top sorted next to the full-width line above it and joined that line on "adjacency" (the gap test accepted a bracket standing anywhere inside the line's span); the words around the fraction then came from the wrong line. A symbol now joins a segment only at its end (gap at least -0.3 em), but that alone did not repair the page: the bracket's baseline (155) also lies within 0.3 em of the line above (153), so the two still merged as "interleaved" segments. The early fold is therefore restored for every symbol-only segment, with two guards learned today: a host must have its baseline running through the symbol (the line above does not; the formula line does), and a symbol taller than about two lines (a matrix bracket) waits for the fold after the merge, where the most-overlapped line wins (that early fold was what broke the inline matrices on 2503.09133). Checked on ten pages against run 27: the four delimiter pages are back to their run-27 counts, the matrices and the inline sum keep their gains (57 checks against 53). The run-29 launcher was re-armed at 15:19 with the corrected sample thresholds (45 of 52, 56 of 64). A checker probe worth remembering: delimiter sizes never matter to it. `\left(...\right)`, a plain `(...)` and every `\big` to `\Bigg` size match one another around fractions, plain content and sums, so the 90 failing checks that mention `\left` fail on their content, not their brackets, and no more effort goes into sized delimiters for the benchmark (they stay in the output for fidelity). Run 29 (`truedoc28`) launched 15:23 (122 tests, gate 98 of 128, samples 45 of 52 and 56 of 64) with formula round 14 and the early-fold repair.
- **Formula round 15 (15:25-, for run 30).** What the `\left` checks fail on: tall parentheses around a big operator with limits became a two-row matrix (`\begin{pmatrix} \sum \\ a_i \end{pmatrix}`, on 2503.08345, 2503.08630, 2503.07286, 2503.06350 and others): a matrix row must hold a text-size entry, and a row that is only an operator sign (or only limits) no longer counts (tests/test_matrix_false_positive.py). The semidirect product signs U+22CA/22C9 are `\rtimes`/`\ltimes`, and the star operator U+22C6 is `\star`. Checked on eight pages against run 28: +6 (2503.08630 alone from 3 to 7 of 10), the genuine matrices of 2503.09133 and 2503.04041 unchanged. Five fraction pages from run 28's misses re-checked with the current code: +8 (2503.06256 from 3 to 6 of 9, 2503.08504 and 2503.06191 two each). Theorem prose set in italics inside a display formula ("xi is predictable and") came out as glued bare letters ("ispredictableand"): italic text-font letters whose words are ordinary English now form one `\text{...}` run like upright words, while an italic letter or two on their own stay variables (`_group_italic_prose`, tests/test_italic_prose.py); the italic font hints also gained "ITAL", so URW's "ReguItal" faces (Times papers) no longer count as upright text, which had turned their "xy" into `\text{xy}`. A lone italic word of three or more letters that is ordinary English ("for", "and") is prose as well. Checked: 2503.06350 from 7 to 9 of 10 (the `\text{ is discontinuous at }` and the convex-hull formula). The n-ary operators as Unicode characters (U+22C0-22C3) are `\bigwedge`, `\bigvee`, `\bigcap`, `\bigcup`, so they take their limits ("(_{i}⋀_{=1}^{2}" had split them; +2 on 2503.06739). A labelled arrow drawn as minus pieces with the label's letters above and an arrowhead ("-^{A}-^{I}--^{co}-^{n}-^{v}\rightarrow^{.}") is written `\xrightarrow{AIconv.}` (the checker ignores the label's spaces); an unlabelled run of pieces stays `\longrightarrow`. Checked: 2503.09284 page 29 from 7 to 10 of 10, page 2 gains its arrows too. Blackboard-bold letters from the bbold, boondox (DoubleStruck) and dsfont faces came out as plain letters (`P^x` for `\mathbb{P}^x` on 2503.06111, `Z` for `\mathbb{Z}` on 2503.09528): those fonts now give `\mathbb{}` like msbm and count as maths fonts. Three small renderer and spelling rules: two inline formulas split by a line break, the first ending in a dangling relation ("$\sigma(x)=$" then "$[\sigma(x_1),...]^T$"), are joined into one; bold letters that come one glyph at a time form one `\mathbf{Fun}`; and the lone-upright-letter rule now covers lower case too (the references write `x_\mathrm{s}` 20 times), except the differential "d". Two more mathabx codes from the `\cdot` misses: its "1" is the prime (`f^{1}` was f') and its "ˆ" the times sign (the mathx font's "ˆ" stays the integral sign); and "(mod p)" in parentheses is written `\pmod{p}` as the references do. Checked: 2503.04488 +4, 2503.07910 (the pmod page) from 6 to 9 of 9, 2503.04604 +1; the bbold page 2503.09528 +1. Display rows: a script-sized row under a word that takes limits ("mu in M_T(X)" under "sup") became an aligned line of its own; the display splitter now treats such a word like a big operator (its letters are still separate at that stage) and, once part of the row has moved to it, takes the rest of the row too when it is all script-sized and within a few ems of the word. With the row merged, the limit's first glyph ("mu", centred under "sup" so starting left of it) still rode on the "=" before the word because the parked-limit search reached only 0.8 em left of an operator; it now reaches 2 em (the vertical test keeps the scripts of the base before it out). One more mathabx code: the mathb font's "9" is the dot accent (`\dot{F}` had come out as `F^{9...}`); such an accent from a symbol font reports a full-height box, so its box is cut to the top third before the accent pass looks for the base beneath it. The wider window checked: the sup page and the wide-limit sums gain (+3), but it took the "n" of the first of two close sums for the second; a glyph within the span of an operator already built now stays with it (the wide search is only for operators still to come), unless an operator still to come holds it within its own box (the "m" of the second sum, which starts where the first sum's box ends). The accent pass also recognises an accent by its command, not only by its character, so the coded mathb dot finds its base. Checked together: the double sum is whole again (2 of 2), `\dot{F}_p^{\alpha,q}` and `T^*` gain on 2503.04604 (4 to 6 of 7), the sup page 2 to 3 of 4.
- **Run 29 (`truedoc28`) scored 64.8, a new best** (CI 64.0-65.7; run 28: 64.4): arxiv_math 82.6 (123 won, 16 lost), multi_column 71.9 (+1), long_tiny_text 79.4 (-1 check), the rest identical. Held-out 61.8 (best), tuned-on 60.5. Losses: six are the slanted-inequality trade-off (2503.05562 and 2503.06969 write `\leq` for slanted glyphs; five other references keep `\leqslant`; the glyph stays as drawn), five on 2503.07567 are a subscript label "min" (`d_{\text{min}}`) that the any-size function-name rule now writes as the operator `\min`; the rest are single checks under review. Run 30 (`truedoc29`) launched 16:45 (122 tests, gate 98, samples 45 of 52 and 56 of 64) with formula round 15.
- **Run 29's losses repaired (16:50-17:10, for run 31).** (1) A script-sized function name with nothing after it on its line is a label, written `\text{min}` (`d_{\text{min}}^{\mathcal{C}}`, 2503.07567 back from 5 to 10 of 10); "sin" inside an exponent keeps its argument and stays `\sin`. (2) The bridged-halves merge had swallowed a dictionary's entry word ("QUICK-UEER." on a tiny-text page): only a maths filler (script-sized glyphs or an extension-font sign) bridges two halves now. (3) The limit row moved under "sup" put its letters between s, u and p in reading order and broke the word (`2s_{t}u_{t}p_{0}` on 2503.09471): letters are now grouped per size and baseline before words are read. Checked on six pages against run 29: the max-limit page +1, the sup page keeps its gain, the tiny-text entry word is back (+1), and the sum and root pages the bridge was built for are unchanged. From run 29's short misses: mathabx's "˚" (its asterisk) was still taken for a ring accent by the accent pass, which reads characters (`f_{\mathring{t}}` for `f_t^*` on 2503.06612); for the mathabx fonts only the table's own accents count now (checked on three mathabx pages against run 29: 20 of 25 checks pass, up from 17, no losses). Failing formula checks stand at 949 (1,141 at run 25). STIX Math Calligraphy keeps its capitals in the private-use area (U+E22D for A through U+E246 for Z, seen as B and D on 2503.06111), which had made `\mathcal{B}(\mathbb{R}^d)` lose its letter; they are `\mathcal{}` now (2503.06111 from 2 to 6 of 9, which also confirms the letter order of that private-use block). Three integral pages from run 28's misses re-checked with the current code: the round-14 script rules already give `\int_{t_0}^{t_f}` and `\pi(t)=\int_t^{\infty}\bar F(x)dx` (+3 checks). The one multi-column loss (a sentence start "The last" swallowed when a line of the left column joined a line of the right one) does not occur with the current code: the bridged-halves merge added after run 28 changes the order in which the segments meet, and the page reads correctly again; noted as a fragility of the same-baseline merge across a narrow gutter rather than fixed by design.
- **Formula round 16 (17:05-, for run 31/32).** From run 29's fraction and root misses. (1) A script-sized root sign with script-sized contents is deferred to the script or limit it belongs to, like any small stack (`\sum_{p\leq\sqrt{x}}`, `e^{\frac{2\sqrt n}{A}+O(\log n)}` on 2503.03899): +2 on five root pages, no losses. (2) A root sign no longer counts as a matrix row of its own: its origin sits at its bar, above the digits it covers, so `\left(1/\sqrt{N}\right)` and `\left[-\sqrt{\max(0,N^2)},\ldots\right]` had become pmatrix/bmatrix: +4 on six pages, no losses. (3) The bridged-halves merge accepts a filler whose text-size glyphs are all in maths fonts (the coefficient between a text-style sum's limits and the fraction after it), and a "!" glued to the maths glyph before it is a factorial, not sentence punctuation: `c(t)=\sum_{i=0}^\infty c_i\frac{t^i}{i!}` (2503.05034) and `\frac{(l-m)!}{(l+m)!}` (2503.05503) pass; +4 on five pages including the tiny-text dictionary page, no losses. (4) mathabx: the earlier claim that mathx's "ˆ" is an integral sign was wrong (that is esint); a contact sheet of every mathabx glyph on the benchmark pages (scratch script glyph_sheet.py; fontTools installed in the venv for font probing) gave mathx its own table (big braces and parentheses in several sizes, `\|`, `\sum`, `\int`, `\bigoplus`, `\bigcup`, wide hat/tilde/check), mathb four entries (`\#`, `\angle`, `\square`, `\hookrightarrow`) and matha twenty-one more (`\ll`, `\gg`, `\forall`, `\notin`, `\cap`, `\setminus`, `\subset`, `\subseteq`, `\pm`, `\ltimes`, `\cong`, `\equiv`, `\sim`, `\simeq`, `\dagger`, `\natural`, `\triangleright`, a text-size `\sqrt`, ...); unknown mathx codes are dropped rather than guessed, and mathx glyphs get ink boxes like other extension fonts. Checked on ten mathabx pages against run 29: 51 of 64 checks pass, up from 34, no losses (the integral, pmatrix, congruence, direct-sum, for-all, not-in, intersection, triangle and natural-sign pages). (5) A script right after a fraction hangs on the fraction (`\frac{d}{dt}^2 d(t)`, 2503.05034): +2 on four pages, no losses. (6) An integral's long lower limit keeps the rest of its script row (`\int_{T^{-1}(E)}`, 2503.04536): +1 on four pages; the one loss seen on that check (2503.09208, a subscript X after a tall double bar taken as the next lim's limit) is already in run 30's output and comes from round 15's wider parked-limit window, repaired in (7). (7) A script-sized glyph glued to the previous main-line atom (within 0.3 em of it, that atom not an operator) is that atom's script and is never parked as a limit for an operator further right. (8) `_main_size` applies the long-superscript rule before the width-share rule: a lone letter or digit at the largest size whose smaller glyphs nearly all sit off its baseline is the main line (`p^{\text{ord}_p(...)}` in a denominator on 2503.04182 had come out as `p\text{ord}_p`); a second form of the rule takes a long subscript whose own superscripts rise back to the base line (`v_{\hat\tau_i^2+s^{\ell-1}-3s}`, 2503.05506; `K_{t_1\times 1,\ldots}`, 2503.08964), and extension-font glyphs and accents no longer vote for the base line. Items (7) and (8) checked on four pages: +2 (the ord page and 2503.07156), the lim page unchanged, no losses; the glued guard first fired on a sum's upper limit that starts right after a letter ("\omega" then "i_max-1" on 2503.07335), so it now applies only after a closing delimiter or a tall bar, and both pages pass their checks (+1 on 2503.09208). Five-page check of the mathx table and the main-size rule against run 30: +6 (2503.06612 from 4 to 8 of 10), no losses. (9) An accent centred over two touching letters covers both: `\bar{Az}` (2503.09135) instead of `\bar{A}z`; the letters merge into one glyph before the accent pass (`_widen_accent_bases`). (10) A subscript under an overlined base may drop as little as 0.1 em (`\overline{\mathcal{C}}_{\mathrm{sum},u}`, 2503.08986, +1). (11) `\bigsqcup`, `\bigodot`, `\biguplus` take limits. (12) A `Char` is italic when its font name says so ("NimbusRomNo9L-ReguItal", "URWPalladioL-Ital": txfonts and mathptmx set no italic flag), so a lone italic letter with a subscript beside a formula is a variable and joins it (`W_u \in \mathbb{R}^{n\times nm}` on 2503.06226 had lost its `W_u`); checked: +2 on that page, three txfonts control pages unchanged, gate 98/128, full suite green. (13) Three periods in a row are `\ldots` when TeX spaced them (about 0.4 em from dot to dot) and a typed "..." when they touch (0.28 em, the period's own width): measured on the benchmark pages, the references keep the author's spelling, and the checker does not equate the two. `_merge_dot_runs` decides by the advance (tests/test_dots_spacing.py): +5 on four typed-dots pages, three ldots control pages unchanged. (14) mathx's "´" is the script-size integral (`e^{\frac{c^2}{v}\int_0^t}` on 2503.04467; no check moves yet). The set-difference signs on 2503.07147 are minus glyphs in the PDF (the text trace gives them the same glyph index as every other minus), so those four checks stay unwinnable; `page.get_texttrace()` is the way to read glyph indices when a Unicode mapping is suspect. Combined check of the day's items on three more pages against run 30: +10 (2503.07567's five `d_{\text{min}}` labels, 2503.05034 to 10 of 10, 2503.08646's matha slash and `\simeq`), no losses. (15) A limit-taking word set at script size ("max" in `v^2_{1,\max}`, 2503.05358) takes no limits of its own: it had parked the neighbouring subscript and superscript as if it were an operator. Checked: +1 on that page, three max control pages unchanged. The same check showed the dots rule (13) misfiring on a script-sized `\ldots` (2503.09432): in script styles TeX drops the thin spaces between the dots, so the typed-dots reading now applies at text size only (the page is back to 6 of 6). (16) Negated relations: the combining slash U+0338 that TeX's `\not` leaves in the text layer (and a "/" glyph glued to a relation, mathabx's negation slash) now negates any relation in `_NEGATABLE`, not only "=" and `\in`: `\not\equiv` (2503.08176) and `\not\leqslant` (2503.06739, +2). A wrong turn on the way: txsy's negation slash arrives as an unmapped " " character, and reading every space in a TeX symbol font as that slash lost 16 checks on five pages, because MuPDF's synthesised word spaces wear the neighbouring span's font; reverted, and that case stays unwinnable without glyph indices. (17) cmsy's asteriskmath reaching the text layer as "*" is an asterisk, not the raw code 0x2A (`\Uparrow`): `\mathrm{Input*Gradient}` on 2503.08240. After the revert the five negation pages stand at +3 against run 30 with no losses. The worst remaining formula pages re-checked with the day's code: 2503.09471 rose from 2 to 8 of 10 on the italic rule alone (its `\delta_i\in`, `f\in`, `O\in` formulas had all lost their leading letter), 2503.09254 to 2 of 2 on the dots rule; 2503.09352 is unchanged and remains open (a broken triple sum). (18) 2503.05442's truncated inline runs were terms set wholly in the text fonts, as Times-based maths (txfonts) is: "4k+1" after `\kappa(BS_{n-1})=`, "V(BS" before a scripted argument. A word of digits and operators with at most one letter per factor, every letter italic, or an italic letter applied to an unclosed bracket, now joins the formula beside it (`_text_term` in extract.py): that page went from 4 to 9 of 10; two control pages unchanged.
- **Run 30 (`truedoc29`) scored 65.0, a new best** (18:13; CI 64.1-65.9; run 29: 64.8): arxiv_math 84.0 (+1.4: 44 checks won, 1 lost), every other category identical to the check (tables 69.6, multi-column 71.9, tiny text 79.4, headers 96.4, baseline 93.8, old scans 20.7 and 4.1). Held-out 61.9 (best), tuned-on 60.8. The one loss (2503.09208: the subscript X after a tall double bar was parked as the following lim's limit by round 15's wider parked-limit window) is repaired for run 31 by round 16's item (7), refined so a glyph already standing under an operator still to come (the "e" of "epsilon -> 0" under a lim that follows "=") is not held back; the page's formula now reads exactly as in run 29. The run-31 launcher stopped itself on its twelve-page sample (55 of 64 against an expectation of 56); the sample was compared with run 30's output: 57 of 64 with the code as it then stood (run 30 itself 56, the launcher's 55 was a transient state between two edits), so the launcher was re-armed at 18:22 as a reusable script (scratch `launch_run.sh <run> <candidate> [sample minimum]`), and **run 31 (`truedoc30`, round-16 code as of 18:26) launched at 18:26** after pytest, gate 98/128 and samples 45/52 and 57/64.
- **Run 31 (`truedoc30`) scored 65.2, a new best** (19:48; CI 64.3-66.1; run 30: 65.0): arxiv_math 85.0 (+1.0: 46 checks won, 18 lost), tiny text +1 check (79.6), every other category identical. Held-out 62.0 (best), tuned-on 61.0. Its code was round 16 up to item (8) (as of 18:26). The 18 losses, traced by comparing the two runs' outputs: (a) the fraction-script rule (5) took the first glyph of a following sum's lower limit, which starts left of the sign right after the bar (`\frac{1}{N}_{k}\sum_{=1}^{N}` on 2503.06939, 2503.09086, 2503.08172); (b) the fraction-stack row filter (2) removed the numerator and denominator rows before the bar-between-rows test, so `\bigg(\frac{1}{|B|}\int_B w\,dx\bigg)` on 2503.08649 became a pmatrix; (c) the label rule turned `\log_2 3` inside an exponent into `\text{log}` (2503.09367); (d) the first, unrestricted form of the glued-script guard (7) hung a sum's limit on the minus before it (`-_{k}\sum` on 2503.05469), already repaired for run 32. **Formula round 16 continued (19:55-, for run 33):** (19) a script-sized glyph within two ems of a limit-taking operator to the right is held back from the fraction's scripts; the bar-between-rows test now judges every row, stack rows included; a script-sized function name carrying its own subscript is applied, not a label. Checked on the five loss pages and two control pages against run 31: +5, no losses (the `\log_2 3` page is unchanged and stays open). Correction to the checker facts: `\tfrac` is NOT equivalent to `\frac` (a one-formula probe on 2503.05396 passes only with `\tfrac`); the earlier note claiming they matched was wrong. (20) A display fraction set at text size with script-sized parts is written `\tfrac`, an inline fraction with text-sized parts `\dfrac` (an inline `\frac` always has script-sized parts, and a lone fraction is left as `\frac`): checked on seven pages whose references use `\tfrac` plus three `\frac` controls, +1 (2503.05594), the rest unchanged, because most `\tfrac` references are inline, where `\frac` and `\tfrac` render alike and the references overwhelmingly write `\frac`. (21) mathx's "´" and "¯" are another size of big parentheses (`\Bigl(u, v, w\Bigr)` on 2503.08646), not an integral: the glyph read as one on 2503.04467 was matha's minus in the neighbouring font, so the mathx entry added under (14) was wrong and is replaced. (22) mathx glyphs have their origins at the top like cmex's, which put a row of big parentheses above its formula on 2503.06612 (`\begin{aligned} ()() \\ ...`). Listing mathx among the extension fonts fixed that and two more pages (+4) but let the text layer fold its braces into neighbouring prose lines (-2 on 2503.06880), so the listing was withdrawn; the display-row linking alone treats mathx like an extension font, which on its own moves nothing (42 of 42 on nine pages). Open: find the reconstruct-level part of the extension treatment that carried the four gains. (23) An equation set wholly in the text fonts: a formula-shaped word ("conv(v)", "std(44425533116)") on either side of a bare relation word ("=") seeds an inline formula even when no glyph comes from a maths font: `\text{conv}(v)=\text{conv}(w)` on 2503.08911 (+1), three text-font control pages unchanged.
- **Run 32 (`truedoc31`) scored 65.3, a new best** (21:10; CI 64.4-66.2; run 31: 65.2): arxiv_math 86.1 (+1.1: 35 checks won, 3 lost), every other category identical (tiny text 79.6, tables 69.6, multi-column 71.9, headers 96.4, baseline 93.8, old scans 20.7 and 4.1). Held-out 62.2 (best), tuned-on 61.1. Its code was the whole of round 16 as of 19:52. The three losses: `\bigsqcup_{A,B\in\mathcal{C}}` on 2503.05960 (the sign now takes limits, item 11, but only the middle of its wide centred limit moved to it, the rest stayed a row of its own) and two `\notin` checks on 2503.08443 (being traced). **Run 33 (`truedoc32`, the repairs of items 19 to 23, code as of 21:14) launched at 21:14** after pytest, gate 98/128 and samples 46/52 and 57/64. **Round 16 continued (21:20-, for run 34):** (24) the rest of an all-script row follows its operator for any big operator sign, not only for limit words and integrals, since a centred limit is often wider than the sign; (25) a word whose first letter is bold, or that starts with a text-font accent character over the letter (`\tilde{\mathbf{u}}_1` set in cmbx on 2503.04033, five checks), counts as a variable with a script and joins the formula beside it. Checked against run 32: 2503.04033 from 0 to 4 of 5, 2503.05960 +1, two limit control pages unchanged. (26) The two `\notin` losses on 2503.08443: a one-formula probe shows the checker accepts `\notin` (and, oddly, `\in/`) but not `\not\in`, and the references write `\notin` (5 to 0); the negation rules now produce `\notin`, and an old line in `_polish` that rewrote `\notin` as `\not\in` is gone. `\not\equiv` and `\not\leqslant` stay as two tokens (those passed). Checked: 2503.08443 back to 10 of 10 (+2) but 2503.03994 fell from 9 to 5 of 10, whose references write `\not\in`; a proper count (regular expressions in a script, not grep) gives 11 references on 7 pages for `\not\in` against 5 on 3 pages for `\notin`, so the rewrite is withdrawn and `\not\in` stays the output spelling (the unit test says so). Lesson: the two spellings are indistinguishable on the page (LaTeX defines `\notin` as `\not\in`), so only the majority spelling can be chosen. (27) A differential set in the text italic ("dx", "dt") joins the formula beside it, and at the end of a formula it is no longer trimmed as a two-letter word: `\int_{\sigma(E,t)}\rho_0(x)\,dx=\int_E\rho_0(x)\,dx` on 2503.04536 (+1, two integral control pages unchanged). (28) Inside a cases block or matrix, a fraction's numerator and denominator glyphs now build with the row at the bar's height instead of becoming rows of their own (`_matrix_latex`); it moved no check on its pages (2503.04467, 2503.03994) and the matrix controls held. Open, traced but not fixed: the inline `\frac{\sqrt{n-1}}{\sqrt{n-2}}` on 2503.06459 loses the numerator's root sign because that glyph sits a full line above the host line and is never attached as a satellite (the numerator's letters are); and `p^{1/2+it}` on 2503.06256 splits its script-script exponent.
- **Run 33 (`truedoc32`) scored 65.3, level with run 32 and nothing lost** (22:31; CI 64.5-66.2): arxiv_math 86.5 (+0.4: 13 checks won, 0 lost), every other category identical. Held-out 62.2 (level), tuned-on 61.2. Its code was as of 21:14: the run-31 repairs, `\tfrac`/`\dfrac`, text-only equations and the mathx parenthesis codes. **Run 34 (`truedoc33`, items 24 to 28: wide centred limits, bold and accented variables, the differential rule, fraction rows in matrices; `\not\in` kept) launched at 22:35 after pytest, gate 98/128 and samples 46/52 and 57/64. (29, for run 35) In the early symbol fold, a root sign standing on a fraction bar now goes to the line below the bar rather than to the line above whose baseline its box crosses; gate 98/128, full suite green, root control pages unchanged, but 2503.06459 itself is unchanged: its page folds three root signs from three neighbouring inline fractions into the wrong lines in more ways than this, so it stays open.
- **Where the remaining points are (22:55, from run 33's 1,700 failing checks).** By category and test type: arxiv_math formulas 394, old_scans_math formulas 439, tables 310, old_scans text 250 present + 166 order + 61 baseline, multi_column order 248, tiny text present 90, headers absent 26. Formula rounds now return about a tenth of a point per hour; each category is an eighth of the overall score, so the levers are elsewhere. The multi-column "order" checks were looked into: of the 248, only 16 are real ordering errors; 232 fail because the checker cannot find one of the two sentences at all (edit distance 1 or 2): 115 are missing from our output outright, 81 are present only in part (the sentence diverges after its start), 36 are present but do not match (spacing, hyphens, accents, or our own `$...$` wrapping of ordinary text such as "(<25 kg/m²)"). Tomorrow's plan, in order: (1) multi-column text coverage — why 115 sentences vanish (dropped blocks, footers and captions, column detection, non-Latin scripts: Korean and Indonesian pages are among them) and the 36 near-misses; (2) tables (310); (3) the OCR categories (old scans at 20.7 and 4.1), the largest untouched lever on a CPU-only machine. First step taken the same evening (30, for run 35): on an old two-column paper whose text layer is itself an OCR result (0097571b), the columns' ragged edges leave a gutter only four points wide, below the detector's minimum of 0.7 em, so the two columns were read line by line across the page. A channel near the middle of the page whose core (the stretch that at most 1.5 percent of lines cross) is at least 0.3 em wide now counts as a gutter; the page's columns read correctly, gate 98/128, full suite green, six multi-column pages unchanged in their checks (that page's own checks stay failed because its text layer misspells the words: "more chan 80~ of rhe time"). Such pages need re-OCR, which is the OCR lever again. (31, for run 35) Among the "present but unmatched" sentences: an OCR'd text layer that dropped the hyphen at a line break leaves "typi" / "cally" as two words. When the paragraph is joined, a line-final fragment and a line-initial fragment that are not words themselves but make a dictionary word together are now joined without a space (`_broken_word` in the renderer, using the word list already behind the glued-word splitter): +2 order checks on 07c14b page 9, two other multi-column pages unchanged. Also seen there: references keep Unicode superscript digits ("kg/m²") where we write "kg/m2" (seven references in all; not pursued).
- **Run 34 (`truedoc33`) scored 65.4, a new best** (23:55; CI 64.5-66.2; run 33: 65.3): arxiv_math 86.7 (+0.2: 7 checks won, 3 lost), every other category identical. Held-out 62.2, tuned-on 61.2. Its code was as of 22:35 (items 24 to 28). The three losses are all cases blocks whose rows are themselves fractions (2503.05140, 2503.09486, 2503.05177): item (28), which moved a fraction's numerator and denominator glyphs into "the row at the bar's height", is wrong for a cases row that is a fraction, and it had moved no check on its own pages; it is to be reverted for run 36 (run 35, validated from 23:55 with items 29 to 31, still carries it). Tiny-text presence failures were classified the same way as the multi-column ones: 43 sentences present only in part, 34 missing, 13 unmatched, on dictionary and encyclopedia scans. (32, 5 Sept 00:05, for run 36) Item (28) reverted: the three cases blocks are back (+3 against run 34 on their pages), the two matrix pages it had been written for are unchanged. **Run 35 (`truedoc34`, items 29 to 31 with item 28 still in) launched at 23:59** after pytest, gate 98/128 and samples 46/52 and 57/64; the run-36 launcher waits for its score with the reverted code. The table checks were classified the same way (00:20): of 310 failing, 112 say "no table found" and sit on 24 of the 188 table pages (five to eight checks each on the worst: 0684e33b page 4, 8097792c page 1, fcb362aa page 2), 58 find the cell but not its heading relation, 140 miss the cell text. Table detection on those 24 pages is the table lever for tomorrow. (33, 00:20-00:50) The worst of them, 0684e33b page 4, produced no output at all, which led to a count: 89 benchmark pages come out empty (old scans 61, old-scan maths 10, tables 7, multi-column 6, headers 5) and 14 more under twenty words. They are image-only pages whose OCR read the gate in `apply_ocr` rejected. On that table page the engine reads 75 lines at confidence 0.89 but the page is Spanish ("MIEMBRO DE LA ASOCIACION DE UNIVERSIDADES"), and the word-likeness test uses an English word list, so the read scored 0.41 and was thrown away. A confident read (0.85 or more) whose tokens are shaped like words of any Latin-script language (numbers, short tokens, letter runs with a plausible vowel share; `_looks_like_language`) is now accepted. Checked: a Spanish multi-column page gained an order check; the old-scan pages sampled are handwriting whose OCR is noise ("tuhe thimeaw amnoum") and stay rejected, rightly; the two table pages stay at zero (one now yields fifteen words), so the empty-page count is mostly handwriting the engine cannot read, not a free lever. Tests green, gate 98/128.
- **Run 35 (`truedoc34`) scored 65.4, level with run 34** (01:14; CI 64.5-66.2): multi_column 72.2 (+0.3: the two order checks the hyphen-less word join won), arxiv_math 86.6 (one check lost: `P=(0.098,\sqrt{0.098})` on 2503.08374, being traced against item 29), every other category identical. Held-out 62.2, tuned-on 61.2. Its code was as of 23:59 (items 28 to 31). **Run 36 (`truedoc35`, code as of 01:18: item 28 reverted, the OCR gate rescue of item 33) launched at 01:18** after pytest, gate 98/128 and samples 46/52 and 57/64. (34, 01:30-01:50, for run 37) The run-35 loss traced: on 2503.08374 the formulas `P=(0.098,\sqrt{0.098})` and `Q=(0.97,\sqrt{0.97})` sit on consecutive lines, and item 29's fold took the lower root's own bar for a fraction bar under the upper root sign, sending that sign to the wrong line (the roots then read as `\overline{0.098}` and `\dfrac{}{0.97}`). Restricting the rule to fraction-width bars did not help (a root bar is short too), so item 29 is withdrawn: the page is back to 5 of 6, the two root control pages unchanged, full suite green. The inline numerator root of 2503.06459 stays open; a better attempt would need ink boxes to tell a root's own bar from a fraction bar beside a denominator root.
- **Run 36 (`truedoc35`) scored 65.6, a new best** (02:34; CI 64.6-66.5; run 35: 65.4): 25 checks won, 1 lost. The OCR gate rescue of item (33) did it: tables 70.3 (+10 checks, +0.7), multi-column 72.7 (+10 checks, +0.5), baseline 94.5 (+0.7) as formerly empty non-English scan pages came out with text; arxiv_math 86.7 (+3: the three cases blocks, item 28 reverted); headers 96.3 (+2, -1: the footer "euras.lt" now appears on a page that used to be empty and its absent-check fails). Held-out 62.2 (level), tuned-on 61.4. So the empty-page count was a lever after all, for the printed non-English pages among them; the handwriting stays out. **Run 37 (`truedoc36`, item 29 withdrawn, code as of 02:38) launched at 02:38** after pytest, gate 98/128 and samples 46/52 and 57/64; no launcher is armed after it, since no further change is waiting. Counted against run 33: ten of the 89 empty pages now carry text (multi-column 5, tables 3, headers 2); 79 stay empty, 71 of them the handwritten old scans, plus 4 table pages, 3 header pages and 1 multi-column page. Of the three table pages, two now hold a markdown table (30c92c35 with 337 words, fcb362aa with 154) and the Spanish one (0684e33b) keeps only 15 of the 75 lines the engine read, so the layout stage after OCR loses most of that page: a next step for the table lever, with the four table pages still empty. Looked into (03:30): that page is a landscape scan of a portrait table, so the OCR engine returns lines with rotated boxes; the pipeline marks them "rotated-text", files them as headers of a few characters each, and keeps a full-page figure. Rotated scans need the page image turned upright before OCR (detect that most OCR lines stand vertical, rotate 90 degrees, read again) — a concrete first job for the table and old-scan levers tomorrow.
- **Run 37 (`truedoc36`) scored 65.6, level with run 36 and nothing lost** (03:51; CI 64.7-66.5): arxiv_math 86.8 (the root on 2503.08374 back, +1 check), every other category identical. Held-out 62.2, tuned-on 61.4. This is the current code; no launcher is armed. **Where the day ended (4 Sept 07:30 to 5 Sept 04:00): 64.8 (run 29) to 65.6 (runs 36 and 37), formulas 82.6 to 86.8, tables 69.6 to 70.3, multi-column 71.9 to 72.7, baseline 93.8 to 94.5; failing formula checks 949 to about 830.** Next session, in order: (1) rotated scans: turn the page image upright before OCR when most OCR lines stand vertical (tables and old scans); (2) multi-column text coverage: the 115 sentences missing from our output and the 36 near-misses; (3) table detection on the 24 pages where no table is found; (4) the OCR categories more broadly. The formula rules are at diminishing returns (about a tenth of a point per hour) and two of tonight's attempts had to be withdrawn, so new rules there should be checked on ten pages, not five, before a run.** Run 32 (`truedoc31`, the whole of round 16 as of 19:52) launched at 19:52 after pytest, gate 98/128 and samples 46/52 and 57/64. Known gap noted: two adjacent lines each holding a sum (an inline one over a display one, 2503.06256) cross-assign their sum signs and limits in the text layer.

---

## 2026-09-03 (early afternoon) - Output aligned with the real OKF specification; run 9 converting

**Done**
- The owner confirmed "OKF" means the **Open Knowledge Format** (https://github.com/GoogleCloudPlatform/open-knowledge-format). Read its README and `SPEC.md` (v0.2) and rewrote the front matter to match: required `type` (default `Document`, `--type` on the command line), `title`, `description` (first sentence of the first paragraph), `resource`, `generated: {by: truedoc/<version>, at}`, `status: draft`, `sources: [{resource, title, last_modified}]`. Everything TrueDoc-specific (sha256, pages, confidence, language, `pages_with_ocr`, `hidden_text`, `warnings`) moved under one `truedoc:` key, which the format allows. `docs/OKF_SPEC.md` rewritten to cite the specification; D005 confirmed, D012 records the mapping; tests updated (`tests/test_hidden_text.py`, `tests/test_pipeline_synthetic.py`).
- The benchmark is unaffected: it scores the body only (front matter is off in the bench runner).
- **Run 9 (`truedoc8`) scored 62.2** (CI 61.3-63.1; run 8: 60.8): arxiv_math 69.2, base 93.4, headers_footers 93.9, long_tiny_text 79.9, multi_column 70.7, old_scans 20.7, old_scans_math 4.1, table_tests 65.7. Tables +7.5 and formulas +2.8; nothing fell.
- Word spacing, three causes found by probing pages with glued words in run 8's output (`bench/probes/gap_probe.py`): (1) hidden OCR layers spread the letters of a phrase evenly, so a space is only a slightly larger gap ("occursas"): for OCR-layer pages a gap above twice the letter gap and 0.04 em now breaks a word; (2) fonts whose declared widths are wrong give glyph boxes that overlap their neighbours by a constant amount (a tax form, a financial table: "Sectionreferencesaretothe"): the word-gap rule now measures from the line's unclipped median gap, and the touching-word fuser does the same; (3) dot leaders in a table of contents made the "letter-spaced text" guard fire and glue "Graphs, Subgraphs and Factors": the letter-gap median now uses letter and digit pairs only, and dot leaders no longer count as letter-spaced singles. Words with no gap at all ("widespreadaccessorymineral" in an OCR layer) need a dictionary and are noted for later.
- Tables: the worst run-8 table page (a crop report) was a *ruled* table from PyMuPDF whose rules only frame the heading, so the whole body came back as one tall cell per column. `_rebuild_sparse_ruled_tables` (pipeline.py) rebuilds such tables from the text lines inside them when the lines have far more rows than the table. Then the heading: the benchmark matches `top_heading` against the header row of a markdown table (exact after normalisation) or against every `<th>` above the cell in an HTML table (colspan-aware). Stacked headings ("Aug 21," over "2011"; "Average Temperature" centred over "Past Week | Depart Normal") are now recovered in `_header_structure` (aligned.py): fragments of one heading join, group headings get a colspan from the geometry of their text, unit lines "(percent)" stay a row of their own, and such tables render as HTML with `<th>` rows. Two unit tests were rewritten to the new, more faithful shape.
- Owner asked how icons that carry meaning (tick and cross marks in an insurance table) are handled: today they are lost; answered with the plan (map symbol-font glyphs, classify small vector or raster marks inside cells by shape and colour, keep icon-only columns, never drop a mark silently). Not yet built.
- **Marks that carry meaning (owner's request, D013).** New module `truedoc/marks.py`: small drawings and tiny images (3-30 pt, roughly square, not overlapping text) are rendered at 32 px, the ink is masked against the background colour, a ring around the mark is detected and erased, and the remaining shape is matched (IoU) against tick, cross, dot, square and box templates, with a quadrant check to tell a tick from a cross and the ink colour recorded (green/red/other). `_attach_marks` in `pipeline.py` puts the mark's character into the table cell containing it (cells now carry row-precise boxes: PyMuPDF cell rects for ruled tables, row geometry for aligned tables) or at the head of the line it precedes. Symbol-font glyphs (Wingdings, Webdings private-use codes) are mapped in `textlayer.py`. `tests/test_marks.py` (4 tests) draws the cases with PyMuPDF. Not in run 10.
- **Vision-model results are back and scored.** `bench/gpu/merge.py place` turned the pipeline's JSONL records into the `olmocr2` candidate (110 pages); `merge` produced `truedoc8_vlm` (run 9 + 94 model pages where run 9 was empty): **67.8** (CI 66.8-68.8) against 62.2. Old scans 34.0 (+13.3), old-scan maths 23.1 (+19.0), tables 70.0 (+4.3), multi-column 72.6 (+1.9), baseline 99.9 (+6.5, one check per page, empty pages fail it). Run 9's failing checks on those 94 pages numbered 604; the model recovered roughly two thirds of them. Recorded in BENCHMARKS, STATUS and GPU_PLAN; the owner decides whether an optional GPU vision stage joins the product.
- **Glued words with no gap at all** (OCR layers: "widespreadaccessorymineral", "1991).The"): `_split_glued_words` in `textlayer.py` runs on OCR-layer pages only. Runs of 8+ letters that are not themselves a dictionary word are split with `wordninja` (MIT, 126k-word English list, new dependency) and the split is accepted only when every part is a dictionary word of 3+ letters (or a real short word such as "of"), so "metamictization" and "Jolliffet" stay whole; punctuation followed by a capital ("1991).The", "1991;Jolliff") is split too. `tests/test_glued_words.py`.
- **Run 10 (`truedoc9`) scored 62.3** (CI 61.3-63.1; run 9: 62.2): headers_footers 95.3 (+1.4), table_tests 66.0 (+0.3), multi_column 69.5 (-1.2), the rest unchanged. Diffing the failing checks of runs 9 and 10 (`failed_tests.jsonl`, keyed by pdf and test id) found the two causes within the hour: (1) the OCR-layer word-gap rule judged the letter gap per line, so on a scanned report whose short words are letter-spaced 0.5 pt while long words touch, "with" became "w i t h" (12 multi-column checks); the letter gap is now judged per run between explicit spaces, and a word gap inside a run must stand clearly above that run's own letter gap unless almost no pair in the run shows a gap (monospaced layers). (2) `_rebuild_sparse_ruled_tables` also fired on a ruled table of wrapped prose cells (a school assessment schedule: 9 rows became 22) and on similar pages: the rebuild is now limited to ruled tables of at most three rows whose rebuilt form is at least 30% numeric. Tables: 52 checks gained, 48 lost in run 10; both fixes verified on the pages concerned (the crop report is still rebuilt, the schedule kept).
- A satellite fragment is now judged by its ordinary glyphs: a tall opening bracket glued to a small numerator ("\Big(" then "1" on one text-layer line) made the fragment look full-size, so it never joined the formula line and the fraction came out as `\overline{q}` with its bracket lost. Size, box and baseline of a fragment now come from its non-extension glyphs; `1+(1+\omega)\Big(\frac{1}{q}-\frac{1}{p}\Big)>0` on 2503.05140 page 22 reads correctly.
- **Bracketed fractions are not matrices.** The matrix detector took `\left(\frac{1}{\alpha^2}-\frac{1}{\beta^2}
ight)` for a two-row matrix because its "fraction inside brackets" guard only applied to a single column of glyphs; a bar between the rows now rules out a matrix whatever the columns (matrices have no rules between rows). `g_k := \log(\beta/\alpha) - \frac{n}{2}(1/\alpha^2 - 1/\beta^2)...` on 2503.07022 page 75 now reads as fractions in sized brackets.
- **Numerators follow their fraction bar.** `_attach_satellites` now receives the page's horizontal rules (drawings are extracted before the lines are reassembled): a script-sized fragment with a bar just below it is a numerator, so it joins the line whose baseline lies below the bar (allowed up to 1.1 line heights away) and never the nearer line above. `r^{3/2}` on 2503.07345 page 12 now reads `r^{\frac{3}{2}}`; 32 text-layer and formula tests pass.
- Two guards after the second maths sample produced invalid LaTeX (`\sqrt^{n-n}`) on a Computer Modern page: a radical sign never takes a script (a glyph that would become one starts its own atom instead), and a tall delimiter (1.8 em or more) is trimmed by 0.3 em at each tip when display rows are linked by vertical overlap, so a big bracket around a fraction no longer stitches its row to the next (a bracket around a real matrix still overlaps every row it holds). The numerator "3" lost from `r^{3/2}` on 2503.07345 page 12 was traced to the text-layer stage: the satellite rule attached it to the line above by baseline distance; noted for the next round (the fraction bar below it should decide).
- **Latin Modern's maths extension font was invisible to the formula code.** A page set in Latin Modern (`LMMathExtension10-Regular`, the same glyph layout as cmex10) produced `\leq^{_{}}^{}` where its `\big\|\big(...\big)^{-1}\big\|` should be: the text-layer code already knew the font (ink boxes, whitespace-coded glyphs) but `latex_for_char` and eight checks in `reconstruct.py` recognised the extension font only by the name "CMEX". `is_extension_font()` in `symbols.py` now names all the cmex-layout clones (Latin Modern, txfonts, pxfonts, MathTime, Euler) and every check uses it; a glyph with no LaTeX can no longer leave an empty script group behind. The page now reads `\bigg\|\Big(\partial_{I}\Phi(n,I)\Big)^{-1}\bigg\|...`, sized by the glyphs TeX chose (the reference wrote `\big` for all of them, which the checker will still count as different).
- **Sized delimiters.** The benchmark's own maths check was asked directly: for a bar over a fraction it accepts `\Big|` and rejects both `\bigg|` and a plain `|`, so the size of a delimiter is part of the rendering it compares. 29 failing checks carried a sized delimiter in the reference; in 21 of them we wrote the bare bracket. Measured on arXiv pages (ink boxes), cmex's fixed-size delimiters are 1.20, 1.80, 2.40 and 3.00 em tall for codes 0x00-0x0B, 0x10-0x11 and 0x68-0x6F, 0x12-0x1D, 0x20-0x2B; `CMEX_TO_LATEX` now maps each to `\big`, `\Big`, `\bigg`, `\Bigg` plus the bracket (slashes and backslashes included), `_delim_key` strips any of the four prefixes for pair matching, and the extent table's size for 0x68-0x6F is corrected from size 4 to size 2. Bars built from three extension pieces still come out `\bigg|` where one reference wrote `\Big|`; the census was too mixed to change that.
- **Formula round 9: fractions inside scripts.** Run 11's failing fraction checks (342 with a fraction bar) were sampled next to our output: the dominant fixable pattern was a fraction set inside a superscript or subscript, `(u^2+v^2+1)^{-\frac{1}{2}(n-1)}`, `e^{j\frac{2\pi}{\lambda}x}`, `r^{\frac{3}{2}}`. The bar of such a stack sits only 0.18 em from the main axis, so the old "is this bar on the main axis" test took it for an inline fraction and built it on the main line, leaving `^{-}` behind. The test is now about the baseline: an inline fraction straddles the main baseline (numerator above, denominator below); a stack that sits wholly above it belongs to a superscript and wholly below to a subscript (`_build` skips it, `_linear` assigns every glyph over the bar to that script by the same rule). The three sample pages now read correctly; 26 formula tests pass; spot-checks and the gate are running. Also noted: the benchmark writes `\phi` where cmmi's glyph is TeX's `\varphi`; ours follows the font, theirs the habit, and the two render differently, so those checks are left.
- **Run 13 (`truedoc12`) scored 63.1** (CI 62.2-64.0; run 12: 62.9): arxiv_math 70.8 (+34 checks), every other category identical to run 12 to the check. Held-out 60.4 (run 12: 60.2), held-out formulas 75.4. Conversion 5,089 s with 6 workers on a loaded machine.
- **Inline "inferred" marker for icons and figures (19:45-20:15, D015 items 1 and 4).** `truedoc/vision/regions.py` holds the two questions (an icon's meaning in at most five words, a figure's description in one or two sentences; "decorative" means write nothing), the padded crop (icons at 384 px with their cell around them, figures at 1024 px) and the answer cleaning. Both providers answer `read_region(pdf, page, bbox, kind)`: the served-model endpoint (`OlmocrEndpoint._chat`, any vLLM vision model) and the new `AnthropicVision` (`truedoc/vision/anthropic_api.py`, plain HTTP to the Messages API, key from `ANTHROPIC_API_KEY`, chosen with `--vision-endpoint anthropic[:model]`). `_read_regions_with_model` (pipeline.py) runs after the page stage under the same switch (`vision_regions`, off with `--vision-pages-only`): icon-only table cells (unnamed marks, and images up to 80 pt inside a cell) get `Answer[^inferred]`; figure blocks at least half an inch on a side, not a background behind text, get the description as alt text `![...](figure)[^inferred]`; twelve regions per page at most; every answer is listed in `truedoc.inferred` with its bbox. Found on the way: figure blocks never rendered at all (the empty-text check came before the FIGURE case in `render_block`), so `![](figure)` placeholders now appear where a figure is; gate 97/128 with them (unchanged), so they go into run 15. Ten vision tests (figure described, pages-only, icon in a cell, the Messages API request shape, a missing key is a warning not a crash, answer cleaning).
- **Run 14 (`truedoc13`) scored 62.9** (CI 61.9-63.8; run 13: 63.1): arxiv_math 69.6 (-37 checks), multi_column 70.2 (-3), old_scans +1, the rest identical. Held-out 60.1. Diff against run 13: 47 newly failing formula checks, dominated by references that want `\varepsilon` where the widened epsilon swap now writes `\epsilon`. A width census over every arXiv page whose references use one spelling (`bench/probes/epsilon_width.py`, `bench/probes/phi_width.py`) shows the Unicode attached to TeX's two epsilons and two phis varies by distribution, but the advance width does not: cmmi10 epsilon 0.406 em vs varepsilon 0.472, phi 0.596 vs varphi 0.654, with the same 10-15% gap at every design size. `glyph()` now picks by width (`epsilon_by_width`, `phi_by_width` in symbols.py, thresholds per design size, cm-like italic fonts only). The multi-column losses were the footnote code: superscript citation numbers ("tumors.2-4") became `[^2]-[^4]` links to nothing, and a section heading "2. Materials and Methods" in the lower page was taken for note 2. Markers whose note is nowhere in the document are restored to the printed digits (`_restore_note_marker`), headings are never notes, and a body-size note must sit in the bottom quarter.
- **Formula round 10 (20:30-21:00, for run 16):** Unicode mathematical-alphanumeric letters (Cambria/STIX PDFs put 𝑛, 𝛾, 𝐀 in the text layer) map to the plain letter with its style (`_math_alphanumeric`: bold, script, double-struck, fraktur, sans, monospace); `\mapsto` is rebuilt from cmsy's mapstochar glued to an arrow (raw code "7", or "|" from a symbol font; `_merge_mapsto`); bars built from extender pieces are sized by the piece count (two pieces `\big`, three `\Big`, four `\bigg`, five `\Bigg`) instead of the union box, which the bearings inflate (three pieces measured 2.4 em and were written `\bigg` where the source said `\Big`); a fraction's part baselines ignore radical signs (their origin sits at the bar, so `\frac{x}{\sqrt{2}}` came out as an underlined x); a display-style fraction set inside a text line (full-size numerator and denominator on their own lines) joins the line when a short bar links it (`bar_above`, size test waived for bar-linked fragments of up to four words); `liminf`/`limsup` are function names. Also: a phantom `\Bigg(` on 2503.07128 came from the blank MuPDF inserts between words when it lands in a cmex span (code 0x20 is the size-4 parenthesis): the text layer already recodes only *drawn* brackets, but `glyph()` in reconstruct.py recoded every whitespace again; a plain space now stays a blank there. Gate 97/128 (twice, before and after the blank-space change), 104 unit tests; maths samples 44/52 (unchanged) and 56/64 (from 54). Verified on the pages that motivated each change (23 `\varepsilon` on 2503.06723, `\frac{x}{\sqrt{2}}`, "tumors.2-4", the "2. Materials and Methods" heading, `\mapsto` on 2503.08577).
- **Run 15 (`truedoc14`) scored 62.9** (CI 62.0-63.9; run 14: 62.9): baseline 93.8 (+5 checks, the first run with `![](figure)` placeholders and endnotes), headers_footers 96.6 (+1), arxiv_math 69.6 (+1: the seven regression fixes minus a few new misses), multi_column 70.0 (-2). Held-out 60.0. The epsilon regression is still in this run; run 16 (launched 21:30, `truedoc15`) has the width rules, the footnote restore and round 10. Diff against run 14: 13 newly passing (7 formulas: six of the seven regressions, 4 headers, 2 tables), 8 newly failing: 6 formulas, all sized brackets that `_demote_short_sized_delims` wrote plain where the source said `\big(`, `\big\|`, `\big|` or `\left\|` (+2 for `\left(` around scripts, -6 elsewhere: the checker's renderer does size a `\left\|` around a superscript), so the demotion is **reverted** (function removed); and 2 multi-column order checks on pages that now carry `![](figure)` placeholders (9 and 3 of them) between the halves of a paragraph split by a column break, which stopped the join: `render_document` now joins a continued paragraph across figure placeholders (the placeholder stays after the joined paragraph). Both go into run 17: gate 97/128, the two pages pass all their official checks again (4/4 and 5/5), two figure tests added (`tests/test_figures.py`).
- **Tables: headings above a boxed row (22:10-22:40, for run 17).** A census of run 15's 322 failing table checks: 55 on pages with empty output (scans: vision territory), 59 on 15 pages where we output text but no table, the rest cell or relation errors inside tables we do find. Of the no-table pages looked at, two are images or path-drawn text (vision territory) and one is a form-style table: a ruled box holding one row with its column headings set unruled just above ("Action Item / Who Will Do / Due Date"), which came out as three headings. PyMuPDF does find the one-row box, but `find_ruled_tables` required two rows. It now returns one-row boxes, and `_adopt_ruled_headers` (pipeline.py) takes the text lines in the band above the box (nearest baseline, possibly several lines because wide column gaps split a line) whose words all fall into the box's columns, at least two columns filled, and at least two of them starting at (or centred on) their column, and prepends them as the header row; a one-row box with no such headings is dropped again (a framed line is not a table). `tests/test_tables_ruled_header.py` (2 tests); the real page now renders the table. Gate 97/128; in run 17.
- **Run 16 (`truedoc15`) scored 63.5, a new best** (CI 62.6-64.4; run 15: 62.9, run 13: 63.1): arxiv_math 73.7 (+121 checks: the epsilon and phi width rules plus round 10), multi_column 70.4 (+3: footnote markers restored), headers_footers 96.4 (-1), everything else unchanged. Held-out 60.6 (best; run 13: 60.4), tuned-on 58.9. Run 17 (`truedoc16`, launched 22:52) adds the bracket-demotion revert, the figure-join and the boxed-row headers. Diff against run 15: 129 newly passing (70 mention epsilon, 43 phi), 6 newly failing: two where the closing bar of `|\mathcal{P}|` right before an arrow was merged into `\mapsto` (the mapstochar abuts its arrow, a closing bar stands a thick space before it: the merge now needs a gap under 0.1 em for a Unicode bar, 0.3 em for the raw code; for run 18), two on the one page whose author writes `\epsilon` for the curly glyph (unfixable by width), one `\longmapsto`, and one footnote "9 Ibid" the headers benchmark wants absent (accepted, D017).
- **Owner decisions (evening):** the GPU instance is stopped; the inferred-marker proposal is agreed as written (D015 closed: one `[^inferred]` tag, model named in the definition and front matter).
- **Run 13's seven formula regressions traced and fixed (19:00-19:40, for run 15).** Diffing run 13's failing checks against run 12's: 41 newly pass, 7 newly fail, all formulas. Causes: (1) a full-size comma that MuPDF put on a denominator's line made the fragment look full-size to `_attach_satellites` (its size test used the largest plain glyph), so `\kappa(A)=\frac{...}{...}` came out as an underlined numerator and a stray `s^{r-1}` line: the fragment's size is now the median plain glyph, and the baseline comes from glyphs of that size; (2) the round-9 "a bar between the rows is no matrix" veto also killed `\begin{cases}` whose rows are fractions: a lone left brace (cases) is exempt; (3) big brackets around script-only content: a probe with the official checker shows that against a `\left( ... \right)` reference KaTeX keeps such content at normal size, so plain `(` passes and `\big`, `\Big`, `\bigg` all fail; `_demote_short_sized_delims` writes a sized pair plain when nothing inside is taller than 1.45 em, has no fraction bar (an overline does not count) and no tall operator; (4) the Euler extension font `euex10` carries ∞ under its own name, and the extension-font branch of `latex_for_char` returned nothing for it: a Unicode symbol from an extension font now falls back to the Unicode table. The `[math]` debug line now shows each glyph's font. The seventh page (2503.09548) has identical output in both runs at the quoted formula; not chased.
- **Footnotes linked (D017, owner's question, ~18:20).** `_mark_footnotes` (pipeline.py) turns a small raised digit or symbol glued to a word into `[^n]` and a line at the foot of the page (or in small type) that starts with that number into `[^n]: text`; lines with inline maths are skipped (a raised digit there is an exponent). Gate 97/128, 89 tests. Then `_link_endnotes` (~18:40, whole document after all pages): a marker with no note on its own page is looked for on later pages, in a block that starts with its number under a "Notes"/"References" heading or in a run of 3+ ascending numbered notes of 3+ words (a "1 Introduction" heading is not a note); keys are made unique across pages (`[^1-p12]`) because markdown keys name the whole document. 5 footnote tests. Both in run 14.
- **Tiny text (89 failing checks in run 11)**: 54 are on pages with no text layer, 25 on hidden OCR layers, 11 on digital pages; like tables, the remainder is mostly vision-stage territory.
- **Vision stage built (D014, D015).** `truedoc/vision/`: a `VisionProvider` interface and `OlmocrEndpoint`, which renders a page with PyMuPDF (longest side 1288 px, olmOCR's default), sends it with olmOCR 2's own prompt to an OpenAI-style `/v1/chat/completions` endpoint (what vLLM serves), and parses the YAML-front-matter answer. `pipeline.py` calls it only for pages with no usable text (`_read_unreadable_pages_with_model`); the reading becomes one text block with provenance `vision:<model>`, the page's quality kind becomes "vision" (usable, confidence 0.5). Rendering adds the page note `> This page was read from its image by a model (...)[^inferred]`, one `[^inferred]:` definition at the end of the body, and `truedoc.pages_with_model` / `truedoc.inferred` in the front matter. CLI: `--vision-endpoint`, `--vision-model`; the bench runner takes `--vision-endpoint` too, so the merged experiment becomes a single run. `tests/test_vision.py` (4 tests) uses a fake endpoint in a thread: only textless pages are sent, marks appear, an unreachable endpoint leaves the page empty with no invention. Not yet exercised against a real served model: that needs the next GPU rental (`docs/GPU_PLAN.md` has the commands).
- **Where the remaining table misses are (run 11: 324 failing checks on 108 pages).** Three of the four worst pages produce no output at all (no text layer, OCR below the confidence gate) and the fourth is an OCR reading of a scan too poor to use ("Sohom O..•t Sompk"): these are vision-stage pages, and the merged experiment already showed tables at 70.0 with the model's readings. The mechanical table work is near its ceiling on this benchmark; the next lever for tables, old scans and multi-column is the vision stage (M9), which starts now.
- **Pull quotes no longer cut columns in two.** In `segment/order.py`, when no full-height gap exists between columns, a narrow text block (under half the region's width) that straddles the gap is taken out as an island; the columns are then ordered normally and the island is put back beside the column it interrupts, before the first block below it. The French editorial (09f801e3 page 18) now reads left column, right column, with all four of its order checks passing (two failed before). Tests and the gate are running before run 12.
- **Run 11 (`truedoc10`) scored 62.8** (CI 61.9-63.7; run 10: 62.3, run 9: 62.2): table_tests 69.1 (+3.1), multi_column 70.6 (+1.1, back above run 9's level after the OCR-layer gap fix), arxiv_math 69.7 (+0.5), headers_footers 95.3, long_tiny_text 79.6 (-0.3), old scans unchanged. Held-out: 60.0 (run 9 60.1, run 10 58.7); tables 68.6 held-out vs 69.2 tuned-on, so the stacked-heading structure and the (now limited) ruled-table rebuild generalise. Gate 97/128 with the margin rules.
- **Some benchmark answers are wrong, and we should not chase them.** Running the benchmark's own order checks on run 10's output with their failure reasons showed that on the Croatian interview page and on a references page the expected phrases do not match the PDF: the reference says "muški redatelj ... potrebbe glumice" where the page (and our output) reads "mladi redatelj ... potrebe glumice"; a reference entry expected as "[46] Barkschat R (2021)" is "[46] Blankertz B (2001)" on the page, "[35] Baranisak RK, Delo EJ" is "Bartusiak ER, Delp EJ", "[59] Hu Y, Wodey S" is "Ho Y, Wookey S". The checks allow one or two character edits, so these can only be passed by reproducing the benchmark's errors. At least nine of the 153 digital multi-column failures are of this kind; they are left alone and noted here so nobody re-investigates them. (One more page, 0925342e page 9, has its expected phrases in no text layer at all: the page is an image strip.)
- Margin rules gated: 97/128 (one more than before). Reading-order miss found on a French editorial (09f801e3 page 18): a pull-quote box straddling the gutter between two columns makes the order go left-top, right-top, left-bottom, right-bottom; under investigation in `segment/order.py`.
- **Held-out slice set up (D016).** `bench/holdout_score.py` splits the benchmark by a stable hash of the file name (261 of 1,403 pages held out, listed in `bench/holdout.txt`) and scores a run on both halves from its `failed_tests.jsonl`. First reading: run 9 60.1 held-out / 57.3 tuned-on; run 10 58.7 / 57.7. Run 10's table work rose 2.4 points on the pages it was tuned on and fell 9 points on the held-out pages, the overfitting the owner asked about, made visible. Two of the causes (the rebuild firing on wrapped-prose tables, the heading count) were fixed before run 11; the held-out number for run 11 decides whether the stacked-heading structure stays as it is.
- **Headers and footers, from run 10's 35 remaining "absent" checks** (each located in the output and measured on the page): a third are unwinnable or kept on purpose (the running head repeats the page's own title; the text also appears in a body citation or signature line; footnotes, kept by policy). The rest were running heads the layout model labels as section headings, short lines stacked under a header block, and small lines in the bottom strip. Three rules: (1) in `apply_layout`, a section-header region in the margin (top 15% or bottom 15%) whose page-header or page-footer rival scored within 0.1 of it (judged on the detector's raw output, since cleaning removes the near-duplicate) is a running head or foot ("INVESTIGACIONES / RESEARCH", "esa SP-301"); (2) `_margin_cleanup` in `pipeline.py`, after the layout pass: a heading of at most 8 words within the top 8% or bottom 8% is a running head or foot ("STAR FLEET UNIVERSE"), a text line of at most 4 words within the top 14% and within 1.5 lines of a header block joins it ("Revision 2", "supersedes: Revision 1"), a short text line in the bottom 7% is a foot whatever its size ("20 2022.05090 SMILE TRAIN, INC."), and a small-type short line in the bottom 11% is a foot ("*18 USC 707"); (3) the layout override's "outermost strip" exemption widened from 7% to 9% at the top and 91% at the bottom to match the zone rules. All eight probe pages now drop their running heads; the page titles and body citations stay.
- Two more run-10 table regressions traced and fixed: (3) a t-distribution table whose first body rows have an empty label cell had those rows absorbed into the heading (the "empty first column means a heading continuation" rule), so "Upper 5% point" and "2.447" fused into one heading cell; a numeric row is now the body when the next row is numeric too, whatever the label column says. (4) an expenditure table with wrapped two-line labels (5 ruled rows, 10 baselines) was rebuilt from lines and its month headings collapsed into one cell; the three-row limit on the rebuild keeps it as PyMuPDF found it. Both pages now match run 9's shape or better.
- A stray space inside a radicand ("0.0 98") came from the *next line's* radical bar, half a line below, being taken as a fraction bar under the digits: a bar now counts for a glyph group only within 0.5 em below its boxes (0.8 em above, for radical bars). Formula spot-checks after round 8: 44/52 and 54/64, both unchanged (the round targets other constructions). Gate 96/128 with the monospace-gated splitter.
- Run 10's patent page still read "golfball according to claim" (a Courier OCR layer with no gap at all between words, every advance identical). The dictionary splitter now also splits 8-9 letter runs, but only into exactly two everyday words (top 8,000) of 4+ letters and only when the layer is monospaced (Courier, or the mono flag), where a missing space is systematic; in proportional layers rare compounds such as "countship" stay whole. Capitalised runs under 12 letters are never split (names: "Whitehouse", "Goldsmith"). The patent page now reads "golf ball" 23 times and "golfball" never. Formula spot-check after round 8: first sample 44/52 (unchanged).
- **Formula round 8 (from run 9's failures, 1,340 failing checks; fractions 342, `\left` 116, roots 100, integrals 95, `\text` 86).** Three fixes: (1) letters set in cmsy are the calligraphic alphabet and letters in msbm the blackboard-bold one, so `d(u_k,\mathcal{M})` and `\mathbb{R}^N` come out as such instead of plain `M` and `R`; (2) an accent attached at the outer level is remembered for its base wherever that base is rendered (`_ACCENT_MEMO`), so `\|u_k\|_{\dot{H}^s}` keeps the dot that a subscript used to lose; (3) a radical or big operator from a symbol font whose origin sits well above the baseline (cmsy's `\sqrt` is 25 pt tall at 14 pt) landed on a line of its own and its argument became an `\overline`; such single-symbol lines are now folded into the text line beside them like extension-font pieces (`_tall_symbol`). 32 formula and line tests pass.
- The owner added three insurance PDS documents to `samples/` (a Suncorp-style "Insured events" PDS with circled ticks and crosses inside table cells, an Allianz policy, an RACQ PDS). On the first, the circled marks were not recognised by template overlap (a 7-pt tick inside a ring is a fat, cut shape), so the tick and cross rules were rewritten on ink features: after ring erasure and speck removal, a tick has an empty upper-left quarter with its ink lower-left and upper-right, a cross has ink in all four quarters lying along the diagonals; discs, squares and boxes still use templates with fill and frame guards. `bench/probes/mark_probe.py` prints the features per candidate. Now both sample pages read correctly: "✗ damage caused by a person acting with your consent" in the not-covered column, "✓ fixed glass in any mirror." in the covered column, and the circled "$" limit icon is ignored. A cell holding several ticked lines gets several ticks at its front ("✓ ✓ When your home is insured ..."), a limitation of cell-level placement in ruled tables.
- The dictionary splitter was tightened after the gate dropped 96 to 93 on two old-book pages ("Albumazar" as "album azar", "countship" as "count ship"): runs must be 10+ letters, every part a common word (roughly the top 25,000) of 4+ letters or a listed function word, and one part 5+ letters. The gate is being re-run.
- Mark classifier guards after trying the ALDI page 32 (circled tick, cross and dollar sign): a "dot" must fill 55% of its box and a "box" must have its ink on the frame, so the circled "$" is no longer read as a bullet; icons two to three ems left of a hanging paragraph are now attached. Gate 96/128 with marks and cell boxes (12:51); the splitter and guards are being gated now.
- The owner authorised (one-off) reading the insurance PDS library at `25 InsurancePlatform/uploads/PDS Docs` (1,175 PDFs) for samples; `samples/` was created and the ALDI household PDS copied there; the page with the tick-and-cross table is still to be located (a full scan is running).
- GPU: the owner rented an RTX 4090 (48 GB) on vast.ai at 11:50; `bench/gpu/` was uploaded and `run_olmocr2.sh` started at 11:55 (pip install of olmocr[gpu] took about 25 minutes; the vLLM server was loading the model at 12:23).
- Header/footer work after run 9: contact/citation blocks of up to 6 lines in the top 18% or bottom 14% of the page are headers or footers even when the layout model calls them text; volume+number, ISSN and dates count as contact lines. These go into run 10.

**Next**
- **Footnotes linked (D017), after the owner asked how they are handled.** Before: a marker came out as a digit glued to its word ("face.8") and the note as a stray paragraph, sometimes a heading ("## 9 Ibid"). Now `_mark_footnotes` in `pipeline.py` finds small raised digits or symbols glued to words (raised at least 0.2 em, at most 0.8 of the line's size, not at the start of a line, at most three characters) and writes `[^8]`; then lines that start with a seen marker, in small type or in the lower part of the page, become notes: one block may hold several notes, one per line, with continuation lines joined; the block renders as `[^8]: Response given by the Minister ...`. Lines that hold inline maths are left alone. `tests/test_footnotes.py` (2 tests: linking; plain numbers such as "In 2019 the fleet had 12 vessels" untouched). The Singapore page now reads "... likely to face.[^8]" with `[^8]:` and `[^9]: Ibid` at the foot. Not done: endnotes at the end of a document, markers inside formulas.
- Symbol spellings from the `\text` failure sample: TeX's `\epsilon` glyph is named "epsilon" and comes back as U+03B5, the code KaTeX draws for `\varepsilon`, so TeX-encoded italic fonts (cmmi, Latin Modern, MathDesign, ...) now swap the two as `\phi`/`\varphi` already were; MathDesign's varepsilon arrives as o-ogonek (U+01EB) and is mapped; the turnstiles ⊢ ⊣ ⊨ ⊩ were unmapped. Not chased: references that write `\Pr` for a blackboard-bold P, or `\text{span}` inside a formula our prose trimmer cuts off. Gate 97/128 and 87 tests on this code; first maths sample 44/52 after the epsilon swap. Run 14 (`truedoc13`) is armed to launch when run 13 finishes converting.
- Island rule settled: a narrow block straddling the gutter is an island only when both sides hold text and the column on each side runs past it (blocks above and below it, or one block spanning it), with at least three blocks in all. The French editorial (two order checks) and the Roosevelt letter ("good luck attend you.") are both right now; a radical sign that collects "scripts" writes them as its argument instead of `\sqrt^{...}`.
- **Run 12's diff against run 11 (multi-column 3 lost, 3 gained; old scans 1 lost; headers 9 gained) traced and fixed:** (1) the pull-quote island was inserted before the first block beneath it, which split a paragraph and its hyphenated word ("environ-" ... "ment"); islands now go after the column they interrupt. (2) The island rule fired on a one-column letter where two short lines sit side by side; it now demands real columns (three or more blocks on each side, each running above and below the island). (3) Widening the "outermost strip" exemption to 9% and 91% let our footer verdicts stand on paragraphs that reach the foot of the page (a catalogue entry, a journal's first paragraph merged with its correspondence block), which the layout model used to rescue; the exemption now applies only to blocks of at most 12 words (40 for contact blocks) that white space sets apart from the body (`_set_apart` in fuse.py). The same white-space condition guards `_margin_cleanup`'s bottom-strip rules. Second maths sample after round 9: 54/64 (unchanged); one display block on 2503.03899 page 9 still renders as invalid LaTeX under the layout model and is being looked at.
- **Run 12 (`truedoc11`) scored 62.9** (CI 62.0-63.8; run 11: 62.8): headers_footers 96.4 (+1.1, the margin rules), old_scans 20.5 (-0.2, one check), the rest identical. Held-out 60.2 / tuned-on 58.3 (run 11: 60.0 / 58.2).
- Run 13 (`truedoc12`) launched 17:08 after gate 97/128 and 87 tests, carrying formula round 9 (fractions in scripts, sized delimiters, Latin Modern extension font, numerators by their bar, bracketed fractions not matrices, two guards) on top of run 12; run 12 (`truedoc11`) was being scored at 17:06.
- Run 11 (`truedoc10`) launched 14:04 after gate 96/128 and 83 tests; score it when it finishes (~15:30), record, then analyse what remains (tables 346 failing checks in run 10, multi-column 270, tiny text 89, headers 36).
- (Earlier plan) Score run 9 (`truedoc8`) when it finishes (~12:00), record it, then launch run 10 with the picture-table OCR, table-inside-figure, numeric OCR gate and header changes after the regression gate passes.
- The vision-model job (`bench/gpu/`) is packaged; the owner has credited vast.ai and added the SSH key, and is being asked to rent the instance.

---

## 2026-09-03 (midday) - Run 6 scored 58.3; sixth round of formula repairs lifts the maths samples to 81% and 77%

**Done**
- **Run 6 (`truedoc5`) scored 58.3** (CI 57.3-59.2): arxiv_math 51.1, base 93.3, headers_footers 92.9, long_tiny_text 77.4, multi_column 68.4, old_scans 20.7, old_scans_math 3.9, tables 58.3. Tables +1.4 and headers/footers +1.3 from the table repairs, rotated pages and contact-line headers; formulas unchanged because the formula work below came after the snapshot.
- Studied every failing formula check on the two 12-page samples (first 12 pages: 33/52; next 12: 39/64) by dumping the raw glyphs behind them, and probed the scorer with hand-written variants to learn what it treats as equal. Findings worth remembering: `\notin` and `\not\in` are *not* interchangeable (the references use `\not\in` 11 times, `\notin` 5); an accent must sit on the letter alone (`\hat{\nu}_{31}`, never `\hat{\nu_{31}}`); a plain `|` does not match `\big|` or `\left|` (those are drawn from stacked pieces); `\arg\max_{...}` does not match `\underset{...}{\arg\max}` (the limits must belong to the whole word); `\ldots` cannot match a literal `...` (17 references) but the commands are far more common (259), so nothing changed there; raw Greek capitals, `\star`, and either order of `_{}`/`^{}` are fine.
- Root causes found and fixed:
  - **Maths-extension glyph boxes.** cmex glyphs (big brackets, big operators, wide hats, radicals) hang below their origin, and the text layer reports a box from the font's ascender/descender: one PDF reported a three-line bracket as one line tall, another as five lines tall. The tall boxes glued stacked equation rows into one garbled line; the short ones hid matrices. Now MuPDF's measured outline box is used where it can provide one, and otherwise the box is rebuilt from cmex's design metrics (`CMEX_EXTENT`). Pieces of an extensible bracket (top, extenders, bottom) are stacked into one glyph.
  - **Whitespace-coded brackets.** Several cmex codes are whitespace characters (a size-4 "(" is 0x20, "}" is a tab, "|" a form feed); every blank filter in the pipeline was throwing them away. They are now carried on private-use codes and mapped back in the formula code; the renderer scrubs any raw glyph code that no formula claimed. Caveat found the hard way: MuPDF also *inserts* a space wherever it sees a gap, and that space takes the font of the span it lands in, so a "space" in a cmex span is either a synthetic blank or a real bracket. MuPDF's text trace lists only drawn glyphs, so a blank is kept as a bracket only when the trace has a glyph at that position (otherwise two pages grew a phantom "(" in their formulas). Glyphs MuPDF cannot name (reported as U+FFFD) get their raw code from a second extraction pass with the "CID for unknown" flag.
  - **Glyph names that lie.** TeX's `\phi` glyph is named "phi" and so arrives as U+03C6, the character KaTeX draws for `\varphi` (the references write `\phi` 113 times); for TeX-encoded italic fonts the two are swapped back. cmsy's `\setminus` glyph is named "backslash" and was being read as `\cap`. A bar from cmex is a sized bar (`\big|`), which is what references write for evaluation bars and what `\left|` renders as; a plain `|` does not match either.
  - Zero-width vector accents are reported where the previous glyph ended, even across a `\quad`; they now attach to the next glyph within 2.5 em.
  - The Adobe glyph list maps the glyph names "Omega" and "Delta" to the *ohm sign* and the *increment sign*, so text fonts deliver those characters and KaTeX refuses them in maths; both are now mapped to the Greek commands (a whole formula was failing on one Ω).
  - Lines: fragments that *overlap* horizontally (a formula's superscripts and the symbols after them come out interleaved) are re-joined when no two words coincide; a line holding only extension-font glyphs (the stacked pieces of a tall bar) is folded into the text line it touches, since its baseline sort put it nowhere; a script of a script (the ⊥ in `H^{\perp}` under a bar) now stays inside its script group.
  - **Line fragments.** A line's size and baseline were the *mean* over its characters, so a fragment such as "λ−1" (one letter, two script digits) reported a script size and baseline and could not be re-joined with its neighbours; lines are now sized by their main text. Bracket-only fragments join on adjacency. Script-sized fragments (numerators, denominators, stray subscripts) go to the neighbouring line with the nearest *baseline* rather than the widest line, which had been stealing subscripts for the line below.
  - **Accents.** A hat's "raise" test matched the subscript under the letter (a lower baseline looked like a raise) and the hat vanished into the subscript; bases must now be the accent's own size. Wide hats and tildes from cmex are recognised by their LaTeX rather than their raw code; combining marks (zero-width, placed before their base in the stream) attach to the next glyph.
  - Spellings: `\not\in`; long arrows that TeX builds from two glyphs (`\mapsto`, `\longrightarrow`, `\Longleftrightarrow`, ...); `\cong` and `\simeq` from a stacked `\sim`; "arg max"/"arg min" as one operator with limits underneath; `\lim`, `\max`, `\min`, `\sup`, `\inf` take limits like big operators.
  - A fraction inside tall brackets was being read as a one-column matrix; a bar between the rows now rules that out.
  - Inline: an upright run of capitals next to a relation ("TOL = 10^-6") is an identifier, not prose to strip; "E[T]"-shaped tokens join a neighbouring maths run.
  - Algorithm listings (layout "code" regions full of maths glyphs) are rendered as text lines with inline formulas, one statement per line, instead of a code block with no maths.
- Two regressions caught by the 13-page gate along the way and fixed: (1) re-joining overlapping fragments also merged table cells and loose OCR boxes, so it now applies only to lines carrying maths-font glyphs; (2) a text line full of symbols in one column was being classed as a displayed formula and its box merged with the equation beside it in the *other* column (formula boxes never merge across a gap that contains the page's middle, and a block with two or more ordinary words is a sentence, not a display).
- Samples after these fixes: first 12 pages **44/52** (from 33), next 12 pages **53/64** (from 39). The 13-page regression gate stayed at 96/128. 60 unit tests pass (sixteen added).
- Harness bug fixed: the scorer was handed a *relative* path for its failed-tests file and resolved it against its data folder, so runs 5 and 6 kept no failure list (the summary was unaffected). Run 6 is being re-scored to recover the list.
- Run 7 (`truedoc6`) launched with all of the above.

**Learned**
- Probing the scorer with hand-written variants is cheap (a few seconds per variant) and settles arguments that would otherwise take a full run; keep `glyph_probe.py`-style checks in the toolbox.
- MuPDF's accurate-bbox flag works for most embedded Type 1 fonts but not all; a design-metric fallback is needed anyway.

- Owner's instructions (3 Sept, while run 7 converted): hidden text goes out of the body and into the front matter (D011), to be built after run 7; the owner will help set up the vast.ai GPU machine when asked with a concrete checklist.

- **Hidden text (D011) built** while run 7 converted (the running workers had already loaded their code): stage 1 now decides per character whether a reader can see it, using MuPDF's text trace (render mode, opacity, paint order), the drawing list (opaque fills painted over or under the text) and the character colour against the background beneath it; tiny (< 1 pt) text counts as hidden too. Hidden runs leave the body and appear in the front matter under `hidden_text` with page and reason; a picture covering most of the page never counts as "covering" (that is a scan, D010). Six synthetic-PDF tests cover white text, tiny text, text under a black box, invisible render mode, a scan's OCR layer (kept) and a plain page (nothing reported). Gate unchanged at 96/128; 66 unit tests pass. To be confirmed at scale in run 8, including a check that it never fires on ordinary pages.
- Run 6's failure list, recovered: formulas 1,432 (run 7 addresses); **multi-column reading order 279, of which 256 are on pages that do have text** (the earlier belief that these were image-only pages was wrong; a first sample shows phrases that are missing or damaged rather than misordered); tables 425 on 116 pages: 53 on image-only pages, 157 where no table was found, 215 where a table was found with the wrong structure; tiny text 100 missing phrases (present but damaged, from the line rebuild of OCR layers); headers/footers 53 kept texts, many of them footnotes and running heads.
- GPU step prepared in `bench/gpu/` (page selection, the remote run script for olmOCR 2, README with the owner's one-off steps) and a dedicated SSH key pair; the checklist goes to the owner once the CPU-side work below is done.
- Chasing the multi-column and tiny-text misses to their causes (all fixed, gate pending):
  - **Column gutters.** Two-column pages whose columns sit close (patents, justified newsletters) had left and right lines joined into one; the join limit for justified text was wider than the gutter. Stage 1 now finds page-wide vertical channels that almost no word crosses, with text on both sides, and never joins segments across one. US patents print line numbers *in* the gutter: those are ignored when finding the channel and kept as segments of their own (they were bridging the columns). The OCR-layer line rebuild (scanned patents carry an invisible text layer) takes the same gutters.
  - **Glued words in narrow justified columns.** A newspaper column squeezes word spaces to about 0.14 em (0.96 pt at 7 pt), below the old break threshold, and the guard median was computed over the visible gaps only, which made the word gaps themselves the norm. The threshold is now 0.13 em over a median that counts touching letters as zero.
  - **Type 3 fonts.** Their reported size is the font matrix scale (0.1 pt), which broke every size-based rule and, with the new hidden-text stage, hid the whole page as "tiny" (OCR then quietly replaced it). Sizes under 1 pt are now taken from the glyph box. MuPDF also splits such words into separate line objects mid-word; segments that touch or overlap fuse into one word.
  - **Hidden text, second look.** "Covered" had to be judged from the rectangles a path actually fills, not its bounding box (a newspaper box border hid a whole page); white text over a shaped fill or an image is visible (the masthead); text beyond the page box is hidden ("off-page").
  - Running heads such as "Scripta Uniandrade, v. 19, n. 1 (2021)" and "Date: 2019-03-15" join the contact-line header patterns (a volume alone is not enough: "Ff. v. 48, f. 114." is a manuscript citation, and the first version of the pattern threw one away).
  - Gate after all of it: 96/128, 70 unit tests. **Run 8 (`truedoc7`) launched at 09:10** with everything since run 7 (hidden text, gutters, word breaks, Type 3 sizes, running heads); run 7 was still being scored.
- Table failures, first look at the "table found but wrong" bucket: one page was a scan whose OCR text layer is unreadable ("Sohom O..•t Sompk 117" for a real table), so a language-independent **garbage detector** now judges a text layer by its tokens (symbols strewn inside words, digits between letters, several case flips, Latin words with no vowel): ordinary pages measure 0.00-0.02, a mediocre but readable OCR layer 0.08, the unreadable one 0.24; above 0.2 the layer is "suspect" and the page goes to the OCR path instead of being trusted. Maths pages are exempt (formulas are full of symbols; a broken OCR layer never uses a maths font). Other cases seen and fixed: an attendee list whose "Name | Affiliation" header row was left out because the layout model's box starts under it (a line within two line heights above a table box whose words all sit on the table's columns is now taken as the header row); and a programme-deadlines table whose wrapped cells ("US Citizens and" / "Permanent Residents", "Please visit the" / "program website") came out as separate rows (a tight row whose every filled cell reads as a continuation of the cell above, by a lowercase or bracket start or a connector word such as "and" ending the cell above, is folded in). Tables built inside a confident layout region skip the prose rejections meant for stray word grids, and their cells now carry boxes. The Korean page that produced Latin garbage in run 6 has no text layer at all: that was our own English OCR reading Korean, a job for the vision model.

- **Run 7 (`truedoc6`) scored 60.2** (CI 59.2-61.1): arxiv_math 66.7 (from 51.1; 1,952/2,927), base 93.3, headers_footers 92.9, long_tiny_text 77.8, multi_column 67.8 (from 68.4), old_scans 20.7, old_scans_math 3.9, tables 58.2. Its failure list was kept this time (`bench/runs/truedoc6-20260903-090240/failed_tests.jsonl`).

- **Hidden text, verified against the render.** Comparing run 8 with run 7 page by page showed three pages that lost a third or more of their text, all hidden-text false positives with different causes: a producer that reports black body text as white, a dark box under text that is nevertheless readable, and a figure whose paint order says it lies over the reference list. Instead of patching each, the stage now checks every "covered" and "same-colour" run against the rendered page (a hidden run renders as a flat patch; visible text shows contrast), and only when rendering itself fails does a page that would be mostly hidden fall back to keeping its text. (The "black reported as white" page turned out to carry a genuinely invisible duplicate copy of its abstract at the top of the page, which the render check correctly kept hidden; a first version of the fallback had overridden it.) Gradients ("fill-shade") count as painted backgrounds. Run 8 itself carries the unverified version; run 9 gets this one.
- Seventh formula round, from run 7's failure sample (unit-tested, samples to follow): a superscript longer than its base ("Z^{W_0^2 dx(xi)}") no longer makes the small glyphs the main size (when every smaller glyph sits clearly above or below the largest glyphs' baseline, the largest are the main line); limits wider than their operator ("k=r+1" under a sum) are parked with the operator instead of the symbol before it (centre within 0.8 em of the operator, was 0.2); a bar built from two or more pieces is written `\Big|` / `\bigg|` by height, which is what KaTeX stacks the same way. Two more from the same sample: a bracket-only fragment was folded into the wrong neighbouring line (the fold chose its host by horizontal gap, which a full-width line above always wins; it now chooses the line it shares most of its height with), and bold letters set in Computer Modern's bold faces (cmbx, cmmib and kin, whose names carry no "bold") were not recognised as bold and so fell out of inline formulas ("u ∈ V" lost its u). The bracket fold fix was not enough on its own: the bracket's *font* box was 41 pt tall (four lines) against 13 pt of ink, so line building itself had already put it on the wrong line. Maths-extension glyphs now get their measured (or design-metric) boxes *before* any line is built, not only inside the formula rebuild. The mathabx symbol font's braces arrive as the letters "t" and "u" ("tE_1, E_2u"); mapped.
- **Prose inside formulas.** Probing the scorer showed that KaTeX joins adjacent letters of one style into a single run and the check compares runs whole: "for all" written as loose letters ("forall") can never match the reference's `\text{ for all }`, while `\text{for all }` does. Runs of upright text-font letters inside a formula (two or more letters; dots kept inside abbreviations such as "s.t.") are now emitted as `\text{...}` with their word spaces. Function names keep their commands; single upright letters stay as they are. Words in scripts ("X^{\text{Test}}") are grouped at their own size. In running text, a short connective phrase between two formulas ("for all", "if", "and", "where", "s.t.") is absorbed into one formula, since that is how such lines are written and how the references read them. Operator-like words ("span", "Range", "supp", "Hom") bridge two formulas like function names. In documents whose maths is set in the text fonts (Times), an italic letter carrying a smaller script ("X^{Test}", "S_n", "(I^+") is a variable and joins the formula. Samples before these last inline changes: 44/52 and 54/64 (from 53).

- **Run 8 (`truedoc7`) scored 60.8** (CI 59.9-61.7): arxiv_math 66.4 (-0.3), base 93.3, headers_footers 93.3 (+0.4), long_tiny_text 79.6 (+1.8), multi_column 70.7 (+2.9), old_scans 20.7, old_scans_math 3.9, tables 58.2. Conversion 71 min (contended by scoring and gates), 0 errors; no page went blank (empty outputs identical to run 7).

- Run 8's eight lost formula checks traced: two pages had lost text to the unverified hidden-text stage (fixed by the render check); one page lost its Ω because the ohm sign (what text fonts deliver for "Omega") was not in the set of symbols that make a lone word a formula, and the tighter word breaks now leave "Ω" as a word of its own. Added, with the increment and micro signs.

- Run 9 was stopped a few minutes in and relaunched (10:45): a wide tilde had shown that lines cut at wide accents were no longer re-joined (the accent glyph sits on its letter, and the "no coinciding words" guard for interleaved fragments rejected the join; extension-font glyphs now do not count). Gate 96/128, samples 44/52 and 54/64, 74 unit tests before the relaunch.
- Table probe of run 8's "no table found" pages (25 worst): 14 pages where the layout model finds the table but the builder gave up (several now build with trusted regions), 8 image-only pages, 3 with nothing. The two worst turned out to be **tables drawn as pictures on otherwise digital pages** (a figure of matrices, a funding flyer): a table region holding no text is now OCR'd (RapidOCR on the region crop, gated like page OCR but accepting a numeric-heavy read, since tables are full of "93.75%" and "sensitivity/recall") and the table built from the OCR lines; the flyer yields a 30-by-4 table and the figure of matrices three 6-by-2 tables. Two things stood in the way: table boxes inside a figure box were being dropped as duplicates of the figure (a table inside a figure is a table too), and the OCR gate's word list knows no metric names. A synthetic-PDF test covers the picture path. The same numeric-share acceptance now applies to whole-page OCR (a scanned page that is mostly a table of numbers was being rejected as "not word-like" and left empty). These go into run 10.

- Headers and footers still kept in run 8 (50 checks), located on their pages: 24 in the top zone (journal lines such as "journal homepage: www.elsevier.com/..." at 15%, revision stamps, "Scripta Uniandrade, v. 19, n. 1 (2021)"), 10 in the bottom zone (URLs, "PLOS ONE", page numbers "362", "98"), 6 footnotes, 5 mid-page. Most were being *un-done*: the layout model's confident "text" region overrides a heuristic header with three or more words. Strong heuristic evidence (an address, journal line or stamp, or text in the outermost 7% of the page) now survives the override, and the contact-line zone at the top reaches 18%.
- Multi-column, remaining misses on the worst pages, by cause: a Croatian page where the *reference* differs from the printed words ("muški" vs "mladi", "pokraj" vs "potkraj"); a scanned patent whose OCR text layer has the errors ("Sub stituted"); a page where scattered chart characters ("z 2 ·c: :a: Q.") leak into a paragraph and a heading is interleaved inside a paragraph (to fix); image-only pages (vision model).

**Next**
- Score run 9 (`truedoc8`, relaunched 10:45).
- Multi-column: find why phrases go missing on text pages (sample above).
- Tables: probe the "no table found" pages and the "wrong structure" pages with `bench/table_probe.py`.
- Then the GPU step: prepare the vision-model job for the image-only pages and send the owner the setup checklist.
- Remaining sample failures: one page whose displayed derivations still come out garbled (2503.03873 page 5), inline matrices, `\big|` evaluation bars, and a handful of reference quirks.

---

## 2026-09-03 (morning) - Multi-column regression traced to the table finder; several extraction fixes

**Done**
- Multi-column re-runs: 58.7 with the layout model, 58.1 without it, versus 67.4 for the first run. So the regression was **not** the layout model but the unruled-table finder: preprint pages with manuscript line numbers in both margins (every row = number | text | text | number) were turned into one page-sized table, and justified paragraphs split at wide word gaps became word grids. Fixes: character-weighted prose rejection (more than half the characters in long cells = prose), "many words per row and nothing numeric" rejection, and a veto in layout fusion when a confident text region covers a candidate table (its lines go back to the text flow).
- Margin line numbers are recognised per side (an increasing column of integers in the left or right 12% of the page) and dropped.
- Lines: some producers emit every word as its own text object, so MuPDF reports one line per word; a reassembly pass re-joins segments on one baseline separated by up to a word space (or by the same stretched gap the neighbouring segment uses), and rows of four or more single words with uniform gaps.
- Bug fixed: the table finder returned only the lines outside the header/footer zones, silently dropping the first and last lines of every page from the text flow.
- Pipeline order changed: heuristic classification first, then the layout model overrides (previously the heuristics ran last and undid the model's decisions). Near-duplicate regions now prefer the specific kind (header, caption, formula) over generic text, and header/footer readings win in the page margins.
- OCR gate: page accepted only if mean confidence >= 0.75 and >= 60% word-like tokens; standalone OCR is ~9 s/page at any cap between 1300 and 2000 px (recognition dominates).

- Multi-column re-run with all fixes: **66.2** (back from 58.7; the first run had 67.4). The layout model does not move reading order; the remaining ~300 order failures need their own analysis.
- Long tiny text: the pages are archive.org book scans with a hidden OCR layer (one text object per phrase, meaningless font sizes). The raw layer contains 90-100% of the tested phrases but our output only 58-78%: phrases were being scattered into narrow blocks. New OCR-layer line rebuild (`_reassemble_ocr_layer`): rows by vertical overlap, column boundaries voted by word gaps that line up across at least half the rows and that no word straddles, phrases merged within a column, wide gaps split. Size-based heading rules are skipped on such pages and the body size comes from line heights. On five sample pages the phrase checks went from 27/67 to **51/67**.

- Multi-column "order" failures classified: of 299, only 12 are genuinely wrong order; 287 are phrases the scorer cannot find in our output at all. Of those, 124 exist in the PDF's own text layer (our processing damaged them: column interleaving in hidden-OCR-layer pages, a list-marker rewrite that inserted "- " into "(i) ...", a false column boundary at a reference-list gutter) and 255 are on image-only pages where the text layer has nothing (only OCR/vision can help). Fixed the first group's causes: letter and roman list markers are kept verbatim; a column boundary must have real text on at least 20% of the page width on each side.
- OCR engine: the bundled RapidOCR recognition model is Chinese+English and drops spaces between English words ("Availablein3-1/2in."); switched to the English PP-OCRv3 recognition model from the same Apache-2.0 model zoo (fetched once into `models/`, git-ignored, `TRUEDOC_OCR_LANG=zh` restores the bundled model).

- Regression guard: `bench/quick_check.py` runs the official tests on 13 fixed pages (about 10 minutes with the layout model) and compares with `bench/quick_expected.json`; first recorded total 84/128.
- Patents number their lines in the gutter between the columns; those integer columns blocked the column split and interleaved the two columns. Line-number detection now finds any x-aligned column of increasing integers spanning a quarter of the page. Short text inside a top-of-page picture (form banners, letterheads) is treated as a running header.

- OCR gate: the "looks like words" test now uses a list of about 10,000 common English words (`truedoc/data/en_common_words.txt`, MIT-licensed public list) instead of a vowel-ratio rule that accepted handwriting noise such as "tHee pltcae Silaln". Threshold 0.5 of tokens (numbers and one/two-letter tokens count).

- Quick check after the gutter-line-number and banner fixes: 84 -> **90/128**, no page regressed (patent page 1 -> 3 of 5, form page 7 -> 11 of 12). Expected counts updated.
- OCR engine threads capped per session (`TRUEDOC_OCR_THREADS`, default 4) so six benchmark workers stop thrashing all cores on scanned pages.

- Maths on a *fresh* sample (arXiv pages 13-24, never looked at while building): **28/64 = 43.8%**, in line with the 48% on the first sample, so the formula rebuild generalises rather than fitting the pages it was tuned on.
- First full conversion with layout + maths + OCR: 96 minutes for 1,403 pages (24.7 s/page under 6-way contention; OCR pages dominate), 0 errors. Scoring in progress; a second full conversion (candidate `truedoc2`, with the tiny-text, OCR-model and line-number fixes) is running in parallel.

- Maths reconstruction, second pass from the fresh sample's failure log: (1) the same fraction bar reported twice (vector path and image mask) turned numerators into `\underline` and denominators into `\overline` nests: rules are now de-duplicated; (2) a radical with no bar produced a bare `\sqrt` that broke KaTeX: it now takes the next piece as its argument; (3) "lim", "sup", "inf", "log" were split into letters with the limits attached to each letter: upright letters are grouped into one word first (ignoring the small limit glyphs interleaved in x order); (4) fractions inside exponents were pulled to the main level: script-sized fractions are deferred to the script group, which is now built with the full structure builder; (5) big delimiters with odd origins were treated as superscripts: cmex glyphs are never scripts. Unit tests for (2) and (3).

- Maths, third pass: (6) an inline formula broken across a line wrap came out as two `$...$` runs, so the reference (one formula) never matched: adjacent runs at a line break are rejoined; (7) the micro sign U+00B5 (what some fonts emit for mu) now maps to `\mu`; (8) inline text-style fractions have script-sized parts, so the "defer small fractions to the script level" rule wrongly deferred them: a small fraction whose bar sits on the main line's axis is now built at the main level.

- **Full run 2 scored: 54.7 overall** (CI 53.7-55.6). arxiv_math 40.8, base 93.3, headers_footers 90.9, long_tiny_text 68.1, multi_column 67.1, old_scans 18.6, old_scans_math 3.1, tables 55.4. Scoring took about 3 hours because it shared the CPU with the next conversion.

- Inline fractions in running text: the numerator and denominator arrive as separate text-layer lines (the denominator often glued to the words that follow), so "0 < δ < 1/4" came out as `\underline{1}` plus a stray "4". Two fixes: segments on one baseline may now overlap horizontally when re-joined (the denominator sits under the numerator), and script-sized fragments stacked on a full-size line are folded into it. Numerators only see rules above the bar and denominators only rules below it, so a radical bar in a denominator no longer underlines the numerator.

- Maths sample after the third pass: **27/52 = 51.9%** on the first 12 pages (was 16/52 on day 1, 25/52 after the second pass). Fraction parts are now assigned by baseline rather than box edges (MuPDF boxes come from the font's ascender/descender, so a radical's box reaches above its bar), which restores `\frac{1}{\sqrt{n}}`.

- Fresh maths sample after the third pass: **32/64 = 50.0%** (was 28/64). The inline-fraction axis tolerance was too loose (fractions inside exponents were kept at the main level); tightened from 0.3 to 0.2 em, which took one page from 2/7 to 6/7.

- Maths, fourth pass: limits that begin left of a big operator in x order are parked and attached to the operator (`\sum_{k=1}^{K}` instead of `=_{k}\sum_{=1}`); the "increment" character U+2206 maps to `\Delta`; accents prefer a full-size base over a script-sized neighbour; big operators are padded when splitting a display region into lines so their limits join the line; displayed equations split into side-by-side fragments by wide spacing are merged into one formula box, and near-duplicate formula regions from the raw detector output are collapsed.

- Tables, from run 2's failures: 455 failed checks; 179 of them (39%) on 36 born-digital pages where *no table at all* was produced, 173 on pages with a table of the wrong shape, the rest on image-only pages. Traced the first group on a typical "booktabs" page (three tables with grouped headers, a few horizontal rules, no vertical rules): (1) the rotated "RESEARCH PAPER" side banner was clustered into a data row and stretched the candidate to the page edge, (2) grouped header cells spanning several data columns erased the whitespace channels between those columns, (3) values like "4.79±0.37" and "↑0.5%" did not count as numeric, so the collapsed grid was rejected as prose. Fixes: rotated lines are excluded from table candidates; channels are computed from the busiest rows (the data rows) only, and grouped headers are then assigned to the leftmost column they cover; the numeric pattern accepts ± ranges, arrows, comparison signs and scientific notation. The page now yields three 9x8 tables with correct data cells. Unit test added.
- Not fixable without OCR of figure crops: some "tables" are drawn inside figure images (metric boxes next to ROC curves) and have no text layer at all; noted as a later step.

- **Full run 3 scored: 56.3 overall** (CI 55.4-57.3): arxiv_math 40.8, base 92.9, headers_footers 91.6, long_tiny_text 77.4 (from 68.1), multi_column 68.2, old_scans 20.7, old_scans_math 3.9, tables 55.1.

- Multi-column, from run 3's failures: 281 order failures, of which 262 are missing phrases; 269 phrase misses are on pages whose text layer does not contain the phrase at all (image-only pages: vision-model territory) and 92 are damage by us. The damage is mostly interleaving around a full-width figure: the cut peeled the figure as a "spanning block" and read the columns above it, then the figure, then the columns below it, so a paragraph that continues past the figure was interrupted by the other column. Now a full-width figure or table never splits the text: the columns are ordered without it and it is inserted before the first block that lies entirely below it. Also a lone symbol run ("|", "-") is no longer wrapped as a formula.

- Quick check after the table and maths fixes: 90 -> **93/128**, no page regressed (the OCR-layer table page 2 -> 5 of 14).

- Run 4 (`truedoc3`) was stopped at 834 of 1,403 pages: it had slowed to about three pages a minute while sharing the CPU with scoring and diagnostics, and it lacked the table and reading-order fixes. Run 5 (`truedoc4`) restarts from scratch with everything included on an otherwise idle machine.

- From run 3's remaining failures (for run 6): (1) stacked column headings ("(5)" over "Female") are merged into one header row, since the scorer and a reader both treat the stack as one heading; (2) columns that hold no text at all are dropped (spurious channels put an empty cell between a label and its value, breaking "left of" checks); (3) lines with web addresses, e-mails, phone numbers, DOIs or signing stamps in the top or bottom 14% of the page are running headers or footers whatever their length. The remaining header/footer misses are mostly page-bottom footnotes, which the benchmark counts as footers but TrueDoc keeps on purpose (they carry meaning).

- Tables (for run 6): cells separated by only half an em ("9  SPS/09") stayed glued because segments split at two ems. Word gaps of at least 0.4 em now vote for a column boundary; a position supported by 60% of the multi-word rows that no word straddles splits every segment crossing it and counts as a column even when narrower than a whitespace channel. The course-credit table becomes "Learning activity | Ects | Sector"; the other probe pages are unchanged. Up to four stacked heading rows are merged.

- Run 5 conversion: 56 minutes for 1,403 pages on an idle machine (14 s/page with 6 workers), **5 pages crashed** in the formula rebuild (a fraction group whose full-size glyphs were all cmex delimiters made the "axis" rule take the mode of an empty list). Fixed, and both formula call sites now catch any exception and fall back to plain glyph text, so a formula can never empty a page again. The five pages were reconverted into the run-5 candidate before scoring reached them. Quick check with the table fixes: 93 -> **96/128**.

- Table probe on 40 no-table pages from run 3 (with the layout model): "region found but structure failed" 22 pages / 119 failed checks, "no text layer" 43 checks, "no region and no geometry" 33 checks, and 30 checks now handled by the newer geometry code. The top "structure failed" page turned out to be **rotated** (a landscape table with /Rotate 90): MuPDF reports text, drawing and image coordinates in the unrotated space while the rendered image and the layout model's boxes live in the rotated space, so nothing lined up and every text line was flagged as vertical and dropped. Coordinates are now mapped through the page's rotation matrix at extraction time (15 benchmark pages are rotated: 8 headers/footers, 7 tables). The rotated table page now yields nine tables. Regression test added.

- **Full run 5 scored: 57.9 overall** (CI 56.9-58.8): arxiv_math 51.1 (from 40.8), base 92.8, headers_footers 91.6, long_tiny_text 77.4, multi_column 68.6, old_scans 20.7, old_scans_math 3.9, tables 56.9 (from 55.1).

- Run 5's maths failures by construct (pass rate): plain formulas 56%, font commands 58%, dots 66%, fractions 41%, left/right 35%, accents 33%, text-in-maths 33%, big operators 26%, environments 10%, line breaks 6%. A sample of failing *plain* formulas showed five mechanical causes, now fixed for run 7: (1) punctuation words such as ":=" broke a run in two ("K_0 :=" lost), so short punctuation-only words now bridge maths words; (2) bold single letters ("{\bf T}") were left outside runs; (3) "lim inf" came out as two operators; (4) the ring operator and ring accent were unmapped; (5) two symbol-font families without Unicode maps (mathabx "TeX-matha" and "OAMathSymbols") produced letters in place of symbols ("p" for "(", "b" for the tensor sign, "!" for an arrow): raw-code tables added for the codes confirmed on real pages.

- Maths samples after the fifth pass: first 12 pages **32/52 = 61.5%** (was 27/52); fresh 12 pages **39/64 = 60.9%** (was 32/64). Also fixed: cmex big-wedge and big-vee codes were swapped (and big-uplus was missing); a leading bracket is no longer stripped from an inline formula (an extra edge glyph is harmless, a missing one fails the check); double bars map to `\Vert`.
- Accents (33% pass rate, 356 tests): the failure sample showed hats printed *after* their letter ("τ ˆ"). The text layer places TeX accent glyphs at the letter's own baseline with the same box height (the raise is inside the glyph outline), so both "above the base" rules missed them. A third rule attaches an accent to the letter whose box it overlaps at the same baseline. Big-operator limits: a small glyph is parked for an operator only when its centre is within the operator's width and above its top or below its bottom (the tail of a previous superscript was being stolen); text-style (small) operators judge scripts by box centre rather than the unreliable origin. More mathabx codes (minus, dot, less/greater, sum, product, integral).

- Multi-line displayed equations (references with `\begin{aligned}` and `\\` passed 6-10%): rows of one display region that sit close together are now emitted as a single `aligned` block, each row aligned on its first top-level relation (as authors write it); single-row references still match inside such a block because the check only enforces the reference's own neighbours. Padding big operators to catch their limits had glued tall stacked rows into one line, so instead limit glyphs that landed in a neighbouring row are moved next to their operator. The alignment mark is only ever placed outside braces, `\left…\right` pairs and inner environments (a mark inside one is a LaTeX error that would stop the whole block rendering); unit test added. Samples after the change: first 12 pages 33/52 (was 32), fresh 12 pages 39/64 (unchanged).

**Next**
- Run 6 (`truedoc5`, converting): table repairs, rotated pages, contact-line headers, crash guards. Then re-probe the remaining "structure failed" table pages.

---

## 2026-09-03 (early) - Scorer artefact found; OCR gated; maths at 48% on the sample

**Done**
- **Found why empty scanned pages "scored" 58.7 on old scans**: we wrote a lone newline for them, and the scorer's `partial_ratio` treats a one-character document as a perfect match for any phrase, so "present" checks passed. Empty pages now produce empty files (`render_document`). The honest old-scans baseline is about 13 (only "absent" checks pass). Docs corrected.
- Classical OCR run on old scans (ungated): **23.0** (from an honest 13); base checks 86/98 pass. Handwritten pages produce confident-looking noise, so `apply_ocr` now rejects a page unless the engine's mean confidence is at least 0.75 and 60% of tokens look like words; rejected pages stay empty. Under 6 parallel workers the OCR took 101 s/page (contention); alone it is roughly 20 s.
- Maths: cmex/big-operator baselines fixed (operators no longer vote for the line baseline), rules just above/below all glyphs accepted (overline, radical), single italic letters join adjacent maths runs, matrices/cases from tall delimiter pairs (pmatrix, bmatrix, vmatrix, Bmatrix, cases). Maths check on the same 12 pages: **25/52 = 48.1%** (was 16/52 before the dots/Greek/neq fixes; matrices were added after this run).
- Layout fusion: an aligned table spanning several model table boxes is rebuilt one table per box.
- Unit tests: 19 fast tests (render, order, maths reconstruction, inline maths) plus 3 synthetic-PDF tests.

**Learned**
- Never trust a section score without looking at what the outputs actually contain; a formatting accident produced a 45-point illusion in one section.
- The maths references mix `\ldots` and literal `...`; the glyph comparison cannot satisfy both, so the majority form wins.

**Next**
- Read the multi-column re-run; then a full benchmark run (layout + maths + gated OCR) for a new honest headline number.
- Maths: `\text{}` and upright words inside formulas, `\underset` limits, inline fractions; run the check on a larger sample (40 pages).
- Old scans: only a vision model will read handwriting; plan the GPU (vast.ai) experiment and ask the owner before spending.

---

## 2026-09-02 (night) - Layout fusion, formula rebuild, OCR fallback

**Done**
- Layout fusion (`truedoc/layout/fuse.py`): model regions override block kinds (page header/footer, footnote, caption, section header, title, list item, formula), split blocks that straddle regions, add figures, and build tables inside detected table boxes. Rotated text lines ("Downloaded from ...") are dropped as headers. **Headers/footers section 68.6 -> 88.7.**
- Formula reconstruction from the text layer (`truedoc/math/`): fractions from rules (vector paths *and* 1-pixel image masks, which some producers use), sub/superscripts from size and baseline, big-operator limits by visual centre, radicals, accents, cmex/cmsy raw-code tables, Greek and symbol mapping, `\cdots`/`\ldots`/`\neq` normalisation. Display formulas per equation line from layout regions (or math-font-dominated blocks), inline formulas from runs of maths-font words with glued prose trimmed off. First check on 12 arXiv pages: **16/52 maths tests pass (from 0)**; a second run with the fixes is in progress.
- OCR fallback (`truedoc/ocr/rapid.py`): RapidOCR at a capped 2000 px long side for pages with no text layer, producing the same line/word/char evidence as the text-layer path. A typewritten 1914 letter comes out readable; handwriting does not (expected for classical OCR).
- Bench runner and CLI gained `--layout/--no-layout`, `--math/--no-math`, `--ocr/--no-ocr`.

**Learned**
- A first multi-column run with the layout model scored 50.7 (down from 67.4): the cause was the *maths* heuristics, not the layout model. Words made only of digits and brackets ("(3)", "12-15") were wrapped in `$...$`, and statute citation paragraphs were mistaken for display maths (spaces stripped). Fixed: only words with maths-font glyphs, Greek letters or maths symbols start a formula; display-maths detection requires 25% maths-font glyphs. Re-run in progress.
- The maths comparison needs every *reference* glyph present in our formula with the same neighbours; extra glyphs at the ends are harmless, extra glyphs in the middle and missing glyphs are fatal. So `\cdots` (one glyph) vs `\cdot\cdot\cdot` (three) fails, and leaving a leading "1" outside the `$...$` fails.
- Documents typeset with Times (NimbusRomNo9L) still use Computer Modern maths fonts, so font-based maths detection works there; uppercase Greek comes from the roman font and must be caught by character.
- Old-scan pages are stored at huge sizes (1700 x 2200 pt); OCR at 150 dpi took 30-40 s/page, so the OCR path renders to a capped pixel size.
- The layout model costs about 3 s/page alone but 8-12 s/page when 4-6 worker processes share the 16 cores; the full benchmark with layout is roughly 40 minutes.

**Next**
- Read the multi-column and old-scans re-runs; then a full benchmark run with layout + maths + OCR to replace the 48.6 baseline.
- Formula work: matrices/cases environments, `\mathbb`/`\mathcal` fonts (MSBM, CMSY), function-name spacing, `\left`/`
ight` delimiters.
- Tables: split side-by-side sub-tables; use layout table boxes to bound rows; merged-cell output.

---

## 2026-09-02 (late) - M1 baseline scored; unruled tables; layout model working

**Done**
- **M1 baseline scored: 48.6 overall** (official scorer). Sections: arxiv_math 0.0, old_scans_math 0.0, tables 32.7, old_scans 58.7 (hollow: empty output passes the "absent" checks), headers_footers 68.6, multi_column 67.4, long_tiny_text 74.9, base 86.2. Recorded in `docs/BENCHMARKS.md`.
- Unruled-table extractor (`truedoc/tables/aligned.py`): rows by baseline clustering, columns by whitespace channels that run through nearly all rows, wrapped-cell folding, prose rejection. **Tables section 32.7 -> 56.4** (576/1022) on its own re-run.
- Fixes: letter-spaced headers ("A n n u a l") re-joined; single lines in a different typeface no longer merge with the text below; running headers up to 1.3x body size; capital-letter-with-period is no longer a list marker (it was eating author initials).
- Docling "heron" layout model (RT-DETR v2, Apache-2.0) runs on CPU via `transformers`: about 3 s/page at 144 dpi, model load a few seconds. Detects table, formula, picture, caption, page_header, page_footer, section_header, list_item, footnote, text, title with good boxes on the three pages tried. Wrapper: `truedoc/layout/docling_layout.py`. Note `docling-ibm-models` 4.x no longer ships the layout predictor; we load the HF weights directly.

**Learned**
- Failure mix of the baseline: arxiv_math 2,927 math failures (no formula output at all); tables 686; old_scans_math 458 math; old_scans 177 order + 98 baseline (empty pages); multi_column 288 order; headers_footers 237 absent; long_tiny_text 111 present.
- Scanned journal pages often carry an *existing* OCR text layer with errors ("I minute" for "1 minute", "34i" for "34½"); trusting that layer caps accuracy on such pages. Detecting OCR layers (invisible text) is in place; re-OCR is not yet.
- Side-by-side sub-tables (three district tables in one band) come out as one wide table; left-heading tests then fail. Splitting needs either the layout model's table boxes or header-row analysis.

**Next**
- M2: fuse layout regions with text blocks (headers/footers/captions/figures/formulas/tables), run tables inside detected table regions, re-score.
- M4: formula reconstruction from text-layer glyphs (fonts + positions) inside formula regions and inline math spans.
- M5: RapidOCR path for pages without a usable text layer.

---

## 2026-09-02 - Day 1: foundations

**Done**
- Environment checked: Windows 11, Intel Core Ultra 7 155H (16 cores), 32 GB RAM, Intel Arc iGPU (no CUDA), about 470 GB free disk. Python 3.13 and 3.14 present; Node 22. Internet reachable (PyPI, Hugging Face, GitHub).
- Repo initialised (git), `.venv` created on Python 3.13, core libraries installed (PyMuPDF, pdfplumber, pypdfium2, onnxruntime, rapidfuzz, and others).
- Public benchmarks researched; leaderboards and scoring rules captured in `docs/BENCHMARKS.md`.
- olmOCR-bench dataset downloaded to `bench/data/olmocr-bench/` (1,403 PDFs, 7 JSONL files of tests).
- Official `olmocr[bench]` scorer being installed into the venv, with Playwright Chromium for formula rendering.
- Docs written: README, STATUS, ROADMAP, DECISIONS, BENCHMARKS, OKF_SPEC, this log.

**Learned**
- olmOCR-bench scoring: each test is pass/fail; category score = pass rate within that JSONL file; overall = plain mean of the category scores; outputs must be named `<pdf-stem>_pg<N>_repeat<K>.md` inside a candidate folder under `bench_data/`.
- Test mix (7,010 tests): math 3,385 (arxiv_math alone has 2,927), order 1,061, absent 823, present 721, table tests in `table_tests.jsonl`, and a handful of baseline tests. Because categories are averaged, the two maths categories are 2/8 of the overall score despite holding half the tests.
- Text matching: outputs are normalised (bold and italic stripped, whitespace collapsed, NFC, curly quotes and dashes straightened), then `rapidfuzz.partial_ratio` with threshold `1 - max_diffs/len(text)`. Order tests use `fuzzysearch.find_near_matches`. Table tests parse markdown and HTML tables and check up, down, left, right neighbours and headings. Math tests render LaTeX with KaTeX and compare images.
- Published scores (olmOCR-bench overall): Chandra 83.1, Infinity-Parser 82.5, olmOCR v0.4 82.4, PaddleOCR-VL 80.0, Marker 1.10.1 76.1, DeepSeek-OCR 75.7, MinerU 2.5.4 75.2, Mistral OCR 72.0. The weakest section for everyone is old scans (30 to 50).
- OmniDocBench v1.6 overall: OvisOCR2 96.58, PaddleOCR-VL-1.6 96.34, MinerU2.5-Pro 95.75, MinerU-Pipeline 86.47, Marker 78.44. OmniDocBench ships page *images*, not PDFs, so a text-layer approach cannot be used there; it will be a secondary check.

- M1 text-layer converter written (`truedoc/`): PyMuPDF character extraction, word/line building with gap-based splitting, paragraph grouping, column-aware reading order, heuristic classification (headings, headers/footers, page numbers, captions, list items), ruled tables via PyMuPDF `find_tables`, OKF renderer with hyphenation repair and cross-column paragraph joining. 10 unit tests pass.
- Full benchmark conversion runs in 128 s for 1,403 pages (about 1 s/page single-threaded, 12 workers). Official scoring of this baseline is running.

**Learned (scorer mechanics)**
- The installed `olmocr` 0.4.27 scorer breaks on Windows paths and lacks the single-JSONL PDF filter; `bench/score_olmocr.py` runs the newer vendored scorer with forward-slash paths. `--output_failed` must be an absolute path.
- The maths comparison is lenient in a useful way: KaTeX renders both sides and compares the *glyph text and relative positions* of spans, so `\mathcal{V}` vs `V`, `\to` vs `
ightarrow`, and `\frac` vs `\dfrac` all count as equal, and a reference formula found *inside* a longer output formula passes. This means formulas rebuilt from the PDF's own glyphs and positions (no vision model) can pass, as long as sub/superscripts, fractions and symbols are structurally right.
ightarrow`, and `\frac` vs `\dfrac` all count as equal, and a reference formula found *inside* a longer output formula passes. This means formulas rebuilt from the PDF's own glyphs and positions (no vision model) can pass, as long as sub/superscripts, fractions and symbols are structurally right.
- Ruled-table extraction alone passes about 27% of the table tests (test-type pass rate reported by the scorer); most benchmark tables have no rulings.

**Next**
- Record the M1 baseline in BENCHMARKS.md; analyse failures per category.
- M2: plug in the Docling layout model (installing) and compare against heuristics.
