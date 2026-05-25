#!/bin/bash
set -eo pipefail

if [ -z "$PATCH_FILE" ] || [ -z "$PATCH_SLUG" ]; then
  echo "usage: PATCH_FILE=... PATCH_SLUG=... [MODEL=qwen3.5:4b] [MAX_RUNTIME_SECONDS=1800] $0" >&2
  exit 1
fi

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PATCH_NUM=${PATCH_NUM:-1}
MODEL=${MODEL:-qwen3.5:4b}
MAX_RUNTIME_SECONDS=${MAX_RUNTIME_SECONDS:-1800}

REPO_ROOT="/home/tlifke/Projects/morel-research"
INV_DIR="$REPO_ROOT/studies/003-automated-w2s-replication/investigations/004-qwen-researcher-floor"
INV003_SCRIPTS="$REPO_ROOT/studies/003-automated-w2s-replication/investigations/003-claude-sdk-shim-and-researcher-swap/scripts"

GATE5_RUN_DIR="$INV_DIR/logs/4b_patch_${PATCH_NUM}_${PATCH_SLUG}_${TIMESTAMP}"
mkdir -p "$GATE5_RUN_DIR"

cp "$PATCH_FILE" "$GATE5_RUN_DIR/patch_text.txt"

export CLAUDE_AGENT_SDK_SHIM_TOOL_INVOCATION_HINT="$(cat $PATCH_FILE)"
export GATE5_RUN_DIR
export GATE5_WORKSPACE="$GATE5_RUN_DIR/workspace"
export MODEL
export MAX_RUNTIME_SECONDS
export UPSTREAM_DIR="/home/tlifke/Projects/automated-w2s-research"
export ORCHESTRATOR_API_URL="http://localhost:8000"
export DATASET_NAME="math"
export WEAK_MODEL="Qwen/Qwen1.5-0.5B-Chat"
export STRONG_MODEL="Qwen/Qwen3-4B-Base"
export BASH_TIMEOUT=1800

export PYTHONPATH="$INV003_SCRIPTS:$UPSTREAM_DIR:$PYTHONPATH"

cd "$INV003_SCRIPTS/tests"
"$UPSTREAM_DIR/.venv/bin/python" test_gate_5_full_loop.py 2>&1 | tee "$GATE5_RUN_DIR/run.log"

echo "GATE5_RUN_DIR=$GATE5_RUN_DIR"
