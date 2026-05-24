#!/usr/bin/env bash
set -u

VENV_PY=/home/tlifke/Projects/automated-w2s-research/.venv/bin/python
REPO=/home/tlifke/Projects/automated-w2s-research

LOG=/tmp/phase2_all.log
VRAMLOG=/tmp/phase2_vram.log
META=/tmp/phase2_vram_watcher_meta.log
INNER=/tmp/phase2_all_inner.sh

rm -f "$LOG" "$VRAMLOG" "$META"

echo "=== phase2 all launcher start $(date) ===" >> "$LOG"
cd "$REPO" || { echo "cd failed" >> "$LOG"; exit 1; }

nohup bash -c '
  while true; do
    nvidia-smi --query-gpu=timestamp,memory.used,memory.free,utilization.gpu --format=csv,noheader,nounits >> /tmp/phase2_vram.log
    sleep 10
  done
' > "$META" 2>&1 &
VRAM_PID=$!
echo "vram_watcher_pid=$VRAM_PID" >> "$LOG"
echo "$VRAM_PID" > /tmp/phase2_vram_watcher.pid

cat > "$INNER" <<'INNERSCRIPT'
#!/usr/bin/env bash
set -u
export WANDB_MODE=disabled
export HF_HUB_DISABLE_TELEMETRY=1
export TORCH_CUDA_ARCH_LIST=8.6
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export PATH=/home/tlifke/Projects/automated-w2s-research/.venv/bin:$PATH
export VLLM_USE_FLASHINFER_SAMPLER=0

cd /home/tlifke/Projects/automated-w2s-research

run_one() {
  local DATASET=$1
  local PER_LOG=/tmp/phase2_${DATASET}.log
  rm -f "$PER_LOG"
  echo "=== phase2 ${DATASET} start $(date) ===" | tee -a "$PER_LOG"
  /home/tlifke/Projects/automated-w2s-research/.venv/bin/python run.py \
    --idea vanilla_w2s \
    --seed 42 \
    --data-dir labeled_data/${DATASET} \
    --batch-size=4 \
    --gradient-accumulation-steps=8 \
    --epochs=5 \
    --max-ctx=2048 \
    2>&1 | tee -a "$PER_LOG"
  local STATUS=${PIPESTATUS[0]}
  echo "=== phase2 ${DATASET} end $(date) exit=${STATUS} ===" | tee -a "$PER_LOG"
  return $STATUS
}

for DATASET in math chat code; do
  echo ""
  echo "######################################################"
  echo "# phase2: starting ${DATASET}  $(date)"
  echo "######################################################"
  run_one "$DATASET"
  RC=$?
  if [ $RC -ne 0 ]; then
    echo "phase2 ${DATASET} FAILED exit=${RC} — stopping"
    exit $RC
  fi
done

echo ""
echo "=== phase2 all complete $(date) ==="
INNERSCRIPT
chmod +x "$INNER"

nohup setsid "$INNER" >> "$LOG" 2>&1 < /dev/null &
RUN_PID=$!
echo "run_pid=$RUN_PID" >> "$LOG"
echo "$RUN_PID" > /tmp/phase2_all.pid

disown -a
sleep 3
echo "after_3s_alive=$(ps -p $RUN_PID >/dev/null 2>&1 && echo yes || echo no)" >> "$LOG"

echo "VRAM_WATCHER_PID=$VRAM_PID"
echo "RUN_PID=$RUN_PID"
