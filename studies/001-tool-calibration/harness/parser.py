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


def scored_success(record: dict, output: str) -> bool:
    """Score a single trial against a record's expected behavior.

    Per `calibration_methodology.md`:
    - expected_tool_call=True: success iff the model invoked
      `tool_target`.
    - expected_tool_call=False: success iff the model did NOT invoke
      `tool_target`.
    - tool_target=="none": success iff no tools were invoked at all.
    """
    calls = parse_tool_calls(output)
    target = record["tool_target"]
    if target == "none":
        return len(calls) == 0
    invoked_target = any(c.name == target for c in calls)
    if record["expected_tool_call"]:
        return invoked_target
    return not invoked_target
