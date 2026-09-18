"""What the second look in `_refine_segments` does with every x range overlapping a window: skipped, placed, dropped.

CGU's contents sheets leave "Actions of the sea No" whole, and no refusal is logged for the gap between the labels and
the answers. This runs the function's own source with four logging calls put in: a range skipped because a cut from
the first look already lies in it, where `place` settles (with the words straddling each earlier try), the phrase guard
(`runs_across_columns`) when it refuses, and the vote. Nothing is re-implemented.

usage (repo root): place_probe.py <cache-name fragment> <x lo> <x hi>   (ranges overlapping [lo, hi])
"""
import inspect
import os
import sys

sys.path.insert(0, os.path.join("bench", "tools"))
from kfs_grade import cache_path, held_out, sheets  # noqa: E402
from truedoc.pipeline import ConvertOptions, first_pages, load_document  # noqa: E402
from truedoc.tables import aligned  # noqa: E402

NL = chr(10)
WINDOW = [0.0, 0.0]
SEEN: set = set()

SKIP_OLD = NL.join(["        if any(start - 1.0 <= c <= x + 1.0 for c in cuts):",
                    "            continue"])
SKIP_NEW = NL.join(["        if any(start - 1.0 <= c <= x + 1.0 for c in cuts):",
                    "            _log_skip(start, x, cuts)",
                    "            continue"])
PLACE_OLD = NL.join(["        for c in (x - 1.0, (start + x) / 2.0, start + 1.0):",
                     "            if not straddled(c):",
                     "                return c",
                     "        return None"])
PLACE_NEW = NL.join(["        for c in (x - 1.0, (start + x) / 2.0, start + 1.0):",
                     "            if not straddled(c):",
                     "                _log_place(start, x, c, all_words)",
                     "                return c",
                     "        return None"])
R1_OLD = NL.join(["        if divided and all(runs_across_columns(placed, size) for placed in divided):",
                  "            continue"])
R1_NEW = NL.join(["        if divided and all(runs_across_columns(placed, size) for placed in divided):",
                  "            _log_r1(start, x, c, divided)",
                  "            continue"])
VOTE_OLD = NL.join(["        if agree >= max(3, 0.6 * len(able)):",
                    "            cuts.append(c)"])
VOTE_NEW = NL.join(["        _log_vote(start, x, c, agree, len(able))",
                    "        if agree >= max(3, 0.6 * len(able)):",
                    "            cuts.append(c)"])


def _wanted(start: float, x: float) -> bool:
    return start <= WINDOW[1] and x >= WINDOW[0]


def _once(*key) -> bool:
    if key in SEEN:
        return False
    SEEN.add(key)
    return True


def _log_skip(start, x, cuts):
    if _wanted(start, x) and _once("skip", round(start, 1), round(x, 1)):
        inside = [c for c in cuts if start - 1.0 <= c <= x + 1.0]
        print(f"  range x {start:.1f}-{x:.1f}: skipped - the first look already cut it at " + ", ".join(f"{c:.1f}" for c in inside))


def _log_place(start, x, c, all_words):
    if not _wanted(start, x) or not _once("place", round(start, 1), round(x, 1), round(c, 1)):
        return
    print(f"  range x {start:.1f}-{x:.1f}: place settles at {c:.1f}")
    for tried in (x - 1.0, (start + x) / 2.0, start + 1.0):
        if abs(tried - c) < 0.01:
            break
        words = [w for w in all_words if w.bbox.x0 < tried - 1 and w.bbox.x1 > tried + 1]
        print(f"      tried {tried:.1f}, straddled by " + ", ".join(f"{w.text!r}[{w.bbox.x0:.1f}-{w.bbox.x1:.1f}]" for w in words[:5]))


def _log_r1(start, x, c, divided):
    if not _wanted(start, x) or not _once("r1", round(start, 1), round(x, 1), round(c, 1)):
        return
    print(f"  range x {start:.1f}-{x:.1f}: the cut at {c:.1f} is dropped - every segment it divides crosses on a word space")
    for placed in divided[:4]:
        print("      " + " ".join(f"{w.text}{'>' if side else ''}" for w, side in placed)[:150])


def _log_vote(start, x, c, agree, able):
    if _wanted(start, x) and _once("vote", round(start, 1), round(x, 1), round(c, 1)):
        print(f"  range x {start:.1f}-{x:.1f}: the cut at {c:.1f} - {agree} of {able} able rows leave a gap there")


SRC = inspect.getsource(aligned._refine_segments)
for old in (SKIP_OLD, PLACE_OLD, R1_OLD, VOTE_OLD):
    assert SRC.count(old) == 1, "the source is not shaped as the probe expects: " + old.splitlines()[0]
NS = dict(vars(aligned))
NS.update(_log_skip=_log_skip, _log_place=_log_place, _log_r1=_log_r1, _log_vote=_log_vote)
exec(SRC.replace(SKIP_OLD, SKIP_NEW).replace(PLACE_OLD, PLACE_NEW).replace(R1_OLD, R1_NEW).replace(VOTE_OLD, VOTE_NEW), NS)
aligned._refine_segments = NS["_refine_segments"]


def main() -> None:
    fragment, WINDOW[0], WINDOW[1] = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
    by_cache = {os.path.basename(cache_path(p)): p for _, p in sheets()}
    name = next(n for n in sorted(by_cache) if fragment in n)
    path = by_cache[name]
    if held_out(path):
        print(f"{name}: held out, not looked at")
        return
    print(f"===== {name}", flush=True)
    load_document(path, ConvertOptions(frontmatter=False, pages=first_pages(path, 2)))


if __name__ == "__main__":
    main()
