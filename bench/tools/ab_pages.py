"""Score benchmark pages with the working tree as it stands, into a named folder, for an A/B.

Why this exists. `page_check.py` compares the working tree against a past run's `failed_tests.jsonl`,
which is the right tool when the past run used the same converter options. On 13 September it was used
against a run launched with `--vision-endpoint file:...olmocr2b+...olmocr2c --vision-deep anthropic`
while the check itself passed no vision flags at all. Every page the benchmark run had read with a
model scored near zero locally, and the gap - 48 checks across 21 pages - was read as a regression in
a change that turned out to touch three checks in the whole category. Two hours went into chasing it.
A control run of the unmodified code scored *identically*, page for page, which is what should have
been run first.

So: this converts with whatever the working tree holds right now, writes the markdown and the scores
under a name you choose, and compares nothing. Run it once with your change, once with it stashed,
and diff the two - both sides then carry the same options, the same machine and the same code path,
and the only difference is the change.

usage (repo root):
    ab_pages.py after  tables/8b02fc... 5c6a9a49 ...     score named pages into bench/out/ab/after
    ab_pages.py after  --subset tables                   the whole subset
    ab_pages.py --compare before after                   what moved between two folders
"""
import glob
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
B = os.path.join(REPO, "bench", "data", "olmocr-bench", "bench_data")
AB = os.path.join(REPO, "bench", "out", "ab")
PY = sys.executable


def tests_for(subset: str):
    from olmocr.bench.tests import load_tests
    name = "table_tests" if subset == "tables" else subset
    return load_tests(os.path.join(B, name + ".jsonl"))


def compare(a: str, b: str) -> None:
    ra = json.load(open(os.path.join(AB, a, "scores.json"), encoding="utf-8"))
    rb = json.load(open(os.path.join(AB, b, "scores.json"), encoding="utf-8"))
    shared = sorted(set(ra) & set(rb))
    moved = [(k, ra[k], rb[k]) for k in shared if ra[k][0] != rb[k][0]]
    ta, tb = sum(ra[k][0] for k in shared), sum(rb[k][0] for k in shared)
    print(f"{len(shared)} pages scored both ways")
    print(f"   {a}: {ta}    {b}: {tb}    delta {tb - ta:+d}")
    if not moved:
        print("   no page moved: the change is a no-op on these pages")
        return
    for k, (na, tot), (nb, _) in sorted(moved, key=lambda r: r[1][0] - r[2][0]):
        print(f"   {nb - na:+3d}  {k[:52]:54s} {na}/{tot} -> {nb}/{tot}")


def main() -> None:
    args = sys.argv[1:]
    if args and args[0] == "--compare":
        compare(args[1], args[2])
        return

    label, args = args[0], args[1:]
    out_dir = os.path.join(AB, label)
    os.makedirs(out_dir, exist_ok=True)

    stems = []
    if args and args[0] == "--subset":
        subset = args[1]
        name = "table_tests" if subset == "tables" else subset
        for line in open(os.path.join(B, name + ".jsonl"), encoding="utf-8"):
            if line.strip():
                s = os.path.basename(json.loads(line)["pdf"]).split(".pdf")[0]
                if s not in stems:
                    stems.append(s)
    else:
        stems = args

    scores = {}
    for n, s in enumerate(stems, 1):
        pdfs = ([os.path.join(B, "pdfs", s.replace("/", os.sep))] if "/" in s
                else glob.glob(os.path.join(B, "pdfs", "*", s + "*.pdf")))
        pdfs = [p for p in pdfs if os.path.exists(p)]
        if not pdfs:
            print(s, "no pdf")
            continue
        pdf = pdfs[0]
        subset = os.path.basename(os.path.dirname(pdf))
        md_path = os.path.join(out_dir, os.path.basename(pdf) + ".md")
        r = subprocess.run([PY, "-m", "truedoc.cli", "convert", pdf, "--no-frontmatter", "-o", md_path],
                           cwd=REPO, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            print(s, "convert failed:", r.stderr[-200:])
            continue
        md = open(md_path, encoding="utf-8").read()
        mine = [t for t in tests_for(subset) if os.path.basename(t.pdf) == os.path.basename(pdf)]
        passed = sum(1 for t in mine if t.run(md)[0])
        scores[s] = (passed, len(mine))
        print(f"  {n:3d}/{len(stems)}  {s[:50]:52s} {passed}/{len(mine)}", flush=True)

    with open(os.path.join(out_dir, "scores.json"), "w", encoding="utf-8") as fh:
        json.dump(scores, fh, indent=1)
    total = sum(p for p, _ in scores.values())
    of = sum(t for _, t in scores.values())
    print(f"\n{label}: {total}/{of} over {len(scores)} pages  ->  bench/out/ab/{label}/")


if __name__ == "__main__":
    main()
