"""Page-by-page difference between two whole-category score files. usage: catdiff.py <A> <B>"""
import sys
def load(n):
    out = {}
    for l in open(f"bench/out/lost/{n}.txt", encoding="utf-8"):
        if l.startswith("TOTAL"): continue
        p, s = l.rsplit("  ", 1); a, b = s.strip().split("/"); out[p.strip()] = (int(a), int(b))
    return out
A, B = load(sys.argv[1]), load(sys.argv[2])
diff = sorted(((B[p][0] - A[p][0], p) for p in A if p in B))
lost = [(d, p) for d, p in diff if d < 0]; won = [(d, p) for d, p in diff if d > 0]
print(f"{sys.argv[2]} - {sys.argv[1]}: net {sum(d for d, _ in diff):+d} (B {sum(v[0] for v in B.values())} v A {sum(v[0] for v in A.values())}); "
      f"lost {sum(-d for d,_ in lost)} on {len(lost)} pages, won {sum(d for d,_ in won)} on {len(won)} pages")
for d, p in lost: print(f"  {d:+d}  {p.split('/')[1][:16]}  A {A[p][0]}/{A[p][1]} -> B {B[p][0]}")
for d, p in won: print(f"  {d:+d}  {p.split('/')[1][:16]}  A {A[p][0]}/{A[p][1]} -> B {B[p][0]}")
