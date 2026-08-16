#!/usr/bin/env bash
set -euo pipefail

ROOT="${CUAD_ROOT:-$HOME/Projects/cuad-baseline}"
NAME="$1"
MODEL_TYPE="$2"
CKPT="$ROOT/ckpt/$NAME"
PREDICT_FILE="${PREDICT_FILE:-$ROOT/smoke.json}"
BS="${BS:-16}"
THREADS="${THREADS:-8}"
OUT="$ROOT/out/$NAME"
CACHE="$ROOT/cache/$NAME"

mkdir -p "$OUT" "$CACHE"
rm -f "$CACHE"/cached_dev_* "$OUT"/nbest_predictions_.json

cd "$ROOT/repo"

nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -l 1 \
  > "$OUT/vram.log" 2>/dev/null &
SMI=$!
trap 'kill $SMI 2>/dev/null || true' EXIT

START=$(date +%s.%N)
"$ROOT/.venv/bin/python" train.py \
  --model_type "$MODEL_TYPE" \
  --model_name_or_path "$CKPT" \
  --predict_file "$PREDICT_FILE" \
  --do_eval \
  --version_2_with_negative \
  --max_seq_length 512 \
  --max_answer_length 512 \
  --doc_stride 256 \
  --n_best_size 20 \
  --per_gpu_eval_batch_size "$BS" \
  --threads "$THREADS" \
  --output_dir "$OUT" \
  --cache_dir "$CACHE" \
  --overwrite_output_dir \
  2>&1 | tee "$OUT/run.log"
END=$(date +%s.%N)

kill $SMI 2>/dev/null || true
echo "WALL_SECONDS $(awk -v a="$START" -v b="$END" 'BEGIN{printf "%.1f", b-a}')" | tee -a "$OUT/run.log"
echo "PEAK_VRAM_MIB $(sort -n "$OUT/vram.log" | tail -1)" | tee -a "$OUT/run.log"
