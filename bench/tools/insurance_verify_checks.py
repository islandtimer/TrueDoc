"""Is each check's quoted text really on the page?

A check that misquotes the page by one character is worse than no check: it fails for ever and looks
like a converter defect. A person eyeballing two hundred quotations against page images will not catch
that; a second independent reading will.

So each page is read again by the frontier reader - a different call, not the converter's output - and
every check's quoted text is looked for in that reading. This can only ever *propose*: a check the
reading does not contain may be a bad check, or may be a passage that reading missed. It is evidence for
the person deciding, never a clearance.

usage (repo root): insurance_verify_checks.py [workers]
"""
import concurrent.futures
import glob
import json
import os
import sys

from rapidfuzz import fuzz

OUT = os.path.join("bench", "out", "insurance_set")
READ = os.path.join(OUT, "independent_read")


def read_one(entry: dict) -> tuple:
    out_path = os.path.join(READ, entry["name"] + ".md")
    if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
        return entry["name"], "already read"
    from truedoc.vision import make_provider

    try:
        text = make_provider("anthropic").read_page(entry["pdf"], entry["page"]) or ""
    except Exception as exc:
        return entry["name"], "FAILED: " + repr(exc)[:110]
    os.makedirs(READ, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return entry["name"], f"{len(text.split())} words"


def flatten(text: str) -> str:
    return " ".join(text.split()).lower()


def verify(name: str) -> list:
    path = os.path.join(READ, name + ".md")
    hay = flatten(open(path, encoding="utf-8").read()) if os.path.exists(path) else ""
    rows = []
    for line in open(os.path.join(OUT, "checks_a", name + ".jsonl"), encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        check = json.loads(line)
        quoted = [check.get(k) for k in ("text", "before", "after", "cell", "left", "right", "up",
                                         "down", "top_heading", "left_heading") if check.get(k)]
        worst = 100.0
        for q in quoted:
            needle = flatten(str(q))
            if not needle or not hay:
                worst = 0.0
                continue
            score = 100.0 if needle in hay else fuzz.partial_ratio(needle, hay)
            worst = min(worst, score)
        rows.append({"check": check, "found": round(worst, 1)})
    return rows


def main() -> None:
    workers = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    pages = json.load(open(os.path.join(OUT, "manifest.json"), encoding="utf-8"))["pages"]
    have = {os.path.splitext(os.path.basename(p))[0] for p in glob.glob(os.path.join(OUT, "checks_a", "*.jsonl"))}
    todo = [p for p in pages if p["name"] in have]
    print(f"{len(todo)} pages have checks; reading each one independently", flush=True)
    os.makedirs(READ, exist_ok=True)
    done = 0
    # Processes, not threads. The first version used threads and every page came back empty:
    # the renderer underneath keeps global state, fails silently in a thread, and the provider
    # turns that into None. The same lesson as the API run earlier today, learned twice.
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
        for name, note in pool.map(read_one, todo):
            done += 1
            print(f"{done:3d}/{len(todo)}  {name[:56]:58s} {note}", flush=True)

    out = {}
    exact = near = missing = 0
    for entry in todo:
        rows = verify(entry["name"])
        out[entry["name"]] = rows
        for r in rows:
            if r["found"] >= 99:
                exact += 1
            elif r["found"] >= 85:
                near += 1
            else:
                missing += 1
    with open(os.path.join(OUT, "verification.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)
    total = exact + near + missing
    print()
    print(f"{total} checks against an independent reading of the same page:")
    print(f"   {exact:4d}  quoted text found word for word")
    print(f"   {near:4d}  found but not exactly - worth a look")
    print(f"   {missing:4d}  not found at all - the check or the reading is wrong")


if __name__ == "__main__":
    main()
