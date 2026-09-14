"""Grade several caches of converted Key Facts Sheets with the one grader, sheet by sheet, tuned-on and held-out apart.

Totals hide trades: a sheet that gains its header while another loses one reads as no change, and an
unchanged answer count can be twenty gained and twenty lost. This grades every cache with `kfs_grade.grade`
itself (never a copy of it), on the grader's own list of sheets and its own held-out split, and names every
sheet whose header or answers differ between consecutive code states.

usage (repo root): kfs_three.py <label>=<cache dir> <label>=<cache dir> [...]
    e.g. kfs_three.py committed=bench/out/kfs_head_cache unfixed=bench/out/kfs_guard_cache fixed=bench/out/kfs
"""
import collections
import io
import os
import sys

sys.path.insert(0, os.path.join("bench", "tools"))
from kfs_grade import cache_path, grade, held_out, sheets  # noqa: E402


def whole(g: dict) -> bool:
    """Header whole as the grader's report counts it: all three parts in the header row, none in the body."""
    return bool(g.get("found") and g["header_whole"] and not g["header_leaks"])


def main() -> None:
    states = [a.split("=", 1) for a in sys.argv[1:]]
    per: dict[str, tuple[str, dict]] = {}
    missing: collections.Counter = collections.Counter()
    for insurer, path in sheets():
        name = os.path.basename(cache_path(path))
        row = {}
        for label, folder in states:
            p = os.path.join(folder, name)
            if os.path.exists(p):
                row[label] = grade(io.open(p, encoding="utf-8").read())
            else:
                missing[label] += 1
        if len(row) == len(states):
            per[path] = (insurer, row)

    for title, keep in (("Tuned on", lambda p: not held_out(p)), ("Held out (never tuned on)", held_out)):
        group = {p: v for p, v in per.items() if keep(p)}
        print(f"== {title}: {len(group)} sheets")
        for label, _ in states:
            gs = [row[label] for _, row in group.values()]
            events = sum(g.get("events", 0) for g in gs) or 1
            hw = sum(whole(g) for g in gs)
            answers = sum(g.get("answers_attached", 0) for g in gs)
            opens = sum(g.get("events_in_rows", 0) for g in gs)
            print(f"   {label:10s} header whole {hw:3d} ({hw / max(1, len(gs)):.0%})   answers {answers}/{events} ({answers / events:.1%})"
                  f"   in rows {opens}   bands swallowed {sum(bool(g.get('band_swallowed')) for g in gs)}"
                  f"   orphans {sum(bool(g.get('orphans')) for g in gs)}   no table {sum(not g.get('found') for g in gs)}")
        for (la, _), (lb, _) in zip(states, states[1:]):
            moved = []
            for p, (insurer, row) in sorted(group.items()):
                a, b = row[la], row[lb]
                dh = int(whole(b)) - int(whole(a))
                da = b.get("answers_attached", 0) - a.get("answers_attached", 0)
                # A band or an orphan row can change without a header or an answer moving, so they are named too.
                db = int(bool(b.get("band_swallowed"))) - int(bool(a.get("band_swallowed")))
                do = int(bool(b.get("orphans"))) - int(bool(a.get("orphans")))
                if dh or da or db or do:
                    moved.append((dh, da, db, do, insurer, os.path.basename(p)))
            gained = sum(1 for m in moved if m[0] > 0)
            lost = sum(1 for m in moved if m[0] < 0)
            print(f"   {la} -> {lb}: {len(moved)} sheets moved; headers +{gained} -{lost}; "
                  f"answers +{sum(m[1] for m in moved if m[1] > 0)} {sum(m[1] for m in moved if m[1] < 0)}; "
                  f"bands swallowed +{sum(1 for m in moved if m[2] > 0)} -{sum(1 for m in moved if m[2] < 0)}; "
                  f"orphans +{sum(1 for m in moved if m[3] > 0)} -{sum(1 for m in moved if m[3] < 0)}")
            for dh, da, db, do, insurer, name in sorted(moved):
                print(f"      header {dh:+d}  answers {da:+d}  band swallowed {db:+d}  orphans {do:+d}   {insurer} / {name[:64]}")
    if missing:
        print("missing from a cache:", dict(missing))


if __name__ == "__main__":
    main()
