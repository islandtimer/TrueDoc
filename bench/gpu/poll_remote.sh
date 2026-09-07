#!/usr/bin/env bash
# Poll a rented GPU machine's ~/gpu/run.log once a minute and print only the lines worth acting on:
# fetch progress, the run script's stage markers, errors, and the count of markdown pages written.
# Exits 0 when the job's "== exit" line appears, 2 after eight failed connections in a row.
#
#   bash bench/gpu/poll_remote.sh <port> <host>
PORT=${1:?port}
HOST=${2:?host}
KEY=~/.ssh/truedoc_vast
seen=0
lastmd=-1
fails=0
while true; do
  if ! out=$(ssh -n -i "$KEY" -p "$PORT" -o BatchMode=yes -o ConnectTimeout=20 "root@$HOST" "cat ~/gpu/run.log 2>/dev/null; echo __MD__; find ~/gpu/out -name '*.md' -path '*/markdown/*' 2>/dev/null | wc -l" 2>/dev/null); then
    fails=$((fails + 1))
    echo "ssh poll failed ($fails) $(date +%H:%M)"
    if [ "$fails" -ge 8 ]; then exit 2; fi
    sleep 60
    continue
  fi
  fails=0
  log=$(printf '%s\n' "$out" | sed '/^__MD__$/,$d' | tr '\r' '\n')
  md=$(printf '%s\n' "$out" | sed -n '/^__MD__$/{n;p}')
  n=$(printf '%s\n' "$log" | wc -l)
  if [ "$n" -gt "$seen" ]; then
    printf '%s\n' "$log" | tail -n +$((seen + 1)) | grep -E "fetched|MISSING|^== |^-- |Traceback|Error|Killed|OOM|CUDA|No space|exit " | tail -n 6
    seen=$n
  fi
  if [ "$md" != "$lastmd" ]; then
    echo "$(date +%H:%M) markdown files so far: $md"
    lastmd=$md
  fi
  if printf '%s\n' "$log" | grep -q '^== exit'; then
    echo "JOB ENDED $(date +%H:%M): $(printf '%s\n' "$log" | grep '^== exit' | tail -1)"
    exit 0
  fi
  sleep 60
done
