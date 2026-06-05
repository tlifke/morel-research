#!/usr/bin/env bash
set -uo pipefail

TEST="${1:?usage: run_batch.sh <t1|t7> <N> [tag]}"
N="${2:?usage: run_batch.sh <t1|t7> <N> [tag]}"
TAG="${3:-$TEST}"
HERE="$(cd "$(dirname "$0")/.." && pwd)"
BATCH="$HERE/runs/batch_${TAG}"
mkdir -p "$BATCH"

echo "batch: $TEST x$N -> $BATCH"
for i in $(seq 1 "$N"); do
  ii=$(printf "%02d" "$i")
  start=$SECONDS
  RUN_DIR="$BATCH/run_$ii" TEST="$TEST" node "$HERE/src/slice.ts" > "$BATCH/run_$ii.console.log" 2>&1
  echo "run $ii done ($((SECONDS-start))s)"
done
echo "batch complete: $BATCH"
