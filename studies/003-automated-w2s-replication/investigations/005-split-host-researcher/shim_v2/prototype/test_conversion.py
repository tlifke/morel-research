"""Unit tests for shim v2 conversion functions.

Run: uv run pytest prototype/test_conversion.py
"""

from __future__ import annotations

import json

from prototype.client import (
    OpenAINativeAdapter,
    Qwen35HermesEmbedAdapter,
    TextBlock,
    ThinkingBlock,
    ToolUseBlock,
    _anthropic_tools_to_openai_tools,
    _make_tool_result_payload,
    _openai_response_to_anthropic_blocks,
    pick_adapter,
)


def _bash_tool_def():
    return {
        "name": "Bash",
        "description": "Run a shell command.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "timeout": {"type": "integer", "default": 600},
            },
            "required": ["command"],
        },
    }


def test_anthropic_tools_to_openai_tools_preserves_schema():
    out = _anthropic_tools_to_openai_tools([_bash_tool_def()])
    assert len(out) == 1
    fn = out[0]
    assert fn["type"] == "function"
    assert fn["function"]["name"] == "Bash"
    assert fn["function"]["description"] == "Run a shell command."
    assert fn["function"]["parameters"] == _bash_tool_def()["input_schema"]


def test_anthropic_tools_to_openai_tools_handles_empty_input_schema():
    out = _anthropic_tools_to_openai_tools(
        [{"name": "Ping", "description": "ping"}]
    )
    assert out[0]["function"]["parameters"] == {"type": "object", "properties": {}}


def test_anthropic_tools_to_openai_tools_skips_unnamed():
    out = _anthropic_tools_to_openai_tools([{"description": "no name"}])
    assert out == []


def test_openai_response_to_anthropic_blocks_text_only():
    resp = {
        "choices": [
            {
                "message": {"role": "assistant", "content": "hello world"},
                "finish_reason": "stop",
            }
        ]
    }
    blocks, stop_reason = _openai_response_to_anthropic_blocks(resp)
    assert len(blocks) == 1
    assert isinstance(blocks[0], TextBlock)
    assert blocks[0].text == "hello world"
    assert stop_reason == "end_turn"


def test_openai_response_to_anthropic_blocks_tool_calls_only():
    resp = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_abc",
                            "type": "function",
                            "function": {
                                "name": "Bash",
                                "arguments": json.dumps({"command": "ls -la"}),
                            },
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ]
    }
    blocks, stop_reason = _openai_response_to_anthropic_blocks(resp)
    assert stop_reason == "tool_use"
    tool_blocks = [b for b in blocks if isinstance(b, ToolUseBlock)]
    assert len(tool_blocks) == 1
    tb = tool_blocks[0]
    assert tb.id == "call_abc"
    assert tb.name == "Bash"
    assert tb.input == {"command": "ls -la"}


def test_openai_response_to_anthropic_blocks_mixed_content_and_tool():
    resp = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "Running the command now.",
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {
                                "name": "Bash",
                                "arguments": '{"command": "pwd"}',
                            },
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ]
    }
    blocks, stop_reason = _openai_response_to_anthropic_blocks(resp)
    assert stop_reason == "tool_use"
    assert isinstance(blocks[0], TextBlock)
    assert blocks[0].text == "Running the command now."
    assert isinstance(blocks[1], ToolUseBlock)
    assert blocks[1].input == {"command": "pwd"}


def test_openai_response_with_reasoning_emits_thinking_block():
    resp = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "reasoning_content": "I should call Bash.",
                    "content": "Calling now.",
                    "tool_calls": [
                        {
                            "id": "c1",
                            "type": "function",
                            "function": {"name": "Bash", "arguments": '{"command": "ls"}'},
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ]
    }
    blocks, stop_reason = _openai_response_to_anthropic_blocks(resp)
    assert stop_reason == "tool_use"
    assert isinstance(blocks[0], ThinkingBlock)
    assert blocks[0].thinking == "I should call Bash."
    assert any(isinstance(b, ToolUseBlock) for b in blocks)


