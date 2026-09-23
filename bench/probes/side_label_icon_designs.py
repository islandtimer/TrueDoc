"""Which documents carry each fault, grouped into designs, so one design sold under several brands counts once.

F2: documents with a side label written after its first line; a design is the set of label wordings with their
column's left edge and gutter (rounded). F3: documents with a repeated mark-sized placeholder; two documents share a
design when they share two repeated icons (same picture and colour). Held-out documents are counted, never named.

usage: side_label_icon_designs.py <convert.jsonl> [--list]   (a side_label_icon_census.py conversion)
"""
import collections
import os
import json
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import side_label_icon_census as c

rows = [r for r in c._rows(sys.argv[1]) if "blocks" in r]
listing = "--list" in sys.argv

# ---------------------------------------------------------------------------------------------------------- F2
per_doc = collections.defaultdict(lambda: {"after": 0, "separated": 0, "right": 0, "inner": 0, "pages": set(), "fault_pages": set(),
                                           "words": collections.Counter(), "x0": collections.Counter(), "insurer": "", "held": False})
for r in rows:
    for x in c.label_outcomes(r):
        if x["purity"] < c.PURITY:
            continue
        d = per_doc[r["doc"]]
        d[x["outcome"]] += 1
        d["pages"].add(r["page"])
        d["insurer"], d["held"] = r["insurer"], r["held_out"]
        if x["outcome"] in ("after", "separated"):
            d["fault_pages"].add(r["page"])
        if not r["held_out"]:
            d["words"][x["label"].strip().lower()] += 1
        d["x0"][round(x["L"][0] / 3) * 3] += 1
faulty = {k: v for k, v in per_doc.items() if v["after"] or v["separated"]}
print("F2 documents with a side label: %d; with one written after its first line or apart from it: %d (held-out %d); insurers %d" % (
    len(per_doc), len(faulty), sum(v["held"] for v in faulty.values()), len({v["insurer"] for v in faulty.values()})))
tot = collections.Counter()
for v in per_doc.values():
    for k in ("after", "separated", "right", "inner"):
        tot[k] += v[k]
print("   labels: %s" % dict(tot))
designs = collections.defaultdict(list)
for k, v in faulty.items():
    if v["held"]:
        continue
    words = tuple(sorted(w for w, n in v["words"].most_common(4)))
    designs[(v["insurer"], words)].append(k)
print("   tuned-on fault documents by insurer and commonest label wordings (%d groups):" % len(designs))
for (ins, words), docs in sorted(designs.items(), key=lambda kv: -sum(len(faulty[d]["fault_pages"]) for d in kv[1])):
    fp = sum(len(faulty[d]["fault_pages"]) for d in docs)
    af = sum(faulty[d]["after"] for d in docs)
    sp = sum(faulty[d]["separated"] for d in docs)
    bf = sum(faulty[d]["right"] for d in docs)
    print("     %-26s docs %2d  fault pages %4d  labels after %4d / apart %4d / right %4d   %s" % (ins[:26], len(docs), fp, af, sp, bf, ", ".join(words)))
    if listing:
        for d in docs:
            print("         %s  pages %s" % (d, sorted(faulty[d]["fault_pages"])[:12]))

# ---------------------------------------------------------------------------------------------------------- F3
groups = collections.defaultdict(list)          # doc -> [[sig, count, where-counter, read-counter]]
meta = {}
for r in rows:
    meta[r["doc"]] = (r["insurer"], r["held_out"])
    for x in c.icon_placeholders(r):
        for g in groups[r["doc"]]:
            if c.same_icon(g[0], x["sig"]):
                break
        else:
            g = [x["sig"], 0, collections.Counter(), collections.Counter(), set()]
            groups[r["doc"]].append(g)
        g[1] += 1
        g[2][x["where"]] += 1
        g[3]["read" if x["read_as_mark"] else "unread"] += 1
        g[4].add(r["page"])
rep = {d: [g for g in gs if g[1] >= 3 and (g[2]["line-head"] + g[2]["table"]) >= 0.5 * g[1]] for d, gs in groups.items()}
rep = {d: gs for d, gs in rep.items() if gs}
print("\nF3 documents with an icon placeholder repeated 3+ times, at line heads or in tables: %d (held-out %d); insurers %d" % (
    len(rep), sum(meta[d][1] for d in rep), len({meta[d][0] for d in rep})))
n_ph = sum(g[1] for gs in rep.values() for g in gs)
pages = {(d, p) for d, gs in rep.items() for g in gs for p in g[4]}
print("   placeholders %d on %d pages" % (n_ph, len(pages)))
# designs: documents sharing two repeated icons
docs = sorted(rep)
parent = {d: d for d in docs}
def find(d):
    while parent[d] != d:
        parent[d] = parent[parent[d]]
        d = parent[d]
    return d
for i, a in enumerate(docs):
    for b in docs[i + 1:]:
        shared = sum(1 for ga in rep[a] if any(c.same_icon(ga[0], gb[0]) for gb in rep[b]))
        if shared >= 2 or (shared >= 1 and len(rep[a]) == 1 and len(rep[b]) == 1):
            parent[find(a)] = find(b)
clusters = collections.defaultdict(list)
for d in docs:
    clusters[find(d)].append(d)
print("   designs (documents sharing two repeated icons): %d" % len(clusters))
for root, ds in sorted(clusters.items(), key=lambda kv: -sum(g[1] for d in kv[1] for g in rep[d])):
    ins = collections.Counter(meta[d][0] for d in ds)
    held = sum(meta[d][1] for d in ds)
    n = sum(g[1] for d in ds for g in rep[d])
    wh = collections.Counter()
    rd = collections.Counter()
    for d in ds:
        for g in rep[d]:
            wh.update(g[2])
            rd.update(g[3])
    cols = collections.Counter(g[0].split("|")[-1] for d in ds for g in rep[d])
    print("     docs %3d (held-out %2d)  placeholders %5d  insurers %s  where %s  %s  colours %s" % (
        len(ds), held, n, dict(ins.most_common(6)), dict(wh), dict(rd), dict(cols)))
    if listing:
        for d in ds:
            if not meta[d][1]:
                print("         %s  pages %s" % (d, sorted({p for g in rep[d] for p in g[4]})[:10]))
