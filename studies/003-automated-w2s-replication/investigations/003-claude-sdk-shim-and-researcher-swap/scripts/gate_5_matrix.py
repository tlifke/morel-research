import json
import os
import shlex
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path


PATCH_TEXT = (
    "Tool invocation protocol: when you need to run a shell command, "
    "read or write a file, or otherwise act on the environment, you MUST "
    "invoke the corresponding tool (Bash, Read, Write, Edit, Glob, Grep) "
    "via a real tool call. Do not write shell commands inside markdown "
    "code blocks or prose; commands written that way will not execute. "
    "If you intend to run something, call Bash with the command. Do not "
    "narrate the command as text and stop."
)

REMOTE_BASE = "/home/tlifke/inv003_shim"
UPSTREAM_DIR = "/home/tlifke/Projects/automated-w2s-research"
SSH = [
    "ssh",
    "-o", "RemoteCommand=none",
    "-o", "RequestTTY=no",
    "-o", "BatchMode=yes",
    "desktop",
]


def ssh_run(remote_cmd: str, timeout: int = 60):
    import base64
    b64 = base64.b64encode(remote_cmd.encode("utf-8")).decode("ascii")
    inner = f'echo {b64} | base64 -d | bash'
    wsl_cmd = f'wsl -- bash -lc "{inner}"'
    return subprocess.run(SSH + [wsl_cmd], capture_output=True, text=True, timeout=timeout)


