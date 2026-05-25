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

    model = os.environ.get("MODEL", "qwen3:4b")
    config = {
        "model": model,
        "dataset": os.environ.get("DATASET_NAME", "math"),
        "weak_model": os.environ.get("WEAK_MODEL", "Qwen/Qwen1.5-0.5B-Chat"),
        "strong_model": os.environ.get("STRONG_MODEL", "Qwen/Qwen3-4B-Base"),
        "max_runtime_seconds": int(os.environ.get("MAX_RUNTIME_SECONDS", "1800")),
        "local_mode": True,
        "timestamp": timestamp,
        "tool_invocation_hint_active": bool(
            os.environ.get("CLAUDE_AGENT_SDK_SHIM_TOOL_INVOCATION_HINT")
        ),
    }
    (run_dir / "config.yaml").write_text(
        "\n".join(f"{k}: {v}" for k, v in config.items()) + "\n"
    )

    sys.path.insert(0, "/home/tlifke/Projects/automated-w2s-research")
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

    from w2s_research.research_loop.agent import AutonomousAgentLoop
    from claude_agent_sdk_shim import create_builtin_tools_server

    idea_uid = f"gate5-{timestamp}"
    idea_name = "gate5_smoke"
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
    loop.mcp_servers["builtin"] = create_builtin_tools_server(
        cwd=str(workspace),
        bash_timeout=int(os.environ.get("BASH_TIMEOUT", "1800")),
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

    print(f"\n=== GATE 5 SUMMARY ===")
    print(f"elapsed_sec={elapsed:.1f}")
    print(f"sessions={result.get('sessions')}")
    print(f"stop_reason={result.get('stop_reason')}")
    print(f"tool_call_lines={len(tool_calls_seen)}")
    for tc in tool_calls_seen[:20]:
        print(f"  {tc}")

    eval_called = any("evaluate_predictions" in tc for tc in tool_calls_seen)
    print(f"evaluate_predictions_called={eval_called}")

    return 0


if __name__ == "__main__":
    sys.exit(main_sync())
