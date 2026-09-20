"""Which Key Facts Sheets' conversions differ from the copies kept before a change.

Copy `bench/out/kfs/*.md` to a folder, change the code, run `kfs_grade.py --fresh`, then run this: tuned-on sheets
that differ are named, held-out sheets are counted and never named.

usage (repo root): kfs_changed.py <folder holding the copies made before the change>
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kfs_grade

before = sys.argv[1]
named, hidden, same, missing = [], 0, 0, 0
for _insurer, pdf in kfs_grade.sheets():
    now = kfs_grade.cache_path(pdf)
    old = os.path.join(before, os.path.basename(now))
    if not os.path.exists(old) or not os.path.exists(now):
        missing += 1
        continue
    if open(old, encoding="utf-8").read() == open(now, encoding="utf-8").read():
        same += 1
    elif kfs_grade.held_out(pdf):
        hidden += 1
    else:
        named.append(os.path.basename(now))
print("sheets the same: %d | differ: %d tuned-on, %d held out (counted, never named) | no pair: %d" % (same, len(named), hidden, missing))
for n in named:
    print("   ", n)
