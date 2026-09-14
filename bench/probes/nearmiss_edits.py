"""For the checks the benchmark could not find but whose words we did write, what exactly differs - and
did the check allow any edits at all? Both texts are put through the benchmark's own `normalize_text`
first, which already folds curly quotes, en and em dashes and unicode forms to ASCII: a first version of
this script compared the raw texts and reported a pile of differences the checker never sees.
usage (repo root): nearmiss_edits.py <run dir> <candidate folder> [category] [how many]"""
import collections
import difflib
import glob
import json
import os
import sys

from fuzzysearch import find_near_matches
from olmocr.bench.tests import normalize_text

run_dir, cand = sys.argv[1], sys.argv[2]
cat = sys.argv[3] if len(sys.argv) > 3 else "old_scans"
show = int(sys.argv[4]) if len(sys.argv) > 4 else 18
B = os.path.join("bench", "data", "olmocr-bench", "bench_data", cand)

cache = {}


def flat(pdf: str) -> str:
    if pdf not in cache:
        hits = glob.glob(os.path.join(B, os.path.splitext(pdf)[0] + "*.md"))
        cache[pdf] = normalize_text(open(hits[0], encoding="utf-8").read()) if hits else ""
    return cache[pdf]


rows = [json.loads(l) for l in open(os.path.join(run_dir, "failed_tests.jsonl"), encoding="utf-8")]
rows = [r for r in rows if r["pdf"].startswith(cat + "/")]

kinds = collections.Counter()
printed = 0
allowed_zero = 0
misses = 0
for r in rows:
    hay = flat(r["pdf"])
    if not hay:
        continue
    for field in ("text", "before", "after"):
        want = normalize_text(" ".join(str(r.get(field) or "").split()))
        if not want or len(want) < 12:
            continue
        if want in hay:
            continue
        near = find_near_matches(want, hay, max_l_dist=max(1, len(want) // 8))
        if not near:
            continue
        m = min(near, key=lambda x: x.dist)
        ours = hay[m.start:m.end]
        misses += 1
        allowed = r.get("max_diffs", 0) or 0
        if allowed == 0:
            allowed_zero += 1
        ops = [op for op in difflib.SequenceMatcher(a=want, b=ours, autojunk=False).get_opcodes() if op[0] != "equal"]
        sig = "; ".join(f"{want[i1:i2]!r}->{ours[j1:j2]!r}" for _tag, i1, i2, j1, j2 in ops[:3])
        kinds[sig[:60]] += 1
        if printed < show:
            printed += 1
            print(f"   {r['pdf'].split('/')[-1][:24]:26s} {r.get('type'):8s} allows {allowed} edits, takes {m.dist}")
            print(f"      want {want[:110]}")
            print(f"      ours {ours[:110]}")
            print(f"      diff {sig[:110]}")
print()
print(f"{misses} near misses in {cat} (after the benchmark's own normalisation); {allowed_zero} allow no edits")
print("the most common differences:")
for sig, n in kinds.most_common(14):
    print(f"   {n:4d}  {sig}")
