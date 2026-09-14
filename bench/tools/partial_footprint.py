"""Pages converted so far whose markdown differs between a candidate pool label and its base, subset by subset.

For reading a candidate's changed pages while its pool is still converting, or after it was stopped: only pages both
folders already hold are compared. Each subset takes the first base label that has a folder for it, so a candidate
can be set against bases converted in separate pools (four subsets in one, three in another).

usage (repo root): partial_footprint.py <candidate label> <base label> [<base label> ...]
    e.g. partial_footprint.py pfoot1 pguard pbase
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
AB = os.path.join(REPO, "bench", "out", "ab")


def pages(folder: str) -> set:
    return {n for n in os.listdir(folder) if n.endswith(".md") and os.path.getsize(os.path.join(folder, n)) > 0}


def main() -> None:
    cand, bases = sys.argv[1], sys.argv[2:]
    for name in sorted(os.listdir(AB)):
        if not name.startswith(cand + "_") or not os.path.isdir(os.path.join(AB, name)):
            continue
        subset = name[len(cand) + 1:]
        base = next((b for b in bases if os.path.isdir(os.path.join(AB, f"{b}_{subset}"))), None)
        if base is None:
            print(f"{subset}: no base folder among {bases}")
            continue
        a_dir, b_dir = os.path.join(AB, f"{base}_{subset}"), os.path.join(AB, name)
        done, have = pages(b_dir), pages(a_dir)
        both = sorted(done & have)
        changed = []
        for n in both:
            with open(os.path.join(a_dir, n), "rb") as fa, open(os.path.join(b_dir, n), "rb") as fb:
                if fa.read() != fb.read():
                    changed.append(n)
        print(f"{subset}: {len(done)} converted, {len(both)} comparable against {base}, {len(changed)} changed")
        for n in changed:
            print("   ", n)


if __name__ == "__main__":
    main()
