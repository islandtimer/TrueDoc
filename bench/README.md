# Benchmark harness

## Data

`bench/data/` is git-ignored. Download olmOCR-bench (about 2 GB) with:

```bash
.venv/Scripts/python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='allenai/olmOCR-bench', repo_type='dataset', local_dir='bench/data/olmocr-bench', allow_patterns=['bench_data/*.jsonl','bench_data/pdfs/**'])"
```

## Running TrueDoc on the benchmark

```bash
# everything (1,403 pages), then score with the official code
.venv/Scripts/python -m truedoc.cli bench --workers 12

# one category, scored against its own test file only (fast iteration)
.venv/Scripts/python -m truedoc.cli bench --categories tables --jsonl table_tests.jsonl
```

Outputs are written where the official scorer expects them:
`bench/data/olmocr-bench/bench_data/<candidate>/<category>/<name>_pg1_repeat1.md`.
Each run also leaves `bench/runs/<candidate>-<timestamp>/` with `summary.json`,
the raw scorer output and `failed_tests.jsonl` (the tests we failed, for
failure analysis).

## Tips

- `--candidate <name>` writes to a separate output folder, so a new full conversion can run while an older candidate is still being scored.
- `--workers 6` with the layout model and OCR is about the limit on a 16-core machine; more workers just thrash. A full conversion takes 60-100 minutes; scoring takes about 40 minutes (formula rendering dominates).
- `python bench/quick_check.py` is the 10-minute regression guard on 13 fixed pages; run it before a full run. `python bench/math_check.py --first 12 --show-fails` scores formulas on a few maths pages and prints why each failure failed.

## Helper tools (`bench/tools/`)

Small scripts used in the improvement loop. Each finds the repository from its own location, so they run from anywhere; run the Python ones with the project's virtual-environment Python.

- `launch_run.sh <N> <candidate> [sample2 minimum]`: validates the code on disk (unit tests; the quick gate at 96 of 128 or more; the two maths samples at 44 and 56 or more), launches a full benchmark conversion for `<candidate>` with six workers, waits for it, then scores it and its held-out slice. Progress goes to `bench/out/launch/launch<N>_status.txt`, whose last line reads "run N scored" when everything is done (about two hours). Runs chain with `until grep -q "run N scored" bench/out/launch/launchN_status.txt; do sleep 60; done; bash bench/tools/launch_run.sh N+1 truedocM`. Start it detached, `nohup bash bench/tools/launch_run.sh N truedocM 56 > bench/out/launch/nohupN.log 2>&1 &`, from a shell that will not time out: the validation alone can run 25 minutes and the whole run about two hours (the scorer is quick when a run's formulas match the previous run's, since rendered formulas are cached). Never edit `truedoc/` between the status file's "validating" and "launched" lines. Run N's candidate has been named `truedoc<N-2>` since run 3.
- `page_check.py <run_dir> <page stems...>`: converts the named benchmark pages with the current code and prints, per page, how many checks pass now against how many passed in `<run_dir>`, with a GAIN or LOSS line for every check that changed. This is how a rule is verified before a full run: check it on the pages it was written for and on a few it was not. `--controls '<latex substring>' N` adds N maths pages whose passing checks contain the substring.
- `run_summary.py <run_dir> [<previous_run_dir>]`: one screen with a scored run's overall score and interval, every category with its checks, the held-out and tuned-on scores, and the diff against the previous run. The first thing to run when a launcher's status file says "scored".
- `run_diff.py <old_run_dir> <new_run_dir> [N]`: gains and losses between two runs by category, with the first N losses named, to trace a regression to its page.
- `pair_probe.py <page stem> '<latex>' ...`: runs one page's formula checks against candidate LaTeX strings, to learn what the checker treats as equal (delimiter sizes never matter; `\tfrac` and `\frac` differ; `\notin` and `\not\in` differ).
- `glyph_sheet.py <out.png> <font substrings...> [--all]`: a contact sheet of the glyphs a maths font family uses across the maths pages, for filling the symbol tables in `truedoc/math/symbols.py` by eye.
- `scan_ctrl.py [--fix] <files...>` and `log_update.py <file> <old.txt> <new.txt>`: keep the documentation's backslashes intact. A shell heredoc turns `\f`, `\t`, `\b`, `\a`, `\r`, `\v` and `\n` inside LaTeX into control characters; edit the docs with a tool that writes bytes verbatim (or with `log_update.py`, which reads the old and new passages from files) and run `scan_ctrl.py docs/*.md` before committing.
- `ab_pages.py` and `ab_pool.py`: score benchmark pages - a named few, or whole subsets many at once - with the working tree as it stands, into a named folder under `bench/out/ab/`, so a change is measured code against code with the same options on both sides. `ab_pages.py --compare <base>_<subset> <label>_<subset>` sets two such folders side by side, page by page.
- `ab_footprint.py <base label> <label>`: the pages whose markdown differs between two such folders, even where no score moved. `review_pages.py <base label> <label>` then renders each of those pages to `bench/out/review/<label>/` with its markdown before and after, to be read against the image before a change is called free.
- `partial_footprint.py <candidate label> <base label> [<base label> ...]`: the same for a pool still converting, or stopped part way, over the pages both folders already hold; each subset takes the first base label with a folder for it, so a candidate can be set against bases converted in separate pools. `convert_compare.py [--pages 1,2] <pdf>=<markdown file> ...` converts named pages with whichever truedoc is on the path (a worktree on PYTHONPATH) and compares each with a conversion already on disk: a rule that can only change what an earlier version changed is checked on just those pages.
- `kfs_grade.py`: converts and grades every Key Facts Sheet in the owner's library against the structure the law prescribes, holding a fifth back by filename hash (decision D027). `kfs_three.py <label>=<cache dir> ...` grades several saved conversions with that one grader, tuned-on and held-out apart, and names every sheet whose header, answers, swallowed band or orphan rows differ; `kfs_quick.py <baseline cache dir> <fragment> ...` converts only the tuned-on sheets a rule was written for, a first look before the whole oracle; `kfs_why.py` and `answer_census.py` sort the sheets still failing by cause, so the next rule is aimed.
- `compare_categories.py <run A> <run B>`: two scored runs, every category side by side, so a change made for one category cannot quietly break another.
- `apply_draft.py <file> <old passage file> <new passage file> [--check]` and `fill_placeholders.py <values.json> <draft.txt> ...`: replace one passage that must occur exactly once, keeping the file's own line endings, and fill a draft's `@@NAME@@` numbers once they are measured.

