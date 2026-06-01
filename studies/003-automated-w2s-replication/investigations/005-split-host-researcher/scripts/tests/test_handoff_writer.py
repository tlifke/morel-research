"""
Synthetic-input tests for handoff_writer.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional, Union

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from handoff_writer import (
    extract_iteration_state,
    make_bootstrap_message,
    read_handoff,
    write_handoff,
)


@dataclass
class TextBlock:
    text: str


@dataclass
class ToolUseBlock:
    id: str
    name: str
    input: dict


@dataclass
class ToolResultBlock:
    tool_use_id: str
    content: Any
    is_error: bool = False


@dataclass
class AssistantMessage:
    content: List[Union[TextBlock, ToolUseBlock]]
    model: Optional[str] = None


@dataclass
class UserMessage:
    content: List[Union[TextBlock, ToolResultBlock]]


@dataclass
class ResultMessage:
    result: Optional[str] = None
    stop_reason: Optional[str] = None


BASH_SUMMARY = (
    "exit_code: 0\n"
    "elapsed: 94.56s\n"
    "stdout: 31250 bytes -> results/run_001/bash_0017.stdout\n"
    "stderr: 412 bytes\n"
    "\n"
    "detected:\n"
    "  - LORA_ADAPTER_WRITTEN\n"
    "  - EVAL_PREDICTIONS_WRITTEN: results/run_001/eval_output.json\n"
    "  - VLLM_EVAL_COMPLETE\n"
    "\n"
    "--- stdout: last 40 lines ---\n"
    "...vllm chatter...\n"
    "eval_output.json written to results/run_001/eval_output.json\n"
)


def _success_messages():
    bash_use = ToolUseBlock(
        id="toolu_01",
        name="Bash",
        input={"command": "python -m w2s_research.ideas.vanilla_w2s.run --test-size 64"},
    )
    bash_result = ToolResultBlock(
        tool_use_id="toolu_01",
        content=[{"type": "text", "text": BASH_SUMMARY}],
    )
    eval_use = ToolUseBlock(
        id="toolu_02",
        name="evaluate_predictions",
        input={"predictions": [1, 0, 1, 1, 0] * 263},
    )
    eval_result = ToolResultBlock(
        tool_use_id="toolu_02",
        content=[{"type": "text", "text": '{"correct": 654, "total": 1315}'}],
    )
    return [
        AssistantMessage(content=[TextBlock(text="Running SFT..."), bash_use]),
        UserMessage(content=[bash_result]),
        AssistantMessage(content=[eval_use]),
        UserMessage(content=[eval_result]),
        ResultMessage(result="ok", stop_reason="end_turn"),
    ]


def test_success_state():
    messages = _success_messages()
    server_acks = {"correct": 654, "total": 1315, "transfer_acc": 0.497}
    state = extract_iteration_state(messages, server_acks=server_acks)

    assert state["result"]["ran_to_completion"] is True
    assert state["result"]["evaluate_predictions"]["submitted"] is True
    assert state["result"]["evaluate_predictions"]["server_ack"] == server_acks
    assert state["result"]["metrics"]["transfer_acc"] == 0.497
    assert state["result"]["exit_code"] == 0
    assert state["result"]["elapsed_sec"] == pytest.approx(94.56)
    assert state["attempted_command"]["full_log"] == "results/run_001/bash_0017.stdout"
    assert "LORA_ADAPTER_WRITTEN" in (state["bash_markers"] or [])
    assert state["tool_call_shape"]["canonical_bash"] == 1
    assert state["tool_call_shape"]["lowercase_bash"] == 0
    assert state["tool_call_shape"]["evaluate_predictions"] == 1
    assert state["failure_log"] == []


def test_failure_state_no_evaluate():
    messages = [m for m in _success_messages() if not (
        isinstance(m, AssistantMessage)
        and any(getattr(b, "name", "") == "evaluate_predictions" for b in m.content)
    )]
    messages = [
        m for m in messages
        if not (
            isinstance(m, UserMessage)
            and any(getattr(b, "tool_use_id", "") == "toolu_02" for b in m.content)
        )
    ]

    state = extract_iteration_state(messages, server_acks=None)

    assert state["result"]["ran_to_completion"] is False
    assert state["result"]["evaluate_predictions"]["submitted"] is False
    assert any("no evaluate_predictions" in s for s in state["failure_log"])
    assert state["tool_call_shape"]["evaluate_predictions"] == 0


def test_round_trip(tmp_path):
    messages = _success_messages()
    server_acks = {"correct": 654, "total": 1315, "transfer_acc": 0.497}
    state = extract_iteration_state(messages, server_acks=server_acks)

    path = write_handoff(state, tmp_path, iteration=3)
    assert path.name == "iteration_03.yaml"
    assert path.exists()

    loaded = read_handoff(path)
    expected = dict(state)
    expected["iteration"] = 3
    assert loaded == expected


def test_bootstrap_message():
    msg = make_bootstrap_message(".agent_handoff/iteration_03.yaml", iteration_n=3)
    assert "iteration 4" in msg
    assert ".agent_handoff/iteration_03.yaml" in msg
    assert len(msg) < 1000


def test_tool_call_classification_includes_invented():
    """Inv 004's mixed-case bash variants + Python-tool hallucinations
    should be counted under lowercase_bash / invented_bash, not silently
    pass through as raw names."""
    messages = [
        AssistantMessage(content=[
            ToolUseBlock(id="t1", name="Bash", input={"command": "ls"}),
            ToolUseBlock(id="t2", name="bash", input={"command": "ls"}),
            ToolUseBlock(id="t3", name="BASH", input={"command": "ls"}),
            ToolUseBlock(id="t4", name="Python", input={"code": "print(1)"}),
            ToolUseBlock(id="t5", name="run_bash", input={"command": "ls"}),
            ToolUseBlock(id="t6", name="terminal", input={"command": "ls"}),
        ]),
        ResultMessage(result="ok", stop_reason="end_turn"),
    ]
    state = extract_iteration_state(messages, server_acks=None)
    shape = state["tool_call_shape"]
    assert shape["canonical_bash"] == 1
    assert shape["lowercase_bash"] == 2  # bash, BASH
    assert shape["invented_bash"] == 3   # Python, run_bash, terminal
    assert shape["total_tool_uses"] == 6
