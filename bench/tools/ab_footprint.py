"""Pages whose markdown differs between two pooled A/B labels, listed for reading against their page images.

A score says whether a check moved; this says whether the output moved. Every page it names is unreviewed until
someone has looked at it.

usage (repo root): ab_footprint.py <base label> <label>      compares bench/out/ab/<label>_<subset> with <base>_<subset>
"""
import io
import os
import sys


def read(path: str) -> str | None:
    return io.open(path, encoding="utf-8").read() if os.path.exists(path) else None


def main() -> None:
    base, label = sys.argv[1], sys.argv[2]
    total = 0
    for subset in ("tables", "multi_column", "long_tiny_text"):
        before = os.path.join("bench", "out", "ab", f"{base}_{subset}")
        after = os.path.join("bench", "out", "ab", f"{label}_{subset}")
        names = sorted(n for n in os.listdir(after) if n.endswith(".md"))
        moved = [n for n in names if read(os.path.join(before, n)) != read(os.path.join(after, n))]
        print(f"{subset}: {len(moved)} of {len(names)} pages differ from {base}")
        for n in moved:
            print(f"   {n[:64]}")
        total += len(moved)
    print(f"FOOTPRINT {total}")


if __name__ == "__main__":
    main()
