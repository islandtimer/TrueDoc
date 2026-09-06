"""List control characters (other than line endings) in the given text files, with context.

usage: python bench/tools/scan_ctrl.py [--fix] <file> ...
A carriage return that is part of a CRLF line ending is not reported or touched.
With --fix, each control character that a mangled backslash escape would have produced is
turned back into the backslash sequence (form feed -> \\f, backspace -> \\b, bell -> \\a,
tab -> \\t, lone carriage return -> \\r, vertical tab -> \\v). Newline mangles cannot be
undone automatically; look for lines starting with "eq", "abla", "otin", "ot " afterwards.

Why this exists: writing documentation through a shell heredoc turns "\\f", "\\t", "\\b", "\\a",
"\\r", "\\v" and "\\n" inside LaTeX into control characters. Edit files with a tool that writes
bytes verbatim, or with log_update.py, and run this scan over docs/*.md before committing.
"""
import sys

NAMES = {"\f": "\\f", "\b": "\\b", "\a": "\\a", "\t": "\\t", "\r": "\\r", "\v": "\\v", "\0": "\\0"}


def main():
    fix = "--fix" in sys.argv
    for p in [a for a in sys.argv[1:] if not a.startswith("--")]:
        s = open(p, encoding="utf-8", newline="").read()
        crlf = "\r\n" in s
        body = s.replace("\r\n", "\n") if crlf else s
        lines = body.split("\n")
        hits = 0
        for i, l in enumerate(lines):
            for j, c in enumerate(l):
                if ord(c) < 32:
                    hits += 1
                    if not fix:
                        print("%s:%d col %d: %r context %r" % (p, i + 1, j + 1, NAMES.get(c, hex(ord(c))), l[max(0, j - 25):j + 25]))
        if fix and hits:
            out = body
            for c, rep in NAMES.items():
                out = out.replace(c, rep)
            if crlf:
                out = out.replace("\n", "\r\n")
            open(p, "w", encoding="utf-8", newline="").write(out)
        print(p, hits, "control characters", "(fixed)" if fix and hits else "")


if __name__ == "__main__":
    main()
