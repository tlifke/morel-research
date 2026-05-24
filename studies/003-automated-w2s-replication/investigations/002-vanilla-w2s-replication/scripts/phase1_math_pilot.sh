#!/usr/bin/env bash
set -u

LOG=/tmp/phase1_math_pilot.log
VRAMLOG=/tmp/phase1_vram.log
META=/tmp/phase1_vram_watcher_meta.log
INNER=/tmp/phase1_math_pilot_inner.sh

rm -f "$LOG" "$VRAMLOG" "$META"

echo "=== phase1 math pilot launcher start $(date) ===" >> "$LOG"
cd /home/tlifke/Projects/automated-w2s-research || { echo "cd failed" >> "$LOG"; exit 1; }
echo "pwd=$(pwd)" >> "$LOG"

nohup bash -c '
  while true; do
    nvidia-smi --query-gpu=timestamp,memory.used,memory.free,utilization.gpu --format=csv,noheader,nounits >> /tmp/phase1_vram.log
    sleep 5
  done
' > "$META" 2>&1 &
VRAM_PID=$!
echo "vram_watcher_pid=$VRAM_PID" >> "$LOG"

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
exec /home/tlifke/Projects/automated-w2s-research/.venv/bin/python run.py \
  --idea vanilla_w2s \
  --seed 42 \
  --data-dir data/math \
  --batch-size=4 \
  --gradient-accumulation-steps=8 \
  --epochs=1 \
  --max-ctx=2048
INNERSCRIPT
chmod +x "$INNER"

nohup setsid "$INNER" >> "$LOG" 2>&1 < /dev/null &
RUN_PID=$!
echo "run_pid=$RUN_PID" >> "$LOG"
echo "$RUN_PID" > /tmp/phase1_math_pilot.pid
echo "$VRAM_PID" > /tmp/phase1_vram_watcher.pid

disown -a
sleep 3
echo "after_3s_alive=$(ps -p $RUN_PID >/dev/null 2>&1 && echo yes || echo no)" >> "$LOG"

echo "VRAM_WATCHER_PID=$VRAM_PID"
echo "RUN_PID=$RUN_PID"
