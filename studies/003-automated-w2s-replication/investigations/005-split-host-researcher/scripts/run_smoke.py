"""Inv 005 smoke runner: split-host researcher (Mac) + agent loop on desktop.

Diverges from inv003_shim/scripts/tests/test_gate_5_full_loop.py in three ways:

1. Adds VLLM_USE_FLASHINFER_SAMPLER, VLLM_DISABLE_FLASHINFER_PREFILL,
   VLLM_ATTENTION_BACKEND to bash_env (inv 4a issue #2 — flashinfer JIT
   compile fails on this WSL host; vLLM init OOMs without these).
2. Sets BASH_DEBUG_LOG_DIR so the patched shim Bash tool dumps every
   subprocess's stdout/stderr/exit_code/elapsed to a known directory.
   Strictly debug — remove once inv 005 closes.
3. Points OLLAMA_ANTHROPIC_BASE_URL at the Mac's Tailscale interface so
   the researcher serves from the Mac while SFT/vLLM run on the desktop.

Driven by env vars:
  MAC_OLLAMA_URL       — required, e.g. http://100.106.241.33:11434
  MODEL                — researcher model (default qwen3.5:4b)
  PATCH_FILE           — required path to tool_invocation_hint patch text
  GATE5_RUN_DIR        — required output directory
  MAX_RUNTIME_SECONDS  — default 900
"""
import asyncio
import json
import os
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

UPSTREAM_DEFAULT = "/home/tlifke/Projects/automated-w2s-research"
SHIM_BASE_DEFAULT = "/home/tlifke/inv003_shim"


