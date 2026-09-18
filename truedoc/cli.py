"""Command line interface."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import typer

app = typer.Typer(add_completion=False, help="TrueDoc: PDF to OKF markdown.")


@app.command()
def convert(
    pdf: Path = typer.Argument(..., exists=True, readable=True, help="PDF file to convert"),
    out: Optional[Path] = typer.Option(None, "-o", "--out", help="Output .md path (default: stdout)"),
    frontmatter: bool = typer.Option(True, help="Include the YAML front matter block"),
    page_markers: bool = typer.Option(False, help="Insert <!-- page: N --> comments"),
    pages: Optional[str] = typer.Option(None, help="Pages to convert, e.g. '1,3-5'"),
    layout: bool = typer.Option(True, help="Use the layout-detection model (slower, better structure)"),
    math: bool = typer.Option(True, help="Rebuild formulas as LaTeX from the text layer"),
    ocr: bool = typer.Option(True, help="OCR pages without a text layer"),
    ocr_pictures: bool = typer.Option(False, "--ocr-pictures", help="Also OCR text kept as pictures on digital pages (experimental)"),
    doc_type: str = typer.Option("Document", "--type", help="OKF `type` for the front matter (e.g. Document, Reference, Playbook)"),
    vision_endpoint: Optional[str] = typer.Option(None, "--vision-endpoint", help="Optional vision stage: endpoint of a served olmOCR-style model, used only for pages with no usable text"),
    vision_deep: Optional[str] = typer.Option(None, "--vision-deep", help="A second, more expensive reader (e.g. 'anthropic') used only for pages the first one cannot manage: no text layer, and our own OCR of them finds nothing word-like"),
    vision_model: str = typer.Option("olmocr", "--vision-model", help="Model name the vision endpoint expects"),
    vision_pages_only: bool = typer.Option(False, "--vision-pages-only", help="With the vision stage on, read only unreadable pages; do not ask about icons and figures"),
    strict: bool = typer.Option(False, "--strict", help="Exit with code 3 when the conversion is not complete (a page nothing could read, a stage that could not run, a model reply cut off). The file is still written"),
    status: Optional[Path] = typer.Option(None, "--status", help="Write how the conversion ended to this file as JSON: completion, pages, and every issue with its code"),
):
    """Convert a PDF. Exit codes: 0 converted (any issues are listed on stderr and in the front matter);
    2 the request cannot be met (a page selection the document does not have); 3 with --strict, converted
    but not complete."""
    import json

    from truedoc.pipeline import ConvertOptions, PageSelectionError, convert_with_status

    try:
        page_list = _parse_pages(pages) if pages is not None else None
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--pages")
    opts = ConvertOptions(frontmatter=frontmatter, page_markers=page_markers, pages=page_list, layout=layout, math=math, ocr=ocr, ocr_pictures=ocr_pictures,
                          doc_type=doc_type, vision_endpoint=vision_endpoint, vision_model=vision_model, vision_regions=not vision_pages_only, vision_deep=vision_deep)
    try:
        result = convert_with_status(str(pdf), opts)
    except PageSelectionError as exc:
        typer.echo(f"truedoc: {exc}", err=True)
        raise typer.Exit(code=2)
    if out is None:
        sys.stdout.write(result.markdown)
    else:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(result.markdown, encoding="utf-8")
        typer.echo(f"wrote {out}")
    if status is not None:
        status.parent.mkdir(parents=True, exist_ok=True)
        status.write_text(json.dumps(result.as_dict(), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    # How it ended goes to stderr whatever was asked for: a body written to stdout, or one with no
    # front matter, or an empty one, carries no status of its own (D037).
    if result.issues:
        typer.echo(f"truedoc: {result.completion} - {len(result.issues)} issue(s)", err=True)
        for issue in result.issues:
            typer.echo(f"  [{issue.severity}] {issue.code}: {issue.message}", err=True)
    if strict and result.completion != "complete":
        raise typer.Exit(code=3)


def _parse_pages(spec: str) -> list[int]:
    """'1,3-5' as page numbers, in the order given. Anything that is not a page number or a range
    running forwards is refused: '2-1' used to mean no pages, which the pipeline took for all of them."""
    pages: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        ends = part.split("-")
        if len(ends) > 2 or not all(e.strip().isdigit() for e in ends):
            raise ValueError(f"'{part}' is not a page number or a range like 3-5")
        first, last = int(ends[0]), int(ends[-1])
        if first < 1:
            raise ValueError(f"'{part}': pages are numbered from 1")
        if last < first:
            raise ValueError(f"'{part}' runs backwards; write {last}-{first}")
        pages.extend(range(first, last + 1))
    if not pages:
        raise ValueError("no page was named")
    return pages


@app.command()
def bench(
    dataset: str = typer.Option("olmocr", help="Benchmark dataset: olmocr"),
    candidate: str = typer.Option("truedoc", help="Candidate name (output folder under bench_data)"),
    workers: int = typer.Option(8, help="Parallel workers for conversion"),
    categories: Optional[str] = typer.Option(None, help="Comma-separated category folders to run (default all)"),
    limit: Optional[int] = typer.Option(None, help="Only convert the first N PDFs per category"),
    score: bool = typer.Option(True, help="Run the official scorer after converting"),
    jsonl: Optional[str] = typer.Option(None, help="Score only this test file, e.g. table_tests.jsonl"),
    layout: bool = typer.Option(True, help="Use the layout-detection model"),
    ocr: bool = typer.Option(True, help="OCR pages without a text layer"),
    vision_endpoint: Optional[str] = typer.Option(None, "--vision-endpoint", help="Optional vision stage endpoint for pages with no usable text"),
    vision_pages_only: bool = typer.Option(False, "--vision-pages-only", help="With the vision stage on, read only unreadable pages; do not ask about icons and figures"),
    vision_deep: Optional[str] = typer.Option(None, "--vision-deep", help="A second, more expensive reader used only for pages the first one cannot manage"),
):
    from truedoc.bench.olmocr import run_olmocr_bench

    cats = [c.strip() for c in categories.split(",")] if categories else None
    run_olmocr_bench(candidate=candidate, workers=workers, categories=cats, limit=limit, score=score, jsonl=jsonl, layout=layout, ocr=ocr,
                     vision_endpoint=vision_endpoint, vision_regions=not vision_pages_only,
                     vision_deep=vision_deep)


if __name__ == "__main__":
    app()
