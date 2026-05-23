#!/usr/bin/env bash
set -u

LOG=/tmp/vanilla_w2s_smoke.log
VRAMLOG=/tmp/vram_during_smoke.log
META=/tmp/vram_watcher_meta.log
INNER=/tmp/run_smoke_inner.sh

rm -f "$LOG" "$VRAMLOG" "$META"

echo "=== smoke launcher start $(date) ===" >> "$LOG"
cd /home/tlifke/Projects/automated-w2s-research || { echo "cd failed" >> "$LOG"; exit 1; }
echo "pwd=$(pwd)" >> "$LOG"

nohup bash -c '
  while true; do
    nvidia-smi --query-gpu=timestamp,memory.used,memory.free,utilization.gpu --format=csv,noheader,nounits >> /tmp/vram_during_smoke.log
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
  --train-size=64 \
  --test-size=64 \
  --max-ctx=2048
INNERSCRIPT
chmod +x "$INNER"

nohup setsid "$INNER" >> "$LOG" 2>&1 < /dev/null &
SMOKE_PID=$!
echo "smoke_pid=$SMOKE_PID" >> "$LOG"

disown -a
sleep 3
echo "after_3s_alive=$(ps -p $SMOKE_PID >/dev/null 2>&1 && echo yes || echo no)" >> "$LOG"

echo "VRAM_WATCHER_PID=$VRAM_PID"
echo "SMOKE_PID=$SMOKE_PID"