def main_sync() -> int:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = Path(os.environ["GATE5_RUN_DIR"]).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)

    mac_ollama_url = os.environ["MAC_OLLAMA_URL"]
    model = os.environ.get("MODEL", "qwen3.5:4b")
    upstream_dir = os.environ.get("UPSTREAM_DIR", UPSTREAM_DEFAULT)
    shim_base = os.environ.get("SHIM_BASE", SHIM_BASE_DEFAULT)

    sys.path.insert(0, shim_base + "/scripts")
    sys.path.insert(0, shim_base + "/shim_pkg")
    sys.path.insert(0, upstream_dir)
    # inv 005: when SHIM_V2_BASE is set, put v2 ahead of v1 so
    # `from claude_agent_sdk import ...` resolves to the OpenAI-compat shim.
    _shim_v2 = os.environ.get("SHIM_V2_BASE")
    if _shim_v2:
        sys.path.insert(0, _shim_v2)
        # also expose the inv 005 scripts dir for handoff_writer
        _inv005_scripts = os.environ.get("INV005_SCRIPTS_DIR")
        if _inv005_scripts:
            sys.path.insert(0, _inv005_scripts)

    from w2s_research.research_loop.agent import AutonomousAgentLoop
    # NOTE: import from claude_agent_sdk (shim_pkg), NOT claude_agent_sdk_shim
    # (scripts), so the returned SdkMcpServer is the same class that client.py's
    # isinstance check in _build_tool_index expects. Importing from the wrong
    # module silently disables every builtin tool — see inv 005 Methods.
    from claude_agent_sdk import create_builtin_tools_server

    config = {
        "model": model,
        "dataset": os.environ.get("DATASET_NAME", "math"),
        "weak_model": os.environ.get("WEAK_MODEL", "Qwen/Qwen1.5-0.5B-Chat"),
        "strong_model": os.environ.get("STRONG_MODEL", "Qwen/Qwen3-4B-Base"),
        "max_runtime_seconds": int(os.environ.get("MAX_RUNTIME_SECONDS", "900")),
        "local_mode": True,
        "timestamp": timestamp,
        "mac_ollama_url": mac_ollama_url,
        "tool_invocation_hint_active": bool(
            os.environ.get("CLAUDE_AGENT_SDK_SHIM_TOOL_INVOCATION_HINT")
        ),
    }
    (run_dir / "config.yaml").write_text(
        "\n".join(f"{k}: {v}" for k, v in config.items()) + "\n"
    )

    idea_uid = f"inv005-{timestamp}"
    idea_name = "inv005_smoke"
    os.environ["IDEA_UID"] = idea_uid
    os.environ["IDEA_NAME"] = idea_name
    os.environ["LOCAL_MODE"] = "true"
    os.environ["RUN_ID"] = str(uuid.uuid4())
    os.environ["OLLAMA_ANTHROPIC_BASE_URL"] = mac_ollama_url

    loop = AutonomousAgentLoop(
        idea_uid=idea_uid,
        idea_name=idea_name,
        logs_dir=run_dir / "logs",
        max_runtime_seconds=config["max_runtime_seconds"],
        model=model,
        local_mode=True,
    )

    workspace = Path(os.environ.get("GATE5_WORKSPACE", str(run_dir / "workspace")))
    workspace.mkdir(parents=True, exist_ok=True)

    bash_debug_dir = run_dir / "bash_subprocess_logs"
    bash_debug_dir.mkdir(parents=True, exist_ok=True)

    venv_bin = f"{upstream_dir}/.venv/bin"
    orchestrator = os.environ.get(
        "ORCHESTRATOR_API_URL", "http://localhost:8000"
    )
    bash_env = {
        "PATH": f"{venv_bin}:{os.environ.get('PATH', '')}",
        "VIRTUAL_ENV": f"{upstream_dir}/.venv",
        "WORKSPACE_DIR": upstream_dir,
        "ORCHESTRATOR_API_URL": orchestrator,
        "SERVER_URL": orchestrator,
        "DATASET_NAME": config["dataset"],
        "DATA_DIR": f"{upstream_dir}/data/{config['dataset']}",
        "GROUND_TRUTH_DIR": f"{upstream_dir}/labeled_data",
        "WEAK_MODEL": config["weak_model"],
        "STRONG_MODEL": config["strong_model"],
        "IDEA_UID": idea_uid,
        "IDEA_NAME": idea_name,
        "RUN_ID": os.environ["RUN_ID"],
        "LOCAL_MODE": "true",
        "WANDB_MODE": os.environ.get("WANDB_MODE", "offline"),
        "WANDB_SILENT": "true",
        "TRANSFORMERS_NO_ADVISORY_WARNINGS": "1",
        "HF_HUB_DISABLE_PROGRESS_BARS": "1",
        "VLLM_USE_FLASHINFER_SAMPLER": "0",
        "VLLM_DISABLE_FLASHINFER_PREFILL": "1",
        "VLLM_ATTENTION_BACKEND": "FLASH_ATTN",
        "BASH_DEBUG_LOG_DIR": str(bash_debug_dir),
    }
    loop.mcp_servers["builtin"] = create_builtin_tools_server(
        cwd=str(workspace),
        bash_timeout=int(os.environ.get("BASH_TIMEOUT", "1800")),
        bash_cwd=upstream_dir,
        bash_env=bash_env,
    )

    start = time.time()
    result = asyncio.run(loop.run())
    elapsed = time.time() - start

    summary = {
        "elapsed_sec": elapsed,
        "sessions": result.get("sessions"),
        "stop_reason": result.get("stop_reason"),
        "run_id": result.get("run_id"),
        "idea_uid": idea_uid,
        "mac_ollama_url": mac_ollama_url,
    }
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2))

    log_files = list((run_dir / "logs").glob("session_*.log"))
    tool_calls_seen = []
    for lf in log_files:
        for line in lf.read_text(errors="ignore").splitlines():
            if line.startswith("Tool: "):
                tool_calls_seen.append(line.strip())

    print(f"\n=== INV-005 SMOKE SUMMARY ===")
    print(f"elapsed_sec={elapsed:.1f}")
    print(f"sessions={result.get('sessions')}")
    print(f"stop_reason={result.get('stop_reason')}")
    print(f"tool_call_lines={len(tool_calls_seen)}")
    for tc in tool_calls_seen[:20]:
        print(f"  {tc}")
    eval_called = any("evaluate_predictions" in tc for tc in tool_calls_seen)
    print(f"evaluate_predictions_called={eval_called}")
    print(f"bash_subprocess_logs_dir={bash_debug_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main_sync())
