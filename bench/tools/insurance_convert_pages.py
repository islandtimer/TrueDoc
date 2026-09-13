"""Convert each page of the insurance test set on its own, so a check can be scored against it.

The checks are written per page, so the conversion has to be per page too. Also gives the dossier the
thing a person needs beside the image: what the converter actually produced.

usage (repo root): insurance_convert_pages.py [workers]
"""
import concurrent.futures
import json
import os
import sys

OUT = os.path.join("bench", "out", "insurance_set")


def one(entry: dict) -> tuple:
    from truedoc.pipeline import ConvertOptions, convert

    out_path = os.path.join(OUT, "converted", entry["name"] + ".md")
    if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
        return entry["name"], "already converted"
    try:
        md = convert(entry["pdf"], ConvertOptions(frontmatter=False, pages=[entry["page"]]))
    except Exception as exc:
        return entry["name"], "FAILED: " + repr(exc)[:110]
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(md)
    return entry["name"], f"{len(md.split())} words"


def main() -> None:
    workers = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    pages = json.load(open(os.path.join(OUT, "manifest.json"), encoding="utf-8"))["pages"]
    done = 0
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
        for name, note in pool.map(one, pages):
            done += 1
            print(f"{done:3d}/{len(pages)}  {name[:60]:62s} {note}", flush=True)
    print("done", flush=True)


if __name__ == "__main__":
    main()
