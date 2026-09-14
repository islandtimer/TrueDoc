"""Convert named tuned-on Key Facts Sheets with the working tree and grade them against a cache of committed code.

A few minutes' look at the sheets a rule was written for, before the whole oracle is spent on it. Sheets are named
by a fragment of their cache name (as the answer census prints them); a held-out sheet is refused, never converted.

usage (repo root): kfs_quick.py <baseline cache dir> <fragment> [<fragment> ...]
"""
import io
import os
import sys

sys.path.insert(0, os.path.join("bench", "tools"))
from kfs_grade import cache_path, grade, held_out, sheets  # noqa: E402
from truedoc.pipeline import ConvertOptions, convert  # noqa: E402


def whole(g: dict) -> bool:
    return bool(g.get("found") and g["header_whole"] and not g["header_leaks"])


def main() -> None:
    baseline, fragments = sys.argv[1], sys.argv[2:]
    by_cache = {os.path.basename(cache_path(p)): p for _, p in sheets()}
    for fragment in fragments:
        matches = [n for n in sorted(by_cache) if fragment in n]
        if not matches:
            print(f"{fragment[:48]:48s} no such sheet")
            continue
        for name in matches:
            path = by_cache[name]
            if held_out(path):
                print(f"{name[:48]:48s} held out - not looked at")
                continue
            now = grade(convert(path, ConvertOptions(frontmatter=False, pages=[1, 2])))
            before = grade(io.open(os.path.join(baseline, name), encoding="utf-8").read())
            print(f"{name[:48]:48s} answers {before.get('answers_attached', 0):2d} -> {now.get('answers_attached', 0):2d}"
                  f"   rows {before.get('events_in_rows', 0):2d} -> {now.get('events_in_rows', 0):2d} of {now.get('events', 0)}"
                  f"   header {whole(before)} -> {whole(now)}"
                  f"   band swallowed {before.get('band_swallowed')} -> {now.get('band_swallowed')}", flush=True)


if __name__ == "__main__":
    main()
