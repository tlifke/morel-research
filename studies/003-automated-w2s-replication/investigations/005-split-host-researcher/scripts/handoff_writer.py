"""
Handoff-artifact writer/reader for inv 005 split-host researcher.

Implements the schema and bootstrap message described in
`handoff-artifact-design.md`. Consumes the agent's `messages` list as
collected in `AutonomousAgentLoop._run_session` (via `BaseAgent.execute`)
and produces a small YAML artifact + bootstrap text for the next iteration.

No live model in the loop here — this is pure extraction code.
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import yaml


SCHEMA_VERSION = "1"

# Inv 005 finding 13 (regex calibration): the reference-returning Bash tool
# emits markers indented under a `detected:` heading like `  - MARKER` or
# `  - MARKER: arg1/arg2`. The earlier `^(MARKER)\b` regex required the
# marker at column 0 and never matched. Below is the actual format.
_MARKER_RE = re.compile(
    r"(?:^|\n)\s*-\s+("
    r"LORA_ADAPTER_WRITTEN|EVAL_PREDICTIONS_WRITTEN|VLLM_EVAL_COMPLETE"
    r"|VLLM_INIT_OK|VLLM_INIT_FAIL|FLASHINFER_JIT_FAIL"
    r"|SFT_COMPLETE|SFT_MEMORY_FREED|PROGRESS_COMPLETE"
    r"|CUDA_OOM|OOM|BENIGN_REDIS_WARNING"
    r"|MODULE_NOT_FOUND|FILE_NOT_FOUND|ERROR"
    r")(?:\s*:\s*([^\n]+))?",
)
_EXIT_CODE_RE = re.compile(r"exit_code\s*[:=]\s*(-?\d+)", re.IGNORECASE)
_ELAPSED_RE = re.compile(r"elapsed(?:_sec)?\s*[:=]\s*([0-9.]+)", re.IGNORECASE)
# The shim emits "stdout: N bytes -> /path/to/log" and/or
# "stderr: N bytes -> /path/to/log". Match either.
_FULL_LOG_RE = re.compile(
    r"(?:stdout|stderr|full[_ ]log|log[_ ]path)\s*:\s*"
    r"(?:\d+\s*bytes\s*->\s*)?([/\w][^\s,]+\.(?:log|stdout|stderr|json))",
    re.IGNORECASE,
)
# Also pluck out eval_output.json path if the markers reference it
_EVAL_OUTPUT_RE = re.compile(r"(\S+eval_output\.json)")


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
    m = _EVAL_OUTPUT_RE.search(text)
    if m:
        out["eval_output_path"] = m.group(1)
    markers = []
    for mm in _MARKER_RE.finditer(text):
        name = mm.group(1)
        arg = (mm.group(2) or "").strip()
        markers.append(f"{name}: {arg}" if arg else name)
    if markers:
        out["markers"] = sorted(set(markers))
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
    *,
    strict: bool | None = None,
) -> dict:
    """
    Walk the agent's `messages` list (as accumulated by
    `BaseAgent.execute`) and return a dict matching the handoff schema.

    `server_acks` is the orchestrator response to `evaluate_predictions`
    (e.g. `{"correct": 654, "total": 1315, "transfer_acc": 0.497}`). If
    the session never submitted, leave it None — the artifact will mark
    `ran_to_completion=False` and the failure_log section will summarize
    why.

    ## Contract (sprint 3)

    This function expects the shim used to drive the agent loop to yield
    `UserMessage(content=[ToolResultBlock(...)])` between
    `AssistantMessage`s. Without this, the handoff yaml ends up with
    `bash_markers: null`, `exit_code: null`, `predictions_file: null`,
    etc. — see inv 005 finding 8 + 12.

    If `messages` contains at least one `ToolUseBlock` but **zero**
    `ToolResultBlock` instances, this function logs a warning to stderr
    naming the missing contract. When `strict=True` (or the
    `HANDOFF_STRICT_CONTRACT` env var is set), it raises instead of
    warning. Default behavior is warning-only so existing call sites
    don't break.
    """

    # Contract validation (sprint 3): count tool_use vs tool_result and warn
    # if the shim isn't yielding the latter. See docstring.
    _tool_use_count = 0
    _tool_result_count = 0
    for _msg, _block in _iter_blocks(messages):
        cls = type(_block).__name__
        if cls == "ToolUseBlock":
            _tool_use_count += 1
        elif cls == "ToolResultBlock":
            _tool_result_count += 1
    if _tool_use_count > 0 and _tool_result_count == 0:
        msg = (
            f"handoff_writer: shim contract violation — messages contain "
            f"{_tool_use_count} ToolUseBlock(s) but ZERO ToolResultBlock(s). "
            f"The shim is not yielding tool results to the consumer. Handoff "
            f"artifact will have null bash_markers / predictions_file / exit_code "
            f"/ elapsed_sec. See inv 005 finding 8 + 12 in investigation.md."
        )
        if strict is None:
            strict = os.environ.get("HANDOFF_STRICT_CONTRACT") == "1"
        if strict:
            raise RuntimeError(msg)
        import sys as _sys
        print(f"WARNING: {msg}", file=_sys.stderr, flush=True)

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
            "predictions_file": last_bash_summary.get("eval_output_path"),
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


def make_bootstrap_message(
    handoff_path: str | Path,
    iteration_n: int,
    prior_state: dict | None = None,
) -> str:
    """
    Build the next-iteration's first user message per the design doc's
    "Bootstrap message shape" section. iteration_n is the *prior*
    iteration's number; the new session is N+1.

    When `prior_state` is provided and the prior iteration ran Bash but
    never submitted predictions, the bootstrap inlines a pointed next-
    action: read predictions_file, call evaluate_predictions on it.
    """
    path = str(handoff_path)
    next_n = iteration_n + 1
    handoff_dir = str(Path(path).parent) or "."

    # Inv 005 finding 13: nemotron under patch 4 reads the handoff but
    # doesn't reliably infer "now call evaluate_predictions" from a
    # generic decision prompt. If the prior iteration left a clean
    # eval_output.json on disk but didn't submit it, inline that fact.
    pointed_hint = ""
    if isinstance(prior_state, dict):
        result = prior_state.get("result") or {}
        eval_pred = (result.get("evaluate_predictions") or {})
        predictions_file = result.get("predictions_file")
        ran_bash = (result.get("exit_code") == 0)
        not_submitted = not eval_pred.get("submitted")
        if predictions_file and ran_bash and not_submitted:
            pointed_hint = (
                f"\n**Immediate next action (decided for you, do this first):** "
                f"The prior iteration ran training successfully and wrote "
                f"predictions to:\n\n"
                f"    {predictions_file}\n\n"
                f"You did NOT submit them. Your *first* action this iteration "
                f"is:\n\n"
                f"    1. `Read` that file to get the integer array under "
                f"`\"predictions\"`.\n"
                f"    2. Call `evaluate_predictions` with `{{\"predictions\": "
                f"[that integer array]}}`.\n\n"
                f"Do not re-run training. The predictions already exist. After "
                f"you submit, the iteration is complete; you may then propose "
                f"a new idea.\n"
            )

    return (
        f"You are autonomous-research-agent iteration {next_n}. The previous "
        f"iteration's handoff artifact is at:\n\n"
        f"  {path}\n\n"
        f"Read it first to see what was tried and what was left undone."
        f"{pointed_hint}\n"
        f"If there is no immediate next action specified above, decide whether "
        f"to:\n"
        f"  (a) Iterate on the same idea with a refinement\n"
        f"  (b) Try a new idea informed by the prior result\n"
        f"  (c) Stop because the search has converged\n\n"
        f"Recent history of all prior iterations is in {handoff_dir}/. Read "
        f"those you find relevant. Do not assume context from earlier turns.\n\n"
        f"Begin."
    )
