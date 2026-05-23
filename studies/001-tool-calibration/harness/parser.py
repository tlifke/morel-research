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

# Accept both the fenced form (```tool_code\n<call>\n```) and the bare
# form (tool_code\n<call>) that some sampling regimes / prompt sets
# produce. Match optional 0-3 leading backticks, the literal
# `tool_code` info tag, optional whitespace, a newline, then capture
# the first non-empty line — that's the call.
_TOOL_BLOCK_RE = re.compile(
    r"`{0,3}tool_code\s*\n(?P<body>[^\n]+)",
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
      - `"under_call"` — model invoked NO tool when a target was
        warranted. The most undesirable failure mode — likely
        produces wrong answers from confabulation.
      - `"wrong_tool"` — model invoked a tool, but not the target.
        Recognized a tool was needed; picked the wrong one.
        Separated from under_call so the SHA-256 / prime-sum
        pattern (model called `calculator` when `python_execute`
        was the target) doesn't get conflated with the
        user_knowledge_lookup pattern (model called nothing).

    Scoring rules (per `calibration_methodology.md`):
      - `tool_target=="none"`: success iff no tools were invoked
        (any invocation → over_call).
      - `expected_tool_call=True`: success iff `tool_target` was
        invoked; `wrong_tool` if some other tool invoked;
        `under_call` if no tool invoked.
      - `expected_tool_call=False`: success iff no tool invoked;
        `over_call` regardless of which tool was invoked.
    """
    calls = parse_tool_calls(output)
    target = record["tool_target"]

    if target == "none":
        return (len(calls) == 0, None if len(calls) == 0 else "over_call")

    any_call = len(calls) > 0
    invoked_target = any(c.name == target for c in calls)

    if record["expected_tool_call"]:
        if invoked_target:
            return (True, None)
        if any_call:
            return (False, "wrong_tool")
        return (False, "under_call")
    # expected_tool_call is False
    if any_call:
        return (False, "over_call")
    return (True, None)


_APOS = r"['’]"
_CLARIFY_PATTERNS = (
    re.compile(r"\bcould you (please )?(tell|give|provide|share|specify|clarify|let me know)\b", re.IGNORECASE),
    re.compile(r"\b(please|can you) (tell|provide|share|specify|clarify|let me know)\b", re.IGNORECASE),
    re.compile(r"\bi (need|require|would need) (some|a little|a bit|more|additional)?\s*(more )?(information|details|context|clarification)\b", re.IGNORECASE),
    re.compile(r"\bwhat (is|are|was|were|do you mean by)\b", re.IGNORECASE),
)
_REFUSAL_PATTERNS = (
    re.compile(rf"\bi (cannot|can{_APOS}?t|am unable|am not able|{_APOS}m not able|do not have the ability)\b", re.IGNORECASE),
    re.compile(rf"\bi (don{_APOS}?t|do not) have (access|the (information|data|ability))\b", re.IGNORECASE),
    re.compile(rf"\bi{_APOS}m sorry,?\s*(but|i)\b", re.IGNORECASE),
)


def classify_no_tool_behavior(output: str) -> str:
    """Sub-classify outputs with no tool call.

    Returns one of:
      - `clarifying_question` — the model asks the user for more
        information (with `?` and/or polite-imperative phrasing).
      - `refusal` — the model declines to answer due to claimed
        inability, without asking for clarifying info.
      - `direct_answer` — the residual; includes confident answers,
        hallucinations, and anything that didn't match the other two.

    Order matters: `clarifying_question` is checked first because
    "I can't… could you tell me?" patterns appear and should count as
    clarifying, not refusal.
    """
    text = output.strip()
    if not text:
        return "direct_answer"
    last_q = text.rstrip().endswith("?")
    has_clarify = any(p.search(text) for p in _CLARIFY_PATTERNS)
    if last_q or has_clarify:
        return "clarifying_question"
    if any(p.search(text) for p in _REFUSAL_PATTERNS):
        return "refusal"
    return "direct_answer"


def scored_success(record: dict, output: str) -> bool:
    """Legacy single-bool scorer. Prefer `classify_trial`."""
    success, _ = classify_trial(record, output)
    return success
