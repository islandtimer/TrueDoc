"""How much text can a picture region physically hold, and how much did each reader say it held?

18 September 2026. Asked TrueDoc's picture-text question, Infinity-Parser2-Flash turned two of 92
crops into thousands of words that are not on the page: an 1,800-row table of numbers for a scatter
plot 328 points tall, and one line repeated 4,095 times for a figure 270 points tall. Neither can be
true of a region that size, whatever is in it: print smaller than about 4 points cannot be read, so
a region H points tall holds at most H/4 lines set one above another, and a region of W x H points
holds at most about W*H/8 characters (4-point type is about 2 points a character wide).

Before any rule is written, this measures the population it would act on: every recorded reading
of every crop, from every reader we have, against both bounds - so the threshold is chosen from
where real transcriptions sit, not from the two that prompted it.

usage (repo root): region_capacity.py [<candidate folder> ...]
"""
import json
import os
import re
import sys

BENCH = os.path.join("bench", "data", "olmocr-bench", "bench_data")
MIN_TYPE = 4.0          # points: smaller print than this is not legible, so nothing is set in it


def answer_text(text):
    """The reading as the pipeline would use it: fences and YAML block off, `none` answers empty."""
    t = re.sub(r"\A---\s*\n.*?\n---\s*\n", "", text, flags=re.S).strip()
    t = re.sub(r"^```[a-z]*\s*|\s*```$", "", t).strip()
    first = t.split("\n\n", 1)[0].strip()
    if re.match(r"^(decorative|decoration|none|n/a)\b", first, re.I):
        return ""
    return t


def lines_of(text):
    """Lines that hold something to read: a markdown table's rule line and an HTML tag alone are not print."""
    out = []
    for line in re.sub(r"<[^>]+>", "\n", text).splitlines():
        line = line.strip()
        if line and not re.fullmatch(r"[|\s:-]+", line):
            out.append(line)
    return out


def main(folders):
    with open(os.path.join("bench", "gpu", "crops_failing", "manifest.json"), encoding="utf-8") as f:
        manifest = json.load(f)
    rows = []
    for folder in folders:
        name = os.path.basename(folder.rstrip("/\\"))
        for e in manifest:
            path = os.path.join(folder, e["crop"][:-4] + "_pg1_repeat1.md")
            if not os.path.exists(path):
                continue
            with open(path, encoding="utf-8") as f:
                text = answer_text(f.read())
            if not text:
                continue
            x0, y0, x1, y1 = e["bbox"]
            w, h = x1 - x0 + 4, y1 - y0 + 4                       # the crop is the image box and 2 points each side
            lines = lines_of(text)
            chars = sum(len(re.sub(r"[|\s]", "", l)) for l in lines)
            line_cap = max(w, h) / MIN_TYPE                        # a table set sideways runs along the width
            char_cap = w * h / (MIN_TYPE * MIN_TYPE / 2)
            rows.append((len(lines) / line_cap, chars / char_cap, name, e["crop"], round(w), round(h), len(lines), chars))
    print("%d readings that hold text, from %d reader(s)\n" % (len(rows), len(folders)))
    for title, key in (("lines written / lines the region can hold", 0), ("characters written / characters the region can hold", 1)):
        rows.sort(key=lambda r: -r[key])
        print(title)
        for r in rows[:8]:
            print("  %6.2f  %-22s %-58s %4d x %-4d pt  %5d lines %6d chars" % (r[key], r[2], r[3][:58], r[4], r[5], r[6], r[7]))
        values = sorted(r[key] for r in rows)
        print("  ... median %.2f, 90th percentile %.2f, above 1.0: %d of %d\n" % (
            values[len(values) // 2], values[int(len(values) * 0.9)], sum(1 for v in values if v > 1.0), len(values)))


if __name__ == "__main__":
    main(sys.argv[1:] or [os.path.join(BENCH, n) for n in ("olmocr2c", "inf2pro_custom_raw", "inf2flash_custom_raw")])
