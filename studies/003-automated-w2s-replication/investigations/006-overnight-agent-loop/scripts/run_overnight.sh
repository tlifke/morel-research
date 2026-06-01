#!/bin/bash
# inv 006 — overnight agent loop launcher.
#
# Wraps inv 005's shim_v2 + handoff machinery for an extended
# unattended run. Key differences from inv 005's run_smoke_v2.sh:
#
# - MAX_RUNTIME_SECONDS=43200 (12 hours, vs 1500 for smoke)
# - HANDOFF_DIR is *persistent* across launches (in a stable path under
#   the inv 006 logs/ dir, not a tmp dir keyed by timestamp). Re-firing
#   this script picks up where the prior run left off.
# - HANDOFF_RESUME=1: the patched agent.py (apply_agent_resume.py)
#   reads the latest iteration_NN.yaml and continues at session N+1.
# - Defaults to inv 006's medium-scale patch text (overrides via
#   PATCH_FILE env var).
#
# Required env (override on cmdline):
#   MAC_OLLAMA_URL   — Mac Tailscale URL, e.g. http://100.106.241.33:11434
#
# Optional env:
#   MODEL            — researcher model (default nemotron-3-nano:4b)
#   MAX_RUNTIME_SECONDS — default 43200 (12 hours)
#   PATCH_FILE       — agent prompt patch (default inv 006 overnight patch)
#   HANDOFF_DIR_NAME — override the persistent handoff dir name
#
# To stop cleanly while running: kill -TERM <pid>. The agent loop
# finishes the current session boundary, writes its handoff, exits.
# To resume: re-run this script with the same env. The agent picks up
# at iteration N+1 from the latest yaml.

set -eo pipefail

REPO_ROOT="/home/tlifke/Projects/morel-research"
INV_DIR="$REPO_ROOT/studies/003-automated-w2s-replication/investigations/006-overnight-agent-loop"
INV005_DIR="$REPO_ROOT/studies/003-automated-w2s-replication/investigations/005-split-host-researcher"
SHIM_BASE="/home/tlifke/inv003_shim"
SHIM_V2_BASE="/home/tlifke/inv003_shim/shim_v2_pkg"
UPSTREAM_DIR="/home/tlifke/Projects/automated-w2s-research"

: "${MAC_OLLAMA_URL:?need MAC_OLLAMA_URL, e.g. http://100.106.241.33:11434}"
export OLLAMA_OPENAI_BASE_URL="$MAC_OLLAMA_URL"
export OLLAMA_ANTHROPIC_BASE_URL="$MAC_OLLAMA_URL"

MODEL=${MODEL:-nemotron-3-nano:4b}
MAX_RUNTIME_SECONDS=${MAX_RUNTIME_SECONDS:-43200}  # 12 hours
PATCH_FILE=${PATCH_FILE:-$INV_DIR/patches/patch_006_overnight_exploration.txt}
HANDOFF_DIR_NAME=${HANDOFF_DIR_NAME:-handoff_math_seed42}

if [ ! -f "$PATCH_FILE" ]; then
  echo "ERROR: patch file missing: $PATCH_FILE" >&2; exit 1
fi

# Persistent handoff dir under the inv 006 logs tree
HANDOFF_PARENT="$INV_DIR/logs/$HANDOFF_DIR_NAME"
HANDOFF_DIR="$HANDOFF_PARENT/.agent_handoff"
WORKSPACE="$HANDOFF_PARENT/workspace"
mkdir -p "$HANDOFF_DIR" "$WORKSPACE"

# Per-launch logs (timestamped) inside the same persistent dir
LAUNCH_TS=$(date +%Y%m%d_%H%M%S)
LAUNCH_DIR="$HANDOFF_PARENT/launches/$LAUNCH_TS"
mkdir -p "$LAUNCH_DIR/bash_subprocess_logs" "$LAUNCH_DIR/logs"

cp "$PATCH_FILE" "$LAUNCH_DIR/patch_text.txt"

# Mirror inv 005's env contract so the rest of the toolchain works
export GATE5_RUN_DIR="$LAUNCH_DIR"
export GATE5_WORKSPACE="$WORKSPACE"
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
export BASH_DEBUG_LOG_DIR="$LAUNCH_DIR/bash_subprocess_logs"

# Handoff machinery
export HANDOFF_ENABLE=1
export HANDOFF_RESUME=1
export HANDOFF_DIR  # informational; agent.py uses workspace/.agent_handoff

# PYTHONPATH: shim_v2 first, then v1 fallback, then upstream, then inv 005
# scripts dir (where handoff_writer.py lives — inv 006 reuses it)
export PYTHONPATH="$SHIM_V2_BASE:$SHIM_BASE/shim_pkg:$SHIM_BASE/scripts:$UPSTREAM_DIR:$INV005_DIR/scripts"
export SHIM_V2_BASE
export INV005_SCRIPTS_DIR="$INV005_DIR/scripts"
export CLAUDE_AGENT_SDK_SHIM_TOOL_INVOCATION_HINT="$(cat "$PATCH_FILE")"

# Pre-emptively unload any lingering Ollama models so the researcher
# has clean state on first call.
curl -s -m 5 http://localhost:11434/api/generate -d '{"model":"qwen3.5:4b","keep_alive":0,"prompt":""}' > /dev/null 2>&1 || true
curl -s -m 5 http://localhost:11434/api/generate -d '{"model":"nemotron-3-nano:4b","keep_alive":0,"prompt":""}' > /dev/null 2>&1 || true

# Workspace must contain a symlink to upstream's research_loop so the
# prompt template resolves. inv 005 ran from UPSTREAM_DIR cwd so this
# was implicit; inv 006 uses its own workspace, so wire it explicitly.
ln -sfn "$UPSTREAM_DIR/w2s_research" "$WORKSPACE/w2s_research" 2>/dev/null || true

# VRAM sampler (1Hz) for the duration of this launch
echo "ts,used_mib,free_mib" > "$LAUNCH_DIR/vram_samples.csv"
(
  while true; do
    LINE=$(nvidia-smi --query-gpu=memory.used,memory.free --format=csv,noheader,nounits 2>/dev/null)
    TS=$(date +%s.%N)
    echo "$TS,$LINE" >> "$LAUNCH_DIR/vram_samples.csv"
    sleep 1
  done
) &
SAMPLER_PID=$!

# Trap SIGTERM/SIGINT: forward to child python, kill sampler. The child
# python (agent loop) has its own SIGTERM handler that finishes the
# current session boundary cleanly.
PYTHON_PID=""
cleanup() {
  if [ -n "$PYTHON_PID" ]; then
    kill -TERM "$PYTHON_PID" 2>/dev/null || true
    wait "$PYTHON_PID" 2>/dev/null || true
  fi
  kill "$SAMPLER_PID" 2>/dev/null || true
}
trap cleanup TERM INT

cd "$UPSTREAM_DIR"
"$UPSTREAM_DIR/.venv/bin/python" "$INV005_DIR/scripts/run_smoke.py" \
    2>&1 | tee "$LAUNCH_DIR/run.log" &
PYTHON_PID=$!
wait "$PYTHON_PID"
EXIT=$?

cleanup
echo
echo "OVERNIGHT_RUN_DIR=$HANDOFF_PARENT"
echo "LAUNCH_DIR=$LAUNCH_DIR"
echo "exit_code=$EXIT"
