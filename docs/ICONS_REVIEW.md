# Do icons carry meaning, and can we work out what they mean? (8-9 September 2026)

The Huddle Black benefit table converted with every coverage cell empty (fixed 8 September: see the
mark-reader repairs in `truedoc/marks.py`). That raised a general question the owner put plainly:

> if the words already contain the meaning, then the icon is just illustration and is not necessary
> for understanding the document

and asked how TrueDoc might find the icons that *do* carry meaning, then work out what they mean.

**Answer, after measuring: for this corpus the problem is small enough not to be worth building for.
The one document where icons genuinely carried meaning is already fixed. No GPU session is needed.**

## The design that was measured

An icon earns a place in the output only when deleting it would lose a distinction the document is
making. That gives two mechanical tests - does it **vary** across parallel slots, and is it already
**named** by text beside it - and an evidence ladder for what it means: the document's own legend,
then a self-describing occurrence elsewhere (the owner's insight: the redundant labelled use is the
teacher), then convention, then a model, then an honest placeholder.

The key architectural point survives everything below: reason per **distinct symbol**, not per page
or per occurrence. Across the corpus 15,085 occurrences collapse to 171 shapes - 88 occurrences per
thing - which is why per-page vision would be the wrong tool even if the problem were real.

## What the corpus says (`bench/tools/icon_census.py`, 1,176 documents, 23,870 pages, 251 s)

| | |
|---|---|
| documents using icons at all | 326 (28%), averaging **7.6 distinct icons** each |
| documents with load-bearing icons | 171 (15%), averaging 4.7 each - 803 in total |
| explained inside their own document | 332 of 803 (41%) |
| ... by a **legend block** | 77 |
| ... by a **short label beside the icon** | 314 |
| documents carrying a legend at all | 66 (**6%**) |

Legends are rare. The self-describing occurrence - the icon sitting beside its own label somewhere -
is available four times more often, so it, not the legend page, is the mechanism that would do the
work. That was the owner's observation and the numbers back it.

## What human review says (`bench/out/dossier2/icons.html`, 159 shapes, 152 decided)

The structural filter's proposals were **wrong on 92 of the 119** cards where it offered one -
agreement 23%. It proposed "carries meaning" for 71 pictograms and was overridden on 62; "ignore"
for 55 letter-shapes and was overridden on 30. **The filter must not ship as it stands.**

**Pictograms are fragments of illustrations.** The "contrasting set of the same size" test matches
coincidental pairs *inside a picture*. In the owner's words, on the two most-used shapes in the whole
corpus (188 and 118 uses): *"this specific occurrence is an icon that denotes a feature on a floor
plan. This is not a tick."* Also *"a red light shade hanging from the ceiling"*, *"not a tick - this
depicts the hair of a female"*, *"not a cross - ... an illustration referring to a broken window"*,
*"not a dot - it is a depiction of the wheel of a car"*.

**Letters spell words, but words we already have.** 30 letter-shapes were marked as carrying meaning,
each named to its word: "insurance", "coles", "Allianz", "CGU", "AUSTRALIAN", "people", "know",
"Good", a phone number, a URL. Checked afterwards against the text layer: coles insurance, CGU, RACT
and the phone number are all **already in the text**, so the drawn glyphs are a duplicate rendering
and ignoring them loses nothing. Where the word is genuinely absent - "Allianz" on a page holding 44
characters, "LUCKY YOU'RE WITH AAMI" on the AAMI covers - it is a cover-page logo whose brand name
appears elsewhere in the document. A cover-page fidelity gap, not a meaning loss.

## The one genuine find, and it was the owner's

**Directional arrows that carry reading order.** Three shapes, about 157 uses across roughly eight
documents:

> "this is a directional arrow, intended to direct the reader to the words to be read next. look on
> page 75, which shows multiple of these arrows, directing the reader to read the applicable text."

Not a value symbol like a tick: an instruction about **what to read next**, which belongs to reading
order rather than cell content. No structural test in this project would have found it. Example:
`aami-home-building-insurance-pds-a01463_4906c3da.pdf`, page 11, and page 75 for the fuller pattern.

Also called meaning: 9 pictograms (mostly single-document schemes) and the letter "A" from Allianz.

## Verdict

Do not build the icon-resolution pipeline. The population it would serve is roughly a dozen shapes;
the one document where icons genuinely carried meaning is fixed; and the GPU session it would have
justified is unnecessary, because the 156-crop estimate collapsed the moment a person ruled out the
illustration fragments for nothing.

Open: the directional arrows, as a reading-order question.

## Tools kept

- `bench/tools/icon_census.py` - the three counts over a folder of PDFs.
- `bench/tools/icon_dossier.py` - builds a review spec: one card per distinct shape, with the icon
  enlarged and the band of page it sits in, its reach, and a proposal with its own failure mode.
- `bench/tools/dossier_two_column.py` - restacks a generated dossier so evidence and decision are on
  screen together.
