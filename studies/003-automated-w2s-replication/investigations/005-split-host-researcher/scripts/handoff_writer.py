"""
Handoff-artifact writer/reader for inv 005 split-host researcher.

Implements the schema and bootstrap message described in
`handoff-artifact-design.md`. Consumes the agent's `messages` list as
collected in `AutonomousAgentLoop._run_session` (via `BaseAgent.execute`)
and produces a small YAML artifact + bootstrap text for the next iteration.

No live model in the loop here — this is pure extraction code.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import yaml


SCHEMA_VERSION = "1"

_MARKER_RE = re.compile(
    r"^(LORA_ADAPTER_WRITTEN|EVAL_PREDICTIONS_WRITTEN|VLLM_EVAL_COMPLETE"
    r"|SFT_COMPLETE|OOM|ERROR)\b",
    re.MULTILINE,
)
_EXIT_CODE_RE = re.compile(r"exit_code\s*[:=]\s*(-?\d+)", re.IGNORECASE)
_ELAPSED_RE = re.compile(r"elapsed(?:_sec)?\s*[:=]\s*([0-9.]+)", re.IGNORECASE)
_FULL_LOG_RE = re.compile(r"(?:full[_ ]log|log[_ ]path)\s*[:=]\s*([^\s,]+)", re.IGNORECASE)


def _iter_blocks(messages: Iterable[Any]) -> Iterable[Any]:
    for msg in messages:
        content = getattr(msg, "content", None)
        if content is None:
            continue
        for block in content:
            yield msg, block


def _block_text(block: Any) -> str:
    content = getattr(block, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and "text" in item:
                parts.append(str(item["text"]))
            elif hasattr(item, "text"):
                parts.append(str(item.text))
        return "\n".join(parts)
    return str(content) if content is not None else ""


def _parse_bash_summary(text: str) -> dict:
    out: dict = {}
    m = _EXIT_CODE_RE.search(text)
    if m:
        try:
            out["exit_code"] = int(m.group(1))
        except ValueError:
            pass
    m = _ELAPSED_RE.search(text)
    if m:
        try:
            out["elapsed_sec"] = float(m.group(1))
        except ValueError:
            pass
    m = _FULL_LOG_RE.search(text)
    if m:
        out["full_log"] = m.group(1).strip().rstrip(",")
    markers = sorted({m.group(1) for m in _MARKER_RE.finditer(text)})
    if markers:
        out["markers"] = markers
    return out


_INVENTED_BASH_NAMES = frozenset({
    "Python", "python", "shell", "exec", "execute", "terminal",
    "run_bash", "run_tool", "Code", "code", "get_file", "file_read",
    "BashCommand", "shellexec",
})


def _classify_tool(name: str) -> str:
    if not name:
        return "unknown"
    if name == "Bash":
        return "canonical_bash"
    if name.lower() == "bash":
        return "lowercase_bash"
    if name in _INVENTED_BASH_NAMES:
        return "invented_bash"
    if name == "evaluate_predictions" or name.endswith("__evaluate_predictions"):
        return "evaluate_predictions"
    return name


def extract_iteration_state(
    messages: list,
    server_acks: dict | None = None,
) -> dict:
    """
    Walk the agent's `messages` list (as accumulated by
    `BaseAgent.execute`) and return a dict matching the handoff schema.

    `server_acks` is the orchestrator response to `evaluate_predictions`
    (e.g. `{"correct": 654, "total": 1315, "transfer_acc": 0.497}`). If
    the session never submitted, leave it None — the artifact will mark
    `ran_to_completion=False` and the failure_log section will summarize
    why.
    """

    tool_use_history: list[dict] = []
    bash_calls: list[dict] = []
    eval_pred_call: dict | None = None
    last_bash_summary: dict = {}
    result_message: Any = None
    failure_log: list[str] = []

    pending_use_by_id: dict[str, dict] = {}

    for msg, block in _iter_blocks(messages):
        cls = type(block).__name__
        if cls == "ToolUseBlock":
            tool_input = getattr(block, "input", {}) or {}
            entry = {
                "id": getattr(block, "id", None),
                "name": getattr(block, "name", ""),
                "kind": _classify_tool(getattr(block, "name", "")),
                "input_keys": sorted(tool_input.keys())
                if isinstance(tool_input, dict)
                else [],
            }
            tool_use_history.append(entry)
            pending_use_by_id[entry["id"]] = entry

            if entry["kind"] in ("canonical_bash", "lowercase_bash"):
                cmd = ""
                if isinstance(tool_input, dict):
                    cmd = str(tool_input.get("command", ""))
                bash_calls.append({"id": entry["id"], "command": cmd[:200]})
            elif entry["kind"] == "evaluate_predictions":
                preds = None
                if isinstance(tool_input, dict):
                    preds = tool_input.get("predictions")
                eval_pred_call = {
                    "id": entry["id"],
                    "predictions_count": len(preds) if isinstance(preds, list) else None,
                }

        elif cls == "ToolResultBlock":
            text = _block_text(block)
            is_error = bool(getattr(block, "is_error", False))
            tuid = getattr(block, "tool_use_id", None)
            origin = pending_use_by_id.get(tuid, {})
            kind = origin.get("kind", "")
            if kind in ("canonical_bash", "lowercase_bash"):
                parsed = _parse_bash_summary(text)
                parsed["is_error"] = is_error
                parsed["tool_use_id"] = tuid
                last_bash_summary = parsed
                bash_calls[-1].update(parsed) if bash_calls else None
            if is_error:
                snippet = text.strip().splitlines()[:3]
                failure_log.append(
                    f"tool_error[{origin.get('name', '?')}]: {' | '.join(snippet)[:300]}"
                )

        elif cls == "ResultMessage":
            result_message = block

    ran_to_completion = eval_pred_call is not None and server_acks is not None
    metrics: dict = {}
    if isinstance(server_acks, dict):
        for k in ("transfer_acc", "weak_acc", "strong_acc", "pgr"):
            if k in server_acks:
                metrics[k] = server_acks[k]
        if "correct" in server_acks and "total" in server_acks and "transfer_acc" not in metrics:
            try:
                metrics["transfer_acc"] = float(server_acks["correct"]) / float(
                    server_acks["total"]
                )
            except (TypeError, ValueError, ZeroDivisionError):
                pass

    if not ran_to_completion:
        if eval_pred_call is None:
            failure_log.append("no evaluate_predictions tool_use observed in session")
        elif server_acks is None:
            failure_log.append(
                "evaluate_predictions submitted but no server_ack captured"
            )

    canonical_n = sum(1 for e in tool_use_history if e["kind"] == "canonical_bash")
    lowercase_n = sum(1 for e in tool_use_history if e["kind"] == "lowercase_bash")
    invented_n = sum(1 for e in tool_use_history if e["kind"] == "invented_bash")

    stop_reason = None
    if result_message is not None:
        stop_reason = getattr(result_message, "stop_reason", None) or getattr(
            result_message, "result", None
        )

    state = {
        "schema_version": SCHEMA_VERSION,
        "iteration": None,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "parent_iteration_path": None,
        "idea": {
            "uid": None,
            "name": None,
            "source_code": {"path": None, "commit": None},
            "hypothesis": None,
        },
        "attempted_command": {
            "argv": None,
            "cwd": None,
            "full_log": last_bash_summary.get("full_log"),
        },
        "result": {
            "ran_to_completion": ran_to_completion,
            "exit_code": last_bash_summary.get("exit_code"),
            "elapsed_sec": last_bash_summary.get("elapsed_sec"),
            "metrics": metrics or None,
            "predictions_file": None,
            "evaluate_predictions": {
                "submitted": eval_pred_call is not None,
                "predictions_count": (eval_pred_call or {}).get("predictions_count"),
                "server_ack": server_acks if isinstance(server_acks, dict) else None,
            },
        },
        "tool_call_shape": {
            "canonical_bash": canonical_n,
            "lowercase_bash": lowercase_n,
            "invented_bash": invented_n,
            "evaluate_predictions": 1 if eval_pred_call else 0,
            "total_tool_uses": len(tool_use_history),
            "stop_reason": stop_reason,
        },
        "bash_markers": last_bash_summary.get("markers"),
        "artifacts": {},
        "learnings": [],
        "next_action_hints": [],
        "failure_log": failure_log,
    }
    return state


def write_handoff(state: dict, output_dir: str | Path, iteration: int) -> Path:
    """Write the handoff dict as YAML to `<output_dir>/iteration_NN.yaml`."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    state = dict(state)
    state["iteration"] = iteration
    path = out_dir / f"iteration_{iteration:02d}.yaml"
    with open(path, "w") as f:
        yaml.safe_dump(
            state,
            f,
            sort_keys=False,
            default_flow_style=False,
            allow_unicode=True,
        )
    return path


def read_handoff(path: str | Path) -> dict:
    """Read a handoff YAML back into a dict."""
    with open(path) as f:
        return yaml.safe_load(f)


def make_bootstrap_message(handoff_path: str | Path, iteration_n: int) -> str:
    """
    Build the next-iteration's first user message per the design doc's
    "Bootstrap message shape" section. iteration_n is the *prior*
    iteration's number; the new session is N+1.
    """
    path = str(handoff_path)
    next_n = iteration_n + 1
    handoff_dir = str(Path(path).parent) or "."
    return (
        f"You are autonomous-research-agent iteration {next_n}. The previous "
        f"iteration's handoff artifact is at:\n\n"
        f"  {path}\n\n"
        f"Read it first, then decide whether to:\n"
        f"  (a) Iterate on the same idea with a refinement\n"
        f"  (b) Try a new idea informed by the prior result\n"
        f"  (c) Stop because the search has converged\n\n"
        f"Recent history of all prior iterations is in {handoff_dir}/. Read "
        f"those you find relevant. Do not assume context from earlier turns.\n\n"
        f"Begin."
    )
