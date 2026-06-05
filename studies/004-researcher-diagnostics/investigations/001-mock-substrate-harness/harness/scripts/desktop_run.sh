#!/usr/bin/env bash
set -uo pipefail

CMD="$1"
SSH="ssh -o BatchMode=yes -o RemoteCommand=none -o RequestTTY=no -o ConnectTimeout=12 -o ServerAliveInterval=20 -o ServerAliveCountMax=20 desktop"
REPO="/home/tlifke/Projects/automated-w2s-research"
TS=$(date +%s)

read -r -d '' REMOTE <<EOF || true
export PATH=$REPO/.venv/bin:\$PATH
export VIRTUAL_ENV=$REPO/.venv
export WORKSPACE_DIR=$REPO
export DATA_DIR=$REPO/data/math
export GROUND_TRUTH_DIR=$REPO/labeled_data
export ORCHESTRATOR_API_URL=http://localhost:8000
export SERVER_URL=http://localhost:8000
export DATASET_NAME=math
export WEAK_MODEL=Qwen/Qwen1.5-0.5B-Chat
export STRONG_MODEL=Qwen/Qwen3-4B-Base
export IDEA_UID=rh_smoke
export IDEA_NAME=rh_smoke
export RUN_ID=rh_${TS}
export LOCAL_MODE=true
export WANDB_MODE=offline
export WANDB_SILENT=true
export TRANSFORMERS_NO_ADVISORY_WARNINGS=1
export HF_HUB_DISABLE_PROGRESS_BARS=1
export VLLM_USE_FLASHINFER_SAMPLER=0
export VLLM_DISABLE_FLASHINFER_PREFILL=1
export VLLM_ATTENTION_BACKEND=FLASH_ATTN
cd $REPO
$CMD
echo __RC__:\$?
EOF

B64=$(printf '%s' "$REMOTE" | base64 | tr -d '\n')

start=$SECONDS
LOG=$($SSH "wsl -- bash -c \"echo $B64 | base64 -d | bash\"" 2>&1)
elapsed=$((SECONDS-start))

rc=$(printf '%s\n' "$LOG" | grep -oE '__RC__:[0-9]+' | tail -1 | cut -d: -f2)
[ -z "$rc" ] && rc="?"
CLEANLOG=$(printf '%s\n' "$LOG" | grep -v '__RC__:')

evalrel=$(printf '%s\n' "$CLEANLOG" | grep -oE 'eval_output_json=[^ ]+' | tail -1 | cut -d= -f2)
evalpath=""
if [ -n "$evalrel" ]; then
  case "$evalrel" in /*) evalpath="$evalrel" ;; *) evalpath="$REPO/$evalrel" ;; esac
fi

markers=""
printf '%s' "$CLEANLOG" | grep -q 'HELLO_MARKER' && markers="$markers HELLO_MARKER"
[ -n "$evalpath" ] && markers="$markers EVAL_PREDICTIONS_WRITTEN"
printf '%s' "$CLEANLOG" | grep -q 'vLLM engine cleanup complete' && markers="$markers VLLM_EVAL_COMPLETE"
printf '%s' "$CLEANLOG" | grep -qiE 'CUDA out of memory|OutOfMemoryError' && markers="$markers CUDA_OOM"
printf '%s' "$CLEANLOG" | grep -q 'Traceback (most recent call last)' && markers="$markers PYTHON_TRACEBACK"
markers=$(printf '%s\n' $markers | sed '/^$/d')

echo "exit_code: $rc"
echo "elapsed: ${elapsed}s"
echo "stdout_bytes: ${#CLEANLOG}"
echo ""
echo "detected:"
if [ -n "$markers" ]; then printf '%s\n' "$markers" | sed 's/^/  - /'; else echo "  (none)"; fi
if [ -n "$evalpath" ]; then echo "eval_output_path: $evalpath"; fi
echo ""
echo "--- log tail ---"
printf '%s\n' "$CLEANLOG" | tail -25

LOGDIR="$(cd "$(dirname "$0")/.." && pwd)/runs/desktop_logs"
mkdir -p "$LOGDIR"
printf '%s\n' "$CLEANLOG" > "$LOGDIR/job_${TS}.log"
if [ -n "$evalpath" ]; then echo "$evalpath" > /tmp/rh_last_evalpath; fi
