"""Convert the benchmark pages `drawn_census.py` lists with whichever truedoc PYTHONPATH selects, and set each against the
`prules` pool's markdown for the same page: whether the markdown changed, and the page's checks passed before and after,
both sides scored here by the benchmark's own tests.

`redraw_tables` can change only a page on which `drawn_grids` reads a table, so these pages are every benchmark page the
drawn-cells rule can move.

On 15 Sept, against the `prules` pool: of the 24 pages, only bdb0c069 pg42 changed, from 0 to 2 of its 3 table checks; the
other 23 read byte for byte as the pool read them (80 to 82 of the 91 checks on those pages).

usage: fills_bench_compare.py <out dir> <census file>     (truedoc from PYTHONPATH)
"""
import glob
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BD = REPO + "/bench/data/olmocr-bench/bench_data"
AB = REPO + "/bench/out/ab"
sys.stdout.reconfigure(encoding="utf-8")


def tests_for(subset: str) -> dict:
    name = "table_tests.jsonl" if subset == "tables" else subset + ".jsonl"
    found: dict[str, list] = {}
    for line in open(os.path.join(BD, name), encoding="utf-8"):
        line = line.strip()
        if line:
            t = json.loads(line)
            found.setdefault(os.path.basename(str(t.get("pdf", ""))), []).append(t)
    return found


def census_pages(path: str) -> list[str]:
    names, inside = [], False
    for line in open(path, encoding="utf-8"):
        if line.startswith("== "):
            inside = line.startswith("== bench")
            continue
        m = re.match(r"^   (\S+\.pdf) p1:", line)
        if inside and m:
            names.append(m.group(1))
    return names


def passed(tests: list, md: str) -> tuple[int, list]:
    from olmocr.bench.tests import load_single_test

    ok, results = 0, []
    for t in tests:
        try:
            good, _ = load_single_test(t).run(md)
        except Exception:
            good = False
        ok += bool(good)
        results.append(bool(good))
    return ok, results


def main() -> None:
    import truedoc
    from truedoc.pipeline import ConvertOptions, convert

    out_dir, census = sys.argv[1], sys.argv[2]
    os.makedirs(out_dir, exist_ok=True)
    print("truedoc from", truedoc.__file__, flush=True)
    cache: dict[str, dict] = {}
    totals = [0, 0, 0]
    for name in census_pages(census):
        pdfs = glob.glob(os.path.join(BD, "pdfs", "*", name))
        if len(pdfs) != 1:
            print(f"   {name}: {len(pdfs)} files match", flush=True)
            continue
        subset = os.path.basename(os.path.dirname(pdfs[0]))
        base_path = os.path.join(AB, f"prules_{subset}", name + ".md")
        base = open(base_path, encoding="utf-8").read() if os.path.exists(base_path) else None
        try:
            md = convert(pdfs[0], ConvertOptions(frontmatter=False))
        except Exception as exc:
            md = "FAILED " + repr(exc)
        with open(os.path.join(out_dir, name + ".md"), "w", encoding="utf-8") as fh:
            fh.write(md)
        if subset not in cache:
            cache[subset] = tests_for(subset)
        tests = cache[subset].get(name, [])
        before, br = passed(tests, base) if base is not None else (0, [])
        after, ar = passed(tests, md)
        flips = [(t.get("type"), str(t.get("cell") or t.get("text") or t.get("before") or "")[:50], b, a)
                 for t, b, a in zip(tests, br, ar) if b != a]
        totals[0] += before
        totals[1] += after
        totals[2] += len(tests)
        same = base is not None and base == md
        print(f"   {subset:16s} {name[:48]:50s} {'same' if same else 'CHANGED'}  {before} -> {after} of {len(tests)}",
              flush=True)
        for kind, text, b, a in flips:
            print(f"        {kind} '{text}': {'pass' if b else 'fail'} -> {'pass' if a else 'fail'}", flush=True)
    print(f"total on these pages: {totals[0]} -> {totals[1]} of {totals[2]}", flush=True)


if __name__ == "__main__":
    main()
