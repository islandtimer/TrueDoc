#!/bin/bash
# Self-contained launcher: validate the code on disk, launch a benchmark candidate, wait for its
# conversion to finish, then score it and its held-out slice.
#
# usage: bash bench/tools/launch_run.sh <run number> <candidate name> [<sample2 minimum, default 56>]
# Extra arguments for the bench command come from the EXTRA environment variable, e.g.
#   EXTRA="--vision-endpoint file:bench/data/olmocr-bench/bench_data/olmocr2b --vision-pages-only"
#
# Writes launch<N>_status.txt, pytest<N>.log, run<N>.log and score<N>.log into bench/out/launch/
# (git-ignored). The status file's last line reads "run N scored" when everything is done.
# Never edit truedoc/ between the "validating" line and the "launched" line: the validation
# and the launch must see the same code.
N="$1"; CAND="$2"; S2_MIN="${3:-56}"
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
S="$REPO/bench/out/launch"
mkdir -p "$S"
PY="$REPO/.venv/Scripts/python.exe"
[ -x "$PY" ] || PY="$REPO/.venv/bin/python"
ST="$S/launch${N}_status.txt"
export HF_HUB_DISABLE_SYMLINKS_WARNING=1
cd "$REPO" || exit 1
echo "$(date +%H:%M) validating for run $N ($CAND)" >> "$ST"
"$PY" -m pytest tests -q -x > "$S/pytest${N}.log" 2>&1; rc=$?
gate=$("$PY" bench/quick_check.py 2>&1 | grep -a -o "TOTAL [0-9]*/" | grep -o "[0-9]*")
s1=$("$PY" bench/math_check.py --first 12 2>&1 | grep -a -o "TOTAL [0-9]*/" | grep -o "[0-9]*")
s2=$("$PY" bench/math_check.py 2503.03873_pg5 2503.03879_pg4 2503.03899_pg9 2503.03903_pg9 2503.03905_pg7 2503.03909_pg14 2503.03948_pg3 2503.03949_pg1 2503.03952_pg5 2503.03994_pg108 2503.04024_pg4 2503.04026_pg2 2>&1 | grep -a -o "TOTAL [0-9]*/" | grep -o "[0-9]*")
echo "$(date +%H:%M) pytest rc=$rc gate=$gate sample1=$s1 sample2=$s2 (need rc=0, gate>=96, sample1>=44, sample2>=$S2_MIN)" >> "$ST"
if [ "$rc" != "0" ] || [ "${gate:-0}" -lt 96 ] || [ "${s1:-0}" -lt 44 ] || [ "${s2:-0}" -lt "$S2_MIN" ]; then
  echo "STOP: validation failed, run $N not launched" >> "$ST"; exit 1
fi
nohup "$PY" -m truedoc.cli bench --candidate "$CAND" --workers 6 --no-score $EXTRA > "$S/run${N}.log" 2>&1 &
echo "$(date +%H:%M) run $N ($CAND) launched" >> "$ST"
sleep 120
until ls "$REPO"/bench/runs/${CAND}-*/conversion.json >/dev/null 2>&1; do sleep 60; done
D=$(ls -d "$REPO"/bench/runs/${CAND}-* | tail -1)
echo "$(date +%H:%M) run $N finished converting; scoring $D" >> "$ST"
"$PY" -c "import sys; from truedoc.bench.olmocr import score_candidate; score_candidate(sys.argv[1], sys.argv[2])" "$CAND" "$D" > "$S/score${N}.log" 2>&1
"$PY" bench/holdout_score.py "$D" >> "$S/score${N}.log" 2>&1
echo "$(date +%H:%M) run $N scored" >> "$ST"
