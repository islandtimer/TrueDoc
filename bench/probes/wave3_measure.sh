#!/bin/bash
# Score the two vision merges built from run 54's pages, then sort the blank pages. One heavy job at a time.
cd "$(dirname "$0")/../.." || exit 1
PY=.venv/Scripts/python
ST=bench/out/launch/wave3_status.txt
SP="${SCRATCH:?set SCRATCH to the folder holding partial_census.py (a session scratchpad, 6 September)}"
for C in truedoc53_vlm truedoc53_vlmall; do
  D="bench/runs/${C}-$(date +%Y%m%d-%H%M%S)"; mkdir -p "$D"
  echo "$(date +%H:%M) scoring $C into $D" >> "$ST"
  $PY -c "import sys; from truedoc.bench.olmocr import score_candidate; score_candidate(sys.argv[1], sys.argv[2])" "$C" "$D" > "bench/out/launch/score_${C}.log" 2>&1
  $PY bench/holdout_score.py "$D" >> "bench/out/launch/score_${C}.log" 2>&1
  echo "$(date +%H:%M) $C scored: $(grep -a -o 'overall [0-9.]*' bench/out/launch/score_${C}.log | head -1) $(grep -a 'held-out' bench/out/launch/score_${C}.log | tail -1)" >> "$ST"
done
echo "$(date +%H:%M) sorting the blank pages of truedoc53" >> "$ST"
$PY "$SP/partial_census.py" truedoc53 "$SP/partial_census_out.txt" > "$SP/partial_census.log" 2>&1
echo "$(date +%H:%M) blank-page sort done (rc=$?)" >> "$ST"