def test_openai_response_hermes_tags_parsed_for_qwen():
    resp = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": (
                        "Let me run that.\n"
                        '<tool_call>{"name": "Bash", "arguments": {"command": "ls"}}</tool_call>\n'
                        "Done."
                    ),
                },
                "finish_reason": "stop",
            }
        ]
    }
    blocks, stop_reason = _openai_response_to_anthropic_blocks(
        resp, parse_hermes_tags=True
    )
    assert stop_reason == "tool_use"
    tool_blocks = [b for b in blocks if isinstance(b, ToolUseBlock)]
    assert len(tool_blocks) == 1
    assert tool_blocks[0].name == "Bash"
    assert tool_blocks[0].input == {"command": "ls"}
    text_blocks = [b for b in blocks if isinstance(b, TextBlock)]
    assert text_blocks
    assert "Let me run that." in text_blocks[0].text
    assert "<tool_call>" not in text_blocks[0].text


def test_openai_response_finish_reason_length():
    resp = {
        "choices": [
            {
                "message": {"role": "assistant", "content": "truncated..."},
                "finish_reason": "length",
            }
        ]
    }
    _, stop_reason = _openai_response_to_anthropic_blocks(resp)
    assert stop_reason == "max_tokens"


def test_make_tool_result_payload_string_content():
    out = _make_tool_result_payload("call_xyz", "stdout line")
    assert out == {"role": "tool", "tool_call_id": "call_xyz", "content": "stdout line"}


def test_make_tool_result_payload_list_content_collapses():
    out = _make_tool_result_payload(
        "call_1",
        [
            {"type": "text", "text": "first line"},
            {"type": "text", "text": "second line"},
        ],
    )
    assert out["role"] == "tool"
    assert out["tool_call_id"] == "call_1"
    assert out["content"] == "first line\nsecond line"


def test_make_tool_result_payload_is_error_prefix():
    out = _make_tool_result_payload("c1", "boom", is_error=True)
    assert out["content"].startswith("[tool error]")
    assert "boom" in out["content"]


def test_pick_adapter_for_nemotron():
    a = pick_adapter("nemotron-3-nano:4b")
    assert isinstance(a, OpenAINativeAdapter)
    assert a.parse_hermes_tags is False


def test_pick_adapter_for_qwen35():
    a = pick_adapter("qwen3.5:4b")
    assert isinstance(a, Qwen35HermesEmbedAdapter)
    assert a.parse_hermes_tags is True


def test_pick_adapter_for_unknown_falls_back_to_generic():
    a = pick_adapter("some-other-model:7b")
    assert not isinstance(a, (OpenAINativeAdapter, Qwen35HermesEmbedAdapter))


def test_qwen_adapter_embeds_tools_in_system_and_omits_tools_field():
    a = Qwen35HermesEmbedAdapter()
    openai_tools = _anthropic_tools_to_openai_tools([_bash_tool_def()])
    payload = a.shape_request(
        system_prompt="be helpful",
        openai_tools=openai_tools,
        messages=[{"role": "user", "content": "hi"}],
        model="qwen3.5:4b",
        max_tokens=100,
    )
    assert "tools" not in payload
    sys_msg = payload["messages"][0]
    assert sys_msg["role"] == "system"
    assert "be helpful" in sys_msg["content"]
    assert "<tools>" in sys_msg["content"]
    assert '"name": "Bash"' in sys_msg["content"]


def test_openai_native_adapter_passes_tools_field():
    a = OpenAINativeAdapter()
    openai_tools = _anthropic_tools_to_openai_tools([_bash_tool_def()])
    payload = a.shape_request(
        system_prompt="sys",
        openai_tools=openai_tools,
        messages=[{"role": "user", "content": "hi"}],
        model="nemotron-3-nano:4b",
        max_tokens=100,
    )
    assert payload["tools"] == openai_tools
    assert payload["tool_choice"] == "auto"
    assert payload["messages"][0] == {"role": "system", "content": "sys"}
