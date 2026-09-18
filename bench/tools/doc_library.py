"""Where the owner's document library is.

The library - a few hundred Australian insurers' product disclosure statements and Key Facts
Sheets, publicly available documents, about a gigabyte - is not in the repository. Its folder
holds <insurer>/<product line>/<file>.pdf. Tools that read it find the folder through the
environment variable TRUEDOC_LIBRARY, or through the git-ignored file bench/library_path.txt
holding the path on one line, and stop with a plain message when neither is set.

Files that are committed name a library document by its path *relative* to that folder
(`relative`), so the repository carries no machine's folders; `absolute` puts the root back.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
PATH_FILE = os.path.join(REPO, "bench", "library_path.txt")


def root() -> str:
    path = os.environ.get("TRUEDOC_LIBRARY", "").strip()
    if not path and os.path.exists(PATH_FILE):
        with open(PATH_FILE, encoding="utf-8") as f:
            path = f.read().strip()
    if not path or not os.path.isdir(path):
        raise SystemExit(
            "the document library was not found: set TRUEDOC_LIBRARY, or write its path on one line in "
            "bench/library_path.txt (the folder holding <insurer>/<product line>/<file>.pdf)"
        )
    return path.replace("\\", "/").rstrip("/")


def relative(path: str) -> str:
    """A library document's path without the machine's part, for files that are committed."""
    p = path.replace("\\", "/")
    r = root()
    if p.startswith(r + "/"):
        return p[len(r) + 1:]
    return p


def absolute(rel: str) -> str:
    """The path on this machine of a document named relative to the library."""
    p = rel.replace("\\", "/")
    if os.path.isabs(p) or (len(p) > 1 and p[1] == ":"):
        return p
    return root() + "/" + p
