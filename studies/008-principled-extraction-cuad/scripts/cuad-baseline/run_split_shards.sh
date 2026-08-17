#!/usr/bin/env bash
set -euo pipefail

ROOT="${CUAD_ROOT:-$HOME/Projects/cuad-baseline}"
SHARDS="$ROOT/shards"
BS="${BS:-16}"
THREADS="${THREADS:-12}"

for f in "$SHARDS"/*.json; do
  case "$(basename "$f")" in
    *test*) echo "REFUSING test shard: $f" >&2; exit 1 ;;
  esac
done

MODELS=(
  "roberta-base roberta"
  "roberta-large roberta"
  "deberta-v2-xlarge deberta-v2"
)

cd "$ROOT/repo"

for entry in "${MODELS[@]}"; do
  set -- $entry
  NAME="$1"; MODEL_TYPE="$2"
  for SHARD in harness_val_g0 harness_val_g1 harness_val_g2 \
               principle_train_g0 principle_train_g1 principle_train_g2; do
    OUT="$ROOT/out-splits/$NAME/$SHARD"
    CACHE="$ROOT/cache-splits/$NAME/$SHARD"
    if [ -f "$OUT/nbest_predictions_.json" ]; then
      echo "SKIP $NAME $SHARD (done)"
      continue
    fi
    mkdir -p "$OUT" "$CACHE"
    rm -f "$CACHE"/cached_dev_*
    echo "START $NAME $SHARD $(date -Is)"
    START=$(date +%s.%N)
    /usr/bin/time -v "$ROOT/.venv/bin/python" train.py \
      --model_type "$MODEL_TYPE" \
      --model_name_or_path "$ROOT/ckpt/$NAME" \
      --predict_file "$SHARDS/$SHARD.json" \
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
      > "$OUT/run.log" 2>&1
    END=$(date +%s.%N)
    echo "WALL_SECONDS $(awk -v a="$START" -v b="$END" 'BEGIN{printf "%.1f", b-a}')" >> "$OUT/run.log"
    rm -rf "$CACHE"
    echo "DONE $NAME $SHARD $(awk -v a="$START" -v b="$END" 'BEGIN{printf "%.1f", b-a}')s"
  done
done

echo "ALL DONE $(date -Is)"
