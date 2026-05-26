import asyncio
import json
import os
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path


def main_sync() -> int:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = Path(os.environ["GATE5_RUN_DIR"]).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)

    model = os.environ.get("MODEL", "qwen3.5:4b")
    config = {
        "model": model,
        "dataset": os.environ.get("DATASET_NAME", "math"),
        "weak_model": os.environ.get("WEAK_MODEL", "Qwen/Qwen1.5-0.5B-Chat"),
        "strong_model": os.environ.get("STRONG_MODEL", "Qwen/Qwen3-4B-Base"),
        "max_runtime_seconds": int(os.environ.get("MAX_RUNTIME_SECONDS", "1500")),
        "local_mode": True,
        "timestamp": timestamp,
        "tool_invocation_hint_active": bool(
            os.environ.get("CLAUDE_AGENT_SDK_SHIM_TOOL_INVOCATION_HINT")
        ),
        "unload_ollama_on_long_bash": True,
        "ollama_unload_base_url": os.environ.get(
            "OLLAMA_UNLOAD_BASE_URL", "http://127.0.0.1:11434"
        ),
    }
    (run_dir / "config.yaml").write_text(
        "\n".join(f"{k}: {v}" for k, v in config.items()) + "\n"
    )

    sys.path.insert(0, os.environ.get("UPSTREAM_DIR", "/home/tlifke/Projects/automated-w2s-research"))
    sys.path.insert(
        0,
        "/home/tlifke/Projects/morel-research/studies/003-automated-w2s-replication/"
        "investigations/003-claude-sdk-shim-and-researcher-swap/scripts",
    )

    from w2s_research.research_loop.agent import AutonomousAgentLoop
    from claude_agent_sdk_shim import create_builtin_tools_server

    idea_uid = f"opt3a-{timestamp}"
    idea_name = "option_3a_time_multiplex_smoke"
    os.environ["IDEA_UID"] = idea_uid
    os.environ["IDEA_NAME"] = idea_name
    os.environ["LOCAL_MODE"] = "true"
    os.environ["RUN_ID"] = str(uuid.uuid4())

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

    upstream_dir = os.environ.get(
        "UPSTREAM_DIR", "/home/tlifke/Projects/automated-w2s-research"
    )
    venv_bin = f"{upstream_dir}/.venv/bin"
    orchestrator = os.environ.get("ORCHESTRATOR_API_URL", "http://localhost:8000")
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
    }
    loop.mcp_servers["builtin"] = create_builtin_tools_server(
        cwd=str(workspace),
        bash_timeout=int(os.environ.get("BASH_TIMEOUT", "1800")),
        bash_cwd=upstream_dir,
        bash_env=bash_env,
        unload_ollama_on_long_bash=True,
        ollama_model=model,
        ollama_unload_base_url=config["ollama_unload_base_url"],
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
    }
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2))

    log_files = list((run_dir / "logs").glob("session_*.log"))
    tool_calls_seen = []
    for lf in log_files:
        text = lf.read_text(errors="ignore")
        for line in text.splitlines():
            if line.startswith("Tool: "):
                tool_calls_seen.append(line.strip())

    sys.stdout.write("\n=== OPTION 3a SUMMARY ===\n")
    sys.stdout.write(f"elapsed_sec={elapsed:.1f}\n")
    sys.stdout.write(f"sessions={result.get('sessions')}\n")
    sys.stdout.write(f"stop_reason={result.get('stop_reason')}\n")
    sys.stdout.write(f"tool_call_lines={len(tool_calls_seen)}\n")
    eval_called = any("evaluate_predictions" in tc for tc in tool_calls_seen)
    sys.stdout.write(f"evaluate_predictions_called={eval_called}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main_sync())
