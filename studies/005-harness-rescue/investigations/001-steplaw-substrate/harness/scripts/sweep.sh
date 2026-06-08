#!/usr/bin/env bash
# usage: sweep.sh PROVIDER MODEL SEED_START SEED_END N:D [N:D ...]
set -u
HARNESS_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$HARNESS_DIR"
[ -f /Users/tylerlifke/Projects/morel-research/.env ] && { set -a; . /Users/tylerlifke/Projects/morel-research/.env; set +a; }

PROVIDER="$1"; MODEL="$2"; S0="$3"; S1="$4"; shift 4
ENVS=("$@")
SWEEP="runs/${SUBDIR:-sweep}"
mkdir -p "$SWEEP"
TAGX="${ARM:+_${ARM}}${THINK:+_re${THINK}}"
LOG="$SWEEP/${PROVIDER}${TAGX}_sweep.log"

for pair in "${ENVS[@]}"; do
  N="${pair%%:*}"; D="${pair##*:}"
  for s in $(seq "$S0" "$S1"); do
    tag="${PROVIDER}${TAGX}_N${N}_D${D}_s${s}"
    RD="$SWEEP/$tag"
    if [ -f "$RD/loop_summary.json" ]; then echo "[skip] $tag"; continue; fi
    echo "[run ] $tag  ($(date +%H:%M:%S))"
    RUN_DIR="$RD" PROVIDER="$PROVIDER" MODEL="$MODEL" N="$N" D="$D" BUDGET="${BUDGET:-50}" \
      THINK="${THINK:-}" REFLECT="${REFLECT:-off}" ACTUATE="${ACTUATE:-off}" OLLAMA_URL="${OLLAMA_URL:-http://localhost:11434/v1}" \
      node src/researcher.ts >> "$LOG" 2>&1 \
      && tail -2 "$LOG" | sed 's/^/        /' \
      || echo "        [ERROR] see $LOG"
  done
done
echo "[DONE] $PROVIDER${RETAG} sweep seeds $S0-$S1"
