"""Two runs, every category, side by side - the check that run 90 needed and did not get.

Run 90 shipped a change measured on one category to all eight, and the category it broke was the one
never looked at. `compare_runs.py` counts checks won and lost; this shows where they were, so a gain in
one place cannot hide a collapse in another.

usage (repo root): compare_categories.py <run A number> <run B number>   e.g. compare_categories.py 89 91
"""
import json
import sys

a_n, b_n = sys.argv[1], sys.argv[2]


def read(n: str) -> tuple:
    txt = open(f"bench/out/launch/score{n}.log", encoding="utf-8").read()
    d = json.loads(txt[txt.index("{"):txt.rindex("}") + 1])
    return d["overall"], {k: (v["score"], v["passed"], v["total"]) for k, v in d["categories"].items()}


a_overall, a = read(a_n)
b_overall, b = read(b_n)

print(f"{'category':18s} {'run ' + a_n:>8s} {'run ' + b_n:>8s} {'checks':>18s}")
worst = []
for cat in sorted(a):
    s1, p1, t = a[cat]
    s2, p2, _ = b.get(cat, (0.0, 0, t))
    moved = p2 - p1
    mark = ""
    if moved <= -10:
        mark = "   <-- lost ground"
        worst.append((cat, moved))
    elif moved > 0:
        mark = "   +"
    print(f"{cat:18s} {s1:8.1f} {s2:8.1f} {p1:6d} -> {p2:<6d} {moved:+5d}{mark}")
print(f"{'OVERALL':18s} {a_overall:8.1f} {b_overall:8.1f} {b_overall - a_overall:+8.1f}")
if worst:
    print()
    print("categories that lost ten checks or more - look at these before calling the run a success:")
    for cat, moved in sorted(worst, key=lambda x: x[1]):
        print(f"   {cat}: {moved}")
else:
    print()
    print("no category lost ten checks or more")
