"""Replace one passage in a text file, with old and new text read from files.

usage: python bench/tools/log_update.py <file to edit> <old text file> <new text file>

The two text files hold the exact old and new passages (UTF-8), so backslashes never pass through
a shell. The old passage must occur exactly once. Written for docs/PROGRESS_LOG.md, whose entries
carry LaTeX; see scan_ctrl.py for why a shell heredoc is not safe for that.
"""
import sys

p = sys.argv[1]
old = open(sys.argv[2], encoding="utf-8").read().strip("\n")
new = open(sys.argv[3], encoding="utf-8").read().strip("\n")
s = open(p, encoding="utf-8").read()
n = s.count(old)
if n != 1:
    raise SystemExit("old text occurs %d times" % n)
open(p, "w", encoding="utf-8").write(s.replace(old, new))
print("replaced; control chars in new text:", sum(1 for c in new if ord(c) < 32))
