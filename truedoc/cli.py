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
):
    from truedoc.pipeline import ConvertOptions, convert as _convert

    page_list = _parse_pages(pages) if pages else None
    opts = ConvertOptions(frontmatter=frontmatter, page_markers=page_markers, pages=page_list, layout=layout, math=math, ocr=ocr, ocr_pictures=ocr_pictures,
                          doc_type=doc_type, vision_endpoint=vision_endpoint, vision_model=vision_model, vision_regions=not vision_pages_only, vision_deep=vision_deep)
    text = _convert(str(pdf), opts)
    if out is None:
        sys.stdout.write(text)
    else:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        typer.echo(f"wrote {out}")


def _parse_pages(spec: str) -> list[int]:
    pages: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            pages.extend(range(int(a), int(b) + 1))
        else:
            pages.append(int(part))
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
):
    from truedoc.bench.olmocr import run_olmocr_bench

    cats = [c.strip() for c in categories.split(",")] if categories else None
    run_olmocr_bench(candidate=candidate, workers=workers, categories=cats, limit=limit, score=score, jsonl=jsonl, layout=layout, ocr=ocr,
                     vision_endpoint=vision_endpoint, vision_regions=not vision_pages_only)


if __name__ == "__main__":
    app()