def push_file(local_path: str, remote_path: str):
    import base64
    with open(local_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    inner = f'echo {b64} | base64 -d > {remote_path}'
    cmd = f'wsl -- bash -lc "{inner}"'
    r = subprocess.run(SSH + [cmd], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise RuntimeError(f"push_file failed: rc={r.returncode} stderr={r.stderr}")


def run_cell(model: str, patch_on: bool, max_runtime_sec: int = 600) -> dict:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    patch_tag = "patch" if patch_on else "nopatch"
    safe_model = model.replace(":", "_").replace("/", "_")
    run_dir = f"{REMOTE_BASE}/logs/gate_5_run_{stamp}_{safe_model}_{patch_tag}"

    with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False) as f:
        f.write("#!/bin/bash\n")
        f.write(f"mkdir -p {run_dir}\n")
        f.write(f"export GATE5_RUN_DIR={shlex.quote(run_dir)}\n")
        f.write(f"export MODEL={shlex.quote(model)}\n")
        f.write(f"export MAX_RUNTIME_SECONDS={max_runtime_sec}\n")
        f.write("export DATASET_NAME=math\n")
        f.write(
            "export PYTHONPATH=/home/tlifke/inv003_shim/shim_pkg:/home/tlifke/inv003_shim/scripts\n"
        )
        if patch_on:
            f.write("read -r -d '' HINT <<'HINT_EOF' || true\n")
            f.write(PATCH_TEXT + "\n")
            f.write("HINT_EOF\n")
            f.write("export CLAUDE_AGENT_SDK_SHIM_TOOL_INVOCATION_HINT=\"$HINT\"\n")
        f.write(f"cd {UPSTREAM_DIR}\n")
        f.write(
            f"uv run python {REMOTE_BASE}/scripts/tests/test_gate_5_full_loop.py "
            f"> {run_dir}/stdout.log 2>&1\n"
        )
        runner_local = f.name

    remote_runner = f"{REMOTE_BASE}/scripts/_cell_runner.sh"
    push_file(runner_local, remote_runner)
    ssh_run(f"chmod +x {remote_runner}")

    print(f"\n=== CELL: model={model} patch={patch_on} ===", flush=True)
    print(f"run_dir={run_dir}", flush=True)
    start = time.time()
    proc = subprocess.run(
        SSH + [f'wsl -- bash -lc "{remote_runner}"'],
        capture_output=True, text=True, timeout=max_runtime_sec + 600,
    )
    elapsed = time.time() - start
    print(f"elapsed={elapsed:.1f}s rc={proc.returncode}", flush=True)
    if proc.returncode != 0:
        print(f"stderr_tail: {proc.stderr[-1500:]}", flush=True)
        print(f"stdout_tail: {proc.stdout[-1500:]}", flush=True)

    metrics = collect_metrics(run_dir)
    metrics.update({
        "model": model,
        "patch_on": patch_on,
        "elapsed_sec": elapsed,
        "rc": proc.returncode,
        "run_dir": run_dir,
    })
    print(json.dumps(metrics, indent=2), flush=True)
    return metrics


def collect_metrics(run_dir: str) -> dict:
    cmd = (
        f"ls {run_dir}/logs/ 2>/dev/null; echo '===SEP==='; "
        f"cat {run_dir}/summary.json 2>/dev/null; echo '===SEP==='; "
        f"grep -h '^Tool:' {run_dir}/logs/session_*.log 2>/dev/null; echo '===SEP==='; "
        f"grep -hE '\\`\\`\\`bash|\\`\\`\\`sh|\\`\\`\\`shell' {run_dir}/logs/session_*.log 2>/dev/null | head -20; echo '===SEP==='; "
        f"ls {run_dir}/workspace 2>/dev/null; echo '===SEP==='; "
        f"tail -100 {run_dir}/stdout.log 2>/dev/null"
    )
    r = ssh_run(cmd, timeout=60)
    out = r.stdout
    parts = out.split("===SEP===")
    sessions_list = parts[0] if len(parts) > 0 else ""
    summary_raw = parts[1] if len(parts) > 1 else ""
    tools_raw = parts[2] if len(parts) > 2 else ""
    md_raw = parts[3] if len(parts) > 3 else ""
    ws_raw = parts[4] if len(parts) > 4 else ""
    stdout_tail = parts[5] if len(parts) > 5 else ""

    n_sessions = sum(1 for line in sessions_list.splitlines() if line.startswith("session_"))
    tool_lines = [l.strip() for l in tools_raw.splitlines() if l.startswith("Tool:")]
    bash_calls = sum(1 for l in tool_lines if l == "Tool: Bash")
    write_calls = sum(1 for l in tool_lines if l == "Tool: Write")
    read_calls = sum(1 for l in tool_lines if l == "Tool: Read")
    eval_calls = sum(1 for l in tool_lines if l == "Tool: evaluate_predictions")
    md_shell_blocks = sum(1 for l in md_raw.splitlines() if "```" in l)
    workspace_files = [l for l in ws_raw.splitlines() if l.strip()]

    try:
        summary = json.loads(summary_raw.strip()) if summary_raw.strip() else {}
    except Exception:
        summary = {}

    passed = bash_calls > 0
    return {
        "sessions": n_sessions,
        "bash_calls": bash_calls,
        "write_calls": write_calls,
        "read_calls": read_calls,
        "evaluate_predictions_calls": eval_calls,
        "markdown_shell_blocks": md_shell_blocks,
        "workspace_nonempty": len(workspace_files) > 0,
        "workspace_files": workspace_files[:10],
        "summary": summary,
        "passed_gate_5": passed,
        "stdout_tail": stdout_tail[-500:],
    }


def main():
    cells = [
        ("qwen3:4b", True),
        ("qwen3.5:4b", False),
        ("qwen3.5:4b", True),
    ]
    out_path = Path(__file__).resolve().parent.parent / "logs" / f"gate_5_matrix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    results = []
    for model, patch in cells:
        res = run_cell(model, patch)
        results.append(res)
        out_path.write_text(json.dumps(results, indent=2))
        if res.get("passed_gate_5"):
            print(f"\n*** CELL PASSED: {model} patch={patch}; stopping matrix ***", flush=True)
            break
    print(f"\nwrote {out_path}", flush=True)


if __name__ == "__main__":
    main()
