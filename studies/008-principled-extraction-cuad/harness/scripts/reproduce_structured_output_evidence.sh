#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STUDY="$(cd "$HERE/../.." && pwd)"
DATA="$STUDY/reviews/structured-output-evidence-data"
PROBE="$HERE/probe_structured_output.py"

: "${TINKER_API_KEY:?TINKER_API_KEY must be set}"
mkdir -p "$DATA"

uv run --no-project python "$PROBE" --phase config \
  --max-tokens 3000 --workers 8 \
  --out "$DATA/phase1-config.json"

uv run --no-project python "$PROBE" --phase stress \
  --n 10 --max-tokens 2000 --workers 12 \
  --variants json_object json_schema_strict guided_json structured_outputs tools_forced none \
  --out "$DATA/phase2-stress.json"

uv run --no-project python "$PROBE" --phase rates \
  --n 20 --temperature 0.7 --max-tokens 16384 --workers 10 \
  --variants json_object tools_forced none \
  --out "$DATA/phase3-rates.json"

uv run --no-project python "$PROBE" --phase anthropic \
  --n 3 --max-tokens 1500 \
  --out "$DATA/phase4-anthropic-tools.json"

uv run --no-project python "$HERE/render_structured_output_evidence.py" \
  --phase1 "$DATA/phase1-config.json" \
  --phase2 "$DATA/phase2-stress.json" \
  --phase3 "$DATA/phase3-rates.json" \
  --phase4 "$DATA/phase4-anthropic-tools.json" \
  --verdicts "$HERE/structured_output_verdicts.json" \
  --coverage-note "$HERE/coverage_note.html" \
  --out "$STUDY/reviews/structured-output-evidence.html"