The tools from `ab_pages.py` down are run from the repository root rather than finding it from their own location.

## Scoring only (outputs already exist)

```bash
.venv/Scripts/python bench/score_olmocr.py --dir bench/data/olmocr-bench/bench_data --candidate truedoc
```

`bench/score_olmocr.py` is a thin wrapper that makes the official scorer work on
Windows paths; it does not change any scoring rule. The official test code is
also copied into `bench/olmocr_ref/` for reading (Apache-2.0, AI2).

## Held-out pages (decision D016)

About one page in five (261 of 1,403, chosen by a stable hash of the file name and listed in `bench/holdout.txt`) is never looked at when a rule is tuned. `python bench/holdout_score.py <run_dir>` reports a run's score on those pages and on the rest separately, using the run's `failed_tests.jsonl`. The two numbers should move together; when the tuned-on score rises and the held-out score does not, a change was fitted to particular pages rather than to a real pattern.

## Maths spot-checks

Two fixed samples, run after any formula change (each takes 5-10 minutes on the loaded machine):

```bash
python bench/math_check.py --first 12
```

expected 44/52 (as of run 13), and the second sample of twelve pages chosen from run-11 failures:

```bash
python bench/math_check.py 2503.03873_pg5 2503.03879_pg4 2503.03899_pg9 2503.03903_pg9 2503.03905_pg7 2503.03909_pg14 2503.03948_pg3 2503.03949_pg1 2503.03952_pg5 2503.03994_pg108 2503.04024_pg4 2503.04026_pg2
```

expected 57/64 (as of run 31's launch, 4 Sept 18:26; 56 from run 28 to run 30, so 56 stays the floor for the launcher gate; 57 for a while on 4 Sept morning, 56 after round 10, 54 at run 13). The first sample expects 46/52 since run 32's launch (45 from run 28, 44 before). Add `--show-fails` to see the failing checks.

## The stopping rule for classical work

`python bench/tools/ceiling_census.py` (from the lateral round, 7 September) sorts every failing text and table check of the latest run into buckets: our output empty; text in the raw layer but not in our output; text in our output but the check still fails; text in neither; no text layer. The first three are the mechanical pool. Run it after each benchmark run; when the pool stops shrinking while runs keep landing, the classical path is done (decision D018). `bench/tools/lateral_census_concept_fan.py` prints the near-miss pairs for the tiny-text and multi-column sections, the harness for the two-witness test.

## Runs with the vision switch on

`bench/tools/launch_run.sh` passes the `EXTRA` environment variable to the bench command, so a run with the vision stage reads like this (run 55, 7 September 2026):

    EXTRA="--vision-endpoint file:bench/data/olmocr-bench/bench_data/olmocr2b --vision-pages-only" nohup bash bench/tools/launch_run.sh 55 truedoc54 56 > bench/out/launch/nohup55.log 2>&1 &

`file:<folder>` replays a model's saved readings (`truedoc/vision/file_readings.py`); a served model takes `http://host:port` instead. `bench/tools/watch_run.sh <N>` prints the run's status lines as they appear and exits when the run is scored, which is what the Monitor tool runs.

Since run 58 two folders are joined with `+` (whole-page readings and picture crops):

    EXTRA="--vision-endpoint file:bench/data/olmocr-bench/bench_data/olmocr2b+bench/data/olmocr-bench/bench_data/olmocr2c" nohup bash bench/tools/launch_run.sh <N> truedoc<N-1> 56 > bench/out/launch/nohup<N>.log 2>&1 &

**Page checks on pages a model read need the same setting**, or they show losses that are not real:

    PAGE_CHECK_ARGS="--vision-endpoint file:<olmocr2b>+<olmocr2c>" python bench/tools/page_check.py <run dir> <stem> ...

Capture a page check to a file rather than piping it through `tail`: the per-page lines are the
evidence, and the total alone cannot tell a real loss from a harness artefact. Until 8 September
the tool matched a page's checks with `t.pdf.endswith(name)`, so `old_scans/5.pdf` also collected
the checks for `15.pdf`, `25.pdf` ... `95.pdf` and reported two dozen losses that did not exist.
When a check reports a surprising loss, remove the change and run it again: if the numbers do not
move, the fault is in the measurement, not the code.

For the next GPU session the two tools beside the crop tool are `bench/gpu/select_bands.py` (dense pages cut into overlapping bands, plus `--also-whole` for pages whose table is a vector drawing) and `bench/gpu/merge_bands.py` (the bands stitched back into one reading, the overlap dropped); the recipe is in `bench/gpu/README.md`.
