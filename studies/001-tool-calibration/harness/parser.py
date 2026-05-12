"""Parse tool calls out of Gemma 3 IT model output.

Per Gemma 3's tool-calling convention (see prompt_format.py), the
model emits a fenced block with the `tool_code` info tag and a
single function-call expression inside:

    ```tool_code
    calculator(expression="3 * 17")
    ```

This parser detects (a) whether any `tool_code` block appears, and
(b) which tool name(s) were invoked. Argument extraction is
best-effort — the harness's calibration scoring (per
`calibration_methodology.md`) only checks whether the *target* tool
was invoked, not the argument shape, so partial parses are
acceptable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_TOOL_BLOCK_RE = re.compile(
    r"```tool_code\s*\n(?P<body>.*?)\n```",
    re.DOTALL,
)
_CALL_RE = re.compile(r"(?P<name>[a-z_][a-z_0-9]*)\s*\(")


@dataclass
class ToolCall:
    name: str
    raw_block: str


def parse_tool_calls(output: str) -> list[ToolCall]:
    calls: list[ToolCall] = []
    for block in _TOOL_BLOCK_RE.finditer(output):
        body = block.group("body").strip()
        m = _CALL_RE.search(body)
        if m:
            calls.append(ToolCall(name=m.group("name"), raw_block=block.group(0)))
    return calls


def classify_trial(record: dict, output: str) -> tuple[bool, str | None]:
    """Classify a single trial against a record's expected behavior.

    Returns `(success, error_type)`. `error_type` is None on success;
    otherwise one of:
      - `"over_call"` — model invoked a tool when none was warranted.
        Per reviewer direction (2026-05-12): less undesirable, since
        the tool typically ensures correctness even on tasks the
        model could have answered directly.
      - `"under_call"` — model failed to invoke a warranted tool.
        More undesirable — likely produces wrong answers.

    Scoring rules (per `calibration_methodology.md`):
      - `tool_target=="none"`: success iff no tools were invoked.
      - `expected_tool_call=True`: success iff `tool_target` was
        invoked; under_call otherwise.
      - `expected_tool_call=False`: success iff `tool_target` was
        NOT invoked; over_call otherwise.
    """
    calls = parse_tool_calls(output)
    target = record["tool_target"]

    if target == "none":
        return (len(calls) == 0, None if len(calls) == 0 else "over_call")

    invoked_target = any(c.name == target for c in calls)
    if record["expected_tool_call"]:
        return (invoked_target, None if invoked_target else "under_call")
    return (not invoked_target, None if not invoked_target else "over_call")


def scored_success(record: dict, output: str) -> bool:
    """Legacy single-bool scorer. Prefer `classify_trial`."""
    success, _ = classify_trial(record, output)
    return success
