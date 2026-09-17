#!/usr/bin/env bash
# Poll a rented machine running run_bakeoff.sh: print the run log's stage markers and anything
# that reads as a failure, the count of markdown files written, and the Pro download's size.
# Exits 0 when the job's "== exit" line appears, 2 after eight failed connections in a row.
#
#   bash bench/gpu/poll_bakeoff.sh <port> <host>
PORT=${1:?port}
HOST=${2:?host}
KEY=~/.ssh/truedoc_vast
seen=0
last=""
fails=0
while true; do
  if ! out=$(ssh -n -i "$KEY" -p "$PORT" -o BatchMode=yes -o ConnectTimeout=20 "root@$HOST" "cat ~/gpu/run.log 2>/dev/null; echo __MD__; find ~/gpu/out/markdown -name '*.md' 2>/dev/null | wc -l; du -sh ~/.cache/huggingface/hub 2>/dev/null | cut -f1" 2>/dev/null); then
    fails=$((fails + 1))
    echo "ssh poll failed ($fails) $(date +%H:%M)"
    if [ "$fails" -ge 8 ]; then exit 2; fi
    sleep 60
    continue
  fi
  fails=0
  log=$(printf '%s\n' "$out" | sed '/^__MD__$/,$d' | tr '\r' '\n')
  state=$(printf '%s\n' "$out" | sed -n '/^__MD__$/,$p' | tail -n +2 | tr '\n' ' ')
  n=$(printf '%s\n' "$log" | wc -l)
  if [ "$n" -gt "$seen" ]; then
    printf '%s\n' "$log" | tail -n +$((seen + 1)) | grep -a -i -E "^== |^-- |fetched|MISSING|Traceback|error|failed|Killed|OOM|No space|died|never came up|torch [0-9]|INF-MLLM at|\[infer\]" | grep -a -v -i "warning" | tail -n 8
    seen=$n
  fi
  # One line per hundred files, not one per minute: every line here is a notification.
  md=$(printf '%s' "$state" | cut -d' ' -f1)
  step=$(( ${md:-0} / 100 ))
  if [ "$step" != "$last" ]; then
    echo "$(date +%H:%M) markdown files / weights cache: $state"
    last=$step
  fi
  if printf '%s\n' "$log" | grep -q '^== exit'; then
    echo "JOB ENDED $(date +%H:%M): $(printf '%s\n' "$log" | grep '^== exit' | tail -1)"
    exit 0
  fi
  sleep 60
done
