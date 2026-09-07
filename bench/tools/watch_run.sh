#!/usr/bin/env bash
# Print each new line of a run's status file as it appears; exit when the run is scored or stopped.
# For the Monitor tool: `bash bench/tools/watch_run.sh <run number>` (a file, so no quoting trouble).
N=${1:?run number}
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
ST="$REPO/bench/out/launch/launch${N}_status.txt"
seen=0
while true; do
  if [ -f "$ST" ]; then
    n=$(wc -l < "$ST")
    if [ "$n" -gt "$seen" ]; then
      tail -n +$((seen + 1)) "$ST"
      seen=$n
    fi
    if tail -n 1 "$ST" | grep -q -E "scored|STOP"; then
      exit 0
    fi
  fi
  sleep 60
done
