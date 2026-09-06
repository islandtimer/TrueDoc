"""Gains and losses between two benchmark runs, from their failed_tests.jsonl files.

usage: python bench/tools/run_diff.py <old_run_dir> <new_run_dir> [N]
Prints per-category counts of checks that newly pass (gains) and newly fail (losses), and up to N
examples of each loss (page, check text) so a regression can be traced to its page.
"""
import collections
import json
import os
import sys


def load(run_dir):
    out = {}
    for line in open(os.path.join(run_dir, "failed_tests.jsonl"), encoding="utf-8"):
        if line.strip():
            t = json.loads(line)
            out[(t["pdf"], t.get("id"))] = t
    return out


def main():
    old, new = load(sys.argv[1]), load(sys.argv[2])
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 12
    gains = [k for k in old if k not in new]
    losses = [k for k in new if k not in old]
    cat = lambda k: k[0].split("/")[0]
    gc, lc = collections.Counter(cat(k) for k in gains), collections.Counter(cat(k) for k in losses)
    print("category            gains  losses")
    for c in sorted(set(gc) | set(lc)):
        print("%-18s %6d %7d" % (c, gc[c], lc[c]))
    print("total              %6d %7d" % (len(gains), len(losses)))
    print("\nlosses (first %d):" % n)
    for k in losses[:n]:
        t = new[k]
        desc = t.get("math") or t.get("text") or t.get("cell") or t.get("type")
        print("  %s | %s" % (k[0], str(desc)[:110]))


if __name__ == "__main__":
    main()
