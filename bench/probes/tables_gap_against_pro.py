import collections, json, os, sys
ours_dir, pro_dir = sys.argv[1], sys.argv[2]
scans = {l.split("\t")[0].strip() for l in open("bench/gpu/pages.txt", encoding="utf-8") if l.strip()}
held = {l.strip() for l in open("bench/holdout.txt", encoding="utf-8") if l.strip() and not l.startswith("#")}
def failed(path):
    out = {}
    for line in open(path, encoding="utf-8"):
        if line.strip():
            t = json.loads(line)
            if t.get("type") == "table":
                out[(t["pdf"], t.get("id"))] = t
    return out
ours, pro = failed(os.path.join(ours_dir, "failed_tests.jsonl")), failed(os.path.join(pro_dir, "failed_tests.jsonl"))
def is_held(pdf):
    return pdf in held or pdf[:-4] in held or os.path.basename(pdf) in held or os.path.basename(pdf)[:-4] in held
only = [k for k in ours if k not in pro and k[0][:-4] not in scans]
t_pages = collections.Counter(k[0] for k in only if not is_held(k[0]))
h = [k for k in only if is_held(k[0])]
print("digital checks we fail and Pro passes: %d, of which on held-out pages (counted, not listed): %d on %d pages" % (len(only), len(h), len({k[0] for k in h})))
print("tuned-on: %d checks on %d pages" % (sum(t_pages.values()), len(t_pages)))
json.dump({p: [ours[k] for k in only if k[0] == p] for p in t_pages}, open(sys.argv[3], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for p, n in t_pages.most_common():
    print("   %d  %s" % (n, p))
