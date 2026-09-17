"""Place a bake-off model's readings as benchmark candidates (run from the repository root).

    python bench/gpu/place_bakeoff.py infinity <folder> <name>
    python bench/gpu/place_bakeoff.py dots <folder> <name>

`infinity`: <folder> is one page set as run_bakeoff.sh leaves it - `inference.jsonl` holding the
model's raw markdown, a line per PDF, beside `<category>/<stem>_pg1_repeat1.md` holding the same
reading after the authors' post-processing, which is keyed on the benchmark's category names.
Two candidates are written, `<name>_raw` and `<name>_post`, because they answer different
questions: the first is what a product would be handed, the second is what the leaderboard scored.

`dots`: <folder> holds `<category>/<stem>/<stem>*.md` and `<stem>*_nohf.md` as the authors' parser
writes them. Two candidates again, `<name>_hf` (headers and footers kept) and `<name>_nohf`.

Every candidate is bench_data/<candidate>/<category>/<stem>_pg1_repeat1.md, the form the scorer,
merge_by_list.py and the converter's `file:` provider all read. Counts are printed per category so
a short folder is seen here and not as a score.
"""
import glob
import json
import os
import re
import sys
from collections import Counter

BENCH = os.path.join("bench", "data", "olmocr-bench", "bench_data")


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def write(candidate, category, stem, text, counts):
    folder = os.path.join(BENCH, candidate, category)
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, stem + "_pg1_repeat1.md"), "w", encoding="utf-8") as f:
        f.write(text)
    counts[(candidate, category, "empty" if not text.strip() else "read")] += 1


_FURNITURE = ("figure", "header", "footer")
_TEXT_FIELD = re.compile(r'"category":\s*"([^"]*)",\s*"text":\s*"((?:[^"\\]|\\.)*)"')


def layout_text(markdown, counts, candidate):
    """The authors' client hands back the model's layout JSON untouched when it cannot make
    markdown of it: a picture with nothing to read (one "figure" item, no text), a page of
    running heads alone, or a reading cut off before its closing bracket. Those are not the
    page's words. Keep the text of every item that is not a figure or a running head, which is
    what their own conversion keeps; from a cut-off reading, keep what can still be parsed."""
    text = markdown.strip()
    if not text.startswith("[{"):
        return markdown
    try:
        items = [(it.get("category", ""), it.get("text") or "") for it in json.loads(text)]
        counts[(candidate, "(layout JSON)", "fixed")] += 1
    except ValueError:
        items = [(c, json.loads('"%s"' % t)) for c, t in _TEXT_FIELD.findall(text)]
        counts[(candidate, "(layout JSON, cut off)", "fixed")] += 1
    return "\n\n".join(t for c, t in items if c not in _FURNITURE and t.strip())


def infinity(folder, name, counts):
    for line in read(os.path.join(folder, "inference.jsonl")).splitlines():
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        pdf = rec["pdf"].replace("\\", "/")
        category, stem = pdf.split("/")[-2], os.path.splitext(os.path.basename(pdf))[0]
        write(name + "_raw", category, stem, layout_text(rec.get("markdown") or "", counts, name + "_raw"), counts)
    for path in glob.glob(os.path.join(folder, "*", "*_pg1_repeat1.md")):
        category = os.path.basename(os.path.dirname(path))
        stem = os.path.basename(path)[: -len("_pg1_repeat1.md")]
        write(name + "_post", category, stem, read(path), counts)


def dots(folder, name, counts):
    for page_dir in glob.glob(os.path.join(folder, "*", "*")):
        if not os.path.isdir(page_dir):
            continue
        category, stem = os.path.basename(os.path.dirname(page_dir)), os.path.basename(page_dir)
        nohf = sorted(glob.glob(os.path.join(page_dir, "*_nohf.md")))
        full = sorted(p for p in glob.glob(os.path.join(page_dir, "*.md")) if not p.endswith("_nohf.md"))
        for suffix, paths in (("_nohf", nohf), ("_hf", full)):
            if paths:  # one-page PDFs: the first page's file is the page
                write(name + suffix, category, stem, read(paths[0]), counts)


if __name__ == "__main__":
    kind, folder, name = sys.argv[1:4]
    counts = Counter()
    {"infinity": infinity, "dots": dots}[kind](folder, name, counts)
    for (candidate, category, state), n in sorted(counts.items()):
        print("%-24s %-18s %-5s %d" % (candidate, category, state, n))
