#!/bin/bash
# Inv 005 smoke launcher. Sets env + invokes run_smoke.py.
#
# Required env (override on cmdline):
#   MAC_OLLAMA_URL   — Mac Tailscale URL, e.g. http://100.106.241.33:11434
#
# Optional env:
#   MODEL            — researcher model (default qwen3.5:4b)
#   MAX_RUNTIME_SECONDS — default 900
#   PATCH_NUM        — labels the log directory (default 4)
#   PATCH_SLUG       — labels the log directory (default directive_first_action)
set -eo pipefail

REPO_ROOT="/home/tlifke/Projects/morel-research"
INV_DIR="$REPO_ROOT/studies/003-automated-w2s-replication/investigations/005-split-host-researcher"
INV004_DIR="$REPO_ROOT/studies/003-automated-w2s-replication/investigations/004-qwen-researcher-floor"
SHIM_BASE="/home/tlifke/inv003_shim"
UPSTREAM_DIR="/home/tlifke/Projects/automated-w2s-research"

: "${MAC_OLLAMA_URL:?need MAC_OLLAMA_URL, e.g. http://100.106.241.33:11434}"
# Belt-and-suspenders: even with the upstream fix in client.py reading
# OLLAMA_ANTHROPIC_BASE_URL per-instantiation, set it before Python starts
# so we don't depend on the inv 005 upstream patch having landed.
export OLLAMA_ANTHROPIC_BASE_URL="$MAC_OLLAMA_URL"
MODEL=${MODEL:-qwen3.5:4b}
MAX_RUNTIME_SECONDS=${MAX_RUNTIME_SECONDS:-900}
PATCH_NUM=${PATCH_NUM:-4}
PATCH_SLUG=${PATCH_SLUG:-directive_first_action}
PATCH_FILE=${PATCH_FILE:-$INV004_DIR/patches/patch_${PATCH_NUM}_${PATCH_SLUG}.txt}

if [ ! -f "$PATCH_FILE" ]; then
  echo "ERROR: patch file missing: $PATCH_FILE" >&2; exit 1
fi

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
SAFE_MODEL=${MODEL//[:\/]/_}
GATE5_RUN_DIR="$INV_DIR/logs/q3_smoke_${SAFE_MODEL}_p${PATCH_NUM}_${TIMESTAMP}"
mkdir -p "$GATE5_RUN_DIR" "$INV_DIR/logs"

cp "$PATCH_FILE" "$GATE5_RUN_DIR/patch_text.txt"

export GATE5_RUN_DIR
export GATE5_WORKSPACE="$GATE5_RUN_DIR/workspace"
export MODEL
export MAX_RUNTIME_SECONDS
export UPSTREAM_DIR
export SHIM_BASE
export MAC_OLLAMA_URL
export ORCHESTRATOR_API_URL="http://localhost:8000"
export DATASET_NAME="math"
export WEAK_MODEL="Qwen/Qwen1.5-0.5B-Chat"
export STRONG_MODEL="Qwen/Qwen3-4B-Base"
export BASH_TIMEOUT=1800
export PYTHONPATH="$SHIM_BASE/shim_pkg:$SHIM_BASE/scripts:$UPSTREAM_DIR"
export CLAUDE_AGENT_SDK_SHIM_TOOL_INVOCATION_HINT="$(cat $PATCH_FILE)"

# Evict anything resident on the desktop GPU before launch
curl -s -m 5 http://localhost:11434/api/generate -d '{"model":"qwen3.5:4b","keep_alive":0,"prompt":""}' > /dev/null 2>&1 || true
curl -s -m 5 http://localhost:11434/api/generate -d '{"model":"nemotron-3-nano:4b","keep_alive":0,"prompt":""}' > /dev/null 2>&1 || true

# GPU sampler
echo "ts,used_mib,free_mib" > "$GATE5_RUN_DIR/vram_samples.csv"
(
  while true; do
    LINE=$(nvidia-smi --query-gpu=memory.used,memory.free --format=csv,noheader,nounits 2>/dev/null)
    TS=$(date +%s.%N)
    echo "$TS,$LINE" >> "$GATE5_RUN_DIR/vram_samples.csv"
    sleep 1
  done
) &
SAMPLER_PID=$!

cd "$UPSTREAM_DIR"
"$UPSTREAM_DIR/.venv/bin/python" "$INV_DIR/scripts/run_smoke.py" 2>&1 | tee "$GATE5_RUN_DIR/run.log"
EXIT=${PIPESTATUS[0]}

kill $SAMPLER_PID 2>/dev/null || true
echo "GATE5_RUN_DIR=$GATE5_RUN_DIR"
echo "exit_code=$EXIT"
