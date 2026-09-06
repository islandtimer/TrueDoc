"""One-screen summary of a scored benchmark run, with the diff against a previous run.

usage: python bench/tools/run_summary.py <run_dir> [<previous_run_dir>]

Prints the overall score and confidence interval, every category's score and
passed/total, the held-out and tuned-on scores (recomputed from failed_tests.jsonl
through bench/holdout_score.py's logic), and, with a previous run, the checks won
and lost per category with the first losses named.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))


def main():
    run_dir = sys.argv[1]
    prev = sys.argv[2] if len(sys.argv) > 2 else None
    s = json.load(open(os.path.join(run_dir, "summary.json"), encoding="utf-8"))
    ci = s.get("ci") or [0, 0]
    print("%s: overall %.1f (CI %.1f-%.1f)" % (s.get("candidate", os.path.basename(run_dir)), s["overall"], ci[0], ci[1]))
    prev_s = json.load(open(os.path.join(prev, "summary.json"), encoding="utf-8")) if prev else None
    for cat, v in s["categories"].items():
        line = "  %-16s %5.1f  (%d/%d)" % (cat, v["score"], v["passed"], v["total"])
        if prev_s and cat in prev_s["categories"]:
            pv = prev_s["categories"][cat]
            line += "   was %5.1f (%+d checks)" % (pv["score"], v["passed"] - pv["passed"])
        print(line)
    py = sys.executable
    out = subprocess.run([py, os.path.join(REPO, "bench", "holdout_score.py"), run_dir], capture_output=True, text=True, encoding="utf-8", errors="replace")
    for line in out.stdout.splitlines():
        if line.startswith(("held-out", "tuned-on")):
            print("  " + line.strip())
    if prev:
        print()
        sys.stdout.flush()
        subprocess.run([py, os.path.join(HERE, "run_diff.py"), prev, run_dir, "10"])


if __name__ == "__main__":
    main()
