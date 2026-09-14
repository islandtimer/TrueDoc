"""Fill @@KEY@@ placeholders in drafted write-ups from a JSON file of values, and refuse to leave any behind.

Numbers copied into prose by hand get mistyped, and a write-up carrying a stray @@ into the docs or a commit
message is worse than none. Each draft is written to `<draft>_filled.txt` beside it; the exit status is
non-zero, naming what is left, if any placeholder survives in any of them.

usage: fill_placeholders.py <values.json> <draft.txt> [<draft.txt> ...]
"""
import io
import json
import os
import re
import sys


def main() -> None:
    values = json.load(io.open(sys.argv[1], encoding="utf-8"))
    incomplete = False
    for draft in sys.argv[2:]:
        body = io.open(draft, encoding="utf-8").read()
        for key, value in values.items():
            body = body.replace("@@" + key + "@@", value)
        left = sorted(set(re.findall("@@[A-Z0-9_]+@@", body)))
        target = draft[:-4] + "_filled.txt"
        io.open(target, "w", encoding="utf-8").write(body)
        print(f"{os.path.basename(target)}: " + ("LEFT " + ", ".join(left) if left else "complete"))
        incomplete = incomplete or bool(left)
    sys.exit(1 if incomplete else 0)


if __name__ == "__main__":
    main()
