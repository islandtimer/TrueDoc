# Roadmap

Milestones are ordered; each one is measured before the next starts. "Score" means the olmOCR-bench overall score unless stated (see `docs/BENCHMARKS.md`).

| # | Milestone | What it delivers | Done when |
|---|---|---|---|
| M0 | Foundations | Repo, docs, benchmark data on disk, the official scorer running locally | Scorer runs end to end on a trial output folder |
| M1 | Honest baseline | Text-layer-only converter (no models): reading order, paragraphs, headings, simple tables | Full benchmark run; score recorded in BENCHMARKS.md |
| M2 | Structure engine | Layout detection (columns, tables, figures, headers and footers), header and footer removal, heading levels, list detection, hyphenation repair | Beats Marker on multi-column, headers and footers, long-tiny-text, base |
| M3 | Tables | Cell-accurate tables from text layer + ruling lines + a structure model; merged cells as HTML | Beats MinerU 2.5 on the tables section |
| M4 | Formulas | LaTeX for display and inline maths (text-layer aware, model-assisted) | Competitive on the arxiv-math section |
| M5 | Scanned pages | OCR path for pages without a usable text layer (open-source OCR or a small vision model, GPU rental if needed), with the same structure engine on top | Competitive on the old-scans sections |
| M6 | Verification layer | Cross-check every model output against raw evidence; confidence score in front matter; nothing invented | Zero invented sentences on a hand-audited sample |
| M7 | Beat them all | Overall score above every published tool on both public benchmarks | Recorded run, reproducible from this repo |
| M7b | Marks that carry meaning | Ticks, crosses, bullets drawn as shapes, tiny images or symbol-font glyphs read into the text | Icon-based tables in the owner's insurance library convert with their meaning intact |
| M8 | Product polish | CLI, batch mode writing an OKF bundle (`index.md`, `log.md`, `okf_version`), cost controls, docs for new users | A stranger can install and convert a folder of PDFs in 10 minutes |

Milestones M2 to M6 loop: build, measure, look at failures, fix, repeat.

## Status of the milestones (updated 2026-09-08, after run 63)

| # | State | Evidence |
|---|---|---|
| M0 | done | Official scorer runs locally; 128 unit tests; quick regression check on 13 pages (`bench/quick_check.py`); the loop's helper tools in `bench/tools/` |
| M1 | done | First full run 48.6 (about 43 once a scorer artefact is removed) |
| M2 | done | Its four sections all beat Marker 1.10.1 at run 63: headers and footers 68.6 -> 96.8 (Marker 86.6), multi-column 68.4 -> 82.9 (80.0), tiny text 88.5 (85.7), baseline 99.8 (99.3). The multi-column family of rules (runs 61 to 63) closed the last gap |
| M3 | done | Tables 32.7 -> 88.2 at run 63, past MinerU 2.5's 84.9 and Chandra's 88.0: the best published figure for the section. 121 of 1,022 checks still fail, a long tail of one-page shapes |
| M4 | done | Formula rebuild from glyphs: 0 -> 87.4 on arXiv maths at run 63, above every published figure (the best is PaddleOCR-VL's 85.7); old-scan maths 4.1 -> 80.8 once a model reads the scans. 369 arXiv checks still fail, at diminishing returns per rule |
| M5 | done | The vision stage is the product path since D019 (run 55 onward): every page without a digital text layer is read by a model, the rest keep their exact text. Old scans 20.7 -> 47.3, old-scan maths 4.1 -> 80.8 at run 63. Competitive, not leading: Chandra publishes 50.4 and Infinity-Parser 83.8, and both gaps are the model's reading quality rather than our code |
| M6 | done | Provenance on every block; OCR gate and empty-output rule; hidden text kept out of the body and listed in the front matter (D011); model-read text marked `[^inferred]` (D015); a document-level confidence figure exists, no per-block one yet. **9 Sept: the invented-text check on model pages is built (D021, `truedoc/vision/corroborate.py`)** - every model-read page is checked against what we can read of it ourselves and a verdict per page goes in the front matter (over the 281 benchmark model pages: 181 corroborated, 91 unchecked for want of a witness, 7 low support, 2 unverified). It reports and never acts, because every low-support page measured had a broken witness rather than an inventing model
