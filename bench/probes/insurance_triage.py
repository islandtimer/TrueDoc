"""Why each insurance check still fails, by the dossier's own computed reason.

Imports bench/tools/insurance_dossier.py and, for every check that fails on the converted pages, prints the group its
`evidence` puts it in (missing text, characters apart, no table, cell nearly right, wrong neighbour, ordering blocked),
the verdict, and the start of the evidence as plain text.

On 15 Sept, at 212 of 229 (inside wt_lig31, 65336b3's reader), the seventeen failures fell into celltext 6, notable 5,
order 3, chars 2 and neighbour 1. Read against the page images: eight are reading faults, seven of them text that wraps
inside a table or card read as a new row; eight turn on whether a table cell is everything drawn inside its box; and
one, QBE's page 16, the rule grid mends.

usage (inside a tree whose bench/out/insurance_set holds converted/ and checks_a/): insurance_triage.py <bench/tools>
"""
import glob
import html
import json
import os
import re
import sys

tools = sys.argv[1]
sys.argv = [sys.argv[0]]
sys.path.insert(0, tools)
import insurance_dossier as d  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
TAG = re.compile("<[^>]+>")


def plain(text):
    return " ".join(html.unescape(TAG.sub(" ", text)).split())


def main():
    names = sorted(os.path.splitext(os.path.basename(p))[0]
                   for p in glob.glob(os.path.join(d.OUT, "checks_a", "*.jsonl")))
    by_group = {}
    for name in names:
        with open(os.path.join(d.OUT, "converted", name + ".md"), encoding="utf-8") as fh:
            md = d.unescape(fh.read())
        norm = d.normalize_text(md)
        tables = d.parse_markdown_tables(md) + d.parse_html_tables(md)
        with open(os.path.join(d.OUT, "checks_a", name + ".jsonl"), encoding="utf-8") as fh:
            checks = [json.loads(line) for line in fh if line.strip()]
        for i, raw in enumerate(checks):
            item = dict(raw)
            item.setdefault("id", f"{name}_{i}")
            try:
                good, _ = d.load_single_test(item).run(md)
            except Exception:
                good = False
            if good:
                continue
            group, verdict, body = d.evidence(raw, md, norm, tables)
            by_group.setdefault(group, []).append((name, raw, plain(verdict), plain(body)))
    for group, rows in sorted(by_group.items(), key=lambda kv: -len(kv[1])):
        print(f"== {group}: {len(rows)}")
        for name, raw, verdict, body in rows:
            what = raw.get("cell") or raw.get("text") or raw.get("before") or ""
            print(f"   {name[:44]} [{raw.get('type')}] {str(what)[:80]}")
            print(f"      {verdict[:170]}")
            print(f"      {body[:320]}")


if __name__ == "__main__":
    main()
