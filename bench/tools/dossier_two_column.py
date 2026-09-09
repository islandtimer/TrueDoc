"""Restack a generated dossier so the evidence and the decision are on screen together.

The generator lays a card out as one column: chips, title, image, fields, verification, guidance,
then the controls. With a tall evidence image that means scrolling away from the picture to read
what you are deciding about, which is exactly backwards for a page whose whole point is judging
against evidence. This injects a stylesheet that puts the image in a sticky left column and
everything else on the right, so both are visible at once, and collapses back to one column on a
narrow screen. Nothing else about the page changes: the persistence, filters and export are the
generator's own.

    python bench/tools/dossier_two_column.py <dossier.html>
"""
import sys

CSS = """
<style>
  /* Evidence and decision side by side: the image stays put while the text is read. */
  header > div, .filters, main, footer { max-width: 1560px !important; }
  .card {
    display: grid;
    grid-template-columns: 460px minmax(0, 1fr);
    column-gap: 24px;
    align-items: start;
  }
  .card > * { grid-column: 2; }
  .card-top { grid-column: 1 / -1; }
  .card-img {
    grid-column: 1;
    grid-row: 2 / span 60;
    position: sticky;
    top: 14px;
    width: 100%;
    max-width: 460px;
    align-self: start;
  }
  .card-title { margin-top: 0; }
  .disp { flex-wrap: wrap; }
  .note { min-width: 240px; }
  @media (max-width: 1080px) {
    .card { grid-template-columns: 1fr; }
    .card > *, .card-img { grid-column: 1; grid-row: auto; position: static; max-width: 100%; }
  }
</style>
"""


def main():
    path = sys.argv[1]
    with open(path, encoding="utf-8") as f:
        html = f.read()
    if "Evidence and decision side by side" in html:
        print("already restacked")
        return
    if "</head>" not in html:
        raise SystemExit("no </head> found - has the generator changed?")
    html = html.replace("</head>", CSS + "</head>", 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print("restacked %s" % path)


if __name__ == "__main__":
    main()
