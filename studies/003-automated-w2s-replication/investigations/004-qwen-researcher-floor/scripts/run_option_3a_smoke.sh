#!/bin/bash
set -eo pipefail

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
MODEL=${MODEL:-qwen3.5:4b}
MAX_RUNTIME_SECONDS=${MAX_RUNTIME_SECONDS:-1500}
PATCH_FILE=${PATCH_FILE:-/home/tlifke/Projects/morel-research/studies/003-automated-w2s-replication/investigations/004-qwen-researcher-floor/patches/patch_4_directive_first_action.txt}

REPO_ROOT="/home/tlifke/Projects/morel-research"
INV_DIR="$REPO_ROOT/studies/003-automated-w2s-replication/investigations/004-qwen-researcher-floor"
SHIM_BASE="/home/tlifke/inv003_shim"
UPSTREAM_DIR="/home/tlifke/Projects/automated-w2s-research"

GATE5_RUN_DIR="$INV_DIR/logs/option_3a_time_multiplex_${TIMESTAMP}"
mkdir -p "$GATE5_RUN_DIR"
cp "$PATCH_FILE" "$GATE5_RUN_DIR/patch_text.txt"

export GATE5_RUN_DIR
export GATE5_WORKSPACE="$GATE5_RUN_DIR/workspace"
export MODEL
export MAX_RUNTIME_SECONDS
export UPSTREAM_DIR
export ORCHESTRATOR_API_URL="http://localhost:8000"
export DATASET_NAME="math"
export WEAK_MODEL="Qwen/Qwen1.5-0.5B-Chat"
export STRONG_MODEL="Qwen/Qwen3-4B-Base"
export BASH_TIMEOUT=1800
export OLLAMA_UNLOAD_ON_LONG_BASH=1
export OLLAMA_UNLOAD_BASE_URL=${OLLAMA_UNLOAD_BASE_URL:-http://127.0.0.1:11434}
export PYTHONPATH="$SHIM_BASE/shim_pkg:$SHIM_BASE/scripts:$UPSTREAM_DIR"
export CLAUDE_AGENT_SDK_SHIM_TOOL_INVOCATION_HINT="$(cat $PATCH_FILE)"

cd "$UPSTREAM_DIR"
"$UPSTREAM_DIR/.venv/bin/python" "$INV_DIR/scripts/option_3a_runner.py" 2>&1 | tee "$GATE5_RUN_DIR/run.log"

echo "GATE5_RUN_DIR=$GATE5_RUN_DIR"
