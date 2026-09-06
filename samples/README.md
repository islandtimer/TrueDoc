# Sample PDFs

Drop PDFs here that show something TrueDoc must get right. They are test cases,
not benchmark data. Convert one with:

    python -m truedoc.cli convert samples/<file>.pdf -o samples/<file>.md

Wanted right now:

- The insurance document whose tables use tick and cross icons (not text) to say
  which line items apply to home cover and to contents cover.

Files here:

- `aldi-household-pds.pdf`: ALDI household insurance PDS (from the owner's library, 3 Sept 2026). Pages 20 and 24 are
  diagrams with numbered dots; page 7 is a table of contents with dot leaders. Not the tick-and-cross table.
  Page 32 is the test page for ringed marks: a circled tick before "You are covered for" items, a circled cross before
  "You are not covered for", and a circled dollar sign (which must not be read as a mark) before limits. Pages 1 of the
  ALDI key facts sheets and page 22 of the ANZ home PDS (in the owner's library) carry similar icons.
