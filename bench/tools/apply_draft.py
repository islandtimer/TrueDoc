"""Replace one passage in a source file with a drafted one, keeping the file's own line endings.

`bench/tools/log_update.py` writes in text mode, which on Windows turns every line ending into CRLF: right
for the docs, which are CRLF already, and wrong for an LF source file such as `truedoc/pipeline.py`, which
would change on every line. This reads and writes bytes-faithfully, gives the drafts the file's own
ending, and refuses unless the old passage occurs exactly once - so a `--check` run is a dry run.

usage (repo root): apply_draft.py <file> <old passage file> <new passage file> [--check]
"""
import io
import sys


def main() -> None:
    target, old_path, new_path = sys.argv[1:4]
    check = "--check" in sys.argv[4:]
    text = io.open(target, encoding="utf-8", newline="").read()
    crlf = chr(13) + chr(10)
    ending = crlf if crlf in text else chr(10)
    old = io.open(old_path, encoding="utf-8").read().strip(chr(10)).replace(chr(10), ending)
    new = io.open(new_path, encoding="utf-8").read().strip(chr(10)).replace(chr(10), ending)
    n = text.count(old)
    if n != 1:
        raise SystemExit(f"{target}: the old passage occurs {n} times; nothing written")
    if check:
        print(f"{target}: one match ({'CRLF' if ending == crlf else 'LF'}); not written (--check)")
        return
    io.open(target, "w", encoding="utf-8", newline="").write(text.replace(old, new))
    print(f"{target}: replaced ({'CRLF' if ending == crlf else 'LF'})")


if __name__ == "__main__":
    main()
