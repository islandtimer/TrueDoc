"""Does the corrected census really see a broken formula? Builds a two-formula page under a throwaway
candidate folder - one sound, one KaTeX refuses - and runs the census over it. Anything but "1 will not
render" means the census is still blind.
usage (repo root): census_selftest.py"""
import os
import shutil
import subprocess
import sys

B = os.path.join("bench", "data", "olmocr-bench", "bench_data")
cand = "censusselftest"
folder = os.path.join(B, cand, "probe")
os.makedirs(folder, exist_ok=True)
page = os.path.join(folder, "selftest.md")
with open(page, "w", encoding="utf-8") as fh:
    fh.write("A sound one: \\(\\frac{a}{b} + \\sqrt{2}\\)\n\n")
    fh.write("A broken one: \\(\\text{&c.} = x\\)\n")

here = os.path.dirname(os.path.abspath(__file__))
out = subprocess.run([sys.executable, os.path.join(here, "formula_render_census.py"), cand],
                     capture_output=True, text=True)
print(out.stdout)
if out.returncode:
    print("stderr:", out.stderr[-500:])
shutil.rmtree(os.path.join(B, cand), ignore_errors=True)
