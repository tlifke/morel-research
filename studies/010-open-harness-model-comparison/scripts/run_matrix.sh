#!/usr/bin/env bash
# Study 010 — full 2x2x2 run matrix:
#   {inklingsmall, glm-5-3-flash} x {clean, pi} x {verify, no-verify}
# Sequential; each run is self-contained under data/runs/.
set -uo pipefail
cd "$(dirname "$0")/.."

LOG="${PI010_MATRIX_LOG:-data/runs/matrix.log}"
echo "=== matrix start $(date -u +%FT%TZ) ===" >> "$LOG"

run() {
  local model="$1" condition="$2" spec="$3" tag="$4"
  echo "--- run: model=$model condition=$condition spec=$spec tag=$tag $(date -u +%FT%TZ)" >> "$LOG"
  node scripts/run_conditions.mjs --model "$model" --condition "$condition" --spec "$spec" --tag "$tag" \
    >> "$LOG" 2>&1
  local rc=$?
  echo "--- run rc=$rc $(date -u +%FT%TZ)" >> "$LOG"
  return $rc
}

fail=0
for model in inklingsmall glm-5-3-flash; do
  for condition in clean pi; do
    run "$model" "$condition" "task-spec.md" "verify" || fail=1
    run "$model" "$condition" "task-spec-variants/moderate-no-verify.md" "noverify" || fail=1
  done
done

echo "=== matrix end $(date -u +%FT%TZ) fail=$fail ===" >> "$LOG"
exit $fail
